"""Unit tests for the app_settings service, called directly (no HTTP layer)."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from app.core.database import engine
from app.models.app_settings import AppSettings
from app.schemas import AppSettingsUpdateRequest
from app.services import app_settings_service


@pytest.fixture()
def db_session(isolated_catalog):
    with Session(engine) as session:
        yield session


def test_get_settings_row_creates_safety_net_row_when_missing(db_session):
    row = db_session.get(AppSettings, 1)
    if row:
        db_session.delete(row)
        db_session.commit()

    created = app_settings_service.get_settings_row(db_session)

    assert created.id == 1
    assert created.max_file_size_mb > 0


def test_get_settings_row_or_raise_fails_when_missing(db_session):
    row = db_session.get(AppSettings, 1)
    if row:
        db_session.delete(row)
        db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        app_settings_service.get_settings_row_or_raise(db_session)
    assert exc_info.value.status_code == 500


def test_get_settings_row_or_raise_returns_row(db_session):
    app_settings_service.get_settings_row(db_session)  # ensure it exists
    row = app_settings_service.get_settings_row_or_raise(db_session)
    assert row.id == 1


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("json,html,htm", "json,html,htm"),
        ("json, HTML, .htm", "json,html,htm"),
        ("  md  , , TXT, ", "md,txt"),
        (".json", "json"),
        ("", ""),
        (",,", ""),
    ],
)
def test_normalize_extensions(raw, expected):
    assert app_settings_service.normalize_extensions(raw) == expected


def test_update_settings_rejects_non_positive_values(db_session):
    app_settings_service.get_settings_row(db_session)
    payload = AppSettingsUpdateRequest(max_file_size_mb=0)
    with pytest.raises(HTTPException) as exc_info:
        app_settings_service.update_settings(db_session, payload)
    assert exc_info.value.status_code == 400


def test_update_settings_rejects_empty_extensions(db_session):
    app_settings_service.get_settings_row(db_session)
    payload = AppSettingsUpdateRequest(translatable_extensions=" , ")
    with pytest.raises(HTTPException) as exc_info:
        app_settings_service.update_settings(db_session, payload)
    assert exc_info.value.status_code == 400


def test_update_settings_normalizes_and_persists(db_session):
    app_settings_service.get_settings_row(db_session)
    payload = AppSettingsUpdateRequest(
        max_text_length_chars=12345,
        translatable_extensions=" JSON, .Md ",
    )
    row = app_settings_service.update_settings(db_session, payload)

    assert row.max_text_length_chars == 12345
    assert row.translatable_extensions == "json,md"

    db_session.refresh(row)
    assert row.max_text_length_chars == 12345


def test_ensure_app_settings_is_idempotent():
    app_settings_service.ensure_app_settings()
    app_settings_service.ensure_app_settings()  # must not raise / duplicate

    with Session(engine) as session:
        rows = session.query(AppSettings).filter(AppSettings.id == 1).all()
        assert len(rows) == 1
