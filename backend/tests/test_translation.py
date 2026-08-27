import io
import os
import zipfile

from sqlmodel import Session, select

from app.core.database import engine
from app.models.translation import (
    TranslationDirection,
    TranslationJob,
    TranslationJobStatus,
    TranslationModel,
    TranslationModelStatus,
)


def _enable_translation_model(direction: str = "fr-en"):
    """Insère/marque un modèle de traduction comme téléchargé+activé."""
    with Session(engine) as session:
        row = session.exec(
            select(TranslationModel).where(TranslationModel.direction == direction)
        ).first()
        if not row:
            row = TranslationModel(direction=TranslationDirection(direction))
        row.status = TranslationModelStatus.downloaded
        row.is_enabled = True
        session.add(row)
        session.commit()


def _make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ------------------------------------------------------------- mode texte


def test_text_job_requires_auth(client):
    response = client.post("/api/translation/jobs", json={"direction": "fr-en", "text": "Hello"})
    assert response.status_code == 401


def test_text_job_without_active_model_fails(client, admin_headers):
    response = client.post(
        "/api/translation/jobs",
        json={"direction": "fr-en", "text": "Hello"},
        headers=admin_headers,
    )
    assert response.status_code == 503


def test_text_job_created(client, admin_headers):
    _enable_translation_model("fr-en")
    response = client.post(
        "/api/translation/jobs",
        json={"direction": "fr-en", "text": "Bonjour le monde."},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "text"
    assert data["direction"] == "fr-en"
    assert data["status"] == "pending"
    assert data["result_preview"] is None


def test_text_job_rejects_invalid_direction(client, admin_headers):
    _enable_translation_model("fr-en")
    response = client.post(
        "/api/translation/jobs",
        json={"direction": "de-en", "text": "Bonjour"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_text_job_rejects_too_long_text(client, admin_headers):
    _enable_translation_model("fr-en")
    response = client.post(
        "/api/translation/jobs",
        json={"direction": "fr-en", "text": "x" * 60000},
        headers=admin_headers,
    )
    assert response.status_code == 413


def test_text_job_preview_truncated(client, admin_headers):
    _enable_translation_model("fr-en")
    job_resp = client.post(
        "/api/translation/jobs",
        json={"direction": "fr-en", "text": "Bonjour"},
        headers=admin_headers,
    )
    job_id = job_resp.json()["id"]

    # Simule la fin du traitement par le worker (non lancé dans les tests).
    with Session(engine) as session:
        job = session.get(TranslationJob, job_id)
        job.status = TranslationJobStatus.done
        job.result_text = "A" * 5000
        session.add(job)
        session.commit()

    # Abaisse le seuil d'aperçu pour couvrir la troncature.
    patch = client.patch(
        "/api/admin/settings",
        json={"preview_truncate_chars": 100},
        headers=admin_headers,
    )
    assert patch.status_code == 200

    response = client.get(f"/api/translation/jobs/{job_id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["result_preview"]) == 100
    assert data["result_truncated"] is True

    # Le texte complet reste téléchargeable.
    download = client.get(f"/api/translation/jobs/{job_id}/download", headers=admin_headers)
    assert download.status_code == 200
    assert len(download.text) == 5000

    client.patch("/api/admin/settings", json={"preview_truncate_chars": 2000}, headers=admin_headers)


def test_translation_history_and_delete(client, admin_headers):
    _enable_translation_model("fr-en")
    job_resp = client.post(
        "/api/translation/jobs",
        json={"direction": "fr-en", "text": "Bonjour"},
        headers=admin_headers,
    )
    job_id = job_resp.json()["id"]

    history = client.get("/api/translation/jobs", headers=admin_headers)
    assert history.status_code == 200
    assert any(j["id"] == job_id for j in history.json())

    delete = client.delete(f"/api/translation/jobs/{job_id}", headers=admin_headers)
    assert delete.status_code == 204


# ------------------------------------------------------------ mode archive


def test_archive_job_created(client, admin_headers):
    _enable_translation_model("fr-en")
    zip_bytes = _make_zip({"data.json": '{"k": "v"}', "page.html": "<p>Hi</p>"})
    response = client.post(
        "/api/translation/jobs/archive",
        files={"file": ("site.zip", io.BytesIO(zip_bytes), "application/zip")},
        data={"direction": "fr-en"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "archive"
    assert data["status"] == "pending"


def test_archive_job_rejects_non_zip_extension(client, admin_headers):
    _enable_translation_model("fr-en")
    response = client.post(
        "/api/translation/jobs/archive",
        files={"file": ("doc.txt", io.BytesIO(b"plain"), "text/plain")},
        data={"direction": "fr-en"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_archive_job_rejects_corrupted_zip(client, admin_headers):
    _enable_translation_model("fr-en")
    response = client.post(
        "/api/translation/jobs/archive",
        files={"file": ("bad.zip", io.BytesIO(b"not a zip at all"), "application/zip")},
        data={"direction": "fr-en"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_archive_job_rejects_zip_slip(client, admin_headers):
    _enable_translation_model("fr-en")
    zip_bytes = _make_zip({"ok.txt": "ok", "../../evil.txt": "boom"})
    response = client.post(
        "/api/translation/jobs/archive",
        files={"file": ("slip.zip", io.BytesIO(zip_bytes), "application/zip")},
        data={"direction": "fr-en"},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_archive_job_rejects_too_many_files(client, admin_headers):
    _enable_translation_model("fr-en")
    # Limite abaissée à 2 fichiers pour le test.
    client.patch("/api/admin/settings", json={"max_archive_files_count": 2}, headers=admin_headers)
    try:
        zip_bytes = _make_zip({f"f{i}.txt": "x" for i in range(5)})
        response = client.post(
            "/api/translation/jobs/archive",
            files={"file": ("many.zip", io.BytesIO(zip_bytes), "application/zip")},
            data={"direction": "fr-en"},
            headers=admin_headers,
        )
        assert response.status_code == 413
    finally:
        client.patch(
            "/api/admin/settings", json={"max_archive_files_count": 500}, headers=admin_headers
        )


def test_archive_job_rejects_oversized_uncompressed(client, admin_headers):
    _enable_translation_model("fr-en")
    client.patch("/api/admin/settings", json={"max_archive_uncompressed_mb": 1}, headers=admin_headers)
    try:
        zip_bytes = _make_zip({"big.bin": b"\0" * (2 * 1024 * 1024)})
        response = client.post(
            "/api/translation/jobs/archive",
            files={"file": ("big.zip", io.BytesIO(zip_bytes), "application/zip")},
            data={"direction": "fr-en"},
            headers=admin_headers,
        )
        assert response.status_code == 413
    finally:
        client.patch(
            "/api/admin/settings", json={"max_archive_uncompressed_mb": 500}, headers=admin_headers
        )


# ------------------------------------------------- modèles (admin + public)


def test_admin_translation_models_seeded(client, admin_headers):
    response = client.get("/api/admin/translation-models", headers=admin_headers)
    assert response.status_code == 200
    directions = sorted(m["direction"] for m in response.json())
    assert directions == ["en-fr", "fr-en"]


def test_translation_model_download_and_delete(client, admin_headers):
    # Indépendant des autres tests : repartir d'un modèle non téléchargé.
    with Session(engine) as session:
        row = session.exec(
            select(TranslationModel).where(TranslationModel.direction == "fr-en")
        ).first()
        if not row:
            row = TranslationModel(direction=TranslationDirection.fr_en)
        row.status = TranslationModelStatus.not_downloaded
        row.is_enabled = False
        session.add(row)
        session.commit()

    post = client.post("/api/admin/translation-models/fr-en/download", headers=admin_headers)
    assert post.status_code == 202

    listed = client.get("/api/admin/translation-models", headers=admin_headers).json()
    model = next(m for m in listed if m["direction"] == "fr-en")
    assert model["status"] == "downloading"
    assert model["download_progress"] == 0

    # Simule la fin du téléchargement côté worker puis suppression.
    with Session(engine) as session:
        row = session.exec(
            select(TranslationModel).where(TranslationModel.direction == "fr-en")
        ).first()
        row.status = TranslationModelStatus.downloaded
        row.download_progress = 100
        row.disk_size_mb = 310
        session.add(row)
        session.commit()

    delete = client.delete("/api/admin/translation-models/fr-en", headers=admin_headers)
    assert delete.status_code == 202
    listed = client.get("/api/admin/translation-models", headers=admin_headers).json()
    model = next(m for m in listed if m["direction"] == "fr-en")
    assert model["status"] == "not_downloaded"
    assert model["download_progress"] is None
    assert model["disk_size_mb"] is None


def test_public_translation_models_requires_auth(client):
    assert client.get("/api/translation/models").status_code == 401


def test_public_translation_models_lists_enabled_only(client, admin_headers):
    _enable_translation_model("fr-en")
    response = client.get("/api/translation/models", headers=admin_headers)
    assert response.status_code == 200
    directions = [m["direction"] for m in response.json()]
    assert "fr-en" in directions
    assert "en-fr" not in directions


# ------------------------------------------------------------------ settings


def test_settings_translation_fields_roundtrip(client, admin_headers):
    patch = client.patch(
        "/api/admin/settings",
        json={"max_text_length_chars": 1000, "preview_truncate_chars": 500},
        headers=admin_headers,
    )
    assert patch.status_code == 200
    data = patch.json()
    assert data["max_text_length_chars"] == 1000
    assert data["preview_truncate_chars"] == 500

    get = client.get("/api/admin/settings", headers=admin_headers)
    assert get.json()["max_text_length_chars"] == 1000

    client.patch(
        "/api/admin/settings",
        json={"max_text_length_chars": 50000, "preview_truncate_chars": 2000},
        headers=admin_headers,
    )


def test_settings_extensions_normalized(client, admin_headers):
    patch = client.patch(
        "/api/admin/settings",
        json={"translatable_extensions": "json, HTML , .htm ,"},
        headers=admin_headers,
    )
    assert patch.status_code == 200
    assert patch.json()["translatable_extensions"] == "json,html,htm"

    invalid = client.patch(
        "/api/admin/settings",
        json={"translatable_extensions": "  , "},
        headers=admin_headers,
    )
    assert invalid.status_code == 400


def test_settings_rejects_non_positive_limits(client, admin_headers):
    response = client.patch(
        "/api/admin/settings",
        json={"max_archive_size_mb": 0},
        headers=admin_headers,
    )
    assert response.status_code == 400


# --- Annulation ---


def test_cancel_pending_translation_job(client, admin_headers):
    _enable_translation_model("fr-en")
    job_resp = client.post(
        "/api/translation/jobs",
        json={"direction": "fr-en", "text": "Bonjour"},
        headers=admin_headers,
    )
    job_id = job_resp.json()["id"]

    response = client.post(f"/api/translation/jobs/{job_id}/cancel", headers=admin_headers)
    assert response.status_code == 202

    # Une seconde demande reste acceptée (idempotent).
    response = client.post(f"/api/translation/jobs/{job_id}/cancel", headers=admin_headers)
    assert response.status_code == 202


def test_cancel_translation_job_forbidden_for_other_user(client, admin_headers):
    _enable_translation_model("fr-en")
    job_resp = client.post(
        "/api/translation/jobs",
        json={"direction": "fr-en", "text": "Bonjour"},
        headers=admin_headers,
    )
    job_id = job_resp.json()["id"]

    client.post(
        "/api/users",
        json={"login": "stranger", "password": "Stranger1", "role": "user"},
        headers=admin_headers,
    )
    login_resp = client.post(
        "/api/auth/login", json={"login": "stranger", "password": "Stranger1"}
    )
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    response = client.post(f"/api/translation/jobs/{job_id}/cancel", headers=headers)
    assert response.status_code == 403
