import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { bridge } from "../lib/api";
import type { Profile } from "../lib/types";
import { useStore } from "../store";
import { Icon } from "./Icons";
import { LangSwitch } from "./LangSwitch";
import { Modal } from "./Modal";

interface Recent {
  folder: string;
  name: string;
  opened: string;
}

export function Welcome() {
  const { t, i18n } = useTranslation();
  const [recent, setRecent] = useState<Recent[]>([]);
  const [wizard, setWizard] = useState(false);
  const [busy, setBusy] = useState(false);
  const [legacyReport, setLegacyReport] = useState<{ folder: string; pages: number; controls: number; issues: string[] } | null>(null);
  const openProject = useStore((s) => s.openProject);
  const toast = useStore((s) => s.toast);

  useEffect(() => {
    void bridge.recentList().then((r) => {
      setRecent(r);
      requestAnimationFrame(() => useStore.getState().markRendered());
    });
  }, []);

  const open = async (folder: string) => {
    setBusy(true);
    try {
      await openProject(folder);
    } catch (e) {
      toast(t("welcome.openFailed", { error: (e as Error).message }), "error");
      await bridge.recentRemove(folder);
      setRecent(await bridge.recentList());
    } finally {
      setBusy(false);
    }
  };

  const browse = async () => {
    const f = await bridge.openFolder({ title: t("welcome.openTitle") });
    if (f) await open(f);
  };

  const importLegacy = async () => {
    const source = await bridge.openFolder({ title: t("welcome.legacySource") });
    if (!source) return;
    const destination = await bridge.openFolder({ title: t("welcome.legacyDestination"), create: true });
    if (!destination) return;
    setBusy(true);
    try {
      const result = await useStore.getState().api!.tool<{ folder: string; pages: number; controls: number; issues: string[] }>(
        "import_legacy_project", { source, destination });
      setLegacyReport(result);
    } catch (e) {
      toast(t("welcome.importFailed", { error: (e as Error).message }), "error");
    } finally { setBusy(false); }
  };

  return (
    <div className="welcome">
      <div className="welcome-top">
        <div className="brand">
          <div className="brand-mark"><Icon name="logo" size={22} /></div>
          <span>OpenDGUS</span>
        </div>
        <LangSwitch />
      </div>
      <div className="welcome-main">
        <section className="welcome-hero">
          <h1>{t("welcome.title")}</h1>
          <p className="lead">{t("welcome.subtitle")}</p>
          <div className="hero-actions">
            <button className="btn primary lg" onClick={() => setWizard(true)} disabled={busy}>
              <Icon name="plus" /> {t("welcome.new")}
            </button>
            <button className="btn lg" onClick={browse} disabled={busy}>
              <Icon name="folder" /> {t("welcome.open")}
            </button>
            <button className="btn lg" onClick={() => void importLegacy()} disabled={busy}>
              <Icon name="upload" /> {t("welcome.importLegacy")}
            </button>
          </div>
          <ul className="feature-list">
            <li><Icon name="check" /> {t("welcome.f1")}</li>
            <li><Icon name="check" /> {t("welcome.f2")}</li>
            <li><Icon name="check" /> {t("welcome.f3")}</li>
          </ul>
        </section>
        <section className="welcome-recent">
          <h3>{t("welcome.recent")}</h3>
          {recent.length === 0 && <p className="muted empty">{t("welcome.noRecent")}</p>}
          <div className="recent-list">
            {recent.map((r) => (
              <button key={r.folder} className="recent-item" onClick={() => open(r.folder)} disabled={busy}>
                <div className="recent-icon"><Icon name="display" size={20} /></div>
                <div className="recent-text">
                  <div className="recent-name">{r.name}</div>
                  <div className="recent-path">{r.folder}</div>
                </div>
                <div className="recent-date">{new Date(r.opened).toLocaleDateString(i18n.language)}</div>
              </button>
            ))}
          </div>
        </section>
      </div>
      {wizard && <NewProjectWizard onClose={() => setWizard(false)} />}
      {legacyReport && <Modal title={t("welcome.importReport")} onClose={() => setLegacyReport(null)} width={640}
        footer={<button className="btn primary" onClick={() => { const folder = legacyReport.folder; setLegacyReport(null); void open(folder); }}>
          {t("welcome.openImported")}</button>}>
        <p>{t("welcome.importSummary", { pages: legacyReport.pages, controls: legacyReport.controls })}</p>
        {legacyReport.issues.length > 0 && <ul className="issue-list">{legacyReport.issues.map((issue, i) => <li key={i} className="issue warning">{issue}</li>)}</ul>}
      </Modal>}
    </div>
  );
}

const slug = (s: string) => s.trim().replace(/[^A-Za-z0-9_\- ]+/g, "").replace(/\s+/g, "_") || "project";

function NewProjectWizard({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const catalog = useStore((s) => s.catalog)!;
  const api = useStore((s) => s.api);
  const createProject = useStore((s) => s.createProject);
  const [step, setStep] = useState(0);
  const [query, setQuery] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [custom, setCustom] = useState({ w: 800, h: 480 });
  const [portrait, setPortrait] = useState(false);
  const [template, setTemplate] = useState<string>("");
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void bridge.defaultProjectsDir().then((d) => setParent((p) => p || d));
  }, []);

  const profiles = useMemo(() => {
    const q = query.trim().toLowerCase();
    return catalog.profiles.filter((p) =>
      !q || `${p.id} ${p.width}x${p.height} ${p.width}×${p.height} ${p.diagonal ?? ""} ${p.series}`.toLowerCase().includes(q));
  }, [catalog.profiles, query]);

  const baseW = profile ? profile.width : custom.w;
  const baseH = profile ? profile.height : custom.h;
  const [W, H] = portrait ? [Math.min(baseW, baseH), Math.max(baseW, baseH)] : [baseW, baseH];
  const sep = parent.includes("\\") ? "\\" : "/";
  const projName = name.trim() || (template ? catalog.templates.find((x) => x.id === template)?.title ?? "" : "") || t("wizard.untitled");
  const folder = parent ? `${parent.replace(/[\\/]+$/, "")}${sep}${slug(projName)}` : "";

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      // Portrait on a catalog display: create at the swapped size, then keep the profile (flash, CPU) on it.
      const rotated = !!profile && (W !== profile.width || H !== profile.height);
      await createProject({
        folder,
        name: projName,
        profile: profile && !rotated ? profile.id : "",
        width: profile && !rotated ? 0 : W,
        height: profile && !rotated ? 0 : H,
        template,
      }, rotated && profile ? { profile: profile.id, flash_mb: profile.flash_mb, cpu: profile.cpu } : undefined);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  const steps = [t("wizard.stepDisplay"), t("wizard.stepTemplate"), t("wizard.stepName")];
  const validDisplay = W >= 16 && H >= 16 && W <= 4096 && H <= 4096;

  return (
    <Modal title={t("wizard.title")} onClose={onClose} width={820} className="wizard"
      footer={
        <>
          <div className="steps">
            {steps.map((s, i) => (
              <span key={s} className={`step ${i === step ? "active" : i < step ? "done" : ""}`}>
                <b>{i + 1}</b> {s}
              </span>
            ))}
          </div>
          <div className="spacer" />
          {step > 0 && <button className="btn" onClick={() => setStep(step - 1)} disabled={busy}><Icon name="arrowLeft" /> {t("common.back")}</button>}
          {step < 2 && (
            <button className="btn primary" onClick={() => setStep(step + 1)} disabled={step === 0 && !validDisplay}>
              {t("common.next")} <Icon name="arrowRight" />
            </button>
          )}
          {step === 2 && (
            <button className="btn primary" onClick={create} disabled={busy || !folder}>
              {busy ? t("wizard.creating") : t("wizard.create")}
            </button>
          )}
        </>
      }>
      {step === 0 && (
        <div className="wizard-display">
          <div className="wizard-col">
            <div className="search">
              <Icon name="search" />
              <input autoFocus placeholder={t("wizard.searchDisplays")} value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <div className="profile-list">
              <button className={`profile-item ${profile === null ? "selected" : ""}`} onClick={() => setProfile(null)}>
                <div className="profile-thumb" style={{ aspectRatio: `${custom.w}/${custom.h}` }} />
                <div className="profile-text">
                  <div className="profile-name">{t("wizard.custom")}</div>
                  <div className="profile-meta">{t("wizard.customHint")}</div>
                </div>
              </button>
              {profiles.map((p) => (
                <button key={p.id} className={`profile-item ${profile?.id === p.id ? "selected" : ""}`} onClick={() => setProfile(p)}>
                  <div className="profile-thumb" style={{ aspectRatio: `${p.width}/${p.height}` }} />
                  <div className="profile-text">
                    <div className="profile-name">{p.width}×{p.height} {p.diagonal ? <span className="chip">{p.diagonal}"</span> : null}</div>
                    <div className="profile-meta">{p.id} · {p.series} · {p.touch === "C" ? t("wizard.touchC") : p.touch === "R" ? t("wizard.touchR") : t("wizard.touchN")}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div className="wizard-side">
            <div className="screen-preview-box">
              <div className="screen-preview" style={{ aspectRatio: `${W}/${H}`, [W >= H ? "width" : "height"]: "100%" }}>
                <span>{W} × {H}</span>
              </div>
            </div>
            {profile === null && (
              <div className="row gap">
                <label className="field">
                  <span>{t("wizard.width")}</span>
                  <input type="number" value={custom.w} min={16} max={4096} onChange={(e) => setCustom({ ...custom, w: Number(e.target.value) })} />
                </label>
                <label className="field">
                  <span>{t("wizard.height")}</span>
                  <input type="number" value={custom.h} min={16} max={4096} onChange={(e) => setCustom({ ...custom, h: Number(e.target.value) })} />
                </label>
              </div>
            )}
            <div className="field">
              <span>{t("wizard.orientation")}</span>
              <div className="segmented">
                <button className={!portrait ? "on" : ""} onClick={() => setPortrait(false)}>{t("wizard.landscape")}</button>
                <button className={portrait ? "on" : ""} onClick={() => setPortrait(true)}>{t("wizard.portrait")}</button>
              </div>
            </div>
            {profile && portrait && W !== profile.width && (
              <p className="alert warn small">{t("wizard.portraitProfile", { id: profile.id, w: W, h: H })}</p>
            )}
            {profile && (
              <dl className="specs">
                <dt>{t("wizard.flash")}</dt><dd>{profile.flash_mb} MB</dd>
                <dt>CPU</dt><dd>{profile.cpu}</dd>
              </dl>
            )}
          </div>
        </div>
      )}
      {step === 1 && (
        <div className="template-grid">
          <button className={`template-card ${template === "" ? "selected" : ""}`} onClick={() => setTemplate("")}>
            <div className="template-art blank"><Icon name="file" size={28} /></div>
            <div className="template-title">{t("wizard.blank")}</div>
            <div className="template-desc">{t("wizard.blankDesc")}</div>
          </button>
          {catalog.templates.map((tp) => (
            <button key={tp.id} className={`template-card ${template === tp.id ? "selected" : ""}`} onClick={() => setTemplate(tp.id)}>
              <TemplateThumb id={tp.id} w={W} h={H} url={api ? api.templateUrl(tp.id, W, H, Math.min(1, 480 / W, 260 / H)) : null} />
              <div className="template-title">{tp.title}</div>
              <div className="template-desc">{tp.description}</div>
            </button>
          ))}
        </div>
      )}
      {step === 2 && (
        <div className="form-col">
          <label className="field">
            <span>{t("wizard.name")}</span>
            <input autoFocus value={name} placeholder={projName} onChange={(e) => setName(e.target.value)} />
          </label>
          <div className="field">
            <span>{t("wizard.location")}</span>
            <div className="row gap">
              <input className="grow" value={parent} onChange={(e) => setParent(e.target.value)} />
              <button className="btn" onClick={async () => {
                const f = await bridge.openFolder({ title: t("wizard.location"), create: true });
                if (f) setParent(f);
              }}><Icon name="folder" /> {t("common.browse")}</button>
            </div>
          </div>
          <p className="muted small">{t("wizard.willCreate")} <code>{folder}</code></p>
          <div className="summary">
            <span className="chip">{W}×{H}</span>
            {profile && <span className="chip">{profile.id}</span>}
            {profile && portrait && W !== profile.width && <span className="chip warn-chip">{t("wizard.portraitChip")}</span>}
            <span className="chip">{template ? catalog.templates.find((x) => x.id === template)?.title : t("wizard.blank")}</span>
          </div>
          {error && <div className="alert error">{error}</div>}
        </div>
      )}
    </Modal>
  );
}

/** Template preview rendered by the backend at the chosen resolution (falls back to icons while loading/failing). */
function TemplateThumb({ url, w, h }: { id: string; url: string | null; w: number; h: number }) {
  const [state, setState] = useState<"loading" | "ok" | "error">(url ? "loading" : "error");
  useEffect(() => setState(url ? "loading" : "error"), [url]);
  return (
    <div className={`template-art thumb ${state}`}>
      {state !== "ok" && (
        <span className="thumb-fallback">
          {state === "loading" ? <span className="mini-spin" /> : <><Icon name="toggle" size={24} /><Icon name="slider" size={24} /><Icon name="number" size={24} /></>}
        </span>
      )}
      {url && state !== "error" && (
        <img src={url} alt="" loading="lazy" style={{ aspectRatio: `${w}/${h}` }}
          onLoad={() => setState("ok")} onError={() => setState("error")} />
      )}
    </div>
  );
}
