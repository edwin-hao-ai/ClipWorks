import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.config import ASSETS_DIR
from app.database import get_db
from app.models import Project, Composition, User, Track, Clip, MediaAsset
from app.routers.auth import get_current_user
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])

_FORMAT_DIMS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def _dims_from_format(fmt: str | None) -> tuple[int, int]:
    return _FORMAT_DIMS.get(fmt or "16:9", (1920, 1080))


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


def _local_to_static(local_path: str | None) -> str | None:
    """容器内素材路径（.../data/assets/...）映射为同源静态 URL /api/static/...。"""
    if not local_path:
        return None
    marker = 'data/assets/'
    idx = local_path.find(marker)
    if idx >= 0:
        return '/api/static/' + local_path[idx + len(marker):]
    return None


def _attach_covers(db: Session, projects: list[Project]) -> list[Project]:
    """为每个项目挑第一张图片素材作为封面（优先本地静态副本，离线也能显示）。"""
    ids = [p.id for p in projects]
    if not ids:
        return projects
    rows = (
        db.query(MediaAsset.project_id, MediaAsset.original_url, MediaAsset.local_path)
        .filter(MediaAsset.project_id.in_(ids), MediaAsset.type == 'image')
        .order_by(MediaAsset.created_at.asc())
        .all()
    )
    covers: dict[str, str] = {}
    for pid, original, local in rows:
        if pid in covers:
            continue
        url = _local_to_static(local) or original
        if url:
            covers[pid] = url
    for p in projects:
        p.cover_url = covers.get(p.id)
    return projects


@router.get("/", response_model=List[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()
    return _attach_covers(db, projects)


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = Project(
        user_id=user.id,
        title=payload.title,
        source_url=payload.source_url,
        source_type=payload.source_type,
        status="draft",
        target_format=payload.target_format or "16:9",
        target_duration=payload.target_duration or 30,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    width, height = _dims_from_format(project.target_format)
    composition = Composition(
        project_id=project.id,
        width=width,
        height=height,
        duration=30,
        fps=30,
    )
    db.add(composition)
    db.commit()
    db.refresh(composition)

    text_track = Track(composition_id=composition.id, type='text', index=0, name='字幕')
    video_track = Track(composition_id=composition.id, type='video', index=1, name='画面')
    db.add_all([text_track, video_track])
    db.flush()

    db.add(Clip(track_id=video_track.id, start_time=0, duration=10, position={}))
    db.add(Clip(track_id=text_track.id, start_time=1, duration=5, text_content='ClipWorks'))
    db.commit()

    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .options(
            joinedload(Project.composition)
            .joinedload(Composition.tracks)
            .joinedload(Track.clips)
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    if payload.title is not None:
        project.title = payload.title
    if payload.source_url is not None:
        project.source_url = payload.source_url
    if payload.target_duration is not None:
        project.target_duration = payload.target_duration
    if payload.target_format is not None:
        project.target_format = payload.target_format
        width, height = _dims_from_format(payload.target_format)
        if project.composition:
            project.composition.width = width
            project.composition.height = height
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_project(project_id, user, db)
    db.delete(project)
    db.commit()
    # 级联删除项目素材目录（含上传文件、渲染输出、转码代理），
    # 避免「DB 删了、磁盘文件残留」的孤立目录泄漏。
    assets_dir = os.path.join(ASSETS_DIR, project_id)
    if os.path.abspath(assets_dir).startswith(os.path.abspath(ASSETS_DIR)):
        shutil.rmtree(assets_dir, ignore_errors=True)
    return {"deleted": True}
