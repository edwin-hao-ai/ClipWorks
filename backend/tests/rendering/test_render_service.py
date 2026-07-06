from unittest.mock import AsyncMock, MagicMock

from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService


def test_service_tries_fallback_on_failure(monkeypatch):
    from app.rendering import service as service_mod

    mock_provider_a = MagicMock()
    mock_provider_a.name = "a"
    mock_provider_a.can_handle = lambda r: True
    mock_provider_a.render = AsyncMock(return_value=MagicMock(success=False, error_message="a failed"))

    mock_provider_b = MagicMock()
    mock_provider_b.name = "b"
    mock_provider_b.can_handle = lambda r: True
    mock_provider_b.render = AsyncMock(return_value=MagicMock(success=True, output_url="/ok.mp4"))

    service_mod.PROVIDERS = [mock_provider_a, mock_provider_b]

    result = RenderService().render(MagicMock(), MagicMock(), RenderRequest(composition={}, assets={}))
    assert result.success is True
    assert result.output_url == "/ok.mp4"
