"""Users controller: HTTP boundary for account administration endpoints."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas import (
    AdminResetPasswordRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("", response_model=List[UserResponse])
def list_users(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return user_service.list_users(session)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return user_service.create_user(session, payload.login, payload.password, payload.role)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return user_service.update_user(session, user_id, payload.is_active, payload.role)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    user_service.reset_password(session, user_id, payload.new_password)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    user_service.delete_user(session, user_id, admin)
