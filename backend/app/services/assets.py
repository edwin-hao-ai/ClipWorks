import logging
import os
import shutil
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.config import ASSETS_DIR
from app.models import MediaAsset

logger = logging.getLogger(__name__)


def _ensure_project_dir(project_id: str) -> str:
    path = os.path.join(ASSETS_DIR, project_id)
    os.makedirs(path, exist_ok=True)
    return path


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def download_image(url: str, project_id: str, asset_id: Optional[str] = None) -> Optional[str]:
    """Download an image from a URL into the project's asset directory. Returns local path or None."""
    try:
        project_dir = _ensure_project_dir(project_id)
        ext = os.path.splitext(urlparse(url).path)[1].lower() or ".jpg"
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            ext = ".jpg"
        name = (asset_id or "img") + ext
        local_path = os.path.join(project_dir, name)

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "ClipWorks/1.0"})
            response.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(response.content)

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
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset
