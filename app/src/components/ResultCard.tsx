import { useEffect, useState } from 'react';
import { ArrowRight, CircleAlert, CircleCheck, Info, RefreshCw, Send, ShieldAlert, Volume2, VolumeX } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AiResult, Phrases } from '../ai/engine';
import { phrasesFor } from '../ai/engine';
import { speakResult, stopSpeaking } from '../ai/speech';

const PILL: Record<AiResult['kind'], { text: string; cls: string }> = {
  diagnosis: { text: 'Likely', cls: 'pill-ok' },
  uncertain: { text: 'Not sure', cls: 'pill-warn' },
  retake: { text: 'Retake needed', cls: 'pill-warn' },
  unsupported: { text: 'Not supported yet', cls: 'pill-muted' },
  error: { text: 'Could not run', cls: 'pill-bad' },
};

export default function ResultCard({ result, onRetry }: { result: AiResult; onRetry?: () => void }) {
  const [speaking, setSpeaking] = useState(false);
  const [noVoice, setNoVoice] = useState(false);
  const [phrases, setPhrases] = useState<Phrases | null>(null);
  const voiceOn = localStorage.getItem('acousticacre.voice') !== 'off';
  const pill = PILL[result.kind];

  useEffect(() => {
    phrasesFor(localStorage.getItem('acousticacre.language')).then(setPhrases).catch(() => undefined);
    return () => stopSpeaking();
  }, []);

  useEffect(() => {
    // speak automatically once, if voice guidance is on (voice-first design)
    if (!voiceOn || result.kind === 'error') return;
    setSpeaking(true);
    speakResult(result).then(ok => setNoVoice(!ok)).finally(() => setSpeaking(false));
  }, [result, voiceOn]);

  function toggleSpeak() {
    if (speaking) { stopSpeaking(); setSpeaking(false); return; }
    setSpeaking(true);
    speakResult(result).then(ok => setNoVoice(!ok)).finally(() => setSpeaking(false));
  }

  const showConfidence = result.kind === 'diagnosis';
  const canSend = result.kind === 'diagnosis' || result.kind === 'uncertain';

  /** Agent mode: a mechanic or extension officer relays the result to a farmer by SMS / WhatsApp. */
  async function sendToFarmer() {
    const what = result.domain === 'crop' ? 'crop photo' : 'machine sound';
    const lines = [
      `AcousticAcre AI (${what}): ${result.name}`,
      ...result.steps.map((s, i) => `${i + 1}. ${s}`),
      result.domain === 'crop' ? 'Guidance only. Confirm with an extension officer.' : 'Guidance only. Confirm with a mechanic.',
    ];
    const text = lines.join('\n');
    try {
      if (navigator.share) { await navigator.share({ text }); return; }
    } catch { /* user closed the share sheet */ return; }
    window.location.href = `sms:?&body=${encodeURIComponent(text)}`;
  }
  const isDraftLanguage = phrases && !phrases.reviewed;

  return (
    <div className={`result-card result-${result.kind}`} role="status" aria-live="polite">
      <div className="result-top">
        <span className="result-label">ON-DEVICE RESULT · {result.domain === 'crop' ? 'CROP PHOTO' : 'MACHINE SOUND'}</span>
        <span className={`result-pill ${pill.cls}`}>{pill.text}</span>
      </div>

      <h3>
        {result.kind === 'diagnosis' ? <CircleCheck size={19} /> : <CircleAlert size={19} />}
        {result.kind === 'diagnosis' || result.kind === 'uncertain' ? result.name : result.reason}
      </h3>

      {showConfidence && (
        <div className="confidence-row">
          <div className="confidence-bar"><i style={{ width: `${Math.round(result.confidence * 100)}%` }} /></div>
          <span>{Math.round(result.confidence * 100)}% confidence</span>
        </div>
      )}

      {result.overlay && (
        <figure className="overlay-figure">
          <img src={result.overlay} alt="Leaf with the area the model focused on highlighted" />
          <figcaption>{phrases?.ui.where_model_looked ?? 'Highlighted: where the model looked.'}</figcaption>
        </figure>
      )}

      {result.steps.length > 0 && (
        <ol className="result-steps">{result.steps.map(s => <li key={s}>{s}</li>)}</ol>
      )}

      <div className="result-actions">
        {result.kind !== 'error' && (
          <button type="button" className="secondary-btn" onClick={toggleSpeak}>
            {speaking ? <><VolumeX size={15} /> Stop</> : <><Volume2 size={15} /> Listen</>}
          </button>
        )}
        {canSend && (
          <button type="button" className="secondary-btn" onClick={sendToFarmer}><Send size={15} /> Send to farmer</button>
        )}
        {onRetry && (result.kind === 'retake' || result.kind === 'error' || result.kind === 'uncertain') && (
          <button type="button" className="secondary-btn" onClick={onRetry}><RefreshCw size={15} /> Try again</button>
        )}
      </div>

      {result.kind === 'uncertain' && (
        <div className="uncertain-box"><ShieldAlert size={18} /><span>The model is not confident, so it is not guessing. Show the {result.domain === 'crop' ? 'plant to an extension officer' : 'machine to a mechanic'}.</span></div>
      )}
      {result.domain === 'machine' && result.kind === 'diagnosis' && (
        <div className="uncertain-box"><Info size={18} /><span>Machine-sound checks are experimental (tested on public factory-pump recordings). Always confirm with a mechanic before running or repairing the machine.</span></div>
      )}
      {result.kind !== 'error' && (
        <div className="uncertain-box"><ShieldAlert size={18} /><span>{phrases?.ui.disclaimer ?? 'Guidance, not a guarantee.'} No pesticide doses are given; follow product labels and expert advice.</span></div>
      )}
      {noVoice && (
        <div className="uncertain-box"><Info size={18} /><span>{phrases?.lang_name ?? 'This language'} voice is not installed on this device yet. Please read the result above.</span></div>
      )}
      {isDraftLanguage && (
        <div className="uncertain-box"><Info size={18} /><span>{phrases?.lang_name}: AI-drafted beta, pending native-speaker review.</span></div>
      )}

      <div className="result-foot">
        <span>Model {result.model}{result.ms !== undefined ? ` · result in ${(result.ms / 1000).toFixed(1)} s` : ''} · runs on this device, nothing uploaded</span>
        <Link className="text-link" to="/history">View history <ArrowRight size={15} /></Link>
      </div>
    </div>
  );
}