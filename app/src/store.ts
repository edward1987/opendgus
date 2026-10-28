// Global editor state (zustand). Edits change the local project JSON, push an undo snapshot and are saved
// with a debounced PUT /api/project; the page preview is re-rendered by the backend after every save.
import { create } from "zustand";
import { Api, bridge } from "./lib/api";
import { createHistory, History, record, redo as hRedo, undo as hUndo } from "./lib/history";
import { allItems, findItem } from "./lib/project";
import type { Catalog, Project } from "./lib/types";
import i18n from "./i18n";

export type RightTab = "props" | "insert" | "vars" | "ai";
export type Mode = "edit" | "run";
export type DialogName = null | "validate" | "build" | "device" | "theme" | "display" | "mcp" | "settings" | "controller";

export interface Toast {
  id: number;
  kind: "info" | "error" | "success";
  text: string;
}

export interface Preview {
  pageId: number;
  url: string;
  img: HTMLImageElement;
  issues: string[];
}

interface State {
  api: Api | null;
  booting: boolean;
  backendError: string | null;
  smoke: boolean;
  /** smoke runs that must finish their own scene (AI demo, Run taps) before the screenshot */
  smokeAiDemo: string | null;
  smokeRun: string | null;
  mode: Mode;
  catalog: Catalog | null;
  folder: string | null;
  project: Project | null;
  pageId: number;
  selection: string[];
  history: History<Project>;
  saveState: "saved" | "pending" | "saving" | "error";
  preview: Preview | null;
  previewLoading: boolean;
  rightTab: RightTab;
  dialog: DialogName;
  toasts: Toast[];
  vpMap: Record<string, string> | null; // from the last build
  live: "ws" | "poll" | "off";
  zoom: number | null; // null = fit
  viewCenter: { x: number; y: number };
  rendered: boolean;

  boot(): Promise<void>;
  openProject(folder: string): Promise<void>;
  createProject(args: Record<string, unknown>, displayPatch?: Record<string, unknown>): Promise<void>;
  closeProject(): Promise<void>;
  commit(next: Project, coalesce?: string | null): void;
  /** Run a backend tool that edits project.json and adopt the result (undoable, no "changed outside" toast). */
  applyTool<T = unknown>(name: string, args?: Record<string, unknown>): Promise<T>;
  undo(): void;
  redo(): void;
  select(ids: string[], additive?: boolean): void;
  setPage(id: number): void;
  setRightTab(t: RightTab): void;
  setDialog(d: DialogName): void;
  toast(text: string, kind?: Toast["kind"]): void;
  flushSave(): Promise<void>;
  refreshPreview(immediate?: boolean): void;
  setZoom(z: number | null): void;
  setViewCenter(c: { x: number; y: number }): void;
  setVpMap(m: Record<string, string> | null): void;
  markRendered(force?: boolean): void;
  setMode(m: Mode): void;
}

let saveTimer: ReturnType<typeof setTimeout> | undefined;
let saving: Promise<void> | null = null;
let saveAgain = false;
let savedJson: string | null = null; // last JSON the server confirmed (to recognise our own writes)
let previewTimer: ReturnType<typeof setTimeout> | undefined;
let previewSeq = 0;
let unwatch: (() => void) | null = null;
let toastSeq = 0;

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("image load failed"));
    img.src = url;
  });
}

export const useStore = create<State>((set, get) => {
  const keepSelection = (p: Project, ids: string[]) => ids.filter((id) => findItem(p, id));

  const adopt = (folder: string, project: Project) => {
    savedJson = JSON.stringify(project);
    const pageId = project.pages.some((p) => p.id === get().pageId) ? get().pageId : project.pages[0]?.id ?? 0;
    set({ folder, project, pageId, saveState: "saved" });
  };

  const onRemoteChange = async () => {
    const { api, project } = get();
    if (!api || !project) return;
    try {
      const r = await api.getProject();
      const json = JSON.stringify(r.project);
      if (json === savedJson) return; // our own write
      if (get().saveState !== "saved") {
        // Local edits pending: last write wins -> our save goes out and overwrites the external change.
        await get().flushSave();
        return;
      }
      const cur = get().project;
      set((s) => ({
        history: cur ? record(s.history, cur) : s.history,
        selection: keepSelection(r.project, s.selection),
      }));
      adopt(r.folder, r.project);
      get().refreshPreview(true);
      get().toast(i18n.t("toast.externalChange"), "info");
    } catch {
      /* backend busy; next event will retry */
    }
  };

  const startEditor = async (folder: string, project: Project) => {
    const { api } = get();
    unwatch?.();
    unwatch = api!.watch(() => void onRemoteChange(), (m) => set({ live: m }));
    set({ history: createHistory(), selection: [], pageId: project.pages[0]?.id ?? 0, zoom: null, vpMap: null, rightTab: "props", rendered: false, mode: "edit" });
    adopt(folder, project);
    void bridge.recentAdd(folder, project.name);
    get().refreshPreview(true);
  };

  return {
    api: null,
    booting: true,
    backendError: null,
    smoke: false,
    smokeAiDemo: null,
    smokeRun: null,
    mode: "edit",
    catalog: null,
    folder: null,
    project: null,
    pageId: 0,
    selection: [],
    history: createHistory(),
    saveState: "saved",
    preview: null,
    previewLoading: false,
    rightTab: "props",
    dialog: null,
    toasts: [],
    vpMap: null,
    live: "off",
    zoom: null,
    viewCenter: { x: 0, y: 0 },
    rendered: false,

    async boot() {
      const cfg = await bridge.getConfig();
      if (!cfg.port || !cfg.token) {
        set({ booting: false, backendError: cfg.backendError ?? "backend not available", smoke: cfg.smoke });
        return;
      }
      if (cfg.lang) void i18n.changeLanguage(cfg.lang);
      const api = new Api(cfg.port, cfg.token);
      set({ api, smoke: cfg.smoke, smokeAiDemo: cfg.smokeAiDemo ?? null, smokeRun: cfg.smokeRun ?? null });
      try {
        const [catalog, health] = await Promise.all([api.catalog(), api.health()]);
        set({ catalog });
        if (health.project) {
          const r = await api.getProject();
          await startEditor(r.folder, r.project);
          const sel = (cfg.select ?? []).filter((id) => findItem(r.project, id));
          if (sel.length) {
            const f = findItem(r.project, sel[0])!;
            get().setPage(f.page.id);
            set({ selection: sel });
          }
          if (cfg.smokeAiDemo !== null && cfg.smokeAiDemo !== undefined) set({ rightTab: "ai" });
          if (cfg.smokeRun !== null && cfg.smokeRun !== undefined) set({ mode: "run" });
          if (cfg.smokeDialog === "mcp") set({ dialog: "mcp", rightTab: "ai" });
          else if (cfg.smokeDialog) set({ dialog: cfg.smokeDialog as DialogName });
        }
      } catch (e) {
        set({ backendError: errText(e) });
      }
      set({ booting: false });
    },

    async openProject(folder) {
      const { api } = get();
      if (!api) return;
      await get().flushSave();
      await api.tool("open_project", { folder });
      const r = await api.getProject();
      await startEditor(r.folder, r.project);
    },

    async createProject(args, displayPatch) {
      const { api } = get();
      if (!api) return;
      await get().flushSave();
      await api.tool("create_project", args);
      let r = await api.getProject();
      if (displayPatch) {
        // e.g. a catalog display used in portrait: keep its profile (flash, CPU) with width/height swapped
        const p = { ...r.project, display: { ...r.project.display, ...displayPatch } };
        r = { folder: r.folder, project: (await api.putProject(p)).project };
      }
      await startEditor(r.folder, r.project);
    },

    async closeProject() {
      await get().flushSave();
      unwatch?.();
      unwatch = null;
      const pv = get().preview;
      if (pv) URL.revokeObjectURL(pv.url);
      set({ project: null, folder: null, preview: null, selection: [], history: createHistory() });
    },

    commit(next, coalesce = null) {
      const cur = get().project;
      if (!cur || next === cur) return;
      set((s) => ({
        project: next,
        history: record(s.history, cur, coalesce),
        selection: keepSelection(next, s.selection),
        saveState: s.saveState === "saving" ? "saving" : "pending",
      }));
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => void get().flushSave(), 150);
    },

    async applyTool<T>(name: string, args: Record<string, unknown> = {}) {
      const { api } = get();
      if (!api) throw new Error("backend not available");
      await get().flushSave();
      const before = get().project;
      const out = await api.tool<T>(name, args);
      const r = await api.getProject();
      if (before) set((s) => ({ history: record(s.history, before) }));
      set((s) => ({ selection: keepSelection(r.project, s.selection) }));
      adopt(r.folder, r.project);
      get().refreshPreview(true);
      return out;
    },

    undo() {
      const { history, project } = get();
      if (!project) return;
      const r = hUndo(history, project);
      if (!r) return;
      set((s) => ({ history: r[0], project: r[1], selection: keepSelection(r[1], s.selection), saveState: "pending" }));
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => void get().flushSave(), 150);
    },

    redo() {
      const { history, project } = get();
      if (!project) return;
      const r = hRedo(history, project);
      if (!r) return;
      set((s) => ({ history: r[0], project: r[1], selection: keepSelection(r[1], s.selection), saveState: "pending" }));
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => void get().flushSave(), 150);
    },

    async flushSave() {
      clearTimeout(saveTimer);
      if (saving) {
        saveAgain = true;
        return saving;
      }
      const { api, project, saveState } = get();
      if (!api || !project || saveState === "saved") return;
      set({ saveState: "saving" });
      saving = (async () => {
        try {
          const r = await api.putProject(project);
          savedJson = JSON.stringify(r.project);
          // Adopt the server's normalised copy only if nothing changed meanwhile.
          if (get().project === project) set({ project: r.project, saveState: saveAgain ? "pending" : "saved" });
          else set({ saveState: "pending" });
          get().refreshPreview();
        } catch (e) {
          set({ saveState: "error" });
          get().toast(i18n.t("toast.saveFailed", { error: errText(e) }), "error");
        }
      })();
      try {
        await saving;
      } finally {
        saving = null;
        if (saveAgain || get().saveState === "pending") {
          saveAgain = false;
          await get().flushSave();
        }
      }
    },

    refreshPreview(immediate = false) {
      clearTimeout(previewTimer);
      const run = async () => {
        const { api, pageId, project } = get();
        if (!api || !project || !project.pages.some((p) => p.id === pageId)) return;
        const seq = ++previewSeq;
        set({ previewLoading: true });
        try {
          const { url, issues } = await api.preview(pageId);
          const img = await loadImage(url);
          if (seq !== previewSeq) {
            URL.revokeObjectURL(url);
            return;
          }
          const old = get().preview;
          set({ preview: { pageId, url, img, issues }, previewLoading: false });
          if (old) setTimeout(() => URL.revokeObjectURL(old.url), 1000);
        } catch (e) {
          if (seq === previewSeq) set({ previewLoading: false });
        }
      };
      if (immediate) void run();
      else previewTimer = setTimeout(run, 120);
    },

    select(ids, additive = false) {
      set((s) => {
        if (!additive) return { selection: ids };
        const sel = new Set(s.selection);
        for (const id of ids) sel.has(id) ? sel.delete(id) : sel.add(id);
        return { selection: [...sel] };
      });
    },

    setPage(id) {
      if (id === get().pageId) return;
      set({ pageId: id, selection: [] });
      get().refreshPreview(true);
    },

    setRightTab: (t) => set({ rightTab: t }),
    setMode: (m) => set({ mode: m, selection: m === "run" ? [] : get().selection }),
    setDialog: (d) => set({ dialog: d }),
    toast(text, kind = "info") {
      const id = ++toastSeq;
      set((s) => ({ toasts: [...s.toasts.slice(-3), { id, kind, text }] }));
      setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), kind === "error" ? 7000 : 3500);
    },
    setZoom: (z) => set({ zoom: z }),
    setViewCenter: (c) => set({ viewCenter: c }),
    setVpMap: (m) => set({ vpMap: m }),
    markRendered(force = false) {
      if (get().rendered) return;
      // AI-demo / Run smoke scenes signal readiness themselves once their content is on screen
      if (!force && (get().smokeAiDemo !== null || get().smokeRun !== null)) return;
      set({ rendered: true });
      bridge.signalRendered();
    },
  };
});

/** Current page object. */
export const currentPage = (s: { project: Project | null; pageId: number }) =>
  s.project?.pages.find((p) => p.id === s.pageId) ?? null;

export const selectedItems = (s: { project: Project | null; pageId: number; selection: string[] }) => {
  const pg = currentPage(s);
  if (!pg) return [];
  const sel = new Set(s.selection);
  return allItems(pg).filter((i) => sel.has(i.id));
};
