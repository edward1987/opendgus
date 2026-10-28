// Chat transcript for the AI designer: a pure reducer over the events streamed by /ws/ai
// (see src/opendgus/ai/agent.py) plus the local actions (user message, stop, reset).

export type AiEvent =
  | { type: "text"; delta: string }
  | { type: "thinking"; delta: string }
  | { type: "tool_call"; id: string; name: string; input?: unknown }
  | { type: "tool_result"; id: string; name: string; ok: boolean; summary?: string }
  | { type: "image"; png_b64: string; caption?: string }
  | { type: "notice"; message: string }
  | { type: "error"; message: string }
  | { type: "done"; stop_reason?: string | null }
  | { type: "reset" };

export type ChatItem =
  | { kind: "user"; key: number; text: string }
  | { kind: "assistant"; key: number; text: string }
  | { kind: "thinking"; key: number; text: string }
  | { kind: "tool"; key: number; callId: string; name: string; input: unknown; status: "running" | "ok" | "error"; summary: string }
  | { kind: "image"; key: number; src: string; caption: string }
  | { kind: "notice"; key: number; text: string }
  | { kind: "error"; key: number; text: string };

export interface ChatState {
  items: ChatItem[];
  running: boolean;
  seq: number;
}

export const emptyChat = (): ChatState => ({ items: [], running: false, seq: 0 });

/** Stop reasons that end a turn normally (anything else is reported as a notice). */
const NORMAL_STOPS = new Set(["end_turn", "stop", "stop_sequence", "tool_use", "error", "refusal", "max_tokens", "tool_rounds", "cancelled", "busy", ""]);

function push(s: ChatState, item: DistributiveOmit<ChatItem, "key">): ChatState {
  return { ...s, seq: s.seq + 1, items: [...s.items, { ...item, key: s.seq + 1 } as ChatItem] };
}

type DistributiveOmit<T, K extends keyof any> = T extends any ? Omit<T, K> : never;

/** Append streamed text to the last item if it is of the same kind (so a reply stays one bubble). */
function appendDelta(s: ChatState, kind: "assistant" | "thinking", delta: string): ChatState {
  if (!delta) return s;
  const last = s.items[s.items.length - 1];
  if (last && last.kind === kind) {
    const items = s.items.slice(0, -1);
    items.push({ ...last, text: last.text + delta });
    return { ...s, items };
  }
  return push(s, { kind, text: delta });
}

export function applyEvent(s: ChatState, ev: AiEvent): ChatState {
  switch (ev.type) {
    case "text":
      return appendDelta(s, "assistant", ev.delta ?? "");
    case "thinking":
      return appendDelta(s, "thinking", ev.delta ?? "");
    case "tool_call":
      return push(s, { kind: "tool", callId: ev.id, name: ev.name, input: ev.input ?? null, status: "running", summary: "" });
    case "tool_result": {
      for (let i = s.items.length - 1; i >= 0; i--) {
        const it = s.items[i];
        if (it.kind === "tool" && it.callId === ev.id) {
          const items = s.items.slice();
          items[i] = { ...it, status: ev.ok ? "ok" : "error", summary: ev.summary ?? "" };
          return { ...s, items };
        }
      }
      // result without a call (should not happen): show it anyway
      return push(s, { kind: "tool", callId: ev.id, name: ev.name, input: null, status: ev.ok ? "ok" : "error", summary: ev.summary ?? "" });
    }
    case "image":
      return push(s, { kind: "image", src: `data:image/png;base64,${ev.png_b64}`, caption: ev.caption ?? "" });
    case "notice":
      return push(s, { kind: "notice", text: ev.message });
    case "error":
      return push(s, { kind: "error", text: ev.message });
    case "done": {
      const items = s.items.map((it) => (it.kind === "tool" && it.status === "running" ? { ...it, status: "error" as const } : it));
      const next = { ...s, items, running: false };
      const reason = ev.stop_reason ?? "";
      return NORMAL_STOPS.has(reason) ? next : push(next, { kind: "notice", text: `stop: ${reason}` });
    }
    case "reset":
      return emptyChat();
    default:
      return s;
  }
}

export function addUserMessage(s: ChatState, text: string): ChatState {
  return { ...push(s, { kind: "user", text }), running: true };
}

/** Local stop (the socket is dropped): open tool calls are marked as failed. */
export function stopTurn(s: ChatState, notice: string): ChatState {
  if (!s.running) return s;
  const items = s.items.map((it) => (it.kind === "tool" && it.status === "running" ? { ...it, status: "error" as const } : it));
  return push({ ...s, items, running: false }, { kind: "notice", text: notice });
}

/** Parse one WebSocket message; returns null for anything that is not an event of `session`. */
export function parseEvent(data: unknown, session: string): AiEvent | null {
  let msg: any;
  try {
    msg = typeof data === "string" ? JSON.parse(data) : data;
  } catch {
    return null;
  }
  if (!msg || typeof msg !== "object" || typeof msg.type !== "string") return null;
  if (msg.session !== undefined && msg.session !== session) return null;
  return msg as AiEvent;
}

/** Short one-line view of a tool call's input for the chip tooltip. */
export function inputPreview(input: unknown, max = 300): string {
  if (input === null || input === undefined) return "";
  let s: string;
  try {
    s = typeof input === "string" ? input : JSON.stringify(input);
  } catch {
    s = String(input);
  }
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}
