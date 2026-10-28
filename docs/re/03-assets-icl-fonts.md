# 03 — Image and font asset formats (ICL, HZK/DZK/BIN, gray fonts, native DLLs)

Scope: page background images, `.ICL` image/icon libraries, font libraries, and the native DLLs shipped with DGUS II V7.651 (T5L).
Status markers: **[V]** verified by code and by a round-trip test; **[C]** read directly from decompiled code; **[M]** from the manual only; **[?]** inferred or unverified.

Path abbreviations:

| Abbrev | Path |
|---|---|
| `DT/` | `vendor/decompiled/DwinTerminal/` |
| `DI/` | `vendor/decompiled/DW_ICON/BuildICO/` |
| `D0/` | `vendor/decompiled/DW_0Font/ttf/` |
| `IG/` | ICLGenerator.dll, decompiled by me with ilspycmd into `scratchpad/re3/decomp/ICLGenerator/` (source binary: `TOOL/multiLanguage/ICL/ICLGenerator.dll`, .NET 5, x64) |
| `UG/` | UnicodeGrayFont.dll → `scratchpad/re3/decomp/UnicodeGrayFont/` |
| `MV/`, `EX/` | Movie2ICL.exe, Excel2ICL.dll → `scratchpad/re3/decomp/{Movie2ICL,Excel2ICL}/` |
| `MAN` | `vendor/docs/txt/T5L_DGUSII-Application-Development-Guide-V2.921.txt` |

Scratchpad root: `C:\Users\Edward\AppData\Local\Temp\claude\D--apps-displayuscreen\304e2e36-9a32-434d-afd0-65a5f528b7e4\scratchpad\re3\`. The decompiled sources there are throwaway; re-create them with `ilspycmd -p -o <dir> <dll>`.

Deliverable code:
- `scratchpad/re3/dgus_assets.py`: ICL reader and writer (stdlib only), JPEG preparation, encoder (needs Pillow), matrix-font index/pack/build, gray-font build/read, and a CLI (`info`, `extract`, `build`).
- `scratchpad/re3/test_dgus_assets.py`: all tests pass. It checks CRC against the C# tables, 0# offsets against MatFonts, ICL round-trip and alignment, agreement with a literal port of the C# parser, legacy 16 MB padding, and the glyph-index formulas.

No sample `.icl`, `.hzk` or `.dzk` files exist under `vendor/tools/`. Everything was checked against the code, not against real DWIN-produced files. **The first thing to do with real hardware is to run `dgus_assets.py info` on an ICL produced by DGUS.**

---

## 1. Page background images

| Item | Finding | Ref |
|---|---|---|
| Accepted inputs (editor) | `*.bmp;*.jpg;*.jpeg;*.png`. The file is **copied verbatim** into the project `DWIN_SET` folder (`fileCopyto` → `File.Copy`). No resize or re-encode at import. | `DT/BizDraw.Controls/DummyTaskList.cs:478-488`, `DT/BizDraw.Controls/TDocumentSpace.cs:2314-2318` [C] |
| Page ID | Leading decimal digits of the file name (`00_boot.jpg` → page 0). | `DT/BizDraw.Controls/DummyTaskList.cs:223-235`; MAN:599-600 [C][M] |
| Required format | Same resolution as the screen, 24-bit colour, JPEG/BMP/PNG. | MAN:597-600 [M] |
| What goes to flash | The T5L cannot read raw JPEG/BMP. Backgrounds are packed into an **ICL** (same DGUS_3 format as icons, §2). Index *n* in the ICL = page *n*. | MAN:511-514, 601-605 [M] |
| File number | Any free ID; **32 is the convention** (`32.ICL`, or `32_anything.ICL`). The background ICL ID is written at **T5LCFG byte 0x08** (0x20 for 32). Register 0xDE switches background ICLs at runtime (multi-language). | MAN:595, 603-607, 1035, 2484-2510 [M] |
| Conversion | Done by ICLGenerator (§2.4): TurboJPEG, quality 75, 4:2:0 by default (4:4:4 selectable), baseline. Pixels are 24-bit RGB → YCbCr JPEG. **There is no RGB565 step** in the T5L path. RGB565 only exists in the legacy `.ICO` format (§2.6). | `IG/DGUSCommon.Tools/IclFileBuilder.cs:433-441`, `IG/ICLGenerator.Models/AppSettings.cs` [C] |
| Size limit per picture | Enforced by `IclFileBuilder` on the padded JPEG: **253 942 B (T5L1)** / **778 230 B (T5L2)**, i.e. 248 KB / 760 KB minus the 10-byte block header. If too big, quality is lowered in steps of 5. | `IG/.../IclFileBuilder.cs:462-497`; MAN:394, 581-582, 7905 [C] |
| Legacy export | `picConv` resizes to the screen size (HighQualityBicubic), optionally rotates 270°, and saves 24bpp BMP. It is only used for project export/rotation, not for the ICL. | `DT/BizDraw.Controls/TDocumentSpace.cs:6054-6073, 2505-2513` [C] |
| Editor preview | Reads backgrounds from the source image files, not from the ICL. Icons are read from `.icl` via `GetICO`. | `DT/BizDraw.Controls/Form_Preview.cs:2300-2305, 4006-4065` [C] |

How the toolchain produces ICLs:
- The DGUS editor (`DGUS_V7.651.exe` / `DwinTerminal.dll`) has **no built-in background→ICL step**.
- The welcome page launches separate tools: "ICL 生成工具" (ICL Generator) runs `TOOL\multiLanguage\ICL\ICLGenerator.exe` (`DT/BizDraw.Controls/DGUS_Welcome.cs:1294-1316`).
- `AllTool.exe` (native Qt + libjpeg) also has "Make ICL / Add to ICL / JPG Quality / 4:4:4" (strings only; launched with `<DWIN_SET> <nType> <lang>`, `DGUS_Welcome.cs:1368-1377`) **[?]**. Its output was not decompiled. Since the manual says only DGUS_3 is accepted (MAN:555), it must be the same container.

## 2. ICL file format ("DGUS_3")

All multi-byte fields are **big-endian**. Writer: `IG/DGUSCommon.Tools/IclFileBuilder.cs:267-361, 502-565`. Readers: `IG/DGUSCommon.Tools/IclFileParser.cs:25-97`, `DT/BizDraw.Controls/frm_ICON_Sel.cs:1596-1660`, `DT/BizDraw.Controls/Form_Preview.cs:4006-4065`.

### 2.1 File header (16 bytes) [V]

| Off | Size | Value | Notes |
|---|---|---|---|
| 0 | 6 | `44 47 55 53 5F 33` = `"DGUS_3"` | magic (`IclFileBuilder.cs:34`) |
| 6 | 2 | CRC | CRC-16/MODBUS (poly 0xA001 reflected, init 0xFFFF) over **bytes 8..EOF**. Stored as std-CRC **little-endian** (DWIN "CRCH,CRCL" table convention). `IclFileBuilder.cs:316-327`, `IG/DGUSUtility.Tools/Crc16.cs`. Verified against the C# tables. |
| 8 | 4 | length | ICLGenerator: **file size − 8**. Legacy writers store `4096 + data_len − 8` (bug; see 2.5). |
| 12 | 1 | `04` | index entry size; readers reject anything else (`IclFileParser.cs:42`) |
| 13 | 2 | max_id | highest icon ID present |
| 15 | 1 | crypto flag | always 0 in ICLGenerator (`new IclFileBuilder(ushort.MaxValue, 0)`, `IG/ICLGenerator/MainWindow.cs:546`). The legacy writers also write 0. |

### 2.2 Index table [V]

- Starts at offset 16 with `max_id+1` entries of u32.
- Each entry is the **absolute file offset** of that icon's block; 0 means no icon. Entry for ID *i* is at `16 + 4*i`.
- ICLGenerator places the data directly after the index (offset `16+4*(max_id+1)`, which is a multiple of 4).

### 2.3 Icon block [V]

| Off (rel. block) | Size | Field |
|---|---|---|
| 0 | 2 | width (from SOF0) |
| 2 | 2 | height |
| 4 | 2 | `header_len` = JPEG bytes from SOI through the end of the (padded) SOS segment |
| 6 | 4 | `data_len` = remaining bytes (entropy data + EOI + padding + 8 zero bytes) |
| 10 | header_len | JPEG header part |
| 10+header_len | data_len | scan data part |

JPEG massaging (`TryAlignAndPadJpeg`, `IclFileBuilder.cs:502-565`):
1. The JPEG must start with `FFD8` and contain **`FFC0` (baseline SOF0)**. Progressive or extended JPEGs fail and get re-encoded.
2. The first `FFFE` COM segment is removed.
3. Size check against the limit (§1).
4. Zero bytes are inserted at the end of the SOS segment and its length field is increased, so that `(block_off + 10 + header_len) % 4 == 0`. The **entropy-coded data therefore starts 4-byte aligned**.
   - Legacy `DT/BizDraw.Utils/ICL.cs:114-130` inserts `0xFF` instead of `0x00`.
   - Up to 3 bytes. In tests the pad was always 3.
5. Zeros are appended so that `(10+len)%4==0`, then **8 more zero bytes**. Each block length is a multiple of 4, so every block starts 4-aligned. This matches the manual note "icl positions and lengths 4-byte aligned since V7.640".

Readers undo step 4:
- Find the last `FFDA` in the header part, set its length back to 12 (3-component SOS), and drop the extra bytes (`IclFileParser.cs:65-82`).
- **The padded JPEG is not decodable by libjpeg without this fix** (bogus SOS length; verified with Pillow). The T5L hardware decoder evidently ignores the SOS length or uses the alignment.
- My reader computes the real length as `6+2*Ns`, so grayscale JPEGs work too. DWIN's hard-coded 12 would break grayscale JPEGs, but ICLGenerator always produces 3-component JPEGs.

### 2.4 Image encoding (ICLGenerator) [C]

| Setting | Default | Ref |
|---|---|---|
| Encoder | libjpeg-turbo (`Quamotion.TurboJpegWrapper`, `turbojpeg.dll`), input BGRA | `IG/DGUSUtility.Tools/JpegHelper.cs:34-56` |
| Quality | 75 (slider 1-100) | `AppSettings.JpegQuality`, `IclFileBuilder.cs:433` |
| Chroma subsampling | UI index 1 = **4:2:0** (default); 0 = 4:4:4 | `AppSettings.ChromaSubsampling=1`, `JpegHelper.MapSubsampling` |
| Re-encode policy | The source is **always decoded and re-encoded**, even if it is already a JPEG. "SkipCompression" keeps the original JPEG bytes if they fit. | `IclFileBuilder.cs:454-500` |
| Overflow | Retry at quality q, q−5, q−10, … ≥1 | `IclFileBuilder.cs:481-497` |
| CPU type | 0 = T5L1 (253 942 B), 1 = T5L2 (778 230 B) | `IclFileBuilder.cs:462` |
| Max icons | 65 536 per ICL (IDs 0-65535); >65536 files is an error | `MainWindow.cs:538-546` |
| ID assignment | **Sequential 0..N-1 in natural sort order of file names in a folder.** Not by leading digits. One ICL per folder, named after the folder. You rename it to `NN_xxx.icl` yourself. | `MainWindow.cs:525-546`, `IclFileBuilder.AddFiles` :91-114 |

**Transparency** (PNG/GIF with alpha < 255 anywhere; `IG/DGUSIconLibrary/IconManager.cs:438-603`). The encoder switches to quality 100 + 4:4:4 for these images. Two modes:
- *Smart* (default):
  - A "rare" key colour is chosen from the per-channel histograms: the middle of a run of ≥42 under-used values, at least distance 300 from the mean colour.
  - Pixels with alpha < 80 become the key colour; others become opaque.
  - **Pixel (0,0) is always forced to the key colour.**
- *Background* (`TransparentImageMode=1`): alpha-composited on a fixed colour (default `#FFFFFF`).

On the screen, the icon controls' "transparent mode" filters the background colour with `Filter_Set` tolerance 0x01-0x3F (MAN:4519-4529). Together with the forced (0,0) pixel, and the legacy `.ICO` storing pixel(0,0) as the key in its index (`DI/frmprogress.cs` Buildconfigbin), **the firmware's key colour is most likely the icon's (0,0) pixel** [?].

### 2.5 Legacy writer variant (`DT/BizDraw.Utils/ICL.cs`, `MV/Movie2ICL.Utils/ICL.cs`, `EX/Excel2ICL.Utils/ICL.cs`) [C]

These are used for multi-language text icons (`DT/BizDraw.Project/Project.cs:411-416`), video frames, and Excel-to-ICL. They differ from ICLGenerator as follows:
- The index area is padded so that **data starts at 0x8000** (`startIndex=32768`). The index has no overflow check, so it holds at most 8188 icons.
- **16 MB boundary rule**: for absolute flash address `file_id*0x40000 + offset`, if an image would cross a 16 MB boundary (`addr>>24` changes), zeros are inserted so it starts exactly at the boundary (`ICL.cs:91-107`). This matches MAN:556 "for multi-Flash expansion, one ICL data is saved in one Flash". ICLGenerator does **not** do this [?: an ICLGenerator ICL with ID ≥ 48 bigger than the space left in the first 16 MB could break on expanded flash].
- Length field = `4096 + data_len − 8` (wrong value). `MV writeICL()` (:188-245) writes `total−8` but computes the CRC over header+index only. **So the firmware probably checks neither the length field nor the CRC strictly** [?].
- The JPEG comes from GDI+ at a quality found by binary search so the size is close to the source file size (`DT/BizDraw.Utils/JpgUtils.cs:82-139`). Movie2ICL uses `ffmpeg -q:v 10/20/30` (`MV/Movie2ICL/Form1.cs:203`).

`dgus_assets.build_icl(..., layout='legacy-32K', file_id=N)` reproduces this layout.

### 2.6 Legacy `.ICO` (DW_ICON.exe, pre-T5L) — not for T5L [C]

`DI/frmprogress.cs` Buildconfigbin/buildPic, read back in `DI/frm_BuildDWICO.cs:1424-1517`:
- Raw RGB565 big-endian (or 24-bit) pixels.
- 6-byte index entries at `id*6`: w_lo, h_lo, `[w_hi<<6 | h_hi<<4 | addr>>24 &0xF]`, addr(3), key colour from pixel(0,0).
- Data starts at 0x40000 (`131072*pix`); max ID 43689.

DGUS II for T5L only loads `.icl`. This format is documented only so it is not confused with ICL.

### 2.7 File number → flash location [M]

| Item | Value |
|---|---|
| Address of a file | `file_id * 256 KB` in the 16 MB NOR (MAN:384-399). |
| Sectors used | `ceil(size/256K)`. You must leave the following IDs free (MAN:392-399, 621-623). |
| Font space vs picture space | Fonts and other BIN files use IDs 0-47; pictures use 16-63. The ranges overlap. |
| Fixed IDs | 12 (input method), 13 (13.bin), 14 (14.bin), 22 (22.bin). |
| Expanded flash | IDs 64+ for expanded NOR. NAND uses 0xC0-0xFF, each 8 MB (MAN:585). |
| Serial (0xAA) download | Uses 32 KB blocks: block = `file_id*8` (MAN:1945-1960). |
| How controls name an ICL | By ID (`Icon_lib` byte). The editor finds the file with glob `"{id}*.icl"` (e.g. `DT/BizDraw.ConfigShow/IconShow.cs:279`). Beware: `4*.icl` also matches `48.icl`. |

## 3. Font files

### 3.1 Font ID → file

- Font file = `ID[_name].BIN|DZK|HZK|GTF` with ID 0-47, stored at `ID*256KB` (MAN:547).
- The editor scans `*zk` files in DWIN_SET and keys them by leading number (0-255). It skips IDs 1-23 (`DT/BizDraw/Globel.cs:330-366`).
- ICLGenerator's font lookup prefers `bin, dzk, hzk, gtf` by `"{id}_*"` (`IG/DGUSIconLibrary/IconManager.cs:654-680`).
- **HZK, DZK and BIN are the same raw matrix layout. Only the name differs.** There is no header [C: MatFonts loads the whole file as a glyph array; DW_0Font writes `.HZK`, its default name is `bmpFont.dzk`, and the BIN writers are the same code].

### 3.2 Matrix glyph format (1 bpp) [V]

- Glyph = `ceil(W/8) * H` bytes, row-major.
- Within a byte the **MSB is the leftmost pixel**; 1 = ink.
- Rows are padded to whole bytes.
- Library = flat array, glyph *n* at `n * glyph_bytes`.

Refs: `DT/BizDraw.Objects/MatFonts.cs:175-208`, `DT/BizDraw.Objects/DrawRectangle.cs:658-690`, `D0/Form1.cs:520-545`.

Glyph index per text-control `Encode_Mode` (byte 0x0B.H low nibble, MAN:5470-5480). Formulas from `DT/BizDraw.Objects/DrawRectangle.cs:416-516`:

| Mode | Encoding | Index for double-byte (hi, lo) | Capacity | ASCII (single byte) |
|---|---|---|---|---|
| 0 | 8-bit | byte value | 256 | lib `Font1_ID`, idx = byte [M] (the preview wrongly uses the ASCII lib) |
| 1 | GB2312 | `(hi-0xA1)*94 + (lo-0xA1)` | 8178 (87×94) | from `Font0_ID` lib at width X/2 |
| 2 | GBK | `(hi-0x81)*190 + (lo-0x40)` if lo≤0x7E else `lo-0x41` | 23 940 | same |
| 3 | BIG5 | `(hi-0xA1)*157 + (lo-0x40)` if lo≤0x7E else `lo-0x62` | 13 973 | same |
| 4 | SJIS | `((hi≤0x9F ? hi-0x81 : hi-0xC1))*189 + lo-0x40` | — | same |
| 5 | UNICODE | UTF-16 code unit | 65 536 | from `Font1_ID` (same lib) [M] |

- In modes 1-4, ASCII glyphs come from `Font0_ID` with width = `Font_X_Dots/2` and height `Font_Y_Dots` (MAN:5463-5467).
- Y dots must be even (MAN:5492).
- Example sizes: a full UNICODE 16×16 library is 2 MB (8 sectors); a GB2312 24×24 library is 588 816 B (3 sectors).

### 3.3 0# ASCII font (factory pre-installed; DW_0Font.exe / Font0_16.exe) [V]

- Contains sizes W = 4..64. Each size is a block of 128 chars (0x00-0x7F), each cell W×2W.
- Blocks are concatenated with no header. The block for width W starts at `Σ_{k=4}^{W-1} 128·2k·ceil(k/8)`. This reproduces exactly the 61-entry table in `DT/BizDraw.Objects/MatFonts.cs:37-46`.
- Total size is 3 082 752 B (12 sectors). DW_0Font writes it as `0_DWIN_ASC.HZK` (`D0/Form1.cs:806-866`).
- Rasterisation: GDI+ `DrawString` (white on black, point size = W, user X/Y offset/scale). **Any non-black pixel counts as ink**, so anti-aliased edges become solid (`D0/Form1.cs:164-195, 520-545`).

### 3.4 Other font generators

These are all native Qt tools. I only inspected their strings; their formats are **[?]**.
- `fontLibrary.exe`: GB2312/UNICODE `*.HZK/*.bin` matrix generator (format = §3.2 [?]).
- `Font_UIC.exe`: generates UIC config modules and font previews.
- `fontbit4.exe`: "Dwin_Gray_Font", "DGUSII Font v3.1", GB2312/UNICODE, `*.bin`. Probably an older 4-bit gray font tool.

### 3.5 4-bit gray (anti-aliased) Unicode font — "DGUS_2" [C, round-trip tested]

Built by `TOOL/unicode gray font/UnicodeGrayFont.exe`, `UG/UnicodeGrayFont.Utils/FontLibUtil.cs:13-156`. Saved as `*.bin`. Used by text display on kernel V45+ (MAN:5931-5945).

| Off | Size | Value |
|---|---|---|
| 0 | 8 | `"DGUS_2"` + `00 00` (CRC not filled in) |
| 8 | 4 | file size (BE) = data_len + 327 936 |
| 12 | 1 | 1 |
| 13 | 2 | glyph_count + 3 |
| 15..19 | 5 | `01 04 80 00 04` (4 = bits/pixel?) [?] |
| 20 | 1 | MaxWidth |
| 21 | 1 | MaxHeight |
| 22 | 1 | 1 |
| 23 | 233 | zeros → header is 256 B |
| 256 | 65536×5 | index per code point U+0000..U+FFFF |
| 327 936 | … | glyph data |

Index entries:
- Glyph: `[valid_width][u32 BE absolute addr | 0xF0000000]`.
- Missing glyph: all zero.
- Control codes ≤ 0x20: `[width][type<<4][0][0][0]`, with LF type 2 width 10, CR type 1 width 10, SPACE type 3 width MaxWidth/4.

Glyph data:
- MaxWidth×MaxHeight Gray8 pixels → high nibbles packed 2 per byte (first pixel in the high nibble), padded to an even byte count.
- The glyph is rendered (WPF `FormattedText`, white on black) and shifted left so its first ink column is x=0 (`UG/.../ImageUtil.cs:107-139, 193-229`).
- 20×20 ≈ 200 B/glyph, matching the manual's "20×20 = 5.85 MB" for a ~29 k-char set.

### 3.6 GTF icon font [M only]

- GTF icon font control 0x5A18: `GTF_ID`, Font_ID 0-0x3FB; key values 0x01-0xFF map to icon rectangles (MAN:6071-6135).
- File ID 0-63, one 256 KB subspace per GTF.
- Made by the separate "GTFTool", which is not present in this install. **The format is unknown.**

## 4. Native DLLs

Exports were parsed with my own PE parser (`scratchpad/re3/pe_exports.py`; pefile is not installed).

| DLL | Arch | Exports | Role | Image related? |
|---|---|---|---|---|
| `DWINDLL.dll` (1.8 MB, MFC) | x86 | `Draw, Func01, Func02, Func03, Func04, GetData, Init, SetData, sum` | `Init()` licence/startup gate (`DGUS_V7.651/BizDrawClient/Program.cs:15`). `GetData/SetData(int nID, …)` control-record codecs (`DT/BizDraw/Globel.cs:145-164`, e.g. `Data_Window.cs:285`). `Func02(max, ref byte[16])` and `Func03(addr, count, ref byte[4])` build the **13/14.bin page index header** (`TDocumentSpace.cs:3886-3899`). `Func01(byte[32]) → control type` for the preview (`Form_Preview.cs:2249-2321`). `Draw` is preview. | **No** — belongs to agent 01/02's scope |
| `CoreDll.dll` | x86 | ~780 C++ exports under `core::settings`, `core::registry`, `core::ms::MSWindow` | generic settings/registry helper | No |
| `SampleApplication.dll` | x86 | `CheckRuntime, EncryptString, GetCpuID(W), GetDiskID(W), GetMacID(W), GetModuleBase, MainDLL, _CorExeMain` | hardware-ID licensing / anti-tamper | No |

**There is no native image or font encoder in the editor.**
- JPEG work is done in managed code: GDI+ in DwinTerminal, TurboJPEG in ICLGenerator, ffmpeg in Movie2ICL.
- All of it can be reproduced in Python with Pillow, which bundles libjpeg-turbo with the same standard IJG quant/Huffman tables.
- Expected result: identical quality scaling and very likely the same bytes for the same quality and subsampling, apart from JFIF density fields [? not diffed against a real ICLGenerator output].
- The format does not need byte identity. The device only needs baseline JPEG with the alignment rules in §2.3.

## 5. Open questions / to verify on hardware

1. Real DGUS-made `.icl`: confirm the header bytes, CRC endianness and length field (use `dgus_assets.py info`). Does the T5L reject a wrong CRC or length field? The legacy writers suggest it does not.
2. Is the transparency key the icon's pixel (0,0), and how does `Filter_Set` tolerance apply?
3. Does the T5L need 4:4:4 vs 4:2:0, or restart intervals? (The manual suggests 4:4:4 to fix "scattered dots".)
4. Does ICLGenerator's lack of the 16 MB boundary padding break ICLs above ID 48 on expanded flash?
5. HZK vs DZK vs BIN: confirm on a real `fontLibrary.exe` output that there is no header. Also confirm how the firmware handles 8-bit mode (0) with the ASCII lib.
6. GTF format, `fontbit4.exe` format, and the meaning of DGUS_2 header bytes 12-22.
7. AllTool.exe "Make ICL" (native) was not decompiled. Is its output the same as ICLGenerator's?
