from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, RenderJob, Composition
import time

router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


def mock_render_task(job_id: str, project_id: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        if job:
            job.status = "running"
            db.commit()
            for i in range(1, 6):
                time.sleep(1)
                job.progress = i * 20
                db.commit()
            job.status = "completed"
            job.progress = 100
            job.output_url = f"/api/static/{project_id}/output.mp4"
            job.html_output_url = f"/api/static/{project_id}/index.html"
            db.commit()
    finally:
        db.close()


@router.post("/generate")
def generate_video(project_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"error": "not found"}

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
def get_render(job_id: str, db: Session = Depends(get_db)):
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job:
        return {"error": "not found"}
    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "output_url": job.output_url,
        "html_output_url": job.html_output_url,
        "error_message": job.error_message,
    }
