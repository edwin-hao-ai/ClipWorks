import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, RenderJob, User
from app.routers.auth import get_current_user
from app.tasks.render_task import render_video_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


def _require_project(project_id: str, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return project


@router.post("/generate", status_code=202)
def generate_video(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _require_project(project_id, user, db)
    project.status = "generating"
    db.commit()

    composition_id = project.composition.id if project.composition else None
    job = RenderJob(project_id=project_id, composition_id=composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    render_video_task.delay(job.id, project_id)
    return {"job_id": job.id, "status": "queued"}


@router.post("/agent-generate", status_code=202)
def agent_generate_video(
    project_id: str,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate video using the Agent, optionally guided by a user prompt and engine choice."""
    project = _require_project(project_id, user, db)
    prompt = data.get("prompt") if isinstance(data, dict) else None
    engine = data.get("engine") if isinstance(data, dict) else None

    project.status = "generating"
    db.commit()

    composition_id = project.composition.id if project.composition else None
    job = RenderJob(project_id=project_id, composition_id=composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    render_video_task.delay(job.id, project_id, prompt, engine)
    return {"job_id": job.id, "status": "queued"}


@router.get("/", response_model=list[dict])
def list_renders(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _require_project(project_id, user, db)
    jobs = (
        db.query(RenderJob)
        .filter(RenderJob.project_id == project.id)
        .order_by(RenderJob.created_at.desc())
        .all()
    )
    return [
        {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "output_url": job.output_url,
            "html_output_url": job.html_output_url,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in jobs
    ]


@router.get("/{job_id}")
def get_render(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    if job.project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this project")
    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "output_url": job.output_url,
        "html_output_url": job.html_output_url,
        "error_message": job.error_message,
    }
