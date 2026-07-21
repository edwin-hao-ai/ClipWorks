import json
import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentAction(BaseModel):
    action: str = Field(..., pattern="^(ask|run_tool|advance|revise|reset|render)$")
    target_step: Optional[str] = None
    response_to_user: str = ""
    payload: dict = Field(default_factory=dict)
    requires_confirmation: bool = True
    confirmation_message: str = ""


def _extract_json_block(text: str) -> Optional[str]:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    return None


def parse_action_json(text: str) -> Optional[AgentAction]:
    block = _extract_json_block(text)
    if not block:
        return None
    try:
        data = json.loads(block)
    except json.JSONDecodeError:
        return None
    try:
        return AgentAction(**data)
    except Exception as exc:
        logger.warning("Invalid action JSON: %s", exc)
        return None
