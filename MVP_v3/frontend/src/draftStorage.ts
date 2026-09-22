import React from 'react';

const readStoredDraft = (storageKey?: string) => {
  if (!storageKey || typeof window === 'undefined') return '';
  try { return window.localStorage.getItem(storageKey) ?? ''; } catch { return ''; }
};

export const usePersistentDraft = (storageKey?: string) => {
  const [draft, setDraft] = React.useState(() => readStoredDraft(storageKey));
  const loadedKeyRef = React.useRef(storageKey);

  React.useEffect(() => {
    loadedKeyRef.current = storageKey;
    setDraft(readStoredDraft(storageKey));
  }, [storageKey]);

  React.useEffect(() => {
    if (loadedKeyRef.current !== storageKey || !storageKey || typeof window === 'undefined') return;
    try {
      if (draft) window.localStorage.setItem(storageKey, draft);
      else window.localStorage.removeItem(storageKey);
    } catch { /* localStorage may be unavailable; the in-memory draft still works. */ }
  }, [draft, storageKey]);

  return [draft, setDraft] as const;
};
