import { describe, expect, it } from "vitest";
import { canRedo, canUndo, createHistory, HISTORY_LIMIT, record, redo, undo } from "./history";

describe("undo stack", () => {
  it("undoes and redoes snapshots in order", () => {
    let h = createHistory<number>();
    h = record(h, 0, null, 1000);
    h = record(h, 1, null, 2000);
    const u1 = undo(h, 2)!;
    expect(u1[1]).toBe(1);
    const u2 = undo(u1[0], 1)!;
    expect(u2[1]).toBe(0);
    expect(canUndo(u2[0])).toBe(false);
    const r1 = redo(u2[0], 0)!;
    expect(r1[1]).toBe(1);
    expect(canRedo(r1[0])).toBe(true);
  });

  it("returns null when nothing to undo/redo", () => {
    const h = createHistory<string>();
    expect(undo(h, "x")).toBeNull();
    expect(redo(h, "x")).toBeNull();
  });

  it("coalesces edits with the same key inside the time window", () => {
    let h = createHistory<string>();
    h = record(h, "a", "typing", 1000);
    h = record(h, "ab", "typing", 1300);
    h = record(h, "abc", "typing", 1600);
    expect(h.past).toEqual(["a"]);
    h = record(h, "abcd", "typing", 5000); // window expired
    expect(h.past).toEqual(["a", "abcd"]);
    h = record(h, "x", "other", 5100);
    expect(h.past.length).toBe(3);
  });

  it("a new edit clears the redo stack", () => {
    let h = createHistory<number>();
    h = record(h, 0, null, 1);
    h = undo(h, 1)![0];
    expect(canRedo(h)).toBe(true);
    h = record(h, 0, null, 2);
    expect(canRedo(h)).toBe(false);
  });

  it("is bounded", () => {
    let h = createHistory<number>();
    for (let i = 0; i < HISTORY_LIMIT + 50; i++) h = record(h, i, null, i * 10000);
    expect(h.past.length).toBe(HISTORY_LIMIT);
    expect(h.past[0]).toBe(50);
  });
});
