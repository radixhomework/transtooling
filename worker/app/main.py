import glob
import logging
import os
import shutil
import threading
import time
from datetime import datetime

from huggingface_hub import snapshot_download
from huggingface_hub.utils.tqdm import tqdm as hf_tqdm
from sqlmodel import Session, create_engine, select

from app.config import settings
from app.models import JobStatus, ModelStatus, TranscriptionJob, WhisperModel
from app.vtt import segments_to_vtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [transcription-worker] %(message)s")
logger = logging.getLogger(__name__)

# Throttle for progress writes to the database: SQLite is shared with the
# backend, so we avoid committing on every segment/token.
PROGRESS_MIN_DELTA_PERCENT = 2
PROGRESS_MIN_INTERVAL_SECONDS = 2.0
# Minimum interval between two cancel-flag reads from the database.
CANCEL_CHECK_INTERVAL_SECONDS = 1.0


class JobCancelled(Exception):
    """Raised when job cancellation is requested during processing."""

engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)

# In-memory cache of already loaded faster-whisper models (avoids
# reloading the model on every job when it matches the previous one).
_loaded_models: dict = {}


def _get_whisper_model(model_name: str):
    from faster_whisper import WhisperModel as FasterWhisperModel

    if model_name not in _loaded_models:
        logger.info("Loading faster-whisper model '%s' into memory...", model_name)
        _loaded_models.clear()  # only one model in memory at a time (simplicity/RAM)
        _loaded_models[model_name] = FasterWhisperModel(
            model_name,
            device="cpu",
            compute_type=settings.whisper_compute_type,
            download_root=settings.whisper_models_path,
        )
    return _loaded_models[model_name]


class _DownloadProgressState:
    """
    Aggregates snapshot_download progress (one tqdm bar per file, potentially
    downloaded in parallel by huggingface_hub) and persists it to
    WhisperModel.download_progress, with throttling.
    """

    def __init__(self, model_id: int, min_interval_seconds: float = 1.0):
        self._model_id = model_id
        self._min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._active_bars: dict[int, tuple[int, int | None]] = {}  # id(bar) -> (octets, total)
        self._completed_bytes = 0
        self._completed_total = 0
        # -inf: the first write always goes through (time.monotonic() can
        # start near zero in a freshly launched container).
        self._last_write = float("-inf")
        self._last_percent = -1

    def record(self, bar_id: int, bar_bytes: int, bar_total: int | None) -> None:
        percent = None
        with self._lock:
            self._active_bars[bar_id] = (bar_bytes, bar_total)
            percent = self._compute_percent_unlocked()
        if percent is not None:
            self._write_percent(percent)

    def finalize(self, bar_id: int, bar_bytes: int, bar_total: int | None) -> None:
        """Moves a closed bar into the cumulative totals: its id can be
        reused by another bar (Python recycles ids)."""
        percent = None
        with self._lock:
            self._active_bars.pop(bar_id, None)
            self._completed_bytes += bar_bytes
            if bar_total:
                self._completed_total += bar_total
            percent = self._compute_percent_unlocked()
        if percent is not None:
            self._write_percent(percent)

    def _compute_percent_unlocked(self) -> int | None:
        total = self._completed_total + sum(t for _, t in self._active_bars.values() if t)
        if total <= 0:
            return None
        downloaded = self._completed_bytes + sum(n for n, _ in self._active_bars.values())
        percent = int(min(99, downloaded * 100 / total))
        now = time.monotonic()
        # Double throttle: minimum delay elapsed AND progress actually
        # changed (otherwise a fast download would write to the database
        # on every small 1% step).
        if now - self._last_write < self._min_interval_seconds:
            return None
        if percent == self._last_percent:
            return None
        self._last_percent = percent
        self._last_write = now
        return percent

    def _write_percent(self, percent: int) -> None:
        try:
            # Dedicated short-lived session: this callback can be called from
            # a huggingface_hub download thread, not the worker's thread.
            with Session(engine) as session:
                model = session.get(WhisperModel, self._model_id)
                if model and model.status == ModelStatus.downloading:
                    model.download_progress = percent
                    session.add(model)
                    session.commit()
        except Exception:  # noqa: BLE001
            # Best effort: a write failure must never break the
            # download itself.
            logger.debug("Could not write progress", exc_info=True)


def _make_progress_tqdm_class(state: _DownloadProgressState) -> type:
    """tqdm class bound to a progress state (closure), to be passed to
    snapshot_download via tqdm_class."""

    class _ProgressTqdm(hf_tqdm):
        def update(self, n=1):
            super().update(n)
            state.record(id(self), self.n, self.total)

        def close(self):
            super().close()
            state.finalize(id(self), self.n, self.total)

    return _ProgressTqdm


def _compute_model_disk_size_mb(model_name: str) -> int | None:
    """Actual on-disk size of the model's huggingface cache, in MB.

    The cache uses blobs (real files) + snapshots (symlinks to blobs):
    links are ignored to avoid double counting.
    """
    pattern = os.path.join(settings.whisper_models_path, f"*{model_name}*")
    total_bytes = 0
    found = False
    for path in glob.glob(pattern):
        if not os.path.isdir(path):
            continue
        found = True
        for root, _dirs, files in os.walk(path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if os.path.islink(file_path):
                    continue
                try:
                    total_bytes += os.path.getsize(file_path)
                except OSError:
                    pass
    return total_bytes // (1024 * 1024) if found else None


def backfill_model_disk_sizes(session: Session) -> None:
    """Fills in the disk size of models downloaded before the disk_size_mb
    column was added (otherwise never computed for them)."""
    models = session.exec(
        select(WhisperModel).where(WhisperModel.status == ModelStatus.downloaded)
    ).all()
    for model in models:
        if model.disk_size_mb is not None:
            continue
        size = _compute_model_disk_size_mb(model.name)
        if size is not None:
            logger.info("Disk size of model '%s' recorded: %s MB.", model.name, size)
            model.disk_size_mb = size
            session.add(model)
    session.commit()


def _resolve_audio_path(job: TranscriptionJob) -> str | None:
    if not job.audio_tmp_filename:
        return None
    path = os.path.join(settings.audio_tmp_path, job.audio_tmp_filename)
    return path if os.path.exists(path) else None


def recover_stale_processing_jobs(session: Session) -> None:
    """
    At worker startup, any job left in 'processing' status signals an
    abnormal stop (crash, container restart) during processing. Temporary
    audio is only deleted once processing finishes (success or failure),
    so it is most likely still present: such jobs are put back in
    'pending' so they get processed again automatically.
    """
    stale_jobs = session.exec(
        select(TranscriptionJob).where(TranscriptionJob.status == JobStatus.processing)
    ).all()

    for job in stale_jobs:
        audio_path = _resolve_audio_path(job)
        if audio_path:
            logger.warning(
                "Job %s found stuck in 'processing' at startup: re-queued.",
                job.id,
            )
            job.status = JobStatus.pending
            job.started_at = None
            job.progress = 0
        else:
            logger.warning(
                "Job %s stuck in 'processing' but audio missing: marked as error.",
                job.id,
            )
            job.status = JobStatus.error
            job.error_message = "Traitement interrompu (redémarrage du worker) et fichier audio introuvable"
            job.finished_at = datetime.utcnow()
        session.add(job)
    session.commit()


def _is_cancel_requested(session: Session, job_id: int) -> bool:
    """Re-reads the cancellation flag from the database (set by the API)."""
    row = session.exec(
        select(TranscriptionJob.cancel_requested).where(TranscriptionJob.id == job_id)
    ).first()
    return bool(row)


def process_pending_job(session: Session) -> bool:
    """Processes a single pending job. Returns True if a job was processed."""
    job = session.exec(
        select(TranscriptionJob)
        .where(TranscriptionJob.status == JobStatus.pending)
        .order_by(TranscriptionJob.created_at)
    ).first()

    if not job:
        return False

    audio_path = _resolve_audio_path(job)
    job.status = JobStatus.processing
    job.started_at = datetime.utcnow()
    job.progress = 0
    session.add(job)
    session.commit()

    # Cancellation requested while the job was queued.
    if _is_cancel_requested(session, job.id):
        job.status = JobStatus.cancelled
        job.error_message = None
        job.finished_at = datetime.utcnow()
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        job.audio_tmp_filename = None
        session.add(job)
        session.commit()
        logger.info("Job %s cancelled by the user before processing.", job.id)
        return True

    last_cancel_check = time.monotonic()

    try:
        if not audio_path:
            raise FileNotFoundError("Fichier audio introuvable pour ce job")

        model = _get_whisper_model(job.model_used)
        segments_iter, info = model.transcribe(audio_path, language="fr")

        # Progress denominator: duration measured by Whisper, or the
        # ffprobe duration from upload time as a fallback.
        duration = getattr(info, "duration", None) or job.audio_duration_seconds

        # segments is a generator consumed as decoding progresses: iterating
        # incrementally allows tracking progress and detecting cancellation
        # without waiting for the end of the file.
        segments = []
        last_commit_percent = 0
        last_commit_at = time.monotonic()
        for segment in segments_iter:
            segments.append(segment)
            now = time.monotonic()
            if now - last_cancel_check >= CANCEL_CHECK_INTERVAL_SECONDS:
                last_cancel_check = now
                if _is_cancel_requested(session, job.id):
                    raise JobCancelled()
            if not duration:
                continue
            percent = min(99, int(segment.end / duration * 100))
            if (
                percent - last_commit_percent >= PROGRESS_MIN_DELTA_PERCENT
                and now - last_commit_at >= PROGRESS_MIN_INTERVAL_SECONDS
            ):
                job.progress = percent
                session.add(job)
                session.commit()
                last_commit_percent = percent
                last_commit_at = now

        # Text cleanup/post-processing (spaces, punctuation, capitals) is
        # applied segment by segment inside segments_to_vtt.
        vtt_content = segments_to_vtt(segments)

        os.makedirs(settings.transcripts_path, exist_ok=True)
        vtt_path = os.path.join(settings.transcripts_path, f"{job.id}.vtt")
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(vtt_content)

        job.result_vtt_path = vtt_path
        job.status = JobStatus.done
        job.progress = 100
        job.finished_at = datetime.utcnow()
        logger.info("Job %s completed successfully.", job.id)

    except JobCancelled:
        logger.info("Job %s cancelled by the user.", job.id)
        job.status = JobStatus.cancelled
        job.error_message = None
        job.finished_at = datetime.utcnow()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error while processing job %s", job.id)
        job.status = JobStatus.error
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()

    finally:
        # The source audio is never kept, whatever the outcome.
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        job.audio_tmp_filename = None
        session.add(job)
        session.commit()

    return True


def process_pending_model_downloads(session: Session) -> None:
    """Downloads models marked 'downloading' by the admin through the API."""
    from faster_whisper import WhisperModel as FasterWhisperModel

    pending_models = session.exec(
        select(WhisperModel).where(WhisperModel.status == ModelStatus.downloading)
    ).all()

    for model in pending_models:
        logger.info("Downloading model '%s'...", model.name)
        # Reset progress before starting (the callback writes through a
        # separate session, this one would not see its values).
        model.download_progress = 0
        session.add(model)
        session.commit()

        state = _DownloadProgressState(model.id)
        try:
            # Explicit download with progress reporting, then model
            # construction (cache hit, no re-download). Repo and patterns
            # follow the faster-whisper convention (Systran/faster-whisper-<name>)
            # to share the same cache.
            snapshot_download(
                repo_id=f"Systran/faster-whisper-{model.name}",
                cache_dir=settings.whisper_models_path,
                allow_patterns=[
                    "config.json",
                    "preprocessor_config.json",
                    "model.bin",
                    "tokenizer.json",
                    "vocabulary.*",
                ],
                tqdm_class=_make_progress_tqdm_class(state),
            )
            FasterWhisperModel(
                model.name,
                device="cpu",
                compute_type=settings.whisper_compute_type,
                download_root=settings.whisper_models_path,
            )
            model.status = ModelStatus.downloaded
            model.downloaded_at = datetime.utcnow()
            model.download_progress = 100
            model.disk_size_mb = _compute_model_disk_size_mb(model.name)
            model.error_message = None
            logger.info("Model '%s' downloaded.", model.name)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Model '%s' download failed", model.name)
            model.status = ModelStatus.error
            model.download_progress = None
            model.error_message = str(exc)

        session.add(model)
        session.commit()


def process_pending_model_deletions(session: Session) -> None:
    """
    Physically deletes the files of a model switched back to 'not_downloaded'
    on the API side while it still exists on disk.
    faster-whisper convention: models--<org>--faster-whisper-<name>
    directory under whisper_models_path (huggingface_hub cache).
    """
    models = session.exec(select(WhisperModel).where(WhisperModel.status == ModelStatus.not_downloaded)).all()
    for model in models:
        pattern = os.path.join(settings.whisper_models_path, f"*{model.name}*")
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                logger.info("Deleting model from disk: %s", path)
                shutil.rmtree(path, ignore_errors=True)


# Columns added after the initial schema: create_all does not run ALTER
# TABLE on an existing database. The backend applies the same patch at
# its startup; this safety net covers the case where the worker starts
# before the backend migration. Keep in sync with
# backend/app/core/database.py.
_SCHEMA_PATCHES = {
    "transcriptionjob": {
        "audio_duration_seconds": "REAL",
        "progress": "INTEGER",
        "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
    },
    "whispermodel": {
        "download_progress": "INTEGER",
    },
}


def _ensure_schema_upgrades() -> None:
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


def main_loop() -> None:
    logger.info("Transcription worker started. Polling every %ss.", settings.poll_interval_seconds)

    _ensure_schema_upgrades()

    with Session(engine) as startup_session:
        try:
            backfill_model_disk_sizes(startup_session)
            recover_stale_processing_jobs(startup_session)
        except Exception:  # noqa: BLE001
            logger.exception("Error while recovering stuck jobs at startup")

    consecutive_errors = 0
    max_backoff_seconds = 60

    while True:
        with Session(engine) as session:
            try:
                process_pending_model_downloads(session)
                process_pending_model_deletions(session)
                processed = process_pending_job(session)
                consecutive_errors = 0
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected error in the worker main loop")
                processed = False
                consecutive_errors += 1

        if consecutive_errors > 0:
            # Exponential backoff with a cap, to avoid an overly aggressive
            # crash loop on persistent issues (e.g. a temporarily
            # unavailable database).
            backoff = min(settings.poll_interval_seconds * (2 ** consecutive_errors), max_backoff_seconds)
            logger.warning("Pausing %ss after %s consecutive error(s).", backoff, consecutive_errors)
            time.sleep(backoff)
        elif not processed:
            time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main_loop()
