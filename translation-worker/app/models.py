"""
Modèles SQLModel du worker de traduction.

NOTE IMPORTANTE : backend et workers sont des images Docker distinctes et ne
partagent pas de code Python directement. Ces définitions doivent donc rester
identiques à celles de backend/app/models/*.py (même table, mêmes colonnes)
puisqu'elles pointent vers la même base SQLite via un volume partagé.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class TranslationJobType(str, Enum):
    text = "text"
    archive = "archive"


class TranslationDirection(str, Enum):
    fr_en = "fr-en"
    en_fr = "en-fr"


class TranslationJobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    cancelling = "cancelling"
    done = "done"
    error = "error"
    cancelled = "cancelled"


class TranslationJob(SQLModel, table=True):
    __tablename__ = "translationjob"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    job_type: TranslationJobType
    direction: TranslationDirection
    source_text: Optional[str] = None
    result_text: Optional[str] = None
    archive_tmp_filename: Optional[str] = None
    result_zip_path: Optional[str] = None
    report_json: Optional[str] = None
    stopped_reason: Optional[str] = None
    status: TranslationJobStatus = Field(default=TranslationJobStatus.pending)
    error_message: Optional[str] = None
    cancel_requested: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class TranslationModelStatus(str, Enum):
    not_downloaded = "not_downloaded"
    downloading = "downloading"
    downloaded = "downloaded"
    error = "error"


class TranslationModel(SQLModel, table=True):
    __tablename__ = "translationmodel"

    id: Optional[int] = Field(default=None, primary_key=True)
    direction: TranslationDirection
    status: TranslationModelStatus = Field(default=TranslationModelStatus.not_downloaded)
    is_enabled: bool = Field(default=False)
    disk_size_mb: Optional[int] = None
    download_progress: Optional[int] = None
    error_message: Optional[str] = None
    downloaded_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TranslationCache(SQLModel, table=True):
    __tablename__ = "translationcache"

    cache_key: str = Field(primary_key=True)
    direction: TranslationDirection
    translated_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppSettings(SQLModel, table=True):
    """Miroir en lecture seule de la ligne singleton des paramètres admin
    (seuls les champs utiles au worker sont lus ; les colonnes doivent
    correspondre à backend/app/models/app_settings.py)."""

    __tablename__ = "appsettings"

    id: Optional[int] = Field(default=1, primary_key=True)
    max_file_size_mb: int
    max_duration_min: float
    max_text_length_chars: int = Field(default=50000)
    preview_truncate_chars: int = Field(default=2000)
    max_archive_size_mb: int = Field(default=200)
    max_archive_files_count: int = Field(default=500)
    max_archive_uncompressed_mb: int = Field(default=500)
    translatable_extensions: str = Field(default="json,html,htm,md")
