import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Project, Composition


def seed(db: Session = None) -> None:
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        user = db.query(User).filter(User.email == "demo@google.com").first()
        if not user:
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
            print(f"Created user {user.id}")

        project = db.query(Project).filter(Project.user_id == user.id).first()
        if not project:
            project = Project(
                user_id=user.id,
                title="Demo Project",
                source_url="https://example.com",
                source_type="url",
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
            print(f"Created project {project.id} with composition {composition.id}")
        else:
            print(f"Project already exists: {project.id}")
    finally:
        if close:
            db.close()


if __name__ == "__main__":
    seed()
