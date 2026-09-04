FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Les tests (dossier tests/, pytest.ini) restent hors de l'image de
# production ; ils sont exécutés en dehors du build (voir README backend).

# Volumes attendus au runtime (montés via docker-compose) :
#   /data          -> base SQLite
#   /audio_tmp     -> fichiers audio temporaires (purgés après traitement)
#   /transcripts   -> fichiers .vtt générés
#   /models        -> modèles Whisper téléchargés (partagé avec le worker)

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
