"""Translation controller: HTTP boundary for translation models (public and
admin) and translation jobs (text and archive)."""

from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas import (
    TranslationJobCreateRequest,
    TranslationModelResponse,
    TranslationModelUpdateRequest,
)
from app.services import translation_service
from app.services.app_settings_service import get_settings_row

router = APIRouter(prefix="/api/translation", tags=["translation"])
admin_models_router = APIRouter(prefix="/api/admin/translation-models", tags=["admin-translation-models"])


# ------------------------------------------------- models (public/admin) ---


@router.get("/models")
def list_enabled_translation_models(
    session: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Directions offered to the user (model downloaded and enabled)."""
    return [
        {"direction": m.direction.value}
        for m in translation_service.list_enabled_models(session)
    ]


@admin_models_router.get("", response_model=List[TranslationModelResponse])
def list_translation_models(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return translation_service.list_models_with_rows_ensured(session)


@admin_models_router.post("/{direction}/download", status_code=status.HTTP_202_ACCEPTED)
def request_translation_model_download(
    direction: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    translation_service.request_model_download(session, direction)
    return {"detail": f"Téléchargement du modèle '{direction}' déclenché"}


@admin_models_router.delete("/{direction}", status_code=status.HTTP_202_ACCEPTED)
def request_translation_model_deletion(
    direction: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    translation_service.request_model_deletion(session, direction)
    return {"detail": f"Suppression du modèle '{direction}' déclenchée"}


@admin_models_router.patch("/{direction}", response_model=TranslationModelResponse)
def update_translation_model(
    direction: str,
    payload: TranslationModelUpdateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return translation_service.update_model(session, direction, payload.is_enabled)


# ------------------------------------------------------- jobs (text mode) ---


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_text_job(
    payload: TranslationJobCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = translation_service.create_text_job(
        session, current_user, payload.direction, payload.text
    )
    return translation_service.job_to_response(job, get_settings_row(session))


# ----------------------------------------------------- jobs (archive mode) ---


@router.post("/jobs/archive", status_code=status.HTTP_201_CREATED)
async def create_archive_job(
    file: UploadFile = File(...),
    direction: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = await translation_service.create_archive_job(
        session, current_user, direction, file.filename, file
    )
    return translation_service.job_to_response(job, get_settings_row(session))


# ------------------------------------------------------------ jobs (common) ---


@router.get("/jobs")
def list_translation_jobs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    jobs = translation_service.list_jobs(session, current_user)
    limits = get_settings_row(session)
    return [translation_service.job_to_response(job, limits) for job in jobs]


@router.get("/jobs/{job_id}")
def get_translation_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = translation_service.get_owned_job(job_id, session, current_user)
    return translation_service.job_to_response(job, get_settings_row(session))


@router.get("/jobs/{job_id}/download")
def download_translation_job_result(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = translation_service.get_owned_job(job_id, session, current_user)
    payload = translation_service.read_result(job)

    if payload["kind"] == "content":
        return PlainTextResponse(
            content=payload["content"],
            media_type=payload["media_type"],
            headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
        )
    return FileResponse(
        path=payload["path"],
        media_type=payload["media_type"],
        filename=payload["filename"],
    )


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_translation_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = translation_service.get_owned_job(job_id, session, current_user)
    translation_service.request_cancel(session, job)
    return {"detail": "Annulation demandée"}


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_translation_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = translation_service.get_owned_job(job_id, session, current_user)
    translation_service.delete_job(session, job)
