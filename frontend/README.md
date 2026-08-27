# Frontend — Interface web de transcription audio

Interface React (Vite), servie en production par Nginx (voir `Dockerfile` et
`nginx.conf`), qui proxifie `/api` vers le backend.

## Structure

```
src/
├── api/            # Wrappers axios par domaine (auth, jobs, users, ...)
├── components/      # Composants réutilisables (Layout, garde de route, badges, Waveform)
├── context/          # AuthContext (utilisateur courant, login/logout)
├── pages/            # Une page par route
└── styles/tokens.css # Système de design (couleurs, typographie, primitives)
```

## Pages

| Route | Accès | Contenu |
|---|---|---|
| `/login` | public | Connexion |
| `/` | authentifié | Upload + historique de ses transcriptions, polling de statut |
| `/account` | authentifié | Changement de mot de passe |
| `/admin/users` | admin | Gestion des utilisateurs |
| `/admin/models` | admin | Gestion des modèles Whisper (téléchargement à la demande) |
| `/admin/settings` | admin | Limites taille/durée de fichier |

## Développement local

```bash
npm install
npm run dev
```

Par défaut, l'app appelle `/api` (voir `src/api/client.js`). En dev local
sans reverse proxy, définir `VITE_API_BASE_URL` (ex: `http://localhost:8000/api`)
dans un fichier `.env` local ou lancer via docker-compose pour bénéficier du
proxy Nginx interne.

## Build de production

```bash
npm run build
```

Génère `dist/`, servi ensuite par le `Dockerfile` (étape Nginx).

## Authentification

- Le token d'accès (courte durée) et le refresh token sont stockés dans
  `localStorage`.
- `src/api/client.js` intercepte automatiquement les réponses `401` : il
  tente un rafraîchissement via `/api/auth/refresh`, rejoue la requête
  d'origine, et déconnecte l'utilisateur (redirection vers `/login`) si le
  rafraîchissement échoue.

## Points non couverts à ce stade

- Aucun test automatisé JS (à évaluer : Vitest + React Testing Library).
- Pas de vue admin listant les transcriptions de tous les utilisateurs
  (l'API le permet déjà pour un rôle admin, l'écran reste à ajouter).
