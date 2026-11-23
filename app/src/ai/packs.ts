/**
 * Install model packs (.aapack) from a file, offline: shared by WhatsApp, Bluetooth, Xender or USB.
 * Every file is checked against the SHA-256 in the pack's manifest; one mismatch rejects the whole pack.
 * Installed files live in Cache Storage under /packs/<type>/ and take priority over the built-in model.
 */
export const PACK_CACHE = 'acousticacre-packs';
export type PackType = 'crop' | 'machine';
export interface PackInfo { pack_id: string; type: PackType; version: string; files: string[] }

// ---- minimal zip reader (stored + deflate), no library needed -------------------
interface ZipEntry { name: string; method: number; size: number; dataStart: number }

function readEntries(buf: ArrayBuffer): ZipEntry[] {
  const v = new DataView(buf);
  let eocd = -1;
  for (let i = buf.byteLength - 22; i >= Math.max(0, buf.byteLength - 66000); i--) {
    if (v.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('This is not a valid pack file (no zip directory found).');
  const count = v.getUint16(eocd + 10, true);
  let p = v.getUint32(eocd + 16, true);
  const dec = new TextDecoder();
  const out: ZipEntry[] = [];
  for (let n = 0; n < count; n++) {
    if (v.getUint32(p, true) !== 0x02014b50) throw new Error('Damaged pack file (bad zip directory).');
    const method = v.getUint16(p + 10, true);
    const size = v.getUint32(p + 20, true);
    const nameLen = v.getUint16(p + 28, true), extraLen = v.getUint16(p + 30, true), commLen = v.getUint16(p + 32, true);
    const local = v.getUint32(p + 42, true);
    const name = dec.decode(new Uint8Array(buf, p + 46, nameLen));
    if (v.getUint32(local, true) !== 0x04034b50) throw new Error('Damaged pack file (bad file header).');
    const dataStart = local + 30 + v.getUint16(local + 26, true) + v.getUint16(local + 28, true);
    out.push({ name, method, size, dataStart });
    p += 46 + nameLen + extraLen + commLen;
  }
  return out;
}

async function extract(buf: ArrayBuffer, e: ZipEntry): Promise<Uint8Array> {
  const raw = new Uint8Array(buf, e.dataStart, e.size);
  if (e.method === 0) return raw.slice();
  if (e.method !== 8) throw new Error(`Unsupported compression in ${e.name}.`);
  const stream = new Blob([raw as unknown as BlobPart]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function sha256hex(bytes: Uint8Array): Promise<string> {
  const d = await crypto.subtle.digest('SHA-256', bytes as unknown as BufferSource);
  return Array.from(new Uint8Array(d), b => b.toString(16).padStart(2, '0')).join('');
}

const SAFE_NAME = /^[A-Za-z0-9._-]{1,100}$/;
const TYPES: string[] = ['crop', 'machine'];

/** Check and install a pack. Throws an Error with a plain-language message if anything is wrong. */
export async function installPack(file: Blob): Promise<PackInfo> {
  if (!('caches' in window)) throw new Error('This browser cannot store packs.');
  const buf = await file.arrayBuffer();
  const entries = readEntries(buf);
  const byName = new Map(entries.map(e => [e.name, e]));
  const mEntry = byName.get('manifest.json');
  if (!mEntry) throw new Error('This pack has no manifest.json.');
  const manifestBytes = await extract(buf, mEntry);
  let manifest: Record<string, any>;
  try { manifest = JSON.parse(new TextDecoder().decode(manifestBytes)); } catch { throw new Error('The pack manifest is not valid JSON.'); }
  if (!TYPES.includes(manifest.type)) throw new Error(`Pack type "${manifest.type}" can't be installed here (crop or machine packs only).`);
  const files: Record<string, string> = manifest.files || {};
  if (!manifest.model || !manifest.labels || !files[manifest.model] || !files[manifest.labels])
    throw new Error('The pack is missing its model or labels.');

  const contents = new Map<string, Uint8Array>();
  for (const [name, expected] of Object.entries(files)) {
    if (!SAFE_NAME.test(name)) throw new Error(`Unsafe file name in pack: ${name}`);
    const e = byName.get(name);
    if (!e) throw new Error(`The pack is missing ${name}.`);
    const bytes = await extract(buf, e);
    const got = await sha256hex(bytes);
    if (got !== String(expected).toLowerCase()) throw new Error(`${name} failed its checksum. The pack is damaged or was changed; it was not installed.`);
    contents.set(name, bytes);
  }

  // Everything verified: replace any earlier pack of this type.
  const type = manifest.type as PackType;
  await removePack(type);
  const cache = await caches.open(PACK_CACHE);
  const put = (name: string, bytes: Uint8Array, ct: string) =>
    cache.put(`/packs/${type}/${name}`, new Response(new Blob([bytes as unknown as BlobPart]), { headers: { 'Content-Type': ct } }));
  for (const [name, bytes] of contents) await put(name, bytes, name.endsWith('.json') ? 'application/json' : 'application/octet-stream');
  await put('manifest.json', manifestBytes, 'application/json');     // written last = install complete
  return { pack_id: manifest.pack_id, type, version: manifest.version, files: [...contents.keys()] };
}

export async function listPacks(): Promise<PackInfo[]> {
  if (!('caches' in window)) return [];
  const cache = await caches.open(PACK_CACHE);
  const out: PackInfo[] = [];
  for (const type of TYPES as PackType[]) {
    const r = await cache.match(`/packs/${type}/manifest.json`);
    if (!r) continue;
    const m = await r.json();
    out.push({ pack_id: m.pack_id, type, version: m.version, files: Object.keys(m.files || {}) });
  }
  return out;
}

export async function removePack(type: PackType): Promise<void> {
  if (!('caches' in window)) return;
  const cache = await caches.open(PACK_CACHE);
  await cache.delete(`/packs/${type}/manifest.json`);                // removed first = pack no longer active
  for (const req of await cache.keys()) {
    if (new URL(req.url).pathname.startsWith(`/packs/${type}/`)) await cache.delete(req);
  }
}

/** Base path the engine should load a model from: an installed pack wins over the built-in one. */
export async function packBase(type: PackType): Promise<string> {
  try {
    if ('caches' in window) {
      const cache = await caches.open(PACK_CACHE);
      if (await cache.match(`/packs/${type}/manifest.json`)) return `/packs/${type}/`;
    }
  } catch { /* storage unavailable: use built-in */ }
  return `/models/${type}/`;
}
