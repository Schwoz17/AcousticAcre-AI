/* AcousticAcre AI worker: runs ONNX models off the main thread so the screen never freezes.
   Plain (classic) worker so it can load ONNX Runtime with importScripts, exactly like the page does.
   Messages in:  {id, op:'create', key, model:ArrayBuffer} | {id, op:'run', key, feeds:{name:{data,dims}}}
   Messages out: {id, ok:true, out?} | {id, ok:false, error} */
let ready = null;
function init() {
  if (!ready) {
    ready = new Promise((resolve, reject) => {
      try {
        importScripts('/ort/ort.js');
        self.ort.env.wasm.wasmPaths = '/ort/';
        self.ort.env.wasm.numThreads = 1;
        resolve(self.ort);
      } catch (e) { reject(e); }
    });
  }
  return ready;
}

const sessions = {};

self.onmessage = async (e) => {
  const { id, op, key } = e.data;
  try {
    const ort = await init();
    if (op === 'create') {
      sessions[key] = await ort.InferenceSession.create(new Uint8Array(e.data.model), { executionProviders: ['wasm'] });
      self.postMessage({ id, ok: true });
    } else if (op === 'run') {
      const s = sessions[key];
      if (!s) throw new Error('No model loaded for ' + key);
      const feeds = {};
      for (const [name, t] of Object.entries(e.data.feeds)) feeds[name] = new ort.Tensor('float32', t.data, t.dims);
      const res = await s.run(feeds);
      const out = {}, transfer = [];
      for (const [name, t] of Object.entries(res)) {
        const data = new Float32Array(t.data);           // own copy, so its buffer can be transferred
        out[name] = { data, dims: Array.from(t.dims) };
        transfer.push(data.buffer);
      }
      self.postMessage({ id, ok: true, out }, transfer);
    } else {
      throw new Error('Unknown op ' + op);
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: String((err && err.message) || err) });
  }
};
