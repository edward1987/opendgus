// Pure helpers over the project model: item lookup, ids, bounding boxes, moves, VP allocation, alignment.
import type { Box, Control, Element, LineElement, Page, Preset, Project, Variable } from "./types";

export type Item = Element | Control;

export const isLine = (it: Item): it is LineElement => it.type === "line";
export const isControl = (it: Item): it is Control => "props" in it && typeof (it as Control).props === "object";

export function allItems(p: Page): Item[] {
  return [...p.elements, ...p.controls];
}

export function findItem(project: Project, id: string): { page: Page; item: Item; kind: "element" | "control"; index: number } | null {
  for (const page of project.pages) {
    let i = page.elements.findIndex((e) => e.id === id);
    if (i >= 0) return { page, item: page.elements[i], kind: "element", index: i };
    i = page.controls.findIndex((c) => c.id === id);
    if (i >= 0) return { page, item: page.controls[i], kind: "control", index: i };
  }
  return null;
}

/** Next unused id like e7 / c8 (same scheme as Project.ensure_ids, numbers shared across prefixes). */
export function nextId(project: Project, prefix: "e" | "c"): string {
  const used = new Set(project.pages.flatMap((p) => allItems(p).map((i) => i.id)));
  let n = 0;
  for (const id of used) {
    const m = /^[ec](\d+)$/.exec(id);
    if (m) n = Math.max(n, Number(m[1]));
  }
  let id = `${prefix}${n + 1}`;
  while (used.has(id)) id = `${prefix}${++n + 1}`;
  return id;
}

export function bbox(it: Item): Box {
  if (isLine(it)) {
    const xs = it.points.filter((_, i) => i % 2 === 0);
    const ys = it.points.filter((_, i) => i % 2 === 1);
    const x = Math.min(...xs), y = Math.min(...ys);
    const pad = Math.ceil(it.width / 2);
    return { x: x - pad, y: y - pad, w: Math.max(...xs) - x + 2 * pad, h: Math.max(...ys) - y + 2 * pad };
  }
  return { x: it.x, y: it.y, w: it.w, h: it.h };
}

/** Return a copy of `it` occupying box `b` (lines are translated/scaled). */
export function withBox(it: Item, b: Box): Item {
  if (isLine(it)) {
    const o = bbox(it);
    const sx = o.w > 0 ? b.w / o.w : 1, sy = o.h > 0 ? b.h / o.h : 1;
    const points = it.points.map((v, i) =>
      i % 2 === 0 ? Math.round(b.x + (v - o.x) * sx) : Math.round(b.y + (v - o.y) * sy));
    return { ...it, points };
  }
  return { ...it, x: Math.round(b.x), y: Math.round(b.y), w: Math.max(1, Math.round(b.w)), h: Math.max(1, Math.round(b.h)) };
}

export function moveBy(it: Item, dx: number, dy: number): Item {
  const b = bbox(it);
  return withBox(it, { ...b, x: b.x + dx, y: b.y + dy });
}

/** Replace items (by id) in a project, immutably. */
export function updateItems(project: Project, changed: Item[]): Project {
  const byId = new Map(changed.map((c) => [c.id, c]));
  return {
    ...project,
    pages: project.pages.map((p) =>
      allItems(p).some((i) => byId.has(i.id))
        ? {
            ...p,
            elements: p.elements.map((e) => (byId.get(e.id) as Element) ?? e),
            controls: p.controls.map((c) => (byId.get(c.id) as Control) ?? c),
          }
        : p),
  };
}

export function removeItems(project: Project, ids: string[]): Project {
  const s = new Set(ids);
  return {
    ...project,
    pages: project.pages.map((p) => ({
      ...p,
      elements: p.elements.filter((e) => !s.has(e.id)),
      controls: p.controls.filter((c) => !s.has(c.id)),
    })),
  };
}

export function updatePage(project: Project, pageId: number, fn: (p: Page) => Page): Project {
  return { ...project, pages: project.pages.map((p) => (p.id === pageId ? fn(p) : p)) };
}

/** Duplicate items (offset by `offset` px), returns [project, new ids]. */
export function duplicateItems(project: Project, ids: string[], offset = 16): [Project, string[]] {
  let p = project;
  const newIds: string[] = [];
  for (const id of ids) {
    const f = findItem(p, id);
    if (!f) continue;
    const copy = moveBy(structuredClone(f.item), offset, offset);
    copy.id = nextId(p, f.kind === "control" ? "c" : "e");
    newIds.push(copy.id);
    p = updatePage(p, f.page.id, (pg) =>
      f.kind === "control" ? { ...pg, controls: [...pg.controls, copy as Control] } : { ...pg, elements: [...pg.elements, copy as Element] });
  }
  return [p, newIds];
}

/** Save selected items as a movable group, including the variables they use. */
export function makePreset(project: Project, ids: string[], name: string): Preset {
  const picked = ids.map((id) => findItem(project, id)?.item).filter((it): it is Item => !!it);
  if (!picked.length) throw new Error("Select at least one item");
  const boxes = picked.map(bbox);
  const x = Math.min(...boxes.map((b) => b.x)), y = Math.min(...boxes.map((b) => b.y));
  const width = Math.max(...boxes.map((b) => b.x + b.w)) - x;
  const height = Math.max(...boxes.map((b) => b.y + b.h)) - y;
  const items = picked.map((it) => moveBy(structuredClone(it), -x, -y));
  const vars = new Set(items.filter(isControl).map((c) => c.var).filter((v): v is string => !!v));
  return { name: name.trim(), width, height,
    elements: items.filter((it) => !isControl(it)) as Element[],
    controls: items.filter(isControl) as Control[],
    variables: project.variables.filter((v) => vars.has(v.name)).map((v) => ({ ...v, vp: null })),
  };
}

/** Insert a preset with independent variable names and fresh item IDs. */
export function insertPreset(project: Project, pageId: number, preset: Preset, centre: { x: number; y: number }): [Project, string[]] {
  let next = project;
  const names = new Map<string, string>();
  for (const v of preset.variables) {
    const name = uniqueVarName(next, v.name);
    names.set(v.name, name);
    next = { ...next, variables: [...next.variables, { ...structuredClone(v), name, vp: null }] };
  }
  const dx = Math.max(0, Math.min(project.display.width - preset.width, Math.round(centre.x - preset.width / 2)));
  const dy = Math.max(0, Math.min(project.display.height - preset.height, Math.round(centre.y - preset.height / 2)));
  const ids: string[] = [];
  for (const item of [...preset.elements, ...preset.controls]) {
    const copy = moveBy(structuredClone(item), dx, dy);
    copy.id = nextId(next, isControl(copy) ? "c" : "e");
    ids.push(copy.id);
    if (isControl(copy)) {
      copy.var = copy.var ? names.get(copy.var) ?? copy.var : null;
    }
    next = updatePage(next, pageId, (pg) => isControl(copy)
      ? { ...pg, controls: [...pg.controls, copy as Control] }
      : { ...pg, elements: [...pg.elements, copy as Element] });
  }
  return [next, ids];
}

/** Move an item within its own list (z-order). dir +1 = towards front. */
export function reorderItem(project: Project, id: string, dir: 1 | -1 | "front" | "back"): Project {
  const f = findItem(project, id);
  if (!f) return project;
  const key = f.kind === "control" ? "controls" : "elements";
  return updatePage(project, f.page.id, (pg) => {
    const list = [...(pg[key] as Item[])];
    const [it] = list.splice(f.index, 1);
    const to = dir === "front" ? list.length : dir === "back" ? 0 : Math.max(0, Math.min(list.length, f.index + dir));
    list.splice(to, 0, it);
    return { ...pg, [key]: list };
  });
}

const WORDS: Record<string, number> = { int16: 1, uint16: 1, int32: 2, uint32: 2, bits: 1 };
export const varWords = (v: Variable) => (v.type === "text" ? Math.floor((v.length + 1) / 2) : WORDS[v.type] ?? 1);

/** Same algorithm as Project.allocate_vps (fixed VPs kept, others packed upward from 0x5000). */
export function allocateVps(vars: Variable[], start = 0x5000): Record<string, number> {
  const out: Record<string, number> = {};
  const used = new Set<number>();
  for (const v of vars) {
    if (v.vp !== null && v.vp !== undefined) {
      out[v.name] = v.vp;
      for (let a = v.vp; a < v.vp + varWords(v); a++) used.add(a);
    }
  }
  let nxt = start;
  for (const v of vars) {
    if (v.vp === null || v.vp === undefined) {
      const w = varWords(v);
      const clash = (n: number) => { for (let a = n; a < n + w; a++) if (used.has(a)) return true; return false; };
      while (clash(nxt)) nxt++;
      out[v.name] = nxt;
      for (let a = nxt; a < nxt + w; a++) used.add(a);
      nxt += w;
    }
  }
  return out;
}

export const hex4 = (n: number) => "0x" + n.toString(16).toUpperCase().padStart(4, "0");

export function uniqueVarName(project: Project, base: string): string {
  const names = new Set(project.variables.map((v) => v.name));
  const clean = base.replace(/[^A-Za-z0-9_]/g, "_").replace(/^([0-9])/, "_$1") || "var";
  for (let n = 1; ; n++) if (!names.has(`${clean}${n}`)) return `${clean}${n}`;
}

export type AlignMode = "left" | "center_x" | "right" | "top" | "center_y" | "bottom" | "distribute_x" | "distribute_y";

/** Align/distribute boxes (same semantics as the `arrange` tool), returns the changed items. */
export function arrangeItems(items: Item[], mode: AlignMode): Item[] {
  const boxes = items.map(bbox);
  if (items.length < 2) return items;
  const minX = Math.min(...boxes.map((b) => b.x)), maxX = Math.max(...boxes.map((b) => b.x + b.w));
  const minY = Math.min(...boxes.map((b) => b.y)), maxY = Math.max(...boxes.map((b) => b.y + b.h));
  if (mode === "distribute_x" || mode === "distribute_y") {
    const ax = mode === "distribute_x" ? "x" : "y", sz = mode === "distribute_x" ? "w" : "h";
    const order = items.map((it, i) => ({ it, b: boxes[i] })).sort((a, b) => a.b[ax] - b.b[ax]);
    const start = order[0].b[ax], end = order[order.length - 1].b[ax] + order[order.length - 1].b[sz];
    const gap = (end - start - order.reduce((s, o) => s + o.b[sz], 0)) / Math.max(1, order.length - 1);
    let pos = start;
    return order.map(({ it, b }) => {
      const nb = { ...b, [ax]: Math.round(pos) };
      pos += b[sz] + gap;
      return withBox(it, nb);
    });
  }
  return items.map((it, i) => {
    const b = { ...boxes[i] };
    if (mode === "left") b.x = minX;
    if (mode === "right") b.x = maxX - b.w;
    if (mode === "center_x") b.x = Math.round((minX + maxX) / 2 - b.w / 2);
    if (mode === "top") b.y = minY;
    if (mode === "bottom") b.y = maxY - b.h;
    if (mode === "center_y") b.y = Math.round((minY + maxY) / 2 - b.h / 2);
    return withBox(it, b);
  });
}

/** Resolve a colour value (token or #hex) to a CSS colour. */
export function resolveColor(project: Project | null, c: string | null | undefined): string | null {
  if (!c || c === "none") return null;
  if (/^#[0-9a-fA-F]{6}$/.test(c)) return c;
  return project?.theme.colors[c] ?? null;
}
