import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.steps._base import parse_json, sse_done, sse_error, sse_token
from app.agent.steps._fallbacks import fallback_assets
from app.agent.steps._prompts import ASSETS_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL

logger = logging.getLogger(__name__)


def _extract_assets_json(text: str) -> Optional[dict]:
    data = parse_json(text)
    if not isinstance(data, dict) or "needed" not in data:
        return None
    return data


def _build_context(project, state: dict, user_input: Optional[str]) -> str:
    script = state.get("script", {})
    lines = [
        f"Project title: {project.title}",
        f"Script: {json.dumps(script, ensure_ascii=False)}",
    ]
    if user_input:
        lines.append(f"User feedback: {user_input}")
    return "\n".join(lines)


def run(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    client = KimiClient(model=KIMI_PLANNING_MODEL)
    context = _build_context(project, state, user_input)
    full_text = ""
    try:
        for chunk in client.chat_completion_stream(ASSETS_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=1.0):
            full_text += chunk
            yield sse_token(chunk)
    except LLMUnavailableError as exc:
        logger.warning("Assets step LLM unavailable: %s", exc)
        assets = fallback_assets(project, state)
        state["assets"] = assets
        yield sse_token("AI 暂不可用，已生成默认素材清单。")
        yield sse_done()
        return
    except Exception as exc:
        logger.exception("Assets step failed: %s", exc)
        yield sse_error("素材清单生成失败，已使用默认素材清单。")
        state["assets"] = fallback_assets(project, state)
        yield sse_done()
        return

    parsed = _extract_assets_json(full_text)
    if parsed:
        state["assets"] = parsed
    else:
        logger.warning("Assets step unparseable: %s", full_text)
        yield sse_error("无法解析素材清单，请手动编辑或重试。")
        state["assets"] = fallback_assets(project, state)
    yield sse_done()
