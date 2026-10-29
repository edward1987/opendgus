import { describe, expect, it } from "vitest";
import { allocateVps, arrangeItems, bbox, duplicateItems, insertPreset, Item, makePreset, moveBy, nextId, reorderItem, withBox } from "./project";
import type { Project, Variable } from "./types";

const v = (name: string, type: Variable["type"] = "int16", vp: number | null = null, length = 16): Variable =>
  ({ name, type, vp, init: 0, length, decimals: 0, doc: "" });

const project = (): Project => ({
  schema_version: 1, name: "t", description: "",
  display: { profile: null, width: 800, height: 480, rotation: 0 },
  theme: { name: "x", colors: {}, font: "Inter", radius: 10 },
  variables: [],
  pages: [{
    id: 0, name: "Home", background: { color: "background", gradient: null, image: null },
    elements: [
      { id: "e1", type: "rect", x: 0, y: 0, w: 10, h: 10, visible: true },
      { id: "e2", type: "line", points: [10, 10, 50, 30], color: "muted", width: 2, visible: true },
    ],
    controls: [{ id: "c3", type: "button", x: 100, y: 100, w: 50, h: 20, var: null, props: {}, visible: true }],
  }],
});

describe("project helpers", () => {
  it("allocates VPs like the backend", () => {
    expect(allocateVps([v("a"), v("b", "int32"), v("c")])).toEqual({ a: 0x5000, b: 0x5001, c: 0x5003 });
    expect(allocateVps([v("a"), v("f", "int16", 0x5001), v("t", "text", null, 5)])).toEqual({ a: 0x5000, f: 0x5001, t: 0x5002 });
  });

  it("generates unused ids", () => {
    expect(nextId(project(), "e")).toBe("e4");
  });

  it("moves and resizes lines through their bounding box", () => {
    const line = project().pages[0].elements[1];
    expect(bbox(line)).toEqual({ x: 9, y: 9, w: 42, h: 22 });
    expect((moveBy(line, 5, -5) as { points: number[] }).points).toEqual([15, 5, 55, 25]);
    const r = withBox({ id: "e1", type: "rect", x: 0, y: 0, w: 10, h: 10, visible: true }, { x: 1.4, y: 2.6, w: 0, h: 20 });
    expect(r).toMatchObject({ x: 1, y: 3, w: 1, h: 20 });
  });

  it("duplicates with new ids and offset", () => {
    const [p, ids] = duplicateItems(project(), ["c3"]);
    expect(ids).toEqual(["c4"]);
    expect(p.pages[0].controls[1]).toMatchObject({ id: "c4", x: 116, y: 116 });
  });

  it("reuses a control group with independent variables", () => {
    const p = project();
    p.variables = [v("mode")];
    p.pages[0].controls[0].var = "mode";
    const preset = makePreset(p, ["e1", "c3"], "Mode control");
    const [next, ids] = insertPreset(p, 0, preset, { x: 400, y: 240 });
    expect(ids).toHaveLength(2);
    expect(next.variables.map((variable) => variable.name)).toEqual(["mode", "mode1"]);
    expect(next.pages[0].controls.at(-1)?.var).toBe("mode1");
    expect(next.pages[0].controls.at(-1)?.id).not.toBe("c3");
  });

  it("reorders within the item's own list", () => {
    const p = reorderItem(project(), "e1", 1);
    expect(p.pages[0].elements.map((e) => e.id)).toEqual(["e2", "e1"]);
  });

  it("aligns items", () => {
    const items: Item[] = [
      { id: "a", type: "rect", x: 10, y: 0, w: 10, h: 10, visible: true },
      { id: "b", type: "rect", x: 50, y: 40, w: 30, h: 10, visible: true },
    ];
    const xs = (l: Item[]) => l.map((i) => bbox(i).x);
    const ys = (l: Item[]) => l.map((i) => bbox(i).y);
    expect(xs(arrangeItems(items, "left"))).toEqual([10, 10]);
    expect(xs(arrangeItems(items, "right"))).toEqual([70, 50]);
    expect(ys(arrangeItems(items, "center_y"))).toEqual([20, 20]);
  });
});
