# 01 – DGUS II (V7.651) project file format and build pipeline

Scope: what the editor saves (`DWprj.hmi`, `DWprj.tft`, `TFT\*.tft`), and what "Generate" writes into `DWIN_SET\`.
Byte layouts of 13/14/22.bin, ICL/fonts and T5LCFG are covered in other docs. This one only shows where they plug in.

Path shorthand (all relative to `vendor/decompiled/`):
- `TDS` = `DwinTerminal/BizDraw.Controls/TDocumentSpace.cs`
- `DTL` = `DwinTerminal/BizDraw.Controls/DummyTaskList.cs`
- `DM` = `DwinTerminal/BizDraw.IO/DocumentManager.cs`
- `GL` = `DwinTerminal/BizDraw/Globel.cs`
- `F1` = `DGUS_V7.651/BizDrawClient/Form1.cs`

Decoder: `re/re1/dgus_project.py`
(`python -I dgus_project.py <projectdir | x.tft | x.hmi> [--json]`). It contains a generic MS-NRBF parser, the DWIN XOR, and an INI reader.

---

## 1. Project folder layout

Created by `NewDocument` (TDS:544-563) and `OpenDocument` (TDS:1696-1706). The paths are set in `Project.setProject` (`BizDraw.Project/Project.cs:144-152`).

| Path | Written by | Purpose |
|---|---|---|
| `DWprj.hmi` | `SaveConfigtft` TDS:640-702 (`WritePrivateProfileString`) | INI project index (see 1.1) |
| `DWprj.tft` | `DocumentManager.Save(currentDocument, …)` TDS:668 | The global `Document`: screen size, global `PageParamList`, VP counters |
| `TFT\<imagefile>.tft` | TDS:665, one per page | That page's `Document` with all its controls. The filename is the image filename plus `.tft`, e.g. `TFT\00_main.jpg.tft` |
| `TFT\coords_13.json` | `BuildInputBinFile` TDS:3645, 3775 | Sidecar: real coordinates of "keyboard" keys (13.bin stores only an index for those; `InputBase.cs:101-117`). Used by import (TDS:4755) |
| `TFT\project.json` | `Project.Save` Project.cs:681-688 (Newtonsoft) | `ProjectParas`: rotary-knob GPIO settings only (`ProjectParas.cs`) |
| `DWIN_SET\` | NewDocument TDS:560 (`Globel.ProjectPathName_Simple="DWIN_SET"`, GL:56) | Holds the background images (copied in on import), the user's .icl/.hzk/.dzk files, and the generated bins |
| `image\`, `ICON\` | TDS:552-559 | Created empty. Nothing in the editor reads them (unverified; used by convention) |
| `Font\` | Multi-language feature, Project.cs:149, 155-300 | `<guid>.bmp` crops, `1.csv`, user-edited `2.xls`, rendered `Font\A\N.bmp` … |
| `HMIConfig.bin` (project root) | `Buildconfigbin` TDS:2817-2901 | Legacy 16-byte-record touch file from the old "compile" menu. Not used for T5L |
| `<exe>\Config\Terminal.ini` | TDS:671-701 | Global editor prefs and an MRU list of `.hmi` paths. Not part of the project |

The sample at `vendor/tools/Terminal-Assistant_V6.0/.../DWprj.{hmi,tft}` comes from the older Terminal Assistant V6 (`DwinTerminal, Version=6.0.0.1`). It is an empty 800x480 project with zero pages and no `TFT\` contents. Its `Document` has only 5 members (Name/Height/Width/Items/DataSource). V7.651's deserializer also requires `PageParamList`, `ImageIndex`, `VarAddress`, `SPAddress` and `CurrVarAddress` (`Document.cs:970-991`), so V7.651 would probably reject this file (unverified). It is a different variant, but the container format is the same.

### 1.1 `DWprj.hmi` = Windows INI (ANSI/GBK)

Written key by key with `WritePrivateProfileString` (TDS:646-661) and read with `IniFiles` (TDS:787-884). The sample's first line is the GBK comment `#表格配置档案`.

```ini
[INIT]
PICFIX=1            ; Document.Picpix (always forced to 1 on load, TDS:792)
VARCount=64         ; 64|128|256. Selects per-page 14.bin slot size in DGUS(I) mode (TDS:3893)
Version=0           ; Globel.VersionBh (combo index)
ProVersion=651      ; editor build. Open refuses if file > editor (TDS:1679-1688). Assembly "DGUS_V7.651" -> "651" (F1:715-717)
SCREENDSIZE=800X480 ; '<W>X<H>' (capital X)
SPADDRESS=16384     ; next free SP (description pointer) address, decimal
[IMG]
0=00_main.jpg       ; <page id>=<image file name in DWIN_SET\>  -> TFT\00_main.jpg.tft
1=01_set.bmp
```
The `[IMG]` order equals the page-list order, which is the order used by Generate. The V6 sample also has `BCOLOR=` and `COLOR=`, which V7.651 ignores.

### 1.2 `DWprj.tft` and `TFT\*.tft` = .NET BinaryFormatter (MS-NRBF)

- These are not XML and not zipped. Ionic.Zip is shipped but not used for the project. `Document.SaveDoc` (XML "DWTFT", `Document.cs:993+`) exists but is not called on the save path.
- `DocumentManager.Save` (DM:165-215) runs `BinaryFormatter.Serialize`, then **XORs** the bytes only `if (Globel.Project_Custom == 0)`.
- `Project_Custom` is hard-set to **2** in `Form1()` (F1:751). It can only become 1 via a hidden combo (F1:1772-1783, `comboBox4` "DGUS"/"DGUS II", `Visible=false` F1:4395-4400). So **stock V7.651 writes plain NRBF**. `Project_Custom==0` is an OEM build that uses the folder `SCREEN` instead of `DWIN_SET` (F1:752-757).
- `Load` (DM:67-160) tries XOR first and falls back to plain on `SerializationException` (DM:146-153), so both forms load.
- XOR algorithm (symmetric): `b[i] ^= KEY[i%256] ^ (((i>>16)+((i>>8)&0xFF)+(i&0xFF)) & 0xFF)`. `KEY` is 128 big-endian u16 (DM:85-105). The same cipher is applied to 14.bin on write when `nJiami==0` (TDS:4255-4284). Import de-XORs 13 and 14 when `Project_Custom==0` (TDS:4769-4798, 5570-5597). The 13.bin writer never XORs. Stock V7.651 does neither.
- `FileMode.OpenOrCreate` without truncate (DM:168): when a smaller document overwrites a larger one, stale trailing bytes remain. They are harmless after the NRBF MessageEnd record. A writer should truncate anyway.
- Type identity: assembly `DwinTerminal, Version=7.3.6.0, Culture=neutral, PublicKeyToken=null` (`DwinTerminal/Properties/AssemblyInfo.cs`, net20). It has no strong name, so the version in the stream is not enforced by the default binder (standard .NET behaviour, unverified against this app).

### 1.3 Serialized object model (V7.651)

| Class (file) | Serialization | Members in stream |
|---|---|---|
| `BizDraw.Core.Document` (`BizDraw.Core/Document.cs:955-991`) | ISerializable | `Name` str, `Height` i32, `Width` i32, `Items` GraphicsList, `DataSource` (abstract `BizDraw.Data.DataSource`, null in practice), `PageParamList` List<PageParam>, `ImageIndex` u16 (= page id), `VarAddress` str, `SPAddress` str, `CurrVarAddress` str, `AutoVP` bool. `backImagePath` is `[NonSerialized]`: the background is found through `[IMG]`, not the .tft |
| `BizDraw.Objects.GraphicsList` (`GraphicsList.cs:9-16`) | default field serialization of `List<DrawObject>` | `dtarget`, `List`1+_items` (DrawObject[]), `_size`, `_version`, plus `SelectedObjectChanged`/`ClickObjectChanged` **event delegates** (the sample contains `DelegateSerializationHolder` → `Document._items_SelectedObjectChanged`). Writers can emit null for those |
| `BizDraw.Objects.DrawRectangle` (`DrawRectangle.cs:1795-1834`), one per control | ISerializable | `Rectangle` (System.Drawing.Rectangle x,y,w,h), `PenWidth` i32, `Color` (System.Drawing.Color), `Toimage` str, `Dismode` enum TDismode, `DHXG` str, `CodeCMD` str, `CodeMS` str, `Cutfile` str, `ScreenSize` Point, `f13Type` i32, `nBianhao` i32, **`ConfigVar`** (the control object), `bLocked` bool |
| `ConfigVar`: input controls, `f13Type < 100` (`BizDraw.ConfigInput/*`, base `InputBase.cs:268-282`) | ISerializable | base keys `Pic_Id, AreaStart, AreaEnd, Pic_Next, Pic_On, tp_code, VarName, Var_MS, Keying, KeyCode, DataConfig, DataLen, IVRing, IVRCode, IVRLen` plus subclass keys. Covered in the 13.bin doc |
| `ConfigVar`: display controls, `100 ≤ f13Type < 202` (`BizDraw.ConfigShow/*`, base `ShowBase.cs`) | ISerializable | base `Var_Name, Var_MS, ICOFileName, Desc_Point, Sp_Mode, VarDescAddress, DrawRect, DataConfig, DataLen` plus subclass keys. Covered in the 14.bin doc |
| `BizDraw.Core.PageParam` (`PageParam.cs:58-73`) | ISerializable | `ParamName, ParamAddress, Paramlen(i16), ParamMS, Used, ParamSP, ParamKeyCode` |

`f13Type` → class, from the importers TDS:4630-4690 (13.bin) and TDS:4968-5200 / 5271-5460 (14.bin):

| f13Type | class | f13Type | class |
|---|---|---|---|
| 1 | VarInput | 100 | IconShow |
| 2 | PopMenu | 101 | AnimateShow |
| 3 | IncManager | 102 | SliderShow |
| 4 | DragManager | 103 | ArtTextShow |
| 5 | RtcInput | 104 | ImageAnimateShow |
| 6 | KeyCodeReturn (basic touch, BaseTouch) | 105 | ICONRotate |
| 7 | KeyCodeReturn (0x05) | 106 | DataTextShow |
| 8 | TextInput | 107 | TextShow |
| 9 | GBKInput | 108 | RtcTextShow |
| 10 | ParamCofig | 109 | Clock_Dis |
| 11 | Key_DO_Ret | 110 | ChartShow |
| 12 | Rotateadjust | 112 | BaseGraphs |
| 13 | SwipeAdjust | 114 | bitIcon |
| 14 | SwipePage (excluded from the overlap check) | 115 | TimeDisplay |
| 15 | ICONDragManager | 116 | ScrTextShow |
| 16 | BitButton | 117 | Two_Dimension |
| | | 118 | ZoneScrolling |
| | | 119 | Data_Window |
| | | 120 | ZoneLightSetting |
| | | 121 | AuxiliaryDisplay |
| | | 122 | TextShowII |
| | | 123 | IconPageTrans |
| | | 124 | VariableJpeg |
| | | 125 | BatchIconShow |
| | | 126 | Roller_character |
| | | 127 | GTFShow |
| | | 129 | VideoShow |
| | | 130 | DW_ProcessBar |
| | | 200 | MultiLanguage |
| | | 202 | RotaryKnob (goes to 120.lib, not 14.bin) |

Control order: Generate iterates `Items` **from last to first** (TDS:3658, 3712, 3910). Item index 0 is the front-most object.

---

## 2. Pages ↔ background images

- **Import** (`DTL.Loadpiclist` DTL:179-282). The image is copied into `DWIN_SET\` under its original name (`fileCopyto` TDS:2314-2318). The **page id is the run of leading decimal digits** of the filename (DTL:226-240): `00_boot.jpg`→0, `12abc.png`→12, `abc.jpg`→**skipped**. Duplicate ids are skipped (DTL:245-248), and ids must be `< 43690` (DTL:251). Accepted types are bmp/jpg/jpeg/gif/png (DTL:136).
- The page list (`dgvPictureList`) has cell0 = id string, cell1 = filename, cell2 = `Document`. It is persisted only as `[IMG] id=filename` plus `TFT\filename.tft`.
- Generate checks that ids are unique (`CheckImgID` TDS:3513-3530). Ids need not be contiguous. 14.bin is indexed by id (TDS:3866-3878, 3901), with a max of 4092 pages in DGUS II mode.
- **Resolution**: every page `Document` takes `Width/Height` from `SCREENDSIZE` (TDS:810-822, 844-851). The editor does **not** validate or convert the image. For page id ≥ 1000, the image's own size is used as the canvas (TDS:3170-3178, 653-660). `picConv` (TDS:6054-6074) resizes or rotates to a BMP, but only in "Save As" with rotation.
- **JPEG/ICL conversion is not done by the editor.** The screen cannot read JPG/BMP directly (manual p.43). The images in `DWIN_SET\` must be packed into a background ICL (e.g. `32.icl`, ID set at T5LCFG 0x08) by the external **ICL generator** `TOOL\multiLanguage\ICL\ICLGenerator.exe` (`DGUS_Welcome.cs:1294-1316`) or the `ImgConversion.exe`/`DW_ICON.exe` tools. Image index inside the ICL = page id. Manual: "images named 00_boot, 01_function…; image 0 is shown at boot" (T5L guide ~l.597-603).
- Editor preview reads icon libraries as `DWIN_SET\<Icon_lib>*.icl` (e.g. `IconShow.cs:279`) and fonts as `*zk`/`HZK` (GL:333, `Form_Preview.cs:314`).

---

## 3. Save / Generate pipeline

### 3.1 Save (`Form1.保存SToolStripButton_Click` F1:876 → `TDS.SaveDocument` TDS:1951 → `SaveConfigtft` TDS:640)
1. Write INI keys `[INIT]` and `[IMG]` to `DWprj.hmi` (TDS:646-664).
2. For each page row: `DocumentManager.Save(doc, TFT\<img>.tft)` (TDS:665).
3. `DocumentManager.Save(currentDocument, DWprj.tft)` (TDS:668).
4. Update the MRU and prefs in `<exe>\Config\Terminal.ini` (TDS:669-701).

Save does **not** generate bins.

### 3.2 Generate ("生成" button: `myButton5`/`toolStripButton2` → `Form1.toolStripButton2_Click` F1:1080, or Alt+B → `TDS.toolStripButton3_Click` TDS:3532-3596)
(Do not confuse it with "导入" Import: `myButton8`/`toolStripButton3` → `Form1.toolStripButton3_Click` F1:1093 → `TDS.toolStripButton1_Click` → `ReCreatFile`.)
It works from the in-memory documents and does not save first.

| Step | Method | Output (in `DWIN_SET\`) |
|---|---|---|
| 1 | `CheckImgID` TDS:3513 | duplicate page ids → abort |
| 2 | `ValidCheck` per page TDS:3598-3640 | warns about overlapping touch areas; the user can ignore |
| 3 | `CheckAllAddress` TDS:6192-6266 | VP/SP overlap → abort bin generation |
| 4 | `BuildInputBinFile(hmi, Project_Custom)` TDS:3642-3780 | **`13TouchFile.bin`**: concatenation of `InputBase.GetByte()` for every input control (pages in list order, items reversed), terminated by `FF FF`. Also `TFT\coords_13.json`. Key_DO_Ret init strings are collected in `iniData_Touch` for step 5 |
| 5 | `BuildShowBinFile(hmi, Project_Custom)` TDS:3815-4331 | **`14ShowFile.bin`** plus **`22_Config.bin`** (see below) |
| 6 | inline TDS:3570-3595 | **`120.lib`**: rotary-knob table. Always written. Header `5A A5 55 AA type rtc tp dp kp`, u16 BE pageCount, zero-padded to 96 bytes. Then per page 8 bytes `[id u16][n u8][0][offset u32 BE]`, then knob records (`Document.getRotaryKnobData` Document.cs:1254-1277, `Project.GetRotaryKnobData` Project.cs:700-713) |

`BuildShowBinFile` in detail:
- 14.bin in **DGUS II mode** (`nJiami=2`, the default) has three parts:
  1. A 16-byte header from native `Globel.Func02(maxPageId, …)`.
  2. 4092 × 4-byte page index entries from native `Func03(addr, count, …)`. The start address is 16384 = 16 + 4092·4, and each page block is `32 * count` bytes.
  3. Per existing page id, ascending: that page's display controls, 32 bytes each (`ShowBase.GetData()`), up to 255 per page.
  4. 32 bytes of `FF` appended (TDS:4249-4254), file written TDS:4285.
  - `Func02`/`Func03` are P/Invoke into **`DWINDLL.dll`** (GL:160-164), so they are not in the C# source.
  - The importer suggests the format (TDS:5604-5623): header `14 'D' 'G' 'U' 'S' '_' '2' 0x10 maxId_hi maxId_lo …` and entry `[count u8][addr u24 BE]`. Inferred, not verified.
  - `DGUS` mode (`nJiami=1`) instead uses fixed `VarCount/64*2048`-byte slots per page and an in-band header in page 0 (TDS:3908-3925).
- **22_Config.bin** = `InitData`, 131076 bytes (= 64K words of VP space + 4). It is built from three sources:
  1. Bytes 2048..2559 are copied from the first 512 bytes of `DWIN_SET\22.bakdata`, if that file exists (TDS:3822-3843). `22.bakdata` is the "network config" file edited by `TOOL\22.exe` (`DGUS_Welcome.cs:1461-1471`).
  2. Each display control's initial value from `GetInitData()` is written at byte `VP*2`, but only when `VP*2 > 512` (TDS:3989-4230). Types: 1/2 byte, 3 word, 4/42 int32, 41 int64, 43 float, 44 double, 5 string in the control's encoding, 30 u16.
  3. Key_DO_Ret hex init strings are written at `VP*2` (TDS:4288-4309).

  Other agent: layout detail.
- On a non-zero return, 14.bin generation reports "VP > VarCount" or a format error (TDS:3552-3565).

### 3.3 File names and the Chinese names
- Defaults in `Globel`: `FileName_13 = "\13触控配置文件.bin"`, `FileName_14 = "\14变量配置文件.bin"` (GL:60-62).
- `Form1.Set_Text` **unconditionally overrides** them with `"\13TouchFile.bin"` / `"\14ShowFile.bin"` (F1:685-686). V7.651 therefore writes ASCII names. The Chinese names only occur if `DwinTerminal.dll` is hosted without Form1, or in older versions.
- **No renaming step exists or is needed.** The T5L SD loader identifies files by their **leading decimal number** ("13*.BIN", "14*.BIN", "22*.BIN", "ID+(optional)filename.ICL"; T5L guide ~l.536-604, "DGUSII_T5L calls configuration files by the filename number"). So `13TouchFile.bin`, `13触控配置文件.bin` and `13.bin` are equivalent on the screen.
- The editor's own **Import** (`ReCreatFile` TDS:3405 → `ReCreatInputFile` TDS:4745 / `ReCreatShowFile` TDS:5560) opens the exact `Globel.FileName_13/14` names. It therefore needs `13TouchFile.bin`/`14ShowFile.bin` and will not open `13.bin`.
- Other `DWIN_SET` content that the editor touches: `CONFIG.txt` (`RC=00;`/`RC=10;` line for VarCount, TDS:704-719, SysCfgDoc), user-supplied `*.icl`, `*.hzk/*.dzk/*.bin` fonts, `T5LCFG*.CFG` (other agent), `22.bakdata`. The multi-language feature (F1:1953-1961) renders `Font\<col>\N.bmp`. Its `40.icl` builder `Project.generateICL` (Project.cs:269-374 → `BizDraw.Utils/ICL.cs`) is private and never called (dead code).

---

## 4. Can we produce DWIN_SET directly, bypassing .hmi?

**Yes. `.hmi`, `.tft`, `TFT\` and `coords_13.json` are editor-only state.**
- The screen consumes only `DWIN_SET\` files (manual l.515-523, 588). None of the generated bins reference the .hmi or .tft.
- Generation is a pure function of (page id list, per-control config objects, VarCount, mode). All of it is in managed code except the 14.bin header and page-index helpers in `DWINDLL.dll`.
- DWIN's own workflow even supports recovering a project from just `DWIN_SET` ("Import", manual §8.1), which confirms the bins are the source of truth.

Minimum SD set for a working UI, from the manual plus this pipeline (other agents confirm the bytes):

| File | Origin |
|---|---|
| `T5LCFG*.CFG` | hardware config. 0x08 = background ICL id, 0x05.5 = load 22 file |
| `32*.ICL` (or the id set in CFG) | background JPEGs, index = page id. Built with external ICL tool, or our own encoder |
| `13*.bin` | touch config |
| `14*.bin` | display config: header + 4092-entry page table + 32-byte records |
| `22*.bin` | VP init image, optional |
| `NN*.ICL` icons, `NN*.HZK/DZK/BIN` fonts | as referenced by controls |
| `120.lib` | only if rotary knobs are used. The editor always writes it (unverified whether stock firmware needs it) |

Optionally emit a `.hmi` + `.tft` set too, so a human can open our output in the GUI. That needs an NRBF *writer* that reproduces the DwinTerminal class shapes in 1.3, including each ConfigVar subclass's `GetObjectData` keys. The format allows it, but it is more work than writing the bins.

---

## Open questions / unverified
1. **`DWINDLL.dll` `Func02`/`Func03`**: the exact 14.bin header bytes (16 bytes) and index-entry encoding. Inferred from the importer as `14 44 47 55 53 5F 32 10 <maxId BE16> …` and `[n][addr BE24]`, addr starting at 0x4000, `+32*n`. Needs a real generated 14ShowFile.bin or a disassembly (no capstone/pefile in this env). The return value 0 means overflow (TDS:3888).
2. No V7.651 `DWprj.tft` or generated `DWIN_SET` sample on disk. The decoder was validated only on the V6 sample and on a synthetic BinaryFormatter stream (Rectangle, Color, Point, arrays, refs, nulls). A real V7 project with controls should be decoded to confirm field names and types.
3. Whether the firmware tolerates a missing `120.lib`, and whether `22_Config.bin` is needed when CFG 0x05.5 is off.
4. Bytes 0..2047 of 22_Config.bin are left zero except for 22.bakdata at 2048. Need to confirm what the screen does with VP 0x0000-0x03FF from the 22 file (the manual says it loads 0x2000-0xFFFF, initializes 0x1000-0xFFFF).
5. Whether `image\` and `ICON\` folders are used by any external tool (ICLGenerator default paths?).
