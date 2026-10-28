// AI designer state: provider settings, in-memory API keys, the chat transcript and the /ws/ai socket.
// Lives outside the AI tab component so a running conversation survives switching tabs.
import { create } from "zustand";
import i18n from "./i18n";
import { addUserMessage, AiEvent, applyEvent, ChatState, emptyChat, parseEvent, stopTurn } from "./lib/aiChat";
import {
  AiProvider, AiSettings, chatRequest, DEFAULT_SETTINGS, normalizeSettings, ProviderId, secretName, SETTINGS_KEY,
} from "./lib/aiSettings";
import { bridge } from "./lib/api";
import { useStore } from "./store";

interface AiState {
  loaded: boolean;
  providers: AiProvider[];
  providersError: string | null;
  settings: AiSettings;
  /** API keys, decrypted on demand by the main process; kept in memory only */
  keys: Partial<Record<ProviderId, string | null>>;
  keyPersisted: Partial<Record<ProviderId, boolean>>;
  chat: ChatState;
  session: string;
  settingsOpen: boolean;

  load(): Promise<void>;
  updateSettings(s: AiSettings): void;
  setApiKey(p: ProviderId, key: string): Promise<void>;
  removeApiKey(p: ProviderId): Promise<void>;
  setSettingsOpen(open: boolean): void;
  send(text: string): void;
  stop(): void;
  reset(): void;
  loadDemo(variant: string): Promise<void>;
}

const newSession = () => (crypto.randomUUID ? crypto.randomUUID() : `s${Date.now()}${Math.random().toString(36).slice(2)}`);

let ws: WebSocket | null = null;
let pending: string | null = null; // request to send once the socket opens

export const currentProvider = (s: Pick<AiState, "providers" | "settings">) =>
  s.providers.find((p) => p.id === s.settings.provider) ?? s.providers[0];

export const useAi = create<AiState>((set, get) => {
  const dispatch = (ev: AiEvent) => set((s) => ({ chat: applyEvent(s.chat, ev) }));

  const openSocket = (): WebSocket | null => {
    const api = useStore.getState().api;
    if (!api) return null;
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return ws;
    const sock = api.aiSocket();
    ws = sock;
    sock.onopen = () => {
      if (pending && sock === ws) {
        sock.send(pending);
        pending = null;
      }
    };
    sock.onmessage = (m) => {
      if (sock !== ws) return;
      const ev = parseEvent(m.data, get().session);
      if (ev) dispatch(ev);
    };
    sock.onclose = () => {
      if (sock !== ws) return; // replaced on purpose (stop / reset)
      ws = null;
      pending = null;
      if (get().chat.running) set((s) => ({ chat: stopTurn(s.chat, i18n.t("ai.connectionLost")) }));
    };
    return sock;
  };

  const dropSocket = () => {
    const sock = ws;
    ws = null;
    pending = null;
    try {
      sock?.close();
    } catch {
      /* ignore */
    }
  };

  return {
    loaded: false,
    providers: [],
    providersError: null,
    settings: DEFAULT_SETTINGS,
    keys: {},
    keyPersisted: {},
    chat: emptyChat(),
    session: newSession(),
    settingsOpen: false,

    async load() {
      if (get().loaded) return;
      const api = useStore.getState().api;
      const [providers, raw] = await Promise.all([
        api ? api.aiProviders().catch((e: Error) => (set({ providersError: e.message }), [] as AiProvider[])) : Promise.resolve([]),
        bridge.settingsGet(SETTINGS_KEY).catch(() => null),
      ]);
      const settings = normalizeSettings(raw);
      const keys: Partial<Record<ProviderId, string | null>> = {};
      const keyPersisted: Partial<Record<ProviderId, boolean>> = {};
      const encrypted = await bridge.secretsEncrypted().catch(() => false);
      for (const p of providers) {
        if (!p.needs_key) continue;
        keys[p.id] = await bridge.getSecret(secretName(p.id)).catch(() => null);
        keyPersisted[p.id] = encrypted;
      }
      const prov = providers.find((p) => p.id === settings.provider) ?? providers[0];
      const missingKey = !!prov && prov.needs_key && !keys[prov.id];
      set({ loaded: true, providers, settings, keys, keyPersisted, settingsOpen: missingKey && useStore.getState().smokeAiDemo === null });
    },

    updateSettings(s) {
      set({ settings: s });
      void bridge.settingsSet(SETTINGS_KEY, s);
    },

    async setApiKey(p, key) {
      const k = key.trim();
      if (!k) return;
      const r = await bridge.setSecret(secretName(p), k);
      if (r.ok) set((s) => ({ keys: { ...s.keys, [p]: k }, keyPersisted: { ...s.keyPersisted, [p]: r.persisted } }));
    },

    async removeApiKey(p) {
      await bridge.deleteSecret(secretName(p));
      set((s) => ({ keys: { ...s.keys, [p]: null } }));
    },

    setSettingsOpen: (open) => set({ settingsOpen: open }),

    send(text) {
      const msg = text.trim();
      const st = get();
      const prov = currentProvider(st);
      if (!msg || st.chat.running || !prov) return;
      const req = JSON.stringify(chatRequest(st.settings, prov, st.keys[prov.id] ?? null, st.session, msg));
      set((s) => ({ chat: addUserMessage(s.chat, msg) }));
      // make sure the agent sees the latest local edits
      void useStore.getState().flushSave().finally(() => {
        const sock = openSocket();
        if (!sock) {
          dispatch({ type: "error", message: i18n.t("ai.sendFailed", { error: "no backend" }) });
          dispatch({ type: "done", stop_reason: "error" });
          return;
        }
        if (sock.readyState === WebSocket.OPEN) sock.send(req);
        else pending = req;
      });
    },

    stop() {
      // Ask the backend to cancel the running turn (it stops at the next event/tool boundary and keeps the
      // history valid). The socket stays open; "done" with stop_reason "cancelled" ends the turn.
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "stop", session: get().session }));
      } else {
        dropSocket();
      }
      set((s) => ({ chat: stopTurn(s.chat, i18n.t("ai.stopped")) }));
    },

    reset() {
      const old = get().session;
      if (get().chat.running) dropSocket();
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "reset", session: old }));
      set({ chat: emptyChat(), session: newSession() });
    },

    async loadDemo(variant) {
      // Canned transcript for the smoke screenshot (no network, no API key).
      await get().load();
      set({ keys: { anthropic: "demo", openai: "demo" }, settingsOpen: variant === "settings" });
      const { api, pageId } = useStore.getState();
      let png = "";
      if (api) {
        try {
          const r = await fetch(`${api.base}/api/preview/${pageId}.png?scale=0.5`, { headers: { "X-OpenDGUS-Token": api.token } });
          const blob = await r.blob();
          png = await new Promise<string>((resolve) => {
            const r = new FileReader();
            r.onload = () => resolve(String(r.result).split(",", 2)[1] ?? "");
            r.onerror = () => resolve("");
            r.readAsDataURL(blob);
          });
        } catch {
          png = "";
        }
      }
      let chat = addUserMessage(emptyChat(), i18n.t("ai.s1"));
      const events: AiEvent[] = [
        { type: "thinking", delta: "The page uses flat cards with small labels. I'll increase contrast, round the cards, " },
        { type: "thinking", delta: "enlarge the main values and align everything to the 8 px grid." },
        { type: "text", delta: "I'll start by reading the current page and theme." },
        { type: "tool_call", id: "t1", name: "get_project", input: {} },
        { type: "tool_result", id: "t1", name: "get_project", ok: true, summary: '{"name":"Home control","pages":3,"variables":9}' },
        { type: "tool_call", id: "t2", name: "set_theme", input: { radius: 22, colors: { surface: "#1B2436" } } },
        { type: "tool_result", id: "t2", name: "set_theme", ok: true, summary: '{"radius":22}' },
        { type: "tool_call", id: "t3", name: "update_item", input: { id: "c5", props: { size: 64 } } },
        { type: "tool_result", id: "t3", name: "update_item", ok: false, summary: "unknown prop 'size' for number; use font_size" },
        { type: "tool_call", id: "t4", name: "update_item", input: { id: "c5", props: { font_size: 64 } } },
        { type: "tool_result", id: "t4", name: "update_item", ok: true, summary: '{"id":"c5"}' },
        { type: "tool_call", id: "t5", name: "render_page", input: { page: 0 } },
        { type: "tool_result", id: "t5", name: "render_page", ok: true, summary: "page 0 rendered, no issues" },
        ...(png ? [{ type: "image", png_b64: png, caption: "page 0 · 1024×600" } as AiEvent] : []),
        { type: "text", delta: "Done. I rounded the cards (radius 22), darkened the surfaces for more contrast and made the " },
        { type: "text", delta: "temperature **64 px** so it reads from across the room. Undo with `Ctrl+Z` if you prefer the old look." },
        { type: "done", stop_reason: "end_turn" },
      ];
      chat = events.reduce(applyEvent, chat);
      chat = addUserMessage(chat, i18n.t("ai.s3"));
      chat = [
        { type: "text", delta: "Adding a gauge for `temp_room` next to the setpoint…" },
        { type: "tool_call", id: "t6", name: "add_control", input: { type: "gauge", var: "temp_room" } },
      ].reduce((c, e) => applyEvent(c, e as AiEvent), chat);
      set({ chat });
    },
  };
});

// A new project starts a new conversation.
useStore.subscribe((s, prev) => {
  if (s.folder !== prev.folder) useAi.getState().reset();
});
