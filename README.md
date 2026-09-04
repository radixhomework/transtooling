# TransTooLing

Self-hosted web application for **audio transcription** and **FR↔EN
translation**, 100% local: no file or text is ever sent to a third-party
service, all processing runs on the machine (CPU only).

## Features

**Transcription** (faster-whisper)
- Audio → timestamped text, in French (`.vtt` or `.txt`)
- Progress percentage, cancellation while processing
- Model choice at upload, models downloaded on demand
- The source audio is deleted after processing; only the transcription is
  kept

**Translation** (NLLB-200 via CTranslate2, CC-BY-NC license — non-commercial
use)
- Manually entered text or ZIP archives of technical files: JSON (keys
  preserved), HTML (text and attributes), Markdown (full syntax: tables,
  code, links — paths and code never translated)
- File names and tree structure preserved, layout respected (line breaks,
  indentation)
- Translation cache, per-file processing report
- Translatable extensions configurable by the administrator

**Common**
- Login-based authentication (JWT), user/admin roles, admin account created
  at first startup
- User, model and limit management from the admin panel
- Sequential processing with automatic recovery after a worker crash
- Docker Compose deployment (FastAPI backend, React frontend, two Python
  workers, shared SQLite), Apache reverse proxy in production

> Note: the user interface is in French (product decision), while all code,
> comments, logs and documentation are in English.
