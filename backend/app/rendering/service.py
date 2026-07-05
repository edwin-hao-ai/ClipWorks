import logging
from app.rendering.provider import RenderRequest, RenderResult
from app.rendering.providers.hyperframes import HyperFramesProvider

logger = logging.getLogger(__name__)

PROVIDERS = [
    HyperFramesProvider(),
]


class RenderService:
    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        selected = next((p for p in PROVIDERS if p.can_handle(request)), None)
        if not selected:
            return RenderResult(success=False, error_message="No provider can handle the request")

        result = await selected.render(job, project, request)
        if result.success:
            return result

        # Fallback to any other provider that can handle the request.
        for provider in PROVIDERS:
            if provider.name == selected.name:
                continue
            if provider.can_handle(request):
                logger.info("Falling back from %s to %s", selected.name, provider.name)
                fb = await provider.render(job, project, request)
                if fb.success:
                    return fb

        return result
