from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import MediaAsset, Project
import os
import shutil

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])

UPLOAD_DIR = "data/assets"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/")
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return db.query(MediaAsset).filter(MediaAsset.project_id == project_id).all()


@router.post("/")
def upload_asset(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1]
    asset_id = os.urandom(8).hex()
    local_path = os.path.join(UPLOAD_DIR, f"{asset_id}{ext}")
    with open(local_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    asset_type = "image"
    if ext.lower() in [".mp4", ".mov", ".webm"]:
        asset_type = "video"
    elif ext.lower() in [".mp3", ".wav", ".aac"]:
        asset_type = "audio"

    asset = MediaAsset(
        project_id=project_id,
        type=asset_type,
        source="upload",
        original_url=file.filename,
        local_path=local_path,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
