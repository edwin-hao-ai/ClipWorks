from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, RenderJob, Project
from app.schemas import UserOut, UserStatsOut, UserUpdateIn

router = APIRouter(prefix="/auth", tags=["auth"])

# 演示环境的套餐额度（与前端计费页 PLAN_META 的「次/月」对应）。
PLAN_CREDITS = {'free': 10, 'pro': 200, 'enterprise': 9999}


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
            credits=10,
            plan='free',
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


@router.post("/logout")
def logout(response: Response):
    # 删除会话 cookie：必须与 set_cookie 使用相同的 path/samesite/httponly，
    # 否则浏览器会忽略删除请求，导致用户实际上仍处于登录状态。
    response.delete_cookie(
        key="session_user_id",
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"user": UserOut.model_validate(user)}


@router.put("/me")
def update_me(payload: UserUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 仅允许修改展示昵称与套餐（mock 计费切换）；邮箱/登录方式等身份字段不在此变更。
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.plan is not None and payload.plan != user.plan:
        user.plan = payload.plan
        # 演示环境没有真实支付：切换套餐即按套餐额度补足生成次数，
        # 否则额度耗尽后「升级套餐」的指引对用户是个死局。
        user.credits = PLAN_CREDITS.get(payload.plan, 10)
    db.commit()
    db.refresh(user)
    return {"user": UserOut.model_validate(user)}


@router.get("/me/stats", response_model=UserStatsOut)
def me_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    videos_generated = (
        db.query(RenderJob)
        .join(Project)
        .filter(Project.user_id == user.id, RenderJob.status == 'completed')
        .count()
    )
    return {
        "videos_generated": videos_generated,
        "remaining_credits": user.credits,
        "current_plan": user.plan,
    }
