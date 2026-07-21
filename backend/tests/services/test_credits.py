import pytest
from fastapi import HTTPException

from app.database import SessionLocal
from app.models import User
from app.services.credits import check_credits, deduct_credits


def test_check_credits_raises_when_zero():
    user = User(email="u1@example.com", credits=0)
    with pytest.raises(HTTPException) as exc_info:
        check_credits(user)
    assert exc_info.value.status_code == 402


def test_check_credits_raises_when_negative():
    user = User(email="u2@example.com", credits=-1)
    with pytest.raises(HTTPException) as exc_info:
        check_credits(user)
    assert exc_info.value.status_code == 402


def test_check_credits_passes_when_positive():
    user = User(email="u3@example.com", credits=1)
    check_credits(user)  # no exception


def test_deduct_credits_atomically_reduces_balance():
    db = SessionLocal()
    try:
        user = User(email="deduct@example.com", credits=3)
        db.add(user)
        db.commit()

        assert deduct_credits(db, user.id, amount=1) is True

        db.refresh(user)
        assert user.credits == 2
    finally:
        db.close()


def test_deduct_credits_fails_when_insufficient():
    db = SessionLocal()
    try:
        user = User(email="empty@example.com", credits=0)
        db.add(user)
        db.commit()

        assert deduct_credits(db, user.id, amount=1) is False

        db.refresh(user)
        assert user.credits == 0
    finally:
        db.close()


def test_deduct_credits_respects_amount():
    db = SessionLocal()
    try:
        user = User(email="amount@example.com", credits=2)
        db.add(user)
        db.commit()

        assert deduct_credits(db, user.id, amount=3) is False

        db.refresh(user)
        assert user.credits == 2
    finally:
        db.close()
