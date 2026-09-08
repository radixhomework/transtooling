"""Application settings controller: HTTP boundary for the admin settings."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_admin
from app.models.user import User
from app.schemas import AppSettingsResponse, AppSettingsUpdateRequest
from app.services import app_settings_service

router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])


@router.get("", response_model=AppSettingsResponse)
def get_settings(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return app_settings_service.get_settings_row_or_raise(session)


@router.patch("", response_model=AppSettingsResponse)
def update_settings(
    payload: AppSettingsUpdateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return app_settings_service.update_settings(session, payload)
