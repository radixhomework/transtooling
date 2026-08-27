"""
Modèles SQLModel du worker.

NOTE IMPORTANTE : backend et worker sont deux images Docker distinctes et ne
partagent pas de code Python directement. Ces définitions doivent donc rester
identiques à celles de backend/app/models/*.py (même table, même colonnes)
puisqu'elles pointent vers la même base SQLite via un volume partagé.

Piste d'amélioration future : extraire ces modèles dans un package Python
partagé (ex. dossier "shared/") monté/installé dans les deux images, pour
éviter la duplication manuelle.
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
