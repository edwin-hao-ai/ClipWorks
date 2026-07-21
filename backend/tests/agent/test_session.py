import json

from app.agent.session import (
    AgentSession,
    AutonomyLevel,
    AgentEvent,
    format_sse,
    sse_event,
)


def test_session_starts_in_understand_step():
    session = AgentSession(project_id="p1")
    assert session.step == "understand"
    assert session.autonomy_level == AutonomyLevel.CONFIRM_EACH
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
    assert d["autonomy_level"] == AutonomyLevel.CONFIRM_EACH
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


def test_format_sse():
    data = {"event": "step", "step": "script"}
    sse = format_sse(data)
    assert sse.startswith("data: ")
    assert sse.endswith("\n\n")
    assert json.loads(sse.replace("data: ", "").strip()) == data


def test_sse_event_helper():
    event = sse_event("step", step="assets", payload={"x": 1}, message="done")
    assert event["event"] == "step"
    assert event["step"] == "assets"
    assert event["payload"] == {"x": 1}
    assert event["message"] == "done"
