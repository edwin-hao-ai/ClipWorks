import asyncio

from app.rendering.engine_selector import select_engine
from app.rendering.providers.hyperframes import HyperFramesProvider
from app.rendering.providers.remotion import RemotionProvider
from app.rendering.providers.video_use import VideoUseProvider
from app.rendering.providers.mock import MockProvider
from app.rendering.provider import RenderRequest, RenderResult

PROVIDERS = [
    HyperFramesProvider(),
    RemotionProvider(),
    VideoUseProvider(),
    MockProvider(),
]


class RenderService:
    def render(self, job, project, request: RenderRequest) -> RenderResult:
        """Synchronous entry point that runs the async render pipeline via asyncio.run().

        This method is intentionally synchronous so it can be called directly from
        synchronous contexts such as Celery tasks. It internally executes the async
        provider chain with asyncio.run().
        """
        return asyncio.run(self._render_async(job, project, request))

    async def _render_async(self, job, project, request: RenderRequest) -> RenderResult:
        engine = request.engine or select_engine(request)
        provider_map = {p.name: p for p in PROVIDERS}
        ordered = [provider_map[engine]] if engine in provider_map else []
        ordered += [p for p in PROVIDERS if p.name != engine and p.can_handle(request)]

        last_error = None
        for provider in ordered:
            result = await provider.render(job, project, request)
            if result.success:
                return result
            last_error = result.error_message

        return RenderResult(success=False, error_message=last_error or "All providers failed")
