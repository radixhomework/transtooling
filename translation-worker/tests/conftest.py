import os
import tempfile

import pytest
from sqlmodel import Session, SQLModel, create_engine

_tmp_dir = tempfile.mkdtemp(prefix="translation-worker-tests-")
os.environ["SQLITE_PATH"] = os.path.join(_tmp_dir, "test.db")
os.environ["TRANSLATION_MODELS_PATH"] = os.path.join(_tmp_dir, "models")
os.environ["TRANSLATION_TMP_PATH"] = os.path.join(_tmp_dir, "tmp")
os.environ["TRANSLATIONS_PATH"] = os.path.join(_tmp_dir, "results")
os.environ["POLL_INTERVAL_SECONDS"] = "1"

os.makedirs(os.environ["TRANSLATION_TMP_PATH"], exist_ok=True)
os.makedirs(os.environ["TRANSLATIONS_PATH"], exist_ok=True)

from app import main as worker_main  # noqa: E402
from app.models import AppSettings, TranslationJob  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_database():
    """Recrée les tables avant chaque test pour repartir d'un état propre."""
    SQLModel.metadata.drop_all(worker_main.engine_db)
    SQLModel.metadata.create_all(worker_main.engine_db)
    with Session(worker_main.engine_db) as session:
        session.add(
            AppSettings(
                id=1,
                max_file_size_mb=200,
                max_duration_min=60,
                translatable_extensions="json,html,htm,md",
            )
        )
        session.commit()
    yield


@pytest.fixture()
def db_session():
    with Session(worker_main.engine_db) as session:
        yield session


class FakeEngine:
    """Moteur de traduction factice : préfixe chaque texte traduit."""

    def __init__(self):
        self.calls: list = []

    def translate(self, texts, should_continue=None):
        self.calls.append(list(texts))
        return [f"[TR]{text}" for text in texts]


@pytest.fixture()
def fake_engine(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(worker_main, "_get_engine", lambda direction: engine)
    return engine


def make_text_job(job_id=1, direction="fr-en", text="Bonjour le monde.", **kwargs):
    return TranslationJob(
        id=job_id,
        user_id=1,
        job_type="text",
        direction=direction,
        source_text=text,
        status="pending",
        **kwargs,
    )


def make_zip_file(files: dict, path: str) -> str:
    """Crée une archive ZIP de test ({nom: contenu}) et retourne son chemin."""
    import zipfile

    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return path
