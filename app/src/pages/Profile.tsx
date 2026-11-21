import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Check, Save, UserRound } from 'lucide-react';
import { getProfile, saveProfile, type FarmerProfile } from '../services/profile';

const empty: FarmerProfile = { fullName: '', email: '', phone: '', farmName: '', location: '', crops: [], farmSize: '', experience: '', language: 'English' };
const cropChoices = ['Cassava','Maize','Tomato','Rice','Yam','Cocoa','Beans / Cowpea','Groundnut','Soybean','Pepper','Okra','Plantain','Millet','Sorghum','Vegetables','Other'];

export default function Profile() {
  const [profile, setProfile] = useState<FarmerProfile>(getProfile() || empty);
  const [saved, setSaved] = useState(false);
  useEffect(() => { setProfile(getProfile() || empty); }, []);
  function update<K extends keyof FarmerProfile>(key: K, value: FarmerProfile[K]) {
    setProfile(current => ({ ...current, [key]: value }));
    setSaved(false);
  }
  function toggleCrop(crop: string) {
    const next = profile.crops.includes(crop) ? profile.crops.filter(item => item !== crop) : [...profile.crops, crop];
    update('crops', next);
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    saveProfile(profile);
    setSaved(true);
  }
  return (
    <div className="page-stack narrow-page">
      <div className="page-intro"><div className="eyebrow">YOUR ACCOUNT</div><h1>Farmer profile</h1><p>Keep your personal and farm information up to date. Changes are saved on this device in the frontend prototype.</p></div>
      <form className="form-panel profile-form" onSubmit={submit}>
        <div className="profile-summary"><div className="profile-avatar-large"><UserRound size={27}/></div><div><b>{profile.fullName || 'Your profile'}</b><span>{profile.email || 'Add your account details'}</span></div></div>
        <div className="onboarding-fields">
          <label>Full name<input value={profile.fullName} onChange={e=>update('fullName',e.target.value)} required /></label>
          <label>Email address<input type="email" value={profile.email} onChange={e=>update('email',e.target.value)} required /></label>
          <label>Phone number<input value={profile.phone} onChange={e=>update('phone',e.target.value)} placeholder="Optional"/></label>
          <label>Farm name<input value={profile.farmName} onChange={e=>update('farmName',e.target.value)} placeholder="Optional"/></label>
          <label>Location<input value={profile.location} onChange={e=>update('location',e.target.value)} required /></label>
          <label>Farm size<select value={profile.farmSize} onChange={e=>update('farmSize',e.target.value)}><option value="">Not specified</option>{['Less than 1 hectare','1–2 hectares','3–5 hectares','6–10 hectares','More than 10 hectares','Prefer not to say'].map(x=><option key={x}>{x}</option>)}</select></label>
          <label>Farming experience<select value={profile.experience} onChange={e=>update('experience',e.target.value)}><option value="">Not specified</option>{['Just starting','1–3 years','4–10 years','More than 10 years'].map(x=><option key={x}>{x}</option>)}</select></label>
          <label>Preferred language<select value={profile.language} onChange={e=>update('language',e.target.value)}>{['English','Hausa','Yoruba','Igbo','French','Swahili'].map(x=><option key={x}>{x}</option>)}</select></label>
        </div>
        <div className="profile-crop-current"><b>What do you grow?</b><p>Select all crops cultivated on your farm. These choices will appear first in crop diagnosis.</p><div className="onboarding-crops">{cropChoices.map(crop=><button type="button" key={crop} className={profile.crops.includes(crop)?'chosen':''} onClick={()=>toggleCrop(crop)}>{profile.crops.includes(crop)&&<Check size={14}/>} {crop}</button>)}</div></div>
        <button className="primary-btn" type="submit"><Save size={16}/> Save profile</button>
        {saved&&<span className="profile-saved" role="status">Profile saved on this device.</span>}
      </form>
    </div>
  );
}
