import type { VoiceCallRole } from './VoiceCallPopup';

export interface VoiceCallSnapshot {
  open: boolean;
  calling: boolean;
  startedAt: number | null;
}

const defaultSnapshot: VoiceCallSnapshot = { open: false, calling: false, startedAt: null };
const storageKey = (role: VoiceCallRole) => `voice-call-${role}`;

export const getVoiceCallSnapshot = (role: VoiceCallRole): VoiceCallSnapshot => {
  try {
    const saved = window.localStorage.getItem(storageKey(role));
    return saved ? { ...defaultSnapshot, ...JSON.parse(saved) } : defaultSnapshot;
  } catch {
    return defaultSnapshot;
  }
};

export const updateVoiceCallSnapshot = (role: VoiceCallRole, patch: Partial<VoiceCallSnapshot>) => {
  const next = { ...getVoiceCallSnapshot(role), ...patch };
  window.localStorage.setItem(storageKey(role), JSON.stringify(next));
};

export const clearVoiceCallSnapshot = (role: VoiceCallRole) => {
  window.localStorage.removeItem(storageKey(role));
};
