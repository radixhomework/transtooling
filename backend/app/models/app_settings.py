from typing import Optional

from sqlmodel import SQLModel, Field


class AppSettings(SQLModel, table=True):
    """
    Singleton row (id=1) holding the admin-configurable application settings:
    max audio file size and duration, and the translation limits/parameters.

    Initialized on first startup from DEFAULT_MAX_FILE_SIZE_MB /
    DEFAULT_MAX_DURATION_MIN (see app.core.config.settings), then editable
    from the admin panel without a restart.
    """

    id: Optional[int] = Field(default=1, primary_key=True)
    max_file_size_mb: int
    max_duration_min: float

    # --- Translation ---
    max_text_length_chars: int = Field(default=50000)
    preview_truncate_chars: int = Field(default=2000)
    max_archive_size_mb: int = Field(default=200)
    max_archive_files_count: int = Field(default=500)
    max_archive_uncompressed_mb: int = Field(default=500)
    # Extensions translated inside archives (comma-separated, case
    # insensitive comparison); other files are copied as-is.
    translatable_extensions: str = Field(default="json,html,htm,md")
