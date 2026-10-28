// Edits the [mcp_servers.opendgus] block of Codex's config.toml as text, so the rest of the user's file (comments,
// order, formatting) stays exactly as it was. Pure functions: the file I/O is in mcpInstall.ts.

export interface ServerSpec {
  command: string;
  args: string[];
  env?: Record<string, string>;
  startupTimeoutSec?: number;
}

/** TOML literal string ('...') when possible, else a basic string with escapes. */
export function tomlString(s: string): string {
  if (!s.includes("'") && !/[\n\r]/.test(s)) return `'${s}'`;
  return JSON.stringify(s);
}

function headerRe(name: string): RegExp {
  const n = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // [mcp_servers.opendgus], [mcp_servers."opendgus"], [mcp_servers.opendgus.env], with optional spaces
  return new RegExp(`^\\s*\\[\\s*mcp_servers\\s*\\.\\s*(?:${n}|"${n}"|'${n}')\\s*(?:\\.[^\\]]*)?\\]\\s*(?:#.*)?$`);
}

const ANY_HEADER = /^\s*\[/;

/** The text with every table of this server removed ([mcp_servers.<name>] and its sub-tables). */
export function removeServer(text: string, name: string): string {
  const eol = text.includes("\r\n") ? "\r\n" : "\n";
  const lines = text.split(/\r?\n/);
  const out: string[] = [];
  const re = headerRe(name);
  let skipping = false;
  for (const line of lines) {
    if (re.test(line)) {
      skipping = true;
      continue;
    }
    if (skipping && ANY_HEADER.test(line)) skipping = false;
    if (!skipping) out.push(line);
  }
  return out.join(eol).replace(/(\r?\n){3,}$/, eol);
}

export function serverBlock(name: string, spec: ServerSpec, eol = "\n"): string {
  const lines = [
    `[mcp_servers.${name}]`,
    "# added by OpenDGUS (AI tab > Connect an AI app); OpenDGUS replaces this block when you press it again",
    `command = ${tomlString(spec.command)}`,
  ];
  if (spec.args.length) lines.push(`args = [${spec.args.map(tomlString).join(", ")}]`);
  if (spec.startupTimeoutSec) lines.push(`startup_timeout_sec = ${spec.startupTimeoutSec}`);
  const env = Object.entries(spec.env ?? {});
  if (env.length) {
    lines.push("", `[mcp_servers.${name}.env]`);
    for (const [k, v] of env) lines.push(`${k} = ${tomlString(v)}`);
  }
  return lines.join(eol) + eol;
}

/** The text with this server's block replaced by (or appended as) `spec`. */
export function setServer(text: string, name: string, spec: ServerSpec): string {
  const eol = text.includes("\r\n") ? "\r\n" : "\n";
  const rest = removeServer(text, name).replace(/\s+$/, "");
  return (rest ? rest + eol + eol : "") + serverBlock(name, spec, eol);
}

function tomlValue(raw: string): string | null {
  const v = raw.trim();
  if (v.startsWith("'")) {
    const end = v.indexOf("'", 1);
    return end > 0 ? v.slice(1, end) : null;
  }
  if (v.startsWith('"')) {
    const m = /^"((?:[^"\\]|\\.)*)"/.exec(v);
    if (!m) return null;
    try {
      return JSON.parse(`"${m[1]}"`) as string;
    } catch {
      return m[1];
    }
  }
  return null;
}

/** The command of this server in the config text, or null when it is not configured. */
export function readServerCommand(text: string, name: string): string | null {
  const re = headerRe(name);
  const sub = /^\s*\[\s*mcp_servers\s*\.\s*(?:"[^"]*"|'[^']*'|[^.\]\s]+)\s*\./; // [mcp_servers.<name>.env] etc.
  let inMain = false;
  for (const line of text.split(/\r?\n/)) {
    if (ANY_HEADER.test(line)) {
      inMain = re.test(line) && !sub.test(line);
      continue;
    }
    if (!inMain) continue;
    const m = /^\s*command\s*=\s*(.+)$/.exec(line);
    if (m) return tomlValue(m[1]);
  }
  return null;
}
