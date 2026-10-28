// HTTP/WebSocket client for the Python backend (src/opendgus/server.py).
import type { AiProvider } from "./aiSettings";
import type { McpCommand } from "./mcpConfig";
import type { Catalog, Project } from "./types";

export interface Bridge {
  getConfig(): Promise<{
    port: number | null;
    token: string | null;
    backendError: string | null;
    initialProject: string | null;
    smoke: boolean;
    select?: string[];
    lang?: string | null;
    smokeAiDemo?: string | null;
    smokeRun?: string | null;
    smokeDialog?: string | null;
    version: string;
    platform: string;
    /** Command that starts the MCP server (bundled sidecar when installed), for external AI apps. */
    mcp?: McpCommand | null;
  }>;
  openFolder(opts?: { title?: string; create?: boolean }): Promise<string | null>;
  openImage(title?: string): Promise<string | null>;
  importAsset(folder: string, file: string): Promise<string>;
  recentList(): Promise<{ folder: string; name: string; opened: string }[]>;
  recentAdd(folder: string, name: string): Promise<void>;
  recentRemove(folder: string): Promise<void>;
  openPath(p: string): Promise<string>;
  defaultProjectsDir(): Promise<string>;
  signalRendered(): void;
  settingsGet(key: string): Promise<unknown>;
  settingsSet(key: string, value: unknown): Promise<boolean>;
  setSecret(name: string, value: string): Promise<{ ok: boolean; persisted: boolean }>;
  getSecret(name: string): Promise<string | null>;
  deleteSecret(name: string): Promise<void>;
  secretsEncrypted(): Promise<boolean>;
}

declare global {
  interface Window {
    opendgus?: Bridge;
  }
}

/** Browser fallback (plain `vite` without Electron): talk to a backend given by ?port=&token= in the URL.
 *  Settings go to localStorage; secrets stay in memory only (no safe place to keep them in a browser). */
function browserBridge(): Bridge {
  const q = new URLSearchParams(location.search);
  const secrets = new Map<string, string>();
  return {
    getConfig: async () => ({
      port: q.get("port") ? Number(q.get("port")) : null,
      token: q.get("token"),
      backendError: q.get("port") ? null : "Run inside Electron (npm run dev), or open with ?port=&token= of a running backend.",
      initialProject: null,
      smoke: false,
      version: "dev",
      platform: "web",
    }),
    openFolder: async (o) => window.prompt(o?.title ?? "Folder"),
    openImage: async (t) => window.prompt(t ?? "Image path"),
    importAsset: async (_f, file) => file,
    recentList: async () => [],
    recentAdd: async () => undefined,
    recentRemove: async () => undefined,
    openPath: async () => "",
    defaultProjectsDir: async () => "",
    signalRendered: () => undefined,
    settingsGet: async (key) => {
      try {
        return JSON.parse(localStorage.getItem(`opendgus.${key}`) ?? "null");
      } catch {
        return null;
      }
    },
    settingsSet: async (key, value) => {
      try {
        localStorage.setItem(`opendgus.${key}`, JSON.stringify(value));
        return true;
      } catch {
        return false;
      }
    },
    setSecret: async (name, value) => {
      secrets.set(name, value);
      return { ok: true, persisted: false };
    },
    getSecret: async (name) => secrets.get(name) ?? null,
    deleteSecret: async (name) => void secrets.delete(name),
    secretsEncrypted: async () => false,
  };
}

export const bridge: Bridge = window.opendgus ?? browserBridge();

export class ApiError extends Error {}

export class Api {
  readonly base: string;
  constructor(readonly port: number, readonly token: string) {
    this.base = `http://127.0.0.1:${port}`;
  }

  private async req<T>(path: string, init: RequestInit = {}): Promise<T> {
    const r = await fetch(this.base + path, {
      ...init,
      headers: { "X-OpenDGUS-Token": this.token, "Content-Type": "application/json", ...(init.headers || {}) },
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok || body?.ok === false) throw new ApiError(body?.error ?? body?.detail ?? `${r.status} ${r.statusText}`);
    return body as T;
  }

  health() {
    return this.req<{ ok: boolean; version: string; project: string | null }>("/api/health");
  }

  async tool<T = any>(name: string, args: Record<string, unknown> = {}): Promise<T> {
    const r = await this.req<{ ok: boolean; result: T }>(`/api/tools/${name}`, { method: "POST", body: JSON.stringify(args) });
    return r.result;
  }

  getProject() {
    return this.req<{ folder: string; project: Project }>("/api/project");
  }

  putProject(project: Project) {
    return this.req<{ ok: boolean; project: Project }>("/api/project", { method: "PUT", body: JSON.stringify(project) });
  }

  catalog() {
    return this.req<Catalog>("/api/catalog");
  }

  /** Page render: returns an object URL (caller revokes) and the compiler issues. */
  async preview(page: number, scale = 1, pressed: string[] = []): Promise<{ url: string; issues: string[] }> {
    const q = new URLSearchParams({ scale: String(scale) });
    if (pressed.length) q.set("pressed", pressed.join(","));
    const r = await fetch(`${this.base}/api/preview/${page}.png?${q}`, { headers: { "X-OpenDGUS-Token": this.token } });
    if (!r.ok) throw new ApiError(`preview ${r.status}`);
    let issues: string[] = [];
    try {
      issues = JSON.parse(r.headers.get("X-OpenDGUS-Issues") || "[]");
    } catch {
      issues = [];
    }
    return { url: URL.createObjectURL(await r.blob()), issues };
  }

  /** URL of an icon glyph PNG (usable as <img src>; the token goes in the query). */
  iconUrl(name: string, size = 32, color = "#E2E8F0") {
    const q = new URLSearchParams({ size: String(size), color, token: this.token });
    return `${this.base}/api/icon/${encodeURIComponent(name)}.png?${q}`;
  }

  /** URL of a template thumbnail rendered at the given display size. */
  templateUrl(id: string, width: number, height: number, scale: number, page = 0) {
    const q = new URLSearchParams({ width: String(width), height: String(height), page: String(page), scale: scale.toFixed(3), token: this.token });
    return `${this.base}/api/template/${encodeURIComponent(id)}.png?${q}`;
  }

  aiProviders() {
    return this.req<AiProvider[]>("/api/ai/providers");
  }

  /** WebSocket for the AI designer (one per chat panel). */
  aiSocket() {
    return new WebSocket(`ws://127.0.0.1:${this.port}/ws/ai?token=${encodeURIComponent(this.token)}`);
  }

  /** Live updates over /ws; reconnects automatically. If the backend has no WebSocket support (uvicorn without
   *  `websockets`/`wsproto`), falls back to polling: onChange() is then called every 2 s and the caller compares. */
  watch(onChange: () => void, onStatus?: (mode: "ws" | "poll" | "off") => void): () => void {
    let ws: WebSocket | null = null;
    let closed = false;
    let everOpened = false;
    let failures = 0;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let poll: ReturnType<typeof setInterval> | undefined;
    const startPolling = () => {
      if (poll) return;
      onStatus?.("poll");
      poll = setInterval(onChange, 2000);
    };
    const open = () => {
      ws = new WebSocket(`ws://127.0.0.1:${this.port}/ws?token=${encodeURIComponent(this.token)}`);
      ws.onopen = () => {
        everOpened = true;
        failures = 0;
        if (poll) clearInterval(poll);
        poll = undefined;
        onStatus?.("ws");
      };
      ws.onmessage = (ev) => {
        try {
          if (JSON.parse(ev.data).type === "project_changed") onChange();
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        if (closed) return;
        failures++;
        if (!everOpened && failures >= 2) startPolling();
        else onStatus?.(poll ? "poll" : "off");
        retry = setTimeout(open, everOpened ? 1500 : 10000);
      };
    };
    open();
    return () => {
      closed = true;
      clearTimeout(retry);
      if (poll) clearInterval(poll);
      ws?.close();
    };
  }
}
