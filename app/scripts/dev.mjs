// Dev runner: compiles main/preload, starts the Vite dev server and launches Electron pointed at it.
// Extra args are passed to Electron, e.g. `npm run dev -- --project C:/path/to/project`.
import { execFileSync, spawn } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const tsc = path.join(appDir, "node_modules", "typescript", "bin", "tsc");
execFileSync(process.execPath, [tsc, "-p", "tsconfig.electron.json"], { stdio: "inherit", cwd: appDir });

const server = await createServer({ root: appDir, configFile: path.join(appDir, "vite.config.mts") });
await server.listen();
const url = server.resolvedUrls?.local?.[0] ?? "http://127.0.0.1:5173/";
server.printUrls();

const electron = createRequire(import.meta.url)("electron");
const child = spawn(electron, [appDir, ...process.argv.slice(2)], {
  stdio: "inherit",
  cwd: appDir,
  env: { ...process.env, VITE_DEV_SERVER_URL: url },
});
child.on("exit", async (code) => {
  await server.close();
  process.exit(code ?? 0);
});
