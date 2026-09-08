"""Translation request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TranslationJobCreateRequest(BaseModel):
    direction: str  # "fr-en" | "en-fr"
    text: str = Field(min_length=1)


class TranslationModelResponse(BaseModel):
    id: int
    direction: str
    status: str
    is_enabled: bool
    disk_size_mb: Optional[int] = None
    download_progress: Optional[int] = None
    error_message: Optional[str] = None
    downloaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TranslationModelUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
