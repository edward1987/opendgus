import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useStore } from "../store";
import { NumberInput, Row } from "./fields";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

const CORE = ["background", "surface", "surface2", "primary", "primary_dark", "accent", "text", "muted", "success", "warning", "danger", "on_primary"];

export function ThemeDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const theme = useStore((s) => s.project!.theme);
  const st = useStore.getState;
  const [newName, setNewName] = useState("");
  const setTheme = (patch: Partial<typeof theme>, key: string) => {
    const p = st().project!;
    st().commit({ ...p, theme: { ...p.theme, ...patch } }, `theme:${key}`);
  };
  const setColor = (k: string, c: string) => setTheme({ colors: { ...theme.colors, [k]: c.toUpperCase() } }, `c.${k}`);
  const nameOk = /^[a-z_][a-z0-9_]*$/.test(newName) && !(newName in theme.colors);

  return (
    <Modal title={t("theme.title")} onClose={onClose} width={640} footer={<button className="btn primary" onClick={onClose}>{t("common.done")}</button>}>
      <p className="muted small">{t("theme.hint")}</p>
      <div className="theme-grid">
        {Object.entries(theme.colors).map(([k, c]) => (
          <div key={k} className="theme-token">
            <input type="color" value={c} onChange={(e) => setColor(k, e.target.value)} />
            <div className="grow">
              <div className="token-name">{k}</div>
              <input className="mono hex" value={c} onChange={(e) => /^#[0-9a-fA-F]{6}$/.test(e.target.value) && setColor(k, e.target.value)} />
            </div>
            {!CORE.includes(k) && (
              <button className="icon-btn xs" title={t("common.delete")} onClick={() => {
                const colors = { ...theme.colors };
                delete colors[k];
                setTheme({ colors }, `rm.${k}`);
              }}><Icon name="trash" size={14} /></button>
            )}
          </div>
        ))}
      </div>
      <div className="row gap add-token">
        <input placeholder={t("theme.newToken")} value={newName} onChange={(e) => setNewName(e.target.value.toLowerCase())} />
        <button className="btn sm" disabled={!nameOk} onClick={() => { setColor(newName, "#888888"); setNewName(""); }}><Icon name="plus" size={14} /> {t("theme.addToken")}</button>
      </div>
      <h4 className="group-title">{t("theme.typography")}</h4>
      <Row label={t("theme.name")}><input value={theme.name} onChange={(e) => setTheme({ name: e.target.value }, "name")} /></Row>
      <Row label={t("theme.font")}><input value={theme.font} onChange={(e) => setTheme({ font: e.target.value }, "font")} /></Row>
      <Row label={t("theme.radius")}>
        <NumberInput value={theme.radius} min={0} max={200} onChange={(n) => n !== null && setTheme({ radius: n }, "radius")} />
        <span className="unit">px</span>
      </Row>
    </Modal>
  );
}
