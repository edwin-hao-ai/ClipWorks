import os
import shutil
from fastapi import FastAPI

ASSETS_DIR = os.getenv("ASSETS_DIR", "/app/data/assets")
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
