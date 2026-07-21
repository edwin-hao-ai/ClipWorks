from app.agent.orchestrator import parse_action_json, AgentAction


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
