from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Project, RenderJob, User
from app.routers.auth import get_current_user
import time

router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


def mock_render_task(job_id: str, project_id: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        project = db.query(Project).filter(Project.id == project_id).first()
        if not job or not project:
            return
        job.status = "running"
        db.commit()
        try:
            for i in range(1, 6):
                time.sleep(1)
                job.progress = i * 20
                db.commit()
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.output_url = "/api/static/sample.mp4"
            job.html_output_url = "/api/static/index.html"
            project.status = "ready"
            db.commit()
        except Exception as exc:
            db.rollback()
            job.status = "failed"
            job.error_message = str(exc)
            project.status = "failed"
            db.commit()
    finally:
        db.close()


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
    background_tasks: BackgroundTasks,
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

    background_tasks.add_task(mock_render_task, job.id, project_id)
    return {"job_id": job.id, "status": "queued"}


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
