// Config snippets that connect an external AI app (Claude Desktop, Codex, Antigravity) to the OpenDGUS MCP server.

export interface McpCommand {
  command: string;
  args: string[];
  source: "bundled" | "venv" | "python";
}

/** Registration of OpenDGUS in an AI app's config (see electron/mcpInstall.ts). */
export interface McpAppStatus {
  config: string;
  command: string | null;
  current: boolean;
  exists: boolean;
  skill: boolean;
}

export interface McpSnippet {
  id: "claude" | "codex" | "codexToml" | "antigravity";
  lang: "json" | "bash" | "toml";
  text: string;
}

/** TOML literal string ('...') when possible, else a basic string with escapes. */
function tomlString(s: string): string {
  if (!s.includes("'") && !/[\n\r]/.test(s)) return `'${s}'`;
  return JSON.stringify(s);
}

/** Quote a command-line argument for a shell. Paths are double-quoted as-is: backslashes stay literal, which is
 *  what PowerShell and cmd expect (POSIX paths have none). */
function shellArg(s: string): string {
  return /^[\w@%+=:,./\\-]+$/.test(s) ? s : `"${s.replace(/"/g, '\\"')}"`;
}

export function mcpSnippets(cmd: McpCommand, project?: string | null): McpSnippet[] {
  const env = project ? { OPENDGUS_PROJECT: project } : undefined;
  const server: Record<string, unknown> = { command: cmd.command };
  if (cmd.args.length) server.args = cmd.args;
  if (env) server.env = env;
  const json = JSON.stringify({ mcpServers: { opendgus: server } }, null, 2);

  const envFlag = project ? ` --env OPENDGUS_PROJECT=${shellArg(project)}` : "";
  const codexCli = `codex mcp add opendgus${envFlag} -- ${[cmd.command, ...cmd.args].map(shellArg).join(" ")}`;

  const toml = [
    "[mcp_servers.opendgus]",
    `command = ${tomlString(cmd.command)}`,
    ...(cmd.args.length ? [`args = [${cmd.args.map(tomlString).join(", ")}]`] : []),
    "startup_timeout_sec = 30",
    ...(project ? [`env = { OPENDGUS_PROJECT = ${tomlString(project)} }`] : []),
  ].join("\n");

  return [
    { id: "claude", lang: "json", text: json },
    { id: "codex", lang: "bash", text: codexCli },
    { id: "codexToml", lang: "toml", text: toml },
    { id: "antigravity", lang: "json", text: json },
  ];
}

/** Where Claude Desktop keeps its config on this platform. */
export function claudeConfigPath(platform: string): string {
  if (platform === "win32") return "%APPDATA%\\Claude\\claude_desktop_config.json";
  if (platform === "darwin") return "~/Library/Application Support/Claude/claude_desktop_config.json";
  return "~/.config/Claude/claude_desktop_config.json";
}
