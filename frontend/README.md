# Frontend — web UI

React (Vite) interface, served in production by Nginx (see `Dockerfile` and
`nginx.conf`), which proxies `/api` to the backend.

The user interface is available in English (default) and French
(i18next, `src/i18n/`), with an EN/FR switcher in the header and on the
login page. The choice is persisted in `localStorage`. Note: error
messages returned by the backend API remain in French.

## Structure

```
src/
├── api/            # Axios wrappers per domain (auth, jobs, users, ...)
├── assets/fonts/    # Embedded woff2 fonts (latin + latin-ext subsets)
├── components/      # Reusable components (Layout, route guards, badges, Waveform)
├── context/         # AuthContext (current user, login/logout)
├── pages/           # One page per route
└── styles/          # Design system (fonts.css, tokens.css: colors, typography, primitives)
```

## Pages

| Route | Access | Content |
|---|---|---|
| `/login` | public | Login |
| `/` | authenticated | Upload + own transcription history, status polling |
| `/translation` | authenticated | Translation (manual text / ZIP archive), history, polling |
| `/account` | authenticated | Password change |
| `/admin/users` | admin | User management |
| `/admin/models` | admin | Model management (Whisper + translation, on-demand download) |
| `/admin/settings` | admin | Size/duration limits + translation settings |

## Local development

```bash
npm install
npm run dev
```

By default, the app calls `/api` (see `src/api/client.js`). In local dev
without a reverse proxy, set `VITE_API_BASE_URL` (e.g.
`http://localhost:8000/api`) in a local `.env` file, or run through
docker-compose to benefit from the internal Nginx proxy.

## Production build

```bash
npm run build
```

Generates `dist/`, then served by the `Dockerfile` (Nginx stage).

## Authentication

- The access token (short-lived) and the refresh token are stored in
  `localStorage`.
- `src/api/client.js` automatically intercepts `401` responses: it attempts
  a refresh via `/api/auth/refresh`, replays the original request, and logs
  the user out (redirect to `/login`) if the refresh fails.

## Not covered at this stage

- No automated JS tests (to evaluate: Vitest + React Testing Library).
- No admin view listing all users' transcriptions (the API already allows
  it for an admin role; the screen remains to be added).
