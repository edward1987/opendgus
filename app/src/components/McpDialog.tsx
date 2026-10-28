// "Connect an AI app (MCP)": config snippets for Claude Desktop, Codex and Antigravity with the real path of the
// installed opendgus-mcp program, each with a copy button.
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { bridge } from "../lib/api";
import { claudeConfigPath, McpCommand, mcpSnippets, McpSnippet } from "../lib/mcpConfig";
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

export function McpDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const folder = useStore((s) => s.folder);
  const [cmd, setCmd] = useState<McpCommand | null | undefined>(undefined);
  const [platform, setPlatform] = useState("win32");
  const [app, setApp] = useState<AppId>("claude");
  const [withProject, setWithProject] = useState(true);

  useEffect(() => {
    void bridge.getConfig().then((c) => {
      setCmd(c.mcp ?? null);
      setPlatform(c.platform);
    });
  }, []);

  const snippets = cmd ? mcpSnippets(cmd, withProject ? folder : null) : [];
  const pick = (id: McpSnippet["id"]) => snippets.find((s) => s.id === id);

  return (
    <Modal title={t("mcp.title")} onClose={onClose} width={640} className="mcp-dialog"
      footer={<><span className="grow" /><button className="btn primary" onClick={onClose}>{t("mcp.done")}</button></>}>
      <p className="muted">{t("mcp.intro")}</p>
      {cmd === undefined ? null : cmd === null ? (
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
