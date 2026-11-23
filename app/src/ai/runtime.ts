/**
 * Where models run. Preferred: a background worker (/ai-worker.js), so the screen stays responsive.
 * If the worker can't start on this browser, the same model runs on the main thread instead.
 * Callers only see createSession() and session.run(); both paths take and return plain arrays.
 */
export interface Feed { data: Float32Array; dims: number[] }
export interface Session {
  backend: 'worker' | 'main';
  run(feeds: Record<string, Feed>): Promise<Record<string, Feed>>;
}

// Minimal typing for the global `ort` from /ort/ort.js (onnxruntime-web).
interface OrtTensorLike { data: Float32Array; dims: readonly number[] }
interface OrtGlobal {
  env: { wasm: { wasmPaths: string; numThreads: number } };
  Tensor: new (type: string, data: Float32Array, dims: number[]) => unknown;
  InferenceSession: {
    create(model: Uint8Array | string, opts?: Record<string, unknown>): Promise<{ run(f: Record<string, unknown>): Promise<Record<string, OrtTensorLike>> }>;
  };
}
declare global { interface Window { ort?: OrtGlobal } }

function getOrt(): OrtGlobal {
  const ort = window.ort;
  if (!ort) throw new Error('AI engine not loaded. Run "npm install" (it copies ONNX Runtime into public/ort) and reload.');
  ort.env.wasm.wasmPaths = '/ort/';
  ort.env.wasm.numThreads = 1;          // no SharedArrayBuffer / special headers needed
  return ort;
}

async function mainSession(model: ArrayBuffer): Promise<Session> {
  const ort = getOrt();
  const s = await ort.InferenceSession.create(new Uint8Array(model), { executionProviders: ['wasm'] });
  return {
    backend: 'main',
    async run(feeds) {
      const f: Record<string, unknown> = {};
      for (const [k, t] of Object.entries(feeds)) f[k] = new ort.Tensor('float32', t.data, t.dims);
      const res = await s.run(f);
      const out: Record<string, Feed> = {};
      for (const [k, t] of Object.entries(res)) out[k] = { data: t.data, dims: Array.from(t.dims) };
      return out;
    },
  };
}

// ---- worker client ----------------------------------------------------------
let worker: Worker | null = null;
let workerBroken = false;
let nextId = 1;
const pending = new Map<number, { resolve: (v: { out?: Record<string, Feed> }) => void; reject: (e: Error) => void }>();

function getWorker(): Worker | null {
  if (workerBroken || typeof Worker === 'undefined') return null;
  if (!worker) {
    try {
      worker = new Worker('/ai-worker.js');
      worker.onmessage = (e: MessageEvent) => {
        const p = pending.get(e.data.id);
        if (!p) return;
        pending.delete(e.data.id);
        if (e.data.ok) p.resolve(e.data); else p.reject(new Error(e.data.error));
      };
      worker.onerror = () => { workerBroken = true; for (const p of pending.values()) p.reject(new Error('AI worker failed')); pending.clear(); };
    } catch {
      workerBroken = true;
      return null;
    }
  }
  return worker;
}

function call(msg: Record<string, unknown>, transfer: Transferable[] = [], timeoutMs = 30000) {
  const w = getWorker();
  if (!w) return Promise.reject(new Error('no worker'));
  const id = nextId++;
  return new Promise<{ out?: Record<string, Feed> }>((resolve, reject) => {
    const t = setTimeout(() => { pending.delete(id); reject(new Error('AI worker timed out')); }, timeoutMs);
    pending.set(id, { resolve: v => { clearTimeout(t); resolve(v); }, reject: e => { clearTimeout(t); reject(e); } });
    w.postMessage({ id, ...msg }, transfer);
  });
}

/** Load a model (bytes). Tries the background worker first, falls back to the main thread. */
export async function createSession(key: string, model: ArrayBuffer): Promise<Session> {
  try {
    const copy = model.slice(0);                       // the worker takes ownership of this copy
    await call({ op: 'create', key, model: copy }, [copy], 60000);
    return {
      backend: 'worker',
      async run(feeds) {
        const plain: Record<string, Feed> = {};
        for (const [k, t] of Object.entries(feeds)) plain[k] = { data: t.data, dims: t.dims };
        const r = await call({ op: 'run', key, feeds: plain });
        return r.out ?? {};
      },
    };
  } catch {
    workerBroken = true;                                // don't keep retrying a broken worker
    return mainSession(model);
  }
}
