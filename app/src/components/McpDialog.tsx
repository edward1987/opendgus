// "Connect an AI app (MCP)": config snippets for Claude Desktop, Codex and Antigravity with the real path of the
// installed opendgus-mcp program, each with a copy button, and one-click registration in Codex.
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { bridge } from "../lib/api";
import { claudeConfigPath, McpAppStatus, McpCommand, mcpSnippets, McpSnippet } from "../lib/mcpConfig";
import { useStore } from "../store";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

type AppId = "claude" | "codex" | "antigravity";
const APPS: AppId[] = ["claude", "codex", "antigravity"];

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  }
}

function Snippet({ s }: { s: McpSnippet }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  return (
    <div className="mcp-snippet">
      <pre className="mcp-code" data-lang={s.lang}>{s.text}</pre>
      <button className="btn sm mcp-copy" onClick={() => void copyText(s.text).then((ok) => {
        setCopied(ok);
        if (ok) setTimeout(() => setCopied(false), 1500);
      })}>
        <Icon name={copied ? "check" : "copy"} size={13} /> {copied ? t("mcp.copied") : t("mcp.copy")}
      </button>
    </div>
  );
}

function CodexSetup({ status, project, onChange }: {
  status: McpAppStatus | null;
  project: string | null;
  onChange: (s: McpAppStatus) => void;
}) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = (action: "install" | "remove") => {
    setBusy(true);
    setError(null);
    bridge.mcpCodex(action, project).then(onChange, (e) => setError(String(e?.message ?? e)))
      .finally(() => setBusy(false));
  };
  if (!status) return null;
  const state = !status.command ? "none" : !status.exists ? "broken" : status.current ? "ok" : "other";
  return (
    <div className="mcp-setup">
      <div className={`alert small ${state === "ok" ? "ok" : state === "none" ? "" : "error"}`}>
        {t(`mcp.codex_${state}`)}
        {status.command && state !== "ok" && <div className="mono small">{status.command}</div>}
      </div>
      <div className="row gap">
        <button className="btn primary" disabled={busy} onClick={() => run("install")}>
          <Icon name="plug" size={14} /> {t(state === "none" ? "mcp.codexAdd" : "mcp.codexUpdate")}
        </button>
        {status.command && (
          <button className="btn" disabled={busy} onClick={() => run("remove")}>{t("mcp.codexRemove")}</button>
        )}
      </div>
      <p className="muted small">{t("mcp.codexAfter", { config: status.config })}</p>
      {error && <div className="alert error small">{error}</div>}
    </div>
  );
}

export function McpDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const folder = useStore((s) => s.folder);
  const [cmd, setCmd] = useState<McpCommand | null | undefined>(undefined);
  const [platform, setPlatform] = useState("win32");
  const [app, setApp] = useState<AppId>("claude");
  const [withProject, setWithProject] = useState(true);
  const [codex, setCodex] = useState<McpAppStatus | null>(null);
  const [prepError, setPrepError] = useState<string | null>(null);

  useEffect(() => {
    void bridge.getConfig().then((c) => {
      setPlatform(c.platform);
      if (c.smokeDialog === "mcp-codex") setApp("codex");
    });
    // may copy the server to a lasting folder first (portable build), which takes a few seconds
    void bridge.mcpPrepare().then((r) => {
      setCmd(r.mcp);
      setCodex(r.codex);
      setPrepError(r.error);
    }, () => setCmd(null));
  }, []);

  const snippets = cmd ? mcpSnippets(cmd, withProject ? folder : null) : [];
  const pick = (id: McpSnippet["id"]) => snippets.find((s) => s.id === id);

  return (
    <Modal title={t("mcp.title")} onClose={onClose} width={640} className="mcp-dialog"
      footer={<><span className="grow" /><button className="btn primary" onClick={onClose}>{t("mcp.done")}</button></>}>
      <p className="muted">{t("mcp.intro")}</p>
      {prepError && <div className="alert error small">{t("mcp.prepareFailed", { error: prepError })}</div>}
      {cmd === undefined ? (
        <p className="muted small">{t("mcp.preparing")}</p>
      ) : cmd === null ? (
        <div className="alert error small">{t("mcp.unavailable")}</div>
      ) : (
        <>
          <label className="field">
            <span>{t("mcp.program")}</span>
            <Snippet s={{ id: "codex", lang: "bash", text: [cmd.command, ...cmd.args].join(" ") }} />
            {cmd.source !== "bundled" && <span className="muted small">{t("mcp.devNote")}</span>}
          </label>
          {folder && (
            <label className="mcp-check">
              <input type="checkbox" checked={withProject} onChange={(e) => setWithProject(e.target.checked)} />
              <span>{t("mcp.withProject")} <span className="mono">{folder}</span></span>
            </label>
          )}
          <div className="segmented">
            {APPS.map((a) => (
              <button key={a} className={app === a ? "on" : ""} onClick={() => setApp(a)}>{t(`mcp.app_${a}`)}</button>
            ))}
          </div>
          {app === "claude" && (
            <>
              <p className="small">{t("mcp.claudeHow", { path: claudeConfigPath(platform) })}</p>
              <Snippet s={pick("claude")!} />
            </>
          )}
          {app === "codex" && (
            <>
              <CodexSetup status={codex} project={withProject ? folder : null} onChange={setCodex} />
              <p className="small">{t("mcp.codexHow")}</p>
              <Snippet s={pick("codex")!} />
              <p className="small">{t("mcp.codexTomlHow")}</p>
              <Snippet s={pick("codexToml")!} />
            </>
          )}
          {app === "antigravity" && (
            <>
              <p className="small">{t("mcp.antigravityHow")}</p>
              <Snippet s={pick("antigravity")!} />
            </>
          )}
          <p className="muted small">{t("mcp.liveNote")}</p>
        </>
      )}
    </Modal>
  );
}
