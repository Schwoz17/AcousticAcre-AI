# AcousticAcre AI — backend + ML (20 Nov 2026, v0.2)

## What's here

| Part | Files | Status |
|---|---|---|
| **Gateway**: USSD, voice, SMS, agent mode | `gateway/` | 36 tests pass (engine). HTTP tests run after `pip install` |
| **Question trees**: cassava, maize, tomato | `content/trees/` | 15 diseases + "Not sure"; every path tested. **Drafts: agronomist review needed** |
| **Languages** | `content/phrases/` | English live. French, Swahili, Hausa, Yoruba = **AI drafts, hidden** until a native speaker signs off (`tools/review_sheet.py`) |
| **Machine-sound model** | `ml/train/audio_baseline.py`, `ml/export/` | Pipeline tested on synthetic audio. Train on MIMII pumps in Colab |
| **Crop photo model** | `ml/train/crop_prepare.py`, `crop_train.py` | Written for Colab GPU, **not yet run** (no GPU here) |
| **Browser code for the frontend** | `web-dsp/logmel.ts`, `web-dsp/image.ts` | Spectrogram parity with Python 2.5e-12 dB; photo checks, tensor and highlight tested |
| **Packs** | `tools/pack_builder.py` | `.aapack` for machine and crop, SHA-256 verified |
| **Colab notebook** | `AcousticAcre_Colab.ipynb` | Trains both models and builds both packs |

---

## 1. Train the models (Colab, ~1 hour)

Open `AcousticAcre_Colab.ipynb` in Colab (File → Upload notebook), set **Runtime → T4 GPU**, upload `acousticacre.zip`, and run all cells. You get:
- `machine_report.json`, `crop_report.json` (send back for the results slide)
- `machine-core-1-0.1.0.aapack`, `crop-core-1-0.1.0.aapack` (for the frontend)

**What each number means (say this out loud):**
| Result | Data | How to describe it |
|---|---|---|
| Machine macro-F1 | MIMII industrial pumps, 4 pumps, leave-one-pump-out | "on real pump recordings, pumps the model never heard; factory data, not farm" |
| Cassava accuracy (`cassava_field`) | Field photos from Uganda, official test split | Field-condition result: quotable |
| Maize/tomato (`plantvillage_lab`) | Lab photos, plain background | **Not** field accuracy. Say "works on lab images; field validation next" |

---

## 2. Run the gateway (≈45 min)

```bash
cd gateway
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill AT_API_KEY, HMAC_SECRET, CALLBACK_TOKEN, AGENT_KEYS
set -a; source .env; set +a
pytest -q
uvicorn app.main:app --port 8000
ngrok http 8000               # second terminal; put the URL in PUBLIC_BASE_URL and restart uvicorn
```
Africa's Talking sandbox: USSD channel callback `https://<ngrok>/ussd?token=<CALLBACK_TOKEN>`; voice callback `https://<ngrok>/voice?token=<CALLBACK_TOKEN>`; test in the simulator.

**USSD paths** (English only = no language menu; crop 1 cassava, 2 maize, 3 tomato):
`1*1*1` cassava mosaic · `2*1` fall armyworm · `3*1` bacterial wilt · `3*2*2*2*1` late blight.
With more than one reviewed language, a language menu comes first.

**Endpoints:** `/ussd`, `/voice`, `/sms/inbound`, `/agent/send`, `/healthz`, `/stats`, `/clips/...`

### Agent mode (FR-10)
```bash
curl -X POST https://<gateway>/agent/send -H "X-Agent-Key: <one of AGENT_KEYS>" \
     -H "Content-Type: application/json" \
     -d '{"farmer_phone":"08031234567","lang":"en","diagnosis_id":"machine_fault"}'
```
Accepts local Nigerian numbers (`0803…`), falls back to English if the language isn't installed, and rejects unknown diagnosis IDs. The app calls this after a scan when the agent has signal. Set `ALLOWED_ORIGINS` to the PWA's address.

---

## 3. Frontend hookup (for the frontend dev)

**Machine scan:** record 5 s → `resampleTo16k` → `quality()` → `logmel()` → `[1,1,64,309]` → ONNX `logits` → `decide()`.
**Photo scan:** `imageFromFile` → `resizeAndCenterCrop(img,256,224)` → `photoQuality()` → `toTensor(crop, manifest.input.mean, manifest.input.std)` → ONNX `logits` + `cam` → `decide()` → `camOverlay(cam, K, 7, 7, index)`.
- Retake messages are phrase IDs `retake_<reason>` in every language pack.
- Label → `labels.json[i].diagnosis_id` → phrase pack `diagnoses[id].name` and `steps`.
- Use `manifest.temperature` and `manifest.thresholds` from each pack; never hard-code them.
- Checks: `node web-dsp/parity.test.ts` and `node web-dsp/image.test.ts`.

---

## 4. Languages

```bash
python tools/review_sheet.py export ha            # review_ha.csv -> reviewer fills "corrected"
python tools/review_sheet.py import ha review_ha.csv --name "Reviewer Name" --role "farmer, native speaker"
```
Only `reviewed: true` packs ship. `ALLOW_UNREVIEWED=1` shows drafts for local testing only, **never in the demo**.
Hausa/Yoruba letters make SMS use 67-character segments, so SMS there can use up to 3 segments (higher cost) [Verify with AT].
USSD screens with Yoruba tone marks may be shortened by some networks [Verify on the simulator].

---

## Changes from the spec
- **Wind check** also needs gusty low-frequency energy. The spec rule alone rejects real generators (50 Hz hum).
- **Audio model:** a linear model on spectrogram statistics (small data), same input/output as the planned CNN.
- **Machine labels:** healthy vs. faulty only.
- **Crop classes** follow the public data: cassava ×5 (field), maize ×4 and tomato ×5 (lab), including "tomato leaf problem, type unclear" for PlantVillage diseases we don't give advice for.
- **Fall armyworm, maize streak, bacterial wilt, Tuta:** question tree only (no public photo set wired in).
- **Callback auth:** `?token=` on callback URLs (AT callbacks aren't signed).

## Still to fill / verify
`[help number]` and reviewer fields in `content/phrases/en.json` · `OFFICER_NUMBER` · agronomist review of all three trees and the advice · AT voice XML details and `<Play>` audio formats · SMS cost per segment.
