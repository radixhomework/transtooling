import json
import os
import zipfile

from sqlmodel import Session, select

from app import main as worker_main
from app.models import (
    TranslationCache,
    TranslationDirection,
    TranslationJob,
    TranslationJobStatus,
    TranslationJobType,
    TranslationModel,
    TranslationModelStatus,
)

# NOTE : ne pas importer depuis tests/conftest.py — cela réexécuterait le
# module (nouveau tmpdir, variables d'environnement écrasées après
# l'import initial de app.main avec les anciens chemins).


def make_text_job(job_id=1, direction="fr-en", text="Bonjour le monde.", status="pending"):
    return TranslationJob(
        id=job_id,
        user_id=1,
        job_type=TranslationJobType.text,
        direction=TranslationDirection(direction),
        source_text=text,
        status=TranslationJobStatus(status),
    )


def make_archive_job(job_id, zip_path):
    return TranslationJob(
        id=job_id,
        user_id=1,
        job_type=TranslationJobType.archive,
        direction=TranslationDirection.fr_en,
        archive_tmp_filename=os.path.basename(zip_path),
        status=TranslationJobStatus.pending,
    )


def make_zip_file(files: dict, path: str) -> str:
    """Crée une archive ZIP de test ({nom: contenu}) et retourne son chemin."""
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return path


# --- Cache de traduction ---


def test_cache_hit_avoids_recomputation(db_session, fake_engine):
    worker_main.translate_texts(db_session, "fr-en", ["Bonjour"])
    call_count = len(fake_engine.calls)
    assert call_count == 1

    # Deuxième appel : hit complet, aucun nouveau calcul ni écriture.
    db_session.expire_all()
    result = worker_main.translate_texts(db_session, "fr-en", ["Bonjour"])
    assert result == ["[TR]Bonjour"]
    assert len(fake_engine.calls) == call_count
    rows = db_session.exec(select(TranslationCache)).all()
    assert len(rows) == 1


def test_cache_write_only_on_miss(db_session, fake_engine):
    worker_main.translate_texts(db_session, "fr-en", ["A", "B", "A"])
    # Dédupliqué : l'engine ne voit que A et B une fois chacun.
    assert fake_engine.calls == [["A", "B"]]
    rows = db_session.exec(select(TranslationCache)).all()
    assert len(rows) == 2


def test_cache_keyed_per_direction(db_session, fake_engine):
    worker_main.translate_texts(db_session, "fr-en", ["Bonjour"])
    worker_main.translate_texts(db_session, "en-fr", ["Bonjour"])
    # Même texte, directions différentes : deux entrées, deux calculs.
    rows = db_session.exec(select(TranslationCache)).all()
    assert len(rows) == 2
    assert fake_engine.calls == [["Bonjour"], ["Bonjour"]]


# --- Jobs mode texte ---


def test_text_job_success(db_session, fake_engine):
    job = make_text_job(job_id=1)
    db_session.add(job)
    db_session.commit()

    assert worker_main.process_pending_job(db_session) is True
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.done
    assert job.result_text == "[TR]Bonjour le monde."
    assert job.finished_at is not None


def test_text_job_no_pending_returns_false(db_session):
    assert worker_main.process_pending_job(db_session) is False


def test_text_job_missing_source_marked_error(db_session, fake_engine):
    job = make_text_job(job_id=2, text=None)
    db_session.add(job)
    db_session.commit()

    worker_main.process_pending_job(db_session)
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.error


# --- Jobs mode archive ---


def _make_archive_job(db_session, job_id, zip_path):
    job = make_archive_job(job_id, zip_path)
    db_session.add(job)
    db_session.commit()
    return job


def test_archive_job_translates_and_copies(db_session, fake_engine):
    files = {
        "data.json": json.dumps({"greeting": "Hello", "nested": {"label": "World"}}),
        "page.html": "<p>Hello html</p>",
        "docs/readme.md": "# Hello md\n\nA **bold** statement and `code`.\n",
        "assets/logo.png": b"\x89PNG-fake",
        "docs/readme.txt": "plain text, not translated",
        "empty/": "",
    }
    zip_path = make_zip_file(files, os.path.join(os.environ["TRANSLATION_TMP_PATH"], "a1.zip"))
    job = _make_archive_job(db_session, 10, zip_path)

    assert worker_main.process_pending_job(db_session) is True
    db_session.refresh(job)

    assert job.status == TranslationJobStatus.done
    assert job.result_zip_path and os.path.exists(job.result_zip_path)
    report = json.loads(job.report_json)
    # data.json, page.html, readme.md traduits ; logo.png, readme.txt copiés
    # (le dossier vide est préservé mais ne compte pas comme fichier).
    assert report["total_files"] == 5
    assert report["translated"] == 3
    assert report["copied"] == 2
    assert report["errors"] == 0

    with zipfile.ZipFile(job.result_zip_path) as zf:
        names = zf.namelist()
        assert "data.json" in names
        assert "page.html" in names
        assert "docs/readme.md" in names
        assert "assets/logo.png" in names
        assert "docs/readme.txt" in names
        assert "empty/" in names  # arborescence conservée
        data = json.loads(zf.read("data.json"))
        assert data["greeting"] == "[TR]Hello"
        assert data["nested"]["label"] == "[TR]World"
        assert b"\x89PNG-fake" == zf.read("assets/logo.png")
        assert "not translated" in zf.read("docs/readme.txt").decode()
        assert "[TR]Hello html" in zf.read("page.html").decode()

    # Nettoyage : archive source supprimée, champ vidé.
    assert not os.path.exists(zip_path)
    assert job.archive_tmp_filename is None


def test_archive_job_per_file_error_best_effort(db_session, fake_engine):
    files = {
        "good.json": json.dumps({"a": "Hello"}),
        "bad.json": "{invalid json",
        "page.html": "<p>Hi</p>",
    }
    zip_path = make_zip_file(files, os.path.join(os.environ["TRANSLATION_TMP_PATH"], "a2.zip"))
    job = _make_archive_job(db_session, 11, zip_path)

    worker_main.process_pending_job(db_session)
    db_session.refresh(job)

    # Le job réussit globalement : erreur par fichier → copie telle quelle.
    assert job.status == TranslationJobStatus.done
    report = json.loads(job.report_json)
    assert report["translated"] == 2
    assert report["errors"] == 1
    assert report["error_details"][0]["file"] == "bad.json"
    with zipfile.ZipFile(job.result_zip_path) as zf:
        assert zf.read("bad.json").decode() == "{invalid json"


def test_archive_job_extension_case_insensitive(db_session, fake_engine):
    files = {"upper.JSON": json.dumps({"k": "value"}), "upper.HTML": "<p>hey</p>"}
    zip_path = make_zip_file(files, os.path.join(os.environ["TRANSLATION_TMP_PATH"], "a3.zip"))
    job = _make_archive_job(db_session, 12, zip_path)

    worker_main.process_pending_job(db_session)
    db_session.refresh(job)
    report = json.loads(job.report_json)
    assert report["translated"] == 2
    assert report["copied"] == 0


def test_archive_job_missing_source_error(db_session, fake_engine):
    job = TranslationJob(
        id=13,
        user_id=1,
        job_type=TranslationJobType.archive,
        direction=TranslationDirection.fr_en,
        archive_tmp_filename="never.zip",
        status=TranslationJobStatus.pending,
    )
    db_session.add(job)
    db_session.commit()

    worker_main.process_pending_job(db_session)
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.error
    assert "introuvable" in (job.error_message or "").lower()


def test_archive_extraction_zip_slip_rejected(db_session, fake_engine):
    zip_path = os.path.join(os.environ["TRANSLATION_TMP_PATH"], "a4.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("normal.txt", "ok")
        # Chemin relatif remontant hors du répertoire d'extraction.
        zf.writestr("../../evil.txt", "boom")

    job = _make_archive_job(db_session, 14, zip_path)
    worker_main.process_pending_job(db_session)
    db_session.refresh(job)

    assert job.status == TranslationJobStatus.error
    assert job.stopped_reason
    assert not os.path.exists(
        os.path.join(os.environ["TRANSLATION_TMP_PATH"], "..", "..", "evil.txt")
    )


# --- Reprise après crash ---


def test_recover_stale_text_job_requeued(db_session):
    job = make_text_job(job_id=20, status="processing")
    db_session.add(job)
    db_session.commit()

    worker_main.recover_stale_processing_jobs(db_session)
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.pending
    assert job.started_at is None


def test_recover_stale_archive_job_with_source_requeued(db_session):
    zip_path = make_zip_file({"a.txt": "x"}, os.path.join(os.environ["TRANSLATION_TMP_PATH"], "a5.zip"))
    job = TranslationJob(
        id=21,
        user_id=1,
        job_type=TranslationJobType.archive,
        direction=TranslationDirection.fr_en,
        archive_tmp_filename=os.path.basename(zip_path),
        status=TranslationJobStatus.processing,
    )
    db_session.add(job)
    db_session.commit()

    worker_main.recover_stale_processing_jobs(db_session)
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.pending


def test_recover_stale_job_without_source_marked_error(db_session):
    job = make_text_job(job_id=22, text=None, status="processing")
    db_session.add(job)
    db_session.commit()

    worker_main.recover_stale_processing_jobs(db_session)
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.error


# --- Téléchargement des modèles ---


def test_model_download_success(db_session, monkeypatch):
    import os

    model = TranslationModel(
        id=30,
        direction=TranslationDirection.fr_en,
        status=TranslationModelStatus.downloading,
    )
    db_session.add(model)
    db_session.commit()

    calls = []

    def fake_snapshot_download(**kwargs):
        calls.append(kwargs)
        cache_dir = os.path.join(
            os.environ["TRANSLATION_MODELS_PATH"], "models--JustFrederik--nllb-200-distilled-600M-ct2-int8"
        )
        os.makedirs(cache_dir, exist_ok=True)
        blob = os.path.join(cache_dir, "model.bin")
        with open(blob, "wb") as f:
            f.write(b"\0" * (2 * 1024 * 1024))
        snapshots = os.path.join(cache_dir, "snapshots", "rev")
        os.makedirs(snapshots, exist_ok=True)
        os.symlink(blob, os.path.join(snapshots, "model.bin"))
        return snapshots

    monkeypatch.setattr(worker_main, "snapshot_download", fake_snapshot_download)

    worker_main.process_pending_model_downloads(db_session)
    db_session.refresh(model)

    assert model.status == TranslationModelStatus.downloaded
    assert model.download_progress == 100
    assert model.disk_size_mb == 2  # symlinks non comptés double
    assert calls[0]["repo_id"] == "JustFrederik/nllb-200-distilled-600M-ct2-int8"


def test_model_download_error(db_session, monkeypatch):
    model = TranslationModel(
        id=31,
        direction=TranslationDirection.en_fr,
        status=TranslationModelStatus.downloading,
    )
    db_session.add(model)
    db_session.commit()

    def failing(**kwargs):
        raise RuntimeError("Réseau indisponible")

    monkeypatch.setattr(worker_main, "snapshot_download", failing)
    worker_main.process_pending_model_downloads(db_session)
    db_session.refresh(model)

    assert model.status == TranslationModelStatus.error
    assert "Réseau indisponible" in model.error_message


# --- Annulation ---


def test_text_job_cancelled_before_processing(db_session, fake_engine):
    job = make_text_job(job_id=40, status="pending")
    job.cancel_requested = True
    db_session.add(job)
    db_session.commit()

    worker_main.process_pending_job(db_session)
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.cancelled
    assert job.result_text is None
    assert job.error_message is None
    assert job.finished_at is not None
    # Aucune traduction n'a été lancée.
    assert fake_engine.calls == []


def test_archive_job_cancelled_keeps_report_empty(db_session, fake_engine):
    zip_path = make_zip_file(
        {"a.json": '{"k": "v"}'}, os.path.join(os.environ["TRANSLATION_TMP_PATH"], "a_cancel.zip")
    )
    job = _make_archive_job(db_session, 41, zip_path)
    job.cancel_requested = True
    db_session.add(job)
    db_session.commit()

    worker_main.process_pending_job(db_session)
    db_session.refresh(job)
    assert job.status == TranslationJobStatus.cancelled
    assert not os.path.exists(zip_path)  # archive source nettoyée
