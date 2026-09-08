"""Business logic for authentication: login, token refresh, password change."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from jose import JWTError
from sqlmodel import Session, select

from app.core.rate_limit import is_locked_out, register_failed_attempt, reset_attempts
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas import TokenResponse


def login(session: Session, login_name: str, password: str) -> TokenResponse:
    if is_locked_out(login_name):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives échouées. Réessayez dans quelques minutes.",
        )

    user = session.exec(select(User).where(User.login == login_name)).first()

    if not user or not verify_password(password, user.password_hash):
        register_failed_attempt(login_name)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé",
        )

    reset_attempts(login_name)

    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()

    return _build_token_pair(user)


def refresh(session: Session, refresh_token: str) -> TokenResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token invalide ou expiré",
    )
    try:
        decoded = decode_token(refresh_token)
        if decoded.get("type") != "refresh":
            raise credentials_exception
        user_id = decoded.get("sub")
    except JWTError:
        raise credentials_exception

    user = session.get(User, int(user_id)) if user_id else None
    if not user or not user.is_active:
        raise credentials_exception

    return _build_token_pair(user)


def change_password(session: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()


def _build_token_pair(user: User) -> TokenResponse:
    access_token = create_access_token(subject=str(user.id), role=user.role.value)
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
