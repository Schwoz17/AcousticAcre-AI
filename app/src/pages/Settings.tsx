import { useEffect, useRef, useState } from 'react';
import { Bell, Gauge, Globe2, HardDrive, LogOut, Package, ShieldCheck, SlidersHorizontal, Trash2, Upload, Volume2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { signOut } from '../services/profile';
import { clearHistory } from '../services/storage';
import { activeModel, resetPacks } from '../ai/engine';
import { installPack, listPacks, removePack, type PackInfo } from '../ai/packs';

export default function Settings() {
  const [language, setLanguage] = useState(localStorage.getItem('acousticacre.language') || 'English');
  const [alerts, setAlerts] = useState(localStorage.getItem('acousticacre.alerts') !== 'off');
  const [voice, setVoice] = useState(localStorage.getItem('acousticacre.voice') !== 'off');
  const [models, setModels] = useState<{ crop: string; machine: string }>({ crop: '…', machine: '…' });
  const [packs, setPacks] = useState<PackInfo[]>([]);
  const [packMsg, setPackMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [storage, setStorage] = useState('Checking…');
  const [cleared, setCleared] = useState(false);
  const packInput = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  async function refreshPacks() {
    setPacks(await listPacks());
    const [crop, machine] = await Promise.all([activeModel('crop').catch(() => 'not loaded'), activeModel('machine').catch(() => 'not loaded')]);
    setModels({ crop, machine });
  }

  useEffect(() => {
    refreshPacks();
    (async () => {
      if (!navigator.storage?.estimate) { setStorage('Storage information is not available in this browser.'); return; }
      const [est, persisted] = await Promise.all([navigator.storage.estimate(), navigator.storage.persisted?.() ?? Promise.resolve(false)]);
      const mb = (n?: number) => ((n ?? 0) / 1048576).toFixed(1);
      setStorage(`${mb(est.usage)} MB used. ${persisted ? 'Protected: the browser will not clear it automatically.' : 'Not protected yet: the browser may clear it when the phone is low on space. Installing the app to the home screen helps.'}`);
    })();
  }, []);

  function changeLanguage(v: string) { setLanguage(v); localStorage.setItem('acousticacre.language', v); }
  function logout() { signOut(); navigate('/signin'); }

  async function onPack(file?: File) {
    if (!file) return;
    setPackMsg({ ok: true, text: 'Checking the pack…' });
    try {
      const info = await installPack(file);
      resetPacks();
      setPackMsg({ ok: true, text: `Installed ${info.pack_id} version ${info.version}. Every file passed its checksum.` });
    } catch (e) {
      setPackMsg({ ok: false, text: e instanceof Error ? e.message : 'The pack could not be installed.' });
    }
    if (packInput.current) packInput.current.value = '';
    refreshPacks();
  }

  async function onRemove(type: PackInfo['type']) {
    await removePack(type);
    resetPacks();
    setPackMsg({ ok: true, text: `Removed the ${type} pack. The built-in model is used again.` });
    refreshPacks();
  }

  return (
    <div className="page-stack narrow-page">
      <div className="page-intro"><div className="eyebrow">MAKE IT WORK FOR YOU</div><h1>Settings</h1><p>Manage your experience on this device.</p></div>
      <section className="settings-panel">
        <div className="settings-row"><div className="settings-icon"><Globe2 /></div><div className="settings-copy"><b>Language</b><span>Choose your preferred display language.</span></div>
          <select value={language} onChange={e => changeLanguage(e.target.value)}><option>English</option><option>Hausa</option><option>Yoruba</option><option>Igbo</option><option>French</option><option>Swahili</option></select></div>
        <div className="settings-row"><div className="settings-icon"><Bell /></div><div className="settings-copy"><b>Notifications</b><span>Allow product and activity reminders when supported.</span></div>
          <button className={`toggle ${alerts ? 'on' : ''}`} onClick={() => { setAlerts(!alerts); localStorage.setItem('acousticacre.alerts', alerts ? 'off' : 'on'); }} aria-label="Toggle notifications"><i /></button></div>
        <div className="settings-row"><div className="settings-icon"><Volume2 /></div><div className="settings-copy"><b>Voice guidance</b><span>Read results out loud automatically.</span></div>
          <button className={`toggle ${voice ? 'on' : ''}`} onClick={() => { setVoice(!voice); localStorage.setItem('acousticacre.voice', voice ? 'off' : 'on'); }} aria-label="Toggle voice guidance"><i /></button></div>
        <div className="settings-row"><div className="settings-icon"><SlidersHorizontal /></div><div className="settings-copy"><b>Profile information</b><span>Update your farm and personal details.</span></div><Link to="/profile" className="settings-link">Edit profile</Link></div>
      </section>

      <section className="settings-panel">
        <div className="settings-row settings-row-top"><div className="settings-icon"><Package /></div>
          <div className="settings-copy"><b>AI model packs</b>
            <span>Crop model: {models.crop}</span>
            <span>Machine model: {models.machine}</span>
            <span>Install a new or updated model from a <code>.aapack</code> file shared by WhatsApp, Bluetooth or USB. No internet needed. Every file is checked before it is used.</span>
            {packs.map(p => (
              <span key={p.type} className="pack-line">{p.pack_id} {p.version} installed <button type="button" className="text-link" onClick={() => onRemove(p.type)}>Remove</button></span>
            ))}
            {packMsg && <span className={packMsg.ok ? 'pack-ok' : 'pack-bad'} role="status">{packMsg.text}</span>}
          </div>
          <button type="button" className="secondary-btn" onClick={() => packInput.current?.click()}><Upload size={15} /> Install pack</button>
          <input ref={packInput} type="file" accept=".aapack,application/zip" hidden onChange={e => onPack(e.target.files?.[0])} />
        </div>
        <div className="settings-row"><div className="settings-icon"><HardDrive /></div><div className="settings-copy"><b>Offline storage</b><span>{storage}</span></div></div>
        <div className="settings-row"><div className="settings-icon"><Gauge /></div><div className="settings-copy"><b>Speed test</b><span>Measure how fast the AI runs on this phone.</span></div><Link to="/speed" className="settings-link">Run test</Link></div>
      </section>

      <section className="settings-panel">
        <div className="settings-row settings-row-top"><div className="settings-icon"><ShieldCheck /></div>
          <div className="settings-copy"><b>Privacy and your data</b>
            <span>Photos and sounds are analysed on this phone and are never uploaded.</span>
            <span>Your scan history is kept only on this phone. You can delete it at any time.</span>
            <span>If you use the USSD or SMS service, we keep your phone number only in scrambled (hashed) form, with your answers, for 30 days, then delete it. We never sell data.</span>
          </div>
          <button type="button" className="secondary-btn danger-btn" onClick={() => { clearHistory(); setCleared(true); }}><Trash2 size={15} /> {cleared ? 'History deleted' : 'Delete history'}</button>
        </div>
      </section>

      <div className="settings-logout"><div><b>Sign out of this device</b><span>End your local prototype session.</span></div><button className="secondary-btn danger-btn" onClick={logout}><LogOut size={15} /> Sign out</button></div>
    </div>
  );
}
