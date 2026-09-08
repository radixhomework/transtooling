"""Whisper model request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.whisper_model import ModelStatus


class WhisperModelResponse(BaseModel):
    id: int
    name: str
    status: ModelStatus
    is_enabled: bool
    is_default: bool
    disk_size_mb: Optional[int] = None
    download_progress: Optional[int] = None
    error_message: Optional[str] = None
    downloaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WhisperModelUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class EnabledModelResponse(BaseModel):
    """Model offered to users (upload selector): downloaded and enabled."""

    name: str
    is_default: bool

    class Config:
        from_attributes = True
