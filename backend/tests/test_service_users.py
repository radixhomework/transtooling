"""Unit tests for the user service, called directly (no HTTP layer)."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.database import engine
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.services import user_service


@pytest.fixture()
def db_session(isolated_catalog):
    with Session(engine) as session:
        yield session


@pytest.fixture()
def unit_admin(db_session):
    """A dedicated admin row to pass as the acting administrator."""
    login_name = "unit-users-admin"
    admin = db_session.exec(select(User).where(User.login == login_name)).first()
    if not admin:
        admin = User(
            login=login_name,
            password_hash=hash_password("AdminPass123"),
            role=UserRole.admin,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    return admin


def _make_user(db_session, login_name, role=UserRole.user):
    user = db_session.exec(select(User).where(User.login == login_name)).first()
    if not user:
        user = User(login=login_name, password_hash=hash_password("SomePass123"), role=role)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_list_users_returns_all_accounts(db_session, unit_admin):
    _make_user(db_session, "unit-list-a")
    _make_user(db_session, "unit-list-b")

    logins = {u.login for u in user_service.list_users(db_session)}
    assert {"unit-list-a", "unit-list-b"} <= logins


def test_create_user_persists_hashed_credentials(db_session):
    created = user_service.create_user(db_session, "unit-created-user", "CreatePass123", UserRole.user)

    assert created.id is not None
    assert created.role == UserRole.user
    stored = db_session.get(User, created.id)
    assert verify_password("CreatePass123", stored.password_hash)


def test_create_user_rejects_duplicate_login(db_session):
    _make_user(db_session, "unit-duplicate-user")
    with pytest.raises(HTTPException) as exc_info:
        user_service.create_user(db_session, "unit-duplicate-user", "OtherPass123", UserRole.user)
    assert exc_info.value.status_code == 400


def test_update_user_changes_active_and_role(db_session):
    user = _make_user(db_session, "unit-update-user")

    updated = user_service.update_user(db_session, user.id, is_active=False, role=UserRole.admin)
    assert updated.is_active is False
    assert updated.role == UserRole.admin


def test_update_user_missing_raises_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        user_service.update_user(db_session, 999999999, is_active=False, role=None)
    assert exc_info.value.status_code == 404


def test_reset_password(db_session):
    user = _make_user(db_session, "unit-reset-user")
    user_service.reset_password(db_session, user.id, "ResetPass123")

    db_session.refresh(user)
    assert verify_password("ResetPass123", user.password_hash)


def test_reset_password_missing_user_raises_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        user_service.reset_password(db_session, 999999999, "ResetPass123")
    assert exc_info.value.status_code == 404


def test_delete_user_removes_the_account(db_session, unit_admin):
    user = _make_user(db_session, "unit-delete-user")
    user_service.delete_user(db_session, user.id, unit_admin)
    assert db_session.get(User, user.id) is None


def test_delete_user_cannot_delete_self(db_session, unit_admin):
    with pytest.raises(HTTPException) as exc_info:
        user_service.delete_user(db_session, unit_admin.id, unit_admin)
    assert exc_info.value.status_code == 400
