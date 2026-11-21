# On-device AI — how it is wired (v0.3.0)

Everything below runs **in the browser on the phone**. No API key, no server call, no internet
needed once the app has been opened once.

## Run it

```bash
npm install          # also copies ONNX Runtime into public/ort/ (postinstall)
npm run dev -- --host # test on a phone on the same Wi-Fi (camera/mic need HTTPS or localhost; see below)
npm run build && npm run preview -- --host   # the service worker (offline mode) only runs in this build
```

Offline test: open the preview build once while online, wait about 10 seconds so the models
download into the cache, then turn on Airplane Mode and reload. Both scans should still work.

Phone camera and microphone need a secure origin. The easiest way is to put an ngrok tunnel in
front of the preview port (`ngrok http 4173`) and open the https link on the phone.

## Files

| Path | What it is |
|---|---|
| `src/ai/engine.ts` | **The only interface the UI uses**: `scanPhoto(file, crop, lang)`, `scanAudio(blob, machine, lang)`, `preload(domain)`. It returns an `AiResult`. Swapping or upgrading a model never touches the pages. |
| `src/ai/logmel.ts` | Audio features (log-Mel), matching the Python training code to 2.5e-12 dB |
| `src/ai/image.ts` | Photo quality gate (dark / bright / blurry / no leaf) and tensor conversion |
| `src/ai/speech.ts` | Speaks a result: pre-recorded clips in `public/clips/<lang>/<id>.mp3`, otherwise the phone's built-in voice |
| `src/services/diagnosis.ts` | Turns an `AiResult` into a saved history record |
| `src/components/ResultCard.tsx` | Result display: confidence, heat-map overlay, steps, Listen button |
| `public/models/crop/` | EfficientNet-Lite0 INT8, 3.9 MB, 14 classes (cassava, maize, tomato) |
| `public/models/machine/` | Experimental pump/engine sound model |
| `public/content/` | Diagnoses and phrase packs (en, ha). Hausa is AI-drafted and labelled beta. |

## Result kinds

`diagnosis` · `uncertain` (the model is not confident enough, so we say "not sure" and refer the
user to an extension officer or mechanic) · `retake` (bad photo or recording, with the reason) ·
`unsupported` (crop or machine not covered yet) · `error`.

## Voice clips

Put the generated MP3s at `public/clips/ha/<id>.mp3` (and `en/` if you have them), then add the
folder names to `OPTIONAL` in `public/sw.js` if they should be available offline. Any clip that
is missing falls back to the phone's own voice, so nothing breaks.

## Verified

- Real models, run in headless Chromium, on 10 cases: leaf photo, dark photo, wall photo,
  unsupported crop, pump hum at 16 kHz and at 44.1 kHz, silence, and unsupported machine. Every
  case produced the expected kind of result.
- The browser's preprocessing gave the same top class as the Python training pipeline. For the
  crop image the tensors correlate at 0.999. For machine sound the average probability was 0.570
  in the browser against 0.563 in Python.
- Not verifiable here (no internet): the exact file names inside the `onnxruntime-web@1.20.1`
  package. If `npm install` prints a `[copy-ort]` error, paste it to Claude.
