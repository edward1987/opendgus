// OpenDGUS Electron main process: starts the Python backend, owns native dialogs and the recent-projects list.
import { app, BrowserWindow, dialog, ipcMain, Menu, safeStorage, session, shell } from "electron";
import * as fs from "fs";
import * as path from "path";
import { Backend, BackendInfo, findBackendRoot, findBundledBackend, mcpCommand, McpCommand, serverLaunch } from "./backend";

interface Cli {
  smokeOut?: string;
  project?: string;
  select?: string; // smoke: comma-separated item ids to select
  lang?: string; // smoke: UI language
  smokeAiDemo?: string; // smoke: show a canned AI transcript (no network); "settings" also opens the settings
  smokeRun?: string; // smoke: open Run mode and tap "x,y[,holdMs];x,y..." (device px) before the capture
  smokeDialog?: string; // smoke: open this dialog (e.g. "mcp") before the capture
}

function parseCli(argv: string[]): Cli {
  const out: Cli = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--smoke-screenshot") out.smokeOut = argv[++i];
    else if (a.startsWith("--smoke-screenshot=")) out.smokeOut = a.split("=", 2)[1];
    else if (a === "--project") out.project = argv[++i];
    else if (a.startsWith("--project=")) out.project = a.split("=", 2)[1];
    else if (a === "--select") out.select = argv[++i];
    else if (a === "--lang") out.lang = argv[++i];
    else if (a === "--smoke-ai-demo") out.smokeAiDemo = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : "";
    else if (a === "--smoke-run") out.smokeRun = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : "";
    else if (a === "--smoke-dialog") out.smokeDialog = argv[++i];
  }
  if (out.smokeOut) out.smokeOut = path.resolve(out.smokeOut);
  if (out.project) out.project = path.resolve(out.project);
  return out;
}

const cli = parseCli(process.argv.slice(1));
const backend = new Backend();
// keep automated runs away from the user's real profile (recent projects, language)
if (cli.smokeOut) app.setPath("userData", path.join(app.getPath("temp"), "opendgus-smoke-profile"));
let backendInfo: BackendInfo | null = null;
let backendError: string | null = null;
let mcp: McpCommand | null = null;
let win: BrowserWindow | null = null;

// ------------------------------------------------------------------ recent projects

interface Recent {
  folder: string;
  name: string;
  opened: string;
}

const recentFile = () => path.join(app.getPath("userData"), "recent.json");

function readRecent(): Recent[] {
  try {
    const list = JSON.parse(fs.readFileSync(recentFile(), "utf-8"));
    return Array.isArray(list) ? list.filter((r) => r && typeof r.folder === "string") : [];
  } catch {
    return [];
  }
}

function writeRecent(list: Recent[]) {
  try {
    fs.mkdirSync(path.dirname(recentFile()), { recursive: true });
    fs.writeFileSync(recentFile(), JSON.stringify(list.slice(0, 12), null, 2));
  } catch {
    /* non-fatal */
  }
}

// ------------------------------------------------------------------ settings & secrets

// Plain UI settings (no secrets) live in settings.json. Secrets (AI API keys) are encrypted with the OS keychain via
// safeStorage and stored as base64 in secrets.json; they are never written in clear text and never logged. When
// the OS offers no encryption, secrets are kept in memory for this run only.
const settingsFile = () => path.join(app.getPath("userData"), "settings.json");
const secretsFile = () => path.join(app.getPath("userData"), "secrets.json");
const KEY_RE = /^[A-Za-z0-9._-]{1,64}$/;
const memorySecrets = new Map<string, string>();

function readJson(file: string): Record<string, unknown> {
  try {
    const v = JSON.parse(fs.readFileSync(file, "utf-8"));
    return v && typeof v === "object" && !Array.isArray(v) ? v : {};
  } catch {
    return {};
  }
}

function writeJson(file: string, data: Record<string, unknown>) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2));
  fs.renameSync(tmp, file);
}

function setSecret(name: string, value: string): { ok: boolean; persisted: boolean } {
  if (!KEY_RE.test(name) || typeof value !== "string") return { ok: false, persisted: false };
  const all = readJson(secretsFile());
  if (!safeStorage.isEncryptionAvailable()) {
    memorySecrets.set(name, value);
    delete all[name];
    writeJson(secretsFile(), all);
    return { ok: true, persisted: false };
  }
  all[name] = safeStorage.encryptString(value).toString("base64");
  writeJson(secretsFile(), all);
  memorySecrets.delete(name);
  return { ok: true, persisted: true };
}

function getSecret(name: string): string | null {
  if (!KEY_RE.test(name)) return null;
  if (memorySecrets.has(name)) return memorySecrets.get(name)!;
  const enc = readJson(secretsFile())[name];
  if (typeof enc !== "string" || !safeStorage.isEncryptionAvailable()) return null;
  try {
    return safeStorage.decryptString(Buffer.from(enc, "base64"));
  } catch {
    return null; // e.g. profile copied from another machine/user
  }
}

function deleteSecret(name: string) {
  if (!KEY_RE.test(name)) return;
  memorySecrets.delete(name);
  const all = readJson(secretsFile());
  if (name in all) {
    delete all[name];
    writeJson(secretsFile(), all);
  }
}

// ------------------------------------------------------------------ window

function createWindow() {
  win = new BrowserWindow({
    width: cli.smokeOut ? 1440 : 1400,
    height: cli.smokeOut ? 900 : 880,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: "#0b0f17",
    title: "OpenDGUS",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.once("ready-to-show", () => (cli.smokeOut ? win?.showInactive() : win?.show()));
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("before-input-event", (_e, input) => {
    if (input.type === "keyDown" && input.key === "F12") win?.webContents.toggleDevTools();
  });
  if (cli.smokeOut || process.env.OPENDGUS_DEBUG) {
    // surface renderer problems on stdout (automated checks have no devtools)
    win.webContents.on("console-message", (...args: unknown[]) => {
      const a = args[0] as { message?: string; level?: string | number };
      const msg = a && typeof a === "object" && "message" in a ? a.message : String(args[2]);
      console.log("[renderer]", msg);
    });
    win.webContents.on("did-fail-load", (_e, code, desc, url) => console.log("[load-failed]", code, desc, url));
    win.webContents.on("preload-error", (_e, p, err) => console.log("[preload-error]", p, err));
    win.webContents.on("render-process-gone", (_e, d) => console.log("[renderer-gone]", d.reason));
  }
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) win.loadURL(devUrl);
  else win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  win.on("closed", () => (win = null));
}

// The backend does not expose X-OpenDGUS-Issues via CORS; allow the renderer to read it.
function exposeBackendHeaders(info: BackendInfo) {
  const filter = { urls: [`http://127.0.0.1:${info.port}/*`] };
  session.defaultSession.webRequest.onHeadersReceived(filter, (details, cb) => {
    const headers = { ...(details.responseHeaders || {}) };
    headers["Access-Control-Expose-Headers"] = ["X-OpenDGUS-Issues"];
    cb({ responseHeaders: headers });
  });
}

// ------------------------------------------------------------------ smoke screenshot

let smokeDone = false;
async function smokeCapture(reason: string) {
  if (smokeDone || !win || !cli.smokeOut) return;
  smokeDone = true;
  await new Promise((r) => setTimeout(r, 700));
  const img = await win.webContents.capturePage();
  fs.mkdirSync(path.dirname(cli.smokeOut), { recursive: true });
  fs.writeFileSync(cli.smokeOut, img.toPNG());
  console.log(JSON.stringify({ event: "smoke", out: cli.smokeOut, reason, size: img.getSize() }));
  backend.stop();
  app.exit(reason === "ready" ? 0 : 2);
}

// ------------------------------------------------------------------ IPC

function registerIpc() {
  ipcMain.handle("config:get", () => ({
    port: backendInfo?.port ?? null,
    token: backendInfo?.token ?? null,
    backendError,
    initialProject: cli.project ?? null,
    smoke: !!cli.smokeOut,
    select: cli.select ? cli.select.split(",").filter(Boolean) : [],
    lang: cli.lang ?? null,
    smokeAiDemo: cli.smokeOut && cli.smokeAiDemo !== undefined ? cli.smokeAiDemo : null,
    smokeRun: cli.smokeOut && cli.smokeRun !== undefined ? cli.smokeRun : null,
    smokeDialog: cli.smokeOut ? cli.smokeDialog ?? null : null,
    version: app.getVersion(),
    platform: process.platform,
    mcp,
  }));
  ipcMain.handle("dialog:openFolder", async (_e, opts: { title?: string; create?: boolean } = {}) => {
    const props: Electron.OpenDialogOptions["properties"] = ["openDirectory"];
    if (opts.create) props.push("createDirectory", "promptToCreate");
    const r = await dialog.showOpenDialog(win!, { title: opts.title, properties: props });
    return r.canceled || !r.filePaths.length ? null : r.filePaths[0];
  });
  ipcMain.handle("dialog:openImage", async (_e, title?: string) => {
    const r = await dialog.showOpenDialog(win!, {
      title,
      properties: ["openFile"],
      filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "bmp", "gif", "webp"] }],
    });
    return r.canceled || !r.filePaths.length ? null : r.filePaths[0];
  });
  ipcMain.handle("assets:import", (_e, folder: string, file: string) => {
    const dir = path.join(folder, "assets");
    fs.mkdirSync(dir, { recursive: true });
    const ext = path.extname(file);
    const base = path.basename(file, ext).replace(/[^A-Za-z0-9_-]+/g, "_") || "image";
    let name = base + ext.toLowerCase();
    for (let n = 2; fs.existsSync(path.join(dir, name)); n++) name = `${base}_${n}${ext.toLowerCase()}`;
    fs.copyFileSync(file, path.join(dir, name));
    return `assets/${name}`;
  });
  ipcMain.handle("recent:list", () => readRecent().filter((r) => fs.existsSync(path.join(r.folder, "project.json"))));
  ipcMain.handle("recent:add", (_e, folder: string, name: string) => {
    const list = readRecent().filter((r) => path.resolve(r.folder) !== path.resolve(folder));
    list.unshift({ folder, name, opened: new Date().toISOString() });
    writeRecent(list);
  });
  ipcMain.handle("recent:remove", (_e, folder: string) => {
    writeRecent(readRecent().filter((r) => path.resolve(r.folder) !== path.resolve(folder)));
  });
  ipcMain.handle("shell:openPath", (_e, p: string) => shell.openPath(p));
  ipcMain.handle("app:defaultProjectsDir", () => path.join(app.getPath("documents"), "OpenDGUS"));
  ipcMain.handle("settings:get", (_e, key: string) => (KEY_RE.test(key) ? readJson(settingsFile())[key] ?? null : null));
  ipcMain.handle("settings:set", (_e, key: string, value: unknown) => {
    if (!KEY_RE.test(key)) return false;
    const all = readJson(settingsFile());
    all[key] = value;
    try {
      writeJson(settingsFile(), all);
      return true;
    } catch {
      return false;
    }
  });
  ipcMain.handle("secret:set", (_e, name: string, value: string) => {
    try {
      return setSecret(name, value);
    } catch {
      return { ok: false, persisted: false };
    }
  });
  ipcMain.handle("secret:get", (_e, name: string) => getSecret(name));
  ipcMain.handle("secret:delete", (_e, name: string) => {
    try {
      deleteSecret(name);
    } catch {
      /* non-fatal */
    }
  });
  ipcMain.handle("secret:available", () => safeStorage.isEncryptionAvailable());
  ipcMain.on("app:rendered", () => {
    if (cli.smokeOut) void smokeCapture("ready");
  });
}

// ------------------------------------------------------------------ lifecycle

if (!cli.smokeOut && !app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) {
      if (win.isMinimized()) win.restore();
      win.focus();
    }
  });

  app.whenReady().then(async () => {
    Menu.setApplicationMenu(null);
    registerIpc();
    const root = findBackendRoot(app.getAppPath(), process.resourcesPath);
    // Packaged: the PyInstaller sidecar in resources/backend (no Python needed). Dev: Python from the repo .venv.
    const sidecar = app.isPackaged ? findBundledBackend(process.resourcesPath) : null;
    mcp = mcpCommand(root, sidecar);
    try {
      backendInfo = await backend.start(serverLaunch(root, sidecar, cli.project));
    } catch (e) {
      backendError = String((e as Error).message || e);
      console.error(backendError);
    }
    if (backendInfo) exposeBackendHeaders(backendInfo);
    createWindow();
    if (cli.smokeOut) setTimeout(() => void smokeCapture("timeout"), 45000);
  });

  app.on("window-all-closed", () => app.quit());
  app.on("before-quit", () => backend.stop());
  app.on("will-quit", () => backend.stop());
  process.on("exit", () => backend.stop());
}
