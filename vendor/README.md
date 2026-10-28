# Vendor tools (DWIN T5L / DGUS II)

Downloaded 2026-10-28 from https://www.dwin-global.com/tool-page/ and /development-guide/.
Binaries are git-ignored; this file is the manifest.

## tools/ (extracted) — downloads/ holds the original archives
| Folder | What | Notes |
|---|---|---|
| DGUS_V7651 | DGUS II editor V7.651 (Google Drive link on tool page) | Main exe is **.NET** (decompile with ILSpy). `TOOL/` = Qt helpers: ICL/icon builder (DW_ICON), font tools, 22.exe (touch/config), movie2icl, ED4 |
| DGUS-Software-Run-Environment2 | .NET 2.0 runtimes + setup doc | |
| NET-Framework-3.5 | .NET 3.5 installer | |
| XR21X141X-Driver | USB-UART driver for HDL662 adapter | |
| DownLoadFor8051-V1.4 | Flash Keil C51 .bin to T5L OS core over UART | |
| OSBuild3.0.2.6 | DWIN OS (assembly-like) builder | |
| Terminal-Assistant_V6.0 | T5L_TA (instruction-mode) terminal | |

## docs/
- T5L_DGUSII-Application-Development-Guide-V2.921.pdf — **main reference** (VP/SP variables, control descriptors, 13/14/22.bin, T5LCFG)
- COF-Screen-Application-DevelopmentT5L_DGUSII20220610.pdf
- Development-Guide-of-T5L-ASIC-2024-09-25.pdf — 8051 core, SFRs, DGUS memory access from C51
- DWIN-T5L-Smart-LCMs-UART-C51-Program.pdf — C51 UART example code
- T5L-DWIN-OS-development-guide-202205181.pdf, Development-Guide-of-DWIN-OS-Platform-Based-on-T5L-CPU12.151.pdf
- T5L_TA-Development-GuideV3.pdf, Evaluation-Board-Schematic.pdf

## Not downloadable / manual
- **Keil C51** v9.61 eval: registration form at https://www.keil.com/demo/eval/c51.htm (2 KB code limit in eval). Free alternative: SDCC.
- **T5L C51 SDK/demo project**: not published on DWIN's site; ask DWIN support/forum or use the code in the ASIC/C51 guides.
- **HDL662S adapter, microSD card**: hardware.
