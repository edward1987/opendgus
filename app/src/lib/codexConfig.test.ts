import { describe, expect, it } from "vitest";
import { readServerCommand, removeServer, serverBlock, setServer } from "../../electron/codexConfig";

const exe = "C:\\Users\\me\\AppData\\Local\\Programs\\OpenDGUS\\resources\\backend\\opendgus-mcp.exe";

const existing = [
  'model = "gpt-6"',
  "",
  "[mcp_servers.node_repl]",
  "command = 'node_repl.exe'",
  "",
  "[mcp_servers.opendgus]",
  "command = 'C:\\Temp\\3LKv\\resources\\backend\\opendgus-mcp.exe'",
  "",
  "[mcp_servers.opendgus.env]",
  "OPENDGUS_PROJECT = 'C:\\old'",
  "",
  "[projects.'d:\\apps\\x']",
  'trust_level = "trusted"',
  "",
].join("\r\n");

describe("codex config.toml", () => {
  it("reads the configured command, ignoring the env sub-table", () => {
    expect(readServerCommand(existing, "opendgus")).toBe("C:\\Temp\\3LKv\\resources\\backend\\opendgus-mcp.exe");
    expect(readServerCommand(existing, "node_repl")).toBe("node_repl.exe");
    expect(readServerCommand(existing, "missing")).toBeNull();
    expect(readServerCommand('[mcp_servers."opendgus"]\ncommand = "C:\\\\a b\\\\x.exe"\n', "opendgus")).toBe("C:\\a b\\x.exe");
  });

  it("removes the server and its sub-tables, keeping everything else byte for byte", () => {
    const out = removeServer(existing, "opendgus");
    expect(out).not.toContain("opendgus");
    expect(out).toContain("[mcp_servers.node_repl]\r\ncommand = 'node_repl.exe'");
    expect(out).toContain("[projects.'d:\\apps\\x']\r\ntrust_level = \"trusted\"");
    expect(out.split("\r\n").every((l) => !l.includes("\n"))).toBe(true);
  });

  it("replaces a stale block with the new one, at the end, with the file's line endings", () => {
    const out = setServer(existing, "opendgus", {
      command: exe, args: [], env: { OPENDGUS_PROJECT: "C:\\work\\screen" }, startupTimeoutSec: 30,
    });
    expect(readServerCommand(out, "opendgus")).toBe(exe);
    expect(out.match(/\[mcp_servers\.opendgus\]/g)).toHaveLength(1);
    expect(out).not.toContain("3LKv");
    expect(out).toContain("startup_timeout_sec = 30\r\n\r\n[mcp_servers.opendgus.env]\r\nOPENDGUS_PROJECT = 'C:\\work\\screen'\r\n");
    expect(out.indexOf("[projects.")).toBeLessThan(out.indexOf("[mcp_servers.opendgus]"));
    expect(setServer(out, "opendgus", { command: exe, args: [], env: { OPENDGUS_PROJECT: "C:\\work\\screen" },
      startupTimeoutSec: 30 })).toBe(out);   // idempotent
  });

  it("creates the file content from scratch and quotes awkward paths", () => {
    const out = setServer("", "opendgus", { command: "/opt/it's/opendgus-mcp", args: ["-m", "x"] });
    expect(out).toBe(serverBlock("opendgus", { command: "/opt/it's/opendgus-mcp", args: ["-m", "x"] }));
    expect(out).toContain(`command = "/opt/it's/opendgus-mcp"`);
    expect(out).toContain("args = ['-m', 'x']");
    expect(readServerCommand(out, "opendgus")).toBe("/opt/it's/opendgus-mcp");
  });
});
