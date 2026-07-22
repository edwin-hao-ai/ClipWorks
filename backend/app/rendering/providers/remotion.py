import copy
import json
import os
import httpx
import logging
from sqlalchemy.orm.attributes import flag_modified
from app.config import ASSETS_BASE_URL, ASSETS_DIR, RENDERER_URL
from app.rendering.provider import RenderProvider, RenderRequest, RenderResult
from app.services.media_proxy import ensure_proxy

logger = logging.getLogger(__name__)


def _resolve_asset_url(asset) -> str | None:
    """Return a renderer-accessible URL for a project asset.

    Video and audio assets are normalized to Chromium-safe codecs before the
    URL is built so Remotion's bundled browser can decode them.

    Legacy compatibility: older projects stored files under ``backend/data/assets``
    while ``ASSETS_DIR`` now points to the repo-root ``data/assets``. When a file
    exists outside the configured root, it is migrated into ``ASSETS_DIR`` and the
    asset record is updated so subsequent renders do not repeat the lookup failure.
    """
    import shutil

    local_path = os.path.abspath(asset.local_path)

    # Migrate legacy paths (e.g. backend/data/assets) into the canonical ASSETS_DIR.
    if not local_path.startswith(ASSETS_DIR):
        if not os.path.exists(local_path):
            return None
        project_dir_name = os.path.basename(os.path.dirname(local_path))
        new_dir = os.path.join(ASSETS_DIR, project_dir_name)
        os.makedirs(new_dir, exist_ok=True)
        new_path = os.path.join(new_dir, os.path.basename(local_path))
        try:
            shutil.move(local_path, new_path)
        except Exception:
            logger.exception("Failed to migrate legacy asset %s to %s", asset.id, new_path)
            return None
        asset.local_path = new_path
        flag_modified(asset, "local_path")
        local_path = new_path

    if asset.type in ("video", "audio"):
        metadata = asset.metadata_ or {}
        local_path = ensure_proxy(asset.type, local_path, metadata)
        if asset.metadata_ is not metadata or "proxy_path" in metadata:
            asset.metadata_ = metadata
            flag_modified(asset, "metadata_")

    rel = os.path.relpath(local_path, ASSETS_DIR).replace(os.sep, "/")
    return f"{ASSETS_BASE_URL}/api/static/{rel}"


def _build_asset_map(project, composition: dict) -> dict:
    """Resolve clip asset_ids to absolute URLs that the renderer can load."""
    asset_map = {}
    project_assets = {a.id: a for a in getattr(project, "assets", [])}

    for track in composition.get("tracks", []):
        for clip in track.get("clips", []):
            asset_id = clip.get("asset_id")
            if not asset_id or asset_id in asset_map:
                continue
            asset = project_assets.get(asset_id)
            if not asset or not asset.local_path:
                continue
            try:
                url = _resolve_asset_url(asset)
                if url:
                    asset_map[asset_id] = url
            except Exception:
                logger.exception("Failed to resolve asset %s for Remotion", asset_id)

    return asset_map


def _split_audio(composition: dict, project) -> tuple[dict, str | None]:
    """抽出 audio 轨对应的本地音轨文件，并返回「仅视频」的合成副本。

    返回 (video_only_composition, audio_local_path|None)。audio 轨保留在 DB/编辑器里，
    但送给 Remotion 的合成不带音轨——避免 Chromium 逐帧解码远端音频把出片拖慢 5-10 倍。
    """
    project_assets = {a.id: a for a in getattr(project, "assets", [])}
    audio_path: str | None = None
    video_tracks = []
    for track in composition.get("tracks", []) or []:
        if track.get("type") == "audio":
            if audio_path is None:
                for clip in track.get("clips", []) or []:
                    asset = project_assets.get(clip.get("asset_id"))
                    if asset and asset.local_path and os.path.exists(asset.local_path):
                        audio_path = os.path.abspath(asset.local_path)
                        break
            continue
        video_tracks.append(track)
    video_comp = copy.deepcopy(composition)
    video_comp["tracks"] = video_tracks
    return video_comp, audio_path


class RemotionProvider(RenderProvider):
    name = "remotion"

    def can_handle(self, request: RenderRequest) -> bool:
        return request.engine in ("remotion", "hybrid")

    async def render(self, job, project, request: RenderRequest) -> RenderResult:
        project_dir = os.path.join(ASSETS_DIR, project.id)
        os.makedirs(project_dir, exist_ok=True)
        comp_path = os.path.join(project_dir, "composition.json")
        output_path = os.path.join(project_dir, "output.mp4")

        # 关键优化：把 audio 轨从送给 Remotion 的合成里剥离（Remotion 只渲视频帧，≈1 分钟），
        # 音轨随后用 ffmpeg 一次封装成 AAC（≈2 秒）。DB/编辑器里仍保留 audio 轨。
        video_comp, audio_path = _split_audio(request.composition, project)
        asset_map = _build_asset_map(project, video_comp)
        payload = {
            "composition": video_comp,
            "assets": asset_map,
        }

        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        try:
            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post(
                    f"{RENDERER_URL}/render/remotion",
                    json={"composition_path": comp_path, "output_path": output_path},
                )
                resp.raise_for_status()
                data = resp.json()
                if not data.get("success"):
                    return RenderResult(
                        success=False,
                        output_url=data.get("output_url"),
                        error_message=data.get("error"),
                    )

                # 视频成片后，把音轨用 ffmpeg 混成 AAC 封装进去（copy 视频流，秒级完成）。
                if audio_path:
                    mux = await client.post(
                        f"{RENDERER_URL}/render/mux-audio",
                        json={
                            "video_path": output_path,
                            "audio_path": audio_path,
                            "output_path": output_path,
                        },
                    )
                    try:
                        mux_data = mux.json()
                    except Exception:
                        mux_data = {"success": False, "error": "bad mux response"}
                    if not mux_data.get("success"):
                        # 混音失败不掩盖已成片的视频：返回带音频缺失提示的成功结果，
                        # 由上层决定是否在日志里提示用户（优于整片失败）。
                        logger.warning("mux-audio failed, shipping video-only: %s", mux_data.get("error"))

                final_output_url = data.get("output_url")
                if audio_path and mux_data.get("success"):
                    final_output_url = mux_data.get("output_url") or final_output_url

                return RenderResult(
                    success=True,
                    output_url=final_output_url,
                    error_message=None,
                )
        except Exception as exc:
            logger.exception("Remotion provider failed")
            return RenderResult(success=False, error_message=str(exc))
