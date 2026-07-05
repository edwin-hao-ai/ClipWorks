import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.rendering.provider import RenderRequest
from app.rendering.providers.remotion import RemotionProvider


@pytest.mark.asyncio
async def test_remotion_provider_can_handle():
    provider = RemotionProvider()
    assert provider.can_handle(RenderRequest(engine="remotion", composition={}, assets={})) is True
    assert provider.can_handle(RenderRequest(engine="hyperframes", composition={}, assets={})) is False


@pytest.mark.asyncio
async def test_remotion_provider_calls_renderer(monkeypatch, tmp_path):
    provider = RemotionProvider()
    project = MagicMock()
    project.id = "proj-1"

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "output_url": "/api/static/proj-1/output.mp4", "error": None}
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    with patch("app.config.ASSETS_DIR", str(tmp_path)):
        result = await provider.render(MagicMock(), project, RenderRequest(composition={"duration": 10}, assets={}))

    assert result.success is True
    assert result.output_url == "/api/static/proj-1/output.mp4"
