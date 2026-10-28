import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import ro from "./locales/ro.json";

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "ro", label: "Română" },
] as const;

function storedLang(): string {
  try {
    const l = localStorage.getItem("opendgus.lang");
    if (l && LANGUAGES.some((x) => x.code === l)) return l;
  } catch {
    /* storage unavailable */
  }
  return navigator.language?.toLowerCase().startsWith("ro") ? "ro" : "en";
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ro: { translation: ro } },
  lng: storedLang(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnNull: false,
});

export function setLanguage(code: string) {
  void i18n.changeLanguage(code);
  try {
    localStorage.setItem("opendgus.lang", code);
  } catch {
    /* ignore */
  }
}

export default i18n;
