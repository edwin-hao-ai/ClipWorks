from app.rendering.engine_selector import select_engine
from app.rendering.providers.hyperframes import HyperFramesProvider
from app.rendering.providers.mock import MockProvider
from app.rendering.provider import RenderRequest, RenderResult

PROVIDERS = [
    HyperFramesProvider(),
    MockProvider(),
]

PROVIDER_MAP = {p.name: p for p in PROVIDERS}


class RenderService:
    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        engine = request.engine or select_engine(request)
        ordered = [PROVIDER_MAP[engine]] if engine in PROVIDER_MAP else []
        ordered += [p for p in PROVIDERS if p.name != engine and p.can_handle(request)]

        last_error = None
        for provider in ordered:
            result = await provider.render(job, project, request)
            if result.success:
                return result
            last_error = result.error_message

        return RenderResult(success=False, error_message=last_error or "All providers failed")
