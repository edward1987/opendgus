import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { bridge } from "../lib/api";
import { findItem } from "../lib/project";
import { useStore } from "../store";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** "error: c3: outside the screen" -> {level, where, message} */
export function parseIssue(s: string) {
  const m = /^(error|warning):\s*([^:]*):\s*(.*)$/s.exec(s);
  return m ? { level: m[1], where: m[2].trim(), message: m[3] } : { level: "warning", where: "", message: s };
}

function IssueList({ issues, onPick }: { issues: string[]; onPick: (id: string) => void }) {
  const { t } = useTranslation();
  if (!issues.length) return <div className="alert ok"><Icon name="check" /> {t("validate.noIssues")}</div>;
  return (
    <ul className="issue-list">
      {issues.map((s, i) => {
        const is = parseIssue(s);
        return (
          <li key={i} className={`issue ${is.level}`}>
            <Icon name={is.level === "error" ? "error" : "warning"} />
            <div className="grow">
              {is.where && <button className="link mono" onClick={() => onPick(is.where)}>{is.where}</button>} {is.message}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function usePick(onClose: () => void) {
  return (id: string) => {
    const s = useStore.getState();
    const f = s.project && findItem(s.project, id);
    if (!f) return;
    s.setPage(f.page.id);
    s.select([id]);
    s.setRightTab("props");
    onClose();
  };
}

export function ValidateDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const [res, setRes] = useState<{ ok: boolean; issues: string[]; pages: number[]; icons: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const pick = usePick(onClose);
  useEffect(() => {
    const s = useStore.getState();
    void s.flushSave().then(() => s.api!.tool("validate")).then(setRes).catch((e) => setErr(errText(e)));
  }, []);
  return (
    <Modal title={t("validate.title")} onClose={onClose} width={620}
      footer={<button className="btn" onClick={onClose}>{t("common.close")}</button>}>
      {!res && !err && <div className="center"><div className="spinner" /></div>}
      {err && <div className="alert error">{err}</div>}
      {res && (
        <>
          <div className="summary">
            <span className={`chip ${res.ok ? "ok" : "bad"}`}>{res.ok ? t("validate.ok") : t("validate.failed")}</span>
            <span className="chip">{t("validate.pages", { count: res.pages.length })}</span>
            <span className="chip">{t("validate.icons", { count: res.icons })}</span>
          </div>
          <IssueList issues={res.issues} onPick={pick} />
        </>
      )}
    </Modal>
  );
}

interface BuildResult {
  ok: boolean;
  out: string;
  files: Record<string, { slot: number | null; size: number; sha256?: string }>;
  issues: string[];
  variables: Record<string, string>;
}

export function BuildDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const [res, setRes] = useState<BuildResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const pick = usePick(onClose);
  useEffect(() => {
    const s = useStore.getState();
    void s.flushSave()
      .then(() => s.api!.tool<BuildResult>("build"))
      .then((r) => { setRes(r); s.setVpMap(r.variables); })
      .catch((e) => setErr(errText(e)));
  }, []);
  const total = res ? Object.values(res.files).reduce((a, f) => a + (f.size || 0), 0) : 0;
  return (
    <Modal title={t("build.title")} onClose={onClose} width={720}
      footer={
        <>
          {res && <button className="btn" onClick={() => void bridge.openPath(res.out)}><Icon name="folder" /> {t("build.openFolder")}</button>}
          <div className="spacer" />
          <button className="btn primary" onClick={onClose}>{t("common.close")}</button>
        </>
      }>
      {!res && !err && <div className="center"><div className="spinner" /><p className="muted">{t("build.building")}</p></div>}
      {err && <div className="alert error">{err}</div>}
      {res && (
        <>
          <div className="summary">
            <span className={`chip ${res.ok ? "ok" : "bad"}`}>{res.ok ? t("build.ok") : t("build.failed")}</span>
            <span className="chip mono" title={res.out}>{res.out}</span>
          </div>
          <div className="two-col">
            <div>
              <h4 className="group-title">{t("build.files")}</h4>
              <table className="table">
                <thead><tr><th>{t("build.file")}</th><th>{t("build.slot")}</th><th className="num">{t("build.size")}</th></tr></thead>
                <tbody>
                  {Object.entries(res.files).map(([n, f]) => (
                    <tr key={n}><td className="mono">{n}</td><td>{f.slot ?? "—"}</td><td className="num">{(f.size / 1024).toFixed(1)} KB</td></tr>
                  ))}
                  <tr className="total"><td>{t("build.total")}</td><td /><td className="num">{(total / 1024).toFixed(1)} KB</td></tr>
                </tbody>
              </table>
            </div>
            <div>
              <h4 className="group-title">{t("build.variables")}</h4>
              <table className="table">
                <thead><tr><th>{t("vars.name")}</th><th>VP</th></tr></thead>
                <tbody>
                  {Object.entries(res.variables).map(([n, vp]) => <tr key={n}><td className="mono">{n}</td><td className="mono">{vp}</td></tr>)}
                </tbody>
              </table>
              <p className="muted small">{t("build.varsHint")}</p>
            </div>
          </div>
          {res.issues.length > 0 && (
            <>
              <h4 className="group-title">{t("validate.issues")}</h4>
              <IssueList issues={res.issues} onPick={pick} />
            </>
          )}
        </>
      )}
    </Modal>
  );
}

export function DeviceDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const api = useStore((s) => s.api)!;
  const baudDefault = useStore((s) => s.project?.display.baud ?? 115200);
  const [ports, setPorts] = useState<{ port: string; description: string }[] | null>(null);
  const [port, setPort] = useState("");
  const [baud, setBaud] = useState(baudDefault);
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState<null | "test" | "upload">(null);
  const [err, setErr] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [result, setResult] = useState<{ uploaded: string[]; note?: string } | null>(null);

  const refresh = () => {
    setPorts(null);
    api.tool<{ port: string; description: string }[]>("list_serial_ports")
      .then((p) => { setPorts(p); setPort((cur) => cur || p[0]?.port || ""); })
      .catch((e) => { setPorts([]); setErr(errText(e)); });
  };
  useEffect(refresh, []);

  const test = async () => {
    setBusy("test"); setErr(null); setInfo(null);
    try { setInfo(await api.tool("device_info", { port, baud })); } catch (e) { setErr(errText(e)); }
    setBusy(null);
  };
  const upload = async () => {
    setBusy("upload"); setErr(null); setResult(null);
    try {
      await useStore.getState().flushSave();
      setResult(await api.tool("device_upload", { port, baud, confirm: true }));
      setConfirm(false);
    } catch (e) { setErr(errText(e)); }
    setBusy(null);
  };

  return (
    <Modal title={t("device.title")} onClose={() => !busy && onClose()} width={600}
      footer={<button className="btn" onClick={onClose} disabled={!!busy}>{t("common.close")}</button>}>
      <div className="form-col">
        <div className="field">
          <span>{t("device.port")}</span>
          <div className="row gap">
            <select className="grow" value={port} onChange={(e) => setPort(e.target.value)} disabled={!ports?.length}>
              {ports === null && <option>{t("common.loading")}</option>}
              {ports?.length === 0 && <option value="">{t("device.noPorts")}</option>}
              {ports?.map((p) => <option key={p.port} value={p.port}>{p.port} — {p.description}</option>)}
            </select>
            <button className="icon-btn" title={t("device.refresh")} onClick={refresh}><Icon name="refresh" /></button>
          </div>
        </div>
        <label className="field">
          <span>{t("device.baud")}</span>
          <select value={baud} onChange={(e) => setBaud(Number(e.target.value))}>
            {[9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600].map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </label>
        <div className="row gap">
          <button className="btn" disabled={!port || !!busy} onClick={test}><Icon name="plug" /> {busy === "test" ? t("device.testing") : t("device.test")}</button>
        </div>
        {info && (
          <div className="alert ok">
            <Icon name="check" /> {t("device.connected")}
            <dl className="specs">{Object.entries(info).map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{String(v)}</dd></Fragment>)}</dl>
          </div>
        )}
        <div className="danger-zone">
          <h4><Icon name="warning" /> {t("device.uploadTitle")}</h4>
          <p>{t("device.uploadWarning")}</p>
          <label className="check">
            <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} /> {t("device.confirm")}
          </label>
          <button className="btn danger" disabled={!port || !confirm || !!busy} onClick={upload}>
            <Icon name="upload" /> {busy === "upload" ? t("device.uploading") : t("device.upload")}
          </button>
        </div>
        {err && <div className="alert error">{err}</div>}
        {result && (
          <div className="alert ok">
            <div><Icon name="check" /> {t("device.uploaded")}</div>
            <ul className="mono small">{result.uploaded.map((l) => <li key={l}>{l}</li>)}</ul>
            {result.note && <div className="muted small">{result.note}</div>}
          </div>
        )}
      </div>
    </Modal>
  );
}
