import { describe, expect, it } from "vitest";
import { claudeConfigPath, mcpSnippets } from "./mcpConfig";

const exe = "C:\\Program Files\\OpenDGUS\\resources\\backend\\opendgus-mcp.exe";

describe("mcpSnippets", () => {
  it("builds Claude/Antigravity JSON with the real path and optional project", () => {
    const s = mcpSnippets({ command: exe, args: [], source: "bundled" }, "C:\\work\\screen");
    const claude = JSON.parse(s.find((x) => x.id === "claude")!.text);
    expect(claude.mcpServers.opendgus.command).toBe(exe);
    expect(claude.mcpServers.opendgus.args).toBeUndefined();
    expect(claude.mcpServers.opendgus.env).toEqual({ OPENDGUS_PROJECT: "C:\\work\\screen" });
    expect(s.find((x) => x.id === "antigravity")!.text).toBe(s.find((x) => x.id === "claude")!.text);
  });

  it("quotes paths with spaces for the codex CLI and uses TOML literal strings", () => {
    const s = mcpSnippets({ command: exe, args: [], source: "bundled" });
    expect(s.find((x) => x.id === "codex")!.text).toBe(`codex mcp add opendgus -- "${exe}"`);
    expect(s.find((x) => x.id === "codexToml")!.text).toBe(`[mcp_servers.opendgus]\ncommand = '${exe}'\nstartup_timeout_sec = 30`);
  });

  it("includes args for the python fallback", () => {
    const s = mcpSnippets({ command: "/usr/bin/python3", args: ["-m", "opendgus.mcp_server"], source: "python" });
    expect(s.find((x) => x.id === "codex")!.text).toBe("codex mcp add opendgus -- /usr/bin/python3 -m opendgus.mcp_server");
    expect(s.find((x) => x.id === "codexToml")!.text).toContain(`args = ['-m', 'opendgus.mcp_server']`);
    expect(JSON.parse(s[0].text).mcpServers.opendgus.args).toEqual(["-m", "opendgus.mcp_server"]);
  });

  it("knows the Claude Desktop config location", () => {
    expect(claudeConfigPath("win32")).toContain("%APPDATA%");
    expect(claudeConfigPath("darwin")).toContain("Application Support");
  });
});
