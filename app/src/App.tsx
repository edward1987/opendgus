import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Editor } from "./components/Editor";
import { Icon } from "./components/Icons";
import { Welcome } from "./components/Welcome";
import { useStore } from "./store";

function Toasts() {
  const toasts = useStore((s) => s.toasts);
  return (
    <div className="toasts">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>{t.text}</div>
      ))}
    </div>
  );
}

export function App() {
  const { t } = useTranslation();
  const booting = useStore((s) => s.booting);
  const backendError = useStore((s) => s.backendError);
  const project = useStore((s) => s.project);

  useEffect(() => {
    void useStore.getState().boot();
  }, []);

  useEffect(() => {
    document.title = project ? `${project.name} — OpenDGUS` : "OpenDGUS";
  }, [project?.name]);

  if (booting)
    return (
      <div className="splash">
        <div className="brand-mark big"><Icon name="logo" size={34} /></div>
        <div className="spinner" />
        <p className="muted">{t("app.starting")}</p>
      </div>
    );
  if (backendError && !project)
    return (
      <div className="splash">
        <div className="brand-mark big danger"><Icon name="error" size={34} /></div>
        <h2>{t("app.backendError")}</h2>
        <pre className="error-pre">{backendError}</pre>
        <p className="muted">{t("app.backendHint")}</p>
      </div>
    );
  return (
    <>
      {project ? <Editor /> : <Welcome />}
      <Toasts />
    </>
  );
}
