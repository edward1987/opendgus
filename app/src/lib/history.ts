// Undo/redo stack of immutable snapshots. Consecutive pushes with the same `coalesce` key within `windowMs`
// replace each other's "before" state (typing in a field or nudging with arrows = one undo step).

export interface History<T> {
  past: T[];
  future: T[];
  lastKey: string | null;
  lastTime: number;
}

export const HISTORY_LIMIT = 200;

export function createHistory<T>(): History<T> {
  return { past: [], future: [], lastKey: null, lastTime: 0 };
}

/** Record `before` (the state prior to an edit). Returns a new history. */
export function record<T>(h: History<T>, before: T, coalesce: string | null = null, now = Date.now(),
                          windowMs = 800): History<T> {
  if (coalesce && h.lastKey === coalesce && now - h.lastTime < windowMs && h.past.length) {
    return { ...h, future: [], lastTime: now };
  }
  const past = [...h.past, before];
  if (past.length > HISTORY_LIMIT) past.splice(0, past.length - HISTORY_LIMIT);
  return { past, future: [], lastKey: coalesce, lastTime: now };
}

export function canUndo<T>(h: History<T>) {
  return h.past.length > 0;
}

export function canRedo<T>(h: History<T>) {
  return h.future.length > 0;
}

/** Undo: returns [history, state to restore] or null. `current` goes to the redo stack. */
export function undo<T>(h: History<T>, current: T): [History<T>, T] | null {
  if (!h.past.length) return null;
  const prev = h.past[h.past.length - 1];
  return [{ past: h.past.slice(0, -1), future: [current, ...h.future], lastKey: null, lastTime: 0 }, prev];
}

export function redo<T>(h: History<T>, current: T): [History<T>, T] | null {
  if (!h.future.length) return null;
  const next = h.future[0];
  return [{ past: [...h.past, current], future: h.future.slice(1), lastKey: null, lastTime: 0 }, next];
}
