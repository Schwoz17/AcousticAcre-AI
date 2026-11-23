import { useEffect, useState } from 'react';
import { RefreshCw, ShieldCheck, X } from 'lucide-react';
import { Link } from 'react-router-dom';

export const UPDATE_EVENT = 'acousticacre:update-ready';
const PRIVACY_KEY = 'acousticacre.privacy.v1';

/** First-run privacy notice (NDPA: say plainly what is stored, for how long, and why) + "new version" prompt. */
export default function AppNotices() {
  const [showPrivacy, setShowPrivacy] = useState(() => localStorage.getItem(PRIVACY_KEY) !== 'seen');
  const [update, setUpdate] = useState(false);

  useEffect(() => {
    const on = () => setUpdate(true);
    window.addEventListener(UPDATE_EVENT, on);
    return () => window.removeEventListener(UPDATE_EVENT, on);
  }, []);

  return (
    <>
      {update && (
        <div className="app-notice notice-update" role="status">
          <RefreshCw size={17} />
          <span><b>A new version is ready.</b> Reload to use it. It still works offline.</span>
          <button className="primary-btn small-btn" onClick={() => window.location.reload()}>Reload</button>
          <button className="icon-btn" aria-label="Later" onClick={() => setUpdate(false)}><X size={16} /></button>
        </div>
      )}
      {showPrivacy && (
        <div className="app-notice notice-privacy" role="dialog" aria-label="How your data is used">
          <ShieldCheck size={18} />
          <span>
            <b>Your data stays with you.</b> Photos and sounds are checked on this phone and never uploaded. History stays on this phone.
            The USSD and SMS service keeps only a scrambled version of your number for 30 days. <Link to="/settings">More</Link>
          </span>
          <button className="primary-btn small-btn" onClick={() => { localStorage.setItem(PRIVACY_KEY, 'seen'); setShowPrivacy(false); }}>OK</button>
        </div>
      )}
    </>
  );
}
