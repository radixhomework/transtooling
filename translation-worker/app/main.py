import glob
import hashlib
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import zipfile
from datetime import datetime

from huggingface_hub import snapshot_download
from huggingface_hub.utils.tqdm import tqdm as hf_tqdm
from sqlmodel import Session, create_engine, select

from app.config import settings
from app.engine import ALLOW_PATTERNS, DIRECTION_REPOS, JobCancelled, TranslationEngine
from app.models import (
    AppSettings,
    TranslationCache,
    TranslationDirection,
    TranslationJob,
    TranslationJobStatus,
    TranslationJobType,
    TranslationModel,
    TranslationModelStatus,
)
from app.translators import (
    translate_html_content,
    translate_json_content,
    translate_markdown_content,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [translation-worker] %(message)s")
logger = logging.getLogger(__name__)

engine_db = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)

# In-memory cache of already loaded engines (at most one per
# direction, to bound RAM usage).
_loaded_engines: dict = {}


def _get_engine(direction: str) -> TranslationEngine:
    if direction not in _loaded_engines:
        logger.info("Loading translation model '%s'...", direction)
        _loaded_engines.clear()
        # allow_patterns also for local reads: otherwise snapshot_download
        # validates the completeness of the WHOLE repository
        # (non-downloaded files).
        model_path = snapshot_download(
            repo_id=DIRECTION_REPOS[direction],
            cache_dir=settings.translation_models_path,
            allow_patterns=list(ALLOW_PATTERNS),
            local_files_only=True,
        )
        _loaded_engines[direction] = TranslationEngine(direction, model_path)
    return _loaded_engines[direction]


def _is_cancel_requested(session: Session, job_id: int) -> bool:
    """Re-reads the cancellation flag from the database (set by the API)."""
    row = session.exec(
        select(TranslationJob.cancel_requested).where(TranslationJob.id == job_id)
    ).first()
    return bool(row)


def _check_cancelled(session: Session, job_id: int) -> None:
    if _is_cancel_requested(session, job_id):
        raise JobCancelled()


# ---------------------------------------------------- translation cache


def cache_key(direction: str, text: str) -> str:
    return hashlib.sha256(f"{direction}\x00{text}".encode("utf-8")).hexdigest()


def translate_texts(session: Session, direction: str, texts: list, job_id: int = None) -> list:
    """
    Translates a list of texts: cache read BEFORE translating, computing
    only the missing (deduplicated) texts, cache written AFTER computing
    only (never on a hit). Raises JobCancelled if the job cancellation is
    requested between two batches.
    """
    results: dict = {}
    misses: list = []
    for text in texts:
        key = cache_key(direction, text)
        row = session.get(TranslationCache, key)
        if row is not None:
            results[text] = row.translated_text
        elif text not in misses:
            misses.append(text)

    if misses:
        engine = _get_engine(direction)

        def _should_continue():
            if job_id is not None:
                _check_cancelled(session, job_id)

        translated = engine.translate(misses, should_continue=_should_continue)
        for source, result in zip(misses, translated):
            session.add(
                TranslationCache(
                    cache_key=cache_key(direction, source),
                    direction=direction,
                    translated_text=result,
                )
            )
            results[source] = result
        session.commit()

    return [results[text] for text in texts]


# ------------------------------------------------------ models: downloads


class _DownloadProgressState:
    """Aggregates snapshot_download progress and persists it (throttled)
    to TranslationModel.download_progress."""

    def __init__(self, model_id: int, min_interval_seconds: float = 1.0):
        self._model_id = model_id
        self._min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._active_bars: dict = {}
        self._completed_bytes = 0
        self._completed_total = 0
        # -inf: the first write always goes through (time.monotonic() can
        # start near zero in a freshly launched container).
        self._last_write = float("-inf")
        self._last_percent = -1

    def record(self, bar_id, bar_bytes, bar_total):
        percent = self._compute(bar_id, bar_bytes, bar_total)
        if percent is not None:
            self._write(percent)

    def finalize(self, bar_id, bar_bytes, bar_total):
        percent = None
        with self._lock:
            self._active_bars.pop(bar_id, None)
            self._completed_bytes += bar_bytes
            if bar_total:
                self._completed_total += bar_total
            total = self._completed_total + sum(t for _, t in self._active_bars.values() if t)
            if total > 0:
                downloaded = self._completed_bytes + sum(n for n, _ in self._active_bars.values())
                percent = self._throttle(int(min(99, downloaded * 100 / total)))
        if percent is not None:
            self._write(percent)

    def _compute(self, bar_id, bar_bytes, bar_total):
        with self._lock:
            self._active_bars[bar_id] = (bar_bytes, bar_total)
            total = self._completed_total + sum(t for _, t in self._active_bars.values() if t)
            if total <= 0:
                return None
            downloaded = self._completed_bytes + sum(n for n, _ in self._active_bars.values())
            return self._throttle(int(min(99, downloaded * 100 / total)))

    def _throttle(self, percent: int):
        now = time.monotonic()
        if now - self._last_write < self._min_interval_seconds or percent == self._last_percent:
            return None
        self._last_percent = percent
        self._last_write = now
        return percent

    def _write(self, percent: int) -> None:
        try:
            with Session(engine_db) as session:
                model = session.get(TranslationModel, self._model_id)
                if model and model.status == TranslationModelStatus.downloading:
                    model.download_progress = percent
                    session.add(model)
                    session.commit()
        except Exception:  # noqa: BLE001
            logger.debug("Could not write progress", exc_info=True)


def _make_progress_tqdm_class(state: _DownloadProgressState) -> type:
    class _ProgressTqdm(hf_tqdm):
        def update(self, n=1):
            super().update(n)
            state.record(id(self), self.n, self.total)

        def close(self):
            super().close()
            state.finalize(id(self), self.n, self.total)

    return _ProgressTqdm


def _repo_cache_glob(direction: str) -> str:
    """Glob of the huggingface cache directory for the repo carrying the
    direction (convention: models--<org>--<repo>)."""
    repo = DIRECTION_REPOS[direction]
    return os.path.join(settings.translation_models_path, f"models--{repo.replace('/', '--')}")


def _compute_model_disk_size_mb(direction: str):
    """Actual on-disk size of the model's huggingface cache, in MB
    (symlinks ignored: blobs + snapshots are not counted twice)."""
    total_bytes = 0
    found = False
    for path in glob.glob(_repo_cache_glob(direction)):
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


def process_pending_model_downloads(session: Session) -> None:
    """Downloads translation models marked 'downloading' by the admin."""
    pending = session.exec(
        select(TranslationModel).where(TranslationModel.status == TranslationModelStatus.downloading)
    ).all()

    for model in pending:
        direction = model.direction.value
        logger.info("Downloading translation model '%s'...", direction)
        model.download_progress = 0
        session.add(model)
        session.commit()

        state = _DownloadProgressState(model.id)
        try:
            snapshot_download(
                repo_id=DIRECTION_REPOS[direction],
                cache_dir=settings.translation_models_path,
                allow_patterns=list(ALLOW_PATTERNS),
                tqdm_class=_make_progress_tqdm_class(state),
            )
            model.status = TranslationModelStatus.downloaded
            model.downloaded_at = datetime.utcnow()
            model.download_progress = 100
            model.disk_size_mb = _compute_model_disk_size_mb(direction)
            model.error_message = None
            logger.info("Translation model '%s' downloaded.", direction)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Model '%s' download failed", direction)
            model.status = TranslationModelStatus.error
            model.download_progress = None
            model.error_message = str(exc)

        session.add(model)
        session.commit()


def process_pending_model_deletions(session: Session) -> None:
    """
    Physically deletes the files of a model switched back to
    'not_downloaded' (huggingface cache convention: models--<org>--<repo>).

    The NLLB model being shared by all directions, files are only deleted
    when no other downloaded direction relies on them.
    """
    models = session.exec(select(TranslationModel)).all()
    downloaded_repos = {
        DIRECTION_REPOS[m.direction.value]
        for m in models
        if m.status == TranslationModelStatus.downloaded
    }
    for model in models:
        if model.status != TranslationModelStatus.not_downloaded:
            continue
        repo = DIRECTION_REPOS[model.direction.value]
        if repo in downloaded_repos:
            continue
        for path in glob.glob(_repo_cache_glob(model.direction.value)):
            if os.path.isdir(path):
                logger.info("Deleting translation model from disk: %s", path)
                shutil.rmtree(path, ignore_errors=True)


# ------------------------------------------------------------ jobs: common


def _resolve_archive_path(job: TranslationJob):
    if not job.archive_tmp_filename:
        return None
    path = os.path.join(settings.translation_tmp_path, job.archive_tmp_filename)
    return path if os.path.exists(path) else None


def recover_stale_processing_jobs(session: Session) -> None:
    """Any job left in 'processing' signals an abnormal worker stop:
    put back in 'pending' if its input still exists (text/archive),
    otherwise marked as error."""
    stale_jobs = session.exec(
        select(TranslationJob).where(TranslationJob.status == TranslationJobStatus.processing)
    ).all()

    for job in stale_jobs:
        if job.job_type == TranslationJobType.text and job.source_text:
            logger.warning("Job %s stuck in 'processing': re-queued.", job.id)
            job.status = TranslationJobStatus.pending
            job.started_at = None
        elif (
            job.job_type == TranslationJobType.archive and _resolve_archive_path(job)
        ):
            logger.warning("Job %s stuck in 'processing': re-queued.", job.id)
            job.status = TranslationJobStatus.pending
            job.started_at = None
        else:
            logger.warning("Job %s stuck in 'processing' without input: marked as error.", job.id)
            job.status = TranslationJobStatus.error
            job.error_message = "Traitement interrompu (redémarrage du worker) et entrée introuvable"
            job.finished_at = datetime.utcnow()
        session.add(job)
    session.commit()


def process_pending_job(session: Session) -> bool:
    """Processes a pending translation job (text or archive mode)."""
    job = session.exec(
        select(TranslationJob)
        .where(TranslationJob.status == TranslationJobStatus.pending)
        .order_by(TranslationJob.created_at)
    ).first()

    if not job:
        return False

    job.status = TranslationJobStatus.processing
    job.started_at = datetime.utcnow()
    session.add(job)
    session.commit()

    try:
        # Cancellation requested while the job was queued: stopped
        # right after being picked up.
        _check_cancelled(session, job.id)
        if job.job_type == TranslationJobType.text:
            _process_text_job(session, job)
        else:
            _process_archive_job(session, job)
    except JobCancelled:
        logger.info("Job %s cancelled by the user.", job.id)
        job.status = TranslationJobStatus.cancelled
        job.error_message = None
        job.finished_at = datetime.utcnow()
        # Cleanup of temporary inputs (cancellation can occur before
        # entering the actual processing).
        if job.job_type == TranslationJobType.archive:
            cancelled_zip = _resolve_archive_path(job)
            if cancelled_zip and os.path.exists(cancelled_zip):
                os.remove(cancelled_zip)
            job.archive_tmp_filename = None
    except _BlockingJobError as exc:
        logger.exception("Blocking error on job %s", job.id)
        job.status = TranslationJobStatus.error
        job.error_message = str(exc.reason or exc)
        job.stopped_reason = exc.reason
        job.finished_at = datetime.utcnow()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error while processing job %s", job.id)
        job.status = TranslationJobStatus.error
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()
    finally:
        session.add(job)
        session.commit()

    return True


class _BlockingJobError(Exception):
    """Erreur qui interrompt tout le traitement d'une archive (statut error
    + stopped_reason), par opposition aux erreurs par fichier (au mieux)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# ------------------------------------------------------------- jobs: text


def _process_text_job(session: Session, job: TranslationJob) -> None:
    if not job.source_text:
        raise _BlockingJobError("Texte source introuvable")
    direction = job.direction.value
    translated = translate_texts(session, direction, [job.source_text], job_id=job.id)[0]
    job.result_text = translated
    job.status = TranslationJobStatus.done
    job.finished_at = datetime.utcnow()
    logger.info("Translation job %s completed.", job.id)


# ---------------------------------------------------------- jobs: archive


def _get_translatable_extensions(session: Session) -> set:
    row = session.get(AppSettings, 1)
    raw = row.translatable_extensions if row else "json,html,htm,md"
    return {part.strip().lstrip(".").lower() for part in raw.split(",") if part.strip()}


def _extract_archive(zip_path: str, extract_dir: str, session: Session) -> None:
    """Secure extraction: any path trying to escape the target directory
    (zip-slip) is rejected, checked member by member."""
    limits = session.get(AppSettings, 1)
    max_uncompressed = (
        limits.max_archive_uncompressed_mb * 1024 * 1024 if limits else 500 * 1024 * 1024
    )
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                # Keep directories (including empty ones) so the tree
                # can be rebuilt identically.
                os.makedirs(os.path.join(extract_dir, info.filename), exist_ok=True)
                continue
            total += info.file_size
            if total > max_uncompressed:
                raise _BlockingJobError("Taille décompressée de l'archive au-delà de la limite")
            # Zip-slip: the resolved path must stay under extract_dir.
            target = os.path.realpath(os.path.join(extract_dir, info.filename))
            if not target.startswith(os.path.realpath(extract_dir) + os.sep):
                raise _BlockingJobError(f"Chemin de fichier invalide dans l'archive : {info.filename}")
            zf.extract(info, extract_dir)


def _translate_archive_file(
    path: str, extension: str, session: Session, direction: str, job_id: int
) -> None:
    with open(path, encoding="utf-8") as f:
        content = f.read()

    def translate_batch(texts: list) -> list:
        return translate_texts(session, direction, texts, job_id=job_id)

    if extension == "json":
        translated = translate_json_content(content, translate_batch)
    elif extension in ("md", "markdown"):
        translated = translate_markdown_content(content, translate_batch)
    else:  # html / htm
        translated = translate_html_content(content, translate_batch)

    with open(path, "w", encoding="utf-8") as f:
        f.write(translated)


def _rebuild_archive(extract_dir: str, output_path: str) -> None:
    """Rebuilds the result archive strictly preserving names and tree
    structure (empty directory entries are kept too)."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(extract_dir):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                rel = os.path.relpath(dir_path, extract_dir).replace(os.sep, "/")
                if not os.listdir(dir_path):
                    zf.write(dir_path, f"{rel}/")
            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel = os.path.relpath(file_path, extract_dir).replace(os.sep, "/")
                zf.write(file_path, rel)


def _process_archive_job(session: Session, job: TranslationJob) -> None:
    zip_path = _resolve_archive_path(job)
    if not zip_path:
        raise _BlockingJobError("Archive source introuvable")

    direction = job.direction.value
    translatable_exts = _get_translatable_extensions(session)
    extract_dir = tempfile.mkdtemp(
        prefix=f"job-{job.id}-", dir=settings.translation_tmp_path
    )

    report = {
        "total_files": 0,
        "translated": 0,
        "copied": 0,
        "errors": 0,
        "error_details": [],
    }

    try:
        _extract_archive(zip_path, extract_dir, session)

        # Deterministic (sorted) traversal for a stable report.
        all_files = []
        for root, _dirs, files in os.walk(extract_dir):
            for file_name in files:
                full = os.path.join(root, file_name)
                rel = os.path.relpath(full, extract_dir)
                all_files.append((rel, full))
        all_files.sort()
        report["total_files"] = len(all_files)

        for rel, full in all_files:
            _check_cancelled(session, job.id)
            ext = os.path.splitext(rel)[1].lstrip(".").lower()
            if ext not in translatable_exts:
                report["copied"] += 1  # copied as-is into the final archive
                continue
            try:
                _translate_archive_file(full, ext, session, direction, job.id)
                report["translated"] += 1
            except JobCancelled:
                raise
            except Exception as exc:  # noqa: BLE001
                # Best-effort processing: file copied as-is + detailed
                # error in the report.
                logger.warning("File %s not translated (%s), copied as-is.", rel, exc)
                report["errors"] += 1
                report["error_details"].append({"file": rel, "error": str(exc)})

        os.makedirs(settings.translations_path, exist_ok=True)
        result_path = os.path.join(settings.translations_path, f"{job.id}.zip")
        _rebuild_archive(extract_dir, result_path)

        job.result_zip_path = result_path
        job.report_json = json.dumps(report, ensure_ascii=False)
        job.status = TranslationJobStatus.done
        job.finished_at = datetime.utcnow()
        logger.info(
            "Archive job %s completed: %s translated, %s copied, %s errors.",
            job.id,
            report["translated"],
            report["copied"],
            report["errors"],
        )

    finally:
        # Source archive and extraction directory are never kept.
        shutil.rmtree(extract_dir, ignore_errors=True)
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
        job.archive_tmp_filename = None


# ------------------------------------------------------------- main loop

_SCHEMA_PATCHES = {
    "translationjob": {
        "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
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


def _ensure_schema_upgrades() -> None:
    """Safety net (the backend applies the same patch at its startup) for
    columns added after the initial schema."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine_db)
    for table, columns in _SCHEMA_PATCHES.items():
        if table not in inspector.get_table_names():
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        for column, ddl_type in columns.items():
            if column in existing:
                continue
            with engine_db.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def main_loop() -> None:
    logger.info(
        "Translation worker started. Polling every %ss.",
        settings.poll_interval_seconds,
    )

    _ensure_schema_upgrades()

    with Session(engine_db) as startup_session:
        try:
            recover_stale_processing_jobs(startup_session)
        except Exception:  # noqa: BLE001
            logger.exception("Error while recovering stuck jobs at startup")

    consecutive_errors = 0
    max_backoff_seconds = 60

    while True:
        with Session(engine_db) as session:
            try:
                process_pending_model_downloads(session)
                process_pending_model_deletions(session)
                processed = process_pending_job(session)
                consecutive_errors = 0
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected error in the main loop")
                processed = False
                consecutive_errors += 1

        if consecutive_errors > 0:
            backoff = min(
                settings.poll_interval_seconds * (2 ** consecutive_errors),
                max_backoff_seconds,
            )
            logger.warning("Pausing %ss after %s consecutive error(s).", backoff, consecutive_errors)
            time.sleep(backoff)
        elif not processed:
            time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main_loop()
