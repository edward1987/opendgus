// Snapping math for the canvas: grid + other items' edges/centres, with guide lines. Pure functions (unit tested).
import type { Box } from "./types";

export interface Guide {
  orientation: "v" | "h";
  pos: number; // x for vertical guides, y for horizontal ones (page px)
}

export interface SnapOptions {
  grid: number; // 0 disables grid snapping
  threshold: number; // max distance (page px) to snap to an item edge/centre
  targets: Box[]; // other items (and usually the page itself)
}

export const snapToGrid = (v: number, grid: number) => (grid > 0 ? Math.round(v / grid) * grid : Math.round(v));

/** Candidate lines of a box on one axis: start, centre, end. */
export function lines(b: Box, axis: "x" | "y"): number[] {
  const s = axis === "x" ? b.x : b.y;
  const len = axis === "x" ? b.w : b.h;
  return [s, s + len / 2, s + len];
}

interface AxisResult {
  value: number;
  guide: number | null;
}

/** Best offset to align any of `own` lines to any target line within threshold. */
function bestAlign(own: number[], targets: number[], threshold: number): { delta: number; at: number } | null {
  let best: { delta: number; at: number } | null = null;
  for (const o of own) {
    for (const t of targets) {
      const d = t - o;
      if (Math.abs(d) <= threshold && (!best || Math.abs(d) < Math.abs(best.delta))) best = { delta: d, at: t };
    }
  }
  return best;
}

function snapAxis(box: Box, axis: "x" | "y", opts: SnapOptions): AxisResult {
  const start = axis === "x" ? box.x : box.y;
  const targetLines = opts.targets.flatMap((t) => lines(t, axis));
  const align = bestAlign(lines(box, axis), targetLines, opts.threshold);
  if (align) return { value: Math.round(start + align.delta), guide: align.at };
  return { value: snapToGrid(start, opts.grid), guide: null };
}

/** Snap a moving box. Item alignment wins over the grid; returns the new position and guide lines to draw. */
export function snapMove(box: Box, opts: SnapOptions): { x: number; y: number; guides: Guide[] } {
  const sx = snapAxis(box, "x", opts);
  const sy = snapAxis(box, "y", opts);
  const guides: Guide[] = [];
  if (sx.guide !== null) guides.push({ orientation: "v", pos: sx.guide });
  if (sy.guide !== null) guides.push({ orientation: "h", pos: sy.guide });
  return { x: sx.value, y: sy.value, guides };
}

export type Edge = "left" | "right" | "top" | "bottom";

/** Snap the moving edges of a box being resized. `edges` are the edges the user drags. */
export function snapResize(box: Box, edges: Edge[], opts: SnapOptions): { box: Box; guides: Guide[] } {
  const out = { ...box };
  const guides: Guide[] = [];
  const snapLine = (v: number, axis: "x" | "y") => {
    const targets = opts.targets.flatMap((t) => lines(t, axis));
    const a = bestAlign([v], targets, opts.threshold);
    if (a) {
      guides.push({ orientation: axis === "x" ? "v" : "h", pos: a.at });
      return Math.round(a.at);
    }
    return snapToGrid(v, opts.grid);
  };
  if (edges.includes("left")) {
    const right = out.x + out.w;
    out.x = snapLine(out.x, "x");
    out.w = right - out.x;
  }
  if (edges.includes("right")) out.w = snapLine(out.x + out.w, "x") - out.x;
  if (edges.includes("top")) {
    const bottom = out.y + out.h;
    out.y = snapLine(out.y, "y");
    out.h = bottom - out.y;
  }
  if (edges.includes("bottom")) out.h = snapLine(out.y + out.h, "y") - out.y;
  out.w = Math.max(1, out.w);
  out.h = Math.max(1, out.h);
  return { box: out, guides };
}

/** Edges affected by a Konva.Transformer anchor name. */
export function anchorEdges(anchor: string | null | undefined): Edge[] {
  const e: Edge[] = [];
  if (!anchor) return e;
  if (anchor.includes("left")) e.push("left");
  if (anchor.includes("right")) e.push("right");
  if (anchor.startsWith("top")) e.push("top");
  if (anchor.startsWith("bottom")) e.push("bottom");
  return e;
}

/** Union bounding box. */
export function unionBox(boxes: Box[]): Box | null {
  if (!boxes.length) return null;
  const x1 = Math.min(...boxes.map((b) => b.x));
  const y1 = Math.min(...boxes.map((b) => b.y));
  const x2 = Math.max(...boxes.map((b) => b.x + b.w));
  const y2 = Math.max(...boxes.map((b) => b.y + b.h));
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
}
