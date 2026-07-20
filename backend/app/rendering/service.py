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

        # 引擎只是「偏好」而非硬性约束：首选失败后，必须继续尝试其它真实引擎，
        # 否则一旦首选引擎（如 hyperframes）在当前环境不可用，就会因为各 provider
        # 的 can_handle 按 engine 名过滤而直接跌落到 Mock 占位片。
        order_names: list[str] = []
        preferred = engine
        if preferred == "hybrid":
            preferred = "remotion"
        if preferred in provider_map:
            order_names.append(preferred)
        for name in ("remotion", "hyperframes"):
            if name in provider_map and name not in order_names:
                order_names.append(name)
        # 其余已注册的真实引擎（含 video-use 或测试替身）按注册顺序补入；
        # 由各 provider 的 can_handle 自行决定是否认领——video-use 的判定很保守，
        # 仅当合成里确实存在本地视频素材 clip 时才会进入降级链。
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
            # 真实引擎若返回占位 sample.mp4，视为失败并继续降级；仅 mock 允许以占位收尾。
            is_real = name != "mock"
            placeholder = "sample.mp4" in (getattr(result, "output_url", None) or "")
            if result.success and not (is_real and placeholder):
                return result
            last_error = getattr(result, "error_message", None) or (
                "placeholder output" if placeholder else None
            )
            logger.warning("provider=%s did not produce a real render: %s", name, last_error)

        return RenderResult(success=False, error_message=last_error or "All providers failed")
