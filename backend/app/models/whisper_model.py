from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class ModelStatus(str, Enum):
    not_downloaded = "not_downloaded"
    downloading = "downloading"
    downloaded = "downloaded"
    error = "error"


class WhisperModel(SQLModel, table=True):
    """
    State of a faster-whisper model (tiny, base, small, medium, large-v3...).
    Download and deletion are triggered from the admin panel and executed by
    the worker.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # e.g. "small", "medium", "large-v3"

    status: ModelStatus = Field(default=ModelStatus.not_downloaded)
    is_enabled: bool = Field(default=False)  # offered to users or not
    is_default: bool = Field(default=False)

    disk_size_mb: Optional[int] = None

    # Download progress as a percentage (0-100), kept up to date by the
    # worker during the download, 100 once finished.
    download_progress: Optional[int] = None

    error_message: Optional[str] = None

    downloaded_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
