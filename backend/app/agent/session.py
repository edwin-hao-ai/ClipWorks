import json
from enum import Enum
from typing import Any, Optional, TypedDict


class AutonomyLevel(str, Enum):
    CONFIRM_EACH = "confirm_each"
    CONFIRM_RENDER_ONLY = "confirm_render_only"
    FULL_AUTO = "full_auto"


class AgentEvent(TypedDict):
    """A single event emitted by the agent session workflow."""

    event: str
    step: Optional[str]
    payload: dict
    message: Optional[str]


class AgentSession:
    """State machine for an LLM-driven video creation agent session.

    Tracks the current workflow step, accumulated payload, conversation
    messages, autonomy level, and whether the orchestrator is waiting for
    user confirmation before proceeding.
    """

    def __init__(
        self,
        project_id: str,
        state: Optional[dict] = None,
    ):
        self.project_id = project_id
        loaded = state or {}
        self.step = loaded.get("step", "understand")
        self.payload = loaded.get("payload", {})
        self.messages = loaded.get("messages", [])
        self.autonomy_level = loaded.get("autonomy_level", AutonomyLevel.CONFIRM_EACH)
        self.pending_user_confirmation = loaded.get("pending_user_confirmation", False)

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "payload": self.payload,
            "messages": self.messages,
            "autonomy_level": self.autonomy_level,
            "pending_user_confirmation": self.pending_user_confirmation,
        }

    def set_step(self, step: str) -> None:
        self.step = step

    def set_payload(self, key: str, value: Any) -> None:
        self.payload[key] = value

    def append_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def mark_waiting(self, waiting: bool = True) -> None:
        self.pending_user_confirmation = waiting


def sse_event(kind: str, data: dict) -> str:
    """Format an SSE data line with a typed event payload."""
    return f"data: {json.dumps({'type': kind, **data}, ensure_ascii=False)}\n\n"


def sse_text(text: str) -> str:
    """Emit a streaming text/token SSE event."""
    return sse_event("token", {"text": text})


def sse_done() -> str:
    """Emit the terminal SSE event."""
    return sse_event("done", {})
