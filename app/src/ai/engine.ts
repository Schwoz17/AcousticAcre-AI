/**
 * AcousticAcre on-device AI engine. Everything runs in the browser; nothing is uploaded.
 *
 * Screens call only:
 *   scanPhoto(file, cropName)      -> AiResult
 *   scanAudio(blob, machineKind)   -> AiResult
 *   phrasesFor(uiLanguage)         -> phrase pack (names, steps, UI strings)
 *
 * Models, labels and thresholds come from /models/<pack>/manifest.json, so a new model
 * can be dropped in without touching the UI (the frontend never depends on the framework).
 * ONNX Runtime Web is loaded as a plain script from /ort/ (see scripts/copy-ort.mjs).
 */
import { logmel, quality, decide, type DspConstants, type Thresholds } from './logmel';
import { toTensor, photoQuality, camOverlay, type RGBA } from './image';
import { createSession, type Feed, type Session } from './runtime';
import { packBase } from './packs';

// ------------------------------------------------------------------ types ---
export type AiKind = 'diagnosis' | 'uncertain' | 'retake' | 'unsupported' | 'error';

export interface AiResult {
  kind: AiKind;
  domain: 'crop' | 'machine';
  diagnosisId?: string;        // e.g. cassava_mosaic, machine_fault
  name: string;                // in the chosen language (falls back to English)
  steps: string[];
  confidence: number;          // 0..1 (calibrated top-1 probability)
  reason?: string;             // retake / unsupported / error message
  overlay?: string;            // data URL: where the model looked (crop only)
  lang: string;                // language code actually used
  model: string;               // pack id + version
  clipIds: string[];           // voice clip ids for speaking the result
  ms?: number;                 // time from scan start to result, on this device
  photos?: number;             // how many photos were combined (crop)
  backend?: 'worker' | 'main'; // where the model ran
}

interface Manifest {
  pack_id: string; version: string; model: string; labels: string;
  temperature: number; thresholds: Thresholds;
  input: { name: string; mean?: number[]; std?: number[]; resize_short_side?: number; size?: number[] };
  output: { name: string; cam?: string };
}
interface Label { index: number; label: string; diagnosis_id: string }
export interface Phrases {
  lang: string; lang_name: string; reviewed: boolean;
  ui: Record<string, string>;
  crops: Record<string, string>;
  diagnoses: Record<string, { name: string }>;
  steps: Record<string, { text: string }>;
}
type Diagnoses = Record<string, { domain: string; crop?: string; steps: string[] }>;

// ------------------------------------------------------------- languages ---
const LANG_CODES: Record<string, string> = {
  English: 'en', Hausa: 'ha', Yoruba: 'yo', Igbo: 'ig', French: 'fr', Swahili: 'sw',
};
/** Languages that have a phrase file in /content/phrases (drafts included; flagged in UI). */
export const AVAILABLE_LANGS = ['en', 'ha'];

export function langCode(uiLanguage: string | null | undefined): string {
  const code = LANG_CODES[uiLanguage || 'English'] || 'en';
  return AVAILABLE_LANGS.includes(code) ? code : 'en';
}

// ----------------------------------------------------------------- caches ---
/** Installed packs live in Cache Storage; everything else comes over the network or the service worker. */
async function getFile(url: string): Promise<Response> {
  try {
    if (url.startsWith('/packs/') && 'caches' in window) {
      const hit = await caches.match(url);
      if (hit) return hit;
    }
  } catch { /* fall through */ }
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Could not load ${url} (${r.status})`);
  return r;
}
const json = async <T>(url: string): Promise<T> => (await getFile(url)).json() as Promise<T>;
const cache = new Map<string, Promise<unknown>>();
function once<T>(key: string, make: () => Promise<T>): Promise<T> {
  if (!cache.has(key)) cache.set(key, make().catch(e => { cache.delete(key); throw e; }));
  return cache.get(key) as Promise<T>;
}

export const phrasesFor = (uiLanguage?: string | null) =>
  once(`phrases:${langCode(uiLanguage)}`, () => json<Phrases>(`/content/phrases/${langCode(uiLanguage)}.json`));
const english = () => once('phrases:en', () => json<Phrases>('/content/phrases/en.json'));
const diagnoses = () => once('diagnoses', () => json<Diagnoses>('/content/diagnoses.json'));

// ------------------------------------------------------------- model packs ---
type OrtTensor = Feed;
interface Pack { manifest: Manifest; labels: Label[]; session: Session; dsp?: DspConstants; base: string }
function loadPack(name: 'crop' | 'machine'): Promise<Pack> {
  return once(`pack:${name}`, async () => {
    const base = await packBase(name);                       // an installed pack wins over the built-in one
    const manifest = await json<Manifest>(base + 'manifest.json');
    const labels = await json<Label[]>(base + manifest.labels);
    const model = await (await getFile(base + manifest.model)).arrayBuffer();
    const session = await createSession(name, model);
    const dsp = name === 'machine' ? await json<DspConstants>(base + 'dsp_constants.json') : undefined;
    return { manifest, labels, session, dsp, base };
  });
}

/** Forget loaded models (after installing or removing a pack) so the next scan loads the new one. */
export function resetPacks(): void {
  for (const k of [...cache.keys()]) if (k.startsWith('pack:')) cache.delete(k);
}

/** Version of the model currently in use, e.g. "crop-core-1@0.2.0 (installed pack)". */
export async function activeModel(name: 'crop' | 'machine'): Promise<string> {
  const base = await packBase(name);
  const m = await json<Manifest>(base + 'manifest.json');
  return `${m.pack_id}@${m.version}${base.startsWith('/packs/') ? ' (installed pack)' : ' (built in)'}`;
}

/** Warm up models in the background (call once when a scan screen opens). */
export function preload(domain: 'crop' | 'machine'): void {
  loadPack(domain).catch(() => { /* surfaced on scan */ });
}

// --------------------------------------------------------------- results ---
async function describe(domain: 'crop' | 'machine', kind: AiKind, diagnosisId: string | undefined,
                        confidence: number, uiLanguage: string | null | undefined, model: string,
                        extra: Partial<AiResult> = {}): Promise<AiResult> {
  const [p, en, dx] = await Promise.all([phrasesFor(uiLanguage), english(), diagnoses()]);
  const ui = (k: string) => p.ui[k] ?? en.ui[k] ?? k;
  const step = (s: string) => p.steps[s]?.text ?? en.steps[s]?.text ?? s;
  let name: string, steps: string[], clipIds: string[];
  if (kind === 'diagnosis' && diagnosisId) {
    name = p.diagnoses[diagnosisId]?.name ?? en.diagnoses[diagnosisId]?.name ?? diagnosisId;
    const ids = dx[diagnosisId]?.steps ?? ['ask_extension_officer'];
    steps = ids.map(step);
    clipIds = [`d_${diagnosisId}`, ...ids.map(s => `s_${s}`), 'disclaimer'];
  } else if (kind === 'uncertain') {
    const nk = domain === 'machine' ? 'not_sure_machine' : 'not_sure';
    const sk = domain === 'machine' ? 'contact_mechanic' : 'ask_extension_officer';
    name = ui(nk);
    steps = [step(sk)];
    clipIds = [nk, `s_${sk}`];
  } else {
    name = extra.reason ?? ui('not_sure');
    steps = [];
    clipIds = [];
  }
  return { kind, domain, diagnosisId, name, steps, confidence, lang: p.lang, model, clipIds, ...extra };
}

function softmax(logits: number[], T: number): number[] {
  const z = logits.map(v => v / T), m = Math.max(...z);
  const e = z.map(v => Math.exp(v - m)), s = e.reduce((a, b) => a + b, 0);
  return e.map(v => v / s);
}

// ------------------------------------------------------------------ photo ---
const CROP_KEYS: Record<string, string> = { Cassava: 'cassava', Maize: 'maize', Tomato: 'tomato' };
export const SUPPORTED_CROPS = Object.keys(CROP_KEYS);

/** Resize like training (short side 256, high-quality smoothing), then centre-crop 224. */
async function prepareImage(file: Blob, short = 256, size = 224): Promise<{ crop: RGBA; preview: HTMLCanvasElement }> {
  const bmp = await createImageBitmap(file);
  const s = short / Math.min(bmp.width, bmp.height);
  const W = Math.max(size, Math.round(bmp.width * s)), H = Math.max(size, Math.round(bmp.height * s));
  const canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(bmp, 0, 0, W, H);
  bmp.close?.();
  const ox = Math.floor((W - size) / 2), oy = Math.floor((H - size) / 2);
  const d = ctx.getImageData(ox, oy, size, size);
  const preview = document.createElement('canvas');
  preview.width = size; preview.height = size;
  preview.getContext('2d')!.putImageData(d, 0, 0);
  return { crop: { data: d.data, width: size, height: size }, preview };
}

function overlayDataUrl(preview: HTMLCanvasElement, cam: OrtTensor, cls: number): string | undefined {
  if (!cam || cam.dims.length !== 4) return undefined;
  const [, K, h, w] = cam.dims;               // trained model: 14 x 6 x 6 -- never hard-code
  const ov = camOverlay(cam.data, K, h, w, cls, preview.width, preview.height);
  const layer = document.createElement('canvas');
  layer.width = preview.width; layer.height = preview.height;
  layer.getContext("2d")!.putImageData(new ImageData(new Uint8ClampedArray(ov.data), ov.width, ov.height), 0, 0);
  const out = document.createElement('canvas');
  out.width = preview.width; out.height = preview.height;
  const ctx = out.getContext('2d')!;
  ctx.drawImage(preview, 0, 0);
  ctx.drawImage(layer, 0, 0);
  return out.toDataURL('image/jpeg', 0.85);
}

/** Time a scan end to end (decode, quality check, model, wording) on this device. */
async function timed(run: () => Promise<AiResult>): Promise<AiResult> {
  const t0 = performance.now();
  const r = await run();
  return { ...r, ms: Math.round(performance.now() - t0) };
}

export const scanPhoto = (file: Blob, cropName: string, uiLanguage?: string | null) =>
  timed(() => scanPhotosInner([file], cropName, uiLanguage));
/** Two or more photos of the same plant (e.g. a second angle after "not sure"): probabilities are averaged. */
export const scanPhotos = (files: Blob[], cropName: string, uiLanguage?: string | null) =>
  timed(() => scanPhotosInner(files, cropName, uiLanguage));
export const scanAudio = (blob: Blob, machineKind: string, uiLanguage?: string | null) =>
  timed(() => scanAudioInner(blob, machineKind, uiLanguage));

async function scanPhotosInner(files: Blob[], cropName: string, uiLanguage?: string | null): Promise<AiResult> {
  const cropKey = CROP_KEYS[cropName];
  const en = await english();
  if (!cropKey) {
    return describe('crop', 'unsupported', undefined, 0, uiLanguage, 'crop-core-1',
      { reason: `${cropName} is not supported yet. Supported now: ${SUPPORTED_CROPS.join(', ')}.` });
  }
  try {
    const pack = await loadPack('crop');
    const { manifest: m, labels } = pack;
    const model = `${m.pack_id}@${m.version}`;
    // score every photo that passes the quality check; average their probabilities
    let avg: number[] | null = null, used = 0, lastQ = 'ok';
    let first: { preview: HTMLCanvasElement; cam?: OrtTensor } | null = null;
    for (const file of files.slice(0, 3)) {
      const { crop, preview } = await prepareImage(file, m.input.resize_short_side ?? 256, m.input.size?.[0] ?? 224);
      const q = photoQuality(crop);
      if (q !== 'ok') { lastQ = q; continue; }
      const x = toTensor(crop, m.input.mean ?? [0.5, 0.5, 0.5], m.input.std ?? [0.5, 0.5, 0.5]);
      const out = await pack.session.run({ [m.input.name]: { data: x, dims: [1, 3, crop.height, crop.width] } });
      const p = softmax(Array.from(out[m.output.name].data), m.temperature);
      avg = avg ? avg.map((v, i) => v + p[i]) : p;
      used++;
      if (!first) first = { preview, cam: m.output.cam ? out[m.output.cam] : undefined };
    }
    if (!avg || !first) {
      const p = await phrasesFor(uiLanguage);
      return describe('crop', 'retake', undefined, 0, uiLanguage, model,
        { reason: p.ui[`retake_${lastQ}`] ?? en.ui[`retake_${lastQ}`] ?? 'Please retake the photo.', clipIds: [`retake_${lastQ}`] });
    }
    const probs = avg.map(v => v / used);
    const d = decide(probs.map(v => Math.log(v + 1e-12)), 1, m.thresholds);   // T already applied
    const top = probs.indexOf(Math.max(...probs));
    const diagId = labels[top]?.diagnosis_id;
    const extra = { photos: used, backend: pack.session.backend };
    // The farmer told us the crop: if the model's best guess is another crop, don't pretend.
    const wrongCrop = diagId && !diagId.startsWith(cropKey + '_');
    if (wrongCrop && d.kind === 'diagnosis') {
      // Confident, but about another crop: tell the farmer which crop to pick instead.
      const p = await phrasesFor(uiLanguage);
      const seenKey = diagId.split('_')[0];
      const name = (k: string) => p.crops?.[k] ?? en.crops?.[k] ?? k;
      const tpl = p.ui.retake_wrong_crop ?? en.ui.retake_wrong_crop;
      const reason = tpl.split('{seen}').join(name(seenKey)).split('{chosen}').join(name(cropKey));
      return describe('crop', 'retake', undefined, 0, uiLanguage, model, { reason, clipIds: [], ...extra });
    }
    if (d.kind === 'uncertain' || wrongCrop) {
      return describe('crop', 'uncertain', undefined, d.confidence, uiLanguage, model, extra);
    }
    const overlay = first.cam ? overlayDataUrl(first.preview, first.cam, top) : undefined;
    return describe('crop', 'diagnosis', diagId, d.confidence, uiLanguage, model, { overlay, ...extra });
  } catch (e) {
    return describe('crop', 'error', undefined, 0, uiLanguage, 'crop-core-1',
      { reason: e instanceof Error ? e.message : 'The crop model could not run on this device.' });
  }
}

// ------------------------------------------------------------------ audio ---
export const SUPPORTED_MACHINES = ['Irrigation pump'];

async function decodeTo16k(blob: Blob, sampleRate = 16000): Promise<Float32Array> {
  const bytes = await blob.arrayBuffer();
  const AC: typeof AudioContext = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AC();
  try {
    const buf = await ctx.decodeAudioData(bytes);
    const len = Math.max(1, Math.ceil(buf.duration * sampleRate));
    const off = new OfflineAudioContext(1, len, sampleRate);
    const src = off.createBufferSource();
    src.buffer = buf;
    src.connect(off.destination);
    src.start();
    return (await off.startRendering()).getChannelData(0).slice();
  } finally {
    ctx.close().catch(() => undefined);
  }
}

async function scanAudioInner(blob: Blob, machineKind: string, uiLanguage?: string | null): Promise<AiResult> {
  if (!SUPPORTED_MACHINES.includes(machineKind)) {
    return describe('machine', 'unsupported', undefined, 0, uiLanguage, 'machine-core-1',
      { reason: `${machineKind} is not supported yet. Supported now: irrigation pumps. Generators and small engines are coming in the next pack.` });
  }
  try {
    const pack = await loadPack('machine');
    const { manifest: m, labels, dsp } = pack;
    const C = dsp!;
    const x = await decodeTo16k(blob, C.sample_rate);
    const model = `${m.pack_id}@${m.version}`;
    // score every 5 s window (hop 2.5 s), average probabilities (one window for a 5 s clip)
    const starts: number[] = [];
    for (let s = 0; s + C.n_samples <= x.length; s += C.n_samples / 2) starts.push(s);
    if (!starts.length) starts.push(0);
    const en = await english();
    let avg: number[] | null = null, used = 0, lastQ = 'ok';
    for (const s of starts.slice(0, 6)) {
      const w = x.subarray(s, s + C.n_samples);
      const q = quality(w, C);
      if (q !== 'ok') { lastQ = q; continue; }
      const feats = logmel(w, C);
      const out = await pack.session.run({ [m.input.name]: { data: feats, dims: [1, 1, C.n_mels, C.n_frames] } });
      const p = softmax(Array.from(out[m.output.name].data), m.temperature);
      avg = avg ? avg.map((v, i) => v + p[i]) : p;
      used++;
    }
    if (!avg) {
      const p = await phrasesFor(uiLanguage);
      return describe('machine', 'retake', undefined, 0, uiLanguage, model,
        { reason: p.ui[`retake_${lastQ}`] ?? en.ui[`retake_${lastQ}`] ?? 'Please record again.', clipIds: [`retake_${lastQ}`] });
    }
    const probs = avg.map(v => v / used);
    // reuse the shared decision layer on log-probabilities (T already applied)
    const d = decide(probs.map(v => Math.log(v + 1e-12)), 1, m.thresholds);
    const extra = { backend: pack.session.backend };
    if (d.kind === 'uncertain') return describe('machine', 'uncertain', undefined, d.confidence, uiLanguage, model, extra);
    return describe('machine', 'diagnosis', labels[d.index].diagnosis_id, d.confidence, uiLanguage, model, extra);
  } catch (e) {
    return describe('machine', 'error', undefined, 0, uiLanguage, 'machine-core-1',
      { reason: e instanceof Error ? e.message : 'The machine model could not run on this device.' });
  }
}

// --------------------------------------------------------------- benchmark ---
export interface BenchResult { model: string; backend: 'worker' | 'main'; runs: number; p50: number; p95: number; mean: number; loadMs: number }

/** Speed test from the Technical Documentation (section 13): 50 runs per model after warm-up. */
export async function benchmark(name: 'crop' | 'machine', runs = 50): Promise<BenchResult> {
  resetPacks();
  const t0 = performance.now();
  const pack = await loadPack(name);
  const loadMs = performance.now() - t0;
  const m = pack.manifest;
  const dims = name === 'crop' ? [1, 3, 224, 224] : [1, 1, pack.dsp!.n_mels, pack.dsp!.n_frames];
  const n = dims.reduce((a, b) => a * b, 1);
  const make = () => { const d = new Float32Array(n); for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1; return d; };
  for (let i = 0; i < 3; i++) await pack.session.run({ [m.input.name]: { data: make(), dims } });   // warm-up
  const times: number[] = [];
  for (let i = 0; i < runs; i++) {
    const data = make();
    const t = performance.now();
    await pack.session.run({ [m.input.name]: { data, dims } });
    times.push(performance.now() - t);
  }
  times.sort((a, b) => a - b);
  const q = (f: number) => times[Math.min(times.length - 1, Math.floor(f * times.length))];
  return { model: `${m.pack_id}@${m.version}`, backend: pack.session.backend, runs,
           p50: q(0.5), p95: q(0.95), mean: times.reduce((a, b) => a + b, 0) / runs, loadMs };
}
