"""Business logic for the singleton application settings row."""

from fastapi import HTTPException
from sqlmodel import Session

from app.core.config import settings as app_config
from app.models.app_settings import AppSettings
from app.schemas import AppSettingsUpdateRequest

INT_FIELDS = (
    "max_file_size_mb",
    "max_duration_min",
    "max_text_length_chars",
    "preview_truncate_chars",
    "max_archive_size_mb",
    "max_archive_files_count",
    "max_archive_uncompressed_mb",
)


def get_settings_row(session: Session) -> AppSettings:
    """Fetches the singleton row, creating it as a safety net when startup
    initialization did not run (e.g. a bare test context)."""
    row = session.get(AppSettings, 1)
    if not row:
        row = AppSettings(
            id=1,
            max_file_size_mb=app_config.default_max_file_size_mb,
            max_duration_min=app_config.default_max_duration_min,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def get_settings_row_or_raise(session: Session) -> AppSettings:
    """Same as ``get_settings_row`` but fails loudly: used by the admin
    settings endpoint where a missing row means a broken installation."""
    row = session.get(AppSettings, 1)
    if not row:
        # Should not happen since ensure_app_settings() runs at startup.
        raise HTTPException(status_code=500, detail="Paramètres applicatifs non initialisés")
    return row


def normalize_extensions(raw: str) -> str:
    """Normalizes the extension list: "json, HTML, .htm" -> "json,html,htm"."""
    parts = [p.strip().lstrip(".").lower() for p in raw.split(",")]
    parts = [p for p in parts if p]
    return ",".join(parts)


def update_settings(
    session: Session, payload: AppSettingsUpdateRequest
) -> AppSettings:
    row = get_settings_row_or_raise(session)

    for field_name in INT_FIELDS:
        value = getattr(payload, field_name)
        if value is not None:
            if value <= 0:
                raise HTTPException(status_code=400, detail=f"{field_name} doit être positif")
            setattr(row, field_name, value)

    if payload.translatable_extensions is not None:
        normalized = normalize_extensions(payload.translatable_extensions)
        if not normalized:
            raise HTTPException(
                status_code=400,
                detail="Au moins une extension traduisible est requise (ex: json,html,htm)",
            )
        row.translatable_extensions = normalized

    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def ensure_app_settings() -> None:
    """Creates the singleton settings row if it does not exist yet (startup)."""
    from app.core.database import engine

    with Session(engine) as session:
        if session.get(AppSettings, 1):
            return
        session.add(
            AppSettings(
                id=1,
                max_file_size_mb=app_config.default_max_file_size_mb,
                max_duration_min=app_config.default_max_duration_min,
            )
        )
        session.commit()
