import type { Diagnosis } from '../types';
import { scanAudio, scanPhoto, type AiResult } from '../ai/engine';

const STATUS: Record<AiResult['kind'], Diagnosis['status']> = {
  diagnosis: 'connected', uncertain: 'uncertain', retake: 'retake', unsupported: 'unsupported', error: 'error',
};

export function toDiagnosis(r: AiResult, subject: string): Diagnosis {
  return {
    id: crypto.randomUUID(), domain: r.domain, subject,
    label: r.kind === 'diagnosis' || r.kind === 'uncertain' ? r.name : (r.reason ?? r.name),
    confidence: Math.round(r.confidence * 100) / 100,
    status: STATUS[r.kind], createdAt: new Date().toISOString(),
    advice: r.steps, diagnosisId: r.diagnosisId, model: r.model, lang: r.lang,
  };
}

/** On-device crop assessment (no upload). */
export async function runCropDiagnosis(file: Blob, crop: string, uiLanguage?: string | null) {
  const result = await scanPhoto(file, crop, uiLanguage);
  return { result, record: toDiagnosis(result, crop) };
}

/** On-device machine sound assessment (no upload). */
export async function runMachineDiagnosis(audio: Blob, kind: string, uiLanguage?: string | null) {
  const result = await scanAudio(audio, kind, uiLanguage);
  return { result, record: toDiagnosis(result, kind) };
}

// Demo adapter kept for UI testing without models.
export async function runDemoDiagnosis(domain: 'crop'|'machine', subject: string): Promise<Diagnosis> {
  await new Promise(resolve => setTimeout(resolve, 1400));
  return { id: crypto.randomUUID(), domain, subject, label: 'Demo analysis — model not connected', confidence: 0, status: 'demo', createdAt: new Date().toISOString(), advice: ['This is a demonstration result, not an agricultural or mechanical diagnosis.', 'Connect the AI inference service before using results to make treatment or repair decisions.', 'If the problem is urgent, contact a qualified extension officer or mechanic.'] };
}
