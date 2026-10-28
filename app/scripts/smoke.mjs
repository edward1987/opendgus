// Automated visual check: build, then launch Electron with --smoke-screenshot against a project.
//   node scripts/smoke.mjs [out.png] [projectFolder]
// Without a project folder, a fresh one is created from the home_control template (1024x600) in the temp dir.
import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(here, "..");
const root = path.resolve(appDir, "..");
const out = path.resolve(process.argv[2] ?? path.join(os.tmpdir(), "opendgus_smoke.png"));
let project = process.argv[3] && !process.argv[3].startsWith("--") ? process.argv[3] : undefined;
const extra = process.argv.slice(project ? 4 : 3); // e.g. --select c5 --lang ro

const python = process.env.OPENDGUS_PYTHON ??
  (process.platform === "win32" ? path.join(root, ".venv", "Scripts", "python.exe") : path.join(root, ".venv", "bin", "python"));

if (!project) {
  project = path.join(os.tmpdir(), "odg_smoke_project");
  rmSync(project, { recursive: true, force: true });
  execFileSync(python, ["-c",
    `from opendgus.templates import home_control; home_control.build(1024, 600).save(r"${project}")`], { stdio: "inherit", cwd: root });
}

if (!existsSync(path.join(appDir, "dist", "index.html")) || process.env.SMOKE_BUILD !== "0") {
  execFileSync(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], { stdio: "inherit", cwd: appDir, shell: process.platform === "win32" });
}

const electron = createRequire(import.meta.url)("electron");
const r = spawnSync(electron, [appDir, "--smoke-screenshot", out, "--project", project, ...extra], { stdio: "inherit", cwd: appDir, timeout: 90000 });
console.log(`smoke exit=${r.status} -> ${out}`);
process.exit(r.status ?? 1);
