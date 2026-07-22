import asyncio
import logging

from app.rendering.engine_selector import select_engine
from app.rendering.providers.hyperframes import HyperFramesProvider
from app.rendering.providers.remotion import RemotionProvider
from app.rendering.providers.video_use import VideoUseProvider
from app.rendering.providers.mock import MockProvider
from app.rendering.provider import RenderRequest, RenderResult

logger = logging.getLogger(__name__)

PROVIDERS = [
    HyperFramesProvider(),
    VideoUseProvider(),
    RemotionProvider(),
    MockProvider(),
]


class RenderService:
    def render(self, job, project, request: RenderRequest) -> RenderResult:
        return asyncio.run(self._render_async(job, project, request))

    async def _render_async(self, job, project, request: RenderRequest) -> RenderResult:
        engine = request.engine or select_engine(request)
        provider_map = {p.name: p for p in PROVIDERS}

        order_names: list[str] = []
        preferred = engine
        if preferred == "hybrid":
            # hybrid 保留旧行为：优先 remotion 总装，但 scene 仍由 HF 预渲染
            preferred = "remotion"
        if preferred in provider_map:
            order_names.append(preferred)

        # 默认 hyperframes 失败后，按 video-use → remotion → mock 降级
        for name in ("video-use", "remotion"):
            if name in provider_map and name not in order_names:
                order_names.append(name)

        # 其余真实引擎（含未加入的）按注册顺序补入
        for p in PROVIDERS:
            if p.name == "mock" or p.name in order_names:
                continue
            if not p.can_handle(request):
                continue
            order_names.append(p.name)

        if "mock" in provider_map and "mock" not in order_names:
            order_names.append("mock")

        logger.info("render engine chain: preferred=%s order=%s", engine, order_names)
        last_error = None
        for name in order_names:
            provider = provider_map[name]
            result = await provider.render(job, project, request)
            is_real = name != "mock"
            placeholder = "sample.mp4" in (getattr(result, "output_url", None) or "")
            if result.success and not (is_real and placeholder):
                return result
            last_error = getattr(result, "error_message", None) or (
                "placeholder output" if placeholder else None
            )
            logger.warning("provider=%s did not produce a real render: %s", name, last_error)

        return RenderResult(success=False, error_message=last_error or "All providers failed")
