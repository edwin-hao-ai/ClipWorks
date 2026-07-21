from unittest.mock import MagicMock

from app.agent.orchestrator import parse_action_json, AgentAction, Orchestrator
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


def test_orchestrator_ask_action():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(
        action="ask",
        response_to_user="Need more info",
        confirmation_message="Please confirm",
    )
    events = list(orch.run_action(session, project, action))
    assert session.pending_user_confirmation is True
    assert any('"type": "token"' in e and '"text": "Need more info"' in e for e in events)
    assert any('"type": "question"' in e and '"text": "Please confirm"' in e for e in events)


def test_orchestrator_advance_action():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(action="advance", target_step="script", response_to_user="Moving on")
    events = list(orch.run_action(session, project, action))
    assert session.step == "script"
    assert session.pending_user_confirmation is True
    assert any('"type": "token"' in e and '"text": "Moving on"' in e for e in events)


def test_orchestrator_advance_requires_target_step():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(action="advance", response_to_user="No target")
    events = list(orch.run_action(session, project, action))
    assert '"type": "error"' in "".join(events)
    assert "target_step" in "".join(events)


def test_orchestrator_revise_uses_current_step():
    session = AgentSession("p1")
    session.set_step("script")
    project = MagicMock()
    orch = Orchestrator()
    with orch._tool_mock("script", iter(['{"type": "done"}'])) as mock_tool:
        action = AgentAction(action="revise", response_to_user="Revising")
        list(orch.run_action(session, project, action, "make it shorter"))
    mock_tool.assert_called_once()
    call_args = mock_tool.call_args
    assert call_args.args[0] is project
    assert call_args.args[2] == "make it shorter"


def test_orchestrator_reset_action():
    session = AgentSession("p1")
    session.set_step("script")
    session.set_payload("script", {"title": "T"})
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(action="reset", response_to_user="Restarting")
    events = list(orch.run_action(session, project, action))
    assert session.step == "understand"
    assert session.payload == {}
    assert session.pending_user_confirmation is True
    assert any('"type": "token"' in e and '"text": "Restarting"' in e for e in events)


def test_orchestrator_reset_uses_default_message():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(action="reset")
    events = list(orch.run_action(session, project, action))
    assert any('"type": "token"' in e and "重新开始" in e for e in events)


def test_orchestrator_unknown_action():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(action="ask")
    action.action = "fly"
    events = list(orch.run_action(session, project, action))
    assert '"type": "error"' in "".join(events)
    assert "Unknown action fly" in "".join(events)


def test_orchestrator_render_action_passes_db_and_user():
    session = AgentSession("p1")
    project = MagicMock()
    db = MagicMock()
    user = MagicMock()
    orch = Orchestrator()
    with orch._tool_mock("render", iter(['{"type": "done"}'])) as mock_tool:
        action = AgentAction(action="render", response_to_user="Rendering")
        list(orch.run_action(session, project, action, "render it", db=db, user=user))
    mock_tool.assert_called_once()
    call_args = mock_tool.call_args
    assert call_args.args[0] is project
    assert call_args.args[1] == session.to_dict()
    assert call_args.args[2] == "render it"
    assert call_args.args[3] is db
    assert call_args.args[4] is user


def test_orchestrator_render_action_missing_db_or_user():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(action="render", response_to_user="Rendering")
    events = list(orch.run_action(session, project, action, "render it"))
    assert '"type": "error"' in "".join(events)
    assert "missing db or user" in "".join(events)


def test_orchestrator_run_tool_missing_tool():
    session = AgentSession("p1")
    project = MagicMock()
    orch = Orchestrator()
    action = AgentAction(action="run_tool", target_step="nonexistent")
    events = list(orch.run_action(session, project, action))
    assert '"type": "error"' in "".join(events)
    assert "No tool for step nonexistent" in "".join(events)


def test_orchestrator_run_tool_defaults_to_session_step():
    session = AgentSession("p1")
    session.set_step("script")
    project = MagicMock()
    orch = Orchestrator()
    with orch._tool_mock("script", iter(['{"type": "done"}'])) as mock_tool:
        action = AgentAction(action="run_tool", response_to_user="OK")
        list(orch.run_action(session, project, action, "hello"))
    mock_tool.assert_called_once()


def test_parse_valid_action_json():
    text = """
    {
      "thinking": "advance",
      "action": "advance",
      "target_step": "script",
      "response_to_user": "OK，去写脚本。",
      "payload": {"script": {"title": "T"}},
      "requires_confirmation": false,
      "confirmation_message": ""
    }
    """
    action = parse_action_json(text)
    assert action.action == "advance"
    assert action.target_step == "script"
    assert action.response_to_user == "OK，去写脚本。"


def test_parse_fenced_json_block():
    text = """
Some explanation before.

```json
{
  "action": "run_tool",
  "target_step": "search",
  "response_to_user": "Searching...",
  "payload": {"query": "cat videos"},
  "requires_confirmation": true,
  "confirmation_message": "Run search?"
}
```

After text.
"""
    action = parse_action_json(text)
    assert action.action == "run_tool"
    assert action.target_step == "search"
    assert action.payload == {"query": "cat videos"}
    assert action.requires_confirmation is True
    assert action.confirmation_message == "Run search?"


def test_parse_generic_fenced_block():
    text = """
```
{
  "action": "ask",
  "response_to_user": "What is the budget?"
}
```
"""
    action = parse_action_json(text)
    assert action.action == "ask"
    assert action.response_to_user == "What is the budget?"
    assert action.payload == {}
    assert action.requires_confirmation is True


def test_parse_bare_json():
    text = '{"action": "render", "target_step": "video", "payload": {}}'
    action = parse_action_json(text)
    assert action.action == "render"
    assert action.target_step == "video"


def test_parse_malformed_json_returns_none():
    assert parse_action_json("not json") is None
    assert parse_action_json("{ broken") is None
    assert parse_action_json("<xml></xml>") is None


def test_parse_invalid_action_returns_none():
    text = '{"action": "fly", "target_step": "moon"}'
    assert parse_action_json(text) is None


def test_agent_action_defaults():
    action = AgentAction(action="ask")
    assert action.target_step is None
    assert action.response_to_user == ""
    assert action.payload == {}
    assert action.requires_confirmation is True
    assert action.confirmation_message == ""


def test_decide_action_parses_llm_json():
    orch = Orchestrator()
    orch.client.chat_completion_stream = lambda *args, **kwargs: iter(
        ['```json\n{"action": "ask", "response_to_user": "What?", "confirmation_message": "What?"}\n```']
    )
    action = orch.decide_action("ctx")
    assert action is not None
    assert action.action == "ask"
    assert action.response_to_user == "What?"
    assert action.confirmation_message == "What?"


def test_decide_action_returns_fallback_on_llm_error():
    orch = Orchestrator()

    def _raise(*args, **kwargs):
        raise Exception("boom")

    orch.client.chat_completion_stream = _raise
    action = orch.decide_action("ctx")
    assert action is not None
    assert action.action == "ask"
    assert "我没听清" in action.response_to_user


def test_decide_action_returns_none_on_unparseable_output():
    orch = Orchestrator()
    orch.client.chat_completion_stream = lambda *args, **kwargs: iter(["not json"])
    assert orch.decide_action("ctx") is None
