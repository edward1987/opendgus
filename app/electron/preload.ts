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
};

contextBridge.exposeInMainWorld("opendgus", api);
