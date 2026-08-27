import os

from app.core.database import engine
from app.models.job import JobStatus, TranscriptionJob
from app.models.whisper_model import ModelStatus, WhisperModel
from sqlmodel import Session, select


def test_create_job_requires_auth(client, short_audio_file):
    with open(short_audio_file, "rb") as f:
        response = client.post("/api/jobs", files={"file": ("test.wav", f, "audio/wav")})
    assert response.status_code == 401


def test_create_job_without_default_model_fails(client, admin_headers, short_audio_file):
    # Aucun modèle activé par défaut à ce stade (fixture enabled_default_model non utilisée)
    with open(short_audio_file, "rb") as f:
        response = client.post(
            "/api/jobs",
            files={"file": ("test.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    assert response.status_code == 503


def test_create_job_success(client, admin_headers, short_audio_file, enabled_default_model):
    with open(short_audio_file, "rb") as f:
        response = client.post(
            "/api/jobs",
            files={"file": ("test.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["language"] == "fr"
    assert data["model_used"] == "tiny"
    assert data["filename_original"] == "test.wav"
    # La durée mesurée par ffprobe est conservée et la progression démarre à 0.
    assert data["audio_duration_seconds"] > 0
    assert data["progress"] == 0


def test_create_job_rejects_unsupported_extension(client, admin_headers, enabled_default_model):
    response = client.post(
        "/api/jobs",
        files={"file": ("test.txt", b"not audio", "text/plain")},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_create_job_rejects_invalid_audio_content(
    client, admin_headers, invalid_audio_file, enabled_default_model
):
    with open(invalid_audio_file, "rb") as f:
        response = client.post(
            "/api/jobs",
            files={"file": ("invalid.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    # Le fichier a une extension valide mais un contenu illisible par ffprobe
    assert response.status_code == 400


def test_create_job_rejects_file_exceeding_duration_limit(
    client, admin_headers, short_audio_file, enabled_default_model
):
    # Le fichier de test fait ~1 seconde ; on fixe une limite de durée
    # volontairement inférieure (0.01 min = 0.6s) pour la faire dépasser.
    patch_response = client.patch(
        "/api/admin/settings",
        json={"max_duration_min": 0.01},
        headers=admin_headers,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["max_duration_min"] == 0.01

    try:
        with open(short_audio_file, "rb") as f:
            response = client.post(
                "/api/jobs",
                files={"file": ("toolong.wav", f, "audio/wav")},
                headers=admin_headers,
            )
        assert response.status_code == 413
    finally:
        # Restaurer une limite raisonnable pour ne pas affecter les autres tests
        client.patch(
            "/api/admin/settings",
            json={"max_duration_min": 60},
            headers=admin_headers,
        )


def test_list_jobs_returns_only_own_jobs_for_regular_user(
    client, admin_headers, short_audio_file, enabled_default_model
):
    # Créer un utilisateur standard
    create_resp = client.post(
        "/api/users",
        json={"login": "jobsowner", "password": "OwnerPass1", "role": "user"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 201

    login_resp = client.post(
        "/api/auth/login",
        json={"login": "jobsowner", "password": "OwnerPass1"},
    )
    user_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    with open(short_audio_file, "rb") as f:
        create_job_resp = client.post(
            "/api/jobs",
            files={"file": ("owned.wav", f, "audio/wav")},
            headers=user_headers,
        )
    assert create_job_resp.status_code == 201

    list_resp = client.get("/api/jobs", headers=user_headers)
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    assert all(j["filename_original"] != "" for j in jobs)
    assert any(j["filename_original"] == "owned.wav" for j in jobs)


def test_get_job_forbidden_for_other_user(client, admin_headers, short_audio_file, enabled_default_model):
    # Utilisateur A crée un job
    client.post(
        "/api/users",
        json={"login": "userA", "password": "UserAPass1", "role": "user"},
        headers=admin_headers,
    )
    login_a = client.post(
        "/api/auth/login", json={"login": "userA", "password": "UserAPass1"}
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    with open(short_audio_file, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            files={"file": ("a_file.wav", f, "audio/wav")},
            headers=headers_a,
        )
    job_id = job_resp.json()["id"]

    # Utilisateur B tente d'accéder au job de A
    client.post(
        "/api/users",
        json={"login": "userB", "password": "UserBPass1", "role": "user"},
        headers=admin_headers,
    )
    login_b = client.post(
        "/api/auth/login", json={"login": "userB", "password": "UserBPass1"}
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    response = client.get(f"/api/jobs/{job_id}", headers=headers_b)
    assert response.status_code == 403


def test_get_nonexistent_job_returns_404(client, admin_headers):
    response = client.get("/api/jobs/999999", headers=admin_headers)
    assert response.status_code == 404


def test_download_incomplete_job_returns_409(
    client, admin_headers, short_audio_file, enabled_default_model
):
    with open(short_audio_file, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            files={"file": ("pending.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    job_id = job_resp.json()["id"]

    response = client.get(f"/api/jobs/{job_id}/download", headers=admin_headers)
    assert response.status_code == 409


def test_owner_can_delete_own_job(client, admin_headers, short_audio_file, enabled_default_model):
    with open(short_audio_file, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            files={"file": ("todelete.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    job_id = job_resp.json()["id"]

    response = client.delete(f"/api/jobs/{job_id}", headers=admin_headers)
    assert response.status_code == 204

    get_response = client.get(f"/api/jobs/{job_id}", headers=admin_headers)
    assert get_response.status_code == 404


# --- Choix du modèle à l'upload ---


def _set_model_state(name: str, **kwargs):
    # Les lignes whisper_models sont créées au premier appel de la liste
    # admin : créer la ligne si elle n'existe pas encore dans ce contexte.
    with Session(engine) as session:
        row = session.exec(select(WhisperModel).where(WhisperModel.name == name)).first()
        if not row:
            row = WhisperModel(name=name)
        for key, value in kwargs.items():
            setattr(row, key, value)
        session.add(row)
        session.commit()


def test_create_job_with_explicit_enabled_model(client, admin_headers, short_audio_file, enabled_default_model):
    _set_model_state("base", status=ModelStatus.downloaded, is_enabled=True)

    with open(short_audio_file, "rb") as f:
        response = client.post(
            "/api/jobs",
            files={"file": ("chosen.wav", f, "audio/wav")},
            data={"model": "base"},
            headers=admin_headers,
        )
    assert response.status_code == 201
    assert response.json()["model_used"] == "base"


def test_create_job_with_unknown_model_rejected(client, admin_headers, short_audio_file, enabled_default_model):
    with open(short_audio_file, "rb") as f:
        response = client.post(
            "/api/jobs",
            files={"file": ("badmodel.wav", f, "audio/wav")},
            data={"model": "inconnu"},
            headers=admin_headers,
        )
    assert response.status_code == 400


def test_create_job_with_disabled_model_rejected(client, admin_headers, short_audio_file, enabled_default_model):
    # Téléchargé mais non activé : refusé pour un job utilisateur.
    _set_model_state("base", status=ModelStatus.downloaded, is_enabled=False)

    with open(short_audio_file, "rb") as f:
        response = client.post(
            "/api/jobs",
            files={"file": ("disabled.wav", f, "audio/wav")},
            data={"model": "base"},
            headers=admin_headers,
        )
    assert response.status_code == 400


# --- Téléchargement du résultat (vtt / txt) ---


def _finish_job_with_vtt(job_id: int) -> None:
    vtt_content = (
        "WEBVTT\n"
        "\n"
        "00:00:00.000 --> 00:00:02.000\n"
        "Bonjour.\n"
        "\n"
        "00:00:02.000 --> 00:00:04.000\n"
        "Ceci est un test.\n"
    )
    vtt_path = os.path.join(os.environ["TRANSCRIPTS_PATH"], f"{job_id}.vtt")
    os.makedirs(os.environ["TRANSCRIPTS_PATH"], exist_ok=True)
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(vtt_content)

    with Session(engine) as session:
        job = session.get(TranscriptionJob, job_id)
        job.status = JobStatus.done
        job.result_vtt_path = vtt_path
        session.add(job)
        session.commit()


def test_download_job_in_txt_format(client, admin_headers, short_audio_file, enabled_default_model):
    with open(short_audio_file, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            files={"file": ("as_txt.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    job_id = job_resp.json()["id"]
    _finish_job_with_vtt(job_id)

    response = client.get(f"/api/jobs/{job_id}/download?format=txt", headers=admin_headers)
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert response.text == "Bonjour.\n\nCeci est un test."
    assert 'filename="as_txt.txt"' in response.headers["content-disposition"]


def test_download_job_in_vtt_format_still_works(client, admin_headers, short_audio_file, enabled_default_model):
    with open(short_audio_file, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            files={"file": ("as_vtt.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    job_id = job_resp.json()["id"]
    _finish_job_with_vtt(job_id)

    response = client.get(f"/api/jobs/{job_id}/download", headers=admin_headers)
    assert response.status_code == 200
    assert "text/vtt" in response.headers["content-type"]
    assert "WEBVTT" in response.text

    response = client.get(f"/api/jobs/{job_id}/download?format=pdf", headers=admin_headers)
    assert response.status_code == 422


# --- Annulation ---


def test_cancel_pending_job(client, admin_headers, short_audio_file, enabled_default_model):
    with open(short_audio_file, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            files={"file": ("tocancel.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    job_id = job_resp.json()["id"]

    response = client.post(f"/api/jobs/{job_id}/cancel", headers=admin_headers)
    assert response.status_code == 202


def test_cancel_done_job_rejected(client, admin_headers, short_audio_file, enabled_default_model):
    with open(short_audio_file, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            files={"file": ("done.wav", f, "audio/wav")},
            headers=admin_headers,
        )
    job_id = job_resp.json()["id"]

    from app.core.database import engine
    from app.models.job import JobStatus

    with Session(engine) as session:
        job = session.get(TranscriptionJob, job_id)
        job.status = JobStatus.done
        session.add(job)
        session.commit()

    response = client.post(f"/api/jobs/{job_id}/cancel", headers=admin_headers)
    assert response.status_code == 409
