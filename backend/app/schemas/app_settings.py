"""Application settings request/response schemas."""

from typing import Optional

from pydantic import BaseModel


class AppSettingsResponse(BaseModel):
    max_file_size_mb: int
    max_duration_min: float
    max_text_length_chars: int
    preview_truncate_chars: int
    max_archive_size_mb: int
    max_archive_files_count: int
    max_archive_uncompressed_mb: int
    translatable_extensions: str


class AppSettingsUpdateRequest(BaseModel):
    max_file_size_mb: Optional[int] = None
    max_duration_min: Optional[float] = None
    max_text_length_chars: Optional[int] = None
    preview_truncate_chars: Optional[int] = None
    max_archive_size_mb: Optional[int] = None
    max_archive_files_count: Optional[int] = None
    max_archive_uncompressed_mb: Optional[int] = None
    translatable_extensions: Optional[str] = None
