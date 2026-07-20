import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.planner import _normalize_plan
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_scenes
from app.agent.steps._prompts import SCENES_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_scenes_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not data or "scenes" not in data:
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    script = state.get("script", {})
    assets = state.get("assets", {})
    lines = [
        f"Project title: {project.title}",
        f"Target duration: {project.target_duration or script.get('duration', 30)}s",
        f"Target format: {project.target_format or script.get('format', '16:9')}",
        f"Script: {json.dumps(script, ensure_ascii=False)}",
        f"Assets: {json.dumps(assets, ensure_ascii=False)}",
    ]
    if user_input:
        lines.append(f"User feedback: {user_input}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(SCENES_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Scenes step LLM unavailable: %s", exc)
        scenes = fallback_scenes(project, state)
        yield sse_token("AI 暂不可用，已生成默认场景。")
        yield sse_done()
        state["scenes"] = scenes
        return

    parsed = _extract_scenes_json(full_text)
    if parsed:
        plan = {
            "duration": project.target_duration or state.get("script", {}).get("duration", 30),
            "scenes": parsed["scenes"],
        }
        _normalize_plan(plan)
        state["scenes"] = {"scenes": plan["scenes"]}
    else:
        logger.warning("Scenes step unparseable: %s", full_text)
        yield sse_error("无法解析场景，请手动编辑或重试。")
        state["scenes"] = fallback_scenes(project, state)
    yield sse_done()
