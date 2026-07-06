from unittest.mock import patch, MagicMock
from app.tasks.render_task import render_video_task


def test_render_video_task_is_celery_task():
    assert hasattr(render_video_task, "delay")


@patch("app.tasks.render_task.RenderService")
@patch("app.tasks.render_task.SessionLocal")
def test_render_video_task_updates_job_on_success(mock_session_local, mock_service_cls):
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session
    mock_job = MagicMock()
    mock_project = MagicMock()
    mock_project.composition = None
    mock_project.source_url = None
    mock_project.assets = []
    mock_session.query.return_value.filter.return_value.first.side_effect = [mock_job, mock_project]
    mock_service = MagicMock()
    mock_service_cls.return_value = mock_service
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output_url = "/api/static/test.mp4"
    mock_result.html_output_url = "/api/static/test/index.html"
    mock_result.error_message = None
    mock_service.render.return_value = mock_result

    render_video_task.run("job-1", "proj-1", "prompt", "mock")

    assert mock_job.status == "completed"
    assert mock_job.output_url == "/api/static/test.mp4"
    mock_session.commit.assert_called()
