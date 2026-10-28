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
        <button className={`btn ghost sm ${zoom === null ? "on" : ""}`} title="Ctrl+0" onClick={() => s().setZoom(null)}><Icon name="fit" /> {t("toolbar.fit")}</button>
        <button className={`btn ghost sm ${zoom === 1 ? "on" : ""}`} title="Ctrl+1" onClick={() => s().setZoom(1)}>100%</button>
      </div>
      <div className="spacer" />
      <div className="tb-group">
        <button className="btn ghost" onClick={() => s().setDialog("theme")}><Icon name="palette" /> {t("toolbar.theme")}</button>
        <button className="btn ghost" onClick={() => s().setDialog("validate")}><Icon name="check" /> {t("toolbar.validate")}</button>
        <button className="btn ghost" onClick={() => s().setDialog("build")}><Icon name="build" /> {t("toolbar.build")}</button>
        <button className="btn primary" onClick={() => s().setDialog("device")}><Icon name="upload" /> {t("toolbar.upload")}</button>
      </div>
      <LangSwitch />
    </header>
  );
}
