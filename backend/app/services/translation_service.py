"""Business logic for translation: model administration, text and archive
job creation, lifecycle and cleanup."""

import json
import os
import uuid
import zipfile

import aiofiles
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings as app_config
from app.models.app_settings import AppSettings
from app.models.translation import (
    TranslationJob,
    TranslationJobStatus,
    TranslationJobType,
    TranslationModel,
    TranslationModelStatus,
)
from app.models.user import User, UserRole
from app.services.app_settings_service import get_settings_row

AVAILABLE_DIRECTIONS = ["fr-en", "en-fr"]


# --------------------------------------------------------------- models ---


def list_enabled_models(session: Session) -> list[TranslationModel]:
    return session.exec(
        select(TranslationModel).where(
            TranslationModel.is_enabled == True,  # noqa: E712
            TranslationModel.status == TranslationModelStatus.downloaded,
        )
    ).all()


def list_models_with_rows_ensured(session: Session) -> list[TranslationModel]:
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


def request_model_download(session: Session, direction: str) -> TranslationModel:
    _check_direction(direction)

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
    return model


def request_model_deletion(session: Session, direction: str) -> TranslationModel:
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
    return model


def update_model(session: Session, direction: str, is_enabled: bool | None) -> TranslationModel:
    model = session.exec(
        select(TranslationModel).where(TranslationModel.direction == direction)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    if is_enabled is not None:
        if is_enabled and model.status != TranslationModelStatus.downloaded:
            raise HTTPException(
                status_code=400,
                detail="Le modèle doit être téléchargé avant d'être activé",
            )
        model.is_enabled = is_enabled

    session.add(model)
    session.commit()
    session.refresh(model)
    return model


# ----------------------------------------------------------------- jobs ---


def job_to_response(job: TranslationJob, settings_row: AppSettings) -> dict:
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


def create_text_job(session: Session, current_user: User, direction: str, text: str) -> TranslationJob:
    _check_direction(direction)

    limits = get_settings_row(session)
    if len(text) > limits.max_text_length_chars:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Texte trop long ({len(text)} caractères, "
                f"max {limits.max_text_length_chars})"
            ),
        )

    _require_enabled_model(session, direction)

    job = TranslationJob(
        user_id=current_user.id,
        job_type=TranslationJobType.text,
        direction=direction,
        source_text=text,
        status=TranslationJobStatus.pending,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


async def create_archive_job(
    session: Session,
    current_user: User,
    direction: str,
    filename: str | None,
    upload_file,  # Starlette UploadFile, streamed to disk by the service
) -> TranslationJob:
    _check_direction(direction)

    ext = os.path.splitext(filename or "")[1].lower()
    if ext != ".zip":
        raise HTTPException(status_code=400, detail="Seules les archives ZIP (.zip) sont acceptées")

    limits = get_settings_row(session)
    max_size_bytes = limits.max_archive_size_mb * 1024 * 1024

    _require_enabled_model(session, direction)

    os.makedirs(app_config.translation_tmp_path, exist_ok=True)
    tmp_filename = f"{uuid.uuid4().hex}.zip"
    tmp_path = os.path.join(app_config.translation_tmp_path, tmp_filename)

    try:
        size = 0
        async with aiofiles.open(tmp_path, "wb") as out_file:
            while chunk := await upload_file.read(1024 * 1024):
                size += len(chunk)
                if size > max_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Archive trop volumineuse (max {limits.max_archive_size_mb} Mo)",
                    )
                await out_file.write(chunk)

        validate_zip_safety(tmp_path, limits)

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
        return job

    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def validate_zip_safety(path: str, limits: AppSettings) -> None:
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


def list_jobs(session: Session, current_user: User) -> list[TranslationJob]:
    query = select(TranslationJob)
    if current_user.role != UserRole.admin:
        query = query.where(TranslationJob.user_id == current_user.id)
    return session.exec(query.order_by(TranslationJob.created_at.desc())).all()  # type: ignore[arg-type]


def get_owned_job(job_id: int, session: Session, current_user: User) -> TranslationJob:
    job = session.get(TranslationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de traduction introuvable")
    if current_user.role != UserRole.admin and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return job


def request_cancel(session: Session, job: TranslationJob) -> None:
    if job.status not in (
        TranslationJobStatus.pending,
        TranslationJobStatus.processing,
        TranslationJobStatus.cancelling,
    ):
        raise HTTPException(status_code=409, detail="Ce job ne peut plus être annulé")

    job.cancel_requested = True
    session.add(job)
    session.commit()


def read_result(job: TranslationJob) -> dict:
    """Download payload: inline text for text jobs, file path for archives."""
    if job.status != TranslationJobStatus.done:
        raise HTTPException(status_code=409, detail="Traduction non terminée")

    if job.job_type == TranslationJobType.text:
        return {
            "kind": "content",
            "content": job.result_text or "",
            "media_type": "text/plain; charset=utf-8",
            "filename": "traduction.txt",
        }

    if not job.result_zip_path or not os.path.exists(job.result_zip_path):
        raise HTTPException(status_code=404, detail="Résultat introuvable")
    return {
        "kind": "file",
        "path": job.result_zip_path,
        "media_type": "application/zip",
        "filename": "traduction.zip",
    }


def delete_job(session: Session, job: TranslationJob) -> None:
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


# -------------------------------------------------------------- helpers ---


def _check_direction(direction: str) -> None:
    if direction not in AVAILABLE_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Direction inconnue (fr-en ou en-fr)")


def _require_enabled_model(session: Session, direction: str) -> None:
    enabled = session.exec(
        select(TranslationModel).where(
            TranslationModel.direction == direction,
            TranslationModel.is_enabled == True,  # noqa: E712
            TranslationModel.status == TranslationModelStatus.downloaded,
        )
    ).first()
    if not enabled:
        raise HTTPException(
            status_code=503,
            detail="Aucun modèle de traduction actif pour cette direction. Contactez un administrateur.",
        )
