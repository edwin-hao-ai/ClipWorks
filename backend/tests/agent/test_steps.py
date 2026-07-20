import json
import pytest
from app.agent.llm import LLMUnavailableError
from app.agent.steps.script_step import _extract_script_json, run as run_script, _build_context as build_script_context
from app.agent.steps.assets_step import run as run_assets
from app.agent.steps.scenes_step import run as run_scenes
from app.agent.steps.effects_step import run as run_effects
from app.agent.steps import run_step, previous_step, STEPS, ORDER
from app.agent.steps._fallbacks import fallback_script, fallback_assets, fallback_scenes, fallback_effects


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


def test_extract_assets_json_non_dict_returns_none():
    assert _extract_assets_json('```json\n[1, 2, 3]\n```') is None
    assert _extract_assets_json('```json\n"just a string"\n```') is None


def test_extract_scenes_json_non_dict_returns_none():
    assert _extract_scenes_json('```json\n[{"start": 0}]\n```') is None
    assert _extract_scenes_json('```json\n"scenes"\n```') is None


def test_extract_effects_json_non_dict_returns_none():
    assert _extract_effects_json('```json\n[{"scene_index": 0}]\n```') is None
    assert _extract_effects_json('```json\n"effects"\n```') is None


def test_build_script_context_includes_project_meta():
    project = FakeProject()
    state = {}
    ctx = build_script_context(project, state, "make a promo")
    assert f"Project title: {project.title}" in ctx
    assert "Target format: 16:9" in ctx
    assert "Target duration: 30s" in ctx
    assert "User brief / feedback: make a promo" in ctx


def test_script_step_run_unparseable_output_uses_fallback(monkeypatch):
    project = FakeProject()
    state = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion_stream(self, *args, **kwargs):
            yield "not valid json"

    monkeypatch.setattr("app.agent.steps.script_step.KimiClient", FakeClient)
    events = [json.loads(e) for e in run_script(project, state, None)]

    assert any(e["type"] == "error" for e in events)
    assert events[-1]["type"] == "done"
    assert state["script"] is not None
    required = {"title", "hook", "roles", "narrative_arc", "cta", "duration", "format"}
    assert required.issubset(state["script"].keys())


def test_script_step_run_llm_unavailable_uses_fallback(monkeypatch):
    project = FakeProject()
    state = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion_stream(self, *args, **kwargs):
            raise LLMUnavailableError("no api key")
            yield ""

    monkeypatch.setattr("app.agent.steps.script_step.KimiClient", FakeClient)
    events = [json.loads(e) for e in run_script(project, state, None)]

    assert all(e["type"] in ("token", "done") for e in events)
    assert events[-1]["type"] == "done"
    assert "script" in state
    required = {"title", "hook", "roles", "narrative_arc", "cta", "duration", "format"}
    assert required.issubset(state["script"].keys())


def test_fallback_script_returns_required_schema():
    project = FakeProject()
    script = fallback_script(project)
    required = {"title", "hook", "roles", "narrative_arc", "cta", "duration", "format"}
    assert required.issubset(script.keys())
    assert script["duration"] == project.target_duration
    assert script["format"] == project.target_format
    assert isinstance(script["roles"], list)


def test_fallback_assets_uses_script_title():
    project = FakeProject()
    state = {"script": {"title": "My Script"}}
    assets = fallback_assets(project, state)
    assert "needed" in assets
    assert len(assets["needed"]) == 3
    assert assets["needed"][0]["query"] == "My Script"


def test_fallback_scenes_returns_normalized_scenes():
    project = FakeProject()
    state = {}
    scenes = fallback_scenes(project, state)
    assert "scenes" in scenes
    assert len(scenes["scenes"]) == 3
    for s in scenes["scenes"]:
        assert "visual_type" in s
        assert "shot" in s
        assert "transition" in s
        assert "lower_third" in s
        assert "required_assets" in s


def test_fallback_effects_derives_from_scenes():
    project = FakeProject()
    state = {"scenes": {"scenes": [{"visual": "科技感画面"}]}}
    effects = fallback_effects(project, state)
    assert "effects" in effects
    assert len(effects["effects"]) == 1
    assert effects["effects"][0]["scene_index"] == 0
    assert "淡入" in effects["effects"][0]["animation_keywords"]
    assert "粒子" in effects["effects"][0]["animation_keywords"]


def test_assets_step_run_unexpected_error_falls_back(monkeypatch):
    project = FakeProject()
    state = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion_stream(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr("app.agent.steps.assets_step.KimiClient", FakeClient)
    events = [json.loads(e) for e in run_assets(project, state, None)]

    assert any(e["type"] == "error" for e in events)
    assert events[-1]["type"] == "done"
    assert "assets" in state
    assert "needed" in state["assets"]


def test_scenes_step_run_llm_unavailable_uses_fallback(monkeypatch):
    project = FakeProject()
    state = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion_stream(self, *args, **kwargs):
            raise LLMUnavailableError("no api key")
            yield ""

    monkeypatch.setattr("app.agent.steps.scenes_step.KimiClient", FakeClient)
    events = [json.loads(e) for e in run_scenes(project, state, None)]

    assert all(e["type"] in ("token", "done") for e in events)
    assert events[-1]["type"] == "done"
    assert "scenes" in state
    assert "scenes" in state["scenes"]


def test_scenes_step_run_unparseable_output_uses_fallback(monkeypatch):
    project = FakeProject()
    state = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion_stream(self, *args, **kwargs):
            yield "not valid json"

    monkeypatch.setattr("app.agent.steps.scenes_step.KimiClient", FakeClient)
    events = [json.loads(e) for e in run_scenes(project, state, None)]

    assert any(e["type"] == "error" for e in events)
    assert events[-1]["type"] == "done"
    assert state["scenes"] is not None
    assert "scenes" in state["scenes"]


def test_effects_step_run_llm_unavailable_uses_fallback(monkeypatch):
    project = FakeProject()
    state = {"scenes": {"scenes": [{"visual": "科技感画面"}]}}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion_stream(self, *args, **kwargs):
            raise LLMUnavailableError("no api key")
            yield ""

    monkeypatch.setattr("app.agent.steps.effects_step.KimiClient", FakeClient)
    events = [json.loads(e) for e in run_effects(project, state, None)]

    assert all(e["type"] in ("token", "done") for e in events)
    assert events[-1]["type"] == "done"
    assert "effects" in state
    assert len(state["effects"]["effects"]) == 1


def test_effects_step_run_unparseable_output_uses_fallback(monkeypatch):
    project = FakeProject()
    state = {"scenes": {"scenes": [{"visual": "科技感画面"}]}}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def chat_completion_stream(self, *args, **kwargs):
            yield "not valid json"

    monkeypatch.setattr("app.agent.steps.effects_step.KimiClient", FakeClient)
    events = [json.loads(e) for e in run_effects(project, state, None)]

    assert any(e["type"] == "error" for e in events)
    assert events[-1]["type"] == "done"
    assert state["effects"] is not None
    assert len(state["effects"]["effects"]) == 1
