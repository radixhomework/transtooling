"""Business logic for Whisper model administration."""

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.whisper_model import ModelStatus, WhisperModel

# Supported faster-whisper models (static reference; the actual download
# state is tracked in the database via WhisperModel).
AVAILABLE_MODEL_NAMES = ["tiny", "base", "small", "medium", "large-v3"]


def list_models_with_rows_ensured(session: Session) -> list[WhisperModel]:
    existing = {m.name: m for m in session.exec(select(WhisperModel)).all()}

    # Ensures every known model has a database row (created if needed).
    for name in AVAILABLE_MODEL_NAMES:
        if name not in existing:
            model = WhisperModel(name=name, status=ModelStatus.not_downloaded)
            session.add(model)
            existing[name] = model
    session.commit()

    return session.exec(select(WhisperModel)).all()


def request_download(session: Session, model_name: str) -> WhisperModel:
    if model_name not in AVAILABLE_MODEL_NAMES:
        raise HTTPException(status_code=400, detail="Modèle inconnu")

    model = session.exec(select(WhisperModel).where(WhisperModel.name == model_name)).first()
    if not model:
        model = WhisperModel(name=model_name)

    if model.status == ModelStatus.downloaded:
        raise HTTPException(status_code=400, detail="Modèle déjà téléchargé")

    # The transition to "downloading" is handled by the worker, which polls
    # models awaiting download.
    model.status = ModelStatus.downloading
    model.download_progress = 0
    model.error_message = None
    session.add(model)
    session.commit()
    return model


def request_deletion(session: Session, model_name: str) -> WhisperModel:
    model = session.exec(select(WhisperModel).where(WhisperModel.name == model_name)).first()
    if not model or model.status != ModelStatus.downloaded:
        raise HTTPException(status_code=400, detail="Modèle non téléchargé")

    if model.is_default:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer le modèle par défaut. Changez d'abord le modèle par défaut.",
        )

    # The physical deletion of the model file is performed by the worker.
    model.status = ModelStatus.not_downloaded
    model.is_enabled = False
    model.download_progress = None
    model.disk_size_mb = None
    session.add(model)
    session.commit()
    return model


def update_model(
    session: Session, model_name: str, is_enabled: bool | None, is_default: bool | None
) -> WhisperModel:
    model = session.exec(select(WhisperModel).where(WhisperModel.name == model_name)).first()
    if not model:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    if is_enabled is not None:
        _apply_enable(model, is_enabled)

    if is_default:
        _apply_default(session, model)

    session.add(model)
    session.commit()
    session.refresh(model)
    return model


def _apply_enable(model: WhisperModel, is_enabled: bool) -> None:
    if is_enabled and model.status != ModelStatus.downloaded:
        raise HTTPException(
            status_code=400,
            detail="Le modèle doit être téléchargé avant d'être activé",
        )
    if not is_enabled and model.is_default:
        raise HTTPException(
            status_code=400,
            detail=(
                "Impossible de désactiver le modèle par défaut. "
                "Changez d'abord le modèle par défaut."
            ),
        )
    model.is_enabled = is_enabled


def _apply_default(session: Session, model: WhisperModel) -> None:
    if model.status != ModelStatus.downloaded:
        raise HTTPException(
            status_code=400,
            detail="Le modèle par défaut doit être téléchargé et activé",
        )
    # Only one default model at a time.
    for other in session.exec(select(WhisperModel)).all():
        if other.id != model.id and other.is_default:
            other.is_default = False
            session.add(other)
    model.is_default = True
    model.is_enabled = True


def list_enabled_models(session: Session) -> list[WhisperModel]:
    """Models offered to users: downloaded AND enabled by the admin."""
    return session.exec(
        select(WhisperModel).where(
            WhisperModel.is_enabled == True,  # noqa: E712
            WhisperModel.status == ModelStatus.downloaded,
        )
    ).all()
