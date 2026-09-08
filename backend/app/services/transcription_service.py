"""Business logic for transcription jobs: upload validation, lifecycle,
result export and cleanup."""

import os
import subprocess
import uuid
from typing import Optional

import aiofiles
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.models.app_settings import AppSettings
from app.models.job import JobStatus, TranscriptionJob
from app.models.user import User, UserRole
from app.models.whisper_model import ModelStatus, WhisperModel
from app.services.app_settings_service import get_settings_row

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}


async def create_job(
    session: Session,
    current_user: User,
    *,
    filename: Optional[str],
    model: Optional[str],
    upload_file,  # Starlette UploadFile, streamed to disk by the service
) -> TranscriptionJob:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Formats acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    chosen_model = _resolve_model(session, model)
    limits = get_settings_row(session)
    max_size_bytes = limits.max_file_size_mb * 1024 * 1024

    os.makedirs(settings.audio_tmp_path, exist_ok=True)
    tmp_filename = f"{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.audio_tmp_path, tmp_filename)

    try:
        await _save_upload_with_limit(upload_file, tmp_path, max_size_bytes, limits.max_file_size_mb)

        duration_seconds = _probe_duration_seconds(tmp_path)
        duration_minutes = duration_seconds / 60
        if duration_minutes > limits.max_duration_min:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Durée du fichier ({duration_minutes:.1f} min) supérieure "
                    f"à la limite autorisée ({limits.max_duration_min} min)"
                ),
            )

        job = TranscriptionJob(
            user_id=current_user.id,
            filename_original=filename,
            model_used=chosen_model.name,
            language="fr",
            status=JobStatus.pending,
            audio_tmp_filename=tmp_filename,
            audio_duration_seconds=round(duration_seconds, 3),
            progress=0,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _resolve_model(session: Session, model: Optional[str]) -> WhisperModel:
    """The model chosen by the user if any (it must be downloaded AND
    enabled), otherwise the default model."""
    if model:
        chosen_model = session.exec(
            select(WhisperModel).where(
                WhisperModel.name == model,
                WhisperModel.is_enabled == True,  # noqa: E712
                WhisperModel.status == ModelStatus.downloaded,
            )
        ).first()
        if not chosen_model:
            raise HTTPException(
                status_code=400,
                detail="Modèle inconnu, non téléchargé ou non activé",
            )
        return chosen_model

    chosen_model = session.exec(
        select(WhisperModel).where(
            WhisperModel.is_default == True,  # noqa: E712
            WhisperModel.status == ModelStatus.downloaded,
        )
    ).first()
    if not chosen_model:
        raise HTTPException(
            status_code=503,
            detail="Aucun modèle Whisper téléchargé/actif. Contactez un administrateur.",
        )
    return chosen_model


async def _save_upload_with_limit(upload_file, tmp_path: str, max_size_bytes: int, max_size_mb: int) -> None:
    size = 0
    async with aiofiles.open(tmp_path, "wb") as out_file:
        while chunk := await upload_file.read(1024 * 1024):
            size += len(chunk)
            if size > max_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Fichier trop volumineux (max {max_size_mb} Mo)",
                )
            await out_file.write(chunk)


def list_jobs(session: Session, current_user: User) -> list[TranscriptionJob]:
    if current_user.role == UserRole.admin:
        return session.exec(select(TranscriptionJob)).all()
    return session.exec(
        select(TranscriptionJob).where(TranscriptionJob.user_id == current_user.id)
    ).all()


def get_owned_job(
    job_id: int,
    session: Session,
    current_user: User,
    not_found_detail: str = "Transcription introuvable",
    forbidden_detail: str = "Accès refusé",
) -> TranscriptionJob:
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=not_found_detail)
    if current_user.role != UserRole.admin and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail=forbidden_detail)
    return job


def request_cancel(session: Session, job: TranscriptionJob) -> None:
    if job.status not in (JobStatus.pending, JobStatus.processing, JobStatus.cancelling):
        raise HTTPException(status_code=409, detail="Cette transcription ne peut plus être annulée")

    # The worker detects the flag during processing (or as soon as it picks
    # the job up if it is still queued) and marks the job as "cancelled".
    job.cancel_requested = True
    session.add(job)
    session.commit()


def delete_job(session: Session, job: TranscriptionJob) -> None:
    if job.result_vtt_path and os.path.exists(job.result_vtt_path):
        os.remove(job.result_vtt_path)

    # If the job has not been processed by the worker yet, the temporary
    # audio may still exist: clean it up too in that case.
    if job.audio_tmp_filename:
        audio_path = os.path.join(settings.audio_tmp_path, job.audio_tmp_filename)
        if os.path.exists(audio_path):
            os.remove(audio_path)

    session.delete(job)
    session.commit()


def read_result_as(job: TranscriptionJob, export_format: str):
    """Returns the download payload for the requested export format.
    Returns (content, media_type, filename) for "txt" (generated on the fly)
    or (path, media_type, filename) for "vtt"."""
    if job.status != JobStatus.done or not job.result_vtt_path:
        raise HTTPException(status_code=409, detail="Transcription non terminée")

    base_name = os.path.splitext(job.filename_original)[0]

    if export_format == "txt":
        with open(job.result_vtt_path, encoding="utf-8") as f:
            plain_text = vtt_to_plain_text(f.read())
        return {
            "kind": "content",
            "content": plain_text,
            "media_type": "text/plain; charset=utf-8",
            "filename": f"{base_name}.txt",
        }

    return {
        "kind": "file",
        "path": job.result_vtt_path,
        "media_type": "text/vtt",
        "filename": f"{base_name}.vtt",
    }


def _probe_duration_seconds(file_path: str) -> float:
    """
    Uses ffprobe (from the ffmpeg package, already present in the worker
    image and also required on the backend to validate uploads) to get the
    exact duration of the audio file.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Impossible de lire le fichier audio (format invalide ou corrompu)",
        ) from exc
    except FileNotFoundError as exc:
        # ffprobe missing from the image: a server configuration error,
        # not the user's fault.
        raise HTTPException(
            status_code=500,
            detail="Erreur serveur : ffprobe non disponible",
        ) from exc


def vtt_to_plain_text(vtt_content: str) -> str:
    """
    Converts the .vtt produced by the worker to plain text: one paragraph
    per segment, without timestamps. The input format is the one produced by
    worker/app/vtt.py (a "-->" timing line, then the segment text).
    """
    paragraphs = []
    for block in vtt_content.replace("\r\n", "\n").split("\n\n"):
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        if lines[0].strip() == "WEBVTT":
            lines = lines[1:]
        if not lines:
            continue
        if "-->" in lines[0]:
            lines = lines[1:]
        text = " ".join(line.strip() for line in lines if line.strip())
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)
