from unittest.mock import patch, MagicMock
from app.tasks.render_task import render_video_task


def test_render_video_task_is_celery_task():
    assert hasattr(render_video_task, "delay")


def _patch_kimi_client():
    """Replace KimiClient in all agent submodules so tests don't hit the network."""
    targets = [
        "app.agent.planner.KimiClient",
        "app.agent.composer.KimiClient",
        "app.agent.html_generator.KimiClient",
        "app.agent.modifier.KimiClient",
    ]
    mock_client = MagicMock()
    mock_client.return_value.chat_completion_json.return_value = {
        "title": "Test",
        "scenes": [],
        "duration": 5,
    }
    mock_client.return_value.chat_completion.return_value = "<html></html>"
    return [patch(t, mock_client) for t in targets]


@patch("app.rendering.qa.check_render_quality", return_value=(True, None))
@patch("app.tasks.render_task.RenderService")
@patch("app.tasks.render_task.SessionLocal")
def test_render_video_task_updates_job_on_success(
    mock_session_local, mock_service_cls, mock_qa
):
    # QA 抽帧闸门本身由 tests/test_qa_gate.py 覆盖；这里只验证任务编排，
    # 把 QA mock 成通过，避免去渲染服务/磁盘找一份并不存在的测试视频。
    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_job = MagicMock()
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [mock_job, mock_project, mock_user]
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
        assert mock_user.credits == 4
        mock_session.commit.assert_called()
    finally:
        for p in patches:
            p.stop()
