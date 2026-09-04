# Backend — transcription API

## Local development (outside Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Required system dependency for tests and for production uploads**:
`ffmpeg` (provides `ffprobe`, used to validate audio file durations).

```bash
# Debian/Ubuntu
sudo apt-get install ffmpeg
```

## Running the tests

```bash
pytest -v
```

The tests use a dedicated temporary SQLite database (created in a system
temporary folder, isolated from any real database) and need no external
service.

Current coverage (Phases 1 & 2 + translation API):
- authentication (login, refresh token, password change, brute-force protection)
- user management (creation, enable/disable, password reset, deletion, admin/user permission checks)
- transcription jobs (valid/invalid upload, unsupported formats, size/duration overflow, owner/admin permissions, `.vtt` download, deletion, cancellation)
- translation jobs (text mode, ZIP archive mode with security checks, formats, permissions, cancellation)
- admin application settings (size/duration limits, database persistence, permission checks)
- Whisper and translation model endpoints (download/delete/enable flows, progress fields)

The tests of the `whisper_models` real download/deletion flows would require
network access to HuggingFace and are not covered.

Upload tests use short audio files generated on the fly via `ffmpeg`
(synthetic silence/tone), so no binary file is committed to the repository.

## Running the server locally

```bash
export SQLITE_PATH=./dev.db
export AUDIO_TMP_PATH=./dev_audio_tmp
export TRANSCRIPTS_PATH=./dev_transcripts
export WHISPER_MODELS_PATH=./dev_models
export ADMIN_LOGIN=admin
export ADMIN_PASSWORD=changeme
export JWT_SECRET=dev-secret

uvicorn app.main:app --reload
```

Interactive documentation then available at http://localhost:8000/docs
