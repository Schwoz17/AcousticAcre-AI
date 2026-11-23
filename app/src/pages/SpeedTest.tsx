import { useState } from 'react';
import { ArrowLeft, Copy, Gauge, LoaderCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { benchmark, type BenchResult } from '../ai/engine';

/** Technical Documentation section 13: 50 runs per model after warm-up; report median (p50) and worst-case (p95). */
export default function SpeedTest() {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<BenchResult[]>([]);
  const [err, setErr] = useState('');
  const [copied, setCopied] = useState(false);
  const nav = navigator as Navigator & { deviceMemory?: number };
  const device = `${navigator.userAgent} · ${navigator.hardwareConcurrency ?? '?'} CPU cores · ${nav.deviceMemory ?? '?'} GB RAM (browser estimate)`;

  async function run() {
    setBusy(true); setErr(''); setRes([]); setCopied(false);
    try {
      const crop = await benchmark('crop', 50);
      setRes([crop]);
      const machine = await benchmark('machine', 50);
      setRes([crop, machine]);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'The test could not run.');
    } finally {
      setBusy(false);
    }
  }

  const report = [
    `AcousticAcre speed test, ${new Date().toISOString()}`,
    device,
    ...res.map(r => `${r.model}: median ${r.p50.toFixed(0)} ms, 95th percentile ${r.p95.toFixed(0)} ms, mean ${r.mean.toFixed(0)} ms over ${r.runs} runs (${r.backend === 'worker' ? 'background worker' : 'main thread'}; load ${r.loadMs.toFixed(0)} ms)`),
  ].join('\n');

  return (
    <div className="page-stack narrow-page">
      <div className="back-row"><Link to="/settings" className="back-link"><ArrowLeft size={16} /> Back to settings</Link></div>
      <div className="page-intro"><div className="eyebrow">MEASURE</div><h1>Speed test</h1>
        <p>Runs each AI model 50 times on this phone after a short warm-up, and reports the typical time (median) and the slow-case time (95th percentile). Model time only; photo and sound preparation add a little more.</p></div>
      <section className="form-panel">
        <button className="primary-btn full-btn" onClick={run} disabled={busy}>
          {busy ? <><LoaderCircle className="spin" size={18} /> Testing… keep this screen open</> : <><Gauge size={18} /> Run speed test</>}
        </button>
        {err && <p className="auth-error" role="alert">{err}</p>}
        {res.length > 0 && (
          <table className="speed-table">
            <thead><tr><th>Model</th><th>Median</th><th>95th pct</th><th>Runs on</th></tr></thead>
            <tbody>{res.map(r => (
              <tr key={r.model}><td>{r.model}</td><td>{r.p50.toFixed(0)} ms</td><td>{r.p95.toFixed(0)} ms</td><td>{r.backend === 'worker' ? 'Background worker' : 'Main thread'}</td></tr>
            ))}</tbody>
          </table>
        )}
        <p className="support-note">{device}</p>
        {res.length === 2 && (
          <button className="secondary-btn" onClick={() => { navigator.clipboard?.writeText(report).then(() => setCopied(true)); }}>
            <Copy size={15} /> {copied ? 'Copied' : 'Copy results'}
          </button>
        )}
      </section>
    </div>
  );
}
