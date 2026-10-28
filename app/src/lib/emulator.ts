// Pure helpers for Run mode (the interactive emulator view).

/** Presses at least this long are sent as a long press (emulator_tap with hold_ms). */
export const HOLD_THRESHOLD_MS = 350;
export const MAX_HOLD_MS = 10000;

export function holdMs(pressedForMs: number): number {
  if (!(pressedForMs >= HOLD_THRESHOLD_MS)) return 0;
  return Math.min(MAX_HOLD_MS, Math.round(pressedForMs));
}

/** Map a pointer position over the displayed image (any CSS scale) to device pixels, clamped to the screen. */
export function toDevice(
  clientX: number, clientY: number,
  rect: { left: number; top: number; width: number; height: number },
  deviceW: number, deviceH: number,
): { x: number; y: number } {
  const fx = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
  const fy = rect.height > 0 ? (clientY - rect.top) / rect.height : 0;
  const clamp = (v: number, max: number) => Math.max(0, Math.min(max - 1, Math.floor(v)));
  return { x: clamp(fx * deviceW, deviceW), y: clamp(fy * deviceH, deviceH) };
}

/** Largest size with the device aspect ratio that fits the box. */
export function fitSize(boxW: number, boxH: number, w: number, h: number): { w: number; h: number } {
  if (w <= 0 || h <= 0 || boxW <= 0 || boxH <= 0) return { w: 0, h: 0 };
  const s = Math.min(boxW / w, boxH / h);
  return { w: Math.floor(w * s), h: Math.floor(h * s) };
}

export interface Change {
  name: string;
  before: unknown;
  after: unknown;
}

export interface CaptionInfo {
  page: number | null;
  hit: unknown;
  changes: Change[];
  raw: string;
}

/** Decode an emulator tool caption (JSON, possibly truncated) into page / hit / changed variables.
 *  - emulator_tap:          {"hit", "page", "changed": {name: [before, after]}}
 *  - emulator_set_variable: {"page", "<name>": value}
 *  - emulator_start:        the device state {"page", "ms", ...} */
export function parseCaption(caption: string | undefined, setName?: string): CaptionInfo {
  const raw = caption ?? "";
  let obj: any = null;
  try {
    obj = JSON.parse(raw);
  } catch {
    obj = null;
  }
  if (!obj || typeof obj !== "object") return { page: null, hit: null, changes: [], raw };
  const changes: Change[] = [];
  if (obj.changed && typeof obj.changed === "object")
    for (const [name, v] of Object.entries(obj.changed as Record<string, unknown>))
      changes.push(Array.isArray(v) ? { name, before: v[0], after: v[1] } : { name, before: undefined, after: v });
  if (setName && setName in obj) changes.push({ name: setName, before: undefined, after: obj[setName] });
  return { page: typeof obj.page === "number" ? obj.page : null, hit: obj.hit ?? null, changes, raw };
}

/** Parse the smoke-test tap script "x,y[,holdMs];x,y;..." (invalid entries are skipped). */
export function parseTapScript(script: string | null | undefined): { x: number; y: number; hold: number }[] {
  if (!script) return [];
  const out: { x: number; y: number; hold: number }[] = [];
  for (const part of script.split(/[;\s]+/)) {
    const n = part.split(",").map((v) => Number(v));
    if (n.length >= 2 && n.slice(0, 2).every((v) => Number.isFinite(v) && v >= 0))
      out.push({ x: Math.round(n[0]), y: Math.round(n[1]), hold: Number.isFinite(n[2]) && n[2] > 0 ? Math.round(n[2]) : 0 });
  }
  return out;
}

/** Parse a value typed into the variables table: integers only (the emulator takes ints). */
export function parseVarValue(text: string): number | null {
  const t = text.trim();
  if (!/^[-+]?\d+$/.test(t)) return null;
  const v = Number(t);
  return Number.isSafeInteger(v) ? v : null;
}
