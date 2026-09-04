import os
import subprocess
import tempfile

import pytest
from fastapi.testclient import TestClient

# Environment variables must be set BEFORE importing the application,
# because app.core.config.settings and app.core.database.engine are
# initialized at module load time.
_tmp_dir = tempfile.mkdtemp(prefix="transcription-tests-")
os.environ["SQLITE_PATH"] = os.path.join(_tmp_dir, "test.db")
os.environ["AUDIO_TMP_PATH"] = os.path.join(_tmp_dir, "audio_tmp")
os.environ["TRANSCRIPTS_PATH"] = os.path.join(_tmp_dir, "transcripts")
os.environ["WHISPER_MODELS_PATH"] = os.path.join(_tmp_dir, "models")
os.environ["TRANSLATION_TMP_PATH"] = os.path.join(_tmp_dir, "translation_tmp")
os.environ["TRANSLATIONS_PATH"] = os.path.join(_tmp_dir, "translations_out")
os.environ["ADMIN_LOGIN"] = "admin"
os.environ["ADMIN_PASSWORD"] = "AdminPass123"
os.environ["JWT_SECRET"] = "test-secret-key"

from app.main import app  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.models.whisper_model import WhisperModel, ModelStatus  # noqa: E402
from sqlmodel import Session  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client):
    response = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "AdminPass123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def enabled_default_model():
    """
    Inserts a Whisper model row directly in the database, marked as
    downloaded, enabled and default, so jobs can be created without an
    actual faster-whisper download (too heavy for unit tests).
    """
    from sqlmodel import select

    with Session(engine) as session:
        existing = session.exec(select(WhisperModel).where(WhisperModel.name == "tiny")).first()
        if existing:
            return existing.name

        model = WhisperModel(
            name="tiny",
            status=ModelStatus.downloaded,
            is_enabled=True,
            is_default=True,
        )
        session.add(model)
        session.commit()
        return "tiny"


def _generate_audio_file(path: str, duration_seconds: int, fmt: str = "wav") -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration_seconds}",
            "-ar", "16000",
            "-ac", "1",
            path,
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )


@pytest.fixture()
def short_audio_file():
    """Valid audio file of ~1 second (well under the default limits)."""
    path = os.path.join(_tmp_dir, "short_audio.wav")
    _generate_audio_file(path, duration_seconds=1)
    yield path


@pytest.fixture()
def invalid_audio_file():
    """File with a valid audio extension but unusable content."""
    path = os.path.join(_tmp_dir, "invalid_audio.wav")
    with open(path, "wb") as f:
        f.write(b"this is not a real audio file")
    yield path
