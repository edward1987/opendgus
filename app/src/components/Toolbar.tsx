import { useState } from "react";
import { useTranslation } from "react-i18next";
import { canRedo, canUndo } from "../lib/history";
import { useStore } from "../store";
import { Icon } from "./Icons";
import { LangSwitch } from "./LangSwitch";

export function Toolbar() {
  const { t } = useTranslation();
  const project = useStore((s) => s.project)!;
  const history = useStore((s) => s.history);
  const zoom = useStore((s) => s.zoom);
  const mode = useStore((s) => s.mode);
  const s = useStore.getState;
  const [editing, setEditing] = useState(false);

  return (
    <header className="toolbar">
      <button className="brand-btn" title={t("toolbar.home")} onClick={() => void s().closeProject()}>
        <div className="brand-mark"><Icon name="logo" size={18} /></div>
      </button>
      {editing ? (
        <input className="project-name-input" autoFocus defaultValue={project.name}
          onBlur={(e) => { setEditing(false); const v = e.target.value.trim(); if (v && v !== project.name) s().commit({ ...s().project!, name: v }); }}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === "Escape") (e.target as HTMLInputElement).blur(); }} />
      ) : (
        <button className="project-name" title={t("toolbar.rename")} onClick={() => setEditing(true)}>{project.name}</button>
      )}
      <div className="tb-group">
        <button className="icon-btn" title={`${t("toolbar.undo")} (Ctrl+Z)`} disabled={!canUndo(history)} onClick={() => s().undo()}><Icon name="undo" /></button>
        <button className="icon-btn" title={`${t("toolbar.redo")} (Ctrl+Y)`} disabled={!canRedo(history)} onClick={() => s().redo()}><Icon name="redo" /></button>
      </div>
      <div className="tb-group">
        <button className={`btn ghost sm ${zoom === null && mode === "edit" ? "on" : ""}`} disabled={mode === "run"} title="Ctrl+0" onClick={() => s().setZoom(null)}><Icon name="fit" /> {t("toolbar.fit")}</button>
        <button className={`btn ghost sm ${zoom === 1 && mode === "edit" ? "on" : ""}`} disabled={mode === "run"} title="Ctrl+1" onClick={() => s().setZoom(1)}>100%</button>
      </div>
      <div className="tb-group">
        <button className={`btn run-btn ${mode === "run" ? "on" : ""}`} title={mode === "run" ? `${t("toolbar.exitRun")} (Esc)` : t("toolbar.runHint")}
          onClick={() => s().setMode(mode === "run" ? "edit" : "run")}>
          <Icon name={mode === "run" ? "stop" : "play"} /> {mode === "run" ? t("toolbar.exitRun") : t("toolbar.run")}
        </button>
      </div>
      <div className="spacer" />
      <div className="tb-group">
        <button className="btn ghost" title={t("toolbar.settingsHint")} onClick={() => s().setDialog("settings")}><Icon name="gear" /> {t("toolbar.settings")}</button>
        <button className="btn ghost" title={t("toolbar.controllerHint")} onClick={() => s().setDialog("controller")}><Icon name="chip" /> {t("toolbar.controller")}</button>
        <button className="btn ghost" onClick={() => s().setDialog("theme")}><Icon name="palette" /> {t("toolbar.theme")}</button>
        <button className="btn ghost" onClick={() => s().setDialog("validate")}><Icon name="check" /> {t("toolbar.validate")}</button>
        <button className="btn ghost" onClick={() => s().setDialog("build")}><Icon name="build" /> {t("toolbar.build")}</button>
        <button className="btn primary" onClick={() => s().setDialog("device")}><Icon name="upload" /> {t("toolbar.upload")}</button>
      </div>
      <LangSwitch />
    </header>
  );
}
