from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(
    session_user_id: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not session_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(User).filter(User.id == session_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/mock-login")
def mock_login(provider: str, response: Response, db: Session = Depends(get_db)):
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
    response.set_cookie(
        key="session_user_id",
        value=user.id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"user": UserOut.model_validate(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": UserOut.model_validate(user)}
