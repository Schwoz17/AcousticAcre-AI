// Copies ONNX Runtime Web from node_modules into public/ort so it is served (and cached
// offline) like any other static file. Runs automatically after `npm install`.
import { cpSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const dist = join('node_modules', 'onnxruntime-web', 'dist');
const out = join('public', 'ort');
if (!existsSync(dist)) {
  console.error('[copy-ort] onnxruntime-web is not installed; run npm install first.');
  process.exit(1);
}
mkdirSync(out, { recursive: true });
const files = readdirSync(dist);
const main = ['ort.wasm.min.js', 'ort.min.js', 'ort.all.min.js'].find(f => files.includes(f));
if (!main) {
  console.error('[copy-ort] no ort*.min.js found in', dist, '\n', files.join(' '));
  process.exit(1);
}
cpSync(join(dist, main), join(out, 'ort.js'));
// the WebAssembly runtime it loads (skip the much larger WebGPU "jsep"/"asyncify" builds)
const runtime = files.filter(f => /^ort-wasm.*\.(wasm|mjs)$/.test(f) && !/jsep|asyncify|jspi/.test(f));
if (!runtime.some(f => f.endsWith('.wasm'))) {
  console.error('[copy-ort] no ort-wasm*.wasm found in', dist);
  process.exit(1);
}
for (const f of runtime) cpSync(join(dist, f), join(out, f));
console.log(`[copy-ort] ${main} -> public/ort/ort.js, plus ${runtime.join(', ')}`);
