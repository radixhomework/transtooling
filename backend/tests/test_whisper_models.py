from sqlmodel import Session, select

from app.core.database import engine
from app.models.whisper_model import ModelStatus, WhisperModel


def _get_model_row(name):
    with Session(engine) as session:
        return session.exec(select(WhisperModel).where(WhisperModel.name == name)).first()


def test_download_resets_progress_to_zero(client, admin_headers):
    # Indépendant des autres tests : repartir d'un modèle non téléchargé.
    with Session(engine) as session:
        row = session.exec(select(WhisperModel).where(WhisperModel.name == "base")).first()
        if not row:
            row = WhisperModel(name="base")
        row.status = ModelStatus.not_downloaded
        row.is_enabled = False
        row.is_default = False
        session.add(row)
        session.commit()

    response = client.post("/api/admin/whisper-models/base/download", headers=admin_headers)
    assert response.status_code == 202

    listed = client.get("/api/admin/whisper-models", headers=admin_headers).json()
    base = next(m for m in listed if m["name"] == "base")
    assert base["status"] == "downloading"
    assert base["download_progress"] == 0

    # Le worker n'est pas lancé dans les tests : simuler la fin de son
    # téléchargement pour ne pas polluer les autres tests (base reste
    # inactif et non par défaut, tiny reste le modèle par défaut).
    with Session(engine) as session:
        row = session.exec(select(WhisperModel).where(WhisperModel.name == "base")).first()
        row.status = ModelStatus.downloaded
        row.download_progress = 100
        row.disk_size_mb = 145
        session.add(row)
        session.commit()


def test_delete_clears_progress_and_size(client, admin_headers):
    # Suite du test précédent : base est "téléchargé" côté base de données.
    response = client.delete("/api/admin/whisper-models/base", headers=admin_headers)
    assert response.status_code == 202

    listed = client.get("/api/admin/whisper-models", headers=admin_headers).json()
    base = next(m for m in listed if m["name"] == "base")
    assert base["status"] == "not_downloaded"
    assert base["download_progress"] is None
    assert base["disk_size_mb"] is None


def test_models_list_exposes_progress_fields(client, admin_headers):
    listed = client.get("/api/admin/whisper-models", headers=admin_headers).json()
    assert len(listed) == 5
    for model in listed:
        assert "download_progress" in model
        assert "disk_size_mb" in model


# --- Activation / désactivation ---


def test_cannot_disable_default_model(client, admin_headers, enabled_default_model):
    response = client.patch(
        "/api/admin/whisper-models/tiny",
        json={"is_enabled": False},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "par défaut" in response.json()["detail"]


def test_can_disable_enabled_non_default_model(client, admin_headers):
    with Session(engine) as session:
        row = session.exec(select(WhisperModel).where(WhisperModel.name == "base")).first()
        row.status = ModelStatus.downloaded
        row.is_enabled = True
        row.is_default = False
        session.add(row)
        session.commit()

    response = client.patch(
        "/api/admin/whisper-models/base",
        json={"is_enabled": False},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_enabled"] is False


# --- Endpoint public des modèles activés (sélecteur d'upload) ---


def test_public_models_requires_auth(client):
    response = client.get("/api/models")
    assert response.status_code == 401


def test_public_models_lists_only_enabled_and_downloaded(client, admin_headers, enabled_default_model):
    # tiny : téléchargé, activé, par défaut (fixture). base : téléchargé
    # mais désactivé par le test précédent → seul tiny doit apparaître.
    response = client.get("/api/models", headers=admin_headers)
    assert response.status_code == 200
    models = response.json()
    names = [m["name"] for m in models]
    assert "tiny" in names
    assert "base" not in names
    assert all(m["is_default"] == (m["name"] == "tiny") for m in models)
