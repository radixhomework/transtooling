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
from app.core.database import engine, init_db  # noqa: E402
from app.models.whisper_model import WhisperModel, ModelStatus  # noqa: E402
from sqlmodel import Session  # noqa: E402


@pytest.fixture(autouse=True)
def _initialized_database():
    """Service-level unit tests never start the ASGI app, so make sure the
    schema exists. init_db() is idempotent (CREATE TABLE IF NOT EXISTS)."""
    init_db()
    yield


@pytest.fixture()
def isolated_catalog():
    """Snapshot-and-restore of the shared catalog tables (models, settings,
    jobs). Service unit tests request it (via their db_session fixture) so
    their mutations stay invisible to the other tests regardless of the
    execution order."""
    from sqlmodel import select

    from app.models.app_settings import AppSettings
    from app.models.job import TranscriptionJob
    from app.models.translation import TranslationJob, TranslationModel
    from app.models.whisper_model import WhisperModel

    with Session(engine) as session:
        whisper_snap = [
            (
                r.name, r.status, r.is_enabled, r.is_default, r.disk_size_mb,
                r.download_progress, r.error_message, r.downloaded_at,
            )
            for r in session.exec(select(WhisperModel)).all()
        ]
        translation_snap = [
            (
                r.direction.value, r.status, r.is_enabled, r.disk_size_mb,
                r.download_progress, r.error_message, r.downloaded_at,
            )
            for r in session.exec(select(TranslationModel)).all()
        ]
        settings_row = session.get(AppSettings, 1)
        if settings_row is None:
            # Some tests delete the singleton row on purpose; re-create it so
            # the snapshot below always has values to restore.
            from app.services.app_settings_service import get_settings_row

            settings_row = get_settings_row(session)
        settings_snap = (
            settings_row.max_file_size_mb,
            settings_row.max_duration_min,
            settings_row.max_text_length_chars,
            settings_row.preview_truncate_chars,
            settings_row.max_archive_size_mb,
            settings_row.max_archive_files_count,
            settings_row.max_archive_uncompressed_mb,
            settings_row.translatable_extensions,
        )
        transcription_job_ids = {r.id for r in session.exec(select(TranscriptionJob)).all()}
        translation_job_ids = {r.id for r in session.exec(select(TranslationJob)).all()}

    yield

    with Session(engine) as session:
        for job in session.exec(select(TranscriptionJob)).all():
            if job.id not in transcription_job_ids:
                session.delete(job)
        for job in session.exec(select(TranslationJob)).all():
            if job.id not in translation_job_ids:
                session.delete(job)

        for row in session.exec(select(WhisperModel)).all():
            snap = next((s for s in whisper_snap if s[0] == row.name), None)
            if snap is None:
                session.delete(row)
                continue
            (_, status, is_enabled, is_default, disk, progress, error, downloaded_at) = snap
            row.status = status
            row.is_enabled = is_enabled
            row.is_default = is_default
            row.disk_size_mb = disk
            row.download_progress = progress
            row.error_message = error
            row.downloaded_at = downloaded_at
            session.add(row)

        for row in session.exec(select(TranslationModel)).all():
            snap = next((s for s in translation_snap if s[0] == row.direction.value), None)
            if snap is None:
                session.delete(row)
                continue
            (_, status, is_enabled, disk, progress, error, downloaded_at) = snap
            row.status = status
            row.is_enabled = is_enabled
            row.disk_size_mb = disk
            row.download_progress = progress
            row.error_message = error
            row.downloaded_at = downloaded_at
            session.add(row)

        row = session.get(AppSettings, 1)
        if row is None:
            row = AppSettings(id=1)
        (
            row.max_file_size_mb,
            row.max_duration_min,
            row.max_text_length_chars,
            row.preview_truncate_chars,
            row.max_archive_size_mb,
            row.max_archive_files_count,
            row.max_archive_uncompressed_mb,
            row.translatable_extensions,
        ) = settings_snap
        session.add(row)
        session.commit()


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
