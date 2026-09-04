import os
import subprocess
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.app_settings import AppSettings
from app.models.job import TranscriptionJob, JobStatus
from app.models.user import User, UserRole
from app.models.whisper_model import WhisperModel, ModelStatus
from app.schemas import JobResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}


def _get_app_limits(session: Session) -> AppSettings:
    row = session.get(AppSettings, 1)
    if not row:
        # Filet de sécurité si l'initialisation au démarrage n'a pas eu lieu
        # (ex: contexte de test ne passant pas par le lifecycle standard).
        row = AppSettings(
            id=1,
            max_file_size_mb=settings.default_max_file_size_mb,
            max_duration_min=settings.default_max_duration_min,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def _probe_duration_seconds(file_path: str) -> float:
    """
    Utilise ffprobe (fourni par le paquet ffmpeg, déjà présent dans l'image
    worker et nécessaire aussi côté backend pour valider l'upload) pour
    obtenir la durée exacte du fichier audio.
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
        # ffprobe absent de l'image : erreur de configuration serveur, pas de
        # la faute de l'utilisateur.
        raise HTTPException(
            status_code=500,
            detail="Erreur serveur : ffprobe non disponible",
        ) from exc


def _vtt_to_plain_text(vtt_content: str) -> str:
    """
    Convertit le .vtt produit par le worker en texte brut : un paragraphe par
    segment, sans les horodatages. Le format d'entrée est celui généré par
    worker/app/vtt.py (une ligne de timing « --> », puis le texte du segment).
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


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Formats acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Modèle à utiliser : celui choisi par l'utilisateur s'il en a proposé un
    # (il doit être téléchargé ET activé), sinon le modèle par défaut.
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
    else:
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

    limits = _get_app_limits(session)
    max_size_bytes = limits.max_file_size_mb * 1024 * 1024

    os.makedirs(settings.audio_tmp_path, exist_ok=True)
    tmp_filename = f"{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.audio_tmp_path, tmp_filename)

    size = 0
    try:
        with open(tmp_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_size_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Fichier trop volumineux (max {limits.max_file_size_mb} Mo)",
                    )
                out_file.write(chunk)

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
            filename_original=file.filename,
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

    except HTTPException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


@router.get("", response_model=List[JobResponse])
def list_jobs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.admin:
        return session.exec(select(TranscriptionJob)).all()
    return session.exec(
        select(TranscriptionJob).where(TranscriptionJob.user_id == current_user.id)
    ).all()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription introuvable")
    if current_user.role != UserRole.admin and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return job


@router.get("/{job_id}/download")
def download_job_result(
    job_id: int,
    format: str = Query("vtt", pattern="^(vtt|txt)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription introuvable")
    if current_user.role != UserRole.admin and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if job.status != JobStatus.done or not job.result_vtt_path:
        raise HTTPException(status_code=409, detail="Transcription non terminée")

    base_name = os.path.splitext(job.filename_original)[0]

    if format == "txt":
        with open(job.result_vtt_path, encoding="utf-8") as f:
            plain_text = _vtt_to_plain_text(f.read())
        return Response(
            content=plain_text,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.txt"'},
        )

    return FileResponse(
        path=job.result_vtt_path,
        media_type="text/vtt",
        filename=f"{base_name}.vtt",
    )


@router.post("/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription introuvable")
    if current_user.role != UserRole.admin and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if job.status not in (JobStatus.pending, JobStatus.processing, JobStatus.cancelling):
        raise HTTPException(status_code=409, detail="Cette transcription ne peut plus être annulée")

    # Le worker détecte le fanion pendant le traitement (ou dès sa prise en
    # charge si le job est encore en file) et passe le job en « cancelled ».
    job.cancel_requested = True
    session.add(job)
    session.commit()
    return {"detail": "Annulation demandée"}


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = session.get(TranscriptionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcription introuvable")
    if current_user.role != UserRole.admin and job.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Seul le propriétaire ou un administrateur peut supprimer cette transcription",
        )

    if job.result_vtt_path and os.path.exists(job.result_vtt_path):
        os.remove(job.result_vtt_path)

    # Si le job n'a pas encore été traité par le worker, l'audio temporaire
    # peut encore exister : le nettoyer aussi dans ce cas.
    if job.audio_tmp_filename:
        audio_path = os.path.join(settings.audio_tmp_path, job.audio_tmp_filename)
        if os.path.exists(audio_path):
            os.remove(audio_path)

    session.delete(job)
    session.commit()
