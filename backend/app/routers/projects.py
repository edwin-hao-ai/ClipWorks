from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Project, Composition, User, Track, Clip
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_or_create_demo_user(db: Session) -> User:
    user = db.query(User).first()
    if user:
        return user
    user = User(
        email="demo@google.com",
        name="Demo Google",
        avatar_url="https://api.dicebear.com/7.x/avataaars/svg?seed=google",
        provider="google",
        provider_id="google_123",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("/", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    user = _get_or_create_demo_user(db)
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
def get_project(project_id: str, db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.id == project_id).first()


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
    return {"deleted": True}
