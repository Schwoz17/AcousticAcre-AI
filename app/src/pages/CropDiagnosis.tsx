import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeft, ArrowRight, Check, ImagePlus, LoaderCircle, RefreshCw,
  ShieldAlert, UploadCloud
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { runCropDiagnosis } from '../services/diagnosis';
import { saveDiagnosis } from '../services/storage';
import { getProfile } from '../services/profile';
import { preload, SUPPORTED_CROPS, type AiResult } from '../ai/engine';
import ResultCard from '../components/ResultCard';

// Keep this catalogue aligned with the crops offered during farmer onboarding.
// A farmer's own selections are shown first, followed by other available choices.
const cropCatalogue = [
  'Cassava', 'Maize', 'Tomato', 'Rice', 'Yam', 'Cocoa',
  'Beans / Cowpea', 'Groundnut', 'Soybean', 'Pepper', 'Okra',
  'Plantain', 'Millet', 'Sorghum', 'Vegetables', 'Other'
];

const cropEmojis: Record<string, string> = {
  Cassava: '🌿',
  Maize: '🌽',
  Tomato: '🍅',
  Rice: '🌾',
  Yam: '🍠',
  Cocoa: '🌳',
  'Beans / Cowpea': '🫘',
  Groundnut: '🥜',
  Soybean: '🫘',
  Pepper: '🌶️',
  Okra: '🥬',
  Plantain: '🍌',
  Millet: '🌾',
  Sorghum: '🌾',
  Vegetables: '🥬',
  Other: '🌱'
};

export default function CropDiagnosis() {
  const farmerCrops = getProfile()?.crops ?? [];
  const cropOptions = [...new Set([...farmerCrops, ...cropCatalogue])];
  const [crop, setCrop] = useState(() => farmerCrops.find(c => SUPPORTED_CROPS.includes(c)) || 'Cassava');
  const [search, setSearch] = useState('');
  const [fileError, setFileError] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AiResult | null>(null);
  const [recordId, setRecordId] = useState<string | undefined>();
  const [second, setSecond] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const angleInput = useRef<HTMLInputElement>(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  useEffect(() => { preload('crop'); }, []);

  function choose(fileToUse?: File) {
    if (!fileToUse) return;
    setFileError('');
    if (!fileToUse.type.startsWith('image/')) { setFileError('Choose an image file (JPG, PNG or WEBP).'); return; }
    if (fileToUse.size > 10 * 1024 * 1024) { setFileError('The image must be 10 MB or smaller.'); return; }
    if (preview) URL.revokeObjectURL(preview);
    setFile(fileToUse);
    setPreview(URL.createObjectURL(fileToUse));
    setSecond(null);
    setResult(null);
  }

  function replacePhoto() {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview('');
    setSecond(null);
    setResult(null);
    if (input.current) input.current.value = '';
    if (angleInput.current) angleInput.current.value = '';
  }

  async function analyse(extra?: File) {
    if (!file || busy) return;
    setBusy(true);
    try {
      const photos = extra ? [file, extra] : [file];
      const { result: r, record } = await runCropDiagnosis(photos, crop, localStorage.getItem('acousticacre.language'));
      if (r.kind === 'diagnosis' || r.kind === 'uncertain') { saveDiagnosis(record); setRecordId(record.id); } else setRecordId(undefined);
      setResult(r);
    } finally {
      setBusy(false);
    }
  }

  /** "Not sure": take one more photo from another angle and combine both (backlog #5). */
  function addAngle(fileToUse?: File) {
    if (!fileToUse || !fileToUse.type.startsWith('image/')) return;
    setSecond(fileToUse);
    analyse(fileToUse);
  }

  return (
    <div className="page-stack narrow-page">
      <div className="back-row">
        <Link to="/dashboard" className="back-link">
          <ArrowLeft size={16} /> Back to overview
        </Link>
        <span className="step-label">CROP ASSESSMENT · STEP 1 OF 2</span>
      </div>

      <div className="page-intro">
        <div className="eyebrow">CROP HEALTH</div>
        <h1>Let's look at your crop.</h1>
        <p>Choose the crop and add a clear photo of the affected leaf. Use natural light where possible.</p>
      </div>

      <section className="form-panel">
        <div className="field-label">1. Which crop are you checking?</div>
        {farmerCrops.length > 0 && (
          <p className="crop-selection-note">
            Your crops selected during onboarding appear first. You can also choose another crop.
          </p>
        )}
        <label className="crop-search-label">Search crops
          <input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search e.g. rice, cocoa or pepper" />
        </label>
        <div className="crop-options">
          {cropOptions.filter(name => name.toLowerCase().includes(search.trim().toLowerCase())).map((cropName) => {
            const isSelected = crop === cropName;
            const isFromProfile = farmerCrops.includes(cropName);
            return (
              <button
                type="button"
                key={cropName}
                onClick={() => {
                  setCrop(cropName);
                  setResult(null);
                }}
                className={`crop-option ${isSelected ? 'selected' : ''}`}
                aria-pressed={isSelected}
              >
                <span className="crop-emoji">{cropEmojis[cropName] || '🌱'}</span>
                <span className="crop-option-copy">
                  <b>{cropName}</b>
                  {isFromProfile && <small>My farm</small>}
                  {!SUPPORTED_CROPS.includes(cropName) && <small>Coming soon</small>}
                </span>
                {isSelected && <Check size={16} />}
              </button>
            );
          })}
        </div>

        <p className="support-note">On-device diagnosis available now for {SUPPORTED_CROPS.join(', ')}. Other crops are coming in later packs.</p>
        <div className="field-label upload-label">2. Add a crop photo</div>
        {preview ? (
          <div className="preview-box">
            <img src={preview} alt="Selected crop" />
            <div className="preview-overlay">
              <span><Check size={15} /> Photo selected</span>
              <button type="button" onClick={replacePhoto}>
                <RefreshCw size={14} /> Replace
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="upload-zone" onClick={() => input.current?.click()}>
            <div className="upload-icon"><ImagePlus size={24} /></div>
            <b>Take a photo or upload an image</b>
            <span>JPG, PNG or WEBP · Clear, close-up leaf photo recommended</span>
            <span className="upload-cta"><UploadCloud size={16} /> Choose image</span>
            <input
              ref={input}
              type="file"
              accept="image/*"
              capture="environment"
              hidden
              onChange={(event) => choose(event.target.files?.[0])}
            />
          </button>
        )}

        {fileError && <p className="auth-error" role="alert">{fileError}</p>}

        <div className="quality-hint">
          <ShieldAlert size={17} />
          <span>For a useful assessment, keep the leaf in focus and avoid shadows, blur and busy backgrounds.</span>
        </div>

        <input ref={angleInput} type="file" accept="image/*" capture="environment" hidden onChange={(event) => addAngle(event.target.files?.[0])} />
        {second && <p className="support-note">Second photo added. Both photos are checked together.</p>}

        <button className="primary-btn full-btn" disabled={!file || busy} onClick={() => analyse(second ?? undefined)}>
          {busy ? (
            <><LoaderCircle className="spin" size={18} /> Checking the leaf on this phone…</>
          ) : (
            <>Continue to assessment <ArrowRight size={17} /></>
          )}
        </button>

        {result && (
          <ResultCard
            result={result}
            onRetry={replacePhoto}
            onAddAngle={!second ? () => angleInput.current?.click() : undefined}
            recordId={recordId}
            media={file}
            subject={crop}
          />
        )}
      </section>

      <div className="privacy-note">
        <ShieldAlert size={16} /> Your photo is analysed on this phone and never uploaded. Works offline after the first visit.
      </div>
    </div>
  );
}
