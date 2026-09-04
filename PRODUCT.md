# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Small team: a few colleagues sign in with their own account (simple login +
password, no email); an administrator manages users, models and settings.
UI available in English (default) and French.

## Product Purpose

TransTooLing is a self-hosted web application with two first-rank features:

- **Transcription**: upload an audio file and get a timestamped written
  transcription, downloadable as `.vtt` or plain text.
- **Translation**: translate manually entered text, or a ZIP archive of
  technical files (JSON, HTML, Markdown), with file names, tree structure
  and file syntax preserved — only the human-readable content is
  translated, never code, paths or configuration.

Both features run entirely on the machine the application is deployed on:
no file or text is ever sent to a third-party service, and processing
requires no GPU. Success means both tasks completed reliably end to end,
with nothing leaving the machine.

## Positioning

100% local processing: content confidentiality is guaranteed by the
architecture, with no dependency on a third-party service and no recurring
cost — something a cloud service cannot verifiably promise.

## Operating Context

- Docker Compose deployment (FastAPI backend, React/Vite frontend served
  by Nginx, two independent sequential job workers, shared SQLite), behind
  an Apache reverse proxy in production, bound to localhost only.
- Jobs processed one at a time per worker; status and progress tracking by
  polling; cancellation supported while processing; automatic recovery
  after a worker crash.
- Processing models are downloaded on demand from the admin panel and can
  be enabled, disabled or deleted there.

## Capabilities and Constraints

- Authentication by simple login (no email), user/admin roles, initial
  admin account created at first startup, brute-force protection on login.
- Transcription: common audio formats accepted; size and duration limits
  configurable by the admin; source audio always deleted after processing
  (only the transcription is kept); progress percentage; cancellation.
- Translation: admin-configurable limits (text length, archive size, file
  count, uncompressed size) and admin-configurable list of translatable
  file extensions; translation cache to avoid re-translating identical
  content; per-file processing report (translated / copied / errors).
- CPU-only processing (no GPU required).
- Bilingual UI (English/French) with a language switcher; backend API
  error messages are returned in French.

## Brand Commitments

- Name: TransTooLing (explicitly chosen by the owner).
- Visual identity: the radixhomework.github.io editorial charte (root
  black, ivory, moss green, patinated copper; serif display typography;
  square corners; no shadows).

## Evidence on Hand

- Complete code and a working local instance (`docker compose up`);
  README.md documents the architecture and deployment.
- No real demo content, testimonials, screenshots or datasets: future work
  must not invent any.

## Product Principles

1. No data ever leaves the machine — an architectural promise, not a
   marketing argument.
2. Simplicity first: short flows, explicit error messages, complex
   settings reserved for the admin panel.
3. Autonomy: runs on a modest machine, no paid service required.
4. Source files are never kept beyond processing.
