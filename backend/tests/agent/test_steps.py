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


def test_extract_script_json_non_dict_returns_none():
    assert _extract_script_json('```json\n[1, 2, 3]\n```') is None


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
    with pytest.raises(ValueError, match="Unknown step: unknown"):
        list(run_step("unknown", FakeProject(), {}))


from app.agent.steps.assets_step import _extract_assets_json
from app.agent.steps.scenes_step import _extract_scenes_json
from app.agent.steps.effects_step import _extract_effects_json


def test_extract_assets_json():
    text = '```json\n{"needed": [{"type": "image", "description": "D", "query": "Q", "count": 1}]}\n```'
    result = _extract_assets_json(text)
    assert result["needed"][0]["type"] == "image"


def test_extract_scenes_json():
    text = '```json\n{"scenes": [{"start": 0, "duration": 5, "description": "D", "visual": "V", "text": "T", "visual_type": "text", "shot": "S", "transition": "fade", "lower_third": "L", "required_assets": [0]}]}\n```'
    result = _extract_scenes_json(text)
    assert len(result["scenes"]) == 1
    assert result["scenes"][0]["transition"] == "fade"


def test_extract_effects_json():
    text = '```json\n{"effects": [{"scene_index": 0, "visual_style": "V", "animation_keywords": ["a"], "generate_image": true, "generate_image_prompt": "P"}]}\n```'
    result = _extract_effects_json(text)
    assert result["effects"][0]["scene_index"] == 0
