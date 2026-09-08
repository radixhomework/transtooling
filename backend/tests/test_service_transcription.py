"""Unit tests for the transcription service, called directly (no HTTP layer)."""

import asyncio
import os

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.core.security import hash_password
from app.models.job import JobStatus, TranscriptionJob
from app.models.user import User, UserRole
from app.models.whisper_model import ModelStatus, WhisperModel
from app.services import transcription_service


@pytest.fixture
def db_session(isolated_catalog):
    with Session(engine) as session:
        yield session


@pytest.fixture
def unit_user(db_session):
    login_name = "unit-transcription-user"
    user = db_session.exec(select(User).where(User.login == login_name)).first()
    if not user:
        user = User(login=login_name, password_hash=hash_password("SomePass123"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def default_model(db_session):
    name = "tiny"
    model = db_session.exec(select(WhisperModel).where(WhisperModel.name == name)).first()
    if not model:
        model = WhisperModel(name=name, status=ModelStatus.downloaded, is_enabled=True, is_default=True)
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)
    return model


class FakeUpload:
    """Minimal stand-in for Starlette's UploadFile: replays in-memory bytes."""

    def __init__(self, content: bytes, filename: str):
        self.filename = filename
        self._content = content

    async def read(self, size: int) -> bytes:
        chunk, self._content = self._content[:size], self._content[size:]
        return chunk


def _make_job(db_session, unit_user, **overrides) -> TranscriptionJob:
    fields = dict(
        user_id=unit_user.id,
        filename_original="audio.wav",
        model_used="tiny",
        language="fr",
        status=JobStatus.pending,
    )
    fields.update(overrides)
    job = TranscriptionJob(**fields)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ------------------------------------------------------------- create_job ---


@pytest.mark.parametrize("filename", ["audio.mp4", "audio", "audio.MP4", "audio.flac"])
def test_create_job_rejects_unsupported_extensions(db_session, unit_user, filename):
    upload = FakeUpload(b"whatever", filename)
    coro = transcription_service.create_job(
        db_session, unit_user, filename=filename, model=None, upload_file=upload
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(coro)
    assert exc_info.value.status_code == 400


def test_create_job_rejects_unknown_model(db_session, unit_user, default_model):
    upload = FakeUpload(b"whatever", "audio.wav")
    coro = transcription_service.create_job(
        db_session, unit_user, filename="audio.wav", model="nonexistent-model", upload_file=upload
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(coro)
    assert exc_info.value.status_code == 400


def test_create_job_rejects_oversized_upload(db_session, unit_user, default_model):
    from app.models.app_settings import AppSettings

    # Shrink the effective limit to 1 MB and push one more byte than that.
    row = db_session.get(AppSettings, 1)
    original = row.max_file_size_mb
    row.max_file_size_mb = 1
    db_session.add(row)
    db_session.commit()
    try:
        big = b"x" * (1024 * 1024 + 1)
        upload = FakeUpload(big, "audio.wav")
        coro = transcription_service.create_job(
            db_session, unit_user, filename="audio.wav", model=None, upload_file=upload
        )
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(coro)
        assert exc_info.value.status_code == 413
    finally:
        row.max_file_size_mb = original
        db_session.add(row)
        db_session.commit()


# ---------------------------------------------------------- get_owned_job ---


def test_get_owned_job_missing_raises_404(db_session, unit_user):
    with pytest.raises(HTTPException) as exc_info:
        transcription_service.get_owned_job(999999999, db_session, unit_user)
    assert exc_info.value.status_code == 404


def test_get_owned_job_other_users_job_raises_403(db_session, unit_user):
    other = User(login="unit-other-owner", password_hash=hash_password("SomePass123"))
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    job = _make_job(db_session, other)
    with pytest.raises(HTTPException) as exc_info:
        transcription_service.get_owned_job(job.id, db_session, unit_user)
    assert exc_info.value.status_code == 403


def test_get_owned_job_admin_sees_everything(db_session, unit_user):
    admin = User(login="unit-transcription-admin", password_hash=hash_password("SomePass123"), role=UserRole.admin)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    job = _make_job(db_session, unit_user)
    assert transcription_service.get_owned_job(job.id, db_session, admin).id == job.id


def test_get_owned_job_owner_can_read(db_session, unit_user):
    job = _make_job(db_session, unit_user)
    assert transcription_service.get_owned_job(job.id, db_session, unit_user).id == job.id


# ---------------------------------------------------------- request_cancel ---


def test_request_cancel_marks_pending_job(db_session, unit_user):
    job = _make_job(db_session, unit_user)
    transcription_service.request_cancel(db_session, job)
    db_session.refresh(job)
    assert job.cancel_requested is True


def test_request_cancel_rejects_done_job(db_session, unit_user):
    job = _make_job(db_session, unit_user, status=JobStatus.done)
    with pytest.raises(HTTPException) as exc_info:
        transcription_service.request_cancel(db_session, job)
    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------- delete ---


def test_delete_job_removes_row_and_files(db_session, unit_user):
    os.makedirs(settings.transcripts_path, exist_ok=True)
    vtt_path = os.path.join(settings.transcripts_path, "unit-delete.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n")
    audio_name = "unit-delete-audio.wav"
    audio_path = os.path.join(settings.audio_tmp_path, audio_name)
    with open(audio_path, "wb") as f:
        f.write(b"audio")

    job = _make_job(db_session, unit_user, result_vtt_path=vtt_path, audio_tmp_filename=audio_name)

    transcription_service.delete_job(db_session, job)

    assert db_session.get(TranscriptionJob, job.id) is None
    assert not os.path.exists(vtt_path)
    assert not os.path.exists(audio_path)


# --------------------------------------------------------------- results ---


def test_read_result_as_rejects_unfinished_job(db_session, unit_user):
    job = _make_job(db_session, unit_user, status=JobStatus.processing)
    with pytest.raises(HTTPException) as exc_info:
        transcription_service.read_result_as(job, "vtt")
    assert exc_info.value.status_code == 409


def test_read_result_as_txt_converts_vtt(db_session, unit_user):
    os.makedirs(settings.transcripts_path, exist_ok=True)
    vtt_path = os.path.join(settings.transcripts_path, "unit-txt.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nBonjour.\n\n00:00:02.000 --> 00:00:04.000\nSalut.\n")

    job = _make_job(db_session, unit_user, status=JobStatus.done, result_vtt_path=vtt_path)
    payload = transcription_service.read_result_as(job, "txt")

    assert payload["kind"] == "content"
    assert payload["filename"] == "audio.txt"
    assert payload["content"] == "Bonjour.\n\nSalut."


def test_read_result_as_vtt_returns_file_payload(db_session, unit_user):
    os.makedirs(settings.transcripts_path, exist_ok=True)
    vtt_path = os.path.join(settings.transcripts_path, "unit-vtt.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n")

    job = _make_job(db_session, unit_user, status=JobStatus.done, result_vtt_path=vtt_path)
    payload = transcription_service.read_result_as(job, "vtt")

    assert payload["kind"] == "file"
    assert payload["filename"] == "audio.vtt"
    assert os.path.exists(payload["path"])


# ------------------------------------------------------------ vtt_to_txt ---


def test_vtt_to_plain_text_strips_timestamps_and_header():
    vtt = (
        "WEBVTT\n"
        "\n"
        "00:00:00.000 --> 00:00:02.000\n"
        "Premier segment.\n"
        "\n"
        "00:00:02.000 --> 00:00:04.000\n"
        "Deuxième segment.\n"
    )
    assert transcription_service.vtt_to_plain_text(vtt) == "Premier segment.\n\nDeuxième segment."


def test_vtt_to_plain_text_joins_wrapped_lines():
    vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nligne une\nligne deux\n"
    assert transcription_service.vtt_to_plain_text(vtt) == "ligne une ligne deux"


def test_vtt_to_plain_text_empty_content():
    assert transcription_service.vtt_to_plain_text("") == ""
