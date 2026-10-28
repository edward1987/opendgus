"""dwinemu - desktop emulator for DWIN T5L (DGUS II) projects.

Reads the same DWIN_SET folder that goes onto the display (ICL images, 13.bin touch, 14.bin display,
22.bin initial values), draws the pages and lets you click them like the touch screen.

    python dwinemu.py ../demo/home_control/DWIN_SET [--size 1024x600] [--scale 1.0]

Supported: page backgrounds (32.icl or --bg-icl), variable icon (0x00), data variable (0x10),
text (0x11); touch: basic touch / page switch, incremental adjust (FE02), return key code (FE05),
press-effect pages (Pic_On). Other control types are outlined in red so nothing is silently missed.
The folder is re-read automatically when its files change (e.g. after running build.py).

0# font model: a character is Font_X * --char-w wide and Font_X * --char-h tall (manual: line pitch
= Font_X * 2). Calibrate these against a photo of the real screen.
"""
import argparse
import io
import struct
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from ..formats import controls as C
from ..formats import icl as A

MONO = "C:/Windows/Fonts/consola.ttf"


def rgb565(v):
    return ((v >> 11) & 0x1F) * 255 // 31, ((v >> 5) & 0x3F) * 255 // 63, (v & 0x1F) * 255 // 31


def u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def s16(b, o):
    return struct.unpack_from(">h", b, o)[0]


# ------------------------------------------------------------------ project model

class Project:
    def __init__(self, folder: Path, bg_icl: int):
        self.folder, self.bg_icl = folder, bg_icl
        self.load()

    def files(self):
        return sorted(p for p in self.folder.iterdir() if p.is_file())

    def stamp(self):
        return tuple((p.name, p.stat().st_mtime_ns) for p in self.files())

    def load(self):
        self.icls, self.warnings = {}, []
        self.touch, self.show, self.init = [], {}, {}
        for p in self.files():
            name, ext = p.name.upper(), p.suffix.upper()
            num = int("".join(ch for ch in name.split("_")[0].split(".")[0] if ch.isdigit()) or -1)
            try:
                if ext == ".ICL":
                    self.icls[num] = A.read_icl(p.read_bytes())
                elif ext == ".BIN" and num == 13:
                    self.touch = [self.decode_touch(r) for r in C.parse_13(p.read_bytes())]
                elif ext == ".BIN" and num == 14:
                    self.show = C.parse_14(p.read_bytes())
                elif ext == ".BIN" and num == 22:
                    d = p.read_bytes()
                    self.init = {i // 2: u16(d, i) for i in range(0x2000, len(d) - 1, 2) if d[i] or d[i + 1]}
            except Exception as e:  # keep running, show the problem
                self.warnings.append(f"{p.name}: {e}")
        self._img_cache = {}

    @staticmethod
    def decode_touch(r: bytes) -> dict:
        t = {"page": u16(r, 0) & 0x3FF, "area": struct.unpack_from(">4H", r, 2),
             "next": None if r[10] == 0xFF else u16(r, 10), "on": None if r[12] == 0xFF else u16(r, 12),
             "code": u16(r, 14), "raw": r}
        if r[14] in (0xFE, 0xFD) and len(r) >= 32:
            t["type"] = r[15]
            t["upload"] = r[14] == 0xFE
            t["vp"], t["vp_mode"] = u16(r, 17), r[19]
            if r[15] == 0x02:
                t.update(inc=bool(r[20]), wrap=bool(r[21]), step=u16(r, 22), vmin=s16(r, 24), vmax=s16(r, 26),
                         once=bool(r[28]))
            elif r[15] == 0x05:
                t.update(key=u16(r, 20))
        else:
            t["type"] = None
        return t

    def image(self, lib: int, icon: int):
        key = (lib, icon)
        if key not in self._img_cache:
            icl = self.icls.get(lib)
            e = icl.entries.get(icon) if icl else None
            self._img_cache[key] = Image.open(io.BytesIO(e.jpeg())).convert("RGB") if e else None
        return self._img_cache[key]

    def pages(self):
        icl = self.icls.get(self.bg_icl)
        ids = set(icl.entries) if icl else set()
        return sorted(ids | set(self.show) | {t["page"] for t in self.touch})


# ------------------------------------------------------------------ renderer

class Renderer:
    def __init__(self, size, char_w, char_h):
        self.W, self.H = size
        self.char_w, self.char_h = char_w, char_h
        self._fonts = {}

    def font(self, px):
        if px not in self._fonts:
            self._fonts[px] = ImageFont.truetype(MONO, max(4, px))
        return self._fonts[px]

    def draw_text(self, img, xy, text, font_x, color):
        """0# font approximation: fixed cells of font_x*char_w by font_x*char_h, glyph centred."""
        cw, ch = max(1, round(font_x * self.char_w)), max(1, round(font_x * self.char_h))
        d = ImageDraw.Draw(img)
        f = self.font(int(ch * 0.95))
        x, y = xy
        for c in text:
            d.text((x + cw / 2, y + ch / 2), c, font=f, fill=color, anchor="mm")
            x += cw
        return (xy[0], xy[1], x, y + ch)

    @staticmethod
    def number_text(v, n_int, n_dot, vtype, zeros):
        if vtype == 0:
            v = v - 0x10000 if v & 0x8000 else v
        elif vtype == 2:
            v = v >> 8
        elif vtype == 3:
            v = v & 0xFF
        neg = v < 0
        digits = str(abs(v)).rjust(n_dot + 1, "0")
        ip, dp = (digits[:-n_dot], digits[-n_dot:]) if n_dot else (digits, "")
        ip = ip[-n_int:] if n_int else ip
        if zeros:
            ip = ip.rjust(n_int, "0")
        return ("-" if neg else "") + ip + ("." + dp if n_dot else "")

    def draw_art(self, proj, img, rec, val, overlay):
        """Artistic variable 0x03: each character is an icon icon0 + index('0123456789-.')."""
        x, y, icon0, lib = u16(rec, 8), u16(rec, 10), u16(rec, 12), rec[0x0E]
        text = self.number_text(val, rec[0x10], rec[0x11], rec[0x12], rec[0x13] & 0x80)
        ims = [proj.image(lib, icon0 + "0123456789-.".index(c)) for c in text]
        if any(im is None for im in ims):
            return [f"artistic VP {u16(rec, 6):04X}: icons {lib}.icl #{icon0}.. missing"]
        width = sum(im.width for im in ims)
        if rec[0x13] & 0x01:                                    # right aligned: x is the top-right corner
            x -= width
        x0 = x
        for im in ims:
            img.paste(im, (x, y))
            x += im.width
        if overlay:
            ImageDraw.Draw(img).rectangle((x0, y, x - 1, y + max(im.height for im in ims) - 1), outline=(255, 0, 255))
        return [f"artistic VP {u16(rec, 6):04X} runs off screen"] if x0 < 0 or x > self.W else []

    @staticmethod
    def format_number(vp_val, rec):
        n_int, n_dot, vtype = rec[0x11], rec[0x12], rec[0x13]
        v = vp_val
        if vtype == 0:
            v = v - 0x10000 if v & 0x8000 else v
        elif vtype == 2:
            v = v >> 8
        elif vtype == 3:
            v = v & 0xFF
        neg = v < 0
        digits = str(abs(v)).rjust(n_dot + 1, "0")
        ip, dp = (digits[:-n_dot], digits[-n_dot:]) if n_dot else (digits, "")
        ip = ip[-n_int:] if n_int else ip                       # device shows only n_int integer digits
        if rec[0x10] & 0x40:                                     # show leading zeros
            ip = ip.rjust(n_int, "0")
        s = ("-" if neg else "") + ip + ("." + dp if n_dot else "")
        unit = bytes(rec[0x15:0x15 + rec[0x14]]).decode("ascii", "replace")
        return s + unit

    def render(self, proj, page, vp, pressed=None, overlay=False):
        bg = proj.image(proj.bg_icl, page)
        img = bg.copy() if bg else Image.new("RGB", (self.W, self.H), (40, 40, 40))
        if pressed and pressed.get("on") is not None:            # press effect: region from Pic_On page
            src = proj.image(proj.bg_icl, pressed["on"])
            if src:
                img.paste(src.crop(pressed["area"]), pressed["area"][:2])
        d = ImageDraw.Draw(img)
        notes = []
        for rec in proj.show.get(page, []):
            typ, vpa = rec[1], u16(rec, 6)
            val = vp.get(vpa, 0)
            if typ == 0x00:                                       # variable icon
                x, y, vmin, vmax, imin, imax = (u16(rec, o) for o in (8, 10, 12, 14, 16, 18))
                lib, mode = rec[0x14], rec[0x15]
                if vmin <= val <= vmax:
                    icon = imin + (val - vmin)
                    im = proj.image(lib, icon)
                    if im is None:
                        notes.append(f"icon {lib}.icl #{icon} missing")
                    else:
                        img.paste(im, (x, y))
                        if overlay:
                            d.rectangle((x, y, x + im.width - 1, y + im.height - 1), outline=(0, 255, 255))
            elif typ == 0x03:                                     # artistic variable (icon digits)
                notes += self.draw_art(proj, img, rec, val, overlay)
            elif typ == 0x10:                                     # data variable
                x, y = u16(rec, 8), u16(rec, 10)
                text = self.format_number(val, rec)
                box = self.draw_text(img, (x, y), text, rec[0x0F], rgb565(u16(rec, 12)))
                if overlay:
                    d.rectangle(box, outline=(255, 0, 255))
                    d.text((box[0], box[1] - 12), f"VP {vpa:04X} font {rec[0x0F]}", fill=(255, 0, 255))
            elif typ == 0x11:                                     # text display (ASCII only here)
                x, y = u16(rec, 8), u16(rec, 10)
                n = u16(rec, 0x16)
                raw = b"".join(vp.get(vpa + i, 0).to_bytes(2, "big") for i in range((n + 1) // 2))
                text = raw.split(b"\0")[0].split(b"\xff")[0].decode("ascii", "replace")
                box = self.draw_text(img, (x, y), text, rec[0x1A], rgb565(u16(rec, 12)))
                if overlay:
                    d.rectangle(box, outline=(255, 0, 255))
            else:
                x, y = u16(rec, 8), u16(rec, 10)
                d.rectangle((x, y, x + 60, y + 20), outline=(255, 0, 0))
                d.text((x + 2, y + 4), f"type {typ:02X}", fill=(255, 0, 0))
                notes.append(f"display type 0x{typ:02X} not emulated")
        if overlay:
            for t in proj.touch:
                if t["page"] == page:
                    d.rectangle(t["area"], outline=(255, 255, 0))
        for i, (x, y, w, h) in enumerate([]):
            pass
        offscreen = [r for r in proj.show.get(page, []) if r[1] == 0x10 and
                     self.draw_text(Image.new("RGB", (1, 1)), (u16(r, 8), u16(r, 10)),
                                    self.format_number(vp.get(u16(r, 6), 0), r), r[0x0F], 0)[2] > self.W]
        notes += [f"VP {u16(r, 6):04X} runs past the right edge" for r in offscreen]
        return img, notes


# ------------------------------------------------------------------ app

class App:
    def __init__(self, args):
        self.args = args
        self.proj = Project(Path(args.folder), args.bg_icl)
        W, H = map(int, args.size.lower().split("x"))
        self.r = Renderer((W, H), args.char_w, args.char_h)
        self.scale = args.scale
        self.vp = dict(self.proj.init)
        self.page = self.proj.pages()[0] if self.proj.pages() else 0
        self.pressed, self.repeat_job = None, None
        self.stamp = self.proj.stamp()

        self.root = tk.Tk()
        self.root.title(f"dwinemu - {args.folder}")
        self.canvas = tk.Canvas(self.root, width=int(W * self.scale), height=int(H * self.scale),
                                highlightthickness=0, bg="black")
        self.canvas.grid(row=0, column=0, rowspan=3, sticky="nw")
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        side = ttk.Frame(self.root, padding=6)
        side.grid(row=0, column=1, sticky="nsew")
        bar = ttk.Frame(side)
        bar.pack(fill="x")
        ttk.Button(bar, text="< page", command=lambda: self.goto(-1)).pack(side="left")
        ttk.Button(bar, text="page >", command=lambda: self.goto(+1)).pack(side="left")
        self.overlay = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="outlines", variable=self.overlay, command=self.redraw).pack(side="left", padx=6)
        ttk.Button(bar, text="reset VPs", command=self.reset_vps).pack(side="left")
        self.page_lbl = ttk.Label(side, text="")
        self.page_lbl.pack(anchor="w", pady=(6, 0))

        ttk.Label(side, text="Variables (double-click to edit = simulate MCU write)").pack(anchor="w", pady=(8, 0))
        self.tree = ttk.Treeview(side, columns=("vp", "val", "dec"), show="headings", height=12)
        for c, w in (("vp", 70), ("val", 70), ("dec", 70)):
            self.tree.heading(c, text={"vp": "VP", "val": "hex", "dec": "dec"}[c])
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="x")
        self.tree.bind("<Double-1>", self.edit_vp)

        ttk.Label(side, text="UART frames the display would send / notes").pack(anchor="w", pady=(8, 0))
        self.log = tk.Text(side, width=52, height=14, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.redraw()
        for w in self.proj.warnings:
            self.say("WARN " + w)
        self.root.after(1000, self.watch)

    # -- helpers
    def say(self, s):
        self.log.insert("end", s + "\n")
        self.log.see("end")

    def vps_in_use(self):
        s = {t["vp"] for t in self.proj.touch if "vp" in t}
        for recs in self.proj.show.values():
            s |= {u16(r, 6) for r in recs}
        return sorted(s)

    def redraw(self):
        img, notes = self.r.render(self.proj, self.page, self.vp, self.pressed, self.overlay.get())
        if self.scale != 1:
            img = img.resize((int(img.width * self.scale), int(img.height * self.scale)), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.page_lbl.config(text=f"page {self.page}   pages: {self.proj.pages()}")
        self.tree.delete(*self.tree.get_children())
        for a in self.vps_in_use():
            v = self.vp.get(a, 0)
            self.tree.insert("", "end", iid=str(a), values=(f"{a:04X}", f"{v:04X}", v))
        for n in notes:
            if n not in getattr(self, "_seen", set()):
                self.say("NOTE " + n)
                self._seen = getattr(self, "_seen", set()) | {n}

    def goto(self, step):
        pages = self.proj.pages()
        if pages:
            i = pages.index(self.page) if self.page in pages else 0
            self.page = pages[(i + step) % len(pages)]
            self.redraw()

    def reset_vps(self):
        self.vp = dict(self.proj.init)
        self.redraw()

    def edit_vp(self, _e):
        sel = self.tree.selection()
        if not sel:
            return
        a = int(sel[0])
        win = tk.Toplevel(self.root)
        win.title(f"VP {a:04X}")
        e = ttk.Entry(win)
        e.insert(0, str(self.vp.get(a, 0)))
        e.pack(padx=8, pady=8)
        e.focus()

        def ok(_=None):
            try:
                self.vp[a] = int(e.get(), 0) & 0xFFFF
                self.say(f"MCU -> 5A A5 05 82 {a >> 8:02X} {a & 0xFF:02X} {self.vp[a] >> 8:02X} {self.vp[a] & 0xFF:02X}")
            except ValueError:
                pass
            win.destroy()
            self.redraw()
        e.bind("<Return>", ok)

    def upload(self, a):
        v = self.vp.get(a, 0)
        self.say(f"5A A5 06 83 {a >> 8:02X} {a & 0xFF:02X} 01 {v >> 8:02X} {v & 0xFF:02X}   (VP {a:04X} = {v})")

    # -- touch
    def hit(self, x, y):
        for t in self.proj.touch:                     # file order; first match wins (unverified on device)
            xs, ys, xe, ye = t["area"]
            if t["page"] == self.page and xs <= x < xe and ys <= y < ye:
                return t
        return None

    def apply(self, t):
        if t["type"] == 0x02:
            a = t["vp"]
            v = self.vp.get(a, 0)
            v = v - 0x10000 if v & 0x8000 else v
            v = v + t["step"] if t["inc"] else v - t["step"]
            if v > t["vmax"]:
                v = t["vmin"] if t["wrap"] else t["vmax"]
            if v < t["vmin"]:
                v = t["vmax"] if t["wrap"] else t["vmin"]
            self.vp[a] = v & 0xFFFF
            if t["upload"]:
                self.upload(a)
        elif t["type"] == 0x05:
            self.vp[t["vp"]] = t["key"]
            if t["upload"]:
                self.upload(t["vp"])
        self.redraw()

    def on_press(self, e):
        x, y = int(e.x / self.scale), int(e.y / self.scale)
        t = self.hit(x, y)
        if not t:
            return
        self.pressed = t
        self.apply(t) if t["type"] in (0x02, 0x05) else self.redraw()
        if t["type"] == 0x02 and not t.get("once"):
            self.repeat_job = self.root.after(500, self.repeat)

    def repeat(self):
        if self.pressed:
            self.apply(self.pressed)
            self.repeat_job = self.root.after(150, self.repeat)

    def on_release(self, _e):
        t, self.pressed = self.pressed, None
        if self.repeat_job:
            self.root.after_cancel(self.repeat_job)
            self.repeat_job = None
        if t and t["next"] is not None:
            self.page = t["next"]
        self.redraw()

    def watch(self):
        try:
            s = self.proj.stamp()
            if s != self.stamp:
                self.stamp = s
                self.proj.load()
                self.say("reloaded " + str(self.proj.folder))
                for w in self.proj.warnings:
                    self.say("WARN " + w)
                self.redraw()
        except OSError:
            pass
        self.root.after(1000, self.watch)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="DWIN_SET folder")
    ap.add_argument("--size", default="1024x600")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--bg-icl", type=int, default=32, help="ICL file number holding the pages (CFG 0x08)")
    ap.add_argument("--char-w", type=float, default=1.0, help="0# font: char width = Font_X * this")
    ap.add_argument("--char-h", type=float, default=2.0, help="0# font: char height = Font_X * this")
    ap.add_argument("--snapshot", help="render all pages to PNG files with this prefix and exit")
    a = ap.parse_args()
    if a.snapshot:
        proj = Project(Path(a.folder), a.bg_icl)
        r = Renderer(tuple(map(int, a.size.lower().split("x"))), a.char_w, a.char_h)
        for p in proj.pages():
            img, notes = r.render(proj, p, dict(proj.init), overlay=True)
            img.save(f"{a.snapshot}{p}.png")
            print(f"page {p}: {a.snapshot}{p}.png", *notes, sep="\n  ")
        print(*proj.warnings, sep="\n")
        return
    App(a).root.mainloop()


if __name__ == "__main__":
    main()
