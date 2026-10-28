# OpenDGUS editor (desktop app)

The desktop designer for DWIN T5L (DGUS II) displays: Electron + Vite + React + TypeScript, with react-konva for the
canvas, zustand for state and i18next for English and Romanian.

## Development

```bash
cd app
npm install          # downloads Electron too (if not: node node_modules/electron/install.js)
npm run dev          # Vite dev server + Electron with hot reload
npm run dev -- --project C:/path/to/project   # open a project at start-up
```

Other scripts:

| script | what it does |
| --- | --- |
| `npm run typecheck` | `tsc` for the renderer and for main/preload |
| `npm run build` | compiles main/preload to `dist-electron/` and the renderer to `dist/` |
| `npm start` | runs the built app (`electron .`) |
| `npm test` | vitest unit tests (schema→form mapping, snapping, undo stack, project helpers) |
| `npm run smoke -- [out.png] [projectFolder] [--select c5] [--lang ro]` | builds, opens a project (by default a fresh `home_control` template) and saves a screenshot |
| `npm run dist` | build and package with electron-builder (optional) |

## How the backend is found

At start-up the main process runs the Python backend with `python -m opendgus.server --port 0 [--project DIR]`, reads
its `{"event":"ready","port":N,"token":"..."}` line, and passes port and token to the renderer through the preload
bridge (`window.opendgus`). It kills the backend when the app quits.

* **Python interpreter:** the `OPENDGUS_PYTHON` environment variable if set; otherwise the repo's `.venv`
  (`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` elsewhere); otherwise `python` on PATH.
* **Backend source:** the folder that contains `src/opendgus/server.py`. That is `OPENDGUS_ROOT` if set, else the repo
  root (the parent of `app/`), else `resources/backend` in a packaged build. `src/` is added to `PYTHONPATH`.
* Set `OPENDGUS_DEBUG=1` to echo backend and renderer logs to the terminal. F12 toggles DevTools.

The renderer can also run in a normal browser for UI work: start a backend by hand and open
`http://127.0.0.1:5173/?port=N&token=T`.

## Automated screenshot

```bash
electron . --smoke-screenshot out.png --project C:/path/to/project [--select c5] [--lang ro]
```

This opens the project, waits until the editor has drawn the page preview, saves `capturePage()` to the PNG and exits.
The exit code is 0, or 2 if it gave up waiting after 45 s. Smoke runs use a separate temporary user profile.

## How editing works

* The canvas shows the **exact device render** from `GET /api/preview/{page}.png` as its background. Transparent Konva
  hit boxes on top handle selecting, dragging (snapping to an 8 px grid and to other items' edges and centres, with
  guide lines; hold Alt to move freely), resizing (Transformer), marquee and Shift multi-select. Ctrl+wheel zooms,
  the wheel pans, and so does middle-drag.
* Every edit changes the local project JSON, pushes an undo snapshot (typing and nudging are merged into one step), and
  is saved with a debounced `PUT /api/project`. The preview is fetched again after each save. Undo and redo just
  restore snapshots.
* Tools endpoints are used for create/open, validate, build, icon search, raw DGUS schemas and the device.
* **Live collaboration:** the editor listens on `WS /ws` for `project_changed`. If the backend has no WebSocket support
  it polls every 2 s instead. On a change it fetches the project. If the result matches what it last saved, the change
  was its own write and is ignored. Otherwise:
  * with no local edits pending, it adopts the external project. The previous state goes on the undo stack, so an AI
    edit can be undone. The selection is kept for ids that still exist.
  * with local edits pending, the local save is sent: **last write wins**, and the local edits overwrite the external
    change.

## Keyboard

Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z) undo and redo · Delete removes the selection · Ctrl+D duplicates · arrows nudge by
1 px (Shift: 10 px) · Ctrl+A selects all · Esc deselects · Ctrl+0 fits · Ctrl+1 zooms to 100% · Ctrl+S saves now.
