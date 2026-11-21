// node web-dsp/image.test.ts
import { resizeAndCenterCrop, toTensor, photoQuality, camOverlay, type RGBA } from './image.ts';

let fails = 0;
const check = (name: string, ok: boolean, extra = '') => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${name} ${extra}`); if (!ok) fails++; };

function make(w: number, h: number, f: (x: number, y: number) => [number, number, number]): RGBA {
  const d = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const [r, g, b] = f(x, y), o = (y * w + x) * 4;
    d[o] = r; d[o + 1] = g; d[o + 2] = b; d[o + 3] = 255;
  }
  return { data: d, width: w, height: h };
}
let seed = 1;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

// textured green leaf with veins and brown spots
const leaf = make(640, 480, (x, y) => {
  const vein = (Math.abs(((x + y) % 40) - 20) < 2) ? 40 : 0;
  const spot = ((x - 300) ** 2 + (y - 200) ** 2 < 900) ? 1 : 0;
  const n = rnd() * 30;
  return spot ? [120 + n, 70 + n, 20] : [40 + vein + n, 140 + vein + n, 40 + n];
});
const crop = resizeAndCenterCrop(leaf, 256, 224);
check('crop size', crop.width === 224 && crop.height === 224);
check('leaf ok', photoQuality(crop) === 'ok', photoQuality(crop));

const dark = make(300, 300, () => [10, 20, 10]);
check('dark', photoQuality(resizeAndCenterCrop(dark)) === 'dark');

const wall = make(300, 300, () => { const n = rnd() * 60; return [120 + n, 120 + n, 125 + n]; });
check('grey wall -> no_leaf', photoQuality(resizeAndCenterCrop(wall)) === 'no_leaf', photoQuality(resizeAndCenterCrop(wall)));

// blur the leaf heavily (box blur 15px)
const blurred = (() => {
  const c = crop, out = new Uint8ClampedArray(c.data.length), R = 7;
  for (let y = 0; y < 224; y++) for (let x = 0; x < 224; x++) for (let k = 0; k < 4; k++) {
    let s = 0, n = 0;
    for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) {
      const yy = Math.min(223, Math.max(0, y + dy)), xx = Math.min(223, Math.max(0, x + dx));
      s += c.data[(yy * 224 + xx) * 4 + k]; n++;
    }
    out[(y * 224 + x) * 4 + k] = s / n;
  }
  return { data: out, width: 224, height: 224 };
})();
check('blurred', photoQuality(blurred) === 'blurry', photoQuality(blurred));

// tensor layout and normalisation
const solid = make(224, 224, () => [255, 0, 128]);
const t = toTensor(solid, [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]);
const n = 224 * 224;
check('tensor NCHW', t.length === 3 * n && Math.abs(t[0] - 1) < 1e-6 && Math.abs(t[n] + 1) < 1e-6 && Math.abs(t[2 * n] - 0.0039) < 1e-3);

// CAM peak lands where it should (class 1, peak at cell (5,2) of 7x7)
const K = 2, cam = new Float32Array(K * 49);
cam[49 + 5 * 7 + 2] = 3; cam[49 + 5 * 7 + 3] = 1;
const ov = camOverlay(cam, K, 7, 7, 1, 224, 224);
let best = -1, bi = 0;
for (let i = 0; i < 224 * 224; i++) if (ov.data[i * 4 + 3] > best) { best = ov.data[i * 4 + 3]; bi = i; }
const by = Math.floor(bi / 224), bx = bi % 224;
check('cam peak location', by >= 160 && by <= 192 && bx >= 64 && bx <= 96, `(${bx},${by})`);
check('cam empty class', camOverlay(cam, K, 7, 7, 0).data.every(v => v === 0));

console.log(fails ? `${fails} FAILED` : 'ALL PASS');
process.exit(fails ? 1 : 0);
