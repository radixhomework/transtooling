# Worker — Transcription processing

## Role

Sequential processing loop (one job at a time) that:
- consumes `pending` jobs created by the backend
- downloads/deletes faster-whisper models on admin request
- transcribes the audio in French with the model configured on the job
- generates a `.vtt` file (cleaned text + timestamps)
- always deletes the source audio after processing (success or failure)
- automatically recovers jobs left stuck in `processing` after a crash or
  container restart
- supports cancellation requested by the user during processing

## Local development (outside Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # includes faster-whisper (heavy)
pip install -r requirements-dev.txt      # pytest for the tests
```

## Running the tests

```bash
pytest -v
```

**Important**: the unit tests (`tests/test_text_postprocess.py`,
`tests/test_vtt.py`, `tests/test_worker_logic.py`) **do not require**
`faster-whisper` to be installed — actual Whisper model loading is
simulated (`monkeypatch`) in `test_worker_logic.py`. To run only these
tests without waiting for `faster-whisper` to install:

```bash
pip install sqlmodel pydantic-settings pytest
pytest -v
```

Current coverage (Phase 3 + progress/cancellation):
- text post-processing (space/punctuation cleanup, capitals) — 12 tests
- WebVTT generation (format, timestamps, empty segments) — 5 tests
- job processing logic: success, missing audio, transcription error, FIFO
  order — 5 tests
- crash recovery of jobs stuck in `processing` — 3 tests
- progress tracking and cancellation — 5 tests
- SQLite schema patch helper — 1 test

Not covered by automated tests (would require a real downloaded
faster-whisper model, too heavy for a unit test suite):
- `_get_whisper_model` (actual model loading)
- `process_pending_model_downloads` / `process_pending_model_deletions`
  (HuggingFace network access / real disk deletion)

## Running the worker locally

```bash
export SQLITE_PATH=./dev.db
export AUDIO_TMP_PATH=./dev_audio_tmp
export TRANSCRIPTS_PATH=./dev_transcripts
export WHISPER_MODELS_PATH=./dev_models

python -m app.main
```
