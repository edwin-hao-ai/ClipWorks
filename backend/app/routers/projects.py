from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Project, Composition, User, Track, Clip
from app.routers.auth import get_current_user
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


@router.get("/", response_model=List[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = Project(
        user_id=user.id,
        title=payload.title,
        source_url=payload.source_url,
        source_type=payload.source_type,
        status="draft",
        target_format="16:9",
        target_duration=30,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    composition = Composition(
        project_id=project.id,
        width=1920,
        height=1080,
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
    return _require_project(project_id, user, db)


@router.delete("/{project_id}")
def delete_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_project(project_id, user, db)
    db.delete(project)
    db.commit()
    return {"deleted": True}
