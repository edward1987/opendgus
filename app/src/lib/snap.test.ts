import { describe, expect, it } from "vitest";
import { anchorEdges, snapMove, snapResize, snapToGrid, unionBox } from "./snap";

const page = { x: 0, y: 0, w: 800, h: 480 };

describe("snapping", () => {
  it("snaps to the grid when no item is near", () => {
    expect(snapToGrid(13, 8)).toBe(16);
    expect(snapToGrid(11, 8)).toBe(8);
    expect(snapToGrid(11.4, 0)).toBe(11);
    const r = snapMove({ x: 203, y: 141, w: 50, h: 50 }, { grid: 8, threshold: 2, targets: [] });
    expect(r).toEqual({ x: 200, y: 144, guides: [] });
  });

  it("aligns edges to other items and reports guides", () => {
    const other = { x: 100, y: 300, w: 80, h: 40 };
    const r = snapMove({ x: 103, y: 50, w: 60, h: 30 }, { grid: 8, threshold: 5, targets: [other] });
    expect(r.x).toBe(100);
    expect(r.guides).toContainEqual({ orientation: "v", pos: 100 });
    expect(r.guides.some((g) => g.orientation === "h")).toBe(false);
  });

  it("aligns centres (page centre)", () => {
    // box centre at 398 -> page centre 400
    const r = snapMove({ x: 348, y: 10, w: 100, h: 20 }, { grid: 8, threshold: 4, targets: [page] });
    expect(r.x).toBe(350);
    expect(r.guides).toContainEqual({ orientation: "v", pos: 400 });
  });

  it("picks the closest alignment", () => {
    const a = { x: 0, y: 0, w: 10, h: 10 };
    const b = { x: 104, y: 0, w: 10, h: 10 };
    const r = snapMove({ x: 102, y: 200, w: 20, h: 20 }, { grid: 0, threshold: 5, targets: [a, b] });
    expect(r.x).toBe(104);
  });

  it("snaps only the dragged edges when resizing", () => {
    const other = { x: 300, y: 0, w: 10, h: 10 };
    const r = snapResize({ x: 100, y: 100, w: 197, h: 51 }, ["right", "bottom"], { grid: 8, threshold: 5, targets: [other] });
    expect(r.box).toEqual({ x: 100, y: 100, w: 200, h: 52 });
    expect(r.guides).toEqual([{ orientation: "v", pos: 300 }]);
    const l = snapResize({ x: 13, y: 100, w: 87, h: 50 }, ["left"], { grid: 8, threshold: 0, targets: [] });
    expect(l.box).toEqual({ x: 16, y: 100, w: 84, h: 50 });
  });

  it("maps transformer anchors to edges", () => {
    expect(anchorEdges("top-left")).toEqual(["left", "top"]);
    expect(anchorEdges("middle-right")).toEqual(["right"]);
    expect(anchorEdges("bottom-center")).toEqual(["bottom"]);
    expect(anchorEdges(null)).toEqual([]);
  });

  it("computes union boxes", () => {
    expect(unionBox([{ x: 0, y: 10, w: 5, h: 5 }, { x: 20, y: 0, w: 10, h: 3 }])).toEqual({ x: 0, y: 0, w: 30, h: 15 });
    expect(unionBox([])).toBeNull();
  });
});
