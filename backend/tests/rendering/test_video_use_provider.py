import os

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.rendering.provider import RenderRequest
from app.rendering.providers.video_use import VideoUseProvider


def _asset(asset_id: str, asset_type: str, local_path: str) -> MagicMock:
    asset = MagicMock()
    asset.id = asset_id
    asset.type = asset_type
    asset.local_path = local_path
    return asset


def _composition_with_video_clip(asset_id: str = "vid-1") -> dict:
    return {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "tracks": [
            {
                "type": "video",
                "index": 0,
                "clips": [
                    {"asset_id": asset_id, "start_time": 0, "duration": 5},
                    {"asset_id": asset_id, "start_time": 5, "duration": 3},
                ],
            },
        ],
    }


@pytest.mark.asyncio
async def test_can_handle_with_local_video_clip():
    provider = VideoUseProvider()
    req = RenderRequest(
        composition=_composition_with_video_clip(),
        assets={"images": {}},
        raw_assets=["/data/assets/proj/a.mp4"],
    )
    assert provider.can_handle(req) is True


@pytest.mark.asyncio
async def test_can_handle_rejects_image_text_composition():
    provider = VideoUseProvider()
    image_text_comp = {
        "tracks": [
            {"type": "image", "index": 0, "clips": [{"asset_id": "img-1", "start_time": 0, "duration": 5}]},
            {"type": "text", "index": 1, "clips": [{"text_content": "标题", "start_time": 0, "duration": 5}]},
        ],
    }
    # 纯图片/文本时间线：交给 remotion，video-use 不接管。
    assert provider.can_handle(
        RenderRequest(
            composition=image_text_comp,
            assets={"images": {"img-1": "/api/static/x.png"}},
            raw_assets=["/data/assets/proj/a.mp4"],
        )
    ) is False

    # 无本地视频素材：不接管。
    assert provider.can_handle(RenderRequest(composition=image_text_comp, assets={})) is False

    # video 轨上的 clip 引用的是已知图片素材（绑图后的常态）：仍算模板型合成。
    image_on_video_track = {
        "tracks": [
            {"type": "video", "index": 0, "clips": [{"asset_id": "img-1", "start_time": 0, "duration": 5}]}
        ],
    }
    assert provider.can_handle(
        RenderRequest(
            composition=image_on_video_track,
            assets={"images": {"img-1": "/api/static/x.png"}},
            raw_assets=["/data/assets/proj/a.mp4"],
        )
    ) is False


@pytest.mark.asyncio
async def test_render_translates_composition_to_spec(monkeypatch, tmp_path):
    provider = VideoUseProvider()
    monkeypatch.setattr("app.rendering.providers.video_use.ASSETS_DIR", str(tmp_path))

    video_path = str(tmp_path / "footage.mp4")
    audio_path = str(tmp_path / "bgm.wav")
    project = MagicMock()
    project.id = "proj-1"
    project.assets = [
        _asset("vid-1", "video", video_path),
        _asset("aud-1", "audio", audio_path),
    ]

    composition = _composition_with_video_clip("vid-1")
    composition["tracks"].append(
        {"type": "audio", "index": 1, "clips": [{"asset_id": "aud-1", "start_time": 0, "duration": 8}]}
    )

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "output_url": "/api/static/proj-1/output.mp4",
        "error": None,
    }
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    result = await provider.render(
        MagicMock(),
        project,
        RenderRequest(composition=composition, assets={}, raw_assets=[video_path]),
    )

    assert result.success is True
    assert result.output_url == "/api/static/proj-1/output.mp4"

    call = mock_post.call_args
    assert call.args[0].endswith("/render/video-use")
    spec = call.kwargs["json"]
    assert spec["width"] == 1920
    assert spec["height"] == 1080
    assert spec["fps"] == 30
    # clip.start_time/duration -> trim_start/trim_duration，按时间线顺序
    assert spec["clips"] == [
        {"path": os.path.abspath(video_path), "trim_start": 0.0, "trim_duration": 5.0},
        {"path": os.path.abspath(video_path), "trim_start": 5.0, "trim_duration": 3.0},
    ]
    assert spec["bgm_path"] == os.path.abspath(audio_path)
    assert spec["output"].endswith(os.path.join("proj-1", "output.mp4"))


@pytest.mark.asyncio
async def test_render_skips_non_video_clips_and_missing_assets(monkeypatch, tmp_path):
    provider = VideoUseProvider()
    monkeypatch.setattr("app.rendering.providers.video_use.ASSETS_DIR", str(tmp_path))

    project = MagicMock()
    project.id = "proj-2"
    project.assets = [_asset("img-1", "image", str(tmp_path / "x.png"))]
    composition = {
        "width": 1080,
        "height": 1920,
        "tracks": [
            {"type": "image", "index": 0, "clips": [{"asset_id": "img-1", "start_time": 0, "duration": 5}]},
            {"type": "video", "index": 1, "clips": [{"asset_id": None, "start_time": 0, "duration": 5}]},
        ],
    }

    mock_post = AsyncMock()
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    result = await provider.render(
        MagicMock(), project, RenderRequest(composition=composition, assets={})
    )

    assert result.success is False
    assert "没有关联本地视频素材" in result.error_message
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_render_propagates_renderer_error(monkeypatch, tmp_path):
    provider = VideoUseProvider()
    monkeypatch.setattr("app.rendering.providers.video_use.ASSETS_DIR", str(tmp_path))

    video_path = str(tmp_path / "footage.mp4")
    project = MagicMock()
    project.id = "proj-3"
    project.assets = [_asset("vid-1", "video", video_path)]

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": False, "output_url": None, "error": "ffmpeg 剪辑失败"}
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    result = await provider.render(
        MagicMock(),
        project,
        RenderRequest(composition=_composition_with_video_clip("vid-1"), assets={}, raw_assets=[video_path]),
    )

    assert result.success is False
    assert result.error_message == "ffmpeg 剪辑失败"
