import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User


def test_user_roundtrip(db_session):
    db_session.add(User(email="a@example.com", password_hash="x"))
    db_session.commit()
    user = db_session.scalars(select(User)).one()
    assert user.email == "a@example.com"
    assert user.is_active is True
    assert user.created_at is not None


def test_email_must_be_unique_ignoring_case(db_session):
    db_session.add(User(email="a@example.com", password_hash="x"))
    db_session.commit()
    db_session.add(User(email="A@Example.com", password_hash="y"))
    with pytest.raises(IntegrityError):
        db_session.commit()