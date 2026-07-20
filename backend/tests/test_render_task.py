import os
from unittest.mock import patch, MagicMock
from app.tasks.render_task import (
    render_video_task,
    _derive_scenes,
    _build_assembly_composition,
)


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


def test_derive_scenes_uses_plan_scenes():
    comp = {
        "metadata": {
            "plan": {
                "scenes": [
                    {"start": 0, "duration": 3, "text": "A"},
                    {"start": 3, "duration": 4, "text": "B"},
                ]
            }
        },
        "tracks": [],
    }
    scenes = _derive_scenes(comp)
    assert len(scenes) == 2
    assert scenes[0]["text"] == "A"
    assert scenes[1]["start"] == 3


def test_derive_scenes_falls_back_to_clips():
    comp = {
        "metadata": {},
        "tracks": [
            {"type": "text", "clips": [
                {"start_time": 0, "duration": 2, "text_content": "X"},
                {"start_time": 2, "duration": 3, "text_content": "Y"},
            ]}
        ],
    }
    scenes = _derive_scenes(comp)
    assert len(scenes) == 2
    assert scenes[0]["text"] == "X"


def test_build_assembly_composition_replaces_visual_clips():
    comp = {
        "width": 1920,
        "height": 1080,
        "duration": 7,
        "tracks": [
            {"type": "video", "index": 0, "clips": [{"start_time": 0, "duration": 3, "asset_id": "old1"}]},
            {"type": "text", "index": 1, "clips": [{"start_time": 0, "duration": 3, "text_content": "A"}]},
        ],
    }
    scenes = [{"start": 0, "duration": 3, "text": "A", "transition": "fade"}]
    scene_results = {0: ("scene_0_asset_id", False)}
    project = MagicMock()
    project.id = "p1"
    project.assets = []
    result = _build_assembly_composition(comp, scenes, scene_results, project)
    assert len(result["tracks"]) == 2
    video_track = result["tracks"][0]
    assert video_track["type"] == "video"
    assert len(video_track["clips"]) == 1
    assert video_track["clips"][0]["asset_id"] == "scene_0_asset_id"
    assert video_track["clips"][0]["style"]["transition"] == "fade"
    # text track unchanged
    assert result["tracks"][1]["clips"][0]["text_content"] == "A"


def test_render_video_task_hybrid_path(monkeypatch):
    """验证 engine='hybrid' 时走 scene 拆分 -> HF 预渲染 -> Remotion 总装流程。"""
    # 屏蔽外部网络/文件系统依赖，保留任务编排逻辑。
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
    monkeypatch.setattr("app.tasks.render_task._write_scene_htmls", lambda *a, **kw: {0: "/tmp/scene_0.html"})
    monkeypatch.setattr(
        "app.tasks.render_task._prerender_scenes",
        lambda *a, **kw: {0: ("scene_asset_id", False)},
    )
    monkeypatch.setattr("app.rendering.qa.check_render_quality", lambda *a, **kw: (True, None))

    patches = _patch_kimi_client()
    for p in patches:
        p.start()
    try:
        mock_job = MagicMock()
        mock_job.status = "queued"
        mock_job.logs = []
        mock_project = MagicMock()
        mock_project.composition = None
        mock_project.source_url = None
        mock_project.assets = []
        mock_project.target_format = None
        mock_user = MagicMock()
        mock_user.credits = 5
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            mock_job,
            mock_project,
            mock_user,
        ]

        plan = {
            "title": "T",
            "duration": 5,
            "format": "16:9",
            "scenes": [{"start": 0, "duration": 5, "text": "Hello"}],
        }
        render_video_task.run("job-1", "proj-hybrid", "prompt", engine="hybrid", plan=plan)

        assert mock_job.status == "completed"
        assert mock_job.output_url == "/api/static/p1/output.mp4"
        assert mock_user.credits == 4
        assert any("总装" in (e.get("message") or "") for e in (mock_job.logs or []))

        call_args = mock_service.render.call_args
        request_arg = call_args[0][2]
        assert request_arg.engine == "hybrid"
        # 总装后的 composition 应把 scene 范围内的 visual clip 替换为预渲染 MP4
        assert any(
            clip.get("asset_id") == "scene_asset_id"
            for track in request_arg.composition.get("tracks", [])
            for clip in track.get("clips", [])
        )
    finally:
        for p in patches:
            p.stop()
