# Backend — API de transcription audio

## Développement local (hors Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Dépendance système requise pour les tests et pour l'upload en production** :
`ffmpeg` (fournit `ffprobe`, utilisé pour valider la durée des fichiers audio).

```bash
# Debian/Ubuntu
sudo apt-get install ffmpeg
```

## Lancer les tests

```bash
pytest -v
```

Les tests utilisent une base SQLite temporaire dédiée (créée dans un dossier
temporaire système, isolée de toute base de données réelle) et n'ont besoin
d'aucun service externe.

Couverture actuelle (Phases 1 & 2) :
- authentification (login, refresh token, changement de mot de passe, protection brute-force)
- gestion des utilisateurs (création, activation/désactivation, réinitialisation de mot de passe, suppression, contrôle des permissions admin/utilisateur)
- jobs de transcription (upload valide/invalide, formats non supportés, dépassement de taille/durée, permissions propriétaire/admin, téléchargement du `.vtt`, suppression)
- paramètres applicatifs admin (limites taille/durée, persistance en base, contrôle des permissions)

Les tests des modules `whisper_models` (téléchargement/suppression réels) et
l'intégration complète du worker (Phase 3) seront ajoutés au fur et à mesure.

Les tests d'upload utilisent de courts fichiers audio générés à la volée via
`ffmpeg` (silence/tonalité synthétique), donc aucun fichier binaire n'est
committé dans le dépôt.

## Lancer le serveur en local

```bash
export SQLITE_PATH=./dev.db
export AUDIO_TMP_PATH=./dev_audio_tmp
export TRANSCRIPTS_PATH=./dev_transcripts
export WHISPER_MODELS_PATH=./dev_models
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD=changeme
export JWT_SECRET=dev-secret

uvicorn app.main:app --reload
```

Documentation interactive disponible ensuite sur http://localhost:8000/docs
