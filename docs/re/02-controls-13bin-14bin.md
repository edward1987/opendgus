# 02: 13.bin (touch controls) and 14.bin (display controls), byte layout

Scope: the binary layout of `13触控配置文件.bin` and `14变量配置文件.bin` (users rename them to `13*.bin` and `14*.bin`) as the DGUS II editor V7.651 writes them for T5L, for every control type.

Sources:
- **DT/** = `vendor/decompiled/DwinTerminal/` (ILSpy output of `DwinTerminal.dll`). References are `file:line`.
- **DLL** = `vendor/tools/DGUS_V7651/DGUS_V7651/DWINDLL.dll`, a native x86 file. It was disassembled with capstone and never run. It holds `Func02`, `Func03` and `SetData`, which write part of 14.bin.
- **Guide** = `vendor/docs/txt/T5L_DGUSII-Application-Development-Guide-V2.921.txt`. Page numbers here are the PDF page, which the txt marks as `=== PAGE n ===`. The page number printed in the PDF is n-1.

Verification: a C# harness transplants the editor's `GetByte()`/`GetData()`/`Id` bodies verbatim. They are extracted mechanically from DT and compiled with `csc`. Its output matches the Python model `re2/dgus_controls.py` byte for byte, including a full 14.bin (see §7). Everything is derived from code, and no real panel was tested. Items marked **[unverified]** are inferences.

---

## 1. File-level structure

### 1.1 How the generator is reached

- Generate button: `TDocumentSpace.toolStripButton3_Click` → `BuildInputBinFile` then `BuildShowBinFile` (DT/BizDraw.Controls/TDocumentSpace.cs:3549-3551, also :5984-5986).
- Both receive `nJiami = Globel.Project_Custom`, which is hard-coded to **2** (DT/BizDraw/Globel.cs:54) and never assigned anywhere else. Two consequences:
  - The XOR "encryption" path (`nJiami == 0`, TDocumentSpace.cs:4255-4284) is **not** used.
  - The legacy fixed-slot 14.bin (`nJiami == 1`) is **not** used.
- File names are set at Globel.cs:60/62. Both files are written into `<project>/DWIN_SET/`.

### 1.2 13.bin (touch)

| Property | Value |
|---|---|
| Header | **None.** |
| Body | Variable-length records (16/32/48/64 bytes), concatenated (TDocumentSpace.cs:3642-3778). |
| Order | Pages in the order of the editor's page grid (`dgvPictureList` rows, normally ascending page ID). Within a page, `Items[Count-1] → Items[0]`. `GraphicsList.Add` inserts at index 0 (GraphicsList.cs:70), so this is **oldest-created first**. |
| Page indexing | None. Each record carries its own Pic_ID (bytes 0-1). The firmware has to scan the file. |
| Terminator | `FF FF` (2 bytes) (TDocumentSpace.cs:3766-3767). No padding. |
| Endianness | Big-endian for all multi-byte fields. |
| Max size | 256 KB (Guide p.23, p.87). The editor does not check this. |
| Flash location | Font/file slot 13. Each slot is 256 KB, so the file is at offset 13×0x40000 = **0x340000** of the 16 MB SPI flash (Guide p.16/p.23). The offset is computed **[unverified]**. |
| Overlaps | `ValidCheck` warns when non-keying touch areas intersect (TDocumentSpace.cs:3598-3639). |

Record length is implied by the TP_Code at bytes 14-15. The editor's re-import (`ReCreatInputFile`, TDocumentSpace.cs:4806-4870) splits records like this:

- `byte14 == 0xFF`, or `byte14 ∉ {0xFD, 0xFE}`: 16-byte "basic touch".
- `byte14 ∈ {0xFE, 0xFD}`: `byte15` is the control code. The length is the `TargetBytes` size of that class (table in §2.1).

The editor does not write a sentinel per page.

### 1.3 14.bin (display), indexed "DGUS_2" format written by V7.651

```
0x0000  16 B   header     14 44 47 55 53 5F 32 10  PP PP  00 00 00 00 00 00
                          ^0x14 "DGUS_2"     ^0x10 ^max page ID (BE16)
0x0010  4092 × 4 B  page index, slot i = page ID i:
                          [count:u8][byte offset of first record:u24 BE]
0x4000  records, 32 B each, page by page (ascending page ID), no gaps
...     32 × 0xFF   tail
```

- **Header.** Built by `Func02(maxPage, buf)` (DLL 0x100bf940; called at TDocumentSpace.cs:3888). The disassembly writes `14 44 47 55 53 5F 32 10`, then `max>>8`, `max&0xFF`, then zeros up to byte 15.
- **Index.** Built by `Func03(off, count, buf)` (DLL 0x100bfa30; loop at TDocumentSpace.cs:3891-3899). It writes `[count, off>>16, off>>8, off]` and returns `off + 32*count`. The first offset is 16384 = 0x4000 = 16 + 4092×4. Pages that do not exist get `count=0` and the current running offset, which is the same offset the next page will use.
  - Both DLL functions check a global (`[0x10252910] == 0x1204`, presumably set by `Init()`). If the check fails, `Func03` returns 0 and the build aborts with code 2.
- **Records.** For every page ID 0…maxPage that exists: `count` × 32-byte records (TDocumentSpace.cs:3911-4239). Within a page the order is `Items[Count-1] → Items[0]`, oldest first. Guide p.121 says: "For the same type of variables, the higher the storage location, the higher the display priority", which means later records are drawn on top.
- **Which controls are counted.** Only controls with `100 ≤ f13Type < 202` (TDocumentSpace.cs:3858, 3960). `RotaryKnob` (202) goes into `120.lib` instead.
- **Per-page limit.** More than 255 controls on one page is an error (TDocumentSpace.cs:3874).
- **Page ID limit.** Page IDs must be < 4092: `array2` is `byte[4092]`, and a larger ID raises an exception and the build fails.
- **Tail.** 32 × `0xFF` (TDocumentSpace.cs:4249-4254).
- **Size.** 16 KB of index plus records. With the 256 KB flash slot (Guide p.23) that leaves room for (256−16) KB / 32 = **7680 records** in total.
- **Flash location.** Slot 14, offset **0x380000** **[unverified]**.
- **Re-import.** The editor recognises this format by the header bytes `14 'DGUS_2' 10` (TDocumentSpace.cs:5606-5620).

**Legacy fixed-slot format.** This is what the Guide (p.121) still describes: every page gets 2/4/8 KB = 64/128/255 slots of 32 bytes, max 2 MB. The editor only writes it when `nJiami == 1` (TDocumentSpace.cs:3902-3944, 4240-4244). In that format, page 0 slot 0 holds `14 'DGUS_2' <VarCount/64> <maxPage BE16>`. Re-import still accepts it (TDocumentSpace.cs:5216-5223 reads `VarCount = byte7*4`).

**Side effect.** `BuildShowBinFile` also writes `DWIN_SET/22_Config.bin` (TDocumentSpace.cs:4287-4300). It contains:
- initial VP values (`GetInitData`), written at byte offset `VP*2` only when `VP*2 > 512`;
- data from Key_DO_Ret `ini1..3`.

22.bin is covered in another report.

---

## 2. 13.bin record layouts

### 2.1 Common 16-byte head, and the type table

From `InputBase.GetByte` (DT/BizDraw.ConfigInput/InputBase.cs:90-173):

| Off | Size | Field | Notes |
|---|---|---|---|
| 0x00 | 2 | Pic_ID | Page ID, BE. If an IVR/audio code is set: `byte0 = (PicID>>8 & 0x03) \| (IVRCode<<2)`, which leaves a 10-bit page ID (InputBase.cs:94-99; re-import :178-190). |
| 0x02 | 8 | TP_Area | Xs, Ys, Xe, Ye (BE16 each). Editor: `Xe = Left+Width`, `Ye = Top+Height` (exclusive edge; InputBase.cs:331-343). |
| 0x0A | 2 | Pic_Next | Target page after the press. "None" = `FF 00`. |
| 0x0C | 2 | Pic_On | Page holding the pressed-state image. "None" = `FF 00`. |
| 0x0E | 2 | TP_Code | `0xFExx` / `0xFDxx` = function control `xx`. Anything else is the key code of a basic touch. |

**"Keying" variant** (`Keying == true`, InputBase.cs:101-117). The area bytes become `FF (KeyCode-1) 00 00 FF KeyCode NN NN`, where `NN NN` is an editor-side index into `TFT/coords_13.json` that holds the real rectangle. This matches Guide p.66 (0xD4 touch simulation with `X = 0xFF:keycode`, `Y = 0x0001`).

**FE vs FD.** Each class has an `FEorFD` flag. It defaults to `Globel.AutoData` when the control is created (DT/BizDraw.Tools/ToolObject.cs:55-110).
- `0xFE`: upload of the changed value depends on CFG 0x05.4.
- `0xFD`: never auto-uploads (Guide p.86).

**Continuation chunks.** Every 16-byte chunk after the first starts with `0xFE` (offsets 0x10, 0x20, 0x30).

| TP_Code | f13Type | Class (DT/BizDraw.ConfigInput/) | Len | Guide |
|---|---|---|---|---|
| key code (e.g. 0x0031) | 6 | KeyCodeReturn, BaseTouch=true | 16 | p.86 |
| FE00/FD00 | 1 | VarInput (data input) | 64 | p.88 |
| FE01/FD01 | 2 | PopMenu | 48 | p.91 |
| FE02/FD02 | 3 | IncManager (incremental adjust) | 32 | p.94 |
| FE03/FD03 | 4 | DragManager (drag / slider adjust) | 32 | p.96 |
| FE04/FD04 | 5 | RtcInput (RTC set) | 48 | not in V2.9 guide |
| FE05/FD05 | 7 | KeyCodeReturn (return key code) | 32 | p.98 |
| FE06/FD06 | 8 | TextInput (ASCII) | 64 | p.102 |
| FE06/FD06 + byte63=0x02 | 9 | GBKInput | 64 | p.105 |
| FE07/FD07 | 10 | ParamCofig (raw data pack) | 32 | not in guide |
| FE08 (always FE) | 11 | Key_DO_Ret (synchro data return) | 48 | p.108 |
| FE09/FD09 | 12 | Rotateadjust | 48 | p.111 |
| FE0A/FD0A | 13 | SwipeAdjust (sliding adjust) | 32 | p.113 |
| FE0B/FD0B | 14 | SwipePage (page sliding) | 32 | p.114 |
| FE0C/FD0C | 15 | ICONDragManager (slide icon select) | 32 | p.116 |
| FE0D/FD0D (default FD) | 16 | BitButton | 32 | p.118 |

The f13Type → class map comes from ToolObject.cs:55-110. The TP_Code assignments are at `Tp_Code = 650xx/647xx` in each class (e.g. VarInput.cs:76/80, BitButton.cs:12/83/87, Key_DO_Ret.cs:263). `TouchReturn.cs` (16+4 bytes) is never instantiated.

All tables below give offsets from 0x10. Bytes not listed are 0.

### 2.2 Basic touch (16 B): KeyCodeReturn.GetByte, BaseTouch (KeyCodeReturn.cs:232-240)
The common head only, with `TP_Code = Key_Code` (for example 0x0030-0x0039, 0x00F0-0x00F2 for keyboard keys, or 0xFF00 = invalid).

### 2.3 Return key code, FE05 (32 B): KeyCodeReturn.cs:241-261
| Off | Sz | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | VP_Mode: 00 = word, 01 = VP_H, 02 = VP_L, 0x10-0x1F = write bit 0 of the key code to VP.bit(n-0x10) |
| 0x14 | 2 | Key_Code |
| 0x16 | 1 | Hold_Time (0.1 s units) |
| 0x17 | 9 | 0 |

### 2.4 Data input, FE00 (64 B): VarInput.cs:492-566
| Off | Sz | Field |
|---|---|---|
| 0x10 | 1 | 0xFE |
| 0x11 | 2 | VP |
| 0x13 | 1 | V_Type: 0 = int16, 1 = int32, 2 = VP_H, 3 = VP_L, 4 = int64, 5 = float |
| 0x14 | 1 | N_Int |
| 0x15 | 1 | N_Dot |
| 0x16 | 4 | display (x, y): upper-right of the input cursor |
| 0x1A | 2 | Color |
| 0x1C | 1 | Lib_ID |
| 0x1D | 1 | Font_Hor |
| 0x1E | 1 | Cursor_Color |
| 0x1F | 1 | Hide_En (0 = show `*`) |
| 0x20 | 1 | 0xFE |
| 0x21 | 1 | KB_Source: 0 = current page, 1 = other page; the editor writes 0x0F when its value is > 1 (assembly keyboard) |
| 0x22 | 2 | PIC_KB |
| 0x24 | 8 | AREA_KB Xs, Ys, Xe, Ye; Xe/Ye clamped to W-1/H-1 |
| 0x2C | 4 | KB position x, y (clamped) |
| 0x30 | 1 | 0xFE |
| 0x31 | 1 | Limits_En (0xFF = on) |
| 0x32 | 4 | V_min, int32 BE |
| 0x36 | 4 | V_max, int32 BE |
| 0x3A | 1 | Return_Set (0x5A = load Return_Data into Return_VP during input) |
| 0x3B | 2 | Return_VP |
| 0x3D | 2 | Return_Data (low 16 bits) |
| 0x3F | 1 | Layer_Gama = 255×percent/100 |

### 2.5 Popup menu, FE01 (48 B): PopMenu.cs:355-411
| Off | Field |
|---|---|
| 0x10 | 0xFE |
| 0x11 | VP |
| 0x13 | VP_Mode (as in §2.3) |
| 0x14 | Pic_Menu |
| 0x16 | Area_Menu Xs, Ys, Xe, Ye (end clamped) |
| 0x1E | Menu_Position_X (2) |
| 0x20 | 0xFE |
| 0x21 | Menu_Position_Y (2) |
| 0x23 | Translucent = 255×%/100 |
| 0x24-0x2F | 0 |

### 2.6 Incremental adjust, FE02 (32 B): IncManager.cs:235-256
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP |
| 0x13 | VP_Mode (00 / 01 / 02 / 0x1n bit) |
| 0x14 | Adj_Mode (0 = −, else +) |
| 0x15 | Return_Mode (0 = clamp, else wrap) |
| 0x16 | Adj_Step (2) |
| 0x18 | V_Min (2) |
| 0x1A | V_Max (2) |
| 0x1C | Key_Mode (0 = repeat while held, 1 = once) |
| 0x1D | **Key_Delay** (not in guide) |
| 0x1E-0x1F | 0 |

### 2.7 Drag adjust, FE03 (32 B): DragManager.cs:231-307
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP |
| 0x13 | Adj_Mode: high nibble = 0 word / 1 VP_H / 2 VP_L; low nibble = 0 horizontal / 1 vertical |
| 0x14 | Area_Adj Xs, Ys, Xe, Ye (Xe/Ye clamped) |
| 0x1C | V_Begin (2) |
| 0x1E | V_End (2) |

The editor also **overwrites TP_Area (0x02-0x09)** with Area_Adj grown by 32 px along the drag axis, clamped to the screen (DragManager.cs:256-297).

### 2.8 RTC input, FE04 (48 B): RtcInput.cs:350-406
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11-0x13 | 0 |
| 0x14 | InShow (x, y) |
| 0x18 | Color |
| 0x1A | Lib_ID |
| 0x1B | Font_Hor |
| 0x1C | Cursor_Color |
| 0x1D | KB_Source |
| 0x1E | PIC_KB |
| 0x20 | FE |
| 0x21 | Area_KB (8, end clamped) |
| 0x29 | KB position (4, clamped) |
| 0x2D-0x2F | 0 |

Not documented in Guide V2.9 **[layout from code only]**.

### 2.9 ASCII text input, FE06 (64 B): TextInput.cs:464-539
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP |
| 0x13 | VP_Len_Max (words) |
| 0x14 | Scan_Mode |
| 0x15 | Lib_ID |
| 0x16 | Font_Hor |
| 0x17 | Font_Ver |
| 0x18 | Cursor_Color |
| 0x19 | Color (2) |
| 0x1B | Scan_Area_Start (x, y) |
| 0x1F | Scan_Return_Mode (0x55 = status at VP-1) |
| 0x20 | FE |
| 0x21 | Scan_Area_End (x, y) clamped |
| 0x25 | KB_Source |
| 0x26 | PIC_KB |
| 0x28 | Area_KB (8, end clamped) |
| 0x30 | FE |
| 0x31 | KB position (4, clamped) |
| 0x35 | Display_EN |
| 0x36 | Layer_Gama = 255×%/100 |
| 0x37-0x3F | 0 |

### 2.10 GBK input, FE06 (64 B): GBKInput.cs:529-581
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP |
| 0x13 | VP_Len_Max |
| 0x14 | Scan_Mode |
| 0x15 | Lib_GBK1 |
| 0x16 | Lib_GBK2 |
| 0x17 | Font_Scale1 |
| 0x18 | Font_Scale2 |
| 0x19 | Cursor_Color |
| 0x1A | Color0 |
| 0x1C | Color1 |
| 0x1E | PY_Disp_Mode |
| 0x1F | Scan_Return_Mode |
| 0x20 | FE |
| 0x21 | Scan0 start (4) |
| 0x25 | Scan0 end (4) |
| 0x29 | Scan1 start (4) |
| 0x2D | Scan_Dis |
| 0x2E | 0 |
| 0x2F | KB_Source |
| 0x30 | FE |
| 0x31 | PIC_KB |
| 0x33 | Area_KB (8) |
| 0x3B | KB position (4) |
| 0x3F | **0x02** = input-method marker that tells it apart from ASCII input |

The editor never writes 0x03 (phonetic input). No clamping is applied here.

### 2.11 Parameter config, FE07 (32 B): ParamCofig.cs:220-237
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP_Mode |
| 0x12.. | `Data_pack`: a user hex string, ≤14 bytes |
| rest | 0 |

The firmware semantics are unknown. FE07 is not in the guide's list **[unverified]**.

### 2.12 Synchro data return, FE08 (48 B): Key_DO_Ret.cs:272-306
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | TP_ON mode |
| 0x12 | VP1S |
| 0x14 | VP1T |
| 0x16 | 0 |
| 0x17 | LEN1 |
| 0x18 | FE |
| 0x19 | TP_ON_C mode |
| 0x1A | VP2S |
| 0x1C | VP2T |
| 0x1E | 0 |
| 0x1F | LEN2 |
| 0x20 | FE |
| 0x21 | TP_OFF mode |
| 0x22 | VP3S |
| 0x24 | VP3T |
| 0x26 | 0 |
| 0x27 | LEN3 |
| 0x28-0x2F | 0 |

TP_Code is forced to FE08. `ini1..3` (hex strings) are copied into 22_Config.bin at `VPnS*2` (TDocumentSpace.cs:3672-3708, 4288-4305).

### 2.13 Rotation adjust, FE09 (48 B): Rotateadjust.cs:247-283
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP |
| 0x13 | Data_Format (0 / 1 / 2) |
| 0x14 | center (x, y) |
| 0x18 | R0 |
| 0x1A | R1 |
| 0x1C | A0 (0.5° units) |
| 0x1E | V_Begin |
| 0x20 | FE |
| 0x21 | A1 |
| 0x23 | V_End |
| 0x25-0x2F | 0 |

### 2.14 Sliding adjust, FE0A (32 B): SwipeAdjust.cs:202-215
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP (data is returned at VP+1) |
| 0x13 | Adj_Mode (0 = H, 1 = V) |
| 0x14 | Step_Dis |
| 0x15-0x1F | 0 |

### 2.15 Page sliding, FE0B (32 B): SwipePage.cs:240-271
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | Pic_Pre |
| 0x13 | Pic_Next |
| 0x15 | Pic_Area: mode 0 = (Ys, Ye) taken from the touch area; mode 1 = (Xs, Xe). End clamped. |
| 0x19 | Push_Speed_Set |
| 0x1A | Push_Dis_Set (2) |
| 0x1C | `(Adj_Mode<<7) + Date_return`: bit 7 = vertical sliding (not in guide); low bits = upload page ID |
| 0x1D | End_animation |
| 0x1E-0x1F | 0 (from the fresh array) |

### 2.16 Slide icon select, FE0C (32 B): ICONDragManager.cs:224-239
- Pic_Next and Pic_On are forced to `FFFF`.

| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP |
| 0x13 | Adj_Mode |
| 0x14 | TP_Page_ID_ICON (2) |
| 0x16 | Speed_Slide (guide: reserved) |
| 0x17-0x1F | 0 |

### 2.17 Bit button, FE0D (32 B): BitButton.cs:163-172
| Off | Field |
|---|---|
| 0x10 | FE |
| 0x11 | VP |
| 0x13 | Bit_Pos (0-15) |
| 0x14 | Adj_Mode: 0 = clear, 1 = set, 2 = toggle, 3 = momentary |
| 0x15-0x1F | 0 |

---

## 3. 14.bin record layouts (32 bytes each)

### 3.1 Common header and type table

From `ShowBase.GetData` (DT/BizDraw.ConfigShow/ShowBase.cs:122-128) and Guide p.121:

| Off | Size | Field |
|---|---|---|
| 0x00 | 1 | 0x5A. 0x5F for data variable, text and icon controls imported with a 0x5F lead byte (`IsShowOnPopMenu`, ShowBase.cs:112-117; DataTextShow.cs:239-249). Purpose undocumented, probably a pop-up/keyboard-layer variable **[unverified]**. |
| 0x01 | 1 | Type code |
| 0x02 | 2 | SP (0xFFFF = none) |
| 0x04 | 2 | Len_Dsc = the number of **words** of the description (starting at offset 0x06) that are copied to SP |
| 0x06 | 2 | VP (usually; see the per-type tables). A high byte of 0xFF disables the instruction (Guide p.121). |
| 0x08.. | | Description. SP word *k* = record bytes `6+2k .. 7+2k`. |

The editor writes no checksum and no per-record padding. Any byte a class does not set stays at its previous value in the per-object `Data[32]`, which starts as zeros. In practice that means 0. One exception: `DataTextShow` does not clear old unit characters when the unit string gets shorter during a session (editor bug; the Python model zero-fills).

| Type | f13Type | Class (DT/BizDraw.ConfigShow/) | Len | Guide | GetData |
|---|---|---|---|---|---|
| 0x00 | 100 | IconShow (variable icon) | 0x0A | p.125 | IconShow.cs:220-261 |
| 0x00 (+[0x1A]=5A, [0x1F]=01) | 200 | MultiLanguage | 0x0A | none | MultiLanguage.cs:227-262 |
| 0x01 | 101 | AnimateShow | 0x0D | p.128 | AnimateShow.cs:202-247 |
| 0x02 | 102 | SliderShow | 0x0C | p.132 | SliderShow.cs:206-238 |
| 0x03 | 103 | ArtTextShow | 0x09 | p.134 | ArtTextShow.cs:286-317 |
| 0x04 | 104 | ImageAnimateShow | 0x05 | p.136 | ImageAnimateShow.cs:84-99 |
| 0x05 | 105 | ICONRotate | 0x0C | p.138 | ICONRotate.cs:233-262 |
| 0x06 | 114 | bitIcon | 0x0D (guide 0x0C) | p.141 | bitIcon.cs:186-226 |
| 0x07 | 123 | IconPageTrans | 0x09 | p.144 | IconPageTrans.cs:216-237 |
| 0x08 | 124 | VariableJpeg (icon overlay / JPEG) | 0x07 (guide 0x09) | p.146 | VariableJpeg.cs:233-252 |
| 0x09 | 125 | BatchIconShow | 0x06 | p.150 | BatchIconShow.cs:229-258 |
| 0x10 | 106 | DataTextShow (data variable) | 0x0D | p.152 | DataTextShow.cs:358-403 |
| 0x11 | 107 | TextShow | 0x0D | p.159 | TextShow.cs:282-336 |
| 0x12, VP=0000 | 108 | RtcTextShow | 0x0D | p.163 | RtcTextShow.cs:226-259 |
| 0x12, VP=0001 | 109 | Clock_Dis (analog clock) | 0x0D | p.165 | Clock_Dis.cs:239-270 |
| 0x13 | 115 | TimeDisplay (HEX data) | 0x0D | p.167 | TimeDisplay.cs:186-221 |
| 0x14 | 116 | ScrTextShow (text scroll) | 0x0C | p.169 | ScrTextShow.cs:273-321 |
| 0x15 | 119 | Data_Window | 0x0C (guide 0x0D) | p.172 | Data_Window.cs:282-321 + DLL SetData(21) |
| 0x16 | 122 | TextShowII (DGUS II text) | 0x0D | p.175 | TextShowII.cs:295-351 |
| 0x17 | 126 | Roller_character | 0x0D | p.180 | Roller_character.cs:396-448 |
| 0x18 | 127 | GTFShow | 0x0B | p.184 | GTFShow.cs:140-176 |
| 0x20 | 110 | ChartShow (real-time curve) | 0x0B | p.189 | ChartShow.cs:186-236 |
| 0x21 | 112 | BaseGraphs (basic graphics) | 0x08 | p.198 | BaseGraphs.cs:144-174 |
| 0x22 | none | ListingShow (table): no tool creates it | 0x0C | none | ListingShow.cs:307-352 |
| 0x23 | 130 | DW_ProcessBar | 0x0D | p.220 | DW_ProcessBar.cs:253-288 |
| 0x23 | 113 | BaseApply (legacy stub, Len 1) | 0x01 | none | BaseApply.cs:104-112 |
| 0x24 | 118 | ZoneScrolling | 0x07 | p.222 | ZoneScrolling.cs:159-179 + DLL SetData(36) |
| 0x25 | 117 | Two_Dimension (QR code) | 0x08 | p.223 | Two_Dimension.cs:170-189 |
| 0x26 | 120 | ZoneLightSetting (area brightness) | 0x05 | p.226 | ZoneLightSetting.cs:159-169 + DLL SetData(38) |
| 0x30 | 121 | AuxiliaryDisplay (data transmit) | 0x0D | p.227 | AuxiliaryDisplay.cs:204-243 |
| 0x31 | 129 | VideoShow | 0x08 | p.228 | VideoShow.cs:72-101 |
| 0x31 | 128 | CameraShow | 0x0A | none | CameraShow.cs:96-132 |

The f13Type → class map is at ToolObject.cs:111-230. The read-back map (type code → class) is at TDocumentSpace.cs:4963-5212. Partial-image copy, icon display, lines and the like are not separate types: they are sub-commands of type 0x21 that live in VP RAM (Guide p.199-200). The editor has no "icon overlay" control other than 0x08.

Recurring encodings:
- **Layer/overlay byte.** The editor writes `BackMode==0 ? 0 : BackMode+1`, so the UI choices *cover / overlay 1 / overlay 2* become **0x00 / 0x02 / 0x03**. The guide lists 0x00 / 0x01 / 0x02 (see §5).
- **Gamma bytes.** `255×percent/100`.
- **Filter_Set.** Raw value, 0x00-0x3F.
- **Mode.** 0 = transparent, 1 = show background.
- **Coordinates.** Several classes clamp a coordinate ≥ W/H to W-1/H-1 (`Globel.Width`/`Height`, the screen size). The clamp is noted per field below. BaseGraphs clamps end coordinates to **W/H**, not W-1.

All offsets below are **record** offsets. SP word = (offset-6)/2.

### 3.2 Icon family

**0x00 Variable icon** (Len 0x0A)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X |
| 0A | Y |
| 0C | V_Min |
| 0E | V_Max (forced ≥ V_Min) |
| 10 | Icon_Min |
| 12 | Icon_Max |
| 14 | Icon_Lib |
| 15 | Mode |
| 16 | Layer_Mode |
| 17 | ICON_Gamma |
| 18 | PIC_Gamma |
| 19 | Filter_Set |
| 1A | 0x5A if "group" is enabled, else 0. Undocumented. The group ID/spacing goes to 22.bin bytes VP×2+1..+3 (TDocumentSpace.cs:4176-4181). |

**MultiLanguage** uses the same layout, with `[1A]=5A` and `[1F]=01`. Its 22.bin entry is `00 00 00 01`.

**0x01 Animation icon** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X (clamped) |
| 0A | Y (clamped) |
| 0C | Reset_ICON_En |
| 0E | V_Stop |
| 10 | V_Start |
| 12 | ICON_Stop |
| 14 | ICON_Start |
| 16 | ICON_End |
| 18 | ICON_Lib |
| 19 | Mode |
| 1A | Layer_Mode |
| 1B | ICON_Gamma |
| 1C | PIC_Gamma |
| 1D | Time (DGUS cycles) |
| 1E | Display mode (0 = loop, 1 = once) |
| 1F | Filter_Set |

**0x02 Slider display** (Len 0x0C)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | V_Begin |
| 0A | V_End |
| 0C | x_Begin |
| 0E | x_End |
| 10 | ICON_ID |
| 12 | Y |
| 14 | x_adj |
| 15 | Mode (0 = H, 1 = V) |
| 16 | ICON_Lib |
| 17 | ICON_Mode |
| 18 | VP_Data_Mode |
| 19 | Layer_Mode |
| 1A | ICON_Gamma |
| 1B | PIC_Gamma |
| 1C | Filter_Set |

From the rectangle: horizontal uses x_Begin = Left, x_End = Right, Y = Top. Vertical swaps the axes.

**0x03 Artistic variable** (Len 0x09)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X |
| 0A | Y |
| 0C | ICON0 |
| 0E | ICON_Lib |
| 0F | ICON_Mode |
| 10 | Integer_Digits |
| 11 | Decimal_Digits |
| 12 | VP_Mode (0-8, same set as the data variable) |
| 13 | Alignment (0 = L, 1 = R); **bit 7 = show leading zeros** (`isShow0`, not in guide) |
| 14 | Layer_Mode |
| 15 | ICON_Gamma |
| 16 | PIC_Gamma |
| 17 | Filter_Set |

**0x04 Image animation** (Len 0x05)
| Off | Field |
|---|---|
| 06 | 0x0000 |
| 08 | Pic_Begin |
| 0A | Pic_End |
| 0C | Frame_Time (8 ms) |
| 0D | ICL_LIB_ID |
| 0E | Pic_End_Exp |

**0x05 Icon rotation** (Len 0x0C)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | ICON_ID |
| 0A | ICON_Xc |
| 0C | ICON_Yc |
| 0E | Xc |
| 10 | Yc |
| 12 | V_Begin |
| 14 | V_End |
| 16 | AL_Begin |
| 18 | AL_End (0.5°) |
| 1A | VP_Mode |
| 1B | Lib_ID |
| 1C | Mode |
| 1D | Filter_Set |

**0x06 Bit icon** (Len **0x0D** in code)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | VP_AUX (2 words, system-owned) |
| 0A | Act_Bit_Set |
| 0C | Display_Mode (0-7) |
| 0D | Move_Mode |
| 0E | Icon_Mode |
| 0F | Icon_Lib |
| 10 | ICON0S |
| 12 | ICON0E |
| 14 | ICON1S |
| 16 | ICON1E |
| 18 | X (clamped) |
| 1A | Y (clamped) |
| 1C | DIS_MOV |
| 1E | Filter_Set (not in guide) |

**0x07 Icon page trans (JPEG icon pan)** (Len 0x09)
| Off | Field |
|---|---|
| 06 | VP (4 words) |
| 08 | ICON_Lib |
| 09 | Disp_Mode |
| 0A | Filter_Set |
| 0B | Move_Mode |
| 0C | ICON_ID |
| 0E | Xs |
| 10 | Ys |
| 12 | Xe |
| 14 | Ye |

**0x08 Icon overlay / variable JPEG** (Len **0x07** in code, 0x09 in guide)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X |
| 0A | Y |
| 0C | Wide_X |
| 0E | Wide_Y |
| 10 | Dim_Set (written raw, *not* scaled) |
| 11 | Disp_Mode |
| 12 | Filter_Set |
| 13 | `(JpgFormat<<7) \| VPAddr`: guide calls this "*VP_Page"; bit 7 is undocumented |

**0x09 Batch variable icon** (Len 0x06)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | VP1 |
| 0A | VP2 |
| 0C | Data_Num |
| 0E | Icon_Source |
| 0F | Icon_Lib |
| 10 | Icon_ID |
| 18-1F | Editor writes the control rectangle Xs, Ys, Xe, Ye into the guide's "reserved" area. Probably round-trip only, ignored by firmware **[unverified]**. |

### 3.3 Text and number family

**0x10 Data variable** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X (clamped) |
| 0A | Y (clamped) |
| 0C | Color (RGB565) |
| 0E | Lib_ID |
| 0F | Font size (x-dots) |
| 10 | `bit7` = "character spacing auto adjust" checkbox (`Modify`), `bit6` = "show invalid (leading) zeros", `bits 0-5` = Alignment (0 L / 1 R / 2 C) |
| 11 | Integer digits |
| 12 | Decimal digits |
| 13 | Var type: 0 = i16, 1 = i32, 2 = VP_H, 3 = VP_L, 4 = i64, 5 = u16, 6 = u32, 7 = f32, 8 = f64 (Guide) |
| 14 | Len_unit (user value; not computed from the string) |
| 15-1F | Unit string, ASCII, ≤ 11 bytes |

**0x11 Text display** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X |
| 0A | Y |
| 0C | Color |
| 0E | Xs |
| 10 | Ys |
| 12 | Xe |
| 14 | Ye (box; all four clamped to W-1/H-1; box = control rectangle with Right/Bottom exclusive) |
| 16 | Text_Length (bytes) |
| 18 | Font0_ID |
| 19 | Font1_ID |
| 1A | Font_X_Dots |
| 1B | Font_Y_Dots |
| 1C | `Encode_Mode \| HAlign<<5 \| VAlign<<4 \| (IsAdjust?0x80)` |
| 1D | HOR_Dis |
| 1E | VER_Dis |
| 1F | 0 |

Encode_Mode values: 0 = 8-bit, 1 = GB2312, 2 = GBK, 3 = BIG5, 4 = SJIS, 5 = UNICODE.

**0x12 RTC (text)** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | **0x0000** (selects text mode) |
| 08 | X |
| 0A | Y |
| 0C | Color |
| 0E | `bit7` = spacing flag, low bits = Lib_ID (the guide says Lib_ID only) |
| 0F | Font width |
| 10-1F | Format string (ASCII, ≤ 16) |

The RTC itself is read from system VP 0x009C.

**0x12 RTC (analog clock)** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | **0x0001** |
| 08 | Xc |
| 0A | Yc |
| 0C | Icon_Hour |
| 0E | Hour center x, y |
| 12 | Icon_Minute |
| 14 | Minute center x, y |
| 18 | Icon_Second |
| 1A | Second center x, y |
| 1E | Icon_Lib |
| 1F | 0 |

**0x13 HEX data** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X |
| 0A | Y |
| 0C | Color |
| 0E | `(Byte_Num & 0x0F) \| BCD<<7` |
| 0F | Lib_ID |
| 10 | Font_x |
| 11-1F | String_Code (≤ 15 bytes, parsed from a hex string) |

**0x14 Text scroll** (Len 0x0C)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | Rolling_Mode |
| 09 | Rolling_Dis |
| 0A | Adjust_Mode |
| 0B | run control |
| 0C | Color |
| 0E | Xs |
| 10 | Ys |
| 12 | Xe |
| 14 | Ye (clamped) |
| 16 | Font0_ID |
| 17 | Font1_ID |
| 18 | Font_X_Dots |
| 19 | Font_Y_Dots |
| 1A | Encode_Mode |
| 1B | Text_Dis |
| 1C | Speed_Set (0 = fastest … 0x0F) |

The text is stored at **VP+3**: the initial text goes into 22.bin at `VP*2+6` (TDocumentSpace.cs:3984).

**0x15 Data window** (Len **0x0C** in code, 0x0D in guide)

The bytes are produced by the native DLL `SetData(21, …)`, disassembled at 0x100bf445-0x100bf5e1.

| Off | Field |
|---|---|
| 06 | VP |
| 08 | V_Min |
| 0A | V_Max |
| 0C | NUM_I |
| 0D | NUM_F |
| 0E | NUM_Digit |
| 0F | Display_Mode |
| 10 | X |
| 12 | Y (center of the selected value) |
| 14 | Step_Adj |
| 16 | F0_X |
| 17 | F0_Y (the DLL forces it to ≥ 2×F0_X) |
| 18 | F0_Color |
| 1A | F1_X |
| 1B | F1_Y (also forced ≥ 2×F1_X) |
| 1C | F1_Color |
| 1E | Font_Lib (written by C#, Data_Window.cs:320) |
| 1F | 0 |

**0x16 DGUS II text** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X |
| 0A | Y |
| 0C | Color |
| 0E | 0x0000 |
| 10 | Xs |
| 12 | Ys |
| 14 | Xe |
| 16 | Ye (clamped) |
| 18 | Text_Length |
| 1A | Font_ID (2 bytes) |
| 1C | `DisAdjust<<7 \| min(127, FontHeight*16/100)` |
| 1D | HOR_Dis |
| 1E | VER_Dis |
| 1F | Align (0 L / 1 R / 2 C) |

**0x17 Roll character** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | `dataType<<4 \| (dataLine-1)/2` |
| 09 | dataType==0xF ? charLen : (NUM_I<<4 \| NUM_F) |
| 0A | dataType==0xF ? VP_String : dataGap |
| 0C | V_Min |
| 0E | V_Max |
| 10 | `Display_0<<7 \| (Font_Set0&7)<<4 \| AddMode<<3 \| BK<<2 \| Align` |
| 11 | `Speed&0x3F \| changeSpeed<<6` |
| 12 | Font_ID |
| 14 | X anchor (from the alignment: L = Xs, C = center, R = Xe) |
| 16 | Y (box middle) |
| 18-1B | Line_Gap0..3 |
| 1C | DIM (unselected brightness) |
| 1D | Line_Height0 |
| 1E | Font1<<4 \| Font2 |
| 1F | Font3<<4 \| Font4 |

**0x18 GTF icon font** (Len 0x0B; the guide's offset table is garbled)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | GTF_ID |
| 0A | Font_ID |
| 0C | X, Y: if align==0 then (Xs, Ys), else (Xe, Ys) |
| 10 | Xs |
| 12 | Ys |
| 14 | Xe |
| 16 | Ye |
| 18 | HOR_Dis |
| 19 | VER_Dis |
| 1A | `back<<7 \| reload<<6 \| icoRecover<<5 \| align` |

### 3.4 Graphics, special and media

**0x20 Real-time curve** (Len 0x0B)
| Off | Field |
|---|---|
| 06 | Move_Dir (0 = newest on the right) |
| 07 | `bit7` = Display_Mode, `bit6` = color comes from VP (both undocumented; the guide says 0) |
| 08 | Xs |
| 0A | Ys |
| 0C | Xe |
| 0E | Ye (clamped) |
| 10 | Y_Central |
| 12 | VD_Central |
| 14 | Color, or the color VP when bit 6 is set |
| 16 | MUL_Y (1/256) |
| 18 | CHANNEL |
| 19 | Dis_HOR |
| 1A | Pixel_Scale |

There is **no VP field**: the data comes from curve channel buffers 0x1000-0x4FFF.

**0x21 Basic graphics** (Len 0x08)
| Off | Field |
|---|---|
| 06 | VP (the drawing command list lives in RAM; command codes on Guide p.199-200) |
| 08 | Xs |
| 0A | Ys |
| 0C | Xe |
| 0E | Ye (end clamped to W/H) |
| 10 | Dashed_Line_En (0x5A) |
| 11-14 | Dash_Set[4] |
| 15 | 0 (guide: Pixel_Scale; the editor never sets it) |

**0x22 Table** (ListingShow; dead code, no tool creates it)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | X_Num |
| 09 | Y_Num |
| 0A | X_Start |
| 0B | Y_Start |
| 0C | Unit_Num |
| 0D | flags/encode |
| 0E | text box (8) |
| 16 | line color |
| 18 | text color |
| 1A | Font0 |
| 1B | Font1 |
| 1C | X dots |
| 1D | Y dots |
| 1E-1F | Tab_X_Adj_Mod (twice) |

**0x23 Process bar** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | Xs |
| 0A | Ys |
| 0C | Xe |
| 0E | Ye |
| 10 | Border color |
| 12 | Foreground color |
| 14 | Background color |
| 16 | V_Max |
| 18 | V_Min |
| 1A | `ShowRate<<7 \| (!FillBack)<<1 \| (!ShowBorder)` |
| 1B | Direction |
| 1C | Data type |
| 1D | 0 |
| 1E | VP_RT (percentage return pointer) |

**0x24 Zone scrolling** (Len 0x07, built by DLL `SetData(36)`)
| Off | Field |
|---|---|
| 06 | VP (system-owned) |
| 08 | Xs |
| 0A | Ys |
| 0C | Xe |
| 0E | Ye (clamped) |
| 10 | Dis_Move |
| 12 | Mode_Move (0 = left, 1 = right, 2 = up, 3 = down) |

**0x25 QR code** (Len 0x08)
| Off | Field |
|---|---|
| 06 | VP (text ending in 0x0000/0xFFFF) |
| 08 | X |
| 0A | Y |
| 0C | 0x00 |
| 0D | Unit_Pixels (1-7) |
| 0E | Fix_Mode (1 = 73×73) |
| 0F | bit 7 = use Color0/Color1 |
| 10 | Color0 (background) |
| 12 | Color1 (code) |

**0x26 Area brightness** (Len 0x05, built by DLL `SetData(38)`)
| Off | Field |
|---|---|
| 06 | VP (brightness 0-100 is *read from VP*) |
| 08 | Xs |
| 0A | Ys |
| 0C | Xe |
| 0E | Ye |
| 10 | 0 |
| 11 | 0 |

The editor's `LightNess` value is passed to the DLL but discarded.

**0x30 Data transmit** (Len 0x0D)
| Off | Field |
|---|---|
| 06 | VP |
| 08 | AUTO_COM_En (0xFF = upload) |
| 09 | 0 |
| 0A | X1 |
| 0C | Y1 |
| 0E | X2 |
| 10 | Y2 |
| 12-1F | Predefined data (hex string, ≤ 14 bytes) |

The guide says 0x0A-0x1F hold 22 bytes of predefined data. The editor puts the control rectangle at 0x0A-0x11 instead (see §5).

**0x31 Video** (Len 0x08)
| Off | Field |
|---|---|
| 06 | VP (6 words) |
| 08 | X |
| 0A | Y |
| 0C | Width |
| 0E | Height |
| 10 | FPS |
| 11 | Type (0 = ICL+WAE) |
| 12 | ICL file ID |
| 14 | WAE file ID |
| 1C | end_x |
| 1E | end_y (editor round-trip, in the guide's reserved area) |

**0x31 Camera** (Len 0x0A; not in the guide)
| Off | Field |
|---|---|
| 06 | VP_Image (forced into 0x2000-0xC000) |
| 08 | X |
| 0A | Y |
| 0C | W |
| 0E | H |
| 10-13 | FF FF FF FF |
| 14 | 0x5A |
| 15 | Camera_ID |
| 16 | `Light<<7 \| Mirror<<6` |
| 17 | Light_Set, or 0 |
| 18 | Resolution |
| 19 | DisplayScale |

---

## 4. VP and SP

**VP (variable pointer).**
- A word address in the 64 K-word (128 KB) variable RAM. 0x0000-0x0FFF are system variables; 0x1000-0xFFFF are for the user (Guide p.17). The byte offset in 22.bin is VP×2.
- In 13.bin, VP is where touch controls write. In 14.bin, it is where display controls read.
- Some controls occupy more than one word:
  - animation icon and data window: 2 words;
  - bit icon: VP plus a 2-word VP_AUX;
  - icon page trans: 4 words;
  - text scroll: data at VP+3;
  - video: 6 words;
  - text input: VP-1 holds the status/length when Scan_Return_Mode = 0x55;
  - sliding adjust: data at VP+1.
- Controls that need no VP store 0x0000 there, or a sub-type selector (RTC: 0000 = text, 0001 = clock).
- A VP high byte of 0xFF disables a display instruction (Guide p.121).
- **How the editor sets VP.** A per-control hex string, `VarStrPoint`, parsed into `Var_Point`. When the page's "AutoVP" option is on, new **touch** controls are pre-filled with `Document.CurrVarAddress` (ToolObject.cs:45-46, 237-240; PageSet.cs:1004).

**SP (description pointer).**
- At load time, when SP ≠ 0xFFFF, the firmware copies the description: **Len_Dsc words starting at record offset 0x06**, beginning with the VP word. They go to RAM at SP (Guide p.18, p.121).
- From then on the control is driven from RAM. The host can change any attribute by writing `SP + k`, where *k* is the word index in the guide's "SP offset" column. Examples: SP+1 = X,Y; SP+3 = color for the data variable; writing `0xFF00` to SP+0 (the VP word) hides the control (Guide p.20, p.155-162).
- SP and VP share the same RAM, so they must not overlap.

How the editor chooses SP:
- **There is no automatic allocation.** The default is "FFFF" (ShowBase.cs:76). The user types a hex value per control (`VarDescAddress` → `Desc_Point`, ShowBase.cs:51-63).
- Batch-property dialogs can assign an SP to several selected controls, starting at a typed value and adding a user step per control (e.g. DT/BizDraw.PropertyConfig/cfg_DisData.cs:335-356).
- The project-level `SPAddress` (INI default 0x4000 / 0x5000; TDocumentSpace.cs:794, Document.cs:303) is stored, but nothing in the generate path uses it **[not found]**.
- **Conflict check** before generating, `CheckAllAddress` (TDocumentSpace.cs:6192-6265). For each display control with SP=s it searches *all pages* for a control of a **different class** whose range `(SP', SP'+10)` (exclusive, ShowBase.cs:86-94) contains s, and if it finds one it refuses to build. Weaknesses:
  - Controls of the same class may share an SP. That is legal per Guide note (4) on p.20.
  - The real Len_Dsc (up to 13) and the VP ranges are not checked.
- Guide convention (p.20): VP in 0x1000-0x7FFF (0x5000-0x7FFF when curves are used), SP in 0x8000-0xFFFF, 0x10 spacing between SPs of the same type, 0x30 between different types.

---

## 5. Where the code and the guide disagree

| # | Topic | Code (V7.651) | Guide V2.9 |
|---|---|---|---|
| 1 | 14.bin container | 16-byte `14 "DGUS_2" 10` header, 4092×4-byte page index, packed 32-byte records, 32×FF tail | "Each page has a fixed allocation of 2/4/8 KB … max 2 MB" (p.121). That is the legacy `nJiami==1` format, which this version no longer writes. |
| 2 | Pic_ID audio bits | `byte0 = IVRCode<<2 \| (page>>8 & 3)`: 6-bit audio code, 10-bit page | "high 4 bit is the audio ID" (p.86) |
| 3 | Layer/overlay byte (icon, animation, slider, art) | Writes 0, 2, 3 for the three UI choices (`BackMode+1`) | Lists 0x00 / 0x01 / 0x02 (p.125, 128, 132, 134). Which values firmware accepts is **[unverified]**. |
| 4 | Text display 0x1C bit 7 | Set when the "auto adjust character spacing" box is ticked | ".7=0 spacing automatically adjusted, .7=1 not adjusted" (p.159). The polarity is reversed, or the UI label is wrong. Data variable 0x10 and DGUS II text 0x1C have the same issue. |
| 5 | Data variable 0x10 | Bit 7 spacing, bit 6 leading zeros, low bits alignment | Alignment only (p.152) |
| 6 | Data window Len_Dsc | 0x000C (from the DLL) | 0x000D (p.172). With 0x0C, Font_Lib at 0x1E is not copied to SP. |
| 7 | Bit icon | Len 0x0D, Filter_Set at 0x1E | Len 0x0C, table ends at 0x1C (p.141) |
| 8 | Icon overlay (0x08) | Len 0x07; byte 0x13 = `JpgFormat<<7 \| VPAddr`; Dim_Set written raw | Len 0x09 (p.146) |
| 9 | Data transmit (0x30) | Rectangle stored at 0x0A-0x11, data at 0x12-0x1F (≤ 14 B) | 22 bytes of predefined data at 0x0A (p.227) **[firmware behaviour unknown]** |
| 10 | Batch icon / video "reserved" bytes | Editor stores the rectangle / end coordinates there | Reserved, write 0 |
| 11 | Curve 0x07 | bit 7 / bit 6 flags; color field can be a VP | "0x00" |
| 12 | Drag adjust TP_Area | Overwritten with Area_Adj ± 32 px | "must be the same as the touch area" (p.96) |
| 13 | Page sliding 0x1C | bit 7 = vertical mode; Pic_Area becomes (Xs, Xe) in vertical mode | FB_En only (p.114) |
| 14 | Incremental 0x1D | Key_Delay | NULL (p.94) |
| 15 | Slide icon 0x16 | Speed_Slide | reserved (p.116) |
| 16 | GBK input | byte 0x3F always 0x02 (pinyin); 0x03 phonetic never emitted | 0x02/0x03 (p.106) |
| 17 | FE04 RTC input, FE07 param config, type 0x31 camera, type 0x22 table, MultiLanguage | Present in code | Absent from guide |
| 18 | GTF (0x18) offsets | §3.3 table | Guide table misaligned/garbled (p.184) |
| 19 | 14.bin size | Not checked by the editor | 256 KB (16 MB flash, p.23); 2 MB (p.121, legacy) |

---

## 6. Open questions

1. Firmware touch-scan priority in 13.bin: is it first match or last match? The editor writes controls oldest-first. The guide says page sliding "must have the highest priority" without saying whether that means first or last.
2. The 0x00B0 touch-access interface addresses "touch control ID 0x01-0xFF (set in DGUSII software)". How the firmware numbers controls within a page (by file order? by code?) is not determined. The editor's `nBianhao` is a per-page counter but is not written to 13.bin.
3. Layer_Mode values 0x01 vs 0x02/0x03 (§5 #3), and the polarity of the spacing bit (§5 #4). Both need a hardware test.
4. Meaning of the 0x5F lead byte (pop-up layer?) and of the FE07 "parameter config" data pack.
5. Whether firmware still accepts the legacy fixed-slot 14.bin, and the exact flash offsets (0x340000/0x380000). The offsets are derived from "slot 13/14 × 256 KB", not observed.
6. The `Func02/03/SetData` gate `[0x10252910] == 0x1204` is set by `DWINDLL.Init()`. If `Init()` failed, the editor would produce a broken 14.bin with code 2. This does not matter for re-implementation.

---

## 7. Python model and cross-check

All of these files are in the scratchpad folder `re/re2/ (research copy; code now in src/opendgus)`:

- `dgus_controls.py`: encoders for
  - touch: basic touch, return key (FE05/FD05), data input (FE00), ASCII text input (FE06);
  - display: variable icon (0x00), data variable (0x10), text display (0x11);
  - containers: `build_13`, `build_14` / `parse_14`, `parse_13`.
- `gen_harness.sh` → `harness_classes.cs`: mechanically extracts the editor's real `GetByte`/`GetData`/`Id` bodies from DT.
- `harness_main.cs`: test vectors plus a transcription of the `BuildShowBinFile` framing and `Func02/Func03`.
- `test_vs_csharp.py`: run with `python -I test_vs_csharp.py`. Result: all 8 record vectors, the full 16,512-byte 14.bin and both round-trips are byte-identical (`ALL OK`).
- `dis.py`, `sym.py`: capstone disassembly of `DWINDLL.dll` exports (Func02/Func03/SetData).
