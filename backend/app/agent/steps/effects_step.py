import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_effects
from app.agent.steps._prompts import EFFECTS_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_effects_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not data or "effects" not in data:
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    scenes = state.get("scenes", {})
    script = state.get("script", {})
    lines = [
        f"Project title: {project.title}",
        f"Target format: {project.target_format or script.get('format', '16:9')}",
        f"Scenes: {json.dumps(scenes, ensure_ascii=False)}",
    ]
    if user_input:
        lines.append(f"User feedback: {user_input}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(EFFECTS_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Effects step LLM unavailable: %s", exc)
        effects = fallback_effects(project, state)
        yield sse_token("AI 暂不可用，已生成默认动效。")
        yield sse_done()
        state["effects"] = effects
        return

    parsed = _extract_effects_json(full_text)
    if parsed:
        state["effects"] = parsed
    else:
        logger.warning("Effects step unparseable: %s", full_text)
        yield sse_error("无法解析动效，请手动编辑或重试。")
        state["effects"] = fallback_effects(project, state)
    yield sse_done()
