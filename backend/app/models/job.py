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
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    filename_original: str
    model_used: str
    language: str = Field(default="fr")

    # Name of the temporary file actually written to the AUDIO_TMP_PATH
    # volume (e.g. "42.mp3"). Filled when the job is created, read by the
    # worker, then set back to None once the file is deleted after
    # processing.
    audio_tmp_filename: Optional[str] = None

    status: JobStatus = Field(default=JobStatus.pending, index=True)
    error_message: Optional[str] = None

    # Cancellation flag set by the user: the worker detects it during
    # processing and ends the job as "cancelled".
    cancel_requested: bool = Field(default=False)

    # Path of the resulting .vtt file (in the /transcripts volume), filled
    # once the job finishes successfully. The source audio is never kept.
    result_vtt_path: Optional[str] = None

    # Audio duration in seconds, measured with ffprobe at upload time:
    # used as the denominator for the worker-side progress computation.
    audio_duration_seconds: Optional[float] = None

    # Transcription progress as a percentage (0-100), kept up to date by
    # the worker during processing and set to 100 at the end.
    progress: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
