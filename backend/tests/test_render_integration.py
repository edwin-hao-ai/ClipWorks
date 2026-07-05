import pytest
from unittest.mock import patch, AsyncMock
from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService


@pytest.mark.asyncio
async def test_render_service_falls_back_to_mock():
    with patch("app.rendering.service.PROVIDERS") as mock_providers:
        failing = AsyncMock()
        failing.name = "hyperframes"
        failing.can_handle = lambda r: True
        failing.render = AsyncMock(return_value=type("R", (), {"success": False, "error_message": "hf down"})())

        mockk = AsyncMock()
        mockk.name = "mock"
        mockk.can_handle = lambda r: True
        mockk.render = AsyncMock(return_value=type("R", (), {"success": True, "output_url": "/sample.mp4"})())

        mock_providers.__iter__ = lambda self: iter([failing, mockk])
        result = await RenderService().render(None, None, RenderRequest(composition={}, assets={}))
        assert result.success is True
