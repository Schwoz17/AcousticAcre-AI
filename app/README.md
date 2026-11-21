# AcousticAcre AI — Frontend

A farmer-first React + TypeScript + Vite frontend for AcousticAcre AI, an agricultural assistant concept for crop-photo assessments and farm-machine sound assessments. This repository is **frontend-only** and is prepared for integration with the team's backend and AI/ML services.

## Included

- Public landing page and responsive navigation.
- Sign up, sign in and forgot-password screens (local demo flow only).
- Farmer onboarding with expanded crop choices, location, farm size, experience and language.
- Protected farmer workspace routes, profile editing and settings.
- Dashboard, crop diagnosis, machine diagnosis, history and help pages.
- Searchable crop catalogue, image type/size checks and local image preview.
- Machine sound recording and audio-file upload with local playback.
- Local prototype history and profile storage.
- PWA manifest and an updated service worker with safer navigation fallback.
- API client foundation and backend/AI-ML integration notes.

## Run locally

Requirements: Node.js 18+ and npm.

```bash
npm install
npm run dev
```

For a production build and local preview:

```bash
npm run build
npm run preview
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

## Important prototype boundaries

This is a frontend prototype, not a production-connected service:

- Sign-up/sign-in create a local demo session. Passwords are not stored or verified by the frontend.
- The route guard is for the demo user experience only. It is not a security boundary; the backend must authorize every protected API request.
- Forgot password does not send email until the backend endpoint is connected.
- Profile, preferences and demo history are stored in this browser's local storage.
- Crop photos and machine audio can be selected/previewed locally. They are not uploaded to a diagnosis server.
- `src/services/diagnosis.ts` returns an explicitly labelled demo result. It does not run AI inference. Never use demo results to make treatment, pesticide, repair or machine-safety decisions.
- Language selection stores a preference; complete translations and reviewed voice packs are not included.

## Backend and AI/ML integration

Read [`FRONTEND_INTEGRATION_NOTES.md`](./FRONTEND_INTEGRATION_NOTES.md) before wiring services.

Main integration points:

- `src/services/profile.ts` — replace local demo session/profile behavior with the backend authentication and farmer-profile contract.
- `src/services/diagnosis.ts` — replace the demo adapter with crop-image and machine-audio API calls.
- `src/services/storage.ts` — replace or synchronize local history with the backend history service.
- `src/services/apiClient.ts` — shared HTTP helper foundation.
- `src/types/index.ts` — align shared response types with the agreed API schema.

When the backend engineer provides the API base URL, place it in `.env` using the key shown in `.env.example`:

```env
VITE_API_BASE_URL=https://your-api-host.example/api
```

`VITE_*` values are included in the browser bundle. Never put secrets, private keys or database credentials in them.

## Release checklist

1. Run `npm install` and `npm run build`.
2. Test signup, sign-in, onboarding, sign-out and protected route redirects.
3. Test profile edits and crop selections.
4. Test crop image upload validation on desktop and a real mobile device.
5. Test microphone permissions, recording, audio upload and playback.
6. Test every route at desktop, tablet and mobile widths.
7. Verify demo labels remain visible until the real AI/ML service is connected.
8. Test the production PWA over HTTPS and validate offline behavior.
9. Review API contracts, privacy, security and translations with the engineering team before public launch.
