// Builds the Python sidecar (opendgus-server, opendgus-mcp, opendgus-load) with PyInstaller into
// packaging/dist/opendgus-backend, which electron-builder ships as resources/backend.
//   node scripts/dist-backend.mjs
// Python: OPENDGUS_PYTHON if set, else the repo .venv, else `python` on PATH. PyInstaller must be installed
// there (`uv pip install -e ".[build]"` or `pip install -e ".[build]"`).
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const venv = process.platform === "win32" ? path.join(root, ".venv", "Scripts", "python.exe") : path.join(root, ".venv", "bin", "python");
const python = process.env.OPENDGUS_PYTHON || (existsSync(venv) ? venv : process.platform === "win32" ? "python" : "python3");

const args = [
  "-m", "PyInstaller", path.join("packaging", "opendgus-backend.spec"),
  "--noconfirm", "--clean",
  "--distpath", path.join("packaging", "dist"),
  "--workpath", path.join("packaging", "build"),
];
console.log(`> ${python} ${args.join(" ")}`);
const r = spawnSync(python, args, { cwd: root, stdio: "inherit" });
if (r.error) console.error(r.error.message);
const exe = path.join(root, "packaging", "dist", "opendgus-backend", `opendgus-server${process.platform === "win32" ? ".exe" : ""}`);
if (r.status === 0 && !existsSync(exe)) {
  console.error(`PyInstaller finished but ${exe} is missing`);
  process.exit(1);
}
process.exit(r.status ?? 1);
