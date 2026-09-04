import json
import os
import uuid
import zipfile
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session, select

from app.core.config import settings as app_config
from app.core.database import get_session
from app.core.deps import get_current_user, require_admin
from app.models.app_settings import AppSettings
from app.models.translation import (
    TranslationDirection,
    TranslationJob,
    TranslationJobStatus,
    TranslationJobType,
    TranslationModel,
    TranslationModelStatus,
)
from app.models.user import User, UserRole
from app.schemas import (
    TranslationJobCreateRequest,
    TranslationModelResponse,
    TranslationModelUpdateRequest,
)

router = APIRouter(prefix="/api/translation", tags=["translation"])
admin_models_router = APIRouter(prefix="/api/admin/translation-models", tags=["admin-translation-models"])

AVAILABLE_DIRECTIONS = ["fr-en", "en-fr"]


# ---------------------------------------------------------------- helpers ---


def _get_settings_row(session: Session) -> AppSettings:
    row = session.get(AppSettings, 1)
    if not row:
        row = AppSettings(
            id=1,
            max_file_size_mb=app_config.default_max_file_size_mb,
            max_duration_min=app_config.default_max_duration_min,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def _get_enabled_model(session: Session, direction: str) -> TranslationModel | None:
    return session.exec(
        select(TranslationModel).where(
            TranslationModel.direction == direction,
            TranslationModel.is_enabled == True,  # noqa: E712
            TranslationModel.status == TranslationModelStatus.downloaded,
        )
    ).first()


def _job_to_response(job: TranslationJob, settings_row: AppSettings) -> dict:
    """Translation job response: truncated result preview according to
    preview_truncate_chars (the full text remains downloadable)."""
    result_preview = None
    result_truncated = False
    if job.result_text:
        limit = settings_row.preview_truncate_chars
        result_preview = job.result_text[:limit]
        result_truncated = len(job.result_text) > limit

    return {
        "id": job.id,
        "user_id": job.user_id,
        "job_type": job.job_type.value,
        "direction": job.direction.value,
        "status": job.status.value,
        "error_message": job.error_message,
        "stopped_reason": job.stopped_reason,
        "result_preview": result_preview,
        "result_truncated": result_truncated,
        "report": json.loads(job.report_json) if job.report_json else None,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


def _get_owned_job(
    job_id: int,
    session: Session,
    current_user: User,
) -> TranslationJob:
    job = session.get(TranslationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de traduction introuvable")
    if current_user.role != UserRole.admin and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return job


# ------------------------------------------------- models (public/admin) ---


@router.get("/models")
def list_enabled_translation_models(
    session: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Directions offered to the user (model downloaded and enabled)."""
    models = session.exec(
        select(TranslationModel).where(
            TranslationModel.is_enabled == True,  # noqa: E712
            TranslationModel.status == TranslationModelStatus.downloaded,
        )
    ).all()
    return [{"direction": m.direction.value} for m in models]


@admin_models_router.get("", response_model=List[TranslationModelResponse])
def list_translation_models(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    existing = {m.direction: m for m in session.exec(select(TranslationModel)).all()}
    for direction in AVAILABLE_DIRECTIONS:
        if direction not in existing:
            model = TranslationModel(
                direction=direction, status=TranslationModelStatus.not_downloaded
            )
            session.add(model)
            existing[direction] = model
    session.commit()
    return session.exec(select(TranslationModel)).all()


@admin_models_router.post("/{direction}/download", status_code=status.HTTP_202_ACCEPTED)
def request_translation_model_download(
    direction: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    if direction not in AVAILABLE_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Direction inconnue (fr-en ou en-fr)")

    model = session.exec(
        select(TranslationModel).where(TranslationModel.direction == direction)
    ).first()
    if not model:
        model = TranslationModel(direction=direction)

    if model.status == TranslationModelStatus.downloaded:
        raise HTTPException(status_code=400, detail="Modèle déjà téléchargé")

    # The transition to "downloading" is handled by the translation-worker.
    model.status = TranslationModelStatus.downloading
    model.download_progress = 0
    model.error_message = None
    session.add(model)
    session.commit()
    return {"detail": f"Téléchargement du modèle '{direction}' déclenché"}


@admin_models_router.delete("/{direction}", status_code=status.HTTP_202_ACCEPTED)
def request_translation_model_deletion(
    direction: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    model = session.exec(
        select(TranslationModel).where(TranslationModel.direction == direction)
    ).first()
    if not model or model.status != TranslationModelStatus.downloaded:
        raise HTTPException(status_code=400, detail="Modèle non téléchargé")

    # The physical deletion is performed by the translation-worker.
    model.status = TranslationModelStatus.not_downloaded
    model.is_enabled = False
    model.download_progress = None
    model.disk_size_mb = None
    session.add(model)
    session.commit()
    return {"detail": f"Suppression du modèle '{direction}' déclenchée"}


@admin_models_router.patch("/{direction}", response_model=TranslationModelResponse)
def update_translation_model(
    direction: str,
    payload: TranslationModelUpdateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    model = session.exec(
        select(TranslationModel).where(TranslationModel.direction == direction)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    if payload.is_enabled is not None:
        if payload.is_enabled and model.status != TranslationModelStatus.downloaded:
            raise HTTPException(
                status_code=400,
                detail="Le modèle doit être téléchargé avant d'être activé",
            )
        model.is_enabled = payload.is_enabled

    session.add(model)
    session.commit()
    session.refresh(model)
    return model


# ------------------------------------------------------- jobs (text mode) ---


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_text_job(
    payload: TranslationJobCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    limits = _get_settings_row(session)

    if payload.direction not in AVAILABLE_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Direction inconnue (fr-en ou en-fr)")

    if len(payload.text) > limits.max_text_length_chars:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Texte trop long ({len(payload.text)} caractères, "
                f"max {limits.max_text_length_chars})"
            ),
        )

    if not _get_enabled_model(session, payload.direction):
        raise HTTPException(
            status_code=503,
            detail="Aucun modèle de traduction actif pour cette direction. Contactez un administrateur.",
        )

    job = TranslationJob(
        user_id=current_user.id,
        job_type=TranslationJobType.text,
        direction=payload.direction,
        source_text=payload.text,
        status=TranslationJobStatus.pending,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return _job_to_response(job, limits)


# ----------------------------------------------------- jobs (archive mode) ---


def _validate_zip_safety(path: str, limits: AppSettings) -> None:
    """Security checks on the archive BEFORE any processing: readable
    archive, no malicious paths (zip-slip), file-count and uncompressed-size
    limits (zip bomb)."""
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Archive ZIP invalide ou corrompue") from exc

    if len(infos) > limits.max_archive_files_count:
        raise HTTPException(
            status_code=413,
            detail=f"Archive contenant trop de fichiers ({len(infos)}, max {limits.max_archive_files_count})",
        )

    total_uncompressed = sum(info.file_size for info in infos)
    if total_uncompressed > limits.max_archive_uncompressed_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Taille décompressée trop importante "
                f"({total_uncompressed // (1024 * 1024)} Mo, max {limits.max_archive_uncompressed_mb} Mo)"
            ),
        )

    for info in infos:
        name = info.filename
        if info.flag_bits & 0x1:
            raise HTTPException(
                status_code=400,
                detail=f"Fichier chiffré non supporté : {name}",
            )
        # Zip-slip: absolute paths, Windows separators, or traversals
        # outside the target directory.
        norm = os.path.normpath(name)
        if (
            "\\" in name
            or os.path.isabs(norm)
            or norm == ".."
            or norm.startswith("../")
            or norm.startswith("..\\")
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Chemin de fichier invalide dans l'archive : {name}",
            )


@router.post("/jobs/archive", status_code=status.HTTP_201_CREATED)
async def create_archive_job(
    file: UploadFile = File(...),
    direction: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if direction not in AVAILABLE_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Direction inconnue (fr-en ou en-fr)")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".zip":
        raise HTTPException(status_code=400, detail="Seules les archives ZIP (.zip) sont acceptées")

    limits = _get_settings_row(session)
    max_size_bytes = limits.max_archive_size_mb * 1024 * 1024

    if not _get_enabled_model(session, direction):
        raise HTTPException(
            status_code=503,
            detail="Aucun modèle de traduction actif pour cette direction. Contactez un administrateur.",
        )

    os.makedirs(app_config.translation_tmp_path, exist_ok=True)
    tmp_filename = f"{uuid.uuid4().hex}.zip"
    tmp_path = os.path.join(app_config.translation_tmp_path, tmp_filename)

    size = 0
    try:
        with open(tmp_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Archive trop volumineuse (max {limits.max_archive_size_mb} Mo)",
                    )
                out_file.write(chunk)

        _validate_zip_safety(tmp_path, limits)

        job = TranslationJob(
            user_id=current_user.id,
            job_type=TranslationJobType.archive,
            direction=direction,
            archive_tmp_filename=tmp_filename,
            status=TranslationJobStatus.pending,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return _job_to_response(job, limits)

    except HTTPException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ------------------------------------------------------------ jobs (common) ---


@router.get("/jobs")
def list_translation_jobs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    limits = _get_settings_row(session)
    query = select(TranslationJob)
    if current_user.role != UserRole.admin:
        query = query.where(TranslationJob.user_id == current_user.id)
    jobs = session.exec(query.order_by(TranslationJob.created_at.desc())).all()  # type: ignore[arg-type]
    return [_job_to_response(job, limits) for job in jobs]


@router.get("/jobs/{job_id}")
def get_translation_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    limits = _get_settings_row(session)
    job = _get_owned_job(job_id, session, current_user)
    return _job_to_response(job, limits)


@router.get("/jobs/{job_id}/download")
def download_translation_job_result(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(job_id, session, current_user)
    if job.status != TranslationJobStatus.done:
        raise HTTPException(status_code=409, detail="Traduction non terminée")

    if job.job_type == TranslationJobType.text:
        return PlainTextResponse(
            content=job.result_text or "",
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="traduction.txt"'},
        )

    if not job.result_zip_path or not os.path.exists(job.result_zip_path):
        raise HTTPException(status_code=404, detail="Résultat introuvable")
    return FileResponse(
        path=job.result_zip_path,
        media_type="application/zip",
        filename="traduction.zip",
    )


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_translation_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(job_id, session, current_user)
    if job.status not in (
        TranslationJobStatus.pending,
        TranslationJobStatus.processing,
        TranslationJobStatus.cancelling,
    ):
        raise HTTPException(status_code=409, detail="Ce job ne peut plus être annulé")

    job.cancel_requested = True
    session.add(job)
    session.commit()
    return {"detail": "Annulation demandée"}


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_translation_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(job_id, session, current_user)

    if job.result_zip_path and os.path.exists(job.result_zip_path):
        os.remove(job.result_zip_path)
    if job.archive_tmp_filename:
        archive_path = os.path.join(
            app_config.translation_tmp_path, job.archive_tmp_filename
        )
        if os.path.exists(archive_path):
            os.remove(archive_path)

    session.delete(job)
    session.commit()
