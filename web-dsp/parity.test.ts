// Node 22+: node web-dsp/parity.test.ts   (fails with exit code 1 on mismatch)
import { readFileSync } from 'node:fs';
import { logmelDb, logmel, quality, decide, type DspConstants } from './logmel.ts';

const dir = new URL('./fixtures/', import.meta.url);
const C: DspConstants = JSON.parse(readFileSync(new URL('dsp_constants.json', dir), 'utf8'));
const ref = JSON.parse(readFileSync(new URL('reference.json', dir), 'utf8'));
const raw = readFileSync(new URL('clips_f32le.bin', dir));
const all = new Float32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
const TOL_DB = 0.1, TOL_NORM = 0.01;
let worstDb = 0, worstNorm = 0, qualityMismatch = 0;
for (let c = 0; c < ref.n; c++) {
  const x = all.subarray(c * C.n_samples, (c + 1) * C.n_samples);
  const db = logmelDb(x, C), nm = logmel(x, C);
  ref.db[c].forEach((v: number, i: number) => { worstDb = Math.max(worstDb, Math.abs(db[i * 7] - v)); });
  ref.norm[c].forEach((v: number, i: number) => { worstNorm = Math.max(worstNorm, Math.abs(nm[i * 7] - v)); });
  if (quality(x, C) !== ref.quality[c]) { qualityMismatch++; console.log(`clip ${c}: quality ${quality(x, C)} vs ${ref.quality[c]}`); }
}
const d = decide([0, 3], 1, { conf: 0.7, margin: 0.2, entropy: 0.69 });
const u = decide([0, 0.1], 1, { conf: 0.7, margin: 0.2, entropy: 0.69 });
console.log(`clips ${ref.n}  max |dB diff| ${worstDb.toExponential(2)} (tol ${TOL_DB})  max |norm diff| ${worstNorm.toExponential(2)} (tol ${TOL_NORM})  quality mismatches ${qualityMismatch}`);
console.log(`decide: [0,3] -> ${d.kind}, [0,0.1] -> ${u.kind}`);
const ok = worstDb <= TOL_DB && worstNorm <= TOL_NORM && qualityMismatch === 0 && d.kind === 'diagnosis' && u.kind === 'uncertain';
console.log(ok ? 'PARITY PASS' : 'PARITY FAIL');
process.exit(ok ? 0 : 1);
