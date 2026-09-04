FROM python:3.11-slim

WORKDIR /app

# ffmpeg required by faster-whisper to decode audio files
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Tests (tests/ folder, pytest.ini, requirements-dev.txt) stay out of the
# production image; they are run outside the build (see worker README).

# Volumes expected at runtime (mounted via docker-compose):
#   /data          -> SQLite database (shared with the backend)
#   /audio_tmp     -> audio files to transcribe (deleted after processing)
#   /transcripts   -> generated .vtt files
#   /models        -> faster-whisper models downloaded on demand

CMD ["python", "-m", "app.main"]
