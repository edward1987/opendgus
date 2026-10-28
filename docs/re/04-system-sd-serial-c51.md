# 04 – System config (T5LCFG.CFG), SD download, memory map, UART protocol, 8051 (C51) side

Scope: T5L (T5L0/T5L1/T5L2) DGUS II, COF module + HDL662S adapter. Out of scope here: project file format,
13/14.bin layouts, ICL/fonts (other reports).

## 0. Sources and conventions

| Tag | File (all under `vendor\`) |
|---|---|
| [AG] | `docs\txt\T5L_DGUSII-Application-Development-Guide-V2.921.txt` (main) |
| [ASIC] | `docs\txt\Development-Guide-of-T5L-ASIC-2024-09-25.txt` |
| [C51] | `docs\txt\DWIN-T5L-Smart-LCMs-UART-C51-Program.txt` |
| [COF] | `docs\txt\COF-Screen-Application-DevelopmentT5L_DGUSII20220610.txt` |
| [OS] | `docs\txt\Development-Guide-of-DWIN-OS-Platform-Based-on-T5L-CPU12.151.txt` |

Refs look like `[AG] p.26 L650`: "p." is the PDF page (the `=== PAGE n ===` marker in the .txt, which is one more than the
number printed on the page), and "L" is the line in the .txt.
Status marks: **[V]** I checked it here (script, compile, or byte-level check). **[D]** The documentation says so, but I have
not tested it on hardware. **[U]** Unverified inference or guess.

Scripts are in `re/re4/ (research copy; code now in src/opendgus)`:
- `t5lcfg.py` decodes a CFG file.
- `dgus_frame.py` builds frames and runs the CRC self-test.
- `hex2bin.py` converts Intel HEX to T5L51.bin.
- `strs.py` dumps strings from a binary.
- `c51\` holds the C51 skeleton.

---

## 1. T5LCFG.CFG (hardware configuration file)

**Naming rule.** The file name must start with `T5LCFG` and end with `.CFG`. Anything in between is free, for example
`T5LCFG_800480.CFG`. A name like `T5L.CFG` is not recognised. Ref: [AG] p.32 L944-948.

**Format.** Binary, big-endian, no checksum. The **magic is 5 bytes: `54 35 4C 43 31` = "T5LC1"**. The "8" in the sample's
"T5LC18" is **not** part of the magic. It is byte 0x05 (SYS_CFG = 0x38), and it only happens to be printable.

**Short files are accepted.** The vendor sample is only 36 bytes and stops after 0x23. Fields that are not in the file are
presumably left unchanged on the device **[U]**. A "Set_En" field must be 0x5A (or 0x5AA5) for its block to take effect.

### 1.1 Byte map
Main source: [AG] p.26-32 L650-940 and p.36-41 L1023-1175. Cross-checked against [COF] p.13-14 L746-869.

| Off | Len | Name | Meaning |
|---|---|---|---|
| 0x00 | 5 | magic | `54 35 4C 43 31` |
| 0x05 | 1 | SYS_CFG | .7 UART2 CRC (1=on). .6 0=buzzer / 1=WAE music. .5 load 22.bin into VP space at power-on. .4 touch-variable auto-upload to UART. .3 touch beep. .2 touch backlight standby (dimming). .1-.0 rotation: 00=0°, 01=90°, 10=180°, 11=270° |
| 0x06 | 1 | SYS_CFG1 | .7 PWM backlight (1 kHz). .6 SPI NAND present. .5 format the NAND (wipes it). .4 NAND size 0=1 Gb / 1=4 Gb. .3 **erase all internal flash**. .2 AD resolution 0=12-bit / 1=16-bit. .1 the 8051 T5L51.bin is encrypted. .0 OS core keeps running during SD download. ([COF] lists .7-.2 as reserved.) |
| 0x07 | 1 | WAE_ID | Location of the music .WAE file, 0x00-0x3F |
| 0x08 | 1 | BG_ICL_ID | Location of the background ICL, 0x10-0x3F. **0x20 → 32.ICL.** A wrong value gives a black screen ([AG] L601-607). |
| 0x09 | 1 | TP_RATE | Touch report rate = 400 Hz ÷ value. Default 0x28. |
| 0x0A | 2 | UART2 baud | Divider = 3225600 ÷ baud (max 0x03FF). 0x001C = 115200, 0x0150 = 9600. |
| 0x0C | 1 | BL_ON | Normal and startup brightness, 0-0x64 (%) |
| 0x0D | 1 | BL_STANDBY | Standby brightness (%) |
| 0x0E | 2 | BL_TIME | Idle time before standby, in 10 ms units |
| 0x10 | 2 | LCD_CFG_EN | 0x5AA5 = apply 0x12-0x1E. Factory-set; leave alone. |
| 0x12 | 1 | PCLK_PHS | Pixel clock latch edge (0/1; [AG] and [COF] disagree on the polarity) |
| 0x13 | 1 | PCLK_DIV | PCLK = 206.4 MHz ÷ value |
| 0x14/0x15 | 1/1 | H_W / H_S | Horizontal sync width / start (back porch?) **[U]** |
| 0x16 | 2 | H_D | Horizontal resolution |
| 0x18 | 1 | H_E | Horizontal end (front porch?) **[U]** |
| 0x19/0x1A | 1/1 | V_W / V_S | Vertical sync width / start |
| 0x1B | 2 | V_D | Vertical resolution |
| 0x1D | 1 | V_E | Vertical end |
| 0x1E | 1 | TCON_SEL | 0 = no TCON init; other values select an init profile (see the TCON table, [AG] p.42 L1176-1222) |
| 0x1F | 1 | reserved | 0 |
| 0x20 | 1 | TP_SET_EN | 0x5A = apply 0x21-0x23 |
| 0x21 | 1 | TP_MODE | Bits .7-.4 = touch type: 0 = 4-wire resistive, 1 = GT911/GT9271/GT9110, 2 = ILI9881H in-cell, 3 = ILI2117, 4 = ILI2130, 5 = BL8825, 6 = GSL1680, 7 = CST340, 8 = ILI231x/251x, F = 5-wire resistive. Bit .3 = resistive calibration on next boot. Bits .2/.1/.0 = invert X / invert Y / swap XY (capacitive only). |
| 0x22 | 1 | TP_SENSE | Capacitive: 0x00-0x1F (default 0x14). Resistive: 0x10-0xFF (default 0x40). 0xFF = keep the hardware default. |
| 0x23 | 1 | TP_FREQ | ILI9881H only. 0 = frequency hopping. |
| 0x24-0x26 | 3 | CKO | En=0x5A, CKO_EN=0x5A (clock out on P3.0), divider: freq = 825.7536 MHz ÷ DIV |
| 0x27-0x2D | 7 | BUZZER | En=0x5A. DIV1 (1 byte), DIV2 (2 bytes), DUTY (2 bytes), TIME (10 ms units). Factory: 6E / 0BB8 / 00F0 / 0A = 2.5 kHz, 8 % duty. |
| 0x2E/0x2F | 1/1 | INIT_FILE | 0x5A + file ID of the init file (default 0x16 = 22) |
| 0x30/0x31 | 1/1 | SYSCLK adjust | 0x5A + trim of -2..+2 (in 1/224 steps). ([AG] also says "0x30 16 bytes reserved"; the two passages conflict.) |
| 0x32/0x33 | 1/1 | PIC_REPLACE | 0x5A + ID of a replacement ICL that overrides pictures in BG_ICL |
| 0x40 | 2 | SD_DIR_EN | 0x5AA5 = rename the SD download folder (persistent) |
| 0x42 | 1 | dir len | 1-8 |
| 0x43 | 8 | dir name | `[0-9A-Za-z_-]`. Invalid characters fall back to "DWIN_SET". |
| 0x4B | 37 | reserved | 0 |
| 0x70/0x71 | 1/1 | BL_DELAY | 0x5A + power-on backlight delay in 10 ms units (default 0x0A) |
| 0x72 | 14 | reserved | 0 (total size is therefore 0x80 = 128 bytes) |

Hardware parameters set by the CFG can also be read and changed at runtime through system variable 0x0080, but those
changes are not saved (§3).

### 1.2 Decode of the vendor sample
The sample is `...\tools\DGUS_V7651\DGUS_V7651\Config\T5LCFG.CFG`, 36 bytes, decoded with `python -I t5lcfg.py <file>` **[V]**:
```
54 35 4C 43 31 38 00 00 20 28 00 1C 40 00 00 00 00 00 01 06 1E 10 03 20 D2 03 14 01 E0 0C 00 00 00 0F 10 00
0x05 SYS_CFG    0x38  CRC off, buzzer, load 22.bin, touch auto-upload on, touch beep on, no standby, 0°
0x06 SYS_CFG1   0x00
0x08 BG_ICL     0x20  -> 32.ICL
0x09 TP_RATE    0x28  (400/40 = 10 Hz as the formula reads; "400 Hz" is probably the ceiling) [U]
0x0A BAUD       0x001C -> 115200
0x0C BL_ON      0x40  (64 %);  0x0D standby 0;  0x0E time 0
0x10 LCD_EN     0x0000 -> LCD timing NOT applied. Payload = 800x480 row of the reference table (PCLK/6 = 34.4 MHz)
0x20 TP_EN      0x00   -> TP not applied. 0x21 = 0x0F, 0x22 = 0x10
```
In other words, this file only sets the common options (byte 0x05, the ICL location, baud and backlight). It does not touch
the panel or touch hardware, which makes it a safe template.

### 1.3 How the editor handles it
- **DGUS V7.651.** `decompiled\DGUS_V7.651\BizDrawClient\Form1.cs:1882-1925` (portrait/landscape button):
  1. If `<project>\T5LCFG.CFG` is missing, copy it from `Config\T5LCFG.CFG`.
  2. Toggle **only** `array[5] bit0` (0 → 90°).
  3. Re-convert the pictures into `DWIN_SET_portrait`.

  The editor has no other CFG writer. The full CFG editor is the Qt tool `TOOL\setdebug.exe` (labels are in
  `TOOL\SystemConfig.ini`; LCD timing presets are in `TOOL\settings.ini [table]`, which matches the [AG] p.42 table).
- **Legacy CONFIG.txt (DwinTerminal).** `decompiled\DwinTerminal\BizDraw.SysConfig\SysCfgDoc.cs:62-304` writes an older text
  config, `CONFIG.txt` (`R1=` baud code 00..11, `R2=` SYS_CFG, `RUN_DWIN_OS;`, `TP_CORRECT;`). Baud code table:
  `SysCfgDoc.cs:81-169`. It is the DGUS-I/T5-era format. On T5L only the binary T5LCFG is documented.

---

## 2. SD-card download

### 2.1 Card and folder rules
Refs: [AG] p.21-24 L490-596; [COF] p.12 L703-743.
- **Card.** SD or SDHC, **FAT32 with 4 KB clusters** (`format g: /fs:fat32 /a:4096 /q`). The guide claims 1-16 GB. A
  Windows right-click format is "not FAT32 enough": the screen shows 0 files or never enters download mode.
- **Folder.** `\DWIN_SET\` at the root only, unless renamed through CFG 0x40-0x4A. **Sub-folders are ignored.**
- **No hot swap.** Power off, insert the card, power on. A **blue download screen** lists the file statistics and ends with
  "SD card process END!". Then power off, remove the card and power on again. Losing power mid-download can leave a black
  screen.
- **CFG 0x06.0** decides whether the 8051 OS core keeps running during the download.

### 2.2 Files recognised in DWIN_SET
The number in a file name is the slot number. Text after the digits is free, e.g. `32_bg.ICL`. Refs: [AG] p.23 L530-580;
[COF] L706-737.

| Pattern | Goes to | Notes |
|---|---|---|
| `T5L_UI*.BIN`, `T5L_OS*.BIN` | GUI-core / OS-core firmware | DWIN kernel |
| `DWINOS*.BIN` | OS core, DWIN-OS bytecode | Code starts at 0x1000 |
| **`T5L51*.BIN`** | OS core user 8051 code | On-chip flash 0x01:0000-0x01:FFFF ([ASIC] p.15 L550). Optional encryption (CFG 0x06.1). |
| `T5L*.BIN` (other) | LCD TCON init | |
| `<id>*.LIB` | On-chip NOR database | id 0-79, 2 K words per ID (160 K words in total) |
| `<id>*.BIN/.DZK/.HZK/.GTF` | Font slot id (0-47 per [AG]) | **Slot 0 = factory ASCII font.** Do not overwrite it unless you mean to. |
| `12*.BIN` | Slot 12 | Input-method file |
| `13*.BIN` | Slot 13 | Touch config, ≤ 256 KB ([COF] says ≤ 32 KB) |
| `14*.BIN` | Slot 14 | Display-variable config, ≤ 256 KB |
| `22*.BIN` | Slot 22 (or the slot in CFG 0x2F) | VP initial values (see 2.4) |
| `<id>*.ICL` | Slot id | Backgrounds (normally **32**, or **23** on 8 MB-flash COF parts) and icons (e.g. 48) |
| `<id>*.WAE` | Slot id | Music. CFG 0x07 points at it. |
| `<id>*.UIC` | UI config module | Each module ID = 32 KB |
| `T5LCFG*.CFG` | System config | §1 |
| `CTPCFG*.CFG` | Capacitive touch controller register burn | magic "CTPS" ([AG] p.43 L1249-1278) |
| `T5*.CRC` | CRC32 verify after download | magic `43 52 43 10` ([AG] p.43 L1228-1248) |

### 2.3 Slot → flash address
Refs: [AG] p.16 L385-404, p.24-26, p.56 (0xAA example).
- The 16 MB SPI NOR is split into **64 × 256 KB slots**. **Byte address = slot × 0x40000.**
  - Slot 13 → 0x340000, slot 14 → 0x380000, slot 22 → 0x580000, slot 32 → 0x800000, slot 48 → 0xC00000.
  - In the 0xAA UART command's 32 KB block numbering, block = slot × 8. Example: 32.ICL → block 0x0100.
- **8 MB parts** (many COF modules) have 32 slots. The background ICL is then usually 23 ([COF] L739-741).
- **Multi-slot files.** A file uses ceil(size ÷ 256 KB) consecutive slots, and nothing checks for overlap. Example: a 1.28 MB
  16.WAE occupies slots 16-21 ([AG] L697-702). Leave room after 32.ICL.
- **Expansion.** NOR can be extended to 64 MB (slot IDs up to 0xBF). SPI NAND uses IDs 0xC0-0xFF, **8 MB each** ([AG] L582-586).
- **Fixed by convention:** 0 (ASCII font), 12, 13, 14, 22, the CFG-selected background slot (32), and the WAE slot.
  Everything else is user-assigned.
- **Per-image limit inside an ICL:** 256 KB (T5L1) or 768 KB (T5L2) ([AG] L392-396).

### 2.4 22.bin, the initial-values file
- It is a byte image of the 128 KB VP RAM: **byte offset = VP × 2**, big-endian words.
- If CFG 0x05.5 = 1, then at boot "load 0x2000-0xFFFF address content and initialize 0x1000-0xFFFF variable space"
  ([AG] L554-555). Byte 0x2000 is VP 0x1000.
- The editor writes `22_Config.bin` as a **131076-byte** buffer (128 KB + 4).
  - Bytes 2048..2559 (VP 0x400-0x4FF, the network-interface block) are copied from `22.bakdata`.
  - Every other initial value is written at `key*2`.
  - Code: `decompiled\DwinTerminal\BizDraw.Controls\TDocumentSpace.cs:3823-3836` and `:4287-4313`.
- [COF] L694-696 confirms that 0x0800-0x09FF in 22.bin holds the communication-device description, and that it is read even
  when the 22-load option is off.

### 2.5 Boot sequence (as documented, not traced in firmware) [D]
1. At power-on the GUI core looks for an SD card with the folder from CFG 0x40 (default DWIN_SET).
2. If found, it shows the blue screen, flashes each recognised file into its slot or on-chip area, then stops.
3. During that download it patches the OS code mark at 0x00F8 from `FFFF` to `0000` ("JMARK forbidden"), keeping
   `44 57 49 4E 54 35` ([ASIC] p.39 L1527-1530).
4. Without a card, it applies CFG, optionally loads 22.bin, shows picture 0 of the background ICL, and starts the 20 ms DGUS
   cycle (reads 13/14.bin). The OS core loads its code from on-chip flash into code RAM and runs from 0x0000 ([ASIC] L548-549).

---

## 3. Memory map

### 3.1 Spaces
| Space | Size | DGUS/UART address | 8051 address | Ref |
|---|---|---|---|---|
| VP RAM (dual-port) | 128 KB | VP 0x0000-0xFFFF (16-bit words) | ADR 0x00:0000-0x00:7FFF (4-byte cells; **cell = VP/2**) | [AG] p.17 L407; [ASIC] p.16 L556-563 |
| Extra variable RAM | 128 KB | Only through UART **0x86/0x87** (dword addresses 0x8000-0xFFFF) | ADR 0x00:8000-0x00:FFFF | [AG] L1381-1400; [ASIC] L560-561 |
| CAN registers | 48 B | — | ADR 0xFF:0060-0xFF:006B | [ASIC] p.31-32 |
| On-chip NOR database | 512 KB (160 K words for user data) | via 0x0008 | — | [AG] L1525 |
| 8051 XDATA | 32 KB | — | 0x8000-0xFFFF (MOVX) | [ASIC] p.18 |

**VP planning** ([AG] p.17-20):
- 0x0000-0x0FFF is system.
- 0x1000-0xFFFF is user space.
- Dynamic curves use 0x1000-0x4FFF (2 K words per channel × 8) when enabled.
- The guide suggests 0x5000-0x7FFF for VPs and 0x8000-0xFFFF for SPs (description pointers).

### 3.2 Most useful system variables (VP 0x0000-0x0FFF)
Source: [AG] Chapter 5, p.49-77, L1504-2945. "D3..D0" means the bytes of a 2-word field, high byte first.

| VP | Name | R/W | Use / format | L# |
|---|---|---|---|---|
| 0x0004 | System_Reset | W | Write `55AA 5AA5` → reset (like a power cycle) | 1509 |
| 0x0006 | OS_Update_CMD | W | D3 = 0x5A go. D2 = type: **0x10** DWIN-OS (28 KB) / **0xA5** 8051 code (64 KB). D1:D0 = VP where the image sits. | 1513 |
| 0x0008 | NOR_FLASH_RW | W | D7 = 0x5A read / 0xA5 write. D6:4 = NOR word address (even). D3:2 = VP. D1:0 = length (even). Poll until D7 = 0. | 1525 |
| 0x000C | UART2 config | W | D3 = 0x5A. D2.7 = CRC. D1:D0 = 206438400 ÷ (64 × baud). Not saved. | 1553 |
| 0x000F | Ver | R | Hi byte GUI version, lo byte OS version (e.g. 0x6322) | 1626 |
| 0x0010 | RTC | R/W | YY MM DD WW hh mm ss 00 (hex) | 1647 |
| 0x0014 | PIC_Now | R | Current page | 1659 |
| 0x0015 | GUI_Status | R | 1 = processing 13/14 | 1664 |
| 0x0016 | TP_Status | R/W | 5A flag, state (1 = press, 2 = lift, 3 = hold), X, Y. **[V]** the 5A flag stays until the MCU clears it | 1669 |
| 0x0031 | LED_Now | R | Current backlight value. **[V]** reads `5A` + level % | 1692 |
| 0x0032-0x0039 | AD0-AD7 | R | Raw ADC | 1698 |
| 0x007A / 0x007B | LCD_HOR / LCD_VER | R | Resolution | 1708 |
| 0x0080 | System_Config | R/W | D3 = 0x5A apply. D0 = live copy of CFG 0x05 (bits .4/.3/.2/.1-0 writable). Not saved. | 1719 |
| **0x0082** | LED_Config | W | D3 = on brightness, D2 = standby brightness, D1:0 = time (10 ms). Plain `5A A5 04 82 00 82 0A` sets brightness. **[V]** with 0x0080 D0 bit 2 set the panel dims after the time; after turning standby off it stays dim until the 1-byte write | 1749 |
| **0x0084** | PIC_Set | W | `5A 01` + page → page switch | 1771 |
| 0x0086 / 0x0088 | PWM0 / PWM1 set | W | 5A + divider + precision | 1786 |
| 0x0092 / 0x0093 | PWM0 / PWM1 out | R/W | Duty cycle | 1816 |
| **0x009C** | RTC_Set | W | `5AA5` YY MM DD hh mm ss (needs a hardware RTC) | 1824 |
| 0x00A0 | Music / buzzer | R/W | Segment, count, volume, status… `5A A5 05 82 00 A0 00 7D` = beep for 1 s (8 ms units) | 1844 |
| **0x00AA** | Ext-flash op | R/W | 5A + mode: 01 read SPI NOR, **02 write a 32 KB block from VP RAM**, 03 font copy, 04-06 NAND | 1879 |
| 0x00B0 | Touch control access | W | Enable, disable or rewrite one touch control | 2302 |
| 0x00D4 | Touch simulation | W | 5AA5 + mode + X + Y | 2405 |
| 0x00D8 | Pointer icon overlay | W | | 2405 |
| 0x00DC / 0x00DE | Switch WAE / background ICL at runtime | W | | 2452 / 2484 |
| 0x00E0 | Memory CRC | R/W | CRC of font slots, OS code or LIB | 2569 |
| 0x00E8 | Page overlay | W | `5A 01` + page | 2603 |
| 0x00F0 | Stream music | W | | 2630 |
| **0x00FC** | DGUS_STOP | W | `55AA5AA5` stop DGUS refresh. `55AA5AAA` also stop the OS core (used for ED4 downloads). `55AA5A5A` disable touch. 0 = resume. | 2758 |
| 0x00FE | UART1 high-speed download | W | 0x5AA5 enable (protocol not documented) | 2771 |
| 0x0100-0x02FF | FSK bus | R/W | | 2772 |
| 0x0300-0x037F | Dynamic curve | R/W | 0x300-0x30F channel pointers, 0x310 write trigger, 0x312+ data blocks | 2778 |
| 0x0380-0x038F | Curve auto-sample | W | Per channel: 5A + interval + VP | 2804 |
| 0x0400-0x04FF | Network (WiFi) | R/W | | 2944 area |
| 0x0F00 | Var-change indication | R/W | 5A + VP + length. Writing it makes the firmware send an 0x83 frame. | 2911 |

---

## 4. UART protocol (DGUS "UART2")

### 4.1 Frame format
Refs: [AG] p.44-47 L1292-1503; [COF] p.6 L267-322.

`5A A5 | LEN | CMD | DATA… | [CRC_lo CRC_hi]`

- Port settings are 8N1, 115200 by default (CFG 0x0A).
- LEN counts CMD + DATA + CRC (when CRC is on).
- The maximum DATA is 249 bytes. For 0x83 the maximum read is 0x7D words (0x7C according to L1440).
- The CRC is enabled by CFG 0x05.7 or by VP 0x000C at runtime. ([COF] L281 says "0x05.6"; that is a typo — its own table
  and [AG] both say .7.)
- **The CRC is CRC-16/MODBUS** (polynomial 0xA001 reflected, init 0xFFFF). It is computed over CMD..DATA and sent low byte
  first. All 10 CRC examples in [AG] and [COF] reproduce exactly with `dgus_frame.py` **[V]**.

| Cmd | Request | Reply |
|---|---|---|
| 0x80 | Register page (0-8) + register + data (DWIN-OS registers) | `4F 4B` |
| 0x81 | Register page + register + byte count | Page, register, length, data |
| **0x82** | VP (2 bytes) + words… | `5A A5 03 82 4F 4B` |
| **0x83** | VP (2 bytes) + word count (1 byte) | `5A A5 LEN 83 VP cnt data…`. The same frame is used for **touch auto-upload**. |
| 0x84 | CH_Mode bitmask + words (write to curve buffers) | `4F 4B` |
| 0x86 / 0x87 | 32-bit dword address (0-0xFFFF) + data / dword count. Reaches all 256 KB. | |

### 4.2 Examples (frame bytes match [AG]; CRC variants checked with `dgus_frame.py`) [V]
```
write VP1000=0002     5A A5 05 82 10 00 00 02
read  VP1000 x1       5A A5 04 83 10 00 01     -> 5A A5 06 83 10 00 01 00 02
read version          5A A5 04 83 00 0F 01     (CRC on: ... 01 ED 90)
page -> 1             5A A5 07 82 00 84 5A 01 00 01
backlight 10 %        5A A5 04 82 00 82 0A     (CRC on: 5A A5 06 82 00 82 0A C8 FB)
reset                 5A A5 07 82 00 04 55 AA 5A A5
RTC set 2019-10-01 11:12:13   5A A5 0B 82 00 9C 5A A5 13 0A 01 0B 0C 0D   (built from the 0x9C table; not a doc example)
baud -> 9600 live     5A A5 07 82 00 0C 5A 00 01 50
beep 1 s              5A A5 05 82 00 A0 00 7D
key upload (touch)    5A A5 06 83 10 01 01 00 0A    (VP 0x1001, key 0x000A)
```
Partial word writes are allowed: `5A A5 04 82 00 82 0A` writes only the high byte of VP 0x0082.

### 4.3 Downloading files over UART instead of SD [D]
1. **Any flash slot (ICL, fonts, 13/14/22, WAE)** uses VP 0x00AA mode 0x02 ([AG] p.56-62 L1879-2300). For each 32 KB block:
   1. Upload the data into scratch VP RAM (e.g. 0x8000-0xBFFF) with 0x82 frames of ≤ 240 bytes. The VP advances by 0x78
      per frame.
   2. Send `5A A5 0F 82 00 AA 5A 02 <blk_hi blk_lo> <VP_hi VP_lo> <delay_ms 2B> 00 00 00 00`, where blk = slot × 8 + n.
   3. Poll `83 00 AA 01` until the high byte ≠ 0x5A.
   4. Finally, reset through 0x0004.

   Optionally stop the DGUS refresh with 0x00FC while doing this.
2. **NOR database (.LIB)**: VP 0x0008 write (0xA5), 2 words of VP per NOR word.
3. **OS-core code**: put the image in VP RAM, then write 0x0006 = `5A A5 <VP>` for 8051 code (64 KB, so VP 0x8000-0xFFFF
   exactly) or `5A 10 <VP>` for DWIN-OS (28 KB).
   - [C51] p.16 L44-47 shows the user `deal_82_cmd` forcing D2 to 0xA5 when the address is 0x0006.
   - **`DownLoadFor8051.exe`** strings **[V]**: `hex2bin `, `64K`, `\T5L51.bin`, `(*.bin;*.hex)`, `COM4`, a serial port, and
     `CalculateCrc16` with `_auchCRCHi/_auchCRCLo` (the classic table-driven Modbus CRC).
   - So it converts HEX to a 64 KB bin and then pushes it over the serial port, most likely with 0x82 frames plus 0x0006
     **[U]**. `flash.dll` is a separate "DWIN Flash with JTAG" Intel-HEX parser (HexParser).
4. **ED4 USB downloader / "virtual UART"**: it talks through the SD-card pins at 8 Mbps. Frame = `5A A5 | LEN (3 bytes) | 82/83 | data`,
   up to 128 KB per frame, strictly request/response ([AG] p.48 L1468-1503). The DGUS TOOL also mentions "ED2" at 6,250,000 baud
   (`TOOL\SystemConfig.ini`).
5. VP 0x00FE "UART1 high-speed download" is not documented any further.

### 4.4 Naming trap: UART1 vs UART2
- **UART1** is the GUI core's own port (pins 39/40). It is used for the USB debug and WiFi link, and C51 code cannot touch it
  ([C51] p.3 L42-49; [ASIC] pin table L233-234).
- **DGUS "UART2"** is "UART0 of OS core" ([COF] p.2 L88-89). That is the 8051's SCON0/SBUF0 on P0.4/P0.5.
- **Consequence [U, strongly suggested]:** the 5A A5 protocol on UART2 is implemented by the **8051 firmware**. The default is
  DWIN's kernel `T5L_OS*.BIN`, and the [C51] sample (p.13-17) re-implements `deal_82_cmd`, `deal_83_cmd` and the 0x0F00
  auto-upload in user C. **Flashing your own T5L51.bin most likely removes the stock UART2 handler.** You must then answer
  82/83 yourself, or use the GUI core's UART1/ED4 for host access.
- On COF parts, UART3 is the internal GUI↔OS link that carries AD samples and PWM values (`AA …` + sum frames,
  [COF] p.6 L324-340).

---

## 5. The 8051 OS core

### 5.1 Memory model ([ASIC] p.15-19)
- **Code**: 64 KB, loaded from on-chip flash 0x01:0000 into code RAM at reset.
  - Vectors: 0x0003 EX0, 0x000B T0, 0x0013 EX1, 0x001B T1, **0x0023 UART2**, 0x002B T2, 0x004B CAN, 0x0053/0x005B UART4
    TX/RX, 0x0063/0x006B UART5 TX/RX, **0x0083 UART3**.
  - Keil interrupt numbers are 0-5, 9-13 and 16.
  - **0x00F8-0x00FF must be `FF FF 44 57 49 4E 54 35`** ("..DWINT5"). FFFF enables JMARK debugging; "DWINT5" is the code ID.
    Without it the OS 8051 stops ([ASIC] L546-547, L1532-1533).
  - User code goes from 0x0100 (63.75 KB).
- **DATA/IDATA**: 256 bytes, standard. **XDATA**: 32 KB at **0x8000-0xFFFF** only. MOVX below 0x8000 is forbidden.
- **SFR quirks**: CPU clock = 206.4384 MHz (11.0592 MHz × 56/3), 1T core. Extended SFRs and the MDU (64-bit MAC/divider) are
  reached through EXADR (0xFE) / EXDATA (0xFF).

### 5.2 Mandatory init ([ASIC] p.14 L474-508)
`CKON=0x00, T2CON=0x70, DPC=0x00 (required for C51), PAGESEL=0x01, D_PAGESEL=0x02, MUX_SEL=0x60, PORTDRV=0x01, RAMMODE=0x00`

### 5.3 DGUS variable window SFRs ([ASIC] p.16-17 L573-650)
| SFR | Addr | Function |
|---|---|---|
| RAMMODE | 0xF8 (bit-addressable) | .7 request, .6 APP_EN (start, cleared by hardware), .5 APP_RW (1 = read), .4 APP_ACK, .3-.0 byte enables for DATA3..0 |
| ADR_H/M/L | 0xF1/F2/F3 | 24-bit **cell** address (cell = 4 bytes = VP pair; 0x00:0800 = VP 0x1000/0x1001) |
| ADR_INC | 0xF4 | Auto-increment after each transfer |
| DATA3/2/1/0 | 0xFA/FB/FC/FD | DATA3:DATA2 = even VP (hi:lo), DATA1:DATA0 = odd VP |

Access sequence:
1. Set ADR and ADR_INC.
2. Set RAMMODE to 0xAF (read) or 0x8x (write with byte mask), then wait for APP_ACK.
3. Per cell: `APP_EN=1; while(APP_EN);`
4. Set RAMMODE to 0.

Disable interrupts around the whole sequence.

**Doc bug:** the asm write example uses `JNB APP_EN,$` after `SETB APP_EN` ([ASIC] L645-646). The read example's
`JB APP_EN,$` is the correct wait.

### 5.4 UART and other SFRs ([ASIC] p.27-30; [C51] p.8-35)
| UART | Control / data | Baud registers | Formula | IE bit |
|---|---|---|---|---|
| UART2 (DGUS port) | SCON0 0x98 / SBUF0 0x99, MUX_SEL.6 | ADCON 0xD8 = 0x80, SREL0H 0xBA / SREL0L 0xAA | 1024 − F ÷ (64 × baud) (SMOD = 0) → 0x03E4 @115200 | IEN0.4 (ES0) |
| UART3 | SCON1 0x9B (write-1-to-clear twice) / SBUF1 0x9C, MUX_SEL.5 | SREL1H 0xBB / SREL1L 0x9D | 1024 − F ÷ (32 × baud) | IEN2.0 |
| UART4 | SCON2T 0x96, SCON2R 0x97, SBUF2_TX 0x9E / RX 0x9F | BODE2_DIV_H 0xD9 / L 0xD7 | F ÷ (8 × baud) | IEN1.2 / .3 |
| UART5 | SCON3T 0xA7, SCON3R 0xAB, SBUF3_TX 0xAC / RX 0xAD | BODE3_DIV_H 0xAE / L 0xAF | F ÷ (8 × baud) | IEN1.4 / .5 |

Other registers:
- IO output enable: P0MDOUT 0xB7, P1MDOUT 0xBC, P2MDOUT 0xBD, P3MDOUT 0xBE.
- Watchdog: MUX_SEL.1 enable / .0 feed, 1 s timeout.
- Timer 2: T2CON 0xC8, reload 0xCB/0xCA (`48333` = 1 ms at /12).
- Interrupts: IEN0 0xA8, IEN1 0xB8, IEN2 0x9A, IEN3 0xD1, IP0 0xA9, IP1 0xB9.
- CAN: CAN_CR 0x8F, CAN_IR 0x91, CAN_ET 0xE8.
- The full header I wrote is `c51\T5L_SFR.H`.

### 5.5 Building T5L51.bin
- **Vendor flow** ([C51] p.13 L-"compiled output is in HEX format"):
  1. Keil C51 builds the project (DWIN's own startup.A51 and SFR header, not shipped here).
  2. `DownLoadFor8051` runs `hex2bin <hex> 64K` and produces `T5L51.bin`.
  3. Copy it to DWIN_SET, or let the same tool push it over UART.
- **Our flow** (`c51\build.bat`, verified):
  ```
  C51  main.c OPTIMIZE(8,SPEED) SMALL OBJECTEXTEND CODE
  A51  STARTUP_T5L.A51          ; T5L SFR init + clears IDATA/XDATA + CSEG AT 0F8H 'FFFF DWINT5'
  BL51 STARTUP_T5L.obj, main.obj TO t5l51 RAMSIZE(256) XDATA(0x8000)
  OH51 t5l51                    ; -> t5l51.hex
  python -I hex2bin.py t5l51.hex T5L51.bin [65536]   ; FF-filled
  ```
- **Result [V]:**
  - C51 V9.60.7 (**Eval**): 0 warnings, 0 errors. BL51: "RESTRICTED VERSION WITH 0800H BYTE CODE SIZE LIMIT; USED: 0195H (19 %)".
  - **The eval linker also places all relocatable code at 0x0800+**. The map shows `?PR?MAIN?MAIN` at 0800H, and the
    0x0100-0x07FF gap is filled with 0xFF.
  - Reset is `02 08 91` (LJMP to startup at 0x0891). 0x00F8 holds `FF FF 44 57 49 4E 54 35` **[V]**. The bin is 2464 bytes.
  - This works on the T5L: there is no address restriction, only the 2 KB size cap. Real projects need a licensed C51 or SDCC
    (SDCC is untested here).
- Unpadded vs 64 KB padding: both are plausible. Padding to 64 KB is the safe choice if the loader always copies 64 KB **[U]**.

### 5.6 Minimal skeleton (`c51\main.c`, compiles) [V compile / D runtime]
```c
static void vp_select(u16 vp){ ADR_H=0; ADR_M=(u8)(vp>>9); ADR_L=(u8)(vp>>1); ADR_INC=1; }
u16 vp_read(u16 vp){ u16 v; bit ea=EA; EA=0; vp_select(vp);
  RAMMODE=0xAF; while(!APP_ACK); APP_EN=1; while(APP_EN);
  v = (vp&1) ? ((u16)DATA1<<8)|DATA0 : ((u16)DATA3<<8)|DATA2;
  RAMMODE=0; EA=ea; return v; }
void vp_write(u16 vp,u16 val){ bit ea=EA; EA=0; vp_select(vp);
  RAMMODE=(vp&1)?0x83:0x8C; while(!APP_ACK);
  if(vp&1){DATA1=val>>8;DATA0=val;} else {DATA3=val>>8;DATA2=val;}
  APP_EN=1; while(APP_EN); RAMMODE=0; EA=ea; }
void dgus_set_page(u16 p){ vp_write(0x0085,p); vp_write(0x0084,0x5A01); }
```
`main()` does three things in a loop:
- increments VP 0x1000;
- copies VP 0x1002 × 2 to 0x1003;
- if a key-return control writes VP 0x1010, switches to that page, echoes the byte on UART2 (SCON0, 115200) and clears it.

The startup code (`STARTUP_T5L.A51`) does the §5.2 init **before** `?C_START`, because DPC must be 0 before any MOVX.

---

## 6. Discrepancies and doc errors found
- CFG magic is 5 bytes ("T5LC1"), not 6.
- The CRC bit is 0x05.7 ([COF] L281 says .6).
- CFG 0x30 is described both as "SYSCLK adjust" and as "16 bytes reserved".
- The 13.bin limit is 256 KB in [AG] but 32 KB in [COF].
- The [ASIC] asm write loop waits with the wrong polarity (`JNB APP_EN`).
- The [AG] T2/TF2 bit naming is ambiguous: the table says TF2 is in "TCON.6", which collides with TR1.
- "UART1/UART2" naming differs between the GUI-core and OS-core perspectives (§4.4).
- 0x83 maximum read length: 0x7D (table) vs 0x7C (text).
