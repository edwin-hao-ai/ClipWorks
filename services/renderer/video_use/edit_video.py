import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _is_under_assets(path: str, assets_dir: str) -> bool:
    abs_path = os.path.abspath(path)
    abs_assets = os.path.abspath(assets_dir)
    try:
        return os.path.commonpath([abs_path, abs_assets]) == abs_assets
    except ValueError:
        return False


def edit_video(asset_paths: list[str], instruction: str, output_path: str, assets_dir: str = None) -> dict:
    """Stub integration for browser-use/video-use. Copies the first asset to output as a placeholder."""
    if not asset_paths:
        return {"success": False, "error": "No raw assets provided"}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    first = asset_paths[0]
    abs_first = os.path.abspath(first)

    if assets_dir is None:
        assets_dir = os.path.abspath(os.getenv("ASSETS_DIR", "/app/data/assets"))

    if not _is_under_assets(abs_first, assets_dir):
        return {"success": False, "error": f"Asset path is not under ASSETS_DIR: {first}"}

    if not os.path.exists(abs_first):
        return {"success": False, "error": f"Asset not found: {first}"}

    # TODO: replace with real video-use/browser-use automation.
    Path(output_path).write_bytes(Path(abs_first).read_bytes())
    return {"success": True, "output_path": output_path}
