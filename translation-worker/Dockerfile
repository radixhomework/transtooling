FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Tests (tests/ folder, pytest.ini, requirements-dev.txt) stay out of the
# production image; they are run outside the build.

# Volumes expected at runtime (mounted via docker-compose):
#   /data               -> SQLite database (shared with the backend)
#   /translation_models -> CTranslate2 translation models downloaded on demand
#   /translation_tmp    -> uploaded archives (deleted after processing)
#   /translations       -> generated translated archives

CMD ["python", "-m", "app.main"]
