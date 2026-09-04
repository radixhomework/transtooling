"""
SQLModel models for the worker.

IMPORTANT NOTE: backend and worker are two distinct Docker images and do
not share Python code directly. These definitions must therefore stay
identical to backend/app/models/*.py (same table, same columns) since they
target the same SQLite database through a shared volume.

Future improvement idea: extract these models into a shared Python package
(e.g. a "shared/" folder) mounted/installed in both images, to avoid the
manual duplication.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    cancelling = "cancelling"
    done = "done"
    error = "error"
    cancelled = "cancelled"


class TranscriptionJob(SQLModel, table=True):
    __tablename__ = "transcriptionjob"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    filename_original: str
    model_used: str
    language: str = Field(default="fr")
    audio_tmp_filename: Optional[str] = None
    status: JobStatus = Field(default=JobStatus.pending)
    error_message: Optional[str] = None
    cancel_requested: bool = Field(default=False)
    result_vtt_path: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    progress: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ModelStatus(str, Enum):
    not_downloaded = "not_downloaded"
    downloading = "downloading"
    downloaded = "downloaded"
    error = "error"


class WhisperModel(SQLModel, table=True):
    __tablename__ = "whispermodel"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    status: ModelStatus = Field(default=ModelStatus.not_downloaded)
    is_enabled: bool = Field(default=False)
    is_default: bool = Field(default=False)
    disk_size_mb: Optional[int] = None
    download_progress: Optional[int] = None
    error_message: Optional[str] = None
    downloaded_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
