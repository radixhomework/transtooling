FROM python:3.11-slim

WORKDIR /app

# ffmpeg requis par faster-whisper pour décoder les fichiers audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Les tests (dossier tests/, pytest.ini, requirements-dev.txt) restent hors
# de l'image de production ; ils sont exécutés en dehors du build (voir
# README worker).

# Volumes attendus au runtime (montés via docker-compose) :
#   /data          -> base SQLite (partagée avec le backend)
#   /audio_tmp     -> fichiers audio à transcrire (supprimés après traitement)
#   /transcripts   -> fichiers .vtt générés
#   /models        -> modèles faster-whisper téléchargés à la demande

CMD ["python", "-m", "app.main"]
