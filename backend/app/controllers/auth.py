"""Auth controller: HTTP boundary for authentication endpoints."""

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    return auth_service.login(session, payload.login, payload.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)):
    return auth_service.refresh(session, payload.refresh_token)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    auth_service.change_password(
        session, current_user, payload.current_password, payload.new_password
    )
