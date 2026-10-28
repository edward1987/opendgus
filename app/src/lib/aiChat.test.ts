import { describe, expect, it } from "vitest";
import { addUserMessage, AiEvent, applyEvent, emptyChat, inputPreview, parseEvent, stopTurn } from "./aiChat";

const run = (events: AiEvent[], s = addUserMessage(emptyChat(), "hi")) => events.reduce(applyEvent, s);

describe("chat reducer", () => {
  it("adds the user message and marks the turn running", () => {
    const s = addUserMessage(emptyChat(), "Make it modern");
    expect(s.running).toBe(true);
    expect(s.items).toEqual([{ kind: "user", key: 1, text: "Make it modern" }]);
  });

  it("merges streamed text deltas into one bubble, separated by tool calls", () => {
    const s = run([
      { type: "text", delta: "Let me " },
      { type: "text", delta: "look." },
      { type: "tool_call", id: "t1", name: "get_project", input: {} },
      { type: "tool_result", id: "t1", name: "get_project", ok: true, summary: "{...}" },
      { type: "text", delta: "Done." },
    ]);
    expect(s.items.map((i) => i.kind)).toEqual(["user", "assistant", "tool", "assistant"]);
    expect(s.items[1]).toMatchObject({ text: "Let me look." });
    expect(s.items[2]).toMatchObject({ status: "ok", summary: "{...}", name: "get_project" });
    expect(new Set(s.items.map((i) => i.key)).size).toBe(4);
  });

  it("keeps thinking separate from the answer", () => {
    const s = run([{ type: "thinking", delta: "a" }, { type: "thinking", delta: "b" }, { type: "text", delta: "c" }]);
    expect(s.items.slice(1)).toMatchObject([{ kind: "thinking", text: "ab" }, { kind: "assistant", text: "c" }]);
  });

  it("matches tool results by id, even out of order", () => {
    const s = run([
      { type: "tool_call", id: "a", name: "x" },
      { type: "tool_call", id: "b", name: "y" },
      { type: "tool_result", id: "a", name: "x", ok: false, summary: "boom" },
    ]);
    expect(s.items[1]).toMatchObject({ callId: "a", status: "error", summary: "boom" });
    expect(s.items[2]).toMatchObject({ callId: "b", status: "running" });
  });

  it("renders images as data URLs and shows notices and errors", () => {
    const s = run([{ type: "image", png_b64: "AAA", caption: "page 0" }, { type: "notice", message: "n" }, { type: "error", message: "e" }]);
    expect(s.items.slice(1)).toMatchObject([
      { kind: "image", src: "data:image/png;base64,AAA", caption: "page 0" },
      { kind: "notice", text: "n" },
      { kind: "error", text: "e" },
    ]);
  });

  it("done ends the turn, fails dangling tool calls and reports unusual stop reasons", () => {
    const s = run([{ type: "tool_call", id: "a", name: "x" }, { type: "done", stop_reason: "end_turn" }]);
    expect(s.running).toBe(false);
    expect(s.items[1]).toMatchObject({ status: "error" });
    expect(s.items).toHaveLength(2);
    const t = run([{ type: "done", stop_reason: "pause_turn" }]);
    expect(t.items[t.items.length - 1]).toMatchObject({ kind: "notice", text: "stop: pause_turn" });
  });

  it("stop marks the turn finished locally; stop when idle is a no-op", () => {
    const s = stopTurn(run([{ type: "tool_call", id: "a", name: "x" }]), "Stopped");
    expect(s.running).toBe(false);
    expect(s.items.map((i) => i.kind)).toEqual(["user", "tool", "notice"]);
    expect(stopTurn(s, "again")).toBe(s);
  });

  it("reset clears the transcript", () => {
    expect(run([{ type: "text", delta: "x" }, { type: "reset" }])).toEqual(emptyChat());
  });
});

describe("parseEvent / inputPreview", () => {
  it("filters by session and rejects junk", () => {
    expect(parseEvent('{"type":"text","delta":"x","session":"s1"}', "s1")).toMatchObject({ type: "text" });
    expect(parseEvent('{"type":"text","delta":"x","session":"s2"}', "s1")).toBeNull();
    expect(parseEvent("not json", "s1")).toBeNull();
    expect(parseEvent('{"nope":1}', "s1")).toBeNull();
  });
  it("truncates long inputs", () => {
    expect(inputPreview({ a: 1 })).toBe('{"a":1}');
    expect(inputPreview("x".repeat(50), 10)).toHaveLength(10);
    expect(inputPreview(null)).toBe("");
  });
});
