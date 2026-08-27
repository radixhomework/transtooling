# Transcription Audio (français) — Self-hosted

Application self-hosted de transcription audio en français, basée sur
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). Aucune donnée
n'est envoyée vers un service tiers (OpenAI ou autre) : tout le traitement
est effectué localement.

Voir `CLAUDE.md` pour l'architecture détaillée et le suivi du plan de
développement (phases 0 à 5, toutes complétées).

## Fonctionnalités

- Transcription audio → texte horodaté (`.vtt`), en français uniquement
- Authentification par identifiant simple (JWT access + refresh token),
  avec compte admin créé automatiquement au premier démarrage
- Gestion des utilisateurs (créer, activer/désactiver, changer de rôle,
  réinitialiser un mot de passe, supprimer) depuis l'interface admin
- Changement de mot de passe en libre-service pour tout utilisateur
- Téléchargement/suppression des modèles faster-whisper **à la demande**
  depuis le panneau admin (tiny → large-v3), avec sélection du modèle par
  défaut, activation/désactivation, barre de progression du téléchargement
  et taille des modèles (approximative avant, réelle sur disque après)
- Annulation d'une transcription ou d'une traduction en cours
- Suivi de l'avancement des transcriptions en pourcentage (calculé sur la
  durée de l'audio, rafraîchi pendant le traitement)
- Choix du modèle de transcription à l'envoi (parmi les modèles activés ;
  modèle par défaut sinon)
- Téléchargement des transcriptions en `.vtt` horodaté ou en `.txt` brut
  (menu de choix du format)
- **Traduction FR↔EN** : texte saisi manuellement ou archives ZIP de fichiers
  techniques (JSON, HTML — extensions configurables par l'admin), noms et
  arborescence conservés, traduction 100 % locale via CTranslate2 + modèles
  OPUS-MT bilingues, avec cache des traductions et rapport de traitement
  (traduits / copiés / erreurs par fichier)
- Limites de taille et de durée de fichier configurables depuis l'admin
- Traitement séquentiel (un job à la fois), avec reprise automatique après
  un crash du worker
- Suppression systématique de l'audio source après traitement — seule la
  transcription `.vtt` est conservée (suppression manuelle possible par le
  propriétaire ou un admin)

## Démarrage rapide (développement / test local)

```bash
cp .env.example .env
# éditer .env : ADMIN_EMAIL, ADMIN_PASSWORD, JWT_SECRET au minimum

docker-compose up -d --build
```

- Frontend : http://localhost:8080 (port configurable via `FRONTEND_HOST_PORT`
  dans `.env`, exposé sur `127.0.0.1` uniquement)
- L'API backend n'est pas exposée directement sur l'hôte ; elle est accessible
  via le frontend sur `/api` (proxy Nginx interne)

Une fois les conteneurs démarrés, vérifier rapidement l'état des services :

```bash
./scripts/check-deployment.sh
```

**Premier démarrage** : connectez-vous avec le compte admin défini dans
`.env`, puis rendez-vous dans **Modèles** pour télécharger au moins un
modèle Whisper (aucun n'est téléchargé par défaut) et le définir comme
modèle par défaut. Sans cela, l'upload de fichiers échouera avec une erreur
explicite. Pour la traduction, téléchargez de même au moins une direction
(FR→EN et/ou EN→FR) dans **Modèles traduction**.

## Déploiement en production

En production, **ne pas exposer directement** le port du conteneur frontend
sur Internet. Le `docker-compose.yml` fourni le lie déjà à `127.0.0.1`
uniquement. Utiliser le reverse proxy Apache fourni dans `reverse-proxy/`
pour exposer l'application en HTTPS — voir `reverse-proxy/README.md` pour
les instructions complètes (modules Apache, certificat Let's Encrypt,
headers de sécurité, alignement des limites de taille de fichier).

## Structure du projet

```
.
├── backend/           # API FastAPI (auth, utilisateurs, jobs, modèles) — voir backend/README.md
├── worker/             # Worker de transcription (faster-whisper) — voir worker/README.md
├── translation-worker/ # Worker de traduction FR↔EN (CTranslate2 + OPUS-MT)
├── frontend/           # Interface web (React + Vite, servie par Nginx) — voir frontend/README.md
├── reverse-proxy/      # Configuration Apache HTTPS — voir reverse-proxy/README.md
├── scripts/            # Scripts utilitaires (vérification de déploiement)
├── docker-compose.yml
├── .env.example
└── CLAUDE.md            # Architecture détaillée + suivi du plan de développement
```

## Tests

- Backend : 69 tests (`cd backend && pytest -v`) — voir `backend/README.md`
- Worker : 33 tests, sans dépendance à un vrai modèle Whisper téléchargé
  (`cd worker && pytest -v`) — voir `worker/README.md`
- Translation worker : 26 tests, sans dépendance à un vrai modèle CTranslate2
  (`cd translation-worker && pytest -v`)
- Frontend : build de production vérifié (`cd frontend && npm run build`) ;
  pas de tests automatisés JS à ce stade

## Sécurité — points d'attention avant mise en production

- Changer impérativement `JWT_SECRET`, `ADMIN_PASSWORD` dans `.env` avant
  tout déploiement (les valeurs par défaut ne sont là que pour le
  développement local)
- Changer le mot de passe admin depuis l'application après le premier
  démarrage
- S'assurer que les limites de taille (`LimitRequestBody` Apache,
  `client_max_body_size` Nginx, limite admin dans l'application) restent
  cohérentes entre elles après toute modification
- Le fichier `.env` contient des secrets : ne jamais le committer (déjà
  exclu via `.gitignore`)
