import type { Diagnosis } from '../types';

const KEY = 'acousticacre.history.v1';
export const HISTORY_UPDATED_EVENT = 'acousticacre:history-updated';

export function getHistory(): Diagnosis[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is Diagnosis =>
      Boolean(item) &&
      typeof item.id === 'string' &&
      (item.domain === 'crop' || item.domain === 'machine') &&
      typeof item.subject === 'string' &&
      typeof item.createdAt === 'string'
    );
  } catch {
    return [];
  }
}

export function saveDiagnosis(item: Diagnosis): void {
  const next = [item, ...getHistory()].slice(0, 50);
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event(HISTORY_UPDATED_EVENT));
}

export function clearHistory(): void {
  localStorage.removeItem(KEY);
  window.dispatchEvent(new Event(HISTORY_UPDATED_EVENT));
}

/** Record the farmer's answer to "Was this right?" on a saved result (kept on this phone only). */
export function setFeedback(id: string, feedback: 'correct' | 'wrong'): void {
  const next = getHistory().map(item => item.id === id ? { ...item, feedback, feedbackAt: new Date().toISOString() } : item);
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new Event(HISTORY_UPDATED_EVENT));
}
