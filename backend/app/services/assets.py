import hashlib
import logging
import os
import shutil
from typing import Optional
from urllib.parse import urlparse

import httpx  # noqa: F401

from app.config import ASSETS_DIR
from app.models import MediaAsset
from app.services.url_safety import safe_get

logger = logging.getLogger(__name__)

# 下载图片上限：与上传 50MB 限制错开，远程抓取收紧到 20MB。
_MAX_IMAGE_BYTES = 20 * 1024 * 1024
_ALLOWED_IMAGE_CONTENT_TYPES = ("image/", "application/octet-stream")


def _ensure_project_dir(project_id: str) -> str:
    path = os.path.join(ASSETS_DIR, project_id)
    os.makedirs(path, exist_ok=True)
    return path


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def download_image(
    url: str,
    project_id: str,
    asset_id: Optional[str] = None,
    trusted_host_suffixes: tuple = (),
) -> Optional[str]:
    """Download an image from a URL into the project's asset directory. Returns local path or None.

    trusted_host_suffixes：可信域名白名单（如自动配图的 picsum.photos），命中后跳过
    DNS-IP 校验，兼容 fake-ip 代理环境；用户输入 URL 不传此参数，保持完整 SSRF 防护。
    """
    try:
        project_dir = _ensure_project_dir(project_id)
        ext = os.path.splitext(urlparse(url).path)[1].lower() or ".jpg"
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            ext = ".jpg"
        if asset_id:
            name = asset_id + ext
        else:
            # 未指定 asset_id 时按 URL 哈希生成确定性唯一文件名：同一 URL 重复下载
            # 覆盖自己（幂等），不同 URL 不再互相覆盖（此前统一写 img.jpg，会丢图）。
            digest = hashlib.sha1(url.encode()).hexdigest()[:10]
            name = f"img_{digest}{ext}"
        local_path = os.path.join(project_dir, name)

        # SSRF/类型/大小防护：仅公网 http/https，逐跳校验重定向，要求图片类型并限制大小。
        body, _response = safe_get(
            url,
            timeout=30,
            headers={"User-Agent": "ClipWorks/1.0"},
            max_bytes=_MAX_IMAGE_BYTES,
            allowed_content_types=_ALLOWED_IMAGE_CONTENT_TYPES,
            trusted_host_suffixes=trusted_host_suffixes,
        )
        with open(local_path, "wb") as f:
            f.write(body)

        return local_path
    except Exception as exc:
        logger.warning("download_image failed for %s: %s", url, exc)
        return None


def resolve_image_asset(query_or_url: str, project_id: str, db_session=None) -> dict:
    """Resolve an image asset: if it's a URL, download it; otherwise return a placeholder record."""
    if _is_url(query_or_url):
        local_path = download_image(query_or_url, project_id)
        if local_path:
            relative = local_path.replace(os.path.sep, "/")
            return {
                "type": "image",
                "source": "user_url",
                "original_url": query_or_url,
                "local_path": relative,
            }

    # Placeholder / query fallback
    return {
        "type": "image",
        "source": "generated",
        "original_url": query_or_url,
        "local_path": None,
    }


def persist_asset(project_id: str, asset_data: dict, db_session) -> MediaAsset:
    """Persist an asset dict to the database."""
    asset = MediaAsset(
        project_id=project_id,
        type=asset_data.get("type", "image"),
        source=asset_data.get("source", "generated"),
        original_url=asset_data.get("original_url"),
        local_path=asset_data.get("local_path"),
        metadata_=asset_data.get("metadata") or {},
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset
