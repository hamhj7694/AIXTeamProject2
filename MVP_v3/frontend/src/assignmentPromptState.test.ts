import { afterEach, describe, expect, it } from 'vitest';
import { hasInitialAssignmentHandled, hasInitialAssignmentPending, markInitialAssignmentHandled, markInitialAssignmentPending, shouldOpenInitialAssignment } from './assignmentPromptState';

const installStorage = () => {
  const values = new Map<string, string>();
  const localStorage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); },
    removeItem: (key: string) => { values.delete(key); },
    clear: () => { values.clear(); },
    key: (index: number) => Array.from(values.keys())[index] ?? null,
    get length() { return values.size; },
  } as Storage;
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { localStorage } });
};

afterEach(() => {
  Reflect.deleteProperty(globalThis, 'window');
});

describe('initial assignment prompt state', () => {
  it('opens only for a pending, unassigned Case that was not handled', () => {
    expect(shouldOpenInitialAssignment({ hasPending: true, hasHandled: false, hasPrimaryAssignee: false, routeHint: false })).toBe(true);
    expect(shouldOpenInitialAssignment({ hasPending: false, hasHandled: false, hasPrimaryAssignee: false, routeHint: true })).toBe(true);
    expect(shouldOpenInitialAssignment({ hasPending: true, hasHandled: true, hasPrimaryAssignee: false, routeHint: true })).toBe(false);
    expect(shouldOpenInitialAssignment({ hasPending: true, hasHandled: false, hasPrimaryAssignee: true, routeHint: true })).toBe(false);
    expect(shouldOpenInitialAssignment({ hasPending: false, hasHandled: false, hasPrimaryAssignee: false, routeHint: false })).toBe(false);
  });

  it('keeps a newly-created Case pending until it is handled', () => {
    installStorage();
    markInitialAssignmentPending('VP-NEW');
    expect(hasInitialAssignmentPending('VP-NEW')).toBe(true);

    markInitialAssignmentHandled('VP-NEW');
    expect(hasInitialAssignmentPending('VP-NEW')).toBe(false);
    expect(hasInitialAssignmentHandled('VP-NEW')).toBe(true);
  });

  it('does not resurrect a Case after the one-time flow is handled', () => {
    installStorage();
    markInitialAssignmentPending('VP-NEW');
    markInitialAssignmentHandled('VP-NEW');
    markInitialAssignmentPending('VP-NEW');
    expect(hasInitialAssignmentPending('VP-NEW')).toBe(false);
  });
});
