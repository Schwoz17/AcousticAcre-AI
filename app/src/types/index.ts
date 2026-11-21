export type Diagnosis = {
  id: string;
  domain: 'crop' | 'machine';
  subject: string;
  label: string;
  confidence: number;
  status: 'demo' | 'uncertain' | 'connected' | 'retake' | 'unsupported' | 'error';
  createdAt: string;
  advice: string[];
  diagnosisId?: string;   // stable id, e.g. cassava_mosaic (for analytics / re-translation)
  model?: string;         // e.g. crop-core-1@0.1.0
  lang?: string;          // language code the result was shown in
};
