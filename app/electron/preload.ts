// Preload: the only bridge between the sandboxed renderer and Electron (contextIsolation on, no Node in renderer).
import { contextBridge, ipcRenderer } from "electron";

const api = {
  getConfig: () => ipcRenderer.invoke("config:get"),
  openFolder: (opts?: { title?: string; create?: boolean }) => ipcRenderer.invoke("dialog:openFolder", opts),
  openImage: (title?: string) => ipcRenderer.invoke("dialog:openImage", title),
  importAsset: (folder: string, file: string) => ipcRenderer.invoke("assets:import", folder, file),
  recentList: () => ipcRenderer.invoke("recent:list"),
  recentAdd: (folder: string, name: string) => ipcRenderer.invoke("recent:add", folder, name),
  recentRemove: (folder: string) => ipcRenderer.invoke("recent:remove", folder),
  openPath: (p: string) => ipcRenderer.invoke("shell:openPath", p),
  defaultProjectsDir: () => ipcRenderer.invoke("app:defaultProjectsDir"),
  signalRendered: () => ipcRenderer.send("app:rendered"),
  settingsGet: (key: string) => ipcRenderer.invoke("settings:get", key),
  settingsSet: (key: string, value: unknown) => ipcRenderer.invoke("settings:set", key, value),
  // API keys: encrypted in the main process with safeStorage; the renderer only ever holds them in memory.
  setSecret: (name: string, value: string) => ipcRenderer.invoke("secret:set", name, value),
  getSecret: (name: string) => ipcRenderer.invoke("secret:get", name),
  deleteSecret: (name: string) => ipcRenderer.invoke("secret:delete", name),
  secretsEncrypted: () => ipcRenderer.invoke("secret:available"),
  mcpPrepare: () => ipcRenderer.invoke("mcp:prepare"),
  mcpCodex: (action: "install" | "remove", project: string | null) => ipcRenderer.invoke("mcp:codex", action, project),
};

contextBridge.exposeInMainWorld("opendgus", api);
