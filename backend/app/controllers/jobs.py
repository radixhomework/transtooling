"""Transcription jobs controller: HTTP boundary for job endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import JobResponse
from app.services import transcription_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = await transcription_service.create_job(
        session,
        current_user,
        filename=file.filename,
        model=model,
        upload_file=file,
    )
    return job


@router.get("", response_model=List[JobResponse])
def list_jobs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return transcription_service.list_jobs(session, current_user)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return transcription_service.get_owned_job(job_id, session, current_user)


@router.get("/{job_id}/download")
def download_job_result(
    job_id: int,
    format: str = Query("vtt", pattern="^(vtt|txt)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = transcription_service.get_owned_job(job_id, session, current_user)
    payload = transcription_service.read_result_as(job, format)

    if payload["kind"] == "content":
        return Response(
            content=payload["content"],
            media_type=payload["media_type"],
            headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
        )
    return FileResponse(
        path=payload["path"],
        media_type=payload["media_type"],
        filename=payload["filename"],
    )


@router.post("/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = transcription_service.get_owned_job(job_id, session, current_user)
    transcription_service.request_cancel(session, job)
    return {"detail": "Annulation demandée"}


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    job = transcription_service.get_owned_job(
        job_id,
        session,
        current_user,
        not_found_detail="Transcription introuvable",
        forbidden_detail=(
            "Seul le propriétaire ou un administrateur peut supprimer cette transcription"
        ),
    )
    transcription_service.delete_job(session, job)
