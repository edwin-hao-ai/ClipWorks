import os
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


@patch("app.services.stock_images.fetch_stock_images", return_value=[])
@patch("app.services.audio_track.build_soundtrack", return_value=None)
@patch("app.rendering.qa.check_render_quality", return_value=(True, None))
@patch("app.tasks.render_task.RenderService")
@patch("app.tasks.render_task.SessionLocal")
def test_render_video_task_updates_job_on_success(
    mock_session_local, mock_service_cls, mock_qa, mock_build_soundtrack, mock_fetch_stock
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
        mock_project.title = "Test Project"
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


def test_render_video_task_uses_whole_page_html(monkeypatch):
    """Default path should call generate_html once and RenderService, not hybrid scene prerender."""
    mock_session = MagicMock()
    monkeypatch.setattr("app.tasks.render_task.SessionLocal", lambda: mock_session)

    calls = {"html": 0}

    def fake_generate_html(comp, assets):
        calls["html"] += 1
        return "<html>whole page</html>"

    monkeypatch.setattr("app.tasks.render_task.generate_html", fake_generate_html)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output_url = "/api/static/p1/output.mp4"
    mock_result.html_output_url = "/api/static/p1/index.html"
    mock_result.error_message = None
    mock_service = MagicMock()
    mock_service.render.return_value = mock_result
    monkeypatch.setattr("app.tasks.render_task.RenderService", lambda: mock_service)

    monkeypatch.setattr("app.services.stock_images.fetch_stock_images", lambda *a, **kw: [])
    monkeypatch.setattr("app.services.audio_track.build_soundtrack", lambda *a, **kw: None)
    monkeypatch.setattr("app.rendering.qa.check_render_quality", lambda *a, **kw: (True, None))

    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_job.logs = []
        mock_job.id = "job-1"
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_project.target_format = None
        mock_project.title = "Test Project"
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            mock_project,
            mock_user,
        ]

        render_video_task.run("job-1", "proj-1", "prompt")

        assert calls["html"] == 1
        assert mock_service.render.call_count == 1
        call_args = mock_service.render.call_args
        request_arg = call_args[0][2]
        assert request_arg.engine == "hyperframes"
        assert request_arg.html_path.endswith("index_job-1.html")
        assert mock_job.status == "completed"
    finally:
        for p in patches:
            p.stop()


def test_render_video_task_explicit_engine_passthrough(monkeypatch):
    """Explicit engine should be passed through to RenderService unchanged."""
    mock_session = MagicMock()
    monkeypatch.setattr("app.tasks.render_task.SessionLocal", lambda: mock_session)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output_url = "/api/static/p1/output.mp4"
    mock_result.html_output_url = None
    mock_result.error_message = None
    mock_service = MagicMock()
    mock_service.render.return_value = mock_result
    monkeypatch.setattr("app.tasks.render_task.RenderService", lambda: mock_service)

    monkeypatch.setattr("app.services.stock_images.fetch_stock_images", lambda *a, **kw: [])
    monkeypatch.setattr("app.services.audio_track.build_soundtrack", lambda *a, **kw: None)
    monkeypatch.setattr("app.rendering.qa.check_render_quality", lambda *a, **kw: (True, None))
    monkeypatch.setattr("app.tasks.render_task.generate_html", lambda *a, **kw: "<html></html>")

    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_job.logs = []
        mock_job.id = "job-1"
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_project.target_format = None
        mock_project.title = "Test Project"
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            mock_project,
            mock_user,
        ]

        render_video_task.run("job-1", "proj-1", "prompt", engine="remotion")

        call_args = mock_service.render.call_args
        request_arg = call_args[0][2]
        assert request_arg.engine == "remotion"
        assert mock_job.status == "completed"
    finally:
        for p in patches:
            p.stop()


def test_render_video_task_default_hyperframes_low_memory(monkeypatch):
    """Default HyperFrames render request should use low-memory single-worker settings."""
    mock_session = MagicMock()
    monkeypatch.setattr("app.tasks.render_task.SessionLocal", lambda: mock_session)

    calls = {"request": None}

    def capture_render(job, project, request):
        calls["request"] = request
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_url = "/api/static/p1/output.mp4"
        mock_result.html_output_url = None
        mock_result.error_message = None
        return mock_result

    mock_service = MagicMock()
    mock_service.render.side_effect = capture_render
    monkeypatch.setattr("app.tasks.render_task.RenderService", lambda: mock_service)

    monkeypatch.setattr("app.services.stock_images.fetch_stock_images", lambda *a, **kw: [])
    monkeypatch.setattr("app.services.audio_track.build_soundtrack", lambda *a, **kw: None)
    monkeypatch.setattr("app.rendering.qa.check_render_quality", lambda *a, **kw: (True, None))
    monkeypatch.setattr("app.tasks.render_task.generate_html", lambda *a, **kw: "<html></html>")

    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_job.logs = []
        mock_job.id = "job-1"
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_project.target_format = "9:16"
        mock_project.title = "Test Project"
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            mock_project,
            mock_user,
        ]

        render_video_task.run("job-1", "proj-1", "prompt")

        req = calls["request"]
        assert req.quality == "standard"
        assert req.workers == 1
        assert req.resolution == "portrait"
        assert req.format == "mp4"
        assert mock_job.status == "completed"
    finally:
        for p in patches:
            p.stop()


def test_render_video_task_ultra_quality_maps_to_4k(monkeypatch):
    """Export quality 'ultra' should map to 4k resolution while keeping safe workers."""
    mock_session = MagicMock()
    monkeypatch.setattr("app.tasks.render_task.SessionLocal", lambda: mock_session)

    calls = {"request": None}

    def capture_render(job, project, request):
        calls["request"] = request
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_url = "/api/static/p1/output.mp4"
        mock_result.html_output_url = None
        mock_result.error_message = None
        return mock_result

    mock_service = MagicMock()
    mock_service.render.side_effect = capture_render
    monkeypatch.setattr("app.tasks.render_task.RenderService", lambda: mock_service)

    monkeypatch.setattr("app.services.stock_images.fetch_stock_images", lambda *a, **kw: [])
    monkeypatch.setattr("app.services.audio_track.build_soundtrack", lambda *a, **kw: None)
    monkeypatch.setattr("app.rendering.qa.check_render_quality", lambda *a, **kw: (True, None))
    monkeypatch.setattr("app.tasks.render_task.generate_html", lambda *a, **kw: "<html></html>")

    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_job.logs = []
        mock_job.id = "job-1"
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_project.target_format = "16:9"
        mock_project.title = "Test Project"
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            mock_project,
            mock_user,
        ]

        render_video_task.run("job-1", "proj-1", "prompt", quality="ultra")

        req = calls["request"]
        assert req.quality == "high"
        assert req.resolution == "4k"
        assert req.workers == 1
        assert mock_job.status == "completed"
    finally:
        for p in patches:
            p.stop()


def test_render_video_task_html_fallback_on_generate_failure(monkeypatch):
    """If generate_html fails with assets, it should retry with empty assets and still render."""
    mock_session = MagicMock()
    monkeypatch.setattr("app.tasks.render_task.SessionLocal", lambda: mock_session)

    calls = {"html": 0, "assets": []}

    def fake_generate_html(comp, assets):
        calls["html"] += 1
        calls["assets"].append(assets)
        if assets:
            raise RuntimeError("LLM failed")
        return "<html>fallback</html>"

    monkeypatch.setattr("app.tasks.render_task.generate_html", fake_generate_html)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output_url = "/api/static/p1/output.mp4"
    mock_result.html_output_url = "/api/static/p1/index.html"
    mock_result.error_message = None
    mock_service = MagicMock()
    mock_service.render.return_value = mock_result
    monkeypatch.setattr("app.tasks.render_task.RenderService", lambda: mock_service)

    monkeypatch.setattr("app.services.stock_images.fetch_stock_images", lambda *a, **kw: [])
    monkeypatch.setattr("app.services.audio_track.build_soundtrack", lambda *a, **kw: None)
    monkeypatch.setattr("app.rendering.qa.check_render_quality", lambda *a, **kw: (True, None))

    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_job.logs = []
        mock_job.id = "job-1"
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_project.target_format = None
        mock_project.title = "Test Project"
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            mock_project,
            mock_user,
        ]

        render_video_task.run("job-1", "proj-1", "prompt")

        assert calls["html"] == 2
        assert calls["assets"][1] == {}
        assert mock_job.status == "completed"
    finally:
        for p in patches:
            p.stop()


def test_render_video_task_html_double_failure_uses_deterministic_html(monkeypatch):
    """If both generate_html attempts fail, render task should use deterministic HTML and not crash."""
    mock_session = MagicMock()
    monkeypatch.setattr("app.tasks.render_task.SessionLocal", lambda: mock_session)

    calls = {"html": 0}

    def fake_generate_html(comp, assets):
        calls["html"] += 1
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr("app.tasks.render_task.generate_html", fake_generate_html)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output_url = "/api/static/p1/output.mp4"
    mock_result.html_output_url = "/api/static/p1/index.html"
    mock_result.error_message = None
    mock_service = MagicMock()
    mock_service.render.return_value = mock_result
    monkeypatch.setattr("app.tasks.render_task.RenderService", lambda: mock_service)

    monkeypatch.setattr("app.services.stock_images.fetch_stock_images", lambda *a, **kw: [])
    monkeypatch.setattr("app.services.audio_track.build_soundtrack", lambda *a, **kw: None)
    monkeypatch.setattr("app.rendering.qa.check_render_quality", lambda *a, **kw: (True, None))

    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_job.logs = []
        mock_job.id = "job-1"
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_project.target_format = None
        mock_project.title = "Test Project"
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            mock_project,
            mock_user,
        ]

        render_video_task.run("job-1", "proj-1", "prompt")

        # Both generate_html attempts (with assets and with empty assets) should have been tried.
        assert calls["html"] == 2
        assert mock_service.render.call_count == 1
        call_args = mock_service.render.call_args
        request_arg = call_args[0][2]
        # The deterministic fallback HTML should have been written to disk and referenced.
        assert request_arg.html_path.endswith("index_job-1.html")
        assert os.path.exists(request_arg.html_path)
        with open(request_arg.html_path, "r", encoding="utf-8") as f:
            html = f.read()
        assert "Test Project" in html
        assert "视频生成未完成" in html
        assert mock_job.status == "completed"
    finally:
        for p in patches:
            p.stop()
