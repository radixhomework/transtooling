from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings

# check_same_thread=False: required for SQLite used from several threads
# (FastAPI + workers accessing the same file through a shared volume).
engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Creates the tables if they do not exist yet."""
    # Models must be imported before create_all so they get registered in
    # SQLModel.metadata.
    from app.models import user, job, whisper_model, app_settings, translation  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_columns()
    _rename_legacy_columns()
    _upgrade_settings_defaults()


def _upgrade_settings_defaults() -> None:
    """Upgrades the default translatable extensions to a newer value
    (e.g. adding "md") for rows never customized: any admin-modified value
    is always preserved."""
    from sqlalchemy import text

    upgrades = (
        ("json,html,htm", "json,html,htm,md"),
    )
    with engine.begin() as conn:
        for old, new in upgrades:
            conn.execute(
                text(
                    "UPDATE appsettings SET translatable_extensions = :new "
                    "WHERE translatable_extensions = :old"
                ),
                {"old": old, "new": new},
            )


# Columns added after the initial schema creation. SQLModel never runs
# ALTER TABLE: create_all ignores an existing table, including its new
# columns. These ALTERs are therefore applied manually, idempotently, for
# already-deployed databases. Keep in sync with worker/app/main.py and
# translation-worker/app/main.py (shared database).
# NOT NULL columns carry a DEFAULT so the ALTER works on a table that
# already contains rows (SQLite).
_SCHEMA_PATCHES = {
    "transcriptionjob": {
        "audio_duration_seconds": "REAL",
        "progress": "INTEGER",
        "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
    },
    "translationjob": {
        "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
    },
    "whispermodel": {
        "download_progress": "INTEGER",
    },
    "appsettings": {
        "max_text_length_chars": "INTEGER NOT NULL DEFAULT 50000",
        "preview_truncate_chars": "INTEGER NOT NULL DEFAULT 2000",
        "max_archive_size_mb": "INTEGER NOT NULL DEFAULT 200",
        "max_archive_files_count": "INTEGER NOT NULL DEFAULT 500",
        "max_archive_uncompressed_mb": "INTEGER NOT NULL DEFAULT 500",
        "translatable_extensions": "TEXT NOT NULL DEFAULT 'json,html,htm,md'",
    },
}

# Columns renamed after the fact (SQLite >= 3.25: ALTER TABLE RENAME COLUMN).
_SCHEMA_RENAMES = {
    "user": {"email": "login"},
}


def _rename_legacy_columns() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    for table, renames in _SCHEMA_RENAMES.items():
        if table not in inspector.get_table_names():
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        for old_name, new_name in renames.items():
            if old_name in existing and new_name not in existing:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {table} RENAME COLUMN {old_name} TO {new_name}")
                    )


def _ensure_columns() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    for table, columns in _SCHEMA_PATCHES.items():
        if table not in inspector.get_table_names():
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column, ddl_type in columns.items():
            if column in existing:
                continue
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
                )


def get_session():
    with Session(engine) as session:
        yield session
