import { useEffect, useState } from 'react';
import { ArrowRight, CircleAlert, CircleCheck, ImagePlus, Info, RefreshCw, Send, ShieldAlert, ThumbsDown, ThumbsUp, UserRound, Volume2, VolumeX } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AiResult, Phrases } from '../ai/engine';
import { phrasesFor } from '../ai/engine';
import { speakResult, stopSpeaking } from '../ai/speech';
import { setFeedback } from '../services/storage';

const PILL: Record<AiResult['kind'], { text: string; cls: string }> = {
  diagnosis: { text: 'Likely', cls: 'pill-ok' },
  uncertain: { text: 'Not sure', cls: 'pill-warn' },
  retake: { text: 'Retake needed', cls: 'pill-warn' },
  unsupported: { text: 'Not supported yet', cls: 'pill-muted' },
  error: { text: 'Could not run', cls: 'pill-bad' },
};

/** Traffic-light confidence (backlog #6): easier to read than a percentage. */
function trafficLight(r: AiResult): { cls: string; label: string; hint: string } | null {
  if (r.kind === 'uncertain') return { cls: 'tl-red', label: 'Not sure', hint: 'Ask an expert before acting.' };
  if (r.kind !== 'diagnosis') return null;
  if (r.confidence >= 0.8) return { cls: 'tl-green', label: 'High confidence', hint: 'Follow the steps below.' };
  return { cls: 'tl-amber', label: 'Medium confidence', hint: 'Follow the steps, and check with an expert if you can.' };
}

interface Props {
  result: AiResult;
  onRetry?: () => void;
  /** Crop only: ask for a second photo from another angle when the result is "not sure" (backlog #5). */
  onAddAngle?: () => void;
  /** History record id, so "Was this right?" can be saved with it (backlog #2). */
  recordId?: string;
  /** The photo or recording, attached when asking an expert (backlog #26). */
  media?: File | Blob | null;
  subject?: string;
}

export default function ResultCard({ result, onRetry, onAddAngle, recordId, media, subject }: Props) {
  const [speaking, setSpeaking] = useState(false);
  const [noVoice, setNoVoice] = useState(false);
  const [phrases, setPhrases] = useState<Phrases | null>(null);
  const [feedback, setFb] = useState<'correct' | 'wrong' | null>(null);
  const voiceOn = localStorage.getItem('acousticacre.voice') !== 'off';
  const pill = PILL[result.kind];
  const light = trafficLight(result);

  useEffect(() => {
    phrasesFor(localStorage.getItem('acousticacre.language')).then(setPhrases).catch(() => undefined);
    return () => stopSpeaking();
  }, []);

  useEffect(() => {
    setFb(null);
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

  const canSend = result.kind === 'diagnosis' || result.kind === 'uncertain';
  const what = result.domain === 'crop' ? `crop photo${subject ? ` (${subject})` : ''}` : `machine sound${subject ? ` (${subject})` : ''}`;
  const expert = result.domain === 'crop' ? 'extension officer' : 'mechanic';

  async function share(text: string, withMedia: boolean) {
    try {
      if (withMedia && media && navigator.share) {
        const ext = media.type.includes('png') ? 'png' : media.type.startsWith('image/') ? 'jpg' : media.type.includes('mp4') ? 'm4a' : 'webm';
        const file = media instanceof File ? media : new File([media], `acousticacre-${result.domain}.${ext}`, { type: media.type });
        if (navigator.canShare?.({ files: [file] })) { await navigator.share({ text, files: [file] }); return; }
      }
      if (navigator.share) { await navigator.share({ text }); return; }
    } catch { return; /* user closed the share sheet */ }
    window.location.href = `sms:?&body=${encodeURIComponent(text)}`;
  }

  /** Agent mode: relay the result to a farmer by SMS / WhatsApp. */
  function sendToFarmer() {
    const lines = [
      `AcousticAcre AI (${what}): ${result.name}`,
      ...result.steps.map((s, i) => `${i + 1}. ${s}`),
      result.domain === 'crop' ? 'Guidance only. Confirm with an extension officer.' : 'Guidance only. Confirm with a mechanic.',
    ];
    share(lines.join('\n'), false);
  }

  /** Human escalation (backlog #26): send the photo or sound to an expert when the app is unsure. */
  function askExpert() {
    const text = [
      `Hello, can you help? AcousticAcre AI was not sure about this ${what}.`,
      result.kind === 'diagnosis' ? `Its best guess: ${result.name} (${Math.round(result.confidence * 100)}%).` : '',
      media ? `The ${result.domain === 'crop' ? 'photo' : 'recording'} is attached.` : '',
      'What do you think it is, and what should I do?',
    ].filter(Boolean).join('\n');
    share(text, true);
  }

  function answer(v: 'correct' | 'wrong') {
    setFb(v);
    if (recordId) setFeedback(recordId, v);
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

      {light && (
        <div className={`traffic-light ${light.cls}`}>
          <span className="tl-dots" aria-hidden="true"><i className="tl-r" /><i className="tl-a" /><i className="tl-g" /></span>
          <span><b>{light.label}</b> · {light.hint}{result.kind === 'diagnosis' ? <small> ({Math.round(result.confidence * 100)}%)</small> : null}</span>
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
        {result.kind === 'uncertain' && onAddAngle && (
          <button type="button" className="primary-btn small-btn" onClick={onAddAngle}><ImagePlus size={15} /> Add a photo from another angle</button>
        )}
        {result.kind === 'uncertain' && (
          <button type="button" className="secondary-btn" onClick={askExpert}><UserRound size={15} /> Ask an expert</button>
        )}
        {canSend && (
          <button type="button" className="secondary-btn" onClick={sendToFarmer}><Send size={15} /> Send to farmer</button>
        )}
        {onRetry && (result.kind === 'retake' || result.kind === 'error' || result.kind === 'uncertain') && (
          <button type="button" className="secondary-btn" onClick={onRetry}><RefreshCw size={15} /> Try again</button>
        )}
      </div>

      {result.kind === 'diagnosis' && (
        <div className="feedback-row">
          {feedback === null ? (
            <>
              <span>Was this right?</span>
              <button type="button" className="fb-btn fb-yes" onClick={() => answer('correct')} aria-label="Yes, this was right"><ThumbsUp size={16} /> Yes</button>
              <button type="button" className="fb-btn fb-no" onClick={() => answer('wrong')} aria-label="No, this was wrong"><ThumbsDown size={16} /> No</button>
            </>
          ) : feedback === 'correct' ? (
            <span>Thank you. Your answer is saved on this phone and helps us measure accuracy.</span>
          ) : (
            <span>Thank you. Please <button type="button" className="text-link" onClick={askExpert}>ask {expert === 'mechanic' ? 'a mechanic' : 'an extension officer'}</button> before acting.</span>
          )}
        </div>
      )}

      {result.kind === 'uncertain' && (
        <div className="uncertain-box"><ShieldAlert size={18} /><span>The model is not confident, so it is not guessing. {onAddAngle ? 'Try one more photo from another angle, or show' : 'Show'} the {result.domain === 'crop' ? 'plant to an extension officer' : 'machine to a mechanic'}.</span></div>
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
        <span>
          Model {result.model}
          {result.photos && result.photos > 1 ? ` · ${result.photos} photos combined` : ''}
          {result.ms !== undefined ? ` · result in ${(result.ms / 1000).toFixed(1)} s` : ''}
          {' · runs on this device, nothing uploaded'}
        </span>
        <Link className="text-link" to="/history">View history <ArrowRight size={15} /></Link>
      </div>
    </div>
  );
}
