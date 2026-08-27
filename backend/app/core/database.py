from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings

# check_same_thread=False : nécessaire pour SQLite utilisé depuis plusieurs
# threads (FastAPI + worker accédant au même fichier via volume partagé).
engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Crée les tables si elles n'existent pas encore."""
    # Les modèles doivent être importés avant create_all pour être enregistrés
    # dans SQLModel.metadata.
    from app.models import user, job, whisper_model, app_settings, translation  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _ensure_columns()
    _rename_legacy_columns()
    _upgrade_settings_defaults()


def _upgrade_settings_defaults() -> None:
    """Fait passer les extensions traduisibles par défaut à une valeur plus
    récente (ex. ajout de « md ») pour les lignes jamais personnalisées :
    une valeur modifiée par l'admin est toujours préservée."""
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


# Colonnes ajoutées après la création initiale du schéma. SQLModel ne fait
# jamais d'ALTER TABLE : create_all ignore une table existante, y compris ses
# nouvelles colonnes. Ces ALTER sont donc joués manuellement, de façon
# idempotente, pour les bases déjà déployées. À maintenir en cohérence avec
# worker/app/main.py et translation-worker/app/main.py (base partagée).
# Les colonnes NOT NULL portent un DEFAULT pour que l'ALTER fonctionne sur
# une table contenant déjà des lignes (SQLite).
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

# Colonnes renommées après coup (SQLite >= 3.25 : ALTER TABLE RENAME COLUMN).
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
