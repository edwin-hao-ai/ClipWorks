from unittest.mock import patch, MagicMock

from app.agent.llm import LLMUnavailableError
from app.agent.tools import run_assets, run_render, run_script, run_understand


def _project(**overrides):
    project = MagicMock()
    project.title = overrides.get("title", "Test")
    project.source_url = overrides.get("source_url", None)
    project.target_format = overrides.get("target_format", "16:9")
    project.target_duration = overrides.get("target_duration", 30)
    return project


def test_run_understand_sets_summary():
    project = _project()
    state = {"payload": {}, "messages": []}

    with patch("app.agent.tools.KimiClient") as MockClient:
        instance = MockClient.return_value
        instance.chat_completion_stream.return_value = iter(
            ['{"summary": "s", "duration": 30, "format": "16:9"}']
        )
        events = list(run_understand(project, state, "make a promo"))

    assert state["payload"]["understand"]["summary"] == "s"
    assert any('"type": "done"' in e for e in events)


def test_run_understand_extracts_json_from_code_fence():
    project = _project()
    state = {"payload": {}, "messages": []}

    with patch("app.agent.tools.KimiClient") as MockClient:
        instance = MockClient.return_value
        instance.chat_completion_stream.return_value = iter(
            ['```json\n{"summary": "code fence summary", "duration": 15, "format": "9:16"}\n```']
        )
        list(run_understand(project, state, "tiktok ad"))

    summary = state["payload"]["understand"]
    assert summary["summary"] == "code fence summary"
    assert summary["duration"] == 15
    assert summary["format"] == "9:16"


def test_run_understand_fallback_on_llm_unavailable():
    project = _project(title="Fallback Project", target_format="1:1", target_duration=20)
    state = {"payload": {}, "messages": []}

    with patch("app.agent.tools.KimiClient") as MockClient:
        instance = MockClient.return_value
        instance.chat_completion_stream.side_effect = LLMUnavailableError("no key")
        events = list(run_understand(project, state, "make a promo"))

    summary = state["payload"]["understand"]
    assert summary["summary"] == "make a promo"
    assert summary["duration"] == 20
    assert summary["format"] == "1:1"
    assert any("AI 暂不可用" in e for e in events)
    assert any('"type": "done"' in e for e in events)


def test_run_understand_fallback_on_unparseable_output():
    project = _project()
    state = {"payload": {}, "messages": []}

    with patch("app.agent.tools.KimiClient") as MockClient:
        instance = MockClient.return_value
        instance.chat_completion_stream.return_value = iter(["not json"])
        events = list(run_understand(project, state, "make a promo"))

    summary = state["payload"]["understand"]
    assert summary["summary"] == "make a promo"
    assert summary["duration"] == 30
    assert summary["format"] == "16:9"
    assert any('"type": "done"' in e for e in events)


def test_run_understand_uses_project_title_when_user_input_empty():
    project = _project(title="Project Title")
    state = {"payload": {}, "messages": []}

    with patch("app.agent.tools.KimiClient") as MockClient:
        instance = MockClient.return_value
        instance.chat_completion_stream.return_value = iter(["bad json"])
        list(run_understand(project, state, None))

    assert state["payload"]["understand"]["summary"] == "Project Title"


def test_run_script_uses_existing_step():
    project = MagicMock()
    state = {"payload": {}}
    with patch("app.agent.tools.run_step") as mock_step:
        mock_step.return_value = iter(['{"type": "done"}'])
        result = list(run_script(project, state, "make it punchier"))
    assert result == ['{"type": "done"}']
    mock_step.assert_called_once_with("script", project, state, "make it punchier")


def test_run_assets_uses_step_generator():
    project = MagicMock()
    state = {"payload": {}}
    with patch("app.agent.tools.run_step") as mock_step:
        mock_step.return_value = iter(['{"type": "done"}'])
        list(run_assets(project, state, ""))
    mock_step.assert_called_once_with("assets", project, state, "")


def test_run_render_errors_without_db_or_user():
    project = MagicMock()
    state = {"payload": {}}
    events = list(run_render(project, state, "render it"))
    assert any('"type": "error"' in e and "missing db or user" in e for e in events)


def test_run_render_errors_when_user_has_no_credits():
    project = MagicMock()
    state = {"payload": {}}
    db = MagicMock()
    user = MagicMock()
    user.credits = 0
    events = list(run_render(project, state, "render it", db=db, user=user))
    assert any('"type": "error"' in e for e in events)
    db.add.assert_not_called()


def test_run_render_creates_job_and_enqueues_task():
    project = MagicMock()
    project.id = "proj-1"
    project.title = "T"
    project.target_format = "16:9"
    project.target_duration = 30
    state = {
        "payload": {
            "script": {
                "title": "S",
                "hook": "H",
                "format": "16:9",
                "duration": 30,
            },
            "scenes": {"scenes": [{"text": "scene1"}]},
            "effects": {"effects": []},
            "assets": {"needed": [{"description": "img1"}]},
        }
    }
    db = MagicMock()
    user = MagicMock()
    user.credits = 5

    def fake_refresh(job):
        job.id = "job-1"

    db.refresh.side_effect = fake_refresh

    with patch("app.agent.tools.render_video_task") as mock_task:
        events = list(run_render(project, state, "render it", db=db, user=user))

    db.add.assert_called_once()
    db.commit.assert_called()
    db.refresh.assert_called_once()
    job = db.add.call_args.args[0]
    assert job.project_id == "proj-1"
    assert job.status == "queued"
    mock_task.delay.assert_called_once_with("job-1", "proj-1", None, None, mock_task.delay.call_args.args[4])
    plan = mock_task.delay.call_args.args[4]
    assert plan["title"] == "S"
    assert plan["format"] == "16:9"
    assert plan["assets_needed"] == ["img1"]
    assert plan["scenes"][0].get("narration") == ""
    assert any('"type": "job_created"' in e for e in events)
    assert any('"type": "done"' in e for e in events)
