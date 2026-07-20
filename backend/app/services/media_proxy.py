import os
import logging
import httpx

from app.config import ASSETS_DIR, RENDERER_URL

logger = logging.getLogger(__name__)

VIDEO_PROXY_EXT = ".webm"
AUDIO_PROXY_EXT = ".ogg"


def _needs_proxy(asset_type: str, local_path: str) -> bool:
    """Return True when the original file is unlikely to play in Chromium."""
    if asset_type == "video":
        # Remotion's bundled Chromium supports VP8/VP9 in WebM, but usually
        # lacks proprietary H.264/HEVC codecs found in MP4/MOV/MKV.
        return not local_path.lower().endswith(".webm")
    if asset_type == "audio":
        # WAV and Ogg are safe; MP3/AAC/FLAC may fail in the headless browser.
        return local_path.lower().endswith((".mp3", ".aac", ".m4a", ".wma", ".flac"))
    return False


def _proxy_path(local_path: str, asset_type: str) -> str:
    base, _ = os.path.splitext(local_path)
    ext = VIDEO_PROXY_EXT if asset_type == "video" else AUDIO_PROXY_EXT
    return f"{base}.remotion{ext}"


def _transcode_with_renderer(input_path: str, output_path: str, asset_type: str) -> str:
    """Ask the renderer service to transcode the media into a browser-safe format."""
    logger.info(
        "Requesting renderer proxy: %s -> %s (%s)", input_path, output_path, asset_type
    )
    try:
        resp = httpx.post(
            f"{RENDERER_URL}/render/proxy",
            json={
                "input_path": input_path,
                "output_path": output_path,
                "asset_type": asset_type,
            },
            timeout=300,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"Renderer proxy request failed: {exc}") from exc

    if not data.get("success"):
        error = data.get("error") or "Unknown proxy error"
        raise RuntimeError(f"Renderer proxy failed: {error}")
    return data["output_path"]


def ensure_proxy(
    asset_type: str, local_path: str, metadata: dict | None = None
) -> str:
    """Return a Remotion-friendly media path.

    If the original file is already in an open codec that Chromium supports,
    return it as-is. Otherwise ask the renderer service to transcode it to
    WebM VP8 (video) or Ogg Vorbis (audio) and cache the proxy path in the
    asset metadata.
    """
    if not local_path or not os.path.exists(local_path):
        raise FileNotFoundError(f"Asset file not found: {local_path}")

    if not _needs_proxy(asset_type, local_path):
        return local_path

    proxy_path = _proxy_path(local_path, asset_type)
    meta = metadata or {}
    cached = meta.get("proxy_path")
    if (
        cached
        and os.path.exists(cached)
        and os.path.getmtime(cached) >= os.path.getmtime(local_path)
    ):
        return cached

    _transcode_with_renderer(local_path, proxy_path, asset_type)
    if metadata is not None:
        metadata["proxy_path"] = proxy_path
    return proxy_path
