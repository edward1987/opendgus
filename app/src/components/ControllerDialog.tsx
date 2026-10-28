// Controller code: generate the MCU project (Arduino, MicroPython, Python) for this design, build it, upload it,
// or start a new project from a ready-made sample.
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { bridge } from "../lib/api";
import { useStore } from "../store";
import { Switch } from "./fields";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

interface BoardInfo { id: string; title: string; language: "arduino" | "micropython" | "python"; network: boolean; max_baud: number; wiring: string[] }
interface SampleInfo { id: string; title: string; description: string; wifi: boolean }
interface GenResult { folder: string; board: string; main: string; files: string[]; changed: string[]; regions: string[]; warnings: string[] }
interface FileResult { path: string; content: string; regions: string[]; files: string[] }
interface BuildOut { ok: boolean; errors?: string[]; output?: string; size?: string[]; note?: string; uploaded?: boolean }
interface Toolchain { arduino_cli: string | null; arduino_cli_version: string | null; install_arduino_cli: string }

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));
const LANGS: BoardInfo["language"][] = ["arduino", "micropython", "python"];

export function ControllerDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"code" | "samples">("code");
  return (
    <Modal title={t("controller.title")} onClose={onClose} width={980} className="controller-modal"
      footer={<button className="btn primary" onClick={onClose}>{t("common.done")}</button>}>
      <div className="seg">
        <button className={tab === "code" ? "on" : ""} onClick={() => setTab("code")}><Icon name="chip" size={14} /> {t("controller.tabCode")}</button>
        <button className={tab === "samples" ? "on" : ""} onClick={() => setTab("samples")}><Icon name="star" size={14} /> {t("controller.tabSamples")}</button>
      </div>
      {tab === "code" ? <CodeTab /> : <SamplesTab onDone={onClose} />}
    </Modal>
  );
}

function useBoards() {
  const api = useStore((s) => s.api);
  const [boards, setBoards] = useState<BoardInfo[]>([]);
  useEffect(() => { void api?.tool<BoardInfo[]>("list_controller_boards").then(setBoards).catch(() => setBoards([])); }, [api]);
  return boards;
}

function BoardSelect({ boards, value, onChange }: { boards: BoardInfo[]; value: string; onChange: (id: string) => void }) {
  const { t } = useTranslation();
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {!value && <option value="">{t("controller.chooseBoard")}</option>}
      {LANGS.map((l) => (
        <optgroup key={l} label={t(`controller.lang_${l}`)}>
          {boards.filter((b) => b.language === l).map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
        </optgroup>
      ))}
    </select>
  );
}

function CodeTab() {
  const { t } = useTranslation();
  const api = useStore((s) => s.api)!;
  const project = useStore((s) => s.project)!;
  const st = useStore.getState;
  const boards = useBoards();
  const [board, setBoard] = useState(project.controller?.board ?? "");
  const [mqtt, setMqtt] = useState(!!project.controller?.mqtt);
  const [gen, setGen] = useState<GenResult | null>(null);
  const [file, setFile] = useState<FileResult | null>(null);
  const [busy, setBusy] = useState<null | "gen" | "build" | "flash">(null);
  const [out, setOut] = useState<BuildOut | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tc, setTc] = useState<Toolchain | null>(null);
  const [ports, setPorts] = useState<{ port: string; description: string }[]>([]);
  const [port, setPort] = useState("");
  const [copied, setCopied] = useState(false);
  const info = boards.find((b) => b.id === board);

  const refreshPorts = () => void api.tool<{ port: string; description: string }[]>("list_serial_ports").then((p) => {
    setPorts(p);
    setPort((cur) => cur || p.find((x) => !/XR21V1410/i.test(x.description))?.port || "");
  }).catch(() => setPorts([]));

  useEffect(() => {
    void api.tool<Toolchain>("controller_toolchain").then(setTc).catch(() => setTc(null));
    refreshPorts();
  }, []);

  const loadFile = async (path = "") => {
    try {
      setFile(await api.tool<FileResult>("read_controller_file", { board, path }));
    } catch {
      setFile(null);
    }
  };
  // show the existing code when the dialog opens on a project that already has it
  useEffect(() => { if (board) void loadFile(); else setFile(null); setGen(null); setOut(null); }, [board]);

  const generate = async () => {
    setBusy("gen"); setErr(null); setOut(null);
    try {
      const r = await st().applyTool<GenResult>("generate_controller_project", { board, mqtt: info?.network ? mqtt : false });
      setGen(r);
      await loadFile();
    } catch (e) { setErr(errText(e)); } finally { setBusy(null); }
  };
  const build = async () => {
    setBusy("build"); setErr(null); setOut(null);
    try { setOut(await api.tool<BuildOut>("compile_controller", { board })); } catch (e) { setErr(errText(e)); } finally { setBusy(null); }
  };
  const flash = async () => {
    if (!port) return;
    setBusy("flash"); setErr(null); setOut(null);
    try { setOut(await api.tool<BuildOut>("flash_controller", { board, port, confirm: true })); } catch (e) { setErr(errText(e)); } finally { setBusy(null); }
  };
  const folder = file ? `${useStore.getState().folder}/controller/${board}` : null;
  const needsCli = info?.language === "arduino" && tc !== null && !tc.arduino_cli;

  return (
    <div className="ctl">
      <div className="ctl-top">
        <label className="ctl-field"><span>{t("controller.board")}</span><BoardSelect boards={boards} value={board} onChange={setBoard} /></label>
        {info?.network && (
          <label className="ctl-field row gap-sm" title={t("controller.mqttHint")}><Switch checked={mqtt} onChange={setMqtt} /> {t("controller.mqtt")}</label>
        )}
        <span className="spacer" />
        <button className="btn primary" disabled={!board || busy !== null} onClick={() => void generate()}>
          <Icon name="refresh" size={14} /> {file ? t("controller.regenerate") : t("controller.generate")}
        </button>
        {folder && <button className="btn" onClick={() => void bridge.openPath(folder)}><Icon name="folder" size={14} /> {t("controller.openFolder")}</button>}
      </div>

      {!board && <p className="muted">{t("controller.intro")}</p>}
      {info && (
        <div className="ctl-info">
          <div>
            <h4 className="group-title">{t("controller.wiring")}</h4>
            <ul className="ctl-wiring">{info.wiring.map((w) => <li key={w}>{w}</li>)}</ul>
          </div>
          {project.display.baud > info.max_baud && (
            <div className="alert warn small">
              {t("controller.baudWarn", { baud: project.display.baud, max: info.max_baud })}
              <button className="btn sm" onClick={() => st().commit({ ...st().project!, display: { ...st().project!.display, baud: info.max_baud } })}>
                {t("controller.setBaud", { max: info.max_baud })}
              </button>
            </div>
          )}
        </div>
      )}
      {gen && <p className="muted small">{t("controller.generated", { count: gen.changed.length })} {t("controller.userCode")}</p>}
      {err && <pre className="error-pre">{err}</pre>}

      {file && (
        <div className="ctl-code">
          <div className="ctl-files">
            {file.files.map((f) => (
              <button key={f} className={`ctl-file ${f === file.path ? "on" : ""}`} onClick={() => void loadFile(f)}>
                <Icon name="file" size={13} /> {f}
              </button>
            ))}
          </div>
          <div className="ctl-view">
            <div className="ctl-view-head">
              <span className="mono small">{file.path}</span>
              <span className="spacer" />
              <button className="btn sm ghost" onClick={() => { void navigator.clipboard.writeText(file.content); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
                <Icon name={copied ? "check" : "copy"} size={13} /> {copied ? t("mcp.copied") : t("mcp.copy")}
              </button>
            </div>
            <pre className="code-view">{file.content}</pre>
          </div>
        </div>
      )}

      {file && (
        <div className="ctl-actions">
          <button className="btn" disabled={busy !== null || needsCli} onClick={() => void build()}>
            <Icon name="build" size={14} /> {info?.language === "arduino" ? t("controller.compile") : t("controller.check")}
          </button>
          {info?.language !== "python" && (
            <>
              <select value={port} onChange={(e) => setPort(e.target.value)}>
                <option value="">{t("controller.port")}</option>
                {ports.map((p) => <option key={p.port} value={p.port}>{p.port} · {p.description}</option>)}
              </select>
              <button className="icon-btn" title={t("controller.refreshPorts")} onClick={refreshPorts}><Icon name="refresh" size={14} /></button>
              <button className="btn primary" disabled={busy !== null || !port || needsCli} onClick={() => void flash()}>
                <Icon name="upload" size={14} /> {t("controller.upload")}
              </button>
            </>
          )}
          {busy && <span className="row gap-sm muted small"><span className="spinner sm" /> {t(`controller.busy_${busy}`)}</span>}
        </div>
      )}
      {needsCli && <div className="alert warn small">{t("controller.noCli")} <span className="mono">{tc!.install_arduino_cli}</span></div>}
      {info?.language === "arduino" && tc?.arduino_cli && <p className="muted small">arduino-cli: {tc.arduino_cli_version ?? tc.arduino_cli}</p>}
      {out && (
        <div className={`alert ${out.ok ? "ok" : "error"} small`}>
          <b>{out.ok ? (out.uploaded ? t("controller.uploaded") : t("controller.compiled")) : t("controller.failed")}</b>
          {out.size?.map((s) => <span key={s}>{s}</span>)}
          {out.note && <span>{out.note}</span>}
          {!out.ok && (out.errors?.length ? out.errors : [out.output ?? ""]).map((e, i) => <span key={i} className="mono">{e}</span>)}
        </div>
      )}
    </div>
  );
}

function SamplesTab({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const api = useStore((s) => s.api)!;
  const project = useStore((s) => s.project)!;
  const boards = useBoards();
  const [samples, setSamples] = useState<SampleInfo[]>([]);
  const [board, setBoard] = useState(project.controller?.board ?? "pico2");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const info = useMemo(() => boards.find((b) => b.id === board), [boards, board]);
  useEffect(() => { void api.tool<SampleInfo[]>("list_controller_samples").then(setSamples).catch(() => setSamples([])); }, [api]);

  const create = async (s: SampleInfo) => {
    const folder = await bridge.openFolder({ title: t("controller.sampleFolder"), create: true });
    if (!folder) return;
    setBusy(s.id); setErr(null);
    try {
      const st = useStore.getState();
      await st.flushSave();
      const d = st.project!.display;
      await api.tool("create_controller_sample", { sample: s.id, board, folder, width: d.width, height: d.height });
      await st.openProject(folder);
      onDone();
      useStore.getState().setDialog("controller");   // reopens on the new project (keyed by folder)
    } catch (e) { setErr(errText(e)); } finally { setBusy(null); }
  };

  return (
    <div className="ctl">
      <div className="ctl-top">
        <label className="ctl-field"><span>{t("controller.board")}</span><BoardSelect boards={boards} value={board} onChange={setBoard} /></label>
        <span className="muted small">{t("controller.samplesHint")}</span>
      </div>
      {err && <pre className="error-pre">{err}</pre>}
      <div className="sample-grid">
        {samples.map((s) => {
          const blocked = s.wifi && !info?.network;
          return (
            <div key={s.id} className={`sample-card ${blocked ? "off" : ""}`}>
              <div className="sample-title">{s.title}{s.wifi && <span className="chip tiny">MQTT</span>}</div>
              <p className="muted small">{s.description}</p>
              <button className="btn sm" disabled={blocked || busy !== null} title={blocked ? t("controller.needsNetwork") : ""} onClick={() => void create(s)}>
                {busy === s.id ? <span className="spinner sm" /> : <Icon name="plus" size={14} />} {t("controller.createSample")}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
