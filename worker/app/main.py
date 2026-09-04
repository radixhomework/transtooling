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

# Throttle des écritures de progression en base : SQLite est partagé avec le
# backend, on évite de committer à chaque segment/token du téléchargement.
PROGRESS_MIN_DELTA_PERCENT = 2
PROGRESS_MIN_INTERVAL_SECONDS = 2.0
# Intervalle minimal entre deux consultations du fanion d'annulation en base.
CANCEL_CHECK_INTERVAL_SECONDS = 1.0


class JobCancelled(Exception):
    """Levée quand l'annulation d'un job est demandée pendant son traitement."""

engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)

# Cache en mémoire des modèles faster-whisper déjà chargés (évite de recharger
# le modèle à chaque job s'il est identique au précédent).
_loaded_models: dict = {}


def _get_whisper_model(model_name: str):
    from faster_whisper import WhisperModel as FasterWhisperModel

    if model_name not in _loaded_models:
        logger.info("Chargement du modèle faster-whisper '%s' en mémoire...", model_name)
        _loaded_models.clear()  # un seul modèle en mémoire à la fois (simplicité/RAM)
        _loaded_models[model_name] = FasterWhisperModel(
            model_name,
            device="cpu",
            compute_type=settings.whisper_compute_type,
            download_root=settings.whisper_models_path,
        )
    return _loaded_models[model_name]


class _DownloadProgressState:
    """
    Agrège la progression d'un snapshot_download (une barre tqdm par fichier,
    téléchargés potentiellement en parallèle par huggingface_hub) et la
    persiste dans WhisperModel.download_progress, avec throttle.
    """

    def __init__(self, model_id: int, min_interval_seconds: float = 1.0):
        self._model_id = model_id
        self._min_interval_seconds = min_interval_seconds
        self._lock = threading.Lock()
        self._active_bars: dict[int, tuple[int, int | None]] = {}  # id(bar) -> (octets, total)
        self._completed_bytes = 0
        self._completed_total = 0
        # -inf : la première écriture passe toujours (time.monotonic() peut
        # démarrer proche de zéro dans un conteneur fraîchement lancé).
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
        """Transfère une barre fermée vers le cumul : son id peut être
        réutilisé par une autre barre (ids Python recyclés)."""
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
        # Double throttle : délai minimum écoulé ET progression réellement
        # changée (sinon un téléchargement rapide écrirait en base à chaque
        # petit saut de 1 %).
        if now - self._last_write < self._min_interval_seconds:
            return None
        if percent == self._last_percent:
            return None
        self._last_percent = percent
        self._last_write = now
        return percent

    def _write_percent(self, percent: int) -> None:
        try:
            # Session courte dédiée : ce callback peut être appelé depuis un
            # thread de téléchargement huggingface_hub, pas celui du worker.
            with Session(engine) as session:
                model = session.get(WhisperModel, self._model_id)
                if model and model.status == ModelStatus.downloading:
                    model.download_progress = percent
                    session.add(model)
                    session.commit()
        except Exception:  # noqa: BLE001
            # Best-effort : un souci d'écriture ne doit jamais casser le
            # téléchargement lui-même.
            logger.debug("Écriture de la progression impossible", exc_info=True)


def _make_progress_tqdm_class(state: _DownloadProgressState) -> type:
    """Classe tqdm branchée sur un état de progression (closure), à passer à
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
    """Taille réelle sur disque du cache huggingface du modèle, en Mo.

    Le cache utilise blobs (fichiers réels) + snapshots (symlinks vers les
    blobs) : les liens sont ignorés pour éviter le double comptage.
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
    """Renseigne la taille disque des modèles téléchargés avant l'ajout de la
    colonne disk_size_mb (jamais calculée pour eux sinon)."""
    models = session.exec(
        select(WhisperModel).where(WhisperModel.status == ModelStatus.downloaded)
    ).all()
    for model in models:
        if model.disk_size_mb is not None:
            continue
        size = _compute_model_disk_size_mb(model.name)
        if size is not None:
            logger.info("Taille disque du modèle '%s' renseignée : %s Mo.", model.name, size)
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
    Au démarrage du worker, tout job resté au statut 'processing' signale un
    arrêt anormal (crash, redémarrage du conteneur) pendant son traitement.
    L'audio temporaire n'est supprimé qu'une fois le traitement terminé
    (succès ou échec), donc il est probablement toujours présent : on
    remet ces jobs en 'pending' pour qu'ils soient retraités automatiquement.
    """
    stale_jobs = session.exec(
        select(TranscriptionJob).where(TranscriptionJob.status == JobStatus.processing)
    ).all()

    for job in stale_jobs:
        audio_path = _resolve_audio_path(job)
        if audio_path:
            logger.warning(
                "Job %s trouvé bloqué en 'processing' au démarrage : remise en file d'attente.",
                job.id,
            )
            job.status = JobStatus.pending
            job.started_at = None
            job.progress = 0
        else:
            logger.warning(
                "Job %s bloqué en 'processing' mais audio introuvable : marqué en erreur.",
                job.id,
            )
            job.status = JobStatus.error
            job.error_message = "Traitement interrompu (redémarrage du worker) et fichier audio introuvable"
            job.finished_at = datetime.utcnow()
        session.add(job)
    session.commit()


def _is_cancel_requested(session: Session, job_id: int) -> bool:
    """Relit le fanion d'annulation depuis la base (posé par l'API)."""
    row = session.exec(
        select(TranscriptionJob.cancel_requested).where(TranscriptionJob.id == job_id)
    ).first()
    return bool(row)


def process_pending_job(session: Session) -> bool:
    """Traite un seul job en attente. Retourne True si un job a été traité."""
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

    # Annulation demandée pendant que le job était en file.
    if _is_cancel_requested(session, job.id):
        job.status = JobStatus.cancelled
        job.error_message = None
        job.finished_at = datetime.utcnow()
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        job.audio_tmp_filename = None
        session.add(job)
        session.commit()
        logger.info("Job %s annulé par l'utilisateur avant traitement.", job.id)
        return True

    last_cancel_check = time.monotonic()

    try:
        if not audio_path:
            raise FileNotFoundError("Fichier audio introuvable pour ce job")

        model = _get_whisper_model(job.model_used)
        segments_iter, info = model.transcribe(audio_path, language="fr")

        # Dénominateur de la progression : durée mesurée par Whisper, à défaut
        # celle mesurée par ffprobe à l'upload.
        duration = getattr(info, "duration", None) or job.audio_duration_seconds

        # segments est un générateur consommé au fil du décodage : itérer
        # incrémentalement permet de suivre la progression et de détecter une
        # annulation sans attendre la fin du fichier.
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

        # Le nettoyage/post-traitement du texte (espaces, ponctuation,
        # majuscules) est appliqué segment par segment dans segments_to_vtt.
        vtt_content = segments_to_vtt(segments)

        os.makedirs(settings.transcripts_path, exist_ok=True)
        vtt_path = os.path.join(settings.transcripts_path, f"{job.id}.vtt")
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(vtt_content)

        job.result_vtt_path = vtt_path
        job.status = JobStatus.done
        job.progress = 100
        job.finished_at = datetime.utcnow()
        logger.info("Job %s terminé avec succès.", job.id)

    except JobCancelled:
        logger.info("Job %s annulé par l'utilisateur.", job.id)
        job.status = JobStatus.cancelled
        job.error_message = None
        job.finished_at = datetime.utcnow()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur lors du traitement du job %s", job.id)
        job.status = JobStatus.error
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()

    finally:
        # L'audio source n'est jamais conservé, succès, échec ou annulation.
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        job.audio_tmp_filename = None
        session.add(job)
        session.commit()

    return True


def process_pending_model_downloads(session: Session) -> None:
    """Télécharge les modèles marqués 'downloading' par l'admin via l'API."""
    from faster_whisper import WhisperModel as FasterWhisperModel

    pending_models = session.exec(
        select(WhisperModel).where(WhisperModel.status == ModelStatus.downloading)
    ).all()

    for model in pending_models:
        logger.info("Téléchargement du modèle '%s'...", model.name)
        # Réinitialise la progression avant de démarrer (le callback écrit
        # via une session séparée, celle-ci ne verrait pas ses valeurs).
        model.download_progress = 0
        session.add(model)
        session.commit()

        state = _DownloadProgressState(model.id)
        try:
            # Téléchargement explicite avec remontée de progression, puis
            # construction du modèle (cache hit, aucun re-téléchargement).
            # Repo et patterns suivent la convention faster-whisper
            # (Systran/faster-whisper-<name>) pour partager le même cache.
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
            logger.info("Modèle '%s' téléchargé.", model.name)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Échec du téléchargement du modèle '%s'", model.name)
            model.status = ModelStatus.error
            model.download_progress = None
            model.error_message = str(exc)

        session.add(model)
        session.commit()


def process_pending_model_deletions(session: Session) -> None:
    """
    Supprime physiquement les fichiers d'un modèle repassé à 'not_downloaded'
    côté API alors qu'il existe encore sur disque.
    Convention faster-whisper : dossier models--<org>--faster-whisper-<name>
    sous whisper_models_path (cache huggingface_hub).
    """
    models = session.exec(select(WhisperModel).where(WhisperModel.status == ModelStatus.not_downloaded)).all()
    for model in models:
        pattern = os.path.join(settings.whisper_models_path, f"*{model.name}*")
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                logger.info("Suppression du modèle sur disque : %s", path)
                shutil.rmtree(path, ignore_errors=True)


# Colonnes apparues après le schéma initial : create_all ne fait pas d'ALTER
# TABLE sur une base existante. Le backend applique le même correctif à son
# démarrage ; ce filet de sécurité couvre le cas où le worker démarrerait
# avant la migration backend. À maintenir en cohérence avec
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
    logger.info("Worker de transcription démarré. Polling toutes les %ss.", settings.poll_interval_seconds)

    _ensure_schema_upgrades()

    with Session(engine) as startup_session:
        try:
            backfill_model_disk_sizes(startup_session)
            recover_stale_processing_jobs(startup_session)
        except Exception:  # noqa: BLE001
            logger.exception("Erreur lors de la reprise des jobs bloqués au démarrage")

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
                logger.exception("Erreur inattendue dans la boucle principale du worker")
                processed = False
                consecutive_errors += 1

        if consecutive_errors > 0:
            # Backoff exponentiel plafonné, pour éviter une boucle de crash
            # trop agressive en cas de problème persistant (ex: base
            # inaccessible temporairement).
            backoff = min(settings.poll_interval_seconds * (2 ** consecutive_errors), max_backoff_seconds)
            logger.warning("Pause de %ss après %s erreur(s) consécutive(s).", backoff, consecutive_errors)
            time.sleep(backoff)
        elif not processed:
            time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main_loop()
