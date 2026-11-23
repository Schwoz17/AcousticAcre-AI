import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, AudioLines, Check, FileAudio, LoaderCircle, Mic, RefreshCw, ShieldAlert, Square, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import { runMachineDiagnosis } from '../services/diagnosis';
import { saveDiagnosis } from '../services/storage';
import { preload, SUPPORTED_MACHINES, type AiResult } from '../ai/engine';
import ResultCard from '../components/ResultCard';

const machineKinds = ['Irrigation pump', 'Generator / small engine', 'Tractor', 'Other farm equipment'];
const MAX_AUDIO_BYTES = 20 * 1024 * 1024;

export default function MachineDiagnosis() {
  const [kind, setKind] = useState(machineKinds[0]);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [audioUrl, setAudioUrl] = useState('');
  const [audioName, setAudioName] = useState('');
  const [audioError, setAudioError] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AiResult | null>(null);
  const [recordId, setRecordId] = useState<string | undefined>();
  const [levels, setLevels] = useState<number[]>(() => Array(34).fill(0));
  const [coach, setCoach] = useState('');
  const meter = useRef<{ ctx: AudioContext; raf: number } | null>(null);
  const audioBlob = useRef<Blob | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const stream = useRef<MediaStream | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => { preload('machine'); }, []);

  function setAudio(blob: Blob, name: string) {
    audioBlob.current = blob;
    setAudioUrl(current => {
      if (current) URL.revokeObjectURL(current);
      return URL.createObjectURL(blob);
    });
    setAudioName(name);
    setAudioError('');
    setResult(null);
  }

  function clearAudio() {
    setAudioUrl(current => {
      if (current) URL.revokeObjectURL(current);
      return '';
    });
    setAudioName('');
    audioBlob.current = null;
    setSeconds(0);
    if (fileInput.current) fileInput.current.value = '';
  }

  /** Live level meter + recording coach (backlog #4): real microphone levels, plain advice while recording. */
  function startMeter(mediaStream: MediaStream) {
    try {
      const AC: typeof AudioContext = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AC();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      ctx.createMediaStreamSource(mediaStream).connect(analyser);
      const buf = new Float32Array(analyser.fftSize);
      let last = 0, quiet = 0, loud = 0, frames = 0;
      const hist: number[] = Array(34).fill(0);
      const tick = (t: number) => {
        analyser.getFloatTimeDomainData(buf);
        let sum = 0, peak = 0;
        for (let i = 0; i < buf.length; i++) { const v = Math.abs(buf[i]); sum += v * v; if (v > peak) peak = v; }
        const rms = Math.sqrt(sum / buf.length);
        frames++; if (rms < 0.01) quiet++; if (peak > 0.98) loud++;
        if (t - last > 100) {                                   // update the screen ~10 times a second
          hist.shift(); hist.push(Math.min(1, rms * 8));
          setLevels([...hist]);
          setCoach(loud / frames > 0.05 ? 'Too loud: move the phone back a little.'
            : quiet / frames > 0.6 ? 'Too quiet: move closer to the machine.'
            : 'Good: hold the phone steady.');
          last = t; quiet = 0; loud = 0; frames = 0;
        }
        if (meter.current) meter.current.raf = requestAnimationFrame(tick);
      };
      meter.current = { ctx, raf: requestAnimationFrame(tick) };
    } catch { /* level meter is optional */ }
  }

  function stopMeter() {
    if (!meter.current) return;
    cancelAnimationFrame(meter.current.raf);
    meter.current.ctx.close().catch(() => undefined);
    meter.current = null;
  }

  function stopRecording() {
    stopMeter();
    if (recorder.current?.state === 'recording') recorder.current.stop();
    setRecording(false);
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
  }

  useEffect(() => {
    if (!recording) return;
    const timer = window.setInterval(() => {
      setSeconds(current => {
        if (current >= 4) {
          window.setTimeout(stopRecording, 0);
          return 5;
        }
        return current + 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(() => () => {
    stopMeter();
    stream.current?.getTracks().forEach(track => track.stop());
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  async function startRecording() {
    setAudioError('');
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setAudioError('Audio recording is not supported in this browser. Try uploading an audio file instead.');
      return;
    }
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = mediaStream;
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(type => MediaRecorder.isTypeSupported(type));
      const mediaRecorder = new MediaRecorder(mediaStream, mimeType ? { mimeType } : undefined);
      recorder.current = mediaRecorder;
      chunks.current = [];
      mediaRecorder.ondataavailable = event => { if (event.data.size) chunks.current.push(event.data); };
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: mediaRecorder.mimeType || 'audio/webm' });
        if (blob.size) setAudio(blob, `Machine recording (${new Date().toLocaleTimeString()})`);
        mediaStream.getTracks().forEach(track => track.stop());
      };
      mediaRecorder.start();
      setSeconds(0);
      clearAudio();
      setCoach('');
      startMeter(mediaStream);
      setRecording(true);
    } catch {
      setAudioError('Microphone access was not granted. Allow microphone access or upload a recording.');
      stream.current?.getTracks().forEach(track => track.stop());
      stream.current = null;
    }
  }

  function uploadAudio(file?: File) {
    if (!file) return;
    if (!file.type.startsWith('audio/')) { setAudioError('Choose a supported audio file.'); return; }
    if (file.size > MAX_AUDIO_BYTES) { setAudioError('The audio file must be 20 MB or smaller.'); return; }
    setAudio(new Blob([file], { type: file.type }), file.name);
  }

  async function analyse() {
    if (!audioUrl || !audioBlob.current || busy) return;
    setBusy(true);
    setAudioError('');
    try {
      const { result: r, record } = await runMachineDiagnosis(audioBlob.current, kind, localStorage.getItem('acousticacre.language'));
      if (r.kind === 'diagnosis' || r.kind === 'uncertain') { saveDiagnosis(record); setRecordId(record.id); } else setRecordId(undefined);
      setResult(r);
    } catch {
      setAudioError('The sound could not be analysed. Please record again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack narrow-page">
      <div className="back-row"><Link to="/dashboard" className="back-link"><ArrowLeft size={16}/> Back to overview</Link><span className="step-label">MACHINE CHECK · STEP 1 OF 2</span></div>
      <div className="page-intro"><div className="eyebrow">MACHINE HEALTH</div><h1>Listen to your machine.</h1><p>Record a short sample while the machine is running normally, or upload an existing recording. Keep a safe distance from moving parts.</p></div>
      <section className="form-panel">
        <div className="field-label">1. What are you checking?</div>
        <div className="machine-options">{machineKinds.map((machine, index) => <button type="button" key={machine} className={`machine-option ${kind===machine?'selected':''}`} onClick={()=>{setKind(machine);setResult(null);}}><span>{['💧','⚙️','🚜','🔧'][index]}</span><b>{machine}{!SUPPORTED_MACHINES.includes(machine)&&<small style={{display:'block',fontWeight:500,color:'#8a978c'}}>Coming soon</small>}</b>{kind===machine&&<Check size={16}/>}</button>)}</div>
        <div className="field-label recorder-label">2. Record or upload machine sound</div>
        <div className={`recorder ${recording?'is-recording':''}`}>
          <div className="mic-orb">{recording?<AudioLines size={30}/>:<Mic size={30}/>}</div>
          <div className="record-time">00:0{seconds}<span> / 00:05</span></div>
          <div className="wave-bars" aria-label={recording ? 'Live microphone level' : undefined}>{levels.map((lv,index)=><i key={index} style={{height:`${recording?6+lv*66:8+Math.abs(Math.sin(index*1.7))*15}px`}}/>)}</div>
          <div className="record-caption" aria-live="polite">{recording?(coach||'Recording… keep the phone steady'):audioUrl?'Audio sample ready':'Ready when your machine is running'}</div>
          <div className="record-controls">
            {!recording&&<button type="button" className="record-btn" onClick={startRecording}><Mic size={17}/> Record 5 seconds</button>}
            {recording&&<button type="button" className="stop-btn" onClick={stopRecording}><Square size={15} fill="currentColor"/> Stop recording</button>}
            {!recording&&<button type="button" className="secondary-btn" onClick={()=>fileInput.current?.click()}><UploadCloud size={15}/> Upload audio</button>}
            <input ref={fileInput} type="file" accept="audio/*" hidden onChange={event=>uploadAudio(event.target.files?.[0])}/>
          </div>
        </div>
        {audioUrl&&<div className="audio-selected"><div><FileAudio size={17}/><span>{audioName}</span></div><audio controls src={audioUrl}/><button type="button" className="text-link" onClick={clearAudio}>Remove audio</button></div>}
        {audioError&&<p className="auth-error" role="alert">{audioError}</p>}
        <div className="quality-hint"><ShieldAlert size={17}/><span>Record in a safe location. Avoid touching moving parts. Wind and handling noise can affect audio quality. Supported upload limit: 20 MB.</span></div>
        <button className="primary-btn full-btn" disabled={!audioUrl||recording||busy} onClick={analyse}>{busy?<><LoaderCircle className="spin" size={18}/> Listening on this phone…</>:<>Analyse sound <ArrowRight size={17}/></>}</button>
        {result&&<ResultCard result={result} onRetry={clearAudio} recordId={recordId} media={audioBlob.current} subject={kind}/>}
      </section>
      <div className="privacy-note"><ShieldAlert size={16}/> Audio is analysed on this phone and never uploaded. Works offline after the first visit.</div>
    </div>
  );
}
