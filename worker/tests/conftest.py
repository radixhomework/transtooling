import os
import tempfile

import pytest
from sqlmodel import Session, SQLModel, create_engine

_tmp_dir = tempfile.mkdtemp(prefix="transcription-worker-tests-")
os.environ["SQLITE_PATH"] = os.path.join(_tmp_dir, "test.db")
os.environ["AUDIO_TMP_PATH"] = os.path.join(_tmp_dir, "audio_tmp")
os.environ["TRANSCRIPTS_PATH"] = os.path.join(_tmp_dir, "transcripts")
os.environ["WHISPER_MODELS_PATH"] = os.path.join(_tmp_dir, "models")
os.environ["POLL_INTERVAL_SECONDS"] = "1"

os.makedirs(os.environ["AUDIO_TMP_PATH"], exist_ok=True)
os.makedirs(os.environ["TRANSCRIPTS_PATH"], exist_ok=True)

from app import main as worker_main  # noqa: E402
from app.models import TranscriptionJob, WhisperModel  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_database():
    """Recrée les tables avant chaque test pour repartir d'un état propre."""
    SQLModel.metadata.drop_all(worker_main.engine)
    SQLModel.metadata.create_all(worker_main.engine)
    yield


@pytest.fixture()
def db_session():
    with Session(worker_main.engine) as session:
        yield session


@pytest.fixture()
def make_audio_file():
    """Crée un fichier audio factice (contenu arbitraire) dans AUDIO_TMP_PATH."""
    def _make(filename: str, content: bytes = b"fake audio content") -> str:
        path = os.path.join(os.environ["AUDIO_TMP_PATH"], filename)
        with open(path, "wb") as f:
            f.write(content)
        return path
    return _make
