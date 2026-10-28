# Research scripts

One-off reverse-engineering tools. Everything proven here now lives in `src/opendgus/`:

| Was | Now |
|---|---|
| re2/dgus_controls.py | `opendgus.formats.controls` |
| re3/dgus_assets.py | `opendgus.formats.icl` / `fonts` / `crc` |
| re4/t5lcfg.py | `opendgus.formats.cfg` |
| dwinload/, dwinemu/ | `opendgus.device.dwinload`, `opendgus.emulator` |

What stays here:
- re1: reader for the DGUS editor's .hmi/.tft project files (MS-NRBF).
- re2: helpers for disassembling DWINDLL.dll.
- re3: PE export dump.
- re4: frame/CRC checks, hex2bin, and the minimal Keil C51 8051 project.
- re5: disassembly of DWIN AllTool.exe's UART downloader.
