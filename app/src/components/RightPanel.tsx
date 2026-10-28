import { useTranslation } from "react-i18next";
import { RightTab, useStore } from "../store";
import { Icon, IconName } from "./Icons";
import { InsertPanel } from "./InsertPanel";
import { PropertiesPanel } from "./PropertiesPanel";
import { VariablesPanel } from "./VariablesPanel";

const TABS: { id: RightTab; icon: IconName }[] = [
  { id: "props", icon: "sliders" },
  { id: "insert", icon: "plus" },
  { id: "vars", icon: "variable" },
  { id: "ai", icon: "sparkles" },
];

export function RightPanel() {
  const { t } = useTranslation();
  const tab = useStore((s) => s.rightTab);
  const setTab = useStore((s) => s.setRightTab);
  return (
    <aside className="panel right-panel">
      <nav className="tabs">
        {TABS.map((x) => (
          <button key={x.id} className={`tab ${tab === x.id ? "on" : ""}`} onClick={() => setTab(x.id)}>
            <Icon name={x.icon} size={15} /> <span>{t(`tabs.${x.id}`)}</span>
          </button>
        ))}
      </nav>
      <div className="tab-body">
        {tab === "props" && <PropertiesPanel />}
        {tab === "insert" && <InsertPanel />}
        {tab === "vars" && <VariablesPanel />}
        {tab === "ai" && <AiPanel />}
      </div>
    </aside>
  );
}

function AiPanel() {
  const { t } = useTranslation();
  return (
    <div className="ai-panel">
      <div className="ai-art"><Icon name="sparkles" size={34} /></div>
      <h3>{t("ai.title")}</h3>
      <p className="muted">{t("ai.text")}</p>
      <textarea disabled placeholder={t("ai.placeholder")} rows={4} />
      <button className="btn primary" disabled>{t("ai.send")}</button>
      <p className="muted small">{t("ai.mcpHint")}</p>
    </div>
  );
}
