import json
import pytest
from app.agent.steps.script_step import _extract_script_json
from app.agent.steps import run_step, previous_step, STEPS, ORDER


class FakeProject:
    title = "Test"
    source_url = ""
    target_format = "16:9"
    target_duration = 30


def test_extract_script_json_from_markdown_block():
    text = 'Some words\n```json\n{"title": "T", "hook": "H", "roles": [], "narrative_arc": "A", "cta": "C", "duration": 30, "format": "16:9"}\n```'
    result = _extract_script_json(text)
    assert result["title"] == "T"
    assert result["format"] == "16:9"


def test_extract_script_json_invalid_returns_none():
    assert _extract_script_json("not json") is None


def test_previous_step_returns_previous_name():
    assert previous_step("assets") == "script"
    assert previous_step("script") is None
    assert previous_step("unknown") is None


def test_run_step_dispatches_script_step(monkeypatch):
    called = {}
    project = FakeProject()

    def fake_run(p, s, user_input):
        called["args"] = (p, s, user_input)
        yield json.dumps({"type": "done"})

    monkeypatch.setitem(STEPS, "script", fake_run)
    state = {}
    list(run_step("script", project, state, "hello"))
    assert called["args"] == (project, state, "hello")


def test_run_step_unknown_raises():
    with pytest.raises(ValueError, match="Unknown step: scenes"):
        list(run_step("scenes", FakeProject(), {}))
