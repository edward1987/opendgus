import { useTranslation } from "react-i18next";
import { LANGUAGES, setLanguage } from "../i18n";
import { Icon } from "./Icons";

export function LangSwitch() {
  const { i18n, t } = useTranslation();
  return (
    <label className="lang-switch" title={t("toolbar.language")}>
      <Icon name="globe" />
      <select value={i18n.language} onChange={(e) => setLanguage(e.target.value)}>
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>{l.label}</option>
        ))}
      </select>
    </label>
  );
}
