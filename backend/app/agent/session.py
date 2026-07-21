import json
from enum import Enum
from typing import Any, Iterator, Optional, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agent.orchestrator import Orchestrator


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

    def run(self, project, user_message: str, orchestrator: "Orchestrator") -> Iterator[str]:
        """Run one turn of the agent session.

        Appends the user message, asks the orchestrator to decide the next
        action, yields SSE events for the response, and updates session state.
        """
        self.append_message("user", user_message)
        self.mark_waiting(False)

        context = self._build_architect_context(project, user_message)
        action = orchestrator.decide_action(context)
        if not action:
            self.mark_waiting(True)
            yield sse_text("我没理解你的意思，能再说详细一点吗？")
            return

        if action.response_to_user:
            yield sse_text(action.response_to_user)

        if action.action == "ask":
            self.mark_waiting(True)
            yield sse_event("question", {"text": action.confirmation_message or action.response_to_user})
            self.append_message("assistant", action.response_to_user)
            return

        yield from orchestrator.run_action(self, project, action, user_message)

        if action.action in ("advance", "render"):
            self.mark_waiting(True)

        self.append_message("assistant", action.response_to_user)

    def _build_architect_context(self, project, user_message: str) -> str:
        """Build the context string fed to the architect LLM."""
        lines = [
            f"Current step: {self.step}",
            f"Autonomy level: {self.autonomy_level}",
            f"Project title: {project.title}",
            f"Target format: {project.target_format or '16:9'}",
            f"Target duration: {project.target_duration or 30}s",
        ]
        if project.source_url:
            lines.append(f"Source URL: {project.source_url}")
        if self.payload:
            lines.append(f"\nCurrent payload: {json.dumps(self.payload, ensure_ascii=False)[:2000]}")
        lines.append(f"\nUser message: {user_message}")
        return "\n".join(lines)


def sse_event(kind: str, data: dict) -> str:
    """Format an SSE data line with a typed event payload."""
    return f"data: {json.dumps({'type': kind, **data}, ensure_ascii=False)}\n\n"


def sse_text(text: str) -> str:
    """Emit a streaming text/token SSE event."""
    return sse_event("token", {"text": text})


def sse_done() -> str:
    """Emit the terminal SSE event."""
    return sse_event("done", {})


def sse_error(message: str) -> str:
    """Emit an error SSE event."""
    return sse_event("error", {"message": message})
