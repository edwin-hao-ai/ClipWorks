import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.rendering.provider import RenderRequest
from app.rendering.providers.remotion import RemotionProvider, _resolve_asset_url


@pytest.mark.asyncio
async def test_remotion_provider_can_handle_explicit_engine():
    provider = RemotionProvider()
    assert provider.can_handle(RenderRequest(engine="remotion", composition={}, assets={})) is True
    assert provider.can_handle(RenderRequest(engine="hybrid", composition={}, assets={})) is True
    assert provider.can_handle(RenderRequest(engine="hyperframes", composition={}, assets={})) is False
    assert provider.can_handle(RenderRequest(composition={}, assets={})) is False


@pytest.mark.asyncio
async def test_remotion_provider_calls_renderer(monkeypatch, tmp_path):
    provider = RemotionProvider()
    project = MagicMock()
    project.id = "proj-1"
    project.assets = []

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "output_url": "/api/static/proj-1/output.mp4", "error": None}
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    with patch("app.rendering.providers.remotion.ASSETS_DIR", str(tmp_path)):
        with patch("app.rendering.providers.remotion.ASSETS_BASE_URL", "http://backend:8000"):
            result = await provider.render(MagicMock(), project, RenderRequest(composition={"duration": 10}, assets={}))

    assert result.success is True
    assert result.output_url == "/api/static/proj-1/output.mp4"


@pytest.mark.asyncio
async def test_remotion_provider_writes_asset_map(monkeypatch, tmp_path):
    provider = RemotionProvider()
    project = MagicMock()
    project.id = "proj-2"

    asset = MagicMock()
    asset.id = "asset-1"
    asset.local_path = os.path.join(str(tmp_path), "proj-2", "image.png")
    os.makedirs(os.path.dirname(asset.local_path), exist_ok=True)
    with open(asset.local_path, "w") as f:
        f.write("placeholder")
    project.assets = [asset]

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "output_url": "/api/static/proj-2/output.mp4", "error": None}
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    composition = {
        "duration": 10,
        "tracks": [
            {
                "type": "image",
                "index": 0,
                "clips": [
                    {"id": "clip-1", "asset_id": "asset-1", "start_time": 0, "duration": 5}
                ],
            }
        ],
    }

    with patch("app.rendering.providers.remotion.ASSETS_DIR", str(tmp_path)):
        with patch("app.rendering.providers.remotion.ASSETS_BASE_URL", "http://backend:8000"):
            await provider.render(MagicMock(), project, RenderRequest(composition=composition, assets={}))

    comp_path = os.path.join(str(tmp_path), "proj-2", "composition.json")
    with open(comp_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    assert "assets" in payload
    assert payload["assets"]["asset-1"] == "http://backend:8000/api/static/proj-2/image.png"


@pytest.mark.asyncio
async def test_remotion_provider_uses_media_proxy_for_video(monkeypatch, tmp_path):
    provider = RemotionProvider()
    project = MagicMock()
    project.id = "proj-3"

    asset = MagicMock()
    asset.id = "asset-video"
    asset.type = "video"
    asset.local_path = os.path.join(str(tmp_path), "proj-3", "clip.mp4")
    asset.metadata_ = {}
    os.makedirs(os.path.dirname(asset.local_path), exist_ok=True)
    with open(asset.local_path, "w") as f:
        f.write("fake mp4")

    proxy_path = os.path.join(str(tmp_path), "proj-3", "clip.remotion.webm")
    with open(proxy_path, "w") as f:
        f.write("fake webm")

    project.assets = [asset]

    mock_post = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "output_url": "/api/static/proj-3/output.mp4", "error": None}
    mock_post.return_value = mock_response
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    composition = {
        "duration": 10,
        "tracks": [
            {
                "type": "video",
                "index": 0,
                "clips": [
                    {"id": "clip-1", "asset_id": "asset-video", "start_time": 0, "duration": 5}
                ],
            }
        ],
    }

    with patch("app.rendering.providers.remotion.ASSETS_DIR", str(tmp_path)):
        with patch("app.rendering.providers.remotion.ASSETS_BASE_URL", "http://backend:8000"):
            with patch("app.rendering.providers.remotion.ensure_proxy", return_value=proxy_path) as mock_proxy:
                await provider.render(MagicMock(), project, RenderRequest(composition=composition, assets={}))

    mock_proxy.assert_called_once_with("video", asset.local_path, asset.metadata_)
    comp_path = os.path.join(str(tmp_path), "proj-3", "composition.json")
    with open(comp_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["assets"]["asset-video"] == "http://backend:8000/api/static/proj-3/clip.remotion.webm"
