FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Tests (tests/ folder, pytest.ini) stay out of the production image;
# they are run outside the build (see backend README).

# Volumes expected at runtime (mounted via docker-compose):
#   /data          -> SQLite database
#   /audio_tmp     -> temporary audio files (purged after processing)
#   /transcripts   -> generated .vtt files
#   /models        -> downloaded Whisper models (shared with the worker)

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
