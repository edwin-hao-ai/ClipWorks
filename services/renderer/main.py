import os
import shutil
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ASSETS_DIR = os.path.abspath(os.getenv("ASSETS_DIR", "/app/data/assets"))
app = FastAPI(title="ClipWorks Renderer")


def _has_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "engines": {
            "hyperframes": _has_command("npx"),
            "remotion": _has_command("npx"),
            "video_use": _has_command("python3"),
        },
    }


class HyperFramesRequest(BaseModel):
    html_path: str
    output_path: str
    duration: int = 30
    fps: int = 30


def _relative_url(abs_path: str) -> str:
    abs_path = os.path.abspath(abs_path)
    if os.path.commonpath([abs_path, ASSETS_DIR]) != ASSETS_DIR:
        raise ValueError(f"Path {abs_path!r} is not under ASSETS_DIR {ASSETS_DIR!r}")
    rel = os.path.relpath(abs_path, ASSETS_DIR)
    return f"/api/static/{rel}"


def _is_under_assets(path: str) -> bool:
    abs_path = os.path.abspath(path)
    return os.path.commonpath([abs_path, ASSETS_DIR]) == ASSETS_DIR


@app.post("/render/hyperframes")
def render_hyperframes(req: HyperFramesRequest):
    if not _is_under_assets(req.html_path) or not _is_under_assets(req.output_path):
        raise HTTPException(status_code=400, detail="Paths must be under ASSETS_DIR")

    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)

    cmd = [
        "npx",
        "hyperframes",
        "render",
        "--duration",
        str(req.duration),
        "--fps",
        str(req.fps),
        req.html_path,
        req.output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
        if result.returncode != 0:
            return {
                "success": False,
                "output_url": None,
                "html_output_url": _relative_url(req.html_path),
                "error": result.stderr or result.stdout or "HyperFrames render failed",
            }
        return {
            "success": True,
            "output_url": _relative_url(req.output_path),
            "html_output_url": _relative_url(req.html_path),
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output_url": None, "html_output_url": _relative_url(req.html_path), "error": "Render timed out"}
    except FileNotFoundError:
        return {"success": False, "output_url": None, "html_output_url": _relative_url(req.html_path), "error": "HyperFrames CLI not found"}
