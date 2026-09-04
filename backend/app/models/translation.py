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
    """
    FR-EN translation job, either text mode (source_text -> result_text) or
    archive mode (technical ZIP -> translated archive, report in report_json).
    Processed by the translation-worker service.
    """

    __tablename__ = "translationjob"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    job_type: TranslationJobType
    direction: TranslationDirection

    # Mode texte
    source_text: Optional[str] = None
    result_text: Optional[str] = None

    # Mode archive
    archive_tmp_filename: Optional[str] = None
    result_zip_path: Optional[str] = None
    # JSON: {total_files, translated, copied, errors, error_details: [{file, error}]}
    report_json: Optional[str] = None
    # Reason of a blocking interruption in archive mode (e.g. unreadable archive)
    stopped_reason: Optional[str] = None

    status: TranslationJobStatus = Field(default=TranslationJobStatus.pending, index=True)
    error_message: Optional[str] = None

    # Cancellation flag set by the user: the worker detects it
    # during processing and ends the job as "cancelled".
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
    """
    State of a translation model (CTranslate2), one per direction.
    Downloaded/deleted/enabled from the admin panel, like Whisper models.
    """

    __tablename__ = "translationmodel"

    id: Optional[int] = Field(default=None, primary_key=True)
    direction: TranslationDirection = Field(index=True, unique=True)

    status: TranslationModelStatus = Field(default=TranslationModelStatus.not_downloaded)
    is_enabled: bool = Field(default=False)

    disk_size_mb: Optional[int] = None
    download_progress: Optional[int] = None  # reported by the worker, not displayed (bar removed)
    error_message: Optional[str] = None

    downloaded_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TranslationCache(SQLModel, table=True):
    """
    Translation cache: one row per hashed (direction, source text) pair.
    Read before any translation, written only after an actual computation
    (never on a cache hit).
    """

    __tablename__ = "translationcache"

    cache_key: str = Field(primary_key=True)  # sha256(direction + \x00 + texte source)
    direction: TranslationDirection
    translated_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
