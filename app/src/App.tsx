import { useEffect, useState } from 'react';
import { NavLink, Route, Routes, useLocation, Link, Navigate, useNavigate } from 'react-router-dom';
import { AudioWaveform, Bell, CircleHelp, ClipboardList, Globe2, Home, Leaf, Menu, Settings as SettingsIcon, Sprout, UserRound, WifiOff, X, LogOut } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import CropDiagnosis from './pages/CropDiagnosis';
import MachineDiagnosis from './pages/MachineDiagnosis';
import History from './pages/History';
import Help from './pages/Help';
import Landing from './pages/Landing';
import Auth from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import SpeedTest from './pages/SpeedTest';
import AppNotices from './components/AppNotices';
import { getProfile, isSignedIn, PROFILE_UPDATED_EVENT, signOut } from './services/profile';

function ProtectedWorkspace() {
  const location = useLocation();
  if (!isSignedIn()) return <Navigate to="/signin" replace state={{ from: location.pathname }} />;
  return <Workspace />;
}

function OnboardingRoute() {
  return isSignedIn() ? <Onboarding /> : <Navigate to="/signup" replace />;
}

function Workspace() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [language, setLanguage] = useState(localStorage.getItem('acousticacre.language') || 'English');
  const [profileName, setProfileName] = useState(getProfile()?.fullName || 'Farmer account');
  const [profileLocation, setProfileLocation] = useState(getProfile()?.location || 'Your farm workspace');
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const refreshProfile = () => {
      const profile = getProfile();
      setProfileName(profile?.fullName || 'Farmer account');
      setProfileLocation(profile?.location || 'Your farm workspace');
    };
    window.addEventListener(PROFILE_UPDATED_EVENT, refreshProfile);
    window.addEventListener('storage', refreshProfile);
    return () => {
      window.removeEventListener(PROFILE_UPDATED_EVENT, refreshProfile);
      window.removeEventListener('storage', refreshProfile);
    };
  }, []);

  const links = [
    { to: '/dashboard', label: 'Overview', icon: Home },
    { to: '/crop', label: 'Crop diagnosis', icon: Leaf },
    { to: '/machine', label: 'Machine diagnosis', icon: AudioWaveform },
    { to: '/history', label: 'Diagnosis history', icon: ClipboardList },
    { to: '/help', label: 'Help & guidance', icon: CircleHelp },
  ];
  const title = links.find(item => item.to === location.pathname)?.label ||
    (location.pathname === '/profile' ? 'Farmer profile' : location.pathname === '/settings' ? 'Settings' : location.pathname === '/speed' ? 'Speed test' : 'AcousticAcre AI');

  function logout() {
    signOut();
    setMobileOpen(false);
    navigate('/signin', { replace: true });
  }

  return (
    <div className="app-shell">
      {mobileOpen && <button className="mobile-scrim" onClick={() => setMobileOpen(false)} aria-label="Close menu" />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Sprout size={23} /></div>
          <div><strong>AcousticAcre</strong><span>AI FARM ASSISTANT</span></div>
          <button className="icon-btn mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X /></button>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>{links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Icon size={18} /><span>{label}</span>
          </NavLink>
        ))}</nav>
        <div className="workspace-label account-label">ACCOUNT</div>
        <nav>
          <NavLink to="/profile" onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><UserRound size={18} /><span>Farmer profile</span></NavLink>
          <NavLink to="/settings" onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><SettingsIcon size={18} /><span>Settings</span></NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="offline-card"><div className="offline-icon"><WifiOff size={17} /></div><div><b>Designed for offline use</b><span>Local-first experience</span></div></div>
          <div className="profile">
            <div className="avatar">{profileName.charAt(0).toUpperCase()}</div>
            <div><b>{profileName}</b><span>{profileLocation}</span></div>
            <button className="profile-logout" title="Sign out" aria-label="Sign out" onClick={logout}><LogOut size={15} /></button>
          </div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="top-left">
            <button className="icon-btn mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu /></button>
            <div><div className="breadcrumb">WORKSPACE <span>/</span> <b>{title.toUpperCase()}</b></div><div className="page-heading">{title}</div></div>
          </div>
          <div className="top-actions">
            <div className="connection-pill"><span /> On-device AI</div>
            <label className="language-select"><Globe2 size={16} /><select aria-label="Display language" value={language} onChange={event => { setLanguage(event.target.value); localStorage.setItem('acousticacre.language', event.target.value); }}>
              <option>English</option><option>Hausa</option><option>Yoruba</option><option>Igbo</option><option>French</option><option>Swahili</option>
            </select></label>
            <Link className="icon-btn notification" to="/settings" title="Settings" aria-label="Settings"><Bell size={18} /></Link>
          </div>
        </header>
        <div className="content">
          <AppNotices />
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/crop" element={<CropDiagnosis />} />
            <Route path="/machine" element={<MachineDiagnosis />} />
            <Route path="/history" element={<History />} />
            <Route path="/help" element={<Help />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/speed" element={<SpeedTest />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          <footer>© 2026 AcousticAcre AI <span>Farmer-first agricultural intelligence</span></footer>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signup" element={<Auth mode="signup" />} />
      <Route path="/signin" element={<Auth mode="signin" />} />
      <Route path="/forgot-password" element={<Auth mode="forgot" />} />
      <Route path="/onboarding" element={<OnboardingRoute />} />
      <Route path="/*" element={<ProtectedWorkspace />} />
    </Routes>
  );
}
