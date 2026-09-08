# Frontend — web UI

React (Vite) interface, served in production by Nginx (see `Dockerfile` and
`nginx.conf`), which proxies `/api` to the backend.

The user interface is available in English (default) and French
(i18next, `src/i18n/`), with an EN/FR switcher in the header and on the
login page. The choice is persisted in `localStorage`. Note: error
messages returned by the backend API remain in French.

## Structure

The frontend follows MVVM:

- **Model** — `src/models/`: API clients (axios wrappers) per domain; the
  data and the access to it.
- **ViewModel** — `src/viewmodels/`: framework-independent state + behavior
  per feature (`useTranscriptionViewModel`, `useTranslationViewModel`,
  `useModelsAdminViewModel`, ...), plus `AuthContext` for session state.
  Views bind to viewmodels through hooks; all business logic lives here.
- **View** — `src/views/`: `pages/` (one per route) and `components/`
  (Layout, route guards, badges, Waveform). Rendering only.

```
src/
├── models/          # API clients per domain (auth, jobs, users, ...)
├── viewmodels/      # Hooks holding state + actions; AuthContext
├── views/
│   ├── pages/       # One page per route
│   └── components/  # Reusable components
├── assets/fonts/    # Embedded woff2 fonts (latin + latin-ext subsets)
├── i18n/            # EN/FR translations
└── styles/          # Design system (fonts.css, tokens.css)
```

## Pages

| Route | Access | Content |
|---|---|---|
| `/login` | public | Login |
| `/` | authenticated | Upload + own transcription history, status polling |
| `/translation` | authenticated | Translation (manual text / ZIP archive), history, polling |
| `/account` | authenticated | Password change |
| `/admin` | admin | Administration: tabs for Users, Models (Whisper + translation, on-demand download) and Settings (size/duration limits + translation settings) |

## Local development

```bash
npm install
npm run dev
```

## Testing

Unit tests run with Vitest + Testing Library (jsdom):

```bash
npm test          # single run
npm run test:watch
```

The tests target the ViewModel layer (`src/viewmodels/`) and the
`AuthContext`: each suite mocks the API modules in `src/models/` at the
module boundary, so no backend is needed. i18n is stubbed globally in
`src/test/setup.js` (keys are returned as-is, with a stable `t` identity).

By default, the app calls `/api` (see `src/models/client.js`). In local dev
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
- `src/models/client.js` automatically intercepts `401` responses: it attempts
  a refresh via `/api/auth/refresh`, replays the original request, and logs
  the user out (redirect to `/login`) if the refresh fails.

## Not covered at this stage

- No automated JS tests (to evaluate: Vitest + React Testing Library).
- No admin view listing all users' transcriptions (the API already allows
  it for an admin role; the screen remains to be added).
