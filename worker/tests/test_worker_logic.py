from dataclasses import dataclass

from sqlmodel import Session

from app import main as worker_main
from app.models import JobStatus, ModelStatus, TranscriptionJob, WhisperModel


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str


@dataclass
class FakeInfo:
    duration: float


class FakeWhisperModel:
    """Simule faster_whisper.WhisperModel.transcribe sans charger de vrai modèle."""

    def transcribe(self, audio_path, language="fr"):
        segments = [
            FakeSegment(start=0.0, end=1.0, text="Bonjour."),
            FakeSegment(start=1.0, end=2.0, text="Ceci est un test."),
        ]
        return iter(segments), FakeInfo(duration=2.0)


def test_process_pending_job_success(db_session, make_audio_file, monkeypatch):
    audio_path = make_audio_file("1.wav")
    job = TranscriptionJob(
        id=1,
        user_id=1,
        filename_original="test.wav",
        model_used="tiny",
        audio_tmp_filename="1.wav",
        status=JobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: FakeWhisperModel())

    processed = worker_main.process_pending_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == JobStatus.done
    assert job.result_vtt_path is not None
    assert job.audio_tmp_filename is None
    assert job.progress == 100
    assert not __import__("os").path.exists(audio_path)  # audio supprimé après traitement

    with open(job.result_vtt_path, encoding="utf-8") as f:
        content = f.read()
    assert "WEBVTT" in content
    assert "Bonjour." in content


def test_process_pending_job_no_pending_returns_false(db_session):
    processed = worker_main.process_pending_job(db_session)
    assert processed is False


def test_process_pending_job_missing_audio_marks_error(db_session, monkeypatch):
    job = TranscriptionJob(
        id=2,
        user_id=1,
        filename_original="missing.wav",
        model_used="tiny",
        audio_tmp_filename="does_not_exist.wav",
        status=JobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: FakeWhisperModel())

    processed = worker_main.process_pending_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == JobStatus.error
    assert "introuvable" in job.error_message.lower()


def test_process_pending_job_transcription_error_marks_error(db_session, make_audio_file, monkeypatch):
    make_audio_file("3.wav")
    job = TranscriptionJob(
        id=3,
        user_id=1,
        filename_original="broken.wav",
        model_used="tiny",
        audio_tmp_filename="3.wav",
        status=JobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()

    class FailingModel:
        def transcribe(self, audio_path, language="fr"):
            raise RuntimeError("Erreur simulée de transcription")

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: FailingModel())

    processed = worker_main.process_pending_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == JobStatus.error
    assert "simulée" in job.error_message

    import os
    assert not os.path.exists(os.path.join(os.environ["AUDIO_TMP_PATH"], "3.wav"))


def test_process_pending_job_picks_oldest_first(db_session, make_audio_file, monkeypatch):
    from datetime import datetime, timedelta

    make_audio_file("10.wav")
    make_audio_file("11.wav")

    older = TranscriptionJob(
        id=10,
        user_id=1,
        filename_original="older.wav",
        model_used="tiny",
        audio_tmp_filename="10.wav",
        status=JobStatus.pending,
        created_at=datetime.utcnow() - timedelta(minutes=5),
    )
    newer = TranscriptionJob(
        id=11,
        user_id=1,
        filename_original="newer.wav",
        model_used="tiny",
        audio_tmp_filename="11.wav",
        status=JobStatus.pending,
        created_at=datetime.utcnow(),
    )
    db_session.add(older)
    db_session.add(newer)
    db_session.commit()

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: FakeWhisperModel())
    worker_main.process_pending_job(db_session)

    db_session.refresh(older)
    db_session.refresh(newer)
    assert older.status == JobStatus.done
    assert newer.status == JobStatus.pending


def test_recover_stale_processing_jobs_with_existing_audio(db_session, make_audio_file):
    make_audio_file("20.wav")
    job = TranscriptionJob(
        id=20,
        user_id=1,
        filename_original="stuck.wav",
        model_used="tiny",
        audio_tmp_filename="20.wav",
        status=JobStatus.processing,
        progress=80,
    )
    db_session.add(job)
    db_session.commit()

    worker_main.recover_stale_processing_jobs(db_session)

    db_session.refresh(job)
    assert job.status == JobStatus.pending
    assert job.started_at is None
    assert job.progress == 0


def test_recover_stale_processing_jobs_without_audio_marks_error(db_session):
    job = TranscriptionJob(
        id=21,
        user_id=1,
        filename_original="stuck_no_audio.wav",
        model_used="tiny",
        audio_tmp_filename="never_existed.wav",
        status=JobStatus.processing,
    )
    db_session.add(job)
    db_session.commit()

    worker_main.recover_stale_processing_jobs(db_session)

    db_session.refresh(job)
    assert job.status == JobStatus.error
    assert job.error_message is not None


def test_recover_stale_processing_jobs_ignores_other_statuses(db_session):
    done_job = TranscriptionJob(
        id=22,
        user_id=1,
        filename_original="already_done.wav",
        model_used="tiny",
        status=JobStatus.done,
    )
    db_session.add(done_job)
    db_session.commit()

    worker_main.recover_stale_processing_jobs(db_session)

    db_session.refresh(done_job)
    assert done_job.status == JobStatus.done


# --- Progression de la transcription ---


def test_process_pending_job_commits_progress_incrementally(db_session, make_audio_file, monkeypatch):
    make_audio_file("30.wav")
    job = TranscriptionJob(
        id=30,
        user_id=1,
        filename_original="progress.wav",
        model_used="tiny",
        audio_tmp_filename="30.wav",
        status=JobStatus.pending,
        audio_duration_seconds=100.0,
    )
    db_session.add(job)
    db_session.commit()

    # Désactive le throttle pour observer un commit par segment.
    monkeypatch.setattr(worker_main, "PROGRESS_MIN_DELTA_PERCENT", 0)
    monkeypatch.setattr(worker_main, "PROGRESS_MIN_INTERVAL_SECONDS", 0.0)

    seen_progress = []

    class RecordingModel:
        def transcribe(self, audio_path, language="fr"):
            def gen():
                for second in range(10, 101, 10):
                    yield FakeSegment(start=second - 10, end=float(second), text=f"Seg {second}.")
                    # Après le yield, le worker a commité la progression de
                    # ce segment : la relire depuis une session neuve.
                    with Session(worker_main.engine) as s:
                        seen_progress.append(s.get(TranscriptionJob, 30).progress)

            return gen(), FakeInfo(duration=100.0)

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: RecordingModel())

    processed = worker_main.process_pending_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == JobStatus.done
    assert job.progress == 100
    # Progression commitée en base au fil des segments, plafonnée à 99
    # pendant le traitement (le 100 final n'est posé qu'au passage à done).
    assert seen_progress == [10, 20, 30, 40, 50, 60, 70, 80, 90, 99]


def test_process_pending_job_without_duration_skips_progress(db_session, make_audio_file, monkeypatch):
    make_audio_file("31.wav")
    job = TranscriptionJob(
        id=31,
        user_id=1,
        filename_original="no_duration.wav",
        model_used="tiny",
        audio_tmp_filename="31.wav",
        status=JobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()

    class NoDurationModel:
        def transcribe(self, audio_path, language="fr"):
            # info sans duration et job sans audio_duration_seconds
            return iter([FakeSegment(0.0, 1.0, "Un.")]), object()

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: NoDurationModel())
    worker_main.process_pending_job(db_session)

    db_session.refresh(job)
    assert job.status == JobStatus.done
    assert job.progress == 100


# --- Progression du téléchargement des modèles ---


def test_download_progress_state_records_percent_in_db(db_session):
    model = WhisperModel(id=3, name="small", status=ModelStatus.downloading)
    db_session.add(model)
    db_session.commit()

    state = worker_main._DownloadProgressState(model.id, min_interval_seconds=0.0)
    bar_a, bar_b = object(), object()

    state.record(id(bar_a), 50, 100)  # 50 %
    with Session(worker_main.engine) as s:
        assert s.get(WhisperModel, 3).download_progress == 50

    state.record(id(bar_b), 25, 100)  # (50+25)/(100+100) = 37 %
    with Session(worker_main.engine) as s:
        assert s.get(WhisperModel, 3).download_progress == 37

    # Fermeture de bar_a : son cumul est conservé (ids recyclables).
    state.finalize(id(bar_a), 50, 100)
    state.record(id(bar_b), 100, 100)  # (50+100)/200 = 75 %
    with Session(worker_main.engine) as s:
        assert s.get(WhisperModel, 3).download_progress == 75


def test_download_progress_state_throttles_writes(db_session):
    model = WhisperModel(id=4, name="medium", status=ModelStatus.downloading)
    db_session.add(model)
    db_session.commit()

    state = worker_main._DownloadProgressState(model.id, min_interval_seconds=3600.0)
    state.record(id("bar"), 40, 100)  # premier write : passe
    state.record(id("bar"), 45, 100)  # trop tôt : supprimé par le throttle
    with Session(worker_main.engine) as s:
        assert s.get(WhisperModel, 4).download_progress == 40


def test_process_pending_model_downloads_success(db_session, monkeypatch):
    import os

    model = WhisperModel(id=5, name="tiny", status=ModelStatus.downloading)
    db_session.add(model)
    db_session.commit()

    snapshot_calls = []

    def fake_snapshot_download(**kwargs):
        snapshot_calls.append(kwargs)
        # Simule le cache huggingface écrit sur disque : blobs (2 Mo) +
        # snapshots (symlinks vers les blobs, à ne pas recompter).
        cache_dir = os.path.join(
            os.environ["WHISPER_MODELS_PATH"], "models--Systran--faster-whisper-tiny"
        )
        os.makedirs(cache_dir, exist_ok=True)
        blob_path = os.path.join(cache_dir, "model.bin")
        with open(blob_path, "wb") as f:
            f.write(b"\0" * (2 * 1024 * 1024))
        snapshots_dir = os.path.join(cache_dir, "snapshots", "rev")
        os.makedirs(snapshots_dir, exist_ok=True)
        os.symlink(blob_path, os.path.join(snapshots_dir, "model.bin"))

    class FakeFasterWhisperModel:
        def __init__(self, name, device=None, compute_type=None, download_root=None):
            self.name = name

    monkeypatch.setattr(worker_main, "snapshot_download", fake_snapshot_download)
    monkeypatch.setattr("faster_whisper.WhisperModel", FakeFasterWhisperModel)

    worker_main.process_pending_model_downloads(db_session)

    db_session.refresh(model)
    assert model.status == ModelStatus.downloaded
    assert model.download_progress == 100
    assert model.disk_size_mb == 2
    assert model.error_message is None
    assert model.downloaded_at is not None
    assert snapshot_calls[0]["repo_id"] == "Systran/faster-whisper-tiny"


def test_process_pending_model_downloads_error(db_session, monkeypatch):
    model = WhisperModel(id=6, name="base", status=ModelStatus.downloading)
    db_session.add(model)
    db_session.commit()

    def failing_snapshot_download(**kwargs):
        raise RuntimeError("Réseau indisponible")

    monkeypatch.setattr(worker_main, "snapshot_download", failing_snapshot_download)

    worker_main.process_pending_model_downloads(db_session)

    db_session.refresh(model)
    assert model.status == ModelStatus.error
    assert model.download_progress is None
    assert "Réseau indisponible" in model.error_message


# --- Migration légère du schéma SQLite ---


def test_backfill_model_disk_sizes_fills_missing(db_session):
    import os

    # Modèle "téléchargé" avant l'ajout de la colonne disk_size_mb.
    model = WhisperModel(id=7, name="small", status=ModelStatus.downloaded, disk_size_mb=None)
    db_session.add(model)
    db_session.commit()

    cache_dir = os.path.join(
        os.environ["WHISPER_MODELS_PATH"], "models--Systran--faster-whisper-small"
    )
    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, "model.bin"), "wb") as f:
        f.write(b"\0" * (3 * 1024 * 1024))

    worker_main.backfill_model_disk_sizes(db_session)

    db_session.refresh(model)
    assert model.disk_size_mb == 3


def test_ensure_schema_upgrades_adds_missing_columns(db_session):
    from sqlalchemy import inspect, text

    with worker_main.engine.begin() as conn:
        conn.execute(text("DROP TABLE transcriptionjob"))
        conn.execute(
            text(
                """
                CREATE TABLE transcriptionjob (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    filename_original VARCHAR,
                    model_used VARCHAR,
                    language VARCHAR,
                    audio_tmp_filename VARCHAR,
                    status VARCHAR,
                    error_message VARCHAR,
                    result_vtt_path VARCHAR,
                    created_at TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP
                )
                """
            )
        )

    worker_main._ensure_schema_upgrades()
    worker_main._ensure_schema_upgrades()  # idempotent

    columns = {c["name"] for c in inspect(worker_main.engine).get_columns("transcriptionjob")}
    assert {"audio_duration_seconds", "progress"} <= columns


# --- Annulation ---


def test_job_cancelled_before_processing(db_session, make_audio_file, monkeypatch):
    audio_path = make_audio_file("40.wav")
    job = TranscriptionJob(
        id=40,
        user_id=1,
        filename_original="cancel.wav",
        model_used="tiny",
        audio_tmp_filename="40.wav",
        status=JobStatus.pending,
        cancel_requested=True,
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: FakeWhisperModel())
    processed = worker_main.process_pending_job(db_session)
    assert processed is True

    db_session.refresh(job)
    assert job.status == JobStatus.cancelled
    assert job.error_message is None
    assert not __import__("os").path.exists(audio_path)  # audio nettoyé


def test_job_cancelled_during_transcription(db_session, make_audio_file, monkeypatch):
    import os

    make_audio_file("41.wav")
    job = TranscriptionJob(
        id=41,
        user_id=1,
        filename_original="cancel_mid.wav",
        model_used="tiny",
        audio_tmp_filename="41.wav",
        status=JobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()

    class SlowlyCancellingModel:
        def transcribe(self, audio_path, language="fr"):
            def gen():
                yield FakeSegment(start=0.0, end=1.0, text="Premier.")
                # Annulation demandée pendant le décodage.
                with Session(worker_main.engine) as s:
                    row = s.get(TranscriptionJob, 41)
                    row.cancel_requested = True
                    s.add(row)
                    s.commit()
                yield FakeSegment(start=1.0, end=2.0, text="Deuxieme.")
                yield FakeSegment(start=2.0, end=3.0, text="Troisieme.")

            info = type("Info", (), {"duration": 3.0})()
            return gen(), info

    monkeypatch.setattr(worker_main, "_get_whisper_model", lambda name: SlowlyCancellingModel())
    # Force la consultation du fanion à chaque segment.
    monkeypatch.setattr(worker_main, "CANCEL_CHECK_INTERVAL_SECONDS", -1.0)

    worker_main.process_pending_job(db_session)
    db_session.refresh(job)
    assert job.status == JobStatus.cancelled
    assert job.result_vtt_path is None
    assert not os.path.exists(os.path.join(os.environ["AUDIO_TMP_PATH"], "41.wav"))
