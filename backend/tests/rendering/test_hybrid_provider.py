import pytest
from app.rendering.provider import RenderRequest
from app.rendering.service import RenderService, PROVIDERS


def test_service_includes_all_providers():
    names = {p.name for p in PROVIDERS}
    assert names == {"hyperframes", "video-use", "remotion", "mock"}


def test_service_default_prefers_hyperframes_then_video_use_then_mock(monkeypatch):
    service = RenderService()

    async def fake_hf(self, job, project, request):
        from app.rendering.provider import RenderResult
        return RenderResult(success=False, error_message="hf fail")

    async def fake_vu(self, job, project, request):
        from app.rendering.provider import RenderResult
        return RenderResult(success=True, output_url="/api/static/vu.mp4")

    async def fake_mock(self, job, project, request):
        from app.rendering.provider import RenderResult
        return RenderResult(success=True, output_url="/api/static/sample.mp4")

    monkeypatch.setattr("app.rendering.providers.hyperframes.HyperFramesProvider.render", fake_hf)
    monkeypatch.setattr("app.rendering.providers.video_use.VideoUseProvider.render", fake_vu)
    monkeypatch.setattr("app.rendering.providers.mock.MockProvider.render", fake_mock)

    req = RenderRequest(composition={}, assets={})
    result = service.render(None, None, req)
    assert result.success
    assert result.output_url == "/api/static/vu.mp4"


def test_service_explicit_remotion_still_works(monkeypatch):
    service = RenderService()

    async def fake_remotion(self, job, project, request):
        from app.rendering.provider import RenderResult
        return RenderResult(success=True, output_url="/api/static/remotion.mp4")

    monkeypatch.setattr("app.rendering.providers.remotion.RemotionProvider.render", fake_remotion)

    req = RenderRequest(composition={}, assets={}, engine="remotion")
    result = service.render(None, None, req)
    assert result.success
    assert result.output_url == "/api/static/remotion.mp4"
