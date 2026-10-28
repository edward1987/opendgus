# 05: How DWIN's AllTool.exe downloads files over UART

Source: `vendor/tools/DGUS_V7651/DGUS_V7651/TOOL/AllTool.exe`, the "T5L Download" window (`MainWindowT5LDown`).
It is a 32-bit MinGW/Qt5 binary, not .NET, so it was disassembled with capstone.
Scripts: `re/re5/alltool_xref.py`, `alltool_frames.py`, `setbyte_frames.py`, `dump_func.py`. Raw dumps are in `re/re5/out/`.

## Sequence

| Step | Frame | Code |
|---|---|---|
| Start, baud ≠ 921600 | `5A A5 07 82 00 FC 55 AA 5A A5`: stop the DGUS refresh, then `QTimer::start(2000)` waits **2 s** | 0x4339D0 → 0x42BCF0 |
| Start, baud = 921600 | No stop. The first data packet is sent immediately. | 0x433CBD |
| Data | `5A A5 len 82 <VP> <240 bytes>`. VP starts at 0x8000 and advances per packet (`QByteArray::mid(.., 0xF0)`). | 0x42C410, 0x434203 |
| Flash 32 KB | `5A A5 0F 82 00 AA 5A 02 <blk_hi blk_lo> 80 00 17 70 00 00 00 00`. The **delay is 0x1770 = 6000 ms**. | 0x4355EF |
| Wait | `5A A5 04 83 00 AA 01`, repeated until the operation clears | 0x434A14 / 0x434EF0 |
| End | `5A A5 07 82 00 04 55 AA 5A A5` (reset) | 0x43511A |

The type-specific paths:
- **.LIB** (NOR database): `82 00 08 A5 <addr> 80 00 <len>`, then poll `83 00 08`.
- **T5L51 (8051)**: `82 00 06 5A A5 80 00`.
- **DWIN-OS**: `82 00 06 5A 10 80 00`.
- Both code paths then poll `83 00 06`.

The "OK" reply is compared against the string `5aa503824f4b`.

## Why the delay matters (tested on hardware, 2026-10-28)

The 0x00AA delay field keeps the DGUS refresh paused after each block. With 6000 ms the refresh never restarts
during a download, because sending the next block takes about 3 s at 115200 baud.

With the 100 ms we first used, the GUI core redrew page 0 from a half-written 32.icl and hung. It then hung at
every boot as well. The display is USB-powered, so the PC could not reach it before the hang, and only an SD-card
download recovered it.

With AllTool's timing, rewriting the active 32.icl over UART works. The read-back was byte-identical and the
screen restarted normally. `dwinload upload` now uses this sequence.
