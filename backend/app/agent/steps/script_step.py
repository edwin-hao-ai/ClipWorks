import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_script
from app.agent.steps._prompts import SCRIPT_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_script_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not data:
        return None
    required = {"title", "hook", "roles", "narrative_arc", "cta", "duration", "format"}
    if not required.issubset(data.keys()):
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    lines = [
        f"Project title: {project.title}",
        f"Target format: {project.target_format or '16:9'}",
        f"Target duration: {project.target_duration or 30}s",
    ]
    if project.source_url:
        lines.append(f"Source URL: {project.source_url}")
    if user_input:
        lines.append(f"User brief / feedback: {user_input}")
    messages = state.get("messages", [])
    if messages:
        lines.append("\nConversation so far:")
        for m in messages[-6:]:
            lines.append(f"{m.get('role')}: {m.get('content', '')[:300]}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(SCRIPT_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Script step LLM unavailable: %s", exc)
        script = fallback_script(project, state)
        yield sse_token("AI 暂不可用，已生成可编辑默认脚本。")
        yield sse_done()
        state["script"] = script
        return

    parsed = _extract_script_json(full_text)
    if parsed:
        state["script"] = parsed
    else:
        logger.warning("Script step produced unparseable output: %s", full_text)
        yield sse_error("无法解析脚本，请手动编辑或重试。")
        state["script"] = fallback_script(project, state)
    yield sse_done()
