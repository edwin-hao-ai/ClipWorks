import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.prompts import ARCHITECT_SYSTEM_PROMPT
from app.agent.session import sse_done, sse_error, sse_event, sse_text
from app.config import KIMI_PLANNING_MODEL
from app.models import RenderJob
from app.routers.renders import _check_credits, render_video_task

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
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())
        if isinstance(data, dict) and "summary" in data:
            return data
    except Exception:
        pass
    return None


def run_understand(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, user_input, state)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(
            _UNDERSTAND_SYSTEM_PROMPT,
            [{"role": "user", "content": context}],
            temperature=0.7,
        ):
            full_text += chunk
            yield sse_text(chunk)
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
        yield sse_done()
        return
    except Exception as exc:
        logger.exception("Understand failed: %s", exc)
        yield sse_error("理解需求失败。")
        yield sse_done()
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
    yield sse_done()


from app.agent.steps import run_step


def run_script(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_step("script", project, state, user_input)


def run_assets(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_step("assets", project, state, user_input)


def run_scenes(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_step("scenes", project, state, user_input)


def run_effects(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_step("effects", project, state, user_input)


def run_render(project, state: dict, user_input: Optional[str] = None, db=None, user=None) -> Iterator[str]:
    if not db or not user:
        yield sse_error("Internal error: missing db or user for render")
        return
    try:
        _check_credits(user)
    except Exception as exc:
        yield sse_error(str(exc))
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
        "title": script.get("title", project.title),
        "hook": script.get("hook", ""),
        "format": script.get("format", project.target_format or "16:9"),
        "duration": script.get("duration", project.target_duration or 30),
        "scenes": enriched_scenes,
        "assets_needed": [a.get("description", "") for a in state.get("payload", {}).get("assets", {}).get("needed", [])],
        "engine_hint": None,
    }

    job = RenderJob(project_id=project.id, status="queued", logs=[])
    db.add(job)
    db.commit()
    db.refresh(job)
    render_video_task.delay(job.id, project.id, None, None, plan)
    yield sse_event("job_created", {"job_id": job.id, "status": "queued"})
    yield sse_done()

