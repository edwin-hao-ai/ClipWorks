import pytest
from unittest.mock import AsyncMock, MagicMock

from app.rendering.provider import RenderRequest
from app.rendering.providers.hyperframes import HyperFramesProvider


@pytest.mark.asyncio
async def test_hyperframes_provider_can_handle_html_request():
    provider = HyperFramesProvider()
    req = RenderRequest(engine="hyperframes", composition={}, assets={})
    assert provider.can_handle(req) is True


@pytest.mark.asyncio
async def test_hyperframes_provider_calls_renderer(monkeypatch, tmp_path):
    provider = HyperFramesProvider()
    job = MagicMock()
    project = MagicMock()
    project.id = "proj-1"
    request = RenderRequest(
        engine="hyperframes",
        composition={"width": 1920, "height": 1080, "duration": 10},
        assets={},
    )

    monkeypatch.setattr(
        "app.rendering.providers.hyperframes.generate_html",
        lambda _comp, _assets: "<html></html>",
    )
    monkeypatch.setattr("app.rendering.providers.hyperframes.ASSETS_DIR", str(tmp_path))

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "output_url": "/api/static/proj-1/output.mp4",
        "html_output_url": "/api/static/proj-1/index.html",
        "error": None,
    }
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    result = await provider.render(job, project, request)
    assert result.success is True
    assert result.output_url == "/api/static/proj-1/output.mp4"
