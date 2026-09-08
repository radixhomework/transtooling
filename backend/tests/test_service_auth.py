"""Unit tests for the auth service, called directly (no HTTP layer)."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.database import engine
from app.core.rate_limit import is_locked_out, register_failed_attempt, reset_attempts
from app.core.security import decode_token, hash_password
from app.models.user import User, UserRole
from app.services import auth_service

PASSWORD = "UnitPass123"


@pytest.fixture()
def db_session(isolated_catalog):
    with Session(engine) as session:
        yield session


@pytest.fixture()
def unit_user(db_session):
    """Dedicated user row so tests never touch the shared admin account."""
    login_name = "unit-auth-user"
    user = db_session.exec(select(User).where(User.login == login_name)).first()
    if not user:
        user = User(login=login_name, password_hash=hash_password(PASSWORD), role=UserRole.user)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    yield user
    reset_attempts(login_name)


def test_login_success_returns_valid_token_pair(db_session, unit_user):
    tokens = auth_service.login(db_session, unit_user.login, PASSWORD)

    assert tokens.token_type == "bearer"
    payload = decode_token(tokens.access_token)
    assert payload["type"] == "access"
    assert payload["sub"] == str(unit_user.id)
    assert payload["role"] == UserRole.user.value

    refresh_payload = decode_token(tokens.refresh_token)
    assert refresh_payload["type"] == "refresh"


def test_login_wrong_password_raises_401(db_session, unit_user):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.login(db_session, unit_user.login, "WrongPass999")
    assert exc_info.value.status_code == 401


def test_login_unknown_user_raises_401(db_session):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.login(db_session, "no-such-user-unit", PASSWORD)
    assert exc_info.value.status_code == 401


def test_login_records_failed_attempts_and_locks_out(db_session, unit_user):
    for _ in range(5):
        with pytest.raises(HTTPException):
            auth_service.login(db_session, unit_user.login, "WrongPass999")

    assert is_locked_out(unit_user.login)

    # Even the correct password is refused while locked out.
    with pytest.raises(HTTPException) as exc_info:
        auth_service.login(db_session, unit_user.login, PASSWORD)
    assert exc_info.value.status_code == 429


def test_login_successful_attempt_resets_the_counter(db_session, unit_user):
    register_failed_attempt(unit_user.login)
    reset_attempts(unit_user.login)

    auth_service.login(db_session, unit_user.login, PASSWORD)
    assert not is_locked_out(unit_user.login)


def test_login_rejects_disabled_account(db_session, unit_user):
    unit_user.is_active = False
    db_session.add(unit_user)
    db_session.commit()
    try:
        with pytest.raises(HTTPException) as exc_info:
            auth_service.login(db_session, unit_user.login, PASSWORD)
        assert exc_info.value.status_code == 403
    finally:
        unit_user.is_active = True
        db_session.add(unit_user)
        db_session.commit()


def test_refresh_returns_new_token_pair(db_session, unit_user):
    tokens = auth_service.login(db_session, unit_user.login, PASSWORD)
    refreshed = auth_service.refresh(db_session, tokens.refresh_token)

    payload = decode_token(refreshed.access_token)
    assert payload["sub"] == str(unit_user.id)


def test_refresh_rejects_an_access_token(db_session, unit_user):
    tokens = auth_service.login(db_session, unit_user.login, PASSWORD)
    with pytest.raises(HTTPException) as exc_info:
        auth_service.refresh(db_session, tokens.access_token)
    assert exc_info.value.status_code == 401


def test_refresh_rejects_garbage_token(db_session):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.refresh(db_session, "not-a-jwt")
    assert exc_info.value.status_code == 401


def test_change_password_updates_hash_and_old_password_stops_working(db_session, unit_user):
    auth_service.change_password(db_session, unit_user, PASSWORD, "NewPass456")

    db_session.refresh(unit_user)
    with pytest.raises(HTTPException):
        auth_service.login(db_session, unit_user.login, PASSWORD)

    tokens = auth_service.login(db_session, unit_user.login, "NewPass456")
    assert tokens.access_token


def test_change_password_rejects_wrong_current_password(db_session, unit_user):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.change_password(db_session, unit_user, "WrongPass999", "NewPass456")
    assert exc_info.value.status_code == 400
