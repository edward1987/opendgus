// Run mode: the built project in the headless display emulator. Clicks become touches (long presses use
// hold_ms), the side table shows the variables and lets you write them as the MCU would.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Change, fitSize, holdMs, parseCaption, parseTapScript, parseVarValue, toDevice } from "../lib/emulator";
import type { Project } from "../lib/types";
import { useStore } from "../store";
import { Icon } from "./Icons";

interface Shot {
  image: string;
  caption?: string;
}

interface LogEntry {
  key: number;
  time: string;
  text: string;
  page: number | null;
  changes: Change[];
  error?: boolean;
}

const fmt = (v: unknown) => (v === undefined ? "?" : typeof v === "object" ? JSON.stringify(v) : String(v));
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function RunView() {
  const { t } = useTranslation();
  const api = useStore((s) => s.api)!;
  const project = useStore((s) => s.project)!;
  const W = project.display.width;
  const H = project.display.height;

  const [status, setStatus] = useState<"starting" | "ready" | "error">("starting");
  const [error, setError] = useState<string | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [page, setPage] = useState<number | null>(null);
  const [vars, setVars] = useState<Record<string, unknown>>({});
  const [log, setLog] = useState<LogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [press, setPress] = useState<{ x: number; y: number; cx: number; cy: number; t0: number } | null>(null);
  const [startedWith, setStartedWith] = useState<Project | null>(null);

  const stageRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  // idle simulation in real time: auto-dim (the display) and the screensaver (what the controller does)
  const lastTouch = useRef(performance.now());
  const saverFrom = useRef<number | null>(null);
  const [idleS, setIdleS] = useState(0);
  const [simController, setSimController] = useState(true);
  const seq = useRef(0);
  const alive = useRef(true);

  useLayoutEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setBox({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setBox({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  useEffect(() => () => void (alive.current = false), []);

  /** Run emulator calls one at a time (taps must not overtake each other). */
  const enqueue = useCallback(<T,>(fn: () => Promise<T>): Promise<T> => {
    const p = queue.current.then(fn, fn);
    queue.current = p.catch(() => undefined);
    return p;
  }, []);

  const addLog = (text: string, caption?: string, setName?: string, isError = false) => {
    const info = parseCaption(caption, setName);
    if (info.page !== null) setPage(info.page);
    setLog((l) => [{ key: ++seq.current, time: new Date().toLocaleTimeString(), text, page: info.page, changes: info.changes, error: isError }, ...l].slice(0, 200));
  };

  const refreshState = async () => {
    const st = await api.tool<{ page: number; variables: Record<string, unknown> }>("emulator_state");
    if (!alive.current) return;
    setVars(st.variables ?? {});
    if (typeof st.page === "number") setPage(st.page);
  };

  const show = (shot: Shot) => setImage(`data:image/png;base64,${shot.image}`);

  const sb = project.display.standby;
  const ss = project.screensaver;
  const saverReady = !!ss?.enabled && ss.page !== null && simController;
  const onSaver = saverReady && page === ss!.page;
  const dimmed = !!sb?.enabled && idleS >= sb.timeout_s;
  const backlight = onSaver && ss!.brightness !== null ? Math.min(ss!.brightness, dimmed ? sb!.level : 100)
    : dimmed ? sb!.level : project.display.backlight ?? 100;

  const goPage = (n: number, text: string) => enqueue(async () => {
    try {
      const shot = await api.tool<Shot>("emulator_set_page", { page: n, scale: 1 });
      if (!alive.current) return;
      show(shot);
      addLog(text, shot.caption);
    } catch (e) {
      addLog(errText(e), undefined, undefined, true);
    }
  });

  useEffect(() => {
    if (status !== "ready") return;
    const id = setInterval(() => setIdleS(Math.floor((performance.now() - lastTouch.current) / 1000)), 250);
    return () => clearInterval(id);
  }, [status]);

  // the controller switches to the screensaver page after its timeout
  useEffect(() => {
    if (!saverReady || status !== "ready" || page === null || page === ss!.page || idleS < ss!.timeout_s) return;
    saverFrom.current = page;
    void goPage(ss!.page!, t("run.saverOn"));
  }, [idleS >= (ss?.timeout_s ?? Infinity), saverReady, status]);

  // keep an animated screensaver moving
  useEffect(() => {
    if (!onSaver || !ss!.frame_pages.length) return;
    const ms = Math.max(120, ss!.frame_ms);
    const id = setInterval(() => void enqueue(async () => {
      try {
        const shot = await api.tool<Shot>("emulator_wait", { ms, scale: 1 });
        if (alive.current) show(shot);
      } catch { /* next frame retries */ }
    }), ms);
    return () => clearInterval(id);
  }, [onSaver, ss?.frame_ms]);

  /** A touch on a dimmed panel or on the screensaver only wakes it (it is not passed to the controls). */
  const wake = (): boolean => {
    const wasDim = dimmed;
    lastTouch.current = performance.now();
    setIdleS(0);
    if (onSaver) {
      const back = ss!.wake_page ?? saverFrom.current ?? 0;
      saverFrom.current = null;
      void goPage(back, t("run.saverOff"));
      return true;
    }
    if (wasDim) {
      addLog(t("run.woke"));
      return true;
    }
    return false;
  };

  const start = useCallback(() => enqueue(async () => {
    setStatus("starting");
    setError(null);
    try {
      await useStore.getState().flushSave();
      const shot = await api.tool<Shot>("emulator_start", { page: 0, scale: 1 });
      if (!alive.current) return false;
      show(shot);
      setStartedWith(useStore.getState().project);
      lastTouch.current = performance.now();
      saverFrom.current = null;
      setIdleS(0);
      setLog([]);
      addLog(t("run.started"), shot.caption);
      await refreshState();
      setStatus("ready");
      return true;
    } catch (e) {
      if (!alive.current) return false;
      setError(errText(e));
      setStatus("error");
      return false;
    }
  }), [api]);

  const tap = (x: number, y: number, hold: number) => enqueue(async () => {
    setBusy(true);
    try {
      const shot = await api.tool<Shot>("emulator_tap", { x, y, hold_ms: hold, scale: 1 });
      if (!alive.current) return;
      show(shot);
      addLog(hold ? t("run.hold", { x, y, ms: hold }) : t("run.tap", { x, y }), shot.caption);
      await refreshState();
    } catch (e) {
      addLog(errText(e), undefined, undefined, true);
    } finally {
      if (alive.current) setBusy(false);
    }
  });

  const setVariable = (name: string, value: number) => enqueue(async () => {
    try {
      const shot = await api.tool<Shot>("emulator_set_variable", { name, value, scale: 1 });
      if (!alive.current) return;
      show(shot);
      addLog(t("run.set", { name, value }), shot.caption, name);
      await refreshState();
    } catch (e) {
      addLog(errText(e), undefined, undefined, true);
    }
  });

  // start on mount; smoke runs then play their tap script and take the screenshot
  useEffect(() => {
    void (async () => {
      const ok = await start();
      const script = useStore.getState().smokeRun;
      if (script === null) return;
      if (ok) for (const s of parseTapScript(script)) await tap(s.x, s.y, s.hold);
      await wait(300);
      requestAnimationFrame(() => requestAnimationFrame(() => useStore.getState().markRendered(true)));
    })();
  }, []);

  const fit = fitSize(Math.max(0, box.w - 48), Math.max(0, box.h - 96), W, H);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0 || status !== "ready" || !imgRef.current) return;
    if (wake()) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const r = imgRef.current.getBoundingClientRect();
    const d = toDevice(e.clientX, e.clientY, r, W, H);
    setPress({ ...d, cx: e.clientX - r.left, cy: e.clientY - r.top, t0: performance.now() });
  };
  const onPointerUp = () => {
    if (!press) return;
    const hold = holdMs(performance.now() - press.t0);
    setPress(null);
    void tap(press.x, press.y, hold);
  };

  const pageName = page !== null ? project.pages.find((p) => p.id === page)?.name : null;
  const designChanged = status === "ready" && startedWith !== null && startedWith !== project;
  const numericVars = project.variables.filter((v) => v.name in vars);

  return (
    <main className="run-view">
      <div className="run-stage" ref={stageRef}>
        <div className="run-bar">
          <span className="run-badge"><span className="live-dot" /> {t("toolbar.run")}</span>
          {page !== null && <span className="chip">{t("run.page", { page })}{pageName ? ` · ${pageName}` : ""}</span>}
          {designChanged && (
            <button className="chip warn-chip" onClick={() => void start()}><Icon name="refresh" size={12} /> {t("run.changed")}</button>
          )}
          {dimmed && <span className="chip">{t("run.dimmed", { level: backlight })}</span>}
          {onSaver && <span className="chip">{t("run.saver")}</span>}
          <span className="spacer" />
          {(sb?.enabled || (ss?.enabled && ss.page !== null)) && (
            <>
              {ss?.enabled && ss.page !== null && (
                <label className="row gap-sm small muted" title={t("run.simControllerHint")}>
                  <input type="checkbox" checked={simController} onChange={(e) => setSimController(e.target.checked)} /> {t("run.simController")}
                </label>
              )}
              <button className="btn sm" disabled={status !== "ready"} title={t("run.idleHint")}
                onClick={() => { lastTouch.current = performance.now() - 1000 * Math.max(sb?.enabled ? sb.timeout_s : 0, saverReady ? ss!.timeout_s : 0); setIdleS(Math.floor((performance.now() - lastTouch.current) / 1000)); }}>
                <Icon name="eyeOff" size={14} /> {t("run.idle")}
              </button>
            </>
          )}
          <span className="muted small">{t("run.hint")}</span>
          <button className="btn sm" onClick={() => void start()} disabled={status === "starting"}><Icon name="refresh" size={14} /> {t("run.restart")}</button>
          <button className="btn sm" onClick={() => useStore.getState().setMode("edit")}><Icon name="close" size={14} /> {t("run.exit")}</button>
        </div>
        <div className="run-center">
          {image && (
            <div className={`run-screen ${busy ? "busy" : ""} ${status !== "ready" ? "dim" : ""}`} style={{ width: fit.w, height: fit.h }}
              onPointerDown={onPointerDown} onPointerUp={onPointerUp} onPointerCancel={() => setPress(null)}>
              <img ref={imgRef} src={image} alt="" draggable={false} />
              <span className="backlight" style={{ opacity: (100 - backlight) / 100 * 0.92 }} />
              {press && <span className="press-ring" style={{ left: press.cx, top: press.cy }} />}
            </div>
          )}
          {status === "starting" && <div className="run-overlay"><div className="spinner" /><p className="muted">{t("run.starting")}</p></div>}
          {status === "error" && (
            <div className="run-overlay">
              <div className="run-error">
                <h3><Icon name="error" /> {t("run.failed")}</h3>
                <pre className="error-pre">{error}</pre>
                <div className="row gap">
                  <button className="btn primary" onClick={() => void start()}><Icon name="refresh" /> {t("run.retry")}</button>
                  <button className="btn" onClick={() => useStore.getState().setMode("edit")}>{t("run.exit")}</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      <aside className="run-side">
        <div className="section-head">{t("run.variables")}<span className="muted">{numericVars.length}</span></div>
        <p className="muted small run-note">{t("run.varHint")}</p>
        <div className="run-vars">
          {numericVars.length === 0 && <div className="list-empty">{t("run.noVariables")}</div>}
          {numericVars.map((v) => (
            <VarRow key={v.name} name={v.name} type={v.type} value={vars[v.name]} disabled={status !== "ready"}
              onSet={(n) => void setVariable(v.name, n)} />
          ))}
        </div>
        <div className="section-head">{t("run.log")}
          <button className="link small run-clear" onClick={() => setLog([])} disabled={!log.length}>{t("run.clearLog")}</button>
        </div>
        <div className="run-log">
          {log.map((e) => (
            <div key={e.key} className={`log-row ${e.error ? "err" : ""}`}>
              <div className="log-head">
                <span className="log-time">{e.time}</span>
                <span className="log-text">{e.text}</span>
                {e.page !== null && <span className="chip tiny">{t("run.toPage", { page: e.page })}</span>}
              </div>
              {e.changes.length > 0 ? (
                <div className="log-changes">
                  {e.changes.map((c) => (
                    <span key={c.name} className="log-change">
                      <b>{c.name}</b> {c.before !== undefined && <>{fmt(c.before)} → </>}{fmt(c.after)}
                    </span>
                  ))}
                </div>
              ) : !e.error && e.text !== t("run.started") ? <div className="log-changes muted">{t("run.noChange")}</div> : null}
            </div>
          ))}
        </div>
      </aside>
    </main>
  );
}

function VarRow({ name, type, value, disabled, onSet }: { name: string; type: string; value: unknown; disabled: boolean; onSet: (v: number) => void }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<string | null>(null);
  const shown = draft ?? fmt(value);
  const invalid = draft !== null && parseVarValue(draft) === null;
  const commit = () => {
    if (draft === null) return;
    const v = parseVarValue(draft);
    setDraft(null);
    if (v !== null && v !== value) onSet(v);
  };
  return (
    <label className="var-row" title={invalid ? t("run.invalidValue") : `${name} · ${type}`}>
      <span className="var-name">{name}</span>
      <span className="var-type">{type}</span>
      <input className={`mono ${invalid ? "invalid" : ""}`} value={shown} disabled={disabled} inputMode="numeric"
        onChange={(e) => setDraft(e.target.value)} onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setDraft(null);
        }} />
    </label>
  );
}
