# Application de transcription audio (français) — Spécification & plan de développement

## 1. Vue d'ensemble

Application self-hosted permettant à des utilisateurs authentifiés d'uploader des fichiers audio et d'obtenir une transcription écrite en français, via un modèle Whisper exécuté localement (aucun appel externe, aucune donnée envoyée à OpenAI).

- **Frontend** : interface web (auth, upload, suivi de transcription, gestion des utilisateurs)
- **Backend** : API REST (auth, gestion utilisateurs, gestion des jobs de transcription)
- **Worker** : traitement asynchrone des transcriptions (faster-whisper ou whisper.cpp)
- **Base de données** : SQLite
- **Reverse proxy** : Apache HTTPD (hors conteneur), HTTPS

Déploiement : `docker-compose` avec 4 services (frontend, backend, worker, base de données/volume), pilotable en une seule commande (`docker-compose up -d`).

---

## 2. Architecture technique

```
                         ┌───────────────────────────┐
                         │   Apache (reverse proxy)   │
                         │   HTTPS / Let's Encrypt    │
                         └────────────┬───────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                     │
            ┌───────▼────────┐                  ┌────────▼────────┐
            │   frontend      │                  │    backend       │
            │ (Nginx + build  │─────API REST────▶│  (FastAPI)       │
            │  React/Vue)     │                  │  Auth JWT        │
            │  Port interne   │                  │  Port interne    │
            └─────────────────┘                  └────────┬─────────┘
                                                            │
                                       ┌────────────────────┼────────────────────┐
                                       │                    │                    │
                              ┌────────▼───────┐  ┌─────────▼────────┐  ┌────────▼────────┐
                              │  SQLite (volume)│  │  File d'attente   │  │ Volume fichiers  │
                              │  users, jobs,   │  │  (jobs à traiter) │  │ audio temporaires│
                              │  config         │  │                   │  │ (purgés après    │
                              └─────────────────┘  └─────────┬─────────┘  │  traitement)     │
                                                              │            └─────────────────┘
                                                    ┌─────────▼─────────┐
                                                    │      worker        │
                                                    │  faster-whisper /  │
                                                    │  whisper.cpp        │
                                                    │  + post-traitement  │
                                                    │  texte (ponctuation)│
                                                    └─────────────────────┘
```

### Services `docker-compose`

| Service    | Rôle                                                                 | Image de base            |
|------------|-----------------------------------------------------------------------|---------------------------|
| `frontend` | Interface web, servie en statique                                     | `node` (build) → `nginx`  |
| `backend`  | API REST, auth, orchestration des jobs                                | `python:3.11-slim`        |
| `transcription-worker` | Consomme la file de jobs, exécute Whisper, écrit le résultat en base | `python:3.11-slim` (+ modèle Whisper) |
| `translation-worker` | Traduction FR↔EN (CTranslate2 + OPUS-MT), worker séquentiel indépendant | `python:3.11-slim` (+ modèles OPUS-MT) |
| `db`       | Pas un vrai service conteneurisé — SQLite en fichier sur volume partagé backend/workers | — (volume Docker) |

> SQLite étant un fichier, il est monté en volume partagé entre `backend` et `worker`. Attention à gérer les accès concurrents (voir section verrouillage plus bas).

> Les modèles faster-whisper téléchargés à la demande sont stockés sur un **volume Docker persistant dédié** (ex. `whisper_models_data`) monté dans le conteneur `worker`, afin de survivre aux redémarrages/recréations du conteneur et éviter un re-téléchargement à chaque déploiement.

### File d'attente de jobs

Pas besoin de Redis/Celery vu le faible volume attendu. Une table `jobs` en base avec statuts (`pending`, `processing`, `done`, `error`) suffit :
- Le `worker` poll la base à intervalle régulier (ex. toutes les 5 secondes) et traite les jobs `pending` un par un (ou en parallèle limité selon CPU).
- Simplicité de mise en œuvre, pas de dépendance supplémentaire, adapté à un usage mono-instance.

---

## 3. Modèle de données (SQLite)

**users**
- id, email/login, password_hash, role (`admin` / `user`), is_active, created_at

**transcription_jobs**
- id, user_id, filename_original, status, model_used, langue (fixé à `fr`), created_at, started_at, finished_at, error_message
- audio_duration_seconds (durée mesurée par ffprobe à l'upload), progress (0-100, mis à jour par le worker pendant le traitement)
- résultat texte stocké directement en base (ou fichier texte sur volume dédié aux résultats, à décider selon volumétrie)

**app_settings** (configurable par l'admin, persistée en base)
- modèle par défaut
- taille max de fichier (Mo)
- durée max de fichier (minutes)

**whisper_models** (état des modèles faster-whisper)
- nom du modèle (tiny, base, small, medium, large-v3...), statut (téléchargé / en cours de téléchargement / non téléchargé), activé (oui/non), taille disque, date de téléchargement
- download_progress (0-100 pendant le téléchargement, remonté par le worker via un callback tqdm branché sur `huggingface_hub.snapshot_download`)

**translation_jobs** (jobs de traduction FR↔EN, traités par translation-worker)
- job_type (`text` | `archive`), direction (`fr-en` | `en-fr`), statut (pending/processing/done/error)
- mode texte : source_text / result_text en base
- mode archive : archive_tmp_filename (source, purgée), result_zip_path, report_json (total/traduits/copiés/erreurs + error_details), stopped_reason (erreur bloquante)
- user_id, created_at, started_at, finished_at, error_message

**translation_models** (état des modèles OPUS-MT CTranslate2, un par direction)
- direction (fr-en / en-fr, unique), statut, activé, taille disque, download_progress, error_message, downloaded_at

**translation_cache** (cache des traductions, table SQLite)
- cache_key = sha256(direction + \x00 + texte source), direction, translated_text ; lu avant toute traduction, écrit uniquement après un calcul effectif (jamais sur un hit)

> Colonnes ajoutées après coup (progress, audio_duration_seconds,
> download_progress) : `create_all` ne fait pas d'ALTER TABLE, un petit
> correctif idempotent (`_ensure_columns` backend / `_ensure_schema_upgrades`
> worker) les ajoute aux bases existantes au démarrage. Les définitions de
> modèles restent dupliquées backend/worker et doivent être modifiées des deux
> côtés.

---

## 4. Fonctionnalités détaillées

### Authentification
- Login/mot de passe, hash argon2/bcrypt
- JWT (access + refresh token)
- Compte admin initial créé au premier démarrage à partir des variables du `.env` (`ADMIN_EMAIL`, `ADMIN_PASSWORD`) — modifiable ensuite depuis l'app
- Changement de mot de passe par l'utilisateur lui-même (ancien mot de passe requis)
- Politique de mot de passe minimale (longueur, complexité) configurable

### Gestion des utilisateurs (admin)
- Créer un utilisateur / administrateur
- Activer / désactiver un compte
- Réinitialiser le mot de passe d'un utilisateur
- Lister les utilisateurs et leur activité (dernière connexion, nb de transcriptions)

### Transcription
- Upload d'un fichier audio (formats : mp3, wav, m4a, ogg, webm)
- Vérification côté backend : taille et durée max (valeurs définies par l'admin)
- Création d'un job en base, statut `pending`
- Le worker traite le job avec le modèle Whisper sélectionné (par défaut, ou choisi par l'utilisateur si plusieurs modèles sont activés)
- Post-traitement du texte : ponctuation, découpage en paragraphes
- Suppression du fichier audio source immédiatement après traitement (succès ou échec) — aucune rétention audio
- Résultat consultable et téléchargeable au format `.vtt` (texte + timestamps)
- Historique des transcriptions par utilisateur (texte `.vtt` conservé indéfiniment, audio jamais conservé)
- Suppression d'une transcription possible par son propriétaire ou par un administrateur (suppression définitive de l'entrée et du fichier `.vtt`)

### Administration — gestion des modèles Whisper
- L'admin voit la liste des modèles faster-whisper disponibles (tiny, base, small, medium, large-v3) avec leur statut : téléchargé / non téléchargé
- Depuis le panneau d'administration, l'admin peut **télécharger** un modèle à la demande (déclenche le téléchargement par le worker vers un volume partagé de modèles) ou **supprimer** un modèle déjà téléchargé (libère l'espace disque)
- Parmi les modèles téléchargés, l'admin choisit lesquels sont **activés** (proposés aux utilisateurs) et lequel est le **modèle par défaut**
- Un job ne peut être lancé qu'avec un modèle effectivement téléchargé et activé
- Configuration de la taille/durée max de fichier accepté

### Journal / traçabilité (recommandé, à confirmer)
- Log simple des connexions et des transcriptions (qui, quand, quel modèle) pour audit — sans donnée audio

---

## 5. Reverse proxy Apache — éléments prévus

- VirtualHost HTTP (port 80) → redirection vers HTTPS
- VirtualHost HTTPS (port 443) avec certificat Let's Encrypt (certbot)
- `ProxyPass` / `ProxyPassReverse` vers le service `frontend` (statique) et `backend` (API, sous un préfixe type `/api`)
- Support des headers nécessaires si upload de gros fichiers (`LimitRequestBody` à adapter à la taille max configurée)
- Headers de sécurité : HSTS, X-Frame-Options, X-Content-Type-Options
- Timeout adapté si transcription synchrone côté requête (normalement non nécessaire puisque le traitement est asynchrone via jobs)

---

## 6. Variables d'environnement prévues (`.env`)

```
# Admin par défaut
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme

# Backend
JWT_SECRET=xxxxx
JWT_EXPIRATION=3600

# Limites par défaut (modifiables ensuite par l'admin en base)
DEFAULT_MAX_FILE_SIZE_MB=200
DEFAULT_MAX_DURATION_MIN=60

# Whisper
DEFAULT_WHISPER_MODEL=small
WHISPER_ENGINE=faster-whisper
WHISPER_MODELS_PATH=/models     # volume persistant dédié aux modèles téléchargés

# Base de données
SQLITE_PATH=/data/app.db
```

---

## 7. Décisions retenues (suite aux points de clarification)

1. **Moteur** : faster-whisper (intégration Python native, cohérent avec FastAPI).
2. **Téléchargement des modèles** : à la demande, déclenché depuis le panneau d'administration. L'admin peut ajouter (télécharger) ou supprimer un modèle Whisper local, sans tout précharger au build de l'image worker.
3. **Format de sortie** : `.vtt` uniquement (avec timestamps). Whisper produit les segments horodatés nativement ; le post-traitement génère un fichier `.vtt` structuré.
4. **Traitement concurrent** : un seul job à la fois dans le worker (file séquentielle). Simple, robuste, adapté à SQLite et évite la contention CPU/RAM.
5. **Rétention des transcriptions** : conservées indéfiniment (texte/.vtt uniquement, jamais l'audio). Suppression possible manuellement par l'utilisateur propriétaire du job ou par un administrateur.

---

## 8. Plan de développement (tâches)

### Phase 0 — Setup projet
- [ ] Structure du repo (`frontend/`, `backend/`, `worker/`, `docker-compose.yml`, `.env.example`)
- [ ] Dockerfile `frontend` (build + nginx)
- [ ] Dockerfile `backend` (FastAPI)
- [ ] Dockerfile `worker` (Python + moteur Whisper choisi)
- [ ] `docker-compose.yml` avec volumes partagés (SQLite, fichiers audio temporaires)
- [ ] `.env.example` complet

### Phase 1 — Backend : auth & utilisateurs
- [x] Modèle de données SQLite (users, jobs, whisper_models) — script d'init via `SQLModel.metadata.create_all` (pas de migrations Alembic pour l'instant, à ajouter si le schéma évolue en prod avec données existantes)
- [x] Endpoint login (JWT access + refresh token)
- [x] Endpoint refresh token (`/api/auth/refresh`)
- [x] Endpoint changement de mot de passe (utilisateur) avec politique de mot de passe minimale (8 caractères, au moins une lettre et un chiffre)
- [x] Endpoints CRUD utilisateurs (admin only) : création, activation/désactivation, réinitialisation de mot de passe, suppression
- [x] Création automatique du compte admin au premier démarrage depuis `.env`
- [x] Middleware de vérification des rôles (admin / user) via `require_admin`
- [x] Protection brute-force basique sur le login (5 tentatives échouées / 5 min par email)
- [x] Tests unitaires (pytest) : authentification et gestion des utilisateurs — 21 tests, voir `backend/tests/` et `backend/README.md`
- [ ] Migrations Alembic (à évaluer si le schéma doit évoluer sans perte de données en prod)
- [ ] Persistance des `app_settings` (limites taille/durée) en base plutôt qu'en mémoire — actuellement un TODO dans `routers/app_settings.py`

### Phase 2 — Backend : gestion des jobs de transcription
- [x] Endpoint upload fichier audio (vérification taille en streaming + durée exacte via `ffprobe`, limites lues depuis la base via `AppSettings`)
- [x] Création de job en base (statut `pending`), avec stockage du nom de fichier temporaire réel (`audio_tmp_filename`) pour une correspondance fiable job ↔ fichier
- [x] Endpoint statut d'un job (`GET /api/jobs/{id}`, polling frontend)
- [x] Endpoint récupération résultat + téléchargement (`GET /api/jobs/{id}/download`, `.vtt`)
- [x] Endpoint historique des transcriptions (par utilisateur ; vue globale pour un admin)
- [x] Endpoint suppression d'une transcription (propriétaire ou admin), avec nettoyage du `.vtt` et de l'audio temporaire résiduel le cas échéant
- [x] Endpoints admin : lister modèles + statut, déclencher téléchargement, supprimer un modèle, activer/désactiver, définir modèle par défaut *(réalisés dès la Phase 0, non retouchés ici)*
- [x] Endpoints admin : limites taille/durée de fichier — **persistées en base** (`AppSettings`, ligne singleton) au lieu d'une variable en mémoire comme en Phase 0
- [x] Worker mis à jour pour consommer `audio_tmp_filename` au lieu d'une convention de nommage fragile
- [x] Tests unitaires (pytest + fichiers audio générés via `ffmpeg`) : upload valide/invalide, formats non supportés, dépassement de taille/durée, permissions, téléchargement, suppression, paramètres admin — 16 tests supplémentaires (37 au total)
- [x] Post-traitement fin du texte (nettoyage espaces/ponctuation, majuscules) — réalisé en Phase 3, voir `worker/app/text_postprocess.py`

### Phase 3 — Worker
- [x] Boucle de polling séquentielle des jobs `pending` (un seul job traité à la fois) — réalisée dès la Phase 0/1, consolidée ici
- [x] Boucle/traitement des demandes de téléchargement de modèle (déclenchées depuis l'admin), avec mise à jour du statut en base (`downloading` → `downloaded` / `error`)
- [x] Suppression physique d'un modèle sur demande admin
- [x] Intégration faster-whisper (chargement dynamique du modèle sélectionné pour chaque job, un seul modèle en RAM à la fois)
- [x] Transcription en français (langue forcée `fr`, pas de détection auto)
- [x] Génération des segments horodatés + post-traitement texte (`worker/app/text_postprocess.py` : nettoyage espaces, espace avant ponctuation, majuscule initiale)
- [x] Génération du fichier `.vtt` final
- [x] Écriture résultat en base (chemin du `.vtt`) + passage statut `done`
- [x] Suppression du fichier audio source (succès ou erreur) — le `.vtt` est conservé
- [x] Gestion des erreurs (statut `error` + message)
- [x] **Reprise après crash** : au démarrage, tout job resté bloqué en `processing` (arrêt anormal du worker) est remis en `pending` si l'audio est encore présent, ou marqué `error` sinon (`recover_stale_processing_jobs`)
- [x] **Backoff progressif** sur erreurs consécutives dans la boucle principale (évite une boucle de crash agressive en cas de problème persistant, ex. base de données temporairement inaccessible)
- [x] Tests unitaires (pytest, sans dépendance à un vrai modèle faster-whisper via `monkeypatch`) : post-traitement texte, génération VTT, traitement de jobs (succès/erreur/audio manquant/ordre FIFO), reprise après crash — 25 tests, voir `worker/README.md`
- [ ] Tests couvrant le téléchargement/suppression réels de modèles (nécessiteraient un accès réseau HuggingFace ou un mock plus poussé — non fait pour rester rapide/léger)

### Phase 4 — Frontend
- [x] Page login, avec gestion des erreurs (identifiants invalides, compte désactivé, verrouillage brute-force)
- [x] Page changement de mot de passe (`/account`), accessible à tout utilisateur connecté
- [x] Page upload (glisser-déposer + sélection de fichier) + suivi de statut par **polling** (toutes les 4s tant qu'un job est `pending`/`processing`)
- [x] Page historique des transcriptions (fusionnée avec l'upload sur `/`) + téléchargement du `.vtt` + suppression (utilisateur propriétaire)
- [x] Espace admin : gestion des utilisateurs (créer, activer/désactiver, changer de rôle, réinitialiser mot de passe via modale, supprimer)
- [x] Espace admin : gestion des modèles Whisper (statut avec polling pendant le téléchargement, activer, définir par défaut, supprimer)
- [x] Espace admin : configuration taille/durée max de fichier
- [x] Rafraîchissement automatique du token JWT (intercepteur axios : retry transparent sur 401 via `/auth/refresh`, déconnexion si le refresh échoue)
- [x] Gestion des rôles côté frontend : navigation et routes admin masquées/protégées pour les utilisateurs non-admin (`RequireAuth`, `RequireAdmin`)
- [x] Identité visuelle dédiée (tokens de couleur/typographie, composant signature "forme d'onde" utilisé comme indicateur de traitement) plutôt qu'un habillage par défaut
- [x] Build de production vérifié (`npm run build` exécuté avec succès, 113 modules, aucune erreur)
- [ ] Vue globale admin des transcriptions de tous les utilisateurs (l'API le permet déjà via `GET /api/jobs` pour un admin, mais l'interface actuelle n'affiche que les jobs de l'utilisateur connecté — à ajouter si le besoin se confirme)
- [ ] Tests frontend (aucun framework de test JS mis en place à ce stade — à évaluer, ex. Vitest + Testing Library, si souhaité)

### Phase 5 — Reverse proxy & sécurisation
- [x] VirtualHost Apache HTTP → HTTPS (redirection 301, avec exception pour le challenge ACME de certbot en mode webroot)
- [x] VirtualHost HTTPS + Let's Encrypt (certbot) — configuration TLS "intermediate" (référence Mozilla SSL Config Generator), OCSP stapling
- [x] Configuration `ProxyPass` frontend (qui proxifie lui-même `/api` vers le backend en interne au réseau Docker — un seul service en aval pour Apache)
- [x] Headers de sécurité (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- [x] `LimitRequestBody` documenté et cohérent avec la taille max de fichier configurable (300 Mo par défaut, avec marge par rapport à la limite applicative de 200 Mo pour permettre un ajustement depuis l'admin sans reconfiguration infra) — même valeur alignée côté `frontend/nginx.conf` (`client_max_body_size`)
- [x] Conteneur `frontend` exposé uniquement sur `127.0.0.1` (`FRONTEND_HOST_PORT` dans `.env`), jamais directement sur Internet — seul Apache doit y accéder
- [x] Healthchecks Docker sur le backend (`/api/health`), avec `depends_on: condition: service_healthy` pour le worker et le frontend (évite les erreurs de démarrage en cascade)
- [x] Script `scripts/check-deployment.sh` : vérification rapide post-déploiement (frontend accessible, API backend accessible via le proxy, endpoint login répond correctement)
- [x] `docker-compose.yml` validé syntaxiquement (`python3 -c "import yaml; yaml.safe_load(...)"`) — **non testé avec un véritable `docker-compose up`**, Docker n'étant pas disponible dans l'environnement de développement utilisé pour générer ce projet ; à valider manuellement avant mise en production (voir section suivante)
- [x] README principal, `reverse-proxy/README.md` et `.env.example` mis à jour pour refléter l'état complet du projet et guider un déploiement de bout en bout

### Validation manuelle recommandée avant mise en production

Le projet n'a **pas pu être testé avec un `docker-compose up` réel** dans
l'environnement utilisé pour ce développement (Docker non disponible). Avant
un déploiement en production, il est recommandé de :
1. Lancer `docker-compose up -d --build` sur une machine avec Docker et
   vérifier que les 3 images se construisent sans erreur
2. Exécuter `./scripts/check-deployment.sh` une fois les conteneurs démarrés
3. Se connecter avec le compte admin, télécharger un modèle Whisper, et
   effectuer un envoi de fichier audio de test de bout en bout
4. Vérifier la configuration Apache avec `apache2ctl configtest` avant de
   recharger le service

### Phase 6 — Tests & finitions
- [ ] Tests unitaires backend (auth, jobs, permissions)
- [ ] Test de charge basique (upload + traitement d'un fichier volumineux)
- [ ] Vérification suppression effective des fichiers audio après traitement
- [ ] Documentation de déploiement (README : `.env`, `docker-compose up`, config Apache)

### Phase 7 — Suivi de progression
- [x] Progression du téléchargement des modèles : le worker passe par `huggingface_hub.snapshot_download` (mêmes repo/patterns que faster-whisper) avec une sous-classe tqdm qui écrit `whisper_models.download_progress` en base (throttle ~1s, session dédiée thread-safe, best-effort)
- [x] Taille des modèles : `disk_size_mb` calculé sur disque après téléchargement ; taille approximative affichée avant téléchargement (table statique côté frontend)
- [x] Progression des transcriptions : itération incrémentale du générateur de segments, `jobs.progress = segment.end / durée` commité avec throttle (≥2 points ou ≥2s), 100 au passage à done ; durée stockée à l'upload (`audio_duration_seconds`) en secours si `info.duration` indisponible
- [x] Migration légère : ALTER TABLE idempotents au démarrage backend/worker pour les 3 nouvelles colonnes (bases existantes)
- [x] Frontend : primitive `.progress-bar` (tokens.css), barre + % sur la page Modèles (polling 2s pendant le téléchargement), barre sous le badge de statut + « En cours · N% » sur le tableau de bord
- [x] Tests : backend 40 (dont 3 nouveaux sur les champs de progression), worker 32 (dont 7 nouveaux : progression transcription, état de téléchargement, throttle, migration)

### Phase 8 — Gestion des modèles côté utilisateur & export
- [x] Désactivation d'un modèle activé depuis le panneau admin (bouton « Désactiver ») ; le modèle **par défaut** ne peut pas être désactivé (400, comme pour la suppression : changer d'abord le défaut)
- [x] Choix du modèle à l'upload : `GET /api/models` (authentifié, non admin) liste les modèles téléchargés+activés ; `POST /api/jobs` accepte un champ `model` (validé téléchargé+activé, sinon 400 ; fallback modèle par défaut si absent) ; sélecteur dans la zone d'upload (affiché seulement si plusieurs modèles activés)
- [x] Export texte brut : `GET /api/jobs/{id}/download?format=vtt|txt` (défaut vtt) — conversion VTT→texte à la volée (un paragraphe par segment, sans horodatages, en-tête WEBVTT ignoré) ; menu déroulant « Télécharger ▾ » côté dashboard avec les deux formats
- [x] Tests backend : 49 au total (désactivation/default bloqué, endpoint public modèles, choix de modèle valide/inconnu/désactivé, formats txt/vtt/rejeté)

### Phase T — Traduction FR↔EN (fichiers texte → texte)

Fonctionnalité additionnelle : traduction FR↔EN de texte saisi manuellement ou
d'archives ZIP de fichiers techniques (JSON, HTML — extensions configurables
par l'admin), en conservant noms de fichiers et arborescence. Moteur :
CTranslate2 + modèles bilingues Helsinki-NLP OPUS-MT déjà convertis
(michaelfeil/ct2fast-opus-mt-fr-en / en-fr), gérés en téléchargement à la
demande comme les modèles Whisper.

**Phase T0 — Modèle de données & infrastructure**
- [x] Tables `translation_jobs`, `translation_models`, `translation_cache` (modèles SQLModel dupliqués backend/translation-worker comme pour Whisper)
- [x] Extension de `app_settings` : max_text_length_chars, preview_truncate_chars, max_archive_size_mb, max_archive_files_count, max_archive_uncompressed_mb, translatable_extensions (ALTER idempotents avec DEFAULT pour les bases existantes)
- [x] Service `translation-worker` dans docker-compose + volumes dédiés (translation_models_data, translation_tmp, translations_data) ; variables d'environnement dans `.env.example`

**Phase T1 — Backend : jobs de traduction (mode texte)**
- [x] `POST /api/translation/jobs` (validation direction + longueur max) ; modèle de la direction requis téléchargé+activé sinon 503
- [x] Statut/résultat avec aperçu tronqué côté API selon preview_truncate_chars (`result_preview` + `result_truncated`), texte complet au téléchargement (.txt)
- [x] Historique `GET /api/translation/jobs` + suppression (propriétaire/admin), même politique que les transcriptions
- [x] Endpoints admin `/api/admin/translation-models` (lister/télécharger/supprimer/activer par direction) + `GET /api/translation/models` public (directions actives)
- [x] Limites de traduction intégrées à `/api/admin/settings` (extensions normalisées, valeurs > 0)

**Phase T2 — Backend : jobs de traduction (mode archive)**
- [x] `POST /api/translation/jobs/archive` : extension .zip, taille streamée, puis vérifications AVANT traitement : archive lisible, nombre de fichiers, taille décompressée, fichiers chiffrés rejetés, zip-slip (chemins absolus / `..` / `\`) rejeté avec 400/413

**Phase T3 — Worker de traduction (translation-worker/)**
- [x] Boucle de polling séquentielle dédiée (même pattern que le worker Whisper : reprise après crash, backoff exponentiel plafonné)
- [x] CTranslate2 + tokenizer Marian (transformers), chargé à la demande selon la direction (snapshot huggingface_hub, fichiers autorisés filtrés)
- [x] Cache de traduction : lecture avant traduction, écriture après calcul uniquement (jamais sur un hit), clé sha256(direction + texte), textes dédupliqués par lot
- [x] Traducteur JSON (valeurs de chaînes uniquement, clés/nombres/booléens préservés) ; traducteur HTML (nœuds texte + attributs alt/title/placeholder/aria-label, exclusion script/style/pre/code, entités protégées par jetons pendant la traduction)
- [x] Copie brute des extensions hors translatable_extensions (comparaison insensible à la casse) ; reconstruction de l'archive strictement identique (noms, arborescence, répertoires vides)
- [x] Traitement « au mieux » : erreur par fichier → copie telle quelle + entrée report_json.error_details ; erreur bloquante (archive illisible, zip-slip à l'extraction, dépassement) → statut error + stopped_reason
- [x] Génération de report_json (total/traduits/copiés/erreurs) ; suppression de l'archive source et du répertoire d'extraction après traitement
- [x] Tests unitaires sans vrai modèle CTranslate2 (cache, traducteurs JSON/HTML, zip-slip, rapport d'erreurs, reprise, téléchargements simulés) — 26 tests

**Phase T4 — Frontend**
- [x] Écran « Traduction » (onglets texte manuel / archive ZIP), sélection du sens parmi les directions actives, aperçu tronqué + téléchargement complet, polling de statut, rapport d'archive (résumé + détails d'erreurs) affiché dans l'écran
- [x] Écran admin « Modèles de traduction » (même pattern que Modèles Whisper, par direction) ; écran « Limites » étendu aux paramètres de traduction ; navigation mise à jour

### Phase 9 — Identifiants, annulation, qualité de traduction
- [x] Identification par simple login (plus d'email) : colonne `user.email` renommée `login` (ALTER RENAME idempotent), validation `[a-zA-Z0-9_.-]{3,64}`, ADMIN_LOGIN dans .env (ADMIN_EMAIL lu en héritage ; le compte admin existant garde son identifiant d'origine)
- [x] Annulation des jobs (transcription + traduction) : colonne `cancel_requested`, statuts `cancelling`/`cancelled`, endpoint `POST .../cancel`, détection par les workers pendant le traitement (segment par segment côté Whisper, entre les lots / par fichier côté traduction), nettoyage des fichiers temporaires, bouton Annuler côté frontend
- [x] Moteur de traduction : passage d'OPUS-MT bilingues à **NLLB-200-distilled-600M** (CTranslate2 int8, modèle unique multilingue partagé par direction via jetons de langue fra_Latn/eng_Latn) — qualité nettement meilleure sur les idiomes ; tokenizer SentencePiece direct (transformers retiré des dépendances)
- [x] Découpe des textes longs par échelle de séparateurs (phrases → propositions `;:` → énumérations `,` → mots), jamais de tokenisation du texte entier (supprime l'avertissement « sequence length longer than maximum » et les coupures aléatoires)
- [x] Préservation de la mise en page : sauts de ligne, lignes vides et espaces en début/fin de ligne réinsérés tels quels autour des blocs traduits
- [x] Renommages UI : TransTooLing (marque/login/titre), menus Transcription / Traduction / Utilisateurs / Modèles / Paramètres, page Modèles fusionnée (section Whisper + section Traduction), service compose `transcription-worker`, logs [transcription-worker]

> Décisions notables du moteur NLLB : traduction **une phrase par morceau**
> (les modèles type NLLB perdent des phrases entières quand on leur fournit
> plusieurs phrases d'un coup), jetons `[src_lang] + pièces + </s>` avec la
> langue cible via `target_prefix` (convention CTranslate2), lot de phrases
> comme unité d'annulation. Le dépôt JustFrederik/nllb-200-distilled-600M-ct2-int8
> est sous licence **CC-BY-NC 4.0** (usage non commercial) : pour un usage
> commercial, remplacer par un autre modèle CT2 (la classe TranslationEngine
> est le seul point à adapter).

### Phase 10 — Traduction Markdown
- [x] `md` ajouté aux extensions traduisibles par défaut (migration de données : les lignes restées à l'ancien défaut passent à `json,html,htm,md`, les valeurs personnalisées sont préservées)
- [x] Traducteur Markdown dédié (`translation-worker/app/translators.py`) : titres, gras/italique/barré (récursifs, `__`/`_` avec frontières de mot pour épargner le snake_case), citations et listes (préfixes préservés, récursifs), séparateurs horizontaux et front matter verbatim
- [x] Jamais traduits : code inline, blocs de code clôturés (``` et ~~~), chemins et titres de liens, chemins d'images (seuls libellés/alt sont traduits), caractères échappés, autoliens et balises HTML
- [x] Espaces significatifs conservés (sauts de ligne durs Markdown, indentation) ; tableaux GFM : format, pipes et ligne d'alignement verbatim, contenu des cellules traduit (pipes échappés non découpés) ; 27 tests dédiés + archive de test incluant un .md

---

## 9. Fonctionnalités volontairement exclues de la V1 (pour référence)

- Détection automatique de la langue
- Rétention des fichiers audio après transcription
- Notification par email
- Diarisation (identification des locuteurs)

Ces fonctionnalités pourront être ajoutées ultérieurement si le besoin évolue.
