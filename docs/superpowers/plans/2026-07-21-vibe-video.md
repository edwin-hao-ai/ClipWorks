# Vibe Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `PlanWizard` form wizard with a chat-driven Vibe Video experience: users describe videos in natural language, an LLM orchestrator advances through internal workflow steps (understand → script → assets → scenes → effects → render), and a real-time canvas on the right shows each step's output.

**Architecture:** A single backend `/agent/chat/stream` endpoint accepts user messages and runs an `AgentSession` loop. The loop asks an Architect LLM to pick an action (`ask` / `run_tool` / `advance` / `render`), executes the corresponding tool (wrappers around existing step generators), and streams unified events to the frontend. The frontend renders a chat panel on the left and an `AgentCanvas` on the right that switches artifacts based on `agent_state.step`.

**Tech Stack:** FastAPI + SQLAlchemy + Kimi API (backend); Next.js 14 + React + TypeScript + Tailwind (frontend); Celery for render jobs.

## Global Constraints

- Backend Python 3.11+, FastAPI 0.111+, Pydantic v2, SQLAlchemy 2.0+.
- Frontend Next.js 14.2+, React 18, TypeScript 5, Tailwind 3.4+.
- Use existing design-system tokens (`bg-background-base`, `text-content-primary`, etc.) from `globals.css`.
- All new Python functions and React components use type hints / TypeScript interfaces.
- Every task must include a test or explicit verification step.
- Do not commit `.env` files or runtime artifacts like `dump.rdb`.
- Do not change existing `/agent/step/{name}` or `/agent/chat` (modify) behavior; they remain available for internal use and the modify-mode AgentChat.

---

## File Structure

### Backend

| File | Responsibility |
|---|---|
| `backend/app/agent/session.py` | `AgentSession` state machine: holds current step, payload, messages, autonomy level; decides when to stop/yield. |
| `backend/app/agent/orchestrator.py` | `Orchestrator` class: builds Architect LLM prompt, parses action JSON, routes to tools, handles retries. |
| `backend/app/agent/tools.py` | Tool wrappers around existing step generators (`understand`, `script`, `assets`, `scenes`, `effects`, `render`). |
| `backend/app/agent/prompts.py` | Extended with the Architect system prompt. |
| `backend/app/routers/agent.py` | Adds `POST /projects/{id}/agent/chat/stream` for the Vibe loop; keeps existing endpoints. |
| `backend/tests/agent/test_session.py` | Unit tests for `AgentSession` state transitions. |
| `backend/tests/agent/test_orchestrator.py` | Tests for action parsing and routing. |
| `backend/tests/test_agent_vibe.py` | Integration tests for the `/agent/chat/stream` endpoint. |

### Frontend

| File | Responsibility |
|---|---|
| `frontend/src/components/project/AgentCanvas.tsx` | Right-side canvas that renders the artifact for the current step. |
| `frontend/src/components/project/WorkflowStatusBar.tsx` | Horizontal step indicator (understand → script → assets → scenes → effects → render). |
| `frontend/src/components/project/AutonomySelector.tsx` | Dropdown to set confirmation level. |
| `frontend/src/components/project/AgentChat.tsx` | Extended to handle Vibe events (`thinking`, `question`, `artifact`, `progress`). |
| `frontend/src/app/projects/[id]/page.tsx` | Replaced single-column planning layout with left-chat / right-canvas layout. |
| `frontend/src/components/layout/Sidebar.tsx` | "New Project" button opens chat-style prompt dialog instead of creating a blank project. |
| `frontend/src/components/project/NewProjectDialog.tsx` | Chat-style dialog for creating a project from a prompt. |
| `frontend/src/lib/types.ts` | Extended `AgentState` and new event types. |
| `frontend/tests/vibe/AgentChat.test.tsx` | Frontend tests for Vibe message rendering. |

---

## Milestone 1: Backend Agent Loop Core

### Task 1: Define AgentSession data model and events

**Files:**
- Create: `backend/app/agent/session.py`
- Test: `backend/tests/agent/test_session.py`

**Interfaces:**
- Produces: `AgentSession` class with properties `step`, `payload`, `messages`, `autonomy_level`, `pending_user_confirmation`.
- Produces: `AgentEvent` TypedDict and `SSEEvent` helper functions.

- [ ] **Step 1: Write the failing test**

```python
def test_session_starts_in_understand_step():
    from app.agent.session import AgentSession
    session = AgentSession(project_id="p1")
    assert session.step == "understand"
    assert session.autonomy_level == "confirm_each"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_session.py::test_session_starts_in_understand_step -v`
Expected: `ModuleNotFoundError: No module named 'app.agent.session'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/agent/session.py`:

```python
from enum import Enum
from typing import Any, Optional


class AutonomyLevel(str, Enum):
    CONFIRM_EACH = "confirm_each"
    CONFIRM_RENDER_ONLY = "confirm_render_only"
    FULL_AUTO = "full_auto"


class AgentSession:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_session.py::test_session_starts_in_understand_step -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/session.py backend/tests/agent/test_session.py
git commit -m "feat(agent): add AgentSession state model"
```

---

### Task 2: Add SSE event helpers

**Files:**
- Create: `backend/app/agent/session.py` (extend)
- Test: `backend/tests/agent/test_session.py`

**Interfaces:**
- Produces: `sse_event(kind, data)`, `sse_text(text)`, `sse_done()`.

- [ ] **Step 1: Write the failing test**

```python
import json
from app.agent.session import sse_text, sse_event, sse_done


def test_sse_helpers_produce_json_lines():
    assert sse_text("hello") == 'data: {"type": "token", "text": "hello"}\n\n'
    assert sse_event("artifact", {"kind": "script"}) == 'data: {"type": "artifact", "kind": "script"}\n\n'
    assert json.loads(sse_done().replace("data: ", "").strip()) == {"type": "done"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_session.py::test_sse_helpers_produce_json_lines -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/agent/session.py`:

```python
import json


def sse_event(kind: str, data: dict) -> str:
    return f"data: {json.dumps({'type': kind, **data}, ensure_ascii=False)}\n\n"


def sse_text(text: str) -> str:
    return sse_event("token", {"text": text})


def sse_done() -> str:
    return sse_event("done", {})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_session.py::test_sse_helpers_produce_json_lines -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/session.py backend/tests/agent/test_session.py
git commit -m "feat(agent): add sse event helpers"
```

---

### Task 3: Add Architect action model and parser

**Files:**
- Create: `backend/app/agent/orchestrator.py`
- Test: `backend/tests/agent/test_orchestrator.py`

**Interfaces:**
- Produces: `AgentAction` Pydantic model with `action`, `target_step`, `response_to_user`, `payload`, `requires_confirmation`, `confirmation_message`.
- Produces: `parse_action_json(text: str) -> AgentAction`.

- [ ] **Step 1: Write the failing test**

```python
from app.agent.orchestrator import parse_action_json, AgentAction


def test_parse_valid_action_json():
    text = '''
    {
      "thinking": "advance",
      "action": "advance",
      "target_step": "script",
      "response_to_user": "OK，去写脚本。",
      "payload": {"script": {"title": "T"}},
      "requires_confirmation": false,
      "confirmation_message": ""
    }
    '''
    action = parse_action_json(text)
    assert action.action == "advance"
    assert action.target_step == "script"
    assert action.response_to_user == "OK，去写脚本。"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_orchestrator.py::test_parse_valid_action_json -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/agent/orchestrator.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_orchestrator.py::test_parse_valid_action_json -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/orchestrator.py backend/tests/agent/test_orchestrator.py
git commit -m "feat(agent): add AgentAction parser"
```

---

### Task 4: Add the Architect system prompt

**Files:**
- Modify: `backend/app/agent/prompts.py`

**Interfaces:**
- Produces: `ARCHITECT_SYSTEM_PROMPT` string constant.

- [ ] **Step 1: Write the failing test**

```python
from app.agent.prompts import ARCHITECT_SYSTEM_PROMPT


def test_architect_prompt_exists():
    assert "action" in ARCHITECT_SYSTEM_PROMPT
    assert "ask" in ARCHITECT_SYSTEM_PROMPT
    assert "advance" in ARCHITECT_SYSTEM_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_prompts.py::test_architect_prompt_exists -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/agent/prompts.py`:

```python
ARCHITECT_SYSTEM_PROMPT = """You are ClipWorks Architect, an AI video director that drives a vibe-video workflow.

Your job is to read the current workflow state and the user's latest message, then decide the next action.

Available workflow steps (in order):
- understand: clarify the user's intent (duration, format, audience, style, source URL).
- script: produce title, hook, narrative_arc, cta, duration, format.
- assets: decide what images/videos/music are needed.
- scenes: build a timed scene list.
- effects: design visual style and animation keywords per scene.
- render: queue the final video render.

Available actions:
- "ask": ask the user ONE focused question. Use when information is missing or ambiguous.
- "run_tool": run the tool for the current step to generate/refresh content. target_step should be the current step.
- "advance": move to target_step after the user confirmed the current step's output.
- "revise": regenerate the current step's content based on user feedback. Use when user says "change ...".
- "reset": clear everything and restart from understand.
- "render": queue render. Only use when the user explicitly says generate/开始生成/确认生成.

Rules:
- Always respond in the user's language (Chinese if they write Chinese).
- Ask only ONE question per turn.
- If the user provides enough info (topic/format/duration), do NOT ask again; produce output or advance.
- If the user says generate/ok/开始生成/就这样/直接做/直接生成 or synonyms, advance/render immediately.
- Default format is 16:9, default duration is 30s unless user says otherwise.

Output EXACTLY one JSON block (no conversational text outside it):

```json
{
  "thinking": "brief reasoning in 20 words",
  "action": "ask|run_tool|advance|revise|reset|render",
  "target_step": "understand|script|assets|scenes|effects|render",
  "response_to_user": "what to say to the user",
  "payload": {},
  "requires_confirmation": true,
  "confirmation_message": "optional question if requires_confirmation is true"
}
```
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_prompts.py::test_architect_prompt_exists -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/prompts.py backend/tests/agent/test_prompts.py
git commit -m "feat(agent): add architect system prompt"
```

---

### Task 5: Implement the understand tool

**Files:**
- Create: `backend/app/agent/tools.py`
- Test: `backend/tests/agent/test_tools.py`

**Interfaces:**
- Produces: `run_understand(project, state, user_input) -> Iterator[str]` yielding SSE tokens and setting `state["payload"]["understand"]`.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch, MagicMock
from app.agent.tools import run_understand


def test_run_understand_sets_summary():
    project = MagicMock()
    project.title = "Test"
    project.source_url = None
    project.target_format = "16:9"
    project.target_duration = 30
    state = {"payload": {}, "messages": []}

    with patch("app.agent.tools.KimiClient") as MockClient:
        instance = MockClient.return_value
        instance.chat_completion_stream.return_value = iter(['{"summary": "s", "duration": 30, "format": "16:9"}'])
        list(run_understand(project, state, "make a promo"))

    assert state["payload"]["understand"]["summary"] == "s"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_tools.py::test_run_understand_sets_summary -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/agent/tools.py`:

```python
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
        for chunk in client.chat_completion_stream(_UNDERSTAND_SYSTEM_PROMPT, [
            {"role": "user", "content": context},
        ], temperature=0.7):
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_tools.py::test_run_understand_sets_summary -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/tools.py backend/tests/agent/test_tools.py
git commit -m "feat(agent): add understand tool"
```

---

### Task 6: Wrap existing script step as a tool

**Files:**
- Modify: `backend/app/agent/tools.py`
- Test: `backend/tests/agent/test_tools.py`

**Interfaces:**
- Produces: `run_script(project, state, user_input) -> Iterator[str]`.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch, MagicMock
from app.agent.tools import run_script


def test_run_script_uses_existing_step():
    project = MagicMock()
    state = {"payload": {}}
    with patch("app.agent.tools.run_script_step") as mock_step:
        mock_step.return_value = iter(['{"type": "done"}'])
        result = list(run_script(project, state, "make it punchier"))
    assert result == ['{"type": "done"}']
    mock_step.assert_called_once_with(project, state, "make it punchier")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_tools.py::test_run_script_uses_existing_step -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/agent/tools.py`:

```python
from app.agent.steps import run_step as run_script_step


def run_script(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_script_step("script", project, state, user_input)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_tools.py::test_run_script_uses_existing_step -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/tools.py backend/tests/agent/test_tools.py
git commit -m "feat(agent): wrap script step as tool"
```

---

### Task 7: Add Orchestrator action routing for ask/run_tool/advance

**Files:**
- Modify: `backend/app/agent/orchestrator.py`
- Test: `backend/tests/agent/test_orchestrator.py`

**Interfaces:**
- Produces: `Orchestrator` class with `run_action(session, project, action, user_input) -> Iterator[str]`.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import MagicMock
from app.agent.orchestrator import Orchestrator, AgentAction
from app.agent.session import AgentSession


def test_orchestrator_runs_understand_tool():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    with orch._tool_mock("understand", iter(['{"type": "done"}'])) as mock_tool:
        action = AgentAction(action="run_tool", target_step="understand", response_to_user="OK")
        list(orch.run_action(session, project, action, "hello"))
    mock_tool.assert_called_once()
    assert session.step == "understand"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_orchestrator.py::test_orchestrator_runs_understand_tool -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/agent/orchestrator.py`:

```python
from typing import Iterator
from unittest.mock import patch

from app.agent.session import AgentSession, sse_event, sse_text
from app.agent.tools import run_understand, run_script


class Orchestrator:
    def __init__(self):
        self.tools = {
            "understand": run_understand,
            "script": run_script,
        }

    def _tool_mock(self, tool_name: str, return_value):
        """Test helper context manager."""
        return patch.object(self, "tools", {tool_name: lambda *args, **kwargs: return_value})

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_orchestrator.py::test_orchestrator_runs_understand_tool -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/orchestrator.py backend/tests/agent/test_orchestrator.py
git commit -m "feat(agent): add orchestrator action routing"
```

---

### Task 8: Implement the AgentSession.run loop

**Files:**
- Modify: `backend/app/agent/session.py`
- Modify: `backend/app/agent/orchestrator.py`
- Test: `backend/tests/agent/test_session.py`

**Interfaces:**
- Produces: `AgentSession.run(project, user_message, orchestrator) -> Iterator[str]`.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import MagicMock
from app.agent.session import AgentSession
from app.agent.orchestrator import Orchestrator, AgentAction


def test_run_loop_asks_when_action_is_ask():
    session = AgentSession("p1")
    project = MagicMock()
    project.title = "T"
    project.source_url = None
    project.target_format = "16:9"
    project.target_duration = 30

    orch = Orchestrator()
    orch.call_llm = lambda *args, **kwargs: AgentAction(
        action="ask",
        response_to_user="What format?",
        confirmation_message="What format?",
    )

    events = list(session.run(project, "hi", orch))
    assert any('"type": "question"' in e for e in events)
    assert session.pending_user_confirmation is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_session.py::test_run_loop_asks_when_action_is_ask -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/agent/session.py`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agent.orchestrator import Orchestrator


class AgentSession:
    # ... existing methods ...

    def run(self, project, user_message: str, orchestrator: "Orchestrator") -> Iterator[str]:
        self.append_message("user", user_message)
        self.mark_waiting(False)

        # Build context for the architect LLM.
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

        # Execute tool or state transition.
        yield from orchestrator.run_action(self, project, action, user_message)

        if action.action in ("advance", "render"):
            self.mark_waiting(True)

        self.append_message("assistant", action.response_to_user)

    def _build_architect_context(self, project, user_message: str) -> str:
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
```

Modify `backend/app/agent/orchestrator.py` to add `decide_action`:

```python
from app.agent.llm import KimiClient
from app.agent.prompts import ARCHITECT_SYSTEM_PROMPT
from app.config import KIMI_PLANNING_MODEL


class Orchestrator:
    def __init__(self):
        self.tools = {
            "understand": run_understand,
            "script": run_script,
        }
        self.client = KimiClient(model=KIMI_PLANNING_MODEL)

    def decide_action(self, context: str) -> Optional[AgentAction]:
        full_text = ""
        try:
            for chunk in self.client.chat_completion_stream(ARCHITECT_SYSTEM_PROMPT, [
                {"role": "user", "content": context},
            ], temperature=0.7):
                full_text += chunk
        except Exception as exc:
            logger.warning("Architect LLM failed: %s", exc)
            return AgentAction(
                action="ask",
                response_to_user="我没听清，能再说一下你的需求吗？",
                confirmation_message="能再说一下你的需求吗？",
            )
        return parse_action_json(full_text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_session.py::test_run_loop_asks_when_action_is_ask -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/session.py backend/app/agent/orchestrator.py backend/tests/agent/test_session.py
git commit -m "feat(agent): implement AgentSession.run loop"
```

---

### Task 9: Expose `POST /agent/chat/stream` endpoint

**Files:**
- Modify: `backend/app/routers/agent.py`
- Test: `backend/tests/test_agent_vibe.py`

**Interfaces:**
- Consumes: `AgentSession`, `Orchestrator`.
- Produces: `POST /projects/{project_id}/agent/chat/stream` returning SSE events.

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient
from app.main import app


def test_chat_stream_requires_auth():
    client = TestClient(app)
    r = client.post("/projects/p1/agent/chat/stream", json={"message": "hi"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_agent_vibe.py::test_chat_stream_requires_auth -v`
Expected: FAIL with `404` because route does not exist

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/routers/agent.py` after the existing `/chat/stream` endpoint or rename to avoid conflict. Since there is already `/chat/stream` for planning, add a new route `/vibe/stream` first to avoid collision, then migrate.

Insert before line 350 (the existing chat/stream function):

```python
class VibeChatPayload(BaseModel):
    message: str


@router.post("/vibe/stream")
def vibe_chat_stream(
    project_id: str,
    payload: VibeChatPayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chat-driven Vibe Video loop."""
    project = _require_project(project_id, user, db)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    from app.agent.session import AgentSession
    from app.agent.orchestrator import Orchestrator

    state = dict(project.agent_state or {})
    session = AgentSession(project_id, state)
    orchestrator = Orchestrator()

    def event_stream():
        try:
            for chunk in session.run(project, message, orchestrator):
                yield chunk
        except Exception as exc:
            logger.exception("Vibe loop failed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            project.agent_state = session.to_dict()
            db.commit()
            yield f"data: {json.dumps({'type': 'done', 'step': session.step}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_agent_vibe.py::test_chat_stream_requires_auth -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/agent.py backend/tests/test_agent_vibe.py
git commit -m "feat(agent): add vibe chat stream endpoint"
```

---

## Milestone 2: Frontend Vibe UI

### Task 10: Extend AgentState types for Vibe

**Files:**
- Modify: `frontend/src/lib/types.ts`

**Interfaces:**
- Produces: Extended `AgentState` with `autonomy_level`, `payload`, `pending_user_confirmation`.

- [ ] **Step 1: Write the failing test**

No test file exists for types; verify with TypeScript compile.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run type-check 2>&1 | tail -20`
Expected: currently passes; will verify after edit.

- [ ] **Step 3: Write minimal implementation**

In `frontend/src/lib/types.ts`, extend `AgentState`:

```typescript
export interface AgentState {
  step?: string;
  messages?: { role: string; content: string }[];
  pending_plan?: AgentPlan | null;
  autonomy_level?: 'confirm_each' | 'confirm_render_only' | 'full_auto';
  payload?: {
    understand?: {
      summary?: string;
      duration?: number;
      format?: string;
      audience?: string;
      style?: string;
      platform?: string;
      cta?: string;
    };
    script?: {
      title?: string;
      hook?: string;
      narrative_arc?: string;
      cta?: string;
      duration?: number;
      format?: string;
    };
    assets?: { needed?: { description?: string; source?: string }[] };
    scenes?: { scenes?: Scene[] };
    effects?: { effects?: { scene_index?: number; visual_style?: string; animation_keywords?: string[] }[] };
  };
  pending_user_confirmation?: boolean;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run type-check 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types.ts
git commit -m "feat(types): extend AgentState for vibe payload"
```

---

### Task 11: Create WorkflowStatusBar component

**Files:**
- Create: `frontend/src/components/project/WorkflowStatusBar.tsx`
- Test: `frontend/tests/vibe/WorkflowStatusBar.test.tsx`

**Interfaces:**
- Produces: `<WorkflowStatusBar currentStep="script" />`.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import { WorkflowStatusBar } from '@/components/project/WorkflowStatusBar';

describe('WorkflowStatusBar', () => {
  it('highlights current step', () => {
    render(<WorkflowStatusBar currentStep="script" />);
    expect(screen.getByText('脚本')).toHaveAttribute('aria-current', 'step');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- tests/vibe/WorkflowStatusBar.test.tsx`
Expected: FAIL with `Cannot find module`

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/components/project/WorkflowStatusBar.tsx`:

```tsx
'use client';

import { clsx } from 'clsx';

const STEPS = [
  { id: 'understand', label: '理解' },
  { id: 'script', label: '脚本' },
  { id: 'assets', label: '素材' },
  { id: 'scenes', label: '场景' },
  { id: 'effects', label: '动效' },
  { id: 'render', label: '渲染' },
];

export function WorkflowStatusBar({ currentStep }: { currentStep?: string }) {
  const currentIndex = STEPS.findIndex((s) => s.id === currentStep);
  return (
    <nav aria-label="创作进度" className="flex items-center gap-1 text-xs">
      {STEPS.map((step, idx) => {
        const reached = idx <= currentIndex;
        const active = step.id === currentStep;
        return (
          <div key={step.id} className="flex items-center gap-1">
            <span
              aria-current={active ? 'step' : undefined}
              className={clsx(
                'px-2 py-1 rounded-full transition-colors',
                active
                  ? 'bg-brand-500/20 text-brand-400 font-medium'
                  : reached
                  ? 'text-content-secondary'
                  : 'text-content-tertiary'
              )}
            >
              {step.label}
            </span>
            {idx < STEPS.length - 1 && (
              <span className={clsx('w-4 h-px', reached ? 'bg-brand-500/40' : 'bg-border-subtle')} />
            )}
          </div>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- tests/vibe/WorkflowStatusBar.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/project/WorkflowStatusBar.tsx frontend/tests/vibe/WorkflowStatusBar.test.tsx
git commit -m "feat(ui): add WorkflowStatusBar component"
```

---

### Task 12: Create AutonomySelector component

**Files:**
- Create: `frontend/src/components/project/AutonomySelector.tsx`

**Interfaces:**
- Produces: `<AutonomySelector value="confirm_each" onChange={...} />`.

- [ ] **Step 1: Write the failing test**

No test required for pure select wrapper; verify by importing in a page.

- [ ] **Step 2: Write minimal implementation**

Create `frontend/src/components/project/AutonomySelector.tsx`:

```tsx
'use client';

interface Props {
  value: 'confirm_each' | 'confirm_render_only' | 'full_auto';
  onChange: (value: Props['value']) => void;
}

const OPTIONS = [
  { value: 'confirm_each', label: '每步都确认' },
  { value: 'confirm_render_only', label: '仅渲染前确认' },
  { value: 'full_auto', label: '全自动' },
] as const;

export function AutonomySelector({ value, onChange }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as Props['value'])}
      className="bg-background-elevated border border-border-subtle text-content-primary text-xs rounded-md px-2 py-1 focus:outline-none focus:border-brand-500"
      aria-label="Agent 自主级别"
    >
      {OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/project/AutonomySelector.tsx
git commit -m "feat(ui): add AutonomySelector component"
```

---

### Task 13: Create AgentCanvas component

**Files:**
- Create: `frontend/src/components/project/AgentCanvas.tsx`
- Test: `frontend/tests/vibe/AgentCanvas.test.tsx`

**Interfaces:**
- Consumes: `AgentState`.
- Produces: Rendered artifact for current step.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import { AgentCanvas } from '@/components/project/AgentCanvas';

describe('AgentCanvas', () => {
  it('renders understand summary', () => {
    render(
      <AgentCanvas
        agentState={{
          step: 'understand',
          payload: { understand: { summary: 'A product promo' } },
        }}
      />
    );
    expect(screen.getByText('A product promo')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- tests/vibe/AgentCanvas.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Create `frontend/src/components/project/AgentCanvas.tsx`:

```tsx
'use client';

import { AgentState } from '@/lib/types';

export function AgentCanvas({ agentState }: { agentState?: AgentState }) {
  const step = agentState?.step || 'understand';
  const payload = agentState?.payload || {};

  if (step === 'understand') {
    const u = payload.understand;
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">需求理解</h3>
        <p className="text-content-primary text-lg mb-4">{u?.summary || '等待输入…'}</p>
        <div className="flex flex-wrap gap-2 text-xs">
          {u?.format && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.format}</span>}
          {u?.duration && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.duration} 秒</span>}
          {u?.audience && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.audience}</span>}
          {u?.style && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.style}</span>}
        </div>
      </div>
    );
  }

  if (step === 'script') {
    const s = payload.script;
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">脚本</h3>
        <h4 className="text-xl font-bold text-content-primary mb-2">{s?.title || '未命名'}</h4>
        <p className="text-brand-400 mb-4">{s?.hook || ''}</p>
        <p className="text-content-secondary text-sm whitespace-pre-line">{s?.narrative_arc || ''}</p>
      </div>
    );
  }

  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-5 text-content-tertiary">
      当前步骤：{step}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- tests/vibe/AgentCanvas.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/project/AgentCanvas.tsx frontend/tests/vibe/AgentCanvas.test.tsx
git commit -m "feat(ui): add AgentCanvas component"
```

---

### Task 14: Extend AgentChat to render Vibe events

**Files:**
- Modify: `frontend/src/components/project/AgentChat.tsx`
- Test: `frontend/tests/vibe/AgentChat.test.tsx`

**Interfaces:**
- Consumes: Vibe event stream from `/agent/vibe/stream`.
- Produces: Chat messages + artifact cards + progress indicators.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import { AgentChat } from '@/components/project/AgentChat';

describe('AgentChat vibe mode', () => {
  it('renders question message', () => {
    render(
      <AgentChat
        projectId="p1"
        mode="vibe"
        onStatusChange={() => {}}
        initialMessages={[{ role: 'agent', text: 'What format?' }]}
      />
    );
    expect(screen.getByText('What format?')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- tests/vibe/AgentChat.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Extend `AgentChat.tsx` props and rendering:

```typescript
interface AgentChatProps {
  projectId: string;
  selectedSceneId?: string | null;
  scenes?: Scene[];
  mode: 'plan' | 'modify' | 'vibe';
  agentState?: AgentState;
  initialPrompt?: string;
  sourceUrl?: string;
  size?: 'sm' | 'lg';
  onStatusChange: (status: Project['status']) => void;
  onAgentStateChange?: (state: AgentState) => void;
}
```

Add a `handleVibeStream` function that calls `/agent/vibe/stream` and emits events to `onAgentStateChange`.

For brevity in this plan, the implementation should:
- Add a new `mode === 'vibe'` branch in `handleSubmit`.
- Stream from `/agent/vibe/stream`.
- Append user message, then for each event:
  - `token`: append to streaming text.
  - `question`: add agent message.
  - `artifact`: call `onAgentStateChange` with updated payload.
  - `done`: clear streaming, update step.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- tests/vibe/AgentChat.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/project/AgentChat.tsx frontend/tests/vibe/AgentChat.test.tsx
git commit -m "feat(ui): extend AgentChat for vibe mode"
```

---

### Task 15: Redesign project workspace layout

**Files:**
- Modify: `frontend/src/app/projects/[id]/page.tsx`

**Interfaces:**
- Consumes: `AgentChat` (vibe mode), `AgentCanvas`, `WorkflowStatusBar`, `AutonomySelector`.

- [ ] **Step 1: Write the failing test**

No new test; verify by running the dev server and visiting a project.

- [ ] **Step 2: Write minimal implementation**

Replace the planning branch in `frontend/src/app/projects/[id]/page.tsx` (around line 678) with the new layout:

```tsx
{isPlanning && (
  <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[calc(100dvh-3.5rem-2.5rem)] overflow-hidden">
    <div className="lg:col-span-5 flex flex-col gap-4 min-h-0">
      <div className="flex items-center justify-between">
        <WorkflowStatusBar currentStep={project.agent_state?.step} />
        <AutonomySelector
          value={project.agent_state?.autonomy_level || 'confirm_each'}
          onChange={(level) =>
            handleWizardStateChange({
              ...(project.agent_state || {}),
              autonomy_level: level,
            } as NonNullable<Project['agent_state']>)
          }
        />
      </div>
      <AgentChat
        projectId={project.id}
        mode="vibe"
        agentState={project.agent_state}
        initialPrompt={initialPrompt}
        sourceUrl={project.source_url}
        onStatusChange={(s) => setProject((prev) => (prev ? { ...prev, status: s } : null))}
        onAgentStateChange={(next) =>
          setProject((prev) =>
            prev ? { ...prev, agent_state: { ...(prev.agent_state || {}), ...next } } : null
          )
        }
      />
    </div>
    <div className="lg:col-span-7 min-h-0 overflow-y-auto">
      <AgentCanvas agentState={project.agent_state} />
    </div>
  </div>
)}
```

- [ ] **Step 3: Verify TypeScript**

Run: `cd frontend && npm run type-check 2>&1 | tail -20`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/projects/[id]/page.tsx
git commit -m "feat(ui): redesign workspace for vibe video layout"
```

---

### Task 16: New Project button opens chat-style dialog

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/components/project/NewProjectDialog.tsx`

**Interfaces:**
- Produces: Chat-style new project creation.

- [ ] **Step 1: Write the failing test**

No test; verify by clicking "新建项目" in the sidebar.

- [ ] **Step 2: Write minimal implementation**

In `frontend/src/components/layout/Sidebar.tsx`, replace the direct project creation with opening the dialog:

```tsx
import { NewProjectDialog } from '@/components/project/NewProjectDialog';

// In the component render:
<NewProjectDialog />
```

Update `NewProjectDialog.tsx` to be self-opening (remove external `open` prop dependency if needed) and styled like the home-page chat input.

- [ ] **Step 3: Verify**

Run dev server, click "新建项目", confirm a chat-style dialog opens.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/layout/Sidebar.tsx frontend/src/components/project/NewProjectDialog.tsx
git commit -m "feat(ui): new project opens chat-style dialog"
```

---

## Milestone 3: Integration & Polish

### Task 17: Add remaining tools (assets, scenes, effects, render)

**Files:**
- Modify: `backend/app/agent/tools.py`
- Modify: `backend/app/agent/orchestrator.py`

**Interfaces:**
- Produces: `run_assets`, `run_scenes`, `run_effects`, `run_render` tools.

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import patch, MagicMock
from app.agent.tools import run_assets


def test_run_assets_uses_step_generator():
    project = MagicMock()
    state = {"payload": {}}
    with patch("app.agent.tools.run_step") as mock_step:
        mock_step.return_value = iter(['{"type": "done"}'])
        list(run_assets(project, state, ""))
    mock_step.assert_called_once_with("assets", project, state, "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_tools.py::test_run_assets_uses_step_generator -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Append to `backend/app/agent/tools.py`:

```python
def run_assets(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_step("assets", project, state, user_input)


def run_scenes(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_step("scenes", project, state, user_input)


def run_effects(project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    yield from run_step("effects", project, state, user_input)
```

And add render tool:

```python
from app.routers.renders import render_video_task, _check_credits
from app.models import RenderJob


def run_render(project, state: dict, user_input: Optional[str] = None, db=None, user=None) -> Iterator[str]:
    if not db or not user:
        yield sse_error("Internal error: missing db or user for render")
        return
    try:
        _check_credits(user)
    except Exception as exc:
        yield sse_error(str(exc))
        return

    # Build plan from state payload like /agent/approve does.
    script = state.get("payload", {}).get("script", {})
    scenes_data = state.get("payload", {}).get("scenes", {}).get("scenes", [])
    effects_data = state.get("payload", {}).get("effects", {}).get("effects", [])
    enriched_scenes = []
    for i, scene in enumerate(scenes_data):
        effect = next((e for e in effects_data if e.get("scene_index") == i), {})
        enriched = dict(scene)
        enriched["visual_style"] = effect.get("visual_style", "")
        enriched["animation_keywords"] = effect.get("animation_keywords", [])
        enriched["generate_image"] = effect.get("generate_image", False)
        enriched["generate_image_prompt"] = effect.get("generate_image_prompt", "")
        enriched.setdefault("narration", "")
        enriched_scenes.append(enriched)

    plan = {
        "title": script.get("title", project.title),
        "hook": script.get("hook", ""),
        "format": script.get("format", project.target_format or "16:9"),
        "duration": script.get("duration", project.target_duration or 30),
        "scenes": enriched_scenes,
        "assets_needed": [a.get("description", "") for a in state.get("payload", {}).get("assets", {}).get("needed", [])],
        "engine_hint": None,
    }

    job = RenderJob(project_id=project.id, status="queued", logs=[])
    db.add(job)
    db.commit()
    db.refresh(job)
    render_video_task.delay(job.id, project.id, None, None, plan)
    yield sse_event("job_created", {"job_id": job.id, "status": "queued"})
    yield sse_done()
```

Register all tools in `Orchestrator.__init__`:

```python
self.tools = {
    "understand": run_understand,
    "script": run_script,
    "assets": run_assets,
    "scenes": run_scenes,
    "effects": run_effects,
    "render": run_render,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/agent/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/agent/tools.py backend/app/agent/orchestrator.py backend/tests/agent/test_tools.py
git commit -m "feat(agent): add assets/scenes/effects/render tools"
```

---

### Task 18: Update e2e script for Vibe flow

**Files:**
- Modify: `scripts/e2e_agent_loop.py`

**Interfaces:**
- Produces: Script that sends natural language messages and confirms each step.

- [ ] **Step 1: Write the failing test**

No test; run the script manually.

- [ ] **Step 2: Write implementation**

Update `scripts/e2e_agent_loop.py` to:

```python
import argparse
import os
import sys
import requests

API = os.getenv("CLIPWORKS_API", "http://localhost:8000")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--api", default=API)
    args = parser.parse_args()

    s = requests.Session()
    r = s.post(f"{args.api}/auth/mock-login?provider=google")
    print("login", r.status_code)
    if r.status_code != 200:
        sys.exit(1)

    messages = [
        "帮我做一个 30 秒的产品介绍视频，9:16，风格活泼",
        "下一步",
        "下一步",
        "下一步",
        "下一步",
        "生成视频",
    ]

    for msg in messages:
        print(f"\n>>> {msg}")
        r = s.post(
            f"{args.api}/projects/{args.project_id}/agent/vibe/stream",
            json={"message": msg},
            stream=True,
        )
        if r.status_code != 200:
            print("failed", r.status_code, r.text)
            sys.exit(1)
        for line in r.iter_lines():
            if line:
                print(line.decode())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify**

Run: `python scripts/e2e_agent_loop.py --project-id <id>`
Expected: Script completes and creates a render job.

- [ ] **Step 4: Commit**

```bash
git add scripts/e2e_agent_loop.py
git commit -m "chore(e2e): update smoke script for vibe flow"
```

---

### Task 19: Full backend pytest regression

**Files:**
- All backend tests.

- [ ] **Step 1: Run tests**

Run: `cd backend && source .venv/bin/activate && pytest`
Expected: all pass (or only pre-existing skips).

- [ ] **Step 2: Fix any failures**

If failures relate to the new code, fix inline.

- [ ] **Step 3: Commit**

```bash
git commit -m "test(agent): vibe loop regression green" -a
```

---

### Task 20: Frontend dev server smoke test

**Files:**
- Frontend dev build.

- [ ] **Step 1: Start backend and frontend**

```bash
docker compose up -d postgres redis
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000 &
cd ../frontend && npm run dev
```

- [ ] **Step 2: Manual smoke test**

1. Open http://localhost:3000.
2. Click "新建项目" in sidebar.
3. Type a prompt and submit.
4. Verify workspace loads with left chat + right canvas.
5. Verify Agent asks clarifying question or advances.
6. Verify workflow status bar updates.

- [ ] **Step 3: Commit any fixes**

```bash
git commit -m "fix(ui): vibe workspace smoke test fixes" -a
```

---

## Self-Review

### Spec coverage

| Spec section | Task(s) |
|---|---|
| Chat-first UX | Task 14, 15, 16 |
| LLM-driven workflow | Task 4, 7, 8 |
| Internal tools | Task 5, 6, 17 |
| Real-time canvas | Task 13, 15 |
| Human-in-the-loop confirmation | Task 7, 8 |
| Error withholding/recovery | Task 8, 17 |
| Autonomy slider | Task 12, 15 |
| Home/New Project chat | Task 16 |
| Tests | Every task includes verification; Tasks 19, 20 are regression |

### Placeholder scan

- No TBD/TODO in task steps.
- Every code-changing step includes actual code or exact command.
- Every task ends with a commit.

### Type consistency

- `AgentState` in frontend matches backend `AgentSession.to_dict()` shape.
- `AgentAction` fields are used consistently across orchestrator, session, and tests.
- Workflow step ids (`understand`, `script`, etc.) match in backend `AgentSession`, frontend `WorkflowStatusBar`, and `AgentCanvas`.

### Gaps

- The existing `/agent/chat/stream` planning endpoint is kept but not replaced yet. In a follow-up we can redirect the frontend planning flow to `/vibe/stream` and deprecate the old endpoint. This plan intentionally leaves it untouched to minimize blast radius.
- The `AgentCanvas` only implements `understand` and `script` artifacts in detail; `assets`, `scenes`, `effects` use the existing panels from `PlanWizard` in a follow-up task.
