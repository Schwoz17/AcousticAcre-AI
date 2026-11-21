export type FarmerProfile = {
  fullName: string;
  email: string;
  phone: string;
  farmName: string;
  location: string;
  crops: string[];
  farmSize: string;
  experience: string;
  language: string;
};

const PROFILE_KEY = 'acousticacre.profile.v1';
const SESSION_KEY = 'acousticacre.session.v1';
export const PROFILE_UPDATED_EVENT = 'acousticacre:profile-updated';

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function getProfile(): FarmerProfile | null {
  const value = readJson<Partial<FarmerProfile> | null>(PROFILE_KEY, null);
  if (!value || typeof value !== 'object') return null;
  return {
    fullName: value.fullName || '',
    email: value.email || '',
    phone: value.phone || '',
    farmName: value.farmName || '',
    location: value.location || '',
    crops: Array.isArray(value.crops) ? value.crops.filter((crop): crop is string => typeof crop === 'string') : [],
    farmSize: value.farmSize || '',
    experience: value.experience || '',
    language: value.language || 'English',
  };
}

export function saveProfile(profile: FarmerProfile): void {
  localStorage.setItem(PROFILE_KEY, JSON.stringify({
    ...profile,
    fullName: profile.fullName.trim(),
    email: profile.email.trim().toLowerCase(),
    crops: [...new Set(profile.crops)],
  }));
  window.dispatchEvent(new Event(PROFILE_UPDATED_EVENT));
}

export function setDemoSession(email: string): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify({
    email: email.trim().toLowerCase(),
    signedInAt: new Date().toISOString(),
    mode: 'frontend-demo',
  }));
}

export function isSignedIn(): boolean {
  const session = readJson<{ email?: string } | null>(SESSION_KEY, null);
  return Boolean(session?.email);
}

export function signOut(): void {
  localStorage.removeItem(SESSION_KEY);
}

export function getSessionEmail(): string {
  return readJson<{ email?: string }>(SESSION_KEY, {}).email || '';
}
