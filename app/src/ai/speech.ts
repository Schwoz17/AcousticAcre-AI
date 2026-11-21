/**
 * Speak a result offline. Prefers pre-generated clips (/clips/<lang>/<id>.mp3, made by
 * tools/make_clips.py). If a clip is missing, falls back to the device's built-in voice, but
 * only if the device really has a voice for that language. Reading Hausa with an English voice
 * is worse than silence, so in that case nothing is spoken and the caller shows a note.
 */
import type { AiResult } from './engine';

let current: HTMLAudioElement | null = null;

function playClip(url: string): Promise<boolean> {
  return new Promise(resolve => {
    const a = new Audio(url);
    current = a;
    a.onended = () => resolve(true);
    a.onerror = () => resolve(false);
    a.play().catch(() => resolve(false));
  });
}

/** Device voices load asynchronously; wait briefly for them. */
function getVoices(): Promise<SpeechSynthesisVoice[]> {
  return new Promise(resolve => {
    if (!('speechSynthesis' in window)) return resolve([]);
    const now = window.speechSynthesis.getVoices();
    if (now.length) return resolve(now);
    const done = () => resolve(window.speechSynthesis.getVoices());
    window.speechSynthesis.addEventListener('voiceschanged', done, { once: true });
    setTimeout(done, 1000);
  });
}

async function voiceFor(lang: string): Promise<SpeechSynthesisVoice | null> {
  const voices = await getVoices();
  const want = lang.toLowerCase();
  return voices.find(v => v.lang.toLowerCase() === `${want}-ng`)
      ?? voices.find(v => v.lang.toLowerCase().startsWith(want))
      ?? null;
}

function sayText(text: string, voice: SpeechSynthesisVoice): Promise<void> {
  return new Promise(resolve => {
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = 0.95;
    u.onend = () => resolve();
    u.onerror = () => resolve();
    window.speechSynthesis.speak(u);
  });
}

export function stopSpeaking(): void {
  current?.pause();
  current = null;
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}

/** Returns false when there was no way to speak this language on this device. */
export async function speakResult(r: AiResult): Promise<boolean> {
  stopSpeaking();
  const texts = r.kind === 'diagnosis' || r.kind === 'uncertain' ? [r.name, ...r.steps] : [r.reason ?? r.name];
  // 1) pre-recorded clips (real Hausa voice), if they are all there
  if (r.clipIds.length) {
    let ok = true;
    for (const id of r.clipIds) {
      ok = await playClip(`/clips/${r.lang}/${id}.mp3`);
      if (!ok) break;
    }
    if (ok) return true;
  }
  // 2) the device's own voice, only if it has one for this language
  const voice = await voiceFor(r.lang);
  if (!voice) return false;
  for (const t of texts) await sayText(t, voice);
  return true;
}