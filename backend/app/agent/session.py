import json
from enum import Enum
from typing import Any, Iterator, Optional, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from app.agent.orchestrator import Orchestrator


# Ordered workflow steps for the vibe-video agent loop.
ORDERED_STEPS = ["understand", "script", "assets", "scenes", "effects", "render", "done"]


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
        # Projects created through the legacy wizard default to step "idle".
        # The Vibe workflow always starts at "understand".
        raw_step = loaded.get("step", "understand")
        self.step = raw_step if raw_step and raw_step != "idle" else "understand"
        self.payload = loaded.get("payload", {})
        self.messages = loaded.get("messages", [])
        # 默认 full_auto：确认模式目前无 UI 入口，确认 each 会导致默认死锁。
        self.autonomy_level = loaded.get("autonomy_level", AutonomyLevel.FULL_AUTO)
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

    def _next_step(self, step: str) -> Optional[str]:
        """Return the step that follows ``step`` in the ordered workflow."""
        try:
            idx = ORDERED_STEPS.index(step)
        except ValueError:
            return None
        return ORDERED_STEPS[idx + 1] if idx + 1 < len(ORDERED_STEPS) else None

    def _step_has_payload(self) -> bool:
        """Return True when the current step already has generated content."""
        data = self.payload.get(self.step)
        if isinstance(data, dict):
            return bool(data)
        return bool(data)

    def _should_auto_confirm(self, action: "AgentAction") -> bool:
        """Return True when the configured autonomy level allows skipping confirmation."""
        if self.autonomy_level == AutonomyLevel.FULL_AUTO:
            return True
        if self.autonomy_level == AutonomyLevel.CONFIRM_RENDER_ONLY and action.action != "render":
            return True
        return False

    def run(
        self,
        project,
        user_message: str,
        orchestrator: "Orchestrator",
        user=None,
    ) -> Iterator[str]:
        """Run the agent session loop.

        Appends the user message, then repeatedly asks the orchestrator to
        decide the next action, yielding SSE events and updating session state.
        The loop stops when a question/confirmation is needed, the workflow
        reaches the render step, or an iteration limit is hit.
        """
        self.append_message("user", user_message)
        self.mark_waiting(False)

        max_actions = 30
        for i in range(max_actions):
            context = self._build_architect_context(project, user_message)
            action = orchestrator.decide_action(context)
            if not action:
                self.mark_waiting(True)
                yield sse_text("我没理解你的意思，能再说详细一点吗？")
                return

            # Guard against an LLM that tries to re-run a step whose payload
            # already exists, or that tries to run a tool out of order.  The
            # workflow progression is deterministic: generate payload, then
            # advance.  We override the architect here instead of trusting it.
            if action.action == "run_tool":
                if self.step == "render":
                    # The render step needs the special render action (it passes
                    # db/user to the render tool).  Treat run_tool(render) as
                    # render so the workflow can finish.
                    from app.agent.orchestrator import AgentAction

                    action = AgentAction(
                        action="render",
                        target_step="render",
                        response_to_user=action.response_to_user or "开始渲染。",
                    )
                elif self._step_has_payload():
                    next_step = self._next_step(self.step)
                    if next_step:
                        from app.agent.orchestrator import AgentAction

                        action = AgentAction(
                            action="advance",
                            target_step=next_step,
                            response_to_user=f"{self.step} 已完成，继续下一步。",
                        )
                elif action.target_step and action.target_step != self.step:
                    # Force the tool to target the current step.
                    action.target_step = self.step

            # Ensure advance always moves to the correct next step, even if the
            # LLM hallucinates the wrong target_step.
            if action.action == "advance":
                expected_next = self._next_step(self.step)
                if expected_next and action.target_step != expected_next:
                    action.target_step = expected_next

            if action.response_to_user:
                yield sse_text(action.response_to_user)

            # "ask" always waits for the user, even in full_auto (we rely on the
            # prompt to tell the architect not to ask when autonomous).
            if action.action == "ask":
                self.mark_waiting(True)
                yield sse_event("question", {"text": action.confirmation_message or action.response_to_user})
                self.append_message("assistant", action.response_to_user)
                return

            # Enforce autonomy level for advance/render: these transition the
            # workflow forward, so they may require user confirmation depending
            # on the configured level. run_tool/revise are executions of the
            # current step and run immediately.  Confirmation is decided only
            # by the configured autonomy level, not by the LLM's flag.
            if action.action in ("advance", "render") and not self._should_auto_confirm(action):
                self.mark_waiting(True)
                yield sse_event("question", {"text": action.confirmation_message or action.response_to_user})
                self.append_message("assistant", action.response_to_user)
                return

            yield from orchestrator.run_action(self, project, action, user_message if i == 0 else "", user=user)
            self.append_message("assistant", action.response_to_user)

            if action.action == "render":
                self.set_step("done")
                return

            if action.action == "reset":
                return

            # After advancing/running a tool, continue automatically when the
            # autonomy level permits; otherwise wait for the user to confirm.
            if self.autonomy_level == AutonomyLevel.FULL_AUTO:
                self.mark_waiting(False)
                continue

            if self.autonomy_level == AutonomyLevel.CONFIRM_RENDER_ONLY and self.step != "render":
                self.mark_waiting(False)
                continue

            # confirm_each: stay waiting after producing output.
            self.mark_waiting(True)
            return

        # Safety cap: if we somehow exhaust the loop, stop waiting for input.
        self.mark_waiting(True)

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
        if self.messages:
            lines.append("\nRecent conversation:")
            for m in self.messages[-6:]:
                role = m.get("role", "unknown")
                content = str(m.get("content", ""))[:300]
                lines.append(f"{role}: {content}")
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
