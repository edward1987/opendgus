import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { duplicateItems, moveBy, removeItems, updateItems } from "../lib/project";
import { currentPage, selectedItems, useStore } from "../store";
import { CanvasView } from "./CanvasView";
import { BuildDialog, DeviceDialog, ValidateDialog } from "./Dialogs";
import { LeftPanel } from "./LeftPanel";
import { McpDialog } from "./McpDialog";
import { RightPanel } from "./RightPanel";
import { RunView } from "./RunView";
import { SettingsDialog } from "./SettingsDialog";
import { ThemeDialog } from "./ThemeDialog";
import { Toolbar } from "./Toolbar";

const NO_ISSUES: string[] = [];

const isTyping = (t: EventTarget | null) => {
  const el = t as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
};

export function Editor() {
  const dialog = useStore((s) => s.dialog);
  const setDialog = useStore((s) => s.setDialog);
  const mode = useStore((s) => s.mode);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTyping(e.target) || useStore.getState().dialog) return;
      const s = useStore.getState();
      if (s.mode === "run") {
        // Run mode: the design is read-only; Esc goes back to editing
        if (e.key === "Escape") s.setMode("edit");
        return;
      }
      const ctrl = e.ctrlKey || e.metaKey;
      const key = e.key.toLowerCase();
      if (ctrl && key === "z" && !e.shiftKey) { e.preventDefault(); s.undo(); return; }
      if (ctrl && (key === "y" || (key === "z" && e.shiftKey))) { e.preventDefault(); s.redo(); return; }
      if (ctrl && key === "s") { e.preventDefault(); void s.flushSave(); return; }
      if (ctrl && key === "0") { e.preventDefault(); s.setZoom(null); return; }
      if (ctrl && key === "1") { e.preventDefault(); s.setZoom(1); return; }
      if (ctrl && key === "a") {
        e.preventDefault();
        const pg = currentPage(s);
        if (pg) s.select([...pg.elements, ...pg.controls].map((i) => i.id));
        return;
      }
      if (!s.project || !s.selection.length) return;
      if (key === "escape") { s.select([]); return; }
      if (key === "delete" || key === "backspace") {
        e.preventDefault();
        s.commit(removeItems(s.project, s.selection));
        s.select([]);
        return;
      }
      if (ctrl && key === "d") {
        e.preventDefault();
        const [p, ids] = duplicateItems(s.project, s.selection);
        s.commit(p);
        s.select(ids);
        return;
      }
      const arrows: Record<string, [number, number]> = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, -1], arrowdown: [0, 1] };
      if (arrows[key]) {
        e.preventDefault();
        const step = e.shiftKey ? 10 : 1;
        const [dx, dy] = arrows[key];
        const moved = selectedItems(s).map((it) => moveBy(it, dx * step, dy * step));
        s.commit(updateItems(s.project, moved), "nudge:" + s.selection.join(","));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="editor">
      <Toolbar />
      <div className="editor-body">
        {mode === "run" ? <RunView /> : <><LeftPanel /><CanvasView /></>}
        <RightPanel />
      </div>
      <StatusBar />
      {dialog === "validate" && <ValidateDialog onClose={() => setDialog(null)} />}
      {dialog === "build" && <BuildDialog onClose={() => setDialog(null)} />}
      {dialog === "device" && <DeviceDialog onClose={() => setDialog(null)} />}
      {dialog === "theme" && <ThemeDialog onClose={() => setDialog(null)} />}
      {dialog === "mcp" && <McpDialog onClose={() => setDialog(null)} />}
      {dialog === "settings" && <SettingsDialog onClose={() => setDialog(null)} />}
    </div>
  );
}

function StatusBar() {
  const { t } = useTranslation();
  const saveState = useStore((s) => s.saveState);
  const live = useStore((s) => s.live);
  const folder = useStore((s) => s.folder);
  const project = useStore((s) => s.project)!;
  const issues = useStore((s) => s.preview?.issues ?? NO_ISSUES);
  const loading = useStore((s) => s.previewLoading);
  const setDialog = useStore((s) => s.setDialog);
  return (
    <div className="statusbar">
      <span className={`dot ${saveState}`} />
      <span>{t(`status.${saveState}`)}</span>
      <span className="sep" />
      <span className="muted" title={folder ?? ""}>{folder}</span>
      <span className="spacer" />
      {loading && <span className="muted">{t("status.rendering")}</span>}
      {issues.length > 0 && (
        <button className="link warn" onClick={() => setDialog("validate")}>
          {t("status.issues", { count: issues.length })}
        </button>
      )}
      <span className="sep" />
      <span className="muted">{project.display.width}×{project.display.height}{project.display.profile ? ` · ${project.display.profile}` : ""}</span>
      <span className="sep" />
      <span className={`live ${live !== "off" ? "on" : ""}`} title={t("status.liveHint")}>{t(`status.live_${live}`)}</span>
    </div>
  );
}
