import os
import shutil
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ASSETS_DIR = os.path.abspath(os.getenv("ASSETS_DIR", "/app/data/assets"))
app = FastAPI(title="ClipWorks Renderer")


def _has_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _command_succeeds(cmd: list[str], cwd: str | None = None, timeout: int = 10) -> bool:
    try:
        result = subprocess.run(cmd, capture_output=True, cwd=cwd, timeout=timeout)
        return result.returncode == 0
    except Exception:
        return False


def _has_chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return os.path.exists(p.chromium.executable_path)
    except Exception:
        return False


@app.get("/health")
def health():
    remotion_dir = os.path.join(os.path.dirname(__file__), "remotion")
    return {
        "status": "ok",
        "engines": {
            "hyperframes": _command_succeeds(["npx", "hyperframes", "--version"]),
            "remotion": _command_succeeds(["npx", "remotion", "--version"], cwd=remotion_dir),
            "video_use": _has_command("ffmpeg") and _has_chromium(),
        },
    }


class HyperFramesRequest(BaseModel):
    html_path: str
    output_path: str
    duration: int = 30
    fps: int = 30


class RemotionRequest(BaseModel):
    composition_path: str
    output_path: str


class VideoUseRequest(BaseModel):
    asset_paths: list[str]
    instruction: str
    output_path: str


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


@app.post("/render/remotion")
def render_remotion(req: RemotionRequest):
    if not _is_under_assets(req.composition_path) or not _is_under_assets(req.output_path):
        raise HTTPException(status_code=400, detail="Paths must be under ASSETS_DIR")

    os.makedirs(os.path.dirname(os.path.abspath(req.output_path)), exist_ok=True)
    remotion_dir = os.path.join(os.path.dirname(__file__), "remotion")

    cmd = [
        "npx", "remotion", "render", "Generic", req.output_path,
        "--props", req.composition_path,
        "--concurrency", "1",
    ]
    try:
        result = subprocess.run(cmd, cwd=remotion_dir, capture_output=True, text=True, timeout=300, check=False)
        if result.returncode != 0:
            return {"success": False, "output_url": None, "error": result.stderr or result.stdout or "Remotion render failed"}
        return {"success": True, "output_url": _relative_url(req.output_path), "error": None}
    except Exception as exc:
        return {"success": False, "output_url": None, "error": str(exc)}


@app.post("/render/video-use")
def render_video_use(req: VideoUseRequest):
    if not _is_under_assets(req.output_path):
        raise HTTPException(status_code=400, detail="Output path must be under ASSETS_DIR")

    for path in req.asset_paths:
        if not _is_under_assets(path):
            raise HTTPException(status_code=400, detail=f"Asset path must be under ASSETS_DIR: {path}")

    from video_use.edit_video import edit_video
    result = edit_video(req.asset_paths, req.instruction, req.output_path, assets_dir=ASSETS_DIR)
    if not result["success"]:
        return {"success": False, "output_url": None, "error": result["error"]}
    return {"success": True, "output_url": _relative_url(req.output_path), "error": None}
