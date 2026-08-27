# Worker — Traitement de transcription

## Rôle

Boucle de traitement séquentielle (un seul job à la fois) qui :
- consomme les jobs `pending` créés par le backend
- télécharge/supprime les modèles faster-whisper à la demande de l'admin
- transcrit l'audio en français avec le modèle configuré sur le job
- génère un fichier `.vtt` (texte nettoyé + horodatage)
- supprime systématiquement l'audio source après traitement (succès ou échec)
- reprend automatiquement les jobs restés bloqués en `processing` après un
  crash ou redémarrage du conteneur

## Développement local (hors Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # inclut faster-whisper (lourd)
pip install -r requirements-dev.txt      # pytest pour les tests
```

## Lancer les tests

```bash
pytest -v
```

**Important** : les tests unitaires (`tests/test_text_postprocess.py`,
`tests/test_vtt.py`, `tests/test_worker_logic.py`) **ne nécessitent pas**
`faster-whisper` installé — le chargement réel d'un modèle Whisper est
simulé (`monkeypatch`) dans `test_worker_logic.py`. Pour lancer uniquement
ces tests sans attendre l'installation de `faster-whisper` :

```bash
pip install sqlmodel pydantic-settings pytest
pytest -v
```

Couverture actuelle (Phase 3) :
- post-traitement du texte (nettoyage espaces/ponctuation, majuscules) — 12 tests
- génération WebVTT (format, horodatage, segments vides) — 5 tests
- logique de traitement des jobs : succès, audio manquant, erreur de
  transcription, ordre FIFO — 5 tests
- reprise après crash des jobs bloqués en `processing` — 3 tests

Non couvert par des tests automatisés (nécessiterait un vrai modèle
faster-whisper téléchargé, trop lourd pour une suite de tests unitaires) :
- `_get_whisper_model` (chargement réel d'un modèle)
- `process_pending_model_downloads` / `process_pending_model_deletions`
  (accès réseau HuggingFace / suppression disque réelle)

## Lancer le worker en local

```bash
export SQLITE_PATH=./dev.db
export AUDIO_TMP_PATH=./dev_audio_tmp
export TRANSCRIPTS_PATH=./dev_transcripts
export WHISPER_MODELS_PATH=./dev_models

python -m app.main
```
