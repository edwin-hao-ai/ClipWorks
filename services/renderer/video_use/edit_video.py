import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def edit_video(asset_paths: list[str], instruction: str, output_path: str) -> dict:
    """Stub integration for browser-use/video-use. Copies the first asset to output as a placeholder."""
    if not asset_paths:
        return {"success": False, "error": "No raw assets provided"}

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    first = asset_paths[0]
    if not os.path.exists(first):
        return {"success": False, "error": f"Asset not found: {first}"}

    # TODO: replace with real video-use/browser-use automation.
    Path(output_path).write_bytes(Path(first).read_bytes())
    return {"success": True, "output_path": output_path}
