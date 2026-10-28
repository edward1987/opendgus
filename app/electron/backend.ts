// Spawns the Python backend (`python -m opendgus.server --port 0`) and waits for its ready line.
import { ChildProcess, spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as readline from "readline";

export interface BackendInfo {
  port: number;
  token: string;
}

/** Folder that contains `src/opendgus` (the repo root in dev, `resources/backend` when packaged). */
export function findBackendRoot(appPath: string, resourcesPath: string): string {
  const candidates = [
    process.env.OPENDGUS_ROOT,
    path.resolve(appPath, ".."),
    path.join(resourcesPath, "backend"),
    path.resolve(appPath, "..", ".."),
  ].filter((p): p is string => !!p);
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, "src", "opendgus", "server.py"))) return c;
  }
  return candidates[0];
}

/** OPENDGUS_PYTHON env, else the repo's .venv, else `python` on PATH. */
export function findPython(root: string): string {
  if (process.env.OPENDGUS_PYTHON) return process.env.OPENDGUS_PYTHON;
  const venv =
    process.platform === "win32"
      ? path.join(root, ".venv", "Scripts", "python.exe")
      : path.join(root, ".venv", "bin", "python");
  if (fs.existsSync(venv)) return venv;
  return process.platform === "win32" ? "python" : "python3";
}

export class Backend {
  proc: ChildProcess | null = null;
  info: BackendInfo | null = null;
  log: string[] = [];

  start(root: string, project?: string, timeoutMs = 30000): Promise<BackendInfo> {
    const python = findPython(root);
    const args = ["-m", "opendgus.server", "--port", "0"];
    if (project) args.push("--project", project);
    const env = {
      ...process.env,
      PYTHONPATH: [path.join(root, "src"), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
      PYTHONUNBUFFERED: "1",
      PYTHONIOENCODING: "utf-8",
    };
    return new Promise((resolve, reject) => {
      let settled = false;
      const fail = (msg: string) => {
        if (settled) return;
        settled = true;
        reject(new Error(`${msg}\npython: ${python}\n${this.log.slice(-20).join("\n")}`));
      };
      let proc: ChildProcess;
      try {
        proc = spawn(python, args, { cwd: root, env, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
      } catch (e) {
        fail(String(e));
        return;
      }
      this.proc = proc;
      const timer = setTimeout(() => fail("backend did not report ready in time"), timeoutMs);
      readline.createInterface({ input: proc.stdout! }).on("line", (line) => {
        if (!settled && line.trim().startsWith("{")) {
          try {
            const msg = JSON.parse(line);
            if (msg.event === "ready") {
              settled = true;
              clearTimeout(timer);
              this.info = { port: msg.port, token: msg.token };
              resolve(this.info);
              return;
            }
          } catch {
            /* not our line */
          }
        }
        this.pushLog(line);
      });
      readline.createInterface({ input: proc.stderr! }).on("line", (line) => this.pushLog(line));
      proc.on("error", (e) => {
        clearTimeout(timer);
        fail(`could not start backend: ${e.message}`);
      });
      proc.on("exit", (code) => {
        clearTimeout(timer);
        this.proc = null;
        fail(`backend exited with code ${code}`);
      });
    });
  }

  private pushLog(line: string) {
    this.log.push(line);
    if (this.log.length > 500) this.log.splice(0, this.log.length - 500);
    if (process.env.OPENDGUS_DEBUG) console.log("[backend]", line);
  }

  stop() {
    const p = this.proc;
    this.proc = null;
    if (!p || p.killed) return;
    try {
      if (process.platform === "win32" && p.pid) {
        spawn("taskkill", ["/pid", String(p.pid), "/t", "/f"], { windowsHide: true });
      } else {
        p.kill("SIGTERM");
      }
    } catch {
      /* already gone */
    }
  }
}
