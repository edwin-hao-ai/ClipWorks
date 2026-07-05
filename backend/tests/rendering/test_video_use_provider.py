import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.rendering.provider import RenderRequest
from app.rendering.providers.video_use import VideoUseProvider


@pytest.mark.asyncio
async def test_video_use_provider_can_handle_raw_assets():
    provider = VideoUseProvider()
    assert provider.can_handle(RenderRequest(composition={}, assets={}, raw_assets=["/tmp/a.mp4"])) is True
    assert provider.can_handle(RenderRequest(composition={}, assets={})) is False


@pytest.mark.asyncio
async def test_video_use_provider_calls_renderer(monkeypatch, tmp_path):
    provider = VideoUseProvider()
    project = MagicMock()
    project.id = "proj-1"

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "output_url": "/api/static/proj-1/output.mp4", "error": None}
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    with patch("app.config.ASSETS_DIR", str(tmp_path)):
        result = await provider.render(
            MagicMock(), project, RenderRequest(composition={}, assets={}, raw_assets=["/tmp/a.mp4"], user_prompt="cut")
        )

    assert result.success is True
    assert result.output_url == "/api/static/proj-1/output.mp4"
