"""Whisper models controller: HTTP boundary for model administration
(admin) and the public selector endpoint."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas import (
    EnabledModelResponse,
    WhisperModelResponse,
    WhisperModelUpdateRequest,
)
from app.services import whisper_model_service

router = APIRouter(prefix="/api/admin/whisper-models", tags=["admin-whisper-models"])

# Public endpoint (any authenticated user): models usable for a
# transcription, offered in the dashboard selector.
public_router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=List[WhisperModelResponse])
def list_models(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return whisper_model_service.list_models_with_rows_ensured(session)


@router.post("/{model_name}/download", status_code=status.HTTP_202_ACCEPTED)
def request_model_download(
    model_name: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    whisper_model_service.request_download(session, model_name)
    return {"detail": f"Téléchargement du modèle '{model_name}' déclenché"}


@router.delete("/{model_name}", status_code=status.HTTP_202_ACCEPTED)
def request_model_deletion(
    model_name: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    whisper_model_service.request_deletion(session, model_name)
    return {"detail": f"Suppression du modèle '{model_name}' déclenchée"}


@router.patch("/{model_name}", response_model=WhisperModelResponse)
def update_model(
    model_name: str,
    payload: WhisperModelUpdateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return whisper_model_service.update_model(
        session, model_name, payload.is_enabled, payload.is_default
    )


@public_router.get("", response_model=List[EnabledModelResponse])
def list_enabled_models(
    session: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Models offered to users: downloaded AND enabled by the admin."""
    return whisper_model_service.list_enabled_models(session)
