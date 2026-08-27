from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_admin
from app.models.app_settings import AppSettings
from app.models.user import User
from app.schemas import AppSettingsResponse, AppSettingsUpdateRequest

router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])


def _get_settings_row(session: Session) -> AppSettings:
    settings_row = session.get(AppSettings, 1)
    if not settings_row:
        # Filet de sécurité : ne devrait pas arriver car _ensure_app_settings()
        # est appelé au démarrage de l'application.
        raise HTTPException(status_code=500, detail="Paramètres applicatifs non initialisés")
    return settings_row


@router.get("", response_model=AppSettingsResponse)
def get_settings(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return _get_settings_row(session)


def _normalize_extensions(raw: str) -> str:
    """Normalise la liste d'extensions : « json, HTML, .htm » → « json,html,htm »."""
    parts = [p.strip().lstrip(".").lower() for p in raw.split(",")]
    parts = [p for p in parts if p]
    return ",".join(parts)


@router.patch("", response_model=AppSettingsResponse)
def update_settings(
    payload: AppSettingsUpdateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    settings_row = _get_settings_row(session)

    int_fields = (
        "max_file_size_mb",
        "max_duration_min",
        "max_text_length_chars",
        "preview_truncate_chars",
        "max_archive_size_mb",
        "max_archive_files_count",
        "max_archive_uncompressed_mb",
    )
    for field_name in int_fields:
        value = getattr(payload, field_name)
        if value is not None:
            if value <= 0:
                raise HTTPException(status_code=400, detail=f"{field_name} doit être positif")
            setattr(settings_row, field_name, value)

    if payload.translatable_extensions is not None:
        normalized = _normalize_extensions(payload.translatable_extensions)
        if not normalized:
            raise HTTPException(
                status_code=400,
                detail="Au moins une extension traduisible est requise (ex: json,html,htm)",
            )
        settings_row.translatable_extensions = normalized

    session.add(settings_row)
    session.commit()
    session.refresh(settings_row)
    return settings_row
