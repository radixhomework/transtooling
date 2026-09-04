FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Les tests (dossier tests/, pytest.ini, requirements-dev.txt) restent hors
# de l'image de production ; ils sont exécutés en dehors du build.

# Volumes attendus au runtime (montés via docker-compose) :
#   /data               -> base SQLite (partagée avec le backend)
#   /translation_models -> modèles OPUS-MT CTranslate2 téléchargés à la demande
#   /translation_tmp    -> archives uploadées (supprimées après traitement)
#   /translations       -> archives traduites générées

CMD ["python", "-m", "app.main"]
