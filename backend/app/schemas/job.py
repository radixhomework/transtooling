"""Transcription job response schema."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.job import JobStatus


class JobResponse(BaseModel):
    id: int
    user_id: int
    filename_original: str
    model_used: str
    language: str
    status: JobStatus
    error_message: Optional[str] = None
    progress: Optional[int] = None
    audio_duration_seconds: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True
