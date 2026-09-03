const RESET_MARKER = 'mvp-v2:runtime-reset:2026-09-03-ai-integration';

const LEGACY_EXACT_KEYS = new Set([
  'customer-last-response',
  'human-takeover',
  'fds-risk',
  'voice-call-bank',
  'voice-call-customer',
]);

/**
 * Removes only MVP_v2 browser data created during local mock/testing work.
 * The marker makes this migration run once per browser origin, so data created
 * after the real Backend/AI integration begins is preserved on later reloads.
 */
export const resetLegacyClientRuntimeDataOnce = () => {
  try {
    if (window.localStorage.getItem(RESET_MARKER) === 'done') return;

    const keys = Array.from({ length: window.localStorage.length }, (_, index) => window.localStorage.key(index))
      .filter((key): key is string => Boolean(key));

    for (const key of keys) {
      if (key.startsWith('mvp-v2:') || LEGACY_EXACT_KEYS.has(key)) {
        window.localStorage.removeItem(key);
      }
    }

    window.localStorage.setItem(RESET_MARKER, 'done');
  } catch {
    // Storage can be unavailable in private/restricted browser contexts.
  }
};
