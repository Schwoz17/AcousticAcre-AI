# AcousticAcre AI

**Diagnoses crops and farm machines, then speaks the answer in the farmer’s own language — offline on a smartphone, or on any basic phone.**

Team Nexora · Sandbox Africa Hackathon 2026 · AgriTech & Food Security

| Channel | Who it is for | How it works |
|---|---|---|
| **Offline web app** (`app/`) | Farmers or agents with a smartphone | Leaf photo or 5 s of pump sound → AI runs **on the phone** → result spoken in Hausa or English. Works in Airplane Mode after the first visit. Nothing is uploaded. |
| **USSD · voice · SMS** (`gateway/`) | Farmers with a basic phone | Dial `*384*4074#` (Africa’s Talking sandbox) → yes/no questions → diagnosis + SMS summary, in English or Hausa. |
| **Agent mode** | Extension officers, mechanics | Scan for a farmer, then send the result by SMS or WhatsApp. When the AI is unsure, “Ask an expert” sends the photo or sound to a human. |

---

## Results (held-out data only)

| What | Data | Result | How to describe it |
|---|---|---|---|
| Cassava diseases (5 classes) | 1,118 field photos never used in training | **84.3% accuracy**; **91.6%** accurate on the 78% of photos where it is confident | Field result: quotable |
| Maize, tomato (8 field classes) | 320 PlantDoc real-scene photos never used in training (near-duplicates removed) | **72.5% accuracy** (was 21.9% with the lab-only model); **88.7%** accurate on the 58% of photos where it is confident | Field result: quotable, small test set |
| Maize, tomato | PlantVillage lab photos | 98.6% (lab) | **Not** field accuracy |
| Pump sound (healthy vs faulty) | 10 MIMII factory pumps; each pump scored by a model that never heard it | **0.57 macro-F1** (chance 0.34). On 6 pumps added later: 0.50 before, **0.55** after retraining | **Experimental.** Factory pumps, not farm pumps; CC BY-NC-SA data |
| Browser vs training sound processing | Parity test | within 2.5 × 10⁻¹² dB | The phone hears exactly what the model was trained on |

When the model is not confident it says **“not sure”** and points to an extension officer or mechanic. It never gives pesticide doses.

---

## Repository

```
app/        React + TypeScript web app (PWA). On-device AI in src/ai/, models in public/models/, Hausa voice in public/clips/
gateway/    FastAPI service for Africa's Talking USSD, voice and SMS (Python). 42 tests
content/    Diagnoses, question trees, phrase packs (en, ha, yo, sw, fr), voice clips
ml/         Training and evaluation: crop (EfficientNet-Lite0, INT8 ONNX), machine sound (log-Mel + classifier)
tools/      Pack builder (.aapack with SHA-256), dataset importers, voice-clip generator (YarnGPT)
web-dsp/    Reference TypeScript sound/photo processing with Python parity tests
```

## Run the app

```bash
cd app
npm install                 # also copies ONNX Runtime into public/ort
npm run build && npm run preview -- --host
```
Open the printed address. For a phone, host it over HTTPS (e.g. drag `app/dist` onto Netlify Drop); camera, microphone and offline mode need HTTPS.

Useful pages: **Settings → AI model packs** (install a `.aapack` from a file, offline; every file is checksum-verified) and **Settings → Speed test** (50 runs per model; median and 95th percentile).

## Run the gateway

```bash
cd gateway
python -m venv .venv && source .venv/bin/activate      # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env        # fill in your own keys — never commit .env
pytest -q
uvicorn app.main:app --port 8000
ngrok http 8000             # point the Africa's Talking USSD/voice callbacks at the ngrok URL
```
`.env` options for the demo: `ALLOW_UNREVIEWED=1` and `DEMO_LANGS=en,ha` (show only English and the Hausa beta).

## Train or re-evaluate (Google Colab)

| Notebook | What it does |
|---|---|
| `AcousticAcre_Colab.ipynb` | Trains the original crop and machine models and builds both packs |
| `AcousticAcre_FieldData.ipynb` | Scores the crop model on real-scene maize/tomato photos (PlantDoc), retrains with them, scores again |
| `AcousticAcre_MorePumps.ipynb` | Adds 6 more real pumps (MIMII, DCASE 2020/2021) and compares before/after on pumps the models never heard |

Upload a clean copy of the repo with `git archive --format=zip -o acousticacre.zip HEAD` (no secrets, no virtual environments).

---

## Privacy

- Photos and sounds are analysed on the phone and never uploaded. Scan history stays on the phone and can be deleted in Settings.
- The gateway stores phone numbers only as an HMAC hash, with the answers, for 30 days. The first USSD screen says so in every offered language.
- Secrets live in `gateway/.env`, which is never committed.

## Honest limits (and what comes next)

- **Hausa** text and voice are AI-drafted (YarnGPT voice) and **pending native-speaker review**. Yoruba, Swahili and French are drafted but switched off.
- **Machine sound** covers irrigation pumps only and is experimental; generators and local Nigerian recordings are the next pack.
- **USSD and voice** run in the Africa’s Talking sandbox; a production code needs provider approval.
- Not yet done: a formal usability test with low-literacy farmers, and a real phone call through the hotline.

## Data and licences

| Data | Licence | Note |
|---|---|---|
| Cassava field photos (iCassava 2019, TensorFlow Datasets) | see dataset page | |
| PlantVillage (lab photos) | see dataset page | |
| PlantDoc (real-scene photos) | CC BY-SA 4.0 | |
| MIMII / DCASE pump recordings | **CC BY-NC-SA 4.0** | **Non-commercial.** A paid product needs our own recordings or the owners’ permission |

## Team Nexora

- **Muiz Adeyemi** — AI/ML and backend: models, on-device engine, USSD/voice/SMS gateway, Hausa voice pipeline
- **Abdulrahman Oladele** — Frontend: app design, screens, scan flow, offline web app
- **Abdulrahman Adeoye** — assisted with the backend
