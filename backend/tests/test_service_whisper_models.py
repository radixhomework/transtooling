"""Unit tests for the whisper model service, called directly (no HTTP layer)."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.database import engine
from app.models.whisper_model import ModelStatus, WhisperModel
from app.services import whisper_model_service


@pytest.fixture
def db_session(isolated_catalog):
    with Session(engine) as session:
        yield session


def _get_model(db_session, name) -> WhisperModel:
    model = db_session.exec(select(WhisperModel).where(WhisperModel.name == name)).first()
    if not model:
        model = WhisperModel(name=name)
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)
    return model


def _make_downloaded(db_session, name, is_enabled=True, is_default=False) -> WhisperModel:
    model = _get_model(db_session, name)
    model.status = ModelStatus.downloaded
    model.is_enabled = is_enabled
    model.is_default = is_default
    model.disk_size_mb = 100
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


def test_list_models_with_rows_ensured_creates_known_models(db_session):
    rows = whisper_model_service.list_models_with_rows_ensured(db_session)
    names = {r.name for r in rows}
    assert {"tiny", "base", "small", "medium", "large-v3"} <= names


def test_request_download_rejects_unknown_name(db_session):
    with pytest.raises(HTTPException) as exc_info:
        whisper_model_service.request_download(db_session, "giant")
    assert exc_info.value.status_code == 400


def test_request_download_rejects_downloaded_model(db_session):
    model = _make_downloaded(db_session, "base")
    with pytest.raises(HTTPException) as exc_info:
        whisper_model_service.request_download(db_session, model.name)
    assert exc_info.value.status_code == 400


def test_request_download_sets_downloading_state(db_session):
    # Force a clean "not downloaded" start: the shared test database may
    # carry over a downloaded state from other tests.
    model = _get_model(db_session, "base")
    model.status = ModelStatus.not_downloaded
    db_session.add(model)
    db_session.commit()

    model = whisper_model_service.request_download(db_session, "base")
    db_session.refresh(model)
    assert model.status == ModelStatus.downloading
    assert model.download_progress == 0
    assert model.error_message is None


def test_request_deletion_requires_downloaded_model(db_session):
    model = whisper_model_service.request_download(db_session, "small")
    with pytest.raises(HTTPException) as exc_info:
        whisper_model_service.request_deletion(db_session, model.name)
    assert exc_info.value.status_code == 400


def test_request_deletion_forbidden_for_default_model(db_session):
    _make_downloaded(db_session, "small", is_default=True)
    with pytest.raises(HTTPException) as exc_info:
        whisper_model_service.request_deletion(db_session, "small")
    assert exc_info.value.status_code == 400


def test_request_deletion_resets_model_state(db_session):
    model = _make_downloaded(db_session, "small")
    updated = whisper_model_service.request_deletion(db_session, model.name)
    db_session.refresh(updated)
    assert updated.status == ModelStatus.not_downloaded
    assert updated.is_enabled is False
    assert updated.download_progress is None
    assert updated.disk_size_mb is None


def test_update_enable_requires_downloaded_model(db_session):
    model = _get_model(db_session, "medium")  # not downloaded
    with pytest.raises(HTTPException) as exc_info:
        whisper_model_service.update_model(db_session, model.name, is_enabled=True, is_default=None)
    assert exc_info.value.status_code == 400


def test_update_cannot_disable_default_model(db_session):
    _make_downloaded(db_session, "medium", is_default=True)
    with pytest.raises(HTTPException) as exc_info:
        whisper_model_service.update_model(db_session, "medium", is_enabled=False, is_default=None)
    assert exc_info.value.status_code == 400


def test_update_set_default_resets_other_defaults(db_session):
    _make_downloaded(db_session, "medium", is_default=True)
    challenger = _make_downloaded(db_session, "base", is_enabled=True)

    updated = whisper_model_service.update_model(db_session, "base", is_enabled=None, is_default=True)

    db_session.refresh(updated)
    assert updated.is_default is True
    assert updated.is_enabled is True

    former = db_session.exec(select(WhisperModel).where(WhisperModel.name == "medium")).first()
    db_session.refresh(former)
    assert former.is_default is False


def test_update_missing_model_raises_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        whisper_model_service.update_model(db_session, "giant", is_enabled=True, is_default=None)
    assert exc_info.value.status_code == 404


def test_list_enabled_models_filters_correctly(db_session):
    _make_downloaded(db_session, "base", is_enabled=True)
    _make_downloaded(db_session, "small", is_enabled=False)
    not_downloaded = _get_model(db_session, "medium")

    names = [m.name for m in whisper_model_service.list_enabled_models(db_session)]
    assert "base" in names
    assert "small" not in names  # disabled
    assert "medium" not in names  # not downloaded
    assert not_downloaded.status != ModelStatus.downloaded
