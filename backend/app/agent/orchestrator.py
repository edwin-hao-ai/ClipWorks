import json
import logging
import re
from contextlib import contextmanager
from typing import Iterator, Optional
from unittest.mock import MagicMock

from pydantic import BaseModel, Field

from app.agent.llm import KimiClient
from app.agent.prompts import ARCHITECT_SYSTEM_PROMPT
from app.agent.session import AgentSession, sse_event, sse_text
from app.agent.tools import (
    run_assets,
    run_effects,
    run_render,
    run_scenes,
    run_script,
    run_understand,
)
from app.config import KIMI_PLANNING_MODEL

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


class Orchestrator:
    def __init__(self):
        self.tools = {
            "understand": run_understand,
            "script": run_script,
            "assets": run_assets,
            "scenes": run_scenes,
            "effects": run_effects,
            "render": run_render,
        }
        self.client = KimiClient(model=KIMI_PLANNING_MODEL)

    def decide_action(self, context: str) -> Optional[AgentAction]:
        """Ask the architect LLM to decide the next action and parse it."""
        full_text = ""
        try:
            for chunk in self.client.chat_completion_stream(
                ARCHITECT_SYSTEM_PROMPT,
                [{"role": "user", "content": context}],
                temperature=0.7,
            ):
                full_text += chunk
        except Exception as exc:
            logger.warning("Architect LLM failed: %s", exc)
            return AgentAction(
                action="ask",
                response_to_user="我没听清，能再说一下你的需求吗？",
                confirmation_message="能再说一下你的需求吗？",
            )
        return parse_action_json(full_text)

    def _tool_mock(self, tool_name: str, return_value):
        """Test helper context manager that replaces a single tool with a mock."""
        @contextmanager
        def _cm():
            mock = MagicMock(return_value=return_value)
            original = self.tools.get(tool_name)
            self.tools[tool_name] = mock
            try:
                yield mock
            finally:
                if original is None:
                    self.tools.pop(tool_name, None)
                else:
                    self.tools[tool_name] = original
        return _cm()

    def run_action(
        self,
        session: AgentSession,
        project,
        action: AgentAction,
        user_input: str | None = None,
    ) -> Iterator[str]:
        if action.action == "ask":
            session.mark_waiting(True)
            yield sse_text(action.response_to_user)
            yield sse_event("question", {"text": action.confirmation_message or action.response_to_user})
            return

        if action.action == "run_tool":
            step = action.target_step or session.step
            tool = self.tools.get(step)
            if not tool:
                yield sse_event("error", {"message": f"No tool for step {step}"})
                return
            session.mark_waiting(False)
            yield from tool(project, session.to_dict(), user_input)
            return

        if action.action == "advance":
            target = action.target_step
            if not target:
                yield sse_event("error", {"message": "advance action requires target_step"})
                return
            session.set_step(target)
            session.mark_waiting(True)
            yield sse_text(action.response_to_user)
            return

        if action.action == "revise":
            tool = self.tools.get(session.step)
            if not tool:
                yield sse_event("error", {"message": f"No tool for step {session.step}"})
                return
            session.mark_waiting(False)
            yield from tool(project, session.to_dict(), user_input)
            return

        if action.action == "reset":
            session.set_step("understand")
            session.payload = {}
            session.mark_waiting(True)
            yield sse_text(action.response_to_user or "好的，我们重新开始。")
            return

        yield sse_event("error", {"message": f"Unknown action {action.action}"})
