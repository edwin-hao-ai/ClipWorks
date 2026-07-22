import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.session import sse_error, sse_event, sse_text
from app.agent.steps import run_step
from app.config import KIMI_PLANNING_MODEL
from app.models import RenderJob
from app.services.credits import deduct_credits
from app.tasks.render_task import render_video_task

logger = logging.getLogger(__name__)


_UNDERSTAND_SYSTEM_PROMPT = """You are a video planning assistant. Given the project context and user message, produce a concise understanding summary as JSON.

Output format:
```json
{
  "summary": "one sentence describing the video",
  "duration": 30,
  "format": "16:9",
  "audience": "target audience",
  "style": "visual style",
  "platform": "platform if mentioned",
  "cta": "call to action if mentioned"
}
```

Use defaults for missing fields. Respond in the user's language."""


def _build_context(project, user_input: Optional[str], state: dict) -> str:
    lines = [
        f"Project title: {project.title}",
        f"Target format: {project.target_format or '16:9'}",
        f"Target duration: {project.target_duration or 30}s",
    ]
    if project.source_url:
        lines.append(f"Source URL: {project.source_url}")
    if user_input:
        lines.append(f"User input: {user_input}")
    messages = state.get("messages", [])
    if messages:
        lines.append("\nConversation so far:")
        for m in messages[-6:]:
            lines.append(f"{m.get('role')}: {m.get('content', '')[:300]}")
    return "\n".join(lines)


def _extract_understand_json(text: str) -> Optional[dict]:
    # Lazy import to avoid a circular dependency: orchestrator imports tools
    # at module load, so tools cannot import orchestrator top-level.
    from app.agent.orchestrator import _extract_json_block

    block = _extract_json_block(text)
    if not block:
        return None
    try:
        data = json.loads(block)
        if isinstance(data, dict) and "summary" in data:
            return data
    except Exception:
        pass
    return None


def _summary_for_understand(data: dict) -> str:
    summary = data.get("summary") or "需求理解完成"
    parts = [summary]
    if data.get("duration"):
        parts.append(f"{data['duration']} 秒")
    if data.get("format"):
        parts.append(data["format"])
    if data.get("style"):
        parts.append(data["style"])
    return "，".join(parts)


def run_understand(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, user_input, state)
    full_text = ""
    try:
        # Accumulate raw LLM output instead of streaming raw JSON tokens into the chat.
        for chunk in client.chat_completion_stream(
            _UNDERSTAND_SYSTEM_PROMPT,
            [{"role": "user", "content": context}],
            temperature=1.0,
        ):
            full_text += chunk
    except LLMUnavailableError as exc:
        logger.warning("Understand LLM unavailable: %s", exc)
        summary = {
            "summary": user_input or project.title,
            "duration": project.target_duration or 30,
            "format": project.target_format or "16:9",
            "audience": "",
            "style": "",
            "platform": "",
            "cta": "",
        }
        state["payload"]["understand"] = summary
        yield sse_text("AI 暂不可用，已使用默认理解摘要。")
        yield sse_event("artifact", {"kind": "understand", "data": summary})
        return
    except Exception as exc:
        logger.exception("Understand failed: %s", exc)
        yield sse_error("理解需求失败。")
        return

    parsed = _extract_understand_json(full_text)
    if parsed:
        state["payload"]["understand"] = parsed
    else:
        logger.warning("Unparseable understand output: %s", full_text)
        state["payload"]["understand"] = {
            "summary": user_input or project.title,
            "duration": project.target_duration or 30,
            "format": project.target_format or "16:9",
            "audience": "",
            "style": "",
            "platform": "",
            "cta": "",
        }

    data = state["payload"]["understand"]
    yield sse_text(f"已理解需求：{_summary_for_understand(data)}")
    yield sse_event("artifact", {"kind": "understand", "data": data})


def _copy_payload_to_top_level(state: dict, step_name: str) -> None:
    """Mirror the payload entry for a step onto the top-level state dict.

    Existing step generators read/write top-level keys (``state["script"]``,
    ``state["assets"]`` etc.) while the Vibe session keeps the same data under
    ``state["payload"]["..."]``. Copying before/after the generator runs keeps
    both views in sync without rewriting the generators.
    """
    payload = state.setdefault("payload", {})
    if step_name in payload:
        state[step_name] = payload[step_name]


def _copy_top_level_to_payload(state: dict, step_name: str) -> None:
    payload = state.setdefault("payload", {})
    if step_name in state:
        payload[step_name] = state[step_name]


def _step_summary(step_name: str, data) -> str:
    if not isinstance(data, dict):
        return f"{step_name} 步骤已完成"
    if step_name == "script":
        return f"脚本已生成：{data.get('title') or '未命名'}"
    if step_name == "assets":
        needed = data.get("needed") or []
        return f"素材清单已确定（{len(needed)} 项）"
    if step_name == "scenes":
        scenes = data.get("scenes") or []
        return f"已规划 {len(scenes)} 个场景"
    if step_name == "effects":
        effects = data.get("effects") or []
        return f"已设计 {len(effects)} 个场景的动效"
    return f"{step_name} 步骤已完成"


def _run_step_adapter(step_name: str, project, state: dict, user_input: Optional[str]) -> Iterator[str]:
    """Run an existing step generator with payload ↔ top-level syncing.

    Raw streaming JSON chunks are accumulated and replaced by a concise summary
    plus an ``artifact`` event so the Vibe UI can update ``AgentCanvas`` without
    dumping LLM JSON into the chat.
    """
    _copy_payload_to_top_level(state, step_name)
    yield sse_event("progress", {"step": step_name, "progress": 0, "message": f"开始 {step_name}…"})

    try:
        for raw in run_step(step_name, project, state, user_input):
            # Forward errors but swallow raw JSON tokens; we emit a clean summary at the end.
            try:
                parsed = json.loads(raw.strip())
            except Exception:
                parsed = {}
            if isinstance(parsed, dict) and parsed.get("type") == "error":
                yield raw
        _copy_top_level_to_payload(state, step_name)
    except Exception as exc:
        logger.exception("%s adapter failed: %s", step_name, exc)
        yield sse_error(f"{step_name} 执行失败")
        return

    data = state.get(step_name)
    yield sse_text(_step_summary(step_name, data))
    yield sse_event("artifact", {"kind": step_name, "data": data})
    yield sse_event("progress", {"step": step_name, "progress": 100})


def run_script(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from _run_step_adapter("script", project, state, user_input)


def run_assets(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from _run_step_adapter("assets", project, state, user_input)


def run_scenes(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from _run_step_adapter("scenes", project, state, user_input)


def run_effects(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from _run_step_adapter("effects", project, state, user_input)


def run_render(project, state: dict, user_input: Optional[str] = None, user=None) -> Iterator[str]:
    if not user:
        yield sse_error("Internal error: missing user for render")
        return

    # 渲染工具自己管理短生命周期 DB session：Vibe 流在调用前已经关闭 request-scoped
    # session 以释放连接池，因此这里按需新建 session、merge 已 detached 的项目对象。
    from app.database import SessionLocal

    try:
        with SessionLocal() as db:
            attached_project = db.merge(project) if project is not None else None
            if attached_project is None:
                yield sse_error("Internal error: unable to attach project")
                return

            # Build plan from state payload like /agent/approve does.
            script = state.get("payload", {}).get("script", {})
            scenes_data = state.get("payload", {}).get("scenes", {}).get("scenes", [])
            effects_data = state.get("payload", {}).get("effects", {}).get("effects", [])
            enriched_scenes = []
            for i, scene in enumerate(scenes_data):
                effect = next((e for e in effects_data if e.get("scene_index") == i), {})
                enriched = dict(scene)
                enriched["visual_style"] = effect.get("visual_style", "")
                enriched["animation_keywords"] = effect.get("animation_keywords", [])
                enriched["generate_image"] = effect.get("generate_image", False)
                enriched["generate_image_prompt"] = effect.get("generate_image_prompt", "")
                enriched.setdefault("narration", "")
                enriched_scenes.append(enriched)

            plan = {
                "title": script.get("title", attached_project.title),
                "hook": script.get("hook", ""),
                "format": script.get("format", attached_project.target_format or "16:9"),
                "duration": script.get("duration", attached_project.target_duration or 30),
                "scenes": enriched_scenes,
                "assets_needed": [a.get("description", "") for a in state.get("payload", {}).get("assets", {}).get("needed", [])],
                "style": script.get("style", ""),
                "mood": script.get("mood", ""),
                "rhythm": script.get("rhythm", ""),
                "engine_hint": None,
            }

            # Mirror the project-setting updates from /agent/approve so the render
            # uses the approved plan format/duration/title.
            if plan.get("format"):
                attached_project.target_format = plan["format"]
            if plan.get("duration"):
                attached_project.target_duration = plan["duration"]
            if plan.get("title"):
                attached_project.title = plan["title"]

            # Deduct one credit atomically before creating the job so concurrent
            # render requests cannot over-deduct and leave orphan queued jobs.
            if not deduct_credits(db, user.id, amount=1):
                yield sse_error("额度不足，请前往计费页升级套餐")
                return

            attached_project.status = "generating"

            job = RenderJob(project_id=attached_project.id, status="queued", logs=[])
            db.add(job)
            db.commit()
            db.refresh(job)

            render_video_task.delay(job.id, attached_project.id, None, None, plan)
            yield sse_event("job_created", {"job_id": job.id, "status": "queued"})
            yield sse_event("progress", {"step": "render", "progress": 0, "message": "已加入渲染队列"})
            yield sse_event("artifact", {"kind": "render", "data": {"job_id": job.id, "status": "queued"}})
    except Exception as exc:
        logger.exception("run_render failed: %s", exc)
        yield sse_error("渲染任务创建失败")

