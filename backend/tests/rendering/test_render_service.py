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


def test_default_chain_does_not_include_remotion(monkeypatch):
    """When engine is None and hyperframes/video-use both fail, the service must
    fall back to mock without invoking Remotion.
    """
    from app.rendering import service as service_mod

    mock_hyperframes = MagicMock()
    mock_hyperframes.name = "hyperframes"
    mock_hyperframes.can_handle = lambda r: True
    mock_hyperframes.render = AsyncMock(return_value=MagicMock(success=False, error_message="hf failed"))

    mock_video_use = MagicMock()
    mock_video_use.name = "video-use"
    mock_video_use.can_handle = lambda r: True
    mock_video_use.render = AsyncMock(return_value=MagicMock(success=False, error_message="vu failed"))

    mock_remotion = MagicMock()
    mock_remotion.name = "remotion"
    mock_remotion.can_handle = lambda r: True
    mock_remotion.render = AsyncMock(return_value=MagicMock(success=True, output_url="/remotion.mp4"))

    mock_mock = MagicMock()
    mock_mock.name = "mock"
    mock_mock.can_handle = lambda r: True
    mock_mock.render = AsyncMock(return_value=MagicMock(success=True, output_url="/mock.mp4"))

    service_mod.PROVIDERS = [mock_hyperframes, mock_video_use, mock_remotion, mock_mock]

    request = RenderRequest(composition={}, assets={})
    result = RenderService().render(MagicMock(), MagicMock(), request)

    assert result.success is True
    assert result.output_url == "/mock.mp4"
    assert mock_hyperframes.render.called
    assert mock_video_use.render.called
    assert mock_mock.render.called
    assert not mock_remotion.render.called
