import { describe, expect, it } from "vitest";
import { fitSize, holdMs, parseCaption, parseTapScript, parseVarValue, toDevice } from "./emulator";

describe("emulator helpers", () => {
  it("short presses are taps, long presses are holds (capped)", () => {
    expect(holdMs(80)).toBe(0);
    expect(holdMs(349)).toBe(0);
    expect(holdMs(800.4)).toBe(800);
    expect(holdMs(60000)).toBe(10000);
    expect(holdMs(NaN)).toBe(0);
  });
  it("maps screen coordinates to device pixels", () => {
    const rect = { left: 100, top: 50, width: 512, height: 300 };
    expect(toDevice(100, 50, rect, 1024, 600)).toEqual({ x: 0, y: 0 });
    expect(toDevice(356, 200, rect, 1024, 600)).toEqual({ x: 512, y: 300 });
    expect(toDevice(9999, -5, rect, 1024, 600)).toEqual({ x: 1023, y: 0 });
  });
  it("fits keeping the aspect ratio", () => {
    expect(fitSize(1000, 1000, 1024, 600)).toEqual({ w: 1000, h: 585 });
    expect(fitSize(1000, 300, 1024, 600)).toEqual({ w: 512, h: 300 });
    expect(fitSize(0, 300, 1024, 600)).toEqual({ w: 0, h: 0 });
  });
  it("parses tap / set / start captions", () => {
    const tap = parseCaption('{"hit": "c3", "page": 1, "changed": {"temp": [20, 21]}}');
    expect(tap).toMatchObject({ page: 1, hit: "c3", changes: [{ name: "temp", before: 20, after: 21 }] });
    const set = parseCaption('{"page": 0, "temp": 25}', "temp");
    expect(set.changes).toEqual([{ name: "temp", before: undefined, after: 25 }]);
    const cut = parseCaption('{"page": 0, "ms": 12, "pre');
    expect(cut).toMatchObject({ page: null, changes: [] });
  });
  it("parses smoke tap scripts and typed values", () => {
    expect(parseTapScript("10,20;30,40,900; bad;5")).toEqual([{ x: 10, y: 20, hold: 0 }, { x: 30, y: 40, hold: 900 }]);
    expect(parseTapScript(null)).toEqual([]);
    expect(parseVarValue(" -12 ")).toBe(-12);
    expect(parseVarValue("1.5")).toBeNull();
    expect(parseVarValue("")).toBeNull();
  });
});
