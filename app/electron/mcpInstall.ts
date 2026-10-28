// Connects external AI apps to the OpenDGUS MCP server: a stable copy of the server for builds that run from a
// temporary folder, and one-click registration in Codex (config.toml + an OpenDGUS skill).
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import type { McpCommand } from "./backend";
import { readServerCommand, removeServer, setServer } from "./codexConfig";

const NAME = "opendgus";
const EXE = process.platform === "win32" ? ".exe" : "";

/** True when the app runs from a folder that disappears when it quits: the Windows portable .exe (unpacks to
 *  %TEMP%), an AppImage (mounted under /tmp) or a .dmg opened without copying the app to Applications. */
export function isTemporaryLocation(sidecarDir: string): boolean {
  if (process.env.PORTABLE_EXECUTABLE_FILE || process.env.APPIMAGE) return true;
  if (process.platform === "darwin" && sidecarDir.startsWith("/Volumes/")) return true;
  const rel = path.relative(fs.realpathSync(os.tmpdir()), fs.realpathSync(sidecarDir));
  return !!rel && !rel.startsWith("..") && !path.isAbsolute(rel);
}

/** For a temporary location, copy the server once per version to `<userData>/mcp-server/<version>` and return
 *  that command (external apps start it later, when OpenDGUS may be closed). Other builds keep their own path. */
export async function stableMcpCommand(cmd: McpCommand, sidecarDir: string | null, userData: string,
                                       version: string): Promise<McpCommand> {
  if (cmd.source !== "bundled" || !sidecarDir || !isTemporaryLocation(sidecarDir)) return cmd;
  const base = path.join(userData, "mcp-server");
  const dest = path.join(base, version);
  const exe = path.join(dest, `opendgus-mcp${EXE}`);
  if (!fs.existsSync(exe)) {
    const tmp = `${dest}.partial`;
    await fs.promises.rm(tmp, { recursive: true, force: true });
    await fs.promises.cp(sidecarDir, tmp, { recursive: true, verbatimSymlinks: true });
    await fs.promises.rm(dest, { recursive: true, force: true });
    await fs.promises.rename(tmp, dest);
  }
  // old versions; a copy still in use by an AI app stays until next time
  for (const d of fs.readdirSync(base)) {
    if (d !== version) await fs.promises.rm(path.join(base, d), { recursive: true, force: true }).catch(() => {});
  }
  return { command: exe, args: [], source: "bundled" };
}

export function codexHome(): string {
  return process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
}

export interface McpAppStatus {
  /** config file that was checked */
  config: string;
  /** command registered for opendgus, or null */
  command: string | null;
  /** the registered command is this OpenDGUS (same path) */
  current: boolean;
  /** the registered command exists on disk */
  exists: boolean;
  skill: boolean;
}

const skillFile = () => path.join(codexHome(), "skills", NAME, "SKILL.md");

function sameFile(a: string, b: string): boolean {
  const norm = (p: string) => (process.platform === "win32" ? path.resolve(p).toLowerCase() : path.resolve(p));
  return norm(a) === norm(b);
}

/** A registered command that will keep working: bare names are looked up on PATH; a path must exist and must not
 *  be in the temp folder (a closed portable copy leaves a half-deleted folder there whose files are still locked). */
function usable(command: string): boolean {
  if (!/[\\/]/.test(command)) return true;
  if (!fs.existsSync(command)) return false;
  try {
    const rel = path.relative(fs.realpathSync(os.tmpdir()), fs.realpathSync(command));
    return !rel || rel.startsWith("..") || path.isAbsolute(rel);
  } catch {
    return false;
  }
}

export function codexStatus(cmd: McpCommand): McpAppStatus {
  const config = path.join(codexHome(), "config.toml");
  const text = fs.existsSync(config) ? fs.readFileSync(config, "utf8") : "";
  const command = readServerCommand(text, NAME);
  return {
    config,
    command,
    current: !!command && sameFile(command, cmd.command),
    exists: !!command && usable(command),
    skill: fs.existsSync(skillFile()),
  };
}

function writeAtomic(file: string, text: string) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.opendgus-tmp`;
  fs.writeFileSync(tmp, text, "utf8");
  fs.renameSync(tmp, file);
}

/** Register (or re-register) OpenDGUS in Codex's config.toml and install the OpenDGUS skill. */
export function installCodex(cmd: McpCommand, project: string | null): McpAppStatus {
  const config = path.join(codexHome(), "config.toml");
  const text = fs.existsSync(config) ? fs.readFileSync(config, "utf8") : "";
  const backup = `${config}.opendgus-backup`;
  if (text && !fs.existsSync(backup)) fs.writeFileSync(backup, text, "utf8");
  writeAtomic(config, setServer(text, NAME, {
    command: cmd.command,
    args: cmd.args,
    env: project ? { OPENDGUS_PROJECT: project } : undefined,
    startupTimeoutSec: 30,   // the first start after an update can be slow while antivirus scans the new files
  }));
  writeAtomic(skillFile(), CODEX_SKILL);
  return codexStatus(cmd);
}

export function removeCodex(cmd: McpCommand): McpAppStatus {
  const config = path.join(codexHome(), "config.toml");
  if (fs.existsSync(config)) {
    const text = fs.readFileSync(config, "utf8");
    const out = removeServer(text, NAME);
    if (out !== text) writeAtomic(config, out);
  }
  fs.rmSync(path.dirname(skillFile()), { recursive: true, force: true });
  return codexStatus(cmd);
}

/** Codex lists skills in its prompt but may hide MCP tools until the model looks for them ("deferred" tools), so
 *  the skill tells it that OpenDGUS is there and how to use it. */
export const CODEX_SKILL = `---
name: opendgus
description: >-
  Design screens for DWIN T5L / DGUS II touch displays (HMI panels) and generate the controller code that drives
  them (Arduino, Raspberry Pi Pico, ESP32, MicroPython, Raspberry Pi) with the OpenDGUS MCP server. Use when the
  user mentions OpenDGUS, DWIN, DGUS, a touch display / HMI screen, or board code for one.
---

# OpenDGUS

OpenDGUS is connected as the MCP server \`opendgus\`. Its tools are named \`mcp__opendgus__<tool>\`, for example
\`mcp__opendgus__get_project\`, \`mcp__opendgus__create_project\` and \`mcp__opendgus__render_page\`.

If they are not in your visible tool list, they are deferred: look them up by name in the full tool list (for
example \`ALL_TOOLS\` inside \`exec\`, names starting with \`mcp__opendgus__\`) and call them from there. Do not search
the web for OpenDGUS: the tools are local. If no such tool exists, tell the user to open OpenDGUS, AI tab, "Connect
an AI app", and press "Add to Codex", then start a new chat.

Workflow:
1. \`get_project\`, or \`open_project\` / \`create_project\` (display profile or width/height, optionally a template).
2. Read the resource \`opendgus://guide\` for the layout rules.
3. Create the variables, then elements and controls. Check every page with \`render_page\` and \`validate\`.
4. Board code: \`generate_controller_project\` (board, and code for the USER CODE regions), then
   \`compile_controller\` until it builds. Tell the user the wiring.
5. Never call \`device_upload\` or \`flash_controller\` unless the user asked to write to the hardware.
`;
