"""Unit tests for the translation service, called directly (no HTTP layer)."""

import asyncio
import json
import os
import zipfile

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.core.security import hash_password
from app.models.app_settings import AppSettings
from app.models.translation import (
    TranslationJob,
    TranslationJobStatus,
    TranslationJobType,
    TranslationModel,
    TranslationModelStatus,
)
from app.models.user import User
from app.services import translation_service


@pytest.fixture()
def db_session(isolated_catalog):
    with Session(engine) as session:
        yield session


@pytest.fixture()
def unit_user(db_session):
    login_name = "unit-translation-user"
    user = db_session.exec(select(User).where(User.login == login_name)).first()
    if not user:
        user = User(login=login_name, password_hash=hash_password("SomePass123"))
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture()
def enabled_model(db_session):
    direction = "fr-en"
    model = db_session.exec(
        select(TranslationModel).where(TranslationModel.direction == direction)
    ).first()
    if not model:
        model = TranslationModel(direction=direction)
    model.status = TranslationModelStatus.downloaded
    model.is_enabled = True
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


class FakeUpload:
    def __init__(self, content: bytes, filename: str):
        self.filename = filename
        self._content = content

    async def read(self, size: int) -> bytes:
        chunk, self._content = self._content[:size], self._content[size:]
        return chunk


def _make_zip(path: str, entries: dict, encrypted_name: str | None = None) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)


# ------------------------------------------------------------ models admin ---


def test_list_enabled_models_only_downloaded_and_enabled(db_session, enabled_model):
    # A downloaded-but-disabled model must not be listed.
    other = TranslationModel(direction="en-fr", status=TranslationModelStatus.downloaded)
    db_session.add(other)
    db_session.commit()

    directions = [m.direction.value for m in translation_service.list_enabled_models(db_session)]
    assert enabled_model.direction.value in directions
    assert "en-fr" not in directions

    db_session.delete(other)
    db_session.commit()


def test_list_models_with_rows_ensured_creates_all_directions(db_session):
    rows = translation_service.list_models_with_rows_ensured(db_session)
    directions = {r.direction.value for r in rows}
    assert {"fr-en", "en-fr"} <= directions


def test_request_model_download_rejects_unknown_direction(db_session):
    with pytest.raises(HTTPException) as exc_info:
        translation_service.request_model_download(db_session, "xx-yy")
    assert exc_info.value.status_code == 400


def test_request_model_download_rejects_already_downloaded(db_session, enabled_model):
    with pytest.raises(HTTPException) as exc_info:
        translation_service.request_model_download(db_session, enabled_model.direction.value)
    assert exc_info.value.status_code == 400


def test_request_model_download_sets_downloading(db_session):
    model = translation_service.request_model_download(db_session, "fr-en")
    db_session.refresh(model)
    assert model.status == TranslationModelStatus.downloading
    assert model.download_progress == 0


def test_request_model_deletion_requires_downloaded_model(db_session):
    model = translation_service.request_model_download(db_session, "en-fr")
    with pytest.raises(HTTPException) as exc_info:
        translation_service.request_model_deletion(db_session, model.direction.value)
    assert exc_info.value.status_code == 400


def test_update_model_requires_downloaded_model_to_enable(db_session):
    model = translation_service.request_model_download(db_session, "fr-en")
    with pytest.raises(HTTPException) as exc_info:
        translation_service.update_model(db_session, model.direction.value, True)
    assert exc_info.value.status_code == 400


def test_update_model_missing_raises_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        translation_service.update_model(db_session, "xx-yy", True)
    assert exc_info.value.status_code == 404


# ----------------------------------------------------------------- jobs ---


def test_create_text_job_rejects_unknown_direction(db_session, unit_user, enabled_model):
    with pytest.raises(HTTPException) as exc_info:
        translation_service.create_text_job(db_session, unit_user, "xx-yy", "hello")
    assert exc_info.value.status_code == 400


def test_create_text_job_rejects_overlong_text(db_session, unit_user, enabled_model):
    row = db_session.get(AppSettings, 1)
    original = row.max_text_length_chars
    row.max_text_length_chars = 10
    db_session.add(row)
    db_session.commit()
    try:
        with pytest.raises(HTTPException) as exc_info:
            translation_service.create_text_job(db_session, unit_user, "fr-en", "x" * 11)
        assert exc_info.value.status_code == 413
    finally:
        row.max_text_length_chars = original
        db_session.add(row)
        db_session.commit()


def test_create_text_job_requires_enabled_model(db_session, unit_user):
    with pytest.raises(HTTPException) as exc_info:
        translation_service.create_text_job(db_session, unit_user, "en-fr", "hello")
    assert exc_info.value.status_code == 503


def test_create_text_job_persists_pending_job(db_session, unit_user, enabled_model):
    job = translation_service.create_text_job(db_session, unit_user, "fr-en", "Bonjour")
    assert job.status == TranslationJobStatus.pending
    assert job.job_type == TranslationJobType.text
    assert job.source_text == "Bonjour"


async def _create_archive(db_session, unit_user, model, tmp_path, entries, filename="archive.zip"):
    zip_path = os.path.join(tmp_path, "in.zip")
    _make_zip(zip_path, entries)
    with open(zip_path, "rb") as f:
        content = f.read()
    upload = FakeUpload(content, filename)
    return await translation_service.create_archive_job(
        db_session, unit_user, "fr-en", filename, upload
    )


def test_create_archive_job_stores_pending_job(db_session, unit_user, enabled_model, tmp_path):
    job = asyncio.run(_create_archive(db_session, unit_user, enabled_model, tmp_path, {"a.txt": "hi"}))
    assert job.status == TranslationJobStatus.pending
    assert job.job_type == TranslationJobType.archive
    stored = os.path.join(settings.translation_tmp_path, job.archive_tmp_filename)
    assert os.path.exists(stored)

    translation_service.delete_job(db_session, job)


def test_create_archive_job_rejects_non_zip(db_session, unit_user, enabled_model):
    upload = FakeUpload(b"plain", "archive.tar")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            translation_service.create_archive_job(
                db_session, unit_user, "fr-en", "archive.tar", upload
            )
        )
    assert exc_info.value.status_code == 400


def test_create_archive_job_cleans_up_on_invalid_zip(db_session, unit_user, enabled_model):
    upload = FakeUpload(b"not a zip", "archive.zip")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            translation_service.create_archive_job(
                db_session, unit_user, "fr-en", "archive.zip", upload
            )
        )
    assert exc_info.value.status_code == 400
    leftovers = [f for f in os.listdir(settings.translation_tmp_path) if f.endswith(".zip")]
    assert leftovers == []


# ------------------------------------------------------ validate_zip_safety ---


def test_validate_zip_safety_rejects_too_many_files(db_session, tmp_path):
    row = db_session.get(AppSettings, 1)
    limits = row
    zip_path = os.path.join(tmp_path, "many.zip")
    _make_zip(zip_path, {f"f{i}.txt": "x" for i in range(limits.max_archive_files_count + 1)})

    with pytest.raises(HTTPException) as exc_info:
        translation_service.validate_zip_safety(zip_path, limits)
    assert exc_info.value.status_code == 413


def test_validate_zip_safety_rejects_uncompressed_overflow(db_session, tmp_path):
    limits = db_session.get(AppSettings, 1)
    zip_path = os.path.join(tmp_path, "bomb.zip")
    # One entry bigger than the uncompressed limit (zeros compress well).
    big = b"\x00" * (limits.max_archive_uncompressed_mb * 1024 * 1024 + 1)
    _make_zip(zip_path, {"big.bin": big})

    with pytest.raises(HTTPException) as exc_info:
        translation_service.validate_zip_safety(zip_path, limits)
    assert exc_info.value.status_code == 413


def test_validate_zip_safety_rejects_zip_slip(db_session, tmp_path):
    limits = db_session.get(AppSettings, 1)
    zip_path = os.path.join(tmp_path, "slip.zip")
    _make_zip(zip_path, {"../evil.txt": "x"})

    with pytest.raises(HTTPException) as exc_info:
        translation_service.validate_zip_safety(zip_path, limits)
    assert exc_info.value.status_code == 400


def test_validate_zip_safety_rejects_encrypted_entries(db_session, tmp_path):
    limits = db_session.get(AppSettings, 1)
    zip_path = os.path.join(tmp_path, "enc.zip")
    _make_zip(zip_path, {"a.txt": "x"})
    # Flip the "encrypted" general-purpose bit manually on the entry.
    with open(zip_path, "r+b") as f:
        data = bytearray(f.read())
        # Set bit 0 (encrypted) of the general-purpose flags in BOTH the
        # local file header and the central directory entry, since
        # zipfile.infolist() reads the flags from the central directory.
        idx = data.find(b"PK\x03\x04")
        flags = int.from_bytes(data[idx + 6 : idx + 8], "little") | 0x1
        data[idx + 6 : idx + 8] = flags.to_bytes(2, "little")
        idx = data.find(b"PK\x01\x02")
        flags = int.from_bytes(data[idx + 8 : idx + 10], "little") | 0x1
        data[idx + 8 : idx + 10] = flags.to_bytes(2, "little")
        f.seek(0)
        f.write(data)

    with pytest.raises(HTTPException) as exc_info:
        translation_service.validate_zip_safety(zip_path, limits)
    assert exc_info.value.status_code == 400


def test_validate_zip_safety_accepts_a_valid_archive(db_session, tmp_path):
    limits = db_session.get(AppSettings, 1)
    zip_path = os.path.join(tmp_path, "ok.zip")
    _make_zip(zip_path, {"sub/dir/a.txt": "hello", "b.json": "{}"})

    translation_service.validate_zip_safety(zip_path, limits)  # must not raise


# ------------------------------------------------------- responses/lifecycle ---


def test_job_to_response_truncates_preview(db_session, unit_user):
    limits = db_session.get(AppSettings, 1)
    limits.preview_truncate_chars = 5
    db_session.add(limits)
    db_session.commit()

    job = TranslationJob(
        user_id=unit_user.id,
        job_type=TranslationJobType.text,
        direction="fr-en",
        status=TranslationJobStatus.done,
        result_text="abcdefghij",
        report_json=json.dumps({"translated": 1, "copied": 0, "errors": 0}),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    data = translation_service.job_to_response(job, limits)
    assert data["result_preview"] == "abcde"
    assert data["result_truncated"] is True
    assert data["report"] == {"translated": 1, "copied": 0, "errors": 0}


def test_job_to_response_without_result(db_session, unit_user):
    limits = db_session.get(AppSettings, 1)
    job = TranslationJob(
        user_id=unit_user.id,
        job_type=TranslationJobType.text,
        direction="fr-en",
        status=TranslationJobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    data = translation_service.job_to_response(job, limits)
    assert data["result_preview"] is None
    assert data["result_truncated"] is False
    assert data["report"] is None


def test_request_cancel_rejects_done_job(db_session, unit_user):
    job = TranslationJob(
        user_id=unit_user.id,
        job_type=TranslationJobType.text,
        direction="fr-en",
        status=TranslationJobStatus.done,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    with pytest.raises(HTTPException) as exc_info:
        translation_service.request_cancel(db_session, job)
    assert exc_info.value.status_code == 409


def test_read_result_rejects_unfinished_job(db_session, unit_user):
    job = TranslationJob(
        user_id=unit_user.id,
        job_type=TranslationJobType.text,
        direction="fr-en",
        status=TranslationJobStatus.processing,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    with pytest.raises(HTTPException) as exc_info:
        translation_service.read_result(job)
    assert exc_info.value.status_code == 409


def test_read_result_text_job_returns_content(db_session, unit_user):
    job = TranslationJob(
        user_id=unit_user.id,
        job_type=TranslationJobType.text,
        direction="fr-en",
        status=TranslationJobStatus.done,
        result_text="Bonjour",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    payload = translation_service.read_result(job)
    assert payload["kind"] == "content"
    assert payload["content"] == "Bonjour"


def test_read_result_archive_job_missing_file_raises_404(db_session, unit_user):
    job = TranslationJob(
        user_id=unit_user.id,
        job_type=TranslationJobType.archive,
        direction="fr-en",
        status=TranslationJobStatus.done,
        result_zip_path=os.path.join(tmp_dir_never(), "missing.zip"),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    with pytest.raises(HTTPException) as exc_info:
        translation_service.read_result(job)
    assert exc_info.value.status_code == 404


def test_delete_job_removes_zip_and_archive(db_session, unit_user):
    os.makedirs(settings.translations_path, exist_ok=True)
    os.makedirs(settings.translation_tmp_path, exist_ok=True)
    zip_path = os.path.join(settings.translations_path, "unit-del.zip")
    with open(zip_path, "wb") as f:
        f.write(b"PK")
    archive_name = "unit-del-in.zip"
    archive_path = os.path.join(settings.translation_tmp_path, archive_name)
    with open(archive_path, "wb") as f:
        f.write(b"PK")

    job = TranslationJob(
        user_id=unit_user.id,
        job_type=TranslationJobType.archive,
        direction="fr-en",
        status=TranslationJobStatus.done,
        result_zip_path=zip_path,
        archive_tmp_filename=archive_name,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    translation_service.delete_job(db_session, job)
    assert not os.path.exists(zip_path)
    assert not os.path.exists(archive_path)


def tmp_dir_never() -> str:
    return os.path.join(settings.translations_path, "does-not-exist")
