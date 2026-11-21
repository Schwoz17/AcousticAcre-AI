/**
 * AcousticAcre photo side: preprocessing, quality gates, and "where the model looked" overlay.
 * Works on plain RGBA buffers so it runs in a Web Worker (and in Node for tests).
 *
 *   const img = await imageFromFile(file);                       // browser helper below
 *   const q = photoQuality(img);   if (q !== 'ok') -> show retake_<q> message
 *   const crop = resizeAndCenterCrop(img, 256, 224);
 *   const x = toTensor(crop, manifest.input.mean, manifest.input.std);   // Float32Array [3*224*224]
 *   const out = await session.run({ input: new ort.Tensor('float32', x, [1, 3, 224, 224]) });
 *   const r = decide(Array.from(out.logits.data), manifest.temperature, manifest.thresholds);  // from logmel.ts
 *   const [, K, h, w] = out.cam.dims;   // trained model: 14 x 6 x 6 -- never hard-code
 *   if (r.kind === 'diagnosis') overlay = camOverlay(out.cam.data as Float32Array, K, h, w, r.index, 224, 224);
 */

export interface RGBA { data: Uint8ClampedArray; width: number; height: number }
export type PhotoQuality = 'ok' | 'blurry' | 'dark' | 'bright' | 'no_leaf';

/** Bilinear resize so the short side = `short`, then centre-crop `crop` x `crop`. */
export function resizeAndCenterCrop(img: RGBA, short = 256, crop = 224): RGBA {
  const s = short / Math.min(img.width, img.height);
  const rw = Math.round(img.width * s), rh = Math.round(img.height * s);
  const ox = Math.floor((rw - crop) / 2), oy = Math.floor((rh - crop) / 2);
  const out = new Uint8ClampedArray(crop * crop * 4);
  for (let y = 0; y < crop; y++) {
    const sy = Math.min(img.height - 1, Math.max(0, (y + oy + 0.5) / s - 0.5));
    const y0 = Math.floor(sy), y1 = Math.min(img.height - 1, y0 + 1), fy = sy - y0;
    for (let x = 0; x < crop; x++) {
      const sx = Math.min(img.width - 1, Math.max(0, (x + ox + 0.5) / s - 0.5));
      const x0 = Math.floor(sx), x1 = Math.min(img.width - 1, x0 + 1), fx = sx - x0;
      for (let c = 0; c < 4; c++) {
        const p = (yy: number, xx: number) => img.data[(yy * img.width + xx) * 4 + c];
        const v = (p(y0, x0) * (1 - fx) + p(y0, x1) * fx) * (1 - fy) + (p(y1, x0) * (1 - fx) + p(y1, x1) * fx) * fy;
        out[(y * crop + x) * 4 + c] = v;
      }
    }
  }
  return { data: out, width: crop, height: crop };
}

/** RGBA -> Float32Array NCHW (batch 1), scaled to [0,1] then (x - mean) / std. */
export function toTensor(img: RGBA, mean: number[], std: number[]): Float32Array {
  const n = img.width * img.height, out = new Float32Array(3 * n);
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < 3; c++) out[c * n + i] = (img.data[i * 4 + c] / 255 - mean[c]) / std[c];
  }
  return out;
}

function gray(img: RGBA): Float32Array {
  const g = new Float32Array(img.width * img.height);
  for (let i = 0; i < g.length; i++) g[i] = 0.299 * img.data[i * 4] + 0.587 * img.data[i * 4 + 1] + 0.114 * img.data[i * 4 + 2];
  return g;
}

export interface PhotoThresholds { dark: number; bright: number; blurVar: number; leafFrac: number }
/** Starting values; tune on real phone photos. */
export const DEFAULT_PHOTO_THRESHOLDS: PhotoThresholds = { dark: 45, bright: 230, blurVar: 40, leafFrac: 0.15 };

/** Run on the 224x224 crop (what the model sees). */
export function photoQuality(img: RGBA, th: PhotoThresholds = DEFAULT_PHOTO_THRESHOLDS): PhotoQuality {
  const g = gray(img), W = img.width, H = img.height;
  let mean = 0;
  for (const v of g) mean += v;
  mean /= g.length;
  if (mean < th.dark) return 'dark';
  if (mean > th.bright) return 'bright';
  // variance of the Laplacian: low = blurry
  let s = 0, s2 = 0, n = 0;
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
    const i = y * W + x;
    const lap = g[i - W] + g[i + W] + g[i - 1] + g[i + 1] - 4 * g[i];
    s += lap; s2 += lap * lap; n++;
  }
  const v = s2 / n - (s / n) ** 2;
  if (v < th.blurVar) return 'blurry';
  // plant-coloured pixels: green to yellow, or brown (diseased tissue), with some saturation
  let plant = 0;
  for (let i = 0; i < W * H; i++) {
    const r = img.data[i * 4] / 255, gg = img.data[i * 4 + 1] / 255, b = img.data[i * 4 + 2] / 255;
    const mx = Math.max(r, gg, b), mn = Math.min(r, gg, b), d = mx - mn;
    if (mx < 0.12 || d / (mx || 1) < 0.15) continue;           // too dark or grey
    let h = mx === r ? ((gg - b) / d) % 6 : mx === gg ? (b - r) / d + 2 : (r - gg) / d + 4;
    h = (h * 60 + 360) % 360;
    if (h >= 15 && h <= 170) plant++;                            // brown, yellow, green
  }
  if (plant / (W * H) < th.leafFrac) return 'no_leaf';
  return 'ok';
}

/** Class activation map for one class -> RGBA overlay (warm colour where the model looked). */
export function camOverlay(cam: Float32Array | number[], K: number, h: number, w: number, cls: number,
                           outW = 224, outH = 224, cut = 0.5): RGBA {
  const m = new Float32Array(h * w);
  let mx = 0;
  for (let i = 0; i < h * w; i++) { m[i] = Math.max(0, cam[cls * h * w + i]); if (m[i] > mx) mx = m[i]; }
  const out = new Uint8ClampedArray(outW * outH * 4);
  if (mx === 0) return { data: out, width: outW, height: outH };
  for (let y = 0; y < outH; y++) {
    const sy = Math.min(h - 1, Math.max(0, ((y + 0.5) * h) / outH - 0.5));
    const y0 = Math.floor(sy), y1 = Math.min(h - 1, y0 + 1), fy = sy - y0;
    for (let x = 0; x < outW; x++) {
      const sx = Math.min(w - 1, Math.max(0, ((x + 0.5) * w) / outW - 0.5));
      const x0 = Math.floor(sx), x1 = Math.min(w - 1, x0 + 1), fx = sx - x0;
      const v = ((m[y0 * w + x0] * (1 - fx) + m[y0 * w + x1] * fx) * (1 - fy)
               + (m[y1 * w + x0] * (1 - fx) + m[y1 * w + x1] * fx) * fy) / mx;
      if (v < cut) continue;
      const o = (y * outW + x) * 4;
      out[o] = 255; out[o + 1] = Math.round(160 * (1 - v)); out[o + 2] = 0;
      out[o + 3] = Math.round(90 + 110 * (v - cut) / (1 - cut));
    }
  }
  return { data: out, width: outW, height: outH };
}

/** Browser only: File/Blob -> RGBA, downscaled so the short side is at most 512 px. */
export async function imageFromFile(file: Blob): Promise<RGBA> {
  const bmp = await createImageBitmap(file);
  const s = Math.min(1, 512 / Math.min(bmp.width, bmp.height));
  const W = Math.round(bmp.width * s), H = Math.round(bmp.height * s);
  const cv = new OffscreenCanvas(W, H);
  const ctx = cv.getContext('2d')!;
  ctx.drawImage(bmp, 0, 0, W, H);
  const d = ctx.getImageData(0, 0, W, H);
  return { data: d.data, width: W, height: H };
}
