/**
 * AcousticAcre in-browser log-Mel front end + decision layer. No dependencies.
 * Must match ml/dsp/logmel.py exactly (checked by web-dsp/parity.test.ts).
 *
 * Usage (in a Web Worker):
 *   const C = await (await fetch('/packs/machine/dsp_constants.json')).json();
 *   const x16k = await resampleTo16k(audioBuffer);          // Float32Array
 *   const feats = logmel(x16k, C);                           // Float32Array, 64*309, row-major [mel][frame]
 *   const tensor = new ort.Tensor('float32', feats, [1, 1, 64, 309]);
 *   const { logits } = await session.run({ input: tensor });
 *   const r = decide(Array.from(logits.data as Float32Array), manifest.temperature, manifest.thresholds);
 */

export interface DspConstants {
  sample_rate: number; n_samples: number; n_fft: number; hop: number; n_frames: number;
  n_mels: number; top_db: number; eps: number;
  mel_rows: { start: number; weights: number[] }[];
}

// ------------------------------------------------------------------ FFT ----
const fftCache = new Map<number, { cos: Float64Array; sin: Float64Array; rev: Uint32Array }>();

function fftTables(n: number) {
  let t = fftCache.get(n);
  if (t) return t;
  const cos = new Float64Array(n / 2), sin = new Float64Array(n / 2), rev = new Uint32Array(n);
  for (let i = 0; i < n / 2; i++) { cos[i] = Math.cos((2 * Math.PI * i) / n); sin[i] = -Math.sin((2 * Math.PI * i) / n); }
  const bits = Math.log2(n);
  for (let i = 0; i < n; i++) { let r = 0; for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b); rev[i] = r; }
  t = { cos, sin, rev };
  fftCache.set(n, t);
  return t;
}

/** In-place radix-2 complex FFT (n must be a power of two). */
function fft(re: Float64Array, im: Float64Array) {
  const n = re.length, { cos, sin, rev } = fftTables(n);
  for (let i = 0; i < n; i++) {
    const j = rev[i];
    if (j > i) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
  }
  for (let size = 2; size <= n; size <<= 1) {
    const half = size >> 1, step = n / size;
    for (let start = 0; start < n; start += size) {
      for (let k = 0; k < half; k++) {
        const wr = cos[k * step], wi = sin[k * step];
        const a = start + k, b = a + half;
        const tr = re[b] * wr - im[b] * wi, ti = re[b] * wi + im[b] * wr;
        re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
      }
    }
  }
}

// --------------------------------------------------------------- features ---
export function fixLength(x: Float32Array, n: number): Float32Array {
  if (x.length === n) return x;
  const out = new Float32Array(n);
  out.set(x.subarray(0, Math.min(n, x.length)));
  return out;
}

/** dB log-Mel before normalisation, Float64Array [n_mels * n_frames], row-major [mel][frame]. */
export function logmelDb(x: Float32Array, C: DspConstants): Float64Array {
  const { n_fft, hop, n_frames, n_mels } = C;
  const sig = fixLength(x, C.n_samples);
  const nBins = n_fft / 2 + 1;
  const win = new Float64Array(n_fft);
  for (let i = 0; i < n_fft; i++) win[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / n_fft);
  const re = new Float64Array(n_fft), im = new Float64Array(n_fft), pow = new Float64Array(nBins);
  const out = new Float64Array(n_mels * n_frames);
  let max = -Infinity;
  for (let t = 0; t < n_frames; t++) {
    const off = t * hop;
    for (let i = 0; i < n_fft; i++) { re[i] = Math.fround(sig[off + i] * Math.fround(win[i])); im[i] = 0; }
    fft(re, im);
    for (let k = 0; k < nBins; k++) pow[k] = re[k] * re[k] + im[k] * im[k];
    for (let m = 0; m < n_mels; m++) {
      const row = C.mel_rows[m];
      let s = 0;
      for (let j = 0; j < row.weights.length; j++) s += row.weights[j] * pow[row.start + j];
      const db = 10 * Math.log10(s + C.eps);
      out[m * n_frames + t] = db;
      if (db > max) max = db;
    }
  }
  const floor = max - C.top_db;
  for (let i = 0; i < out.length; i++) if (out[i] < floor) out[i] = floor;
  return out;
}

/** Normalised model features, Float32Array [n_mels * n_frames]. */
export function logmel(x: Float32Array, C: DspConstants): Float32Array {
  const db = logmelDb(x, C);
  let mean = 0;
  for (let i = 0; i < db.length; i++) mean += db[i];
  mean /= db.length;
  let v = 0;
  for (let i = 0; i < db.length; i++) v += (db[i] - mean) ** 2;
  const std = Math.sqrt(v / db.length) + 1e-6;
  const out = new Float32Array(db.length);
  for (let i = 0; i < db.length; i++) out[i] = (db[i] - mean) / std;
  return out;
}

// ---------------------------------------------------------- quality gates ---
export type Quality = 'ok' | 'too_quiet' | 'clipping' | 'wind' | 'no_machine';

/** Same starting thresholds as ml/dsp/logmel.py quality(). Call before inference. */
export function quality(x: Float32Array, C: DspConstants): Quality {
  const sig = fixLength(x, C.n_samples);
  let ss = 0, clipped = 0;
  for (let i = 0; i < sig.length; i++) { ss += sig[i] * sig[i]; if (Math.abs(sig[i]) >= 0.999) clipped++; }
  if (Math.sqrt(ss / sig.length) < 0.003) return 'too_quiet';
  if (clipped / sig.length > 0.01) return 'clipping';
  const { n_fft, hop, n_frames } = C, nBins = n_fft / 2 + 1, binHz = C.sample_rate / n_fft;
  const re = new Float64Array(n_fft), im = new Float64Array(n_fft);
  const meanPow = new Float64Array(nBins), low = new Float64Array(n_frames);
  for (let t = 0; t < n_frames; t++) {
    for (let i = 0; i < n_fft; i++) { re[i] = Math.fround(sig[t * hop + i] * Math.fround(0.5 - 0.5 * Math.cos((2 * Math.PI * i) / n_fft))); im[i] = 0; }
    fft(re, im);
    for (let k = 0; k < nBins; k++) {
      const p = re[k] * re[k] + im[k] * im[k];
      meanPow[k] += p / n_frames;
      if (k * binHz < 100) low[t] += p;
    }
  }
  let total = 0, lowTotal = 0, logSum = 0;
  for (let k = 0; k < nBins; k++) { total += meanPow[k]; if (k * binHz < 100) lowTotal += meanPow[k]; logSum += Math.log(meanPow[k] + C.eps); }
  let lm = 0; for (const v of low) lm += v; lm /= n_frames;
  let lv = 0; for (const v of low) lv += (v - lm) ** 2;
  const gusty = Math.sqrt(lv / n_frames) / (lm + C.eps) > 0.8;
  if (lowTotal / (total + C.eps) > 0.6 && gusty) return 'wind';
  const flatness = Math.exp(logSum / nBins) / (total / nBins + C.eps);
  if (flatness > 0.5) return 'no_machine';
  return 'ok';
}

// --------------------------------------------------------- decision layer ---
export interface Thresholds { conf: number; margin: number; entropy: number }
export type Decision = { kind: 'diagnosis'; index: number; confidence: number; probs: number[] }
                     | { kind: 'uncertain'; confidence: number; probs: number[] };

export function decide(logits: number[], temperature: number, th: Thresholds): Decision {
  const z = logits.map(v => v / temperature);
  const mx = Math.max(...z);
  const e = z.map(v => Math.exp(v - mx));
  const sum = e.reduce((a, b) => a + b, 0);
  const p = e.map(v => v / sum);
  const order = p.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0]);
  const top1 = order[0][0], top2 = order.length > 1 ? order[1][0] : 0;
  const entropy = -p.reduce((a, v) => a + v * Math.log(v + 1e-12), 0);
  if (top1 >= th.conf && top1 - top2 >= th.margin && entropy <= th.entropy) {
    return { kind: 'diagnosis', index: order[0][1], confidence: top1, probs: p };
  }
  return { kind: 'uncertain', confidence: top1, probs: p };
}

// ------------------------------------------------------------- resampling ---
/** Browser only. Resample a decoded/recorded AudioBuffer to 16 kHz mono.
 *  Note: this resampler differs slightly from scipy's; the parity test covers
 *  everything after resampling. Better: record with new AudioContext({ sampleRate: 16000 }). */
export async function resampleTo16k(buf: AudioBuffer): Promise<Float32Array> {
  const len = Math.ceil(buf.duration * 16000);
  const ctx = new OfflineAudioContext(1, len, 16000);
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.connect(ctx.destination);
  src.start();
  return (await ctx.startRendering()).getChannelData(0).slice();
}
