from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import MediaAsset, Project, User
from app.routers.auth import get_current_user
import logging
import os
import re
import shutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])

UPLOAD_DIR = "data/assets"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
    ".mp3",
    ".wav",
    ".aac",
    ".ogg",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
}


def _sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename).strip()
    base = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    return base or "upload"


def _get_asset_type(ext: str) -> str:
    ext_lower = ext.lower()
    if ext_lower in {".mp4", ".mov", ".webm", ".mkv"}:
        return "video"
    if ext_lower in {".mp3", ".wav", ".aac", ".ogg"}:
        return "audio"
    if ext_lower in {".ttf", ".otf", ".woff", ".woff2"}:
        return "font"
    return "image"


def _resolve_under_upload_dir(local_path: str | None) -> str | None:
    """Return the absolute path if it lives under UPLOAD_DIR, else None.

    删除磁盘文件前先做路径穿越校验，避免 local_path 被篡改后删到目录外。
    """
    if not local_path:
        return None
    base = os.path.abspath(UPLOAD_DIR)
    candidate = os.path.abspath(local_path)
    try:
        if os.path.commonpath([base, candidate]) != base:
            return None
    except ValueError:
        return None
    return candidate


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


@router.get("/")
def list_assets(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_project(project_id, user, db)
    return db.query(MediaAsset).filter(MediaAsset.project_id == project_id).all()


@router.post("/", status_code=201)
def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_project(project_id, user, db)

    filename = _sanitize_filename(file.filename or "")
    ext = os.path.splitext(filename)[1].lower()
    if not ext or ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' is not allowed",
        )

    # Determine file size without reading the whole stream into memory.
    try:
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
    except Exception:
        size = None

    if size is not None and size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds maximum size of 50 MB")

    asset_id = os.urandom(8).hex()
    local_path = os.path.join(UPLOAD_DIR, f"{asset_id}{ext}")
    with open(local_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    asset = MediaAsset(
        project_id=project_id,
        type=_get_asset_type(ext),
        source="upload",
        original_url=filename,
        local_path=local_path,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_asset(
    project_id: str,
    asset_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_project(project_id, user, db)

    # 必须确认素材确实属于该项目，避免越权删除其它项目的素材。
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
    if not asset or asset.project_id != project_id:
        raise HTTPException(status_code=404, detail="Asset not found")

    # 仅在文件位于上传目录内时才删除磁盘文件；文件已不存在则忽略。
    disk_path = _resolve_under_upload_dir(asset.local_path)
    if disk_path:
        try:
            os.remove(disk_path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("Failed to remove asset file %s: %s", disk_path, exc)

    db.delete(asset)
    db.commit()
    return {"ok": True}
