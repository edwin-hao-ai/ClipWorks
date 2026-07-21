from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import User


def check_credits(user: User) -> None:
    """Hard gate: refuse to queue a new render when the user has no credits left.

    Returns HTTP 402 so the frontend can render an inline upgrade prompt instead
    of silently falling back to a placeholder or blowing up the workspace.
    """
    if (user.credits or 0) <= 0:
        raise HTTPException(status_code=402, detail="额度不足，请前往计费页升级套餐")


def deduct_credits(db: Session, user_id: str, amount: int = 1) -> bool:
    """Atomically deduct credits from a user.

    Performs a single ``UPDATE users SET credits = credits - :amount
    WHERE id = :id AND credits >= :amount`` so concurrent render requests
    cannot over-deduct. Returns ``True`` when the row was updated (deduction
    succeeded) and ``False`` when the user had insufficient credits.
    """
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.credits >= amount)
        .values(credits=User.credits - amount)
    )
    return result.rowcount == 1
