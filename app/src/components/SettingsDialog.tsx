// Project settings: backlight / auto-dim (done by the display) and the screensaver (switched by the controller).
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { bridge } from "../lib/api";
import type { Screensaver, Standby } from "../lib/types";
import { useStore } from "../store";
import { NumberInput, Row, Switch } from "./fields";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

const STANDBY_DEFAULT: Standby = { enabled: false, level: 10, timeout_s: 60 };
const SAVER_DEFAULT: Screensaver = { enabled: false, timeout_s: 120, page: null, frame_pages: [], frame_ms: 100, source: null, wake_page: null, brightness: null };
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** 90 -> "1 min 30 s" */
export function formatSeconds(s: number): string {
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60), r = s % 60;
  if (m < 60) return r ? `${m} min ${r} s` : `${m} min`;
  const h = Math.floor(m / 60), rm = m % 60;
  return rm ? `${h} h ${rm} min` : `${h} h`;
}

function Seconds({ value, min, max, presets, onChange }: { value: number; min: number; max: number; presets: number[]; onChange: (n: number) => void }) {
  return (
    <span className="row gap-sm wrap sec-field">
      <NumberInput value={value} min={min} max={max} onChange={(n) => n !== null && onChange(n)} />
      <span className="unit">s</span>
      {presets.filter((p) => p >= min && p <= max).map((p) => (
        <button key={p} type="button" className={`chip tiny ${p === value ? "on" : ""}`} onClick={() => onChange(p)}>{formatSeconds(p)}</button>
      ))}
    </span>
  );
}

function Percent({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  return (
    <span className="row gap-sm grow pct-field">
      <input type="range" min={0} max={100} value={value} onChange={(e) => onChange(Number(e.target.value))} className="grow" />
      <NumberInput value={value} min={0} max={100} onChange={(n) => n !== null && onChange(n)} />
      <span className="unit">%</span>
    </span>
  );
}

export function SettingsDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const project = useStore((s) => s.project)!;
  const folder = useStore((s) => s.folder);
  const api = useStore((s) => s.api);
  const st = useStore.getState;
  const d = { ...project.display, backlight: project.display.backlight ?? 100 };
  const sb = { ...STANDBY_DEFAULT, ...d.standby };
  const ss = { ...SAVER_DEFAULT, ...project.screensaver };
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [thumb, setThumb] = useState<string | null>(null);

  const setDisplay = (patch: Record<string, unknown>, key: string) => {
    const p = st().project!;
    st().commit({ ...p, display: { ...p.display, ...patch } }, `settings:${key}`);
  };
  const setStandby = (patch: Partial<Standby>, key: string) => setDisplay({ standby: { ...sb, ...patch } }, `sb.${key}`);
  const setSaver = (patch: Partial<Screensaver>, key: string) => {
    const p = st().project!;
    st().commit({ ...p, screensaver: { ...ss, ...patch } }, `settings:ss.${key}`);
  };
  const tool = async (args: Record<string, unknown>) => {
    setBusy(true);
    setErr(null);
    try {
      await st().applyTool("set_screensaver", args);
    } catch (e) {
      setErr(errText(e));
    } finally {
      setBusy(false);
    }
  };

  const chooseImage = async () => {
    if (!folder) return;
    const file = await bridge.openImage(t("settings.chooseImage"));
    if (!file) return;
    const src = await bridge.importAsset(folder, file);
    await tool({ image: src });
  };

  // preview of the screensaver page as the display shows it
  useEffect(() => {
    let url: string | null = null;
    let live = true;
    if (api && ss.page !== null && project.pages.some((p) => p.id === ss.page)) {
      void api.preview(ss.page, 0.4).then((r) => {
        url = r.url;
        if (live) setThumb(r.url);
        else URL.revokeObjectURL(r.url);
      }).catch(() => setThumb(null));
    } else setThumb(null);
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [api, ss.page, ss.source]);

  const userPages = project.pages.filter((p) => p.id !== ss.page && !ss.frame_pages.includes(p.id));
  const frames = ss.page === null ? 0 : ss.frame_pages.length + 1;

  return (
    <Modal title={t("settings.title")} onClose={onClose} width={680} className="settings-modal" footer={<button className="btn primary" onClick={onClose}>{t("common.done")}</button>}>
      <h4 className="group-title"><Icon name="display" size={14} /> {t("settings.power")}</h4>
      <Row label={t("props.backlight")}><Percent value={d.backlight} onChange={(n) => setDisplay({ backlight: n }, "backlight")} /></Row>
      <Row label={t("settings.autoDim")}><Switch checked={sb.enabled} onChange={(v) => setStandby({ enabled: v }, "enabled")} /></Row>
      {sb.enabled && (
        <>
          <Row label={t("settings.dimTo")}><Percent value={sb.level} onChange={(n) => setStandby({ level: n }, "level")} /></Row>
          <Row label={t("settings.dimAfter")}>
            <Seconds value={sb.timeout_s} min={1} max={655} presets={[30, 60, 120, 300, 600]} onChange={(n) => setStandby({ timeout_s: n }, "timeout")} />
          </Row>
        </>
      )}
      <p className="muted small">{t("settings.dimHint")}</p>

      <h4 className="group-title"><Icon name="image" size={14} /> {t("settings.screensaver")}</h4>
      <div className="saver-box">
        <div className="saver-thumb" style={{ aspectRatio: `${d.width} / ${d.height}` }}>
          {thumb ? <img src={thumb} alt="" /> : <span className="muted small">{t("settings.noImage")}</span>}
          {frames > 1 && <span className="chip tiny saver-frames">{t("settings.frames", { count: frames })}</span>}
        </div>
        <div className="grow">
          <div className="row gap-sm wrap">
            <button className="btn sm" disabled={busy || !folder} onClick={() => void chooseImage()}>
              <Icon name="image" size={14} /> {ss.page === null ? t("settings.chooseImage") : t("settings.changeImage")}
            </button>
            {ss.page !== null && (
              <button className="btn sm ghost" disabled={busy} onClick={() => void tool({ remove: true })}><Icon name="trash" size={14} /> {t("settings.removeSaver")}</button>
            )}
            {busy && <div className="spinner sm" />}
          </div>
          <p className="muted small">{t("settings.imageHint")}</p>
          {ss.source && <p className="muted small mono">{ss.source}</p>}
        </div>
      </div>
      {err && <pre className="error-pre">{err}</pre>}
      {ss.page !== null && (
        <>
          <Row label={t("settings.saverOn")}><Switch checked={ss.enabled} onChange={(v) => setSaver({ enabled: v }, "enabled")} /></Row>
          <Row label={t("settings.saverAfter")}>
            <Seconds value={ss.timeout_s} min={5} max={86400} presets={[60, 120, 300, 900, 1800]} onChange={(n) => setSaver({ timeout_s: n }, "timeout")} />
          </Row>
          {frames > 1 && (
            <Row label={t("settings.frameTime")}>
              <span className="row gap-sm sec-field"><NumberInput value={ss.frame_ms} min={8} max={2040} onChange={(n) => n !== null && setSaver({ frame_ms: n }, "frame")} />
              <span className="unit">ms</span>
              <button className="btn sm ghost" disabled={busy} onClick={() => void tool({ frame_ms: ss.frame_ms })}>{t("settings.applyFrame")}</button></span>
            </Row>
          )}
          <Row label={t("settings.wake")}>
            <select value={ss.wake_page ?? -1} disabled={busy} onChange={(e) => void tool({ wake_page: Number(e.target.value) })}>
              <option value={-1}>{t("settings.wakePrevious")}</option>
              {userPages.map((p) => <option key={p.id} value={p.id}>{p.id} · {p.name || t("pages.unnamed")}</option>)}
            </select>
          </Row>
          <Row label={t("settings.saverBrightness")}>
            <span className="row gap-sm grow">
              <Switch checked={ss.brightness !== null} onChange={(v) => setSaver({ brightness: v ? Math.min(d.backlight, 30) : null }, "bright.on")} />
              {ss.brightness !== null ? <Percent value={ss.brightness} onChange={(n) => setSaver({ brightness: n }, "bright")} /> : <span className="muted small">{t("settings.unchanged")}</span>}
            </span>
          </Row>
        </>
      )}
      <div className="note-box">
        <Icon name="chip" size={16} />
        <div className="grow">
          <p className="small">{t("settings.saverNeedsController")}</p>
          <button className="btn sm" onClick={() => st().setDialog("controller")}><Icon name="chip" size={14} /> {t("settings.openController")}</button>
        </div>
      </div>
    </Modal>
  );
}
