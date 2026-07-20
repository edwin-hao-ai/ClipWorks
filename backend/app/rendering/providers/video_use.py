import os
import httpx
import logging
from app.config import ASSETS_DIR, RENDERER_URL
from app.rendering.provider import RenderProvider, RenderRequest, RenderResult

logger = logging.getLogger(__name__)


def _project_assets(project) -> dict:
    return {a.id: a for a in getattr(project, "assets", []) or []}


def _local_path_under_assets(asset) -> str | None:
    """返回素材在 ASSETS_DIR 下的绝对路径；不在则 None。

    video-use 走 ffmpeg 直接读原始文件，不需要 Remotion 链路那种 Chromium 安全
    转码（proxy_path），直接用 local_path 即可。
    """
    local_path = getattr(asset, "local_path", None)
    if not local_path:
        return None
    abs_path = os.path.abspath(local_path)
    if not abs_path.startswith(os.path.abspath(ASSETS_DIR)):
        return None
    return abs_path


def _collect_video_clips(project, composition: dict) -> list[dict]:
    """把时间线上关联了本地视频素材的 clip 翻译成 spec clips（按时间线顺序）。

    clip.start_time/duration 映射为 trim_start/trim_duration：时间线第 N 段播放
    源素材的 [start_time, start_time+duration] 区间，trim 超出素材时长时 ffmpeg
    会自然截断，无需特殊处理。
    """
    assets = _project_assets(project)
    timed: list[tuple[float, dict]] = []
    for track in composition.get("tracks", []) or []:
        if track.get("type") != "video":
            continue
        for clip in track.get("clips", []) or []:
            asset = assets.get(clip.get("asset_id"))
            if not asset or getattr(asset, "type", None) != "video":
                continue
            path = _local_path_under_assets(asset)
            if not path:
                continue
            start = float(clip.get("start_time", 0) or 0)
            duration = float(clip.get("duration", 0) or 0)
            if duration <= 0:
                continue
            timed.append((start, {"path": path, "trim_start": start, "trim_duration": duration}))
    timed.sort(key=lambda item: item[0])
    return [seg for _, seg in timed]


def _find_bgm(project, composition: dict) -> str | None:
    """取合成里第一条可用的音频轨素材作为背景音乐。"""
    assets = _project_assets(project)
    for track in composition.get("tracks", []) or []:
        if track.get("type") != "audio":
            continue
        for clip in track.get("clips", []) or []:
            asset = assets.get(clip.get("asset_id"))
            if asset:
                path = _local_path_under_assets(asset)
                if path:
                    return path
    return None


class VideoUseProvider(RenderProvider):
    """video-use：真实视频素材剪辑引擎（ffmpeg trim + concat + 可选 bgm）。

    只接管「合成里确实存在本地视频素材 clip」的请求；纯图片/文本/生成素材的
    模板型合成留给 remotion。can_handle 故意保守：只有 clip 的 asset_id 指向
    非已知图片素材的视频轨片段时才认领，绝不抢占 remotion 的主场。
    """

    name = "video-use"

    def can_handle(self, request: RenderRequest) -> bool:
        if not request.raw_assets:
            return False
        images = (request.assets or {}).get("images", {}) or {}
        for track in (request.composition or {}).get("tracks", []) or []:
            if track.get("type") != "video":
                continue
            for clip in track.get("clips", []) or []:
                asset_id = clip.get("asset_id")
                # 已知图片素材（_build_assets 收集的 image_ids）不算视频素材；
                # 视频轨上引用了非图片素材的 clip 才视为真实视频素材片段。
                if asset_id and asset_id not in images:
                    return True
        return False

    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        composition = request.composition or {}
        clips = _collect_video_clips(project, composition)
        if not clips:
            return RenderResult(
                success=False,
                error_message="video-use: 时间线上没有关联本地视频素材的 clip",
            )

        output_path = os.path.join(ASSETS_DIR, project.id, "output.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        spec = {
            "width": int(composition.get("width") or 1920),
            "height": int(composition.get("height") or 1080),
            "fps": int(composition.get("fps") or 30),
            "clips": clips,
            "output": output_path,
        }
        bgm_path = _find_bgm(project, composition)
        if bgm_path:
            spec["bgm_path"] = bgm_path

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(f"{RENDERER_URL}/render/video-use", json=spec)
                resp.raise_for_status()
                data = resp.json()
                return RenderResult(
                    success=data.get("success", False),
                    output_url=data.get("output_url"),
                    error_message=data.get("error"),
                )
        except Exception as exc:
            logger.exception("VideoUse provider failed")
            return RenderResult(success=False, error_message=str(exc))
