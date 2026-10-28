# OpenDGUS

**Open-source designer and toolkit for DWIN T5L (DGUS II) smart displays.**

DWIN's T5L displays are cheap and capable, but the official DGUS editor is Windows-only, closed and hard to start
with. OpenDGUS writes the display's files directly, so you can design screens without it. The project grew out of
reverse engineering the editor and its tools.

> Status: early development (v0.1). The file formats and the serial upload already work on real hardware. The
> desktop editor, the AI designer and the MCP server are under construction. See [Roadmap](#roadmap).

## What works today

| Area | Status |
|---|---|
| ICL image libraries (`DGUS_3`) | read and write. A rebuilt library was byte-identical to a DWIN-made one |
| 13.bin touch controls and 14.bin display controls | 13 of 47 control types encoded and byte-matched to DGUS's own code; the rest are documented |
| 22.bin initial variables | write, verified on hardware |
| Fonts (HZK/DZK/BIN, 0# ASCII, 4-bit gray) | write (and read for some) |
| T5LCFG.CFG | decode |
| UART upload, read-back, live variables, touch simulation | works on hardware, using the same sequence as DWIN's AllTool |
| Desktop emulator | page images, icons, numbers, toggles, buttons |

## Quick start (developer preview)

```bash
git clone <this repo> && cd opendgus
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

python -m opendgus.templates.home_control           # builds build/home_control/DWIN_SET
opendgus-emu build/home_control/DWIN_SET            # try it on the desktop
opendgus-load ports                                 # find the display's COM port
opendgus-load upload build/home_control/DWIN_SET -p COM3 --reset
```

You can also copy `DWIN_SET` to a FAT32 microSD card with 4 KB clusters (`opendgus-load sd DWIN_SET E:`) and power the
display on with the card inserted.

## Roadmap

- [x] Reverse-engineered formats, UART protocol, emulator (milestone 1)
- [ ] All 47 DGUS control types, byte-matched against DGUS
- [ ] Project model, compiler and smart widgets (button, toggle, slider, gauge, chart, keypad...)
- [ ] An emulator for every control
- [ ] MCP server, so Claude Desktop, Codex and Antigravity can design screens
- [ ] Electron desktop editor (English / Romanian)
- [ ] In-app AI designer (Claude API, OpenAI-compatible, Ollama)
- [ ] 20 templates for different resolutions and display profiles

## Repository layout

```
src/opendgus/      the Python package (formats, device, emulator, templates)
tests/             pytest suite; tests/vectors holds byte vectors produced by DGUS's own C# code
tools/             csharp_harness: regenerates those vectors from a local decompile (not redistributed)
docs/re/           reverse-engineering notes for every file format and protocol
re/                one-off research scripts
```

## Legal

OpenDGUS is licensed under the **GNU GPL v3 or later** (see `LICENSE`). It contains no DWIN code or binaries; the
formats are implemented from our own reverse-engineering notes in `docs/re/`. DWIN and DGUS are trademarks of
Beijing DWIN Technology Co., Ltd. This project is not affiliated with DWIN.
