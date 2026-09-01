import { VoiceCallRole } from './VoiceCallPopup';

const STORAGE_KEY = 'voice-call-state';

export const requestVoiceCall = (role: VoiceCallRole) => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ open: true, role }));
  window.dispatchEvent(new Event('voice-call-change'));
};

export const readVoiceCallState = () => {
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (!saved) return { open: false, role: 'customer' as VoiceCallRole };
  try { return JSON.parse(saved) as { open: boolean; role: VoiceCallRole }; } catch { return { open: false, role: 'customer' as VoiceCallRole }; }
};

export const closeVoiceCall = () => {
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new Event('voice-call-change'));
};
