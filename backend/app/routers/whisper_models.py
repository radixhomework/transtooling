from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.models.whisper_model import WhisperModel, ModelStatus
from app.schemas import (
    EnabledModelResponse,
    WhisperModelResponse,
    WhisperModelUpdateRequest,
)

router = APIRouter(prefix="/api/admin/whisper-models", tags=["admin-whisper-models"])

# Endpoint public (tout utilisateur authentifié) : modèles utilisables pour
# une transcription, proposés dans le sélecteur du tableau de bord.
public_router = APIRouter(prefix="/api/models", tags=["models"])

# Modèles faster-whisper supportés (référence statique ; l'état réel de
# téléchargement est suivi en base via WhisperModel).
AVAILABLE_MODEL_NAMES = ["tiny", "base", "small", "medium", "large-v3"]


@router.get("", response_model=List[WhisperModelResponse])
def list_models(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    existing = {m.name: m for m in session.exec(select(WhisperModel)).all()}

    # S'assure que chaque modèle connu a une entrée en base (créée au besoin).
    for name in AVAILABLE_MODEL_NAMES:
        if name not in existing:
            model = WhisperModel(name=name, status=ModelStatus.not_downloaded)
            session.add(model)
            existing[name] = model
    session.commit()

    return session.exec(select(WhisperModel)).all()


@router.post("/{model_name}/download", status_code=status.HTTP_202_ACCEPTED)
def request_model_download(
    model_name: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    if model_name not in AVAILABLE_MODEL_NAMES:
        raise HTTPException(status_code=400, detail="Modèle inconnu")

    model = session.exec(select(WhisperModel).where(WhisperModel.name == model_name)).first()
    if not model:
        model = WhisperModel(name=model_name)

    if model.status == ModelStatus.downloaded:
        raise HTTPException(status_code=400, detail="Modèle déjà téléchargé")

    # Le passage à "downloading" sera pris en charge par le worker, qui poll
    # les modèles en attente de téléchargement (voir Phase 3 - worker).
    model.status = ModelStatus.downloading
    model.download_progress = 0
    model.error_message = None
    session.add(model)
    session.commit()
    return {"detail": f"Téléchargement du modèle '{model_name}' déclenché"}


@router.delete("/{model_name}", status_code=status.HTTP_202_ACCEPTED)
def request_model_deletion(
    model_name: str,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    model = session.exec(select(WhisperModel).where(WhisperModel.name == model_name)).first()
    if not model or model.status != ModelStatus.downloaded:
        raise HTTPException(status_code=400, detail="Modèle non téléchargé")

    if model.is_default:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer le modèle par défaut. Changez d'abord le modèle par défaut.",
        )

    # La suppression physique du fichier modèle est effectuée par le worker.
    model.status = ModelStatus.not_downloaded
    model.is_enabled = False
    model.download_progress = None
    model.disk_size_mb = None
    session.add(model)
    session.commit()
    return {"detail": f"Suppression du modèle '{model_name}' déclenchée"}


@router.patch("/{model_name}", response_model=WhisperModelResponse)
def update_model(
    model_name: str,
    payload: WhisperModelUpdateRequest,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    model = session.exec(select(WhisperModel).where(WhisperModel.name == model_name)).first()
    if not model:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    if payload.is_enabled is not None:
        if payload.is_enabled and model.status != ModelStatus.downloaded:
            raise HTTPException(
                status_code=400,
                detail="Le modèle doit être téléchargé avant d'être activé",
            )
        if not payload.is_enabled and model.is_default:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Impossible de désactiver le modèle par défaut. "
                    "Changez d'abord le modèle par défaut."
                ),
            )
        model.is_enabled = payload.is_enabled

    if payload.is_default is not None and payload.is_default:
        if model.status != ModelStatus.downloaded:
            raise HTTPException(
                status_code=400,
                detail="Le modèle par défaut doit être téléchargé et activé",
            )
        # Un seul modèle par défaut à la fois.
        for other in session.exec(select(WhisperModel)).all():
            if other.id != model.id and other.is_default:
                other.is_default = False
                session.add(other)
        model.is_default = True
        model.is_enabled = True

    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@public_router.get("", response_model=List[EnabledModelResponse])
def list_enabled_models(
    session: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Modèles proposés aux utilisateurs : téléchargés ET activés par l'admin."""
    return session.exec(
        select(WhisperModel).where(
            WhisperModel.is_enabled == True,  # noqa: E712
            WhisperModel.status == ModelStatus.downloaded,
        )
    ).all()
