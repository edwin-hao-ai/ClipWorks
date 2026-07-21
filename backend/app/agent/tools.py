import json
import logging
from typing import Iterator, Optional

from app.agent.llm import KimiClient, LLMUnavailableError
from app.agent.prompts import ARCHITECT_SYSTEM_PROMPT
from app.agent.session import sse_done, sse_error, sse_text
from app.config import KIMI_PLANNING_MODEL

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
