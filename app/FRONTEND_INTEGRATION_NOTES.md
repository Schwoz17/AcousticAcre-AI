# AcousticAcre AI — Frontend hand-off notes

This repository is the React + Vite + TypeScript frontend. The backend and AI/ML engineers own secure authentication, persistence, file storage and model inference. No backend endpoints or model behaviour are assumed by this frontend.

## Run locally

```bash
npm install
npm run dev
```

Create a production build with `npm run build`, then test it using `npm run preview`.

## Current prototype behaviour

- Sign-up/sign-in create a local demo session so the screens and protected workspace can be demonstrated.
- No password is stored by the frontend prototype and no real account verification or password reset email is performed.
- Farmer profile, preferences and demo history are stored in this browser's local storage.
- Crop photo and machine audio can be selected/previewed locally; the current diagnosis adapter returns an explicitly labelled demo result.
- Do not use demo outputs for crop treatment, pesticide choice, machine repair or safety decisions.

## Frontend integration points

| Capability | Current frontend location | Integration owner |
|---|---|---|
| Sign-up, sign-in, sign-out, password reset | `src/services/profile.ts` (prototype adapter) + `src/pages/Auth.tsx` | Backend |
| Farmer profile | `src/services/profile.ts` + `src/pages/Onboarding.tsx` + `src/pages/Profile.tsx` | Backend |
| Crop image assessment | `src/services/diagnosis.ts` + `src/pages/CropDiagnosis.tsx` | AI/ML + Backend |
| Machine audio assessment | `src/services/diagnosis.ts` + `src/pages/MachineDiagnosis.tsx` | AI/ML + Backend |
| Assessment history | `src/services/storage.ts` + `src/pages/History.tsx` | Backend |
| Shared HTTP helper | `src/services/apiClient.ts` | Frontend/backend agreement |
| Shared data contracts | `src/types/index.ts` | Team agreement |

## API decisions required before integration

Agree these with the backend and AI/ML engineers before replacing the demo adapters:

1. API base URL for local, staging and production environments.
2. Authentication method (prefer secure, HttpOnly cookies where supported), refresh and logout semantics.
3. Request content types and multipart field names for image/audio uploads, including size and format limits.
4. Machine types and supported crop catalogue, including unsupported/uncertain outcomes.
5. Exact diagnosis response schema: label, confidence scale, uncertainty, severity, advice, warnings and model version.
6. History pagination, ownership, deletion and timestamps/time zones.
7. Standard error response and rate-limit format.

`VITE_*` variables are public browser-bundle configuration. Never place secrets, API private keys or database credentials in them.

## Important security note

The local demo session is only a navigation prototype. It is not authentication and must be replaced by the backend's real session mechanism before public launch. The frontend route guard improves the demo flow but is not a security boundary; the backend must authorize every protected API request.
