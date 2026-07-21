import json
from unittest.mock import MagicMock, patch

from app.agent.orchestrator import AgentAction, Orchestrator
from app.agent.session import (
    AgentSession,
    AutonomyLevel,
    AgentEvent,
    sse_text,
    sse_event,
    sse_done,
    sse_error,
)


def test_session_starts_in_understand_step():
    session = AgentSession(project_id="p1")
    assert session.step == "understand"
    # 默认 full_auto：确认模式目前无 UI 入口，默认 confirm_each 会死锁。
    assert session.autonomy_level == AutonomyLevel.FULL_AUTO
    assert session.payload == {}
    assert session.messages == []
    assert session.pending_user_confirmation is False


def test_session_loads_state():
    state = {
        "step": "script",
        "payload": {"foo": "bar"},
        "messages": [{"role": "user", "content": "hello"}],
        "autonomy_level": "full_auto",
        "pending_user_confirmation": True,
    }
    session = AgentSession(project_id="p1", state=state)
    assert session.step == "script"
    assert session.payload == {"foo": "bar"}
    assert session.messages == [{"role": "user", "content": "hello"}]
    assert session.autonomy_level == AutonomyLevel.FULL_AUTO
    assert session.pending_user_confirmation is True


def test_session_to_dict_round_trip():
    session = AgentSession(project_id="p1")
    session.set_step("assets")
    session.set_payload("key", "value")
    session.append_message("user", "hi")
    session.mark_waiting(True)

    d = session.to_dict()
    assert d["step"] == "assets"
    assert d["payload"] == {"key": "value"}
    assert d["messages"] == [{"role": "user", "content": "hi"}]
    assert d["autonomy_level"] == AutonomyLevel.FULL_AUTO
    assert d["pending_user_confirmation"] is True


def test_session_setters():
    session = AgentSession(project_id="p1")
    session.set_step("render")
    assert session.step == "render"

    session.set_payload("script", {"scenes": []})
    assert session.payload["script"] == {"scenes": []}

    session.append_message("assistant", "ok")
    assert session.messages == [{"role": "assistant", "content": "ok"}]

    session.mark_waiting(True)
    assert session.pending_user_confirmation is True

    session.mark_waiting(False)
    assert session.pending_user_confirmation is False


def test_autonomy_level_enum_values():
    assert AutonomyLevel.CONFIRM_EACH == "confirm_each"
    assert AutonomyLevel.CONFIRM_RENDER_ONLY == "confirm_render_only"
    assert AutonomyLevel.FULL_AUTO == "full_auto"


def test_agent_event_typed_dict():
    event: AgentEvent = {
        "event": "step",
        "step": "understand",
        "payload": {"project_id": "p1"},
        "message": "started",
    }
    assert event["event"] == "step"


def test_sse_helpers_produce_json_lines():
    assert sse_text("hello") == 'data: {"type": "token", "text": "hello"}\n\n'
    assert sse_event("artifact", {"kind": "script"}) == 'data: {"type": "artifact", "kind": "script"}\n\n'
    assert json.loads(sse_done().replace("data: ", "").strip()) == {"type": "done"}
    assert json.loads(sse_error("oops").replace("data: ", "").strip()) == {
        "type": "error",
        "message": "oops",
    }


def test_run_loop_asks_when_action_is_ask():
    session = AgentSession("p1")
    project = MagicMock()
    project.title = "T"
    project.source_url = None
    project.target_format = "16:9"
    project.target_duration = 30

    orch = Orchestrator()
    orch.decide_action = lambda context: AgentAction(
        action="ask",
        response_to_user="What format?",
        confirmation_message="What format?",
    )

    events = list(session.run(project, "hi", orch))
    assert any('"type": "question"' in e for e in events)
    assert session.pending_user_confirmation is True
    assert session.messages[-1] == {"role": "assistant", "content": "What format?"}


def test_run_loop_fallback_when_decide_returns_none():
    session = AgentSession("p1")
    project = MagicMock()
    project.title = "T"
    project.source_url = None
    project.target_format = "16:9"
    project.target_duration = 30

    orch = Orchestrator()
    orch.decide_action = lambda context: None

    events = list(session.run(project, "hi", orch))
    assert any("我没理解你的意思" in e for e in events)
    assert session.pending_user_confirmation is True


def test_run_loop_runs_tool_and_appends_assistant_message():
    session = AgentSession("p1")
    project = MagicMock()
    project.title = "T"
    project.source_url = None
    project.target_format = "16:9"
    project.target_duration = 30

    orch = Orchestrator()
    orch.decide_action = lambda context: AgentAction(
        action="run_tool",
        target_step="understand",
        response_to_user="OK",
    )

    mock_tool = MagicMock(return_value=iter([sse_done()]))
    with patch.dict(orch.tools, {"understand": mock_tool}):
        events = list(session.run(project, "make a video", orch))

    assert any('"type": "done"' in e for e in events)
    assert session.messages[-1] == {"role": "assistant", "content": "OK"}


def test_build_architect_context_includes_project_and_payload():
    session = AgentSession("p1")
    session.set_payload("script", {"title": "Hello"})
    project = MagicMock()
    project.title = "T"
    project.source_url = "http://example.com"
    project.target_format = "9:16"
    project.target_duration = 15

    context = session._build_architect_context(project, "hi")
    assert "Current step: understand" in context
    assert "Project title: T" in context
    assert "Target format: 9:16" in context
    assert "Target duration: 15s" in context
    assert "Source URL: http://example.com" in context
    assert "Current payload:" in context
    assert '"title": "Hello"' in context
    assert "User message: hi" in context


def _make_project():
    project = MagicMock()
    project.title = "T"
    project.source_url = None
    project.target_format = "16:9"
    project.target_duration = 30
    return project


def test_confirm_each_ignores_llm_requires_confirmation_flag_for_advance():
    """A misbehaving LLM cannot bypass confirmation by setting requires_confirmation=False."""
    session = AgentSession("p1", state={"autonomy_level": "confirm_each"})
    project = _make_project()

    orch = Orchestrator()
    orch.decide_action = lambda context: AgentAction(
        action="advance",
        target_step="script",
        response_to_user="Moving on",
        requires_confirmation=False,
    )

    events = list(session.run(project, "hi", orch))
    assert any('"type": "question"' in e for e in events)
    assert session.step == "understand"
    assert session.pending_user_confirmation is True


def test_confirm_each_ignores_llm_requires_confirmation_flag_for_render():
    session = AgentSession("p1", state={"autonomy_level": "confirm_each"})
    project = _make_project()

    orch = Orchestrator()
    orch.decide_action = lambda context: AgentAction(
        action="render",
        response_to_user="Rendering",
        requires_confirmation=False,
    )

    events = list(session.run(project, "hi", orch))
    assert any('"type": "question"' in e for e in events)
    assert session.step == "understand"
    assert session.pending_user_confirmation is True


def test_confirm_render_only_asks_render_even_when_llm_flag_is_false():
    session = AgentSession("p1", state={"autonomy_level": "confirm_render_only"})
    project = _make_project()

    orch = Orchestrator()
    orch.decide_action = lambda context: AgentAction(
        action="render",
        response_to_user="Rendering",
        requires_confirmation=False,
    )

    events = list(session.run(project, "hi", orch))
    assert any('"type": "question"' in e for e in events)
    assert session.step == "understand"
    assert session.pending_user_confirmation is True


def test_full_auto_advance_runs_without_confirmation():
    session = AgentSession("p1", state={"autonomy_level": "full_auto"})
    project = _make_project()

    orch = Orchestrator()
    orch.decide_action = lambda context: AgentAction(
        action="advance",
        target_step="script",
        response_to_user="Moving on",
        requires_confirmation=True,
    )

    events = list(session.run(project, "hi", orch))
    assert not any('"type": "question"' in e for e in events)
    assert session.step == "script"
    assert session.messages[-1] == {"role": "assistant", "content": "Moving on"}
