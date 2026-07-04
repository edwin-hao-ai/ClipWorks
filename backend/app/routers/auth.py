from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/mock-login")
def mock_login(provider: str, db: Session = Depends(get_db)):
    email = f"demo@{provider}.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=f"Demo {provider.title()}",
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={provider}",
            provider=provider,
            provider_id=f"{provider}_123",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"user": UserOut.model_validate(user)}


@router.get("/me")
def me(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return mock_login("google", db)
    return {"user": UserOut.model_validate(user)}
