"""dwinemu - desktop emulator for DWIN T5L (DGUS II) projects.

Reads the same DWIN_SET folder that goes onto the display (ICL images, 13.bin touch, 14.bin display,
22.bin initial values, T5LCFG.CFG), draws the pages and lets you click them like the touch screen.

    opendgus-emu path/to/DWIN_SET [--scale 1.0] [--snapshot PREFIX]

All the device behaviour lives in opendgus.emulator.engine.Device (headless, also used by the MCP server and
tests); this module is only the Tk front end. The folder is re-read automatically when its files change
(e.g. after a rebuild).
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from .engine import Device

MCU_FRAME = "MCU -> 5A A5 05 82 {a:04X} {v:04X}"


class App:
    def __init__(self, args):
        import tkinter as tk
        from tkinter import ttk
        from PIL import ImageTk  # noqa: F401  (fail early without Tk support)

        self.tk, self.ttk = tk, ttk
        self.args = args
        self.dev = make_device(args)
        self.scale = args.scale
        self.stamp = self.dev.stamp()
        self.seen_uploads = self.seen_events = 0
        self._seen_notes: set[str] = set()
        self._last = time.monotonic()

        W, H = self.dev.width, self.dev.height
        self.root = tk.Tk()
        self.root.title(f"dwinemu - {args.folder}")
        self.canvas = tk.Canvas(self.root, width=int(W * self.scale), height=int(H * self.scale),
                                highlightthickness=0, bg="black")
        self.canvas.grid(row=0, column=0, rowspan=3, sticky="nw")
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        side = ttk.Frame(self.root, padding=6)
        side.grid(row=0, column=1, sticky="nsew")
        bar = ttk.Frame(side)
        bar.pack(fill="x")
        ttk.Button(bar, text="< page", command=lambda: self.goto(-1)).pack(side="left")
        ttk.Button(bar, text="page >", command=lambda: self.goto(+1)).pack(side="left")
        self.overlay = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="outlines", variable=self.overlay, command=self.redraw).pack(side="left", padx=6)
        ttk.Button(bar, text="reset", command=self.reset).pack(side="left")
        self.page_lbl = ttk.Label(side, text="")
        self.page_lbl.pack(anchor="w", pady=(6, 0))
        self.input_bar = ttk.Frame(side)
        self.input_bar.pack(fill="x", pady=(4, 0))
        self.input_lbl = ttk.Label(self.input_bar, text="")
        self.input_lbl.pack(side="left")
        self.input_entry = ttk.Entry(self.input_bar, width=14)
        self.input_entry.bind("<Return>", self.on_enter_value)

        ttk.Label(side, text="Variables (double-click to edit = simulate MCU write)").pack(anchor="w", pady=(8, 0))
        self.tree = ttk.Treeview(side, columns=("name", "vp", "val", "dec"), show="headings", height=12)
        for c, w in (("name", 110), ("vp", 60), ("val", 60), ("dec", 70)):
            self.tree.heading(c, text={"name": "name", "vp": "VP", "val": "hex", "dec": "dec"}[c])
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="x")
        self.tree.bind("<Double-1>", self.edit_vp)

        ttk.Label(side, text="UART frames the display sends / events / notes").pack(anchor="w", pady=(8, 0))
        self.log = tk.Text(side, width=60, height=14, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        for w in self.dev.warnings:
            self.say("WARN " + w)
        self.redraw()
        self.root.after(50, self.loop)
        self.root.after(1000, self.watch)

    # -- helpers
    def say(self, s):
        self.log.insert("end", s + "\n")
        self.log.see("end")

    def vps_in_use(self):
        names = {a: n for n, a in self.dev.variables.items()}
        s = set(names)
        for t in self.dev.touch:
            if "vp" in t.v:
                s.add(t.v["vp"])
        for recs in self.dev.show.values():
            s |= {c.v["vp"] for c in recs if "vp" in c.v}
        return [(a, names.get(a, "")) for a in sorted(s)]

    def flush_log(self):
        for u in self.dev.uploads[self.seen_uploads:]:
            self.say(f"{u['frame'].hex(' ').upper()}   (VP {u['vp']:04X} = {u['value']})")
        self.seen_uploads = len(self.dev.uploads)
        for e in self.dev.events[self.seen_events:]:
            self.say("EVENT " + ", ".join(f"{k}={v}" for k, v in e.items() if k != "ms"))
        self.seen_events = len(self.dev.events)
        for n in self.dev.notes:
            if n not in self._seen_notes:
                self._seen_notes.add(n)
                self.say("NOTE " + n)

    def redraw(self):
        from PIL import Image, ImageTk
        img = self.dev.render(outlines=self.overlay.get())
        if self.scale != 1:
            img = img.resize((int(img.width * self.scale), int(img.height * self.scale)), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.page_lbl.config(text=f"page {self.dev.page}   pages: {self.dev.pages()}")
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for a, name in self.vps_in_use():
            v = self.dev.vp[a]
            self.tree.insert("", "end", iid=str(a), values=(name, f"{a:04X}", f"{v:04X}", v - 0x10000 if v & 0x8000
                                                            else v))
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel)
        p = self.dev.pending_input
        if p:
            self.input_lbl.config(text=f"{p['kind']} VP {p['vp'] or 0:04X}: type a value + Enter")
            self.input_entry.pack(side="left", padx=4)
        else:
            self.input_lbl.config(text="")
            self.input_entry.pack_forget()
        self.flush_log()

    def goto(self, step):
        pages = self.dev.pages()
        if pages:
            i = pages.index(self.dev.page) if self.dev.page in pages else 0
            self.dev.set_page(pages[(i + step) % len(pages)])
            self.redraw()

    def reset(self):
        self.dev.reset()
        self.redraw()

    def edit_vp(self, _e):
        tk, ttk = self.tk, self.ttk
        sel = self.tree.selection()
        if not sel:
            return
        a = int(sel[0])
        win = tk.Toplevel(self.root)
        win.title(f"VP {a:04X}")
        e = ttk.Entry(win)
        e.insert(0, str(self.dev.vp[a]))
        e.pack(padx=8, pady=8)
        e.focus()

        def ok(_=None):
            try:
                v = int(e.get(), 0) & 0xFFFF
                self.dev.write_vp(a, v)
                self.say(MCU_FRAME.format(a=a, v=v))
            except ValueError:
                pass
            win.destroy()
            self.redraw()
        e.bind("<Return>", ok)

    def on_enter_value(self, _e):
        txt = self.input_entry.get()
        try:
            self.dev.enter_value(txt)
        except (ValueError, RuntimeError) as ex:
            self.say(f"input rejected: {ex}")
        self.input_entry.delete(0, "end")
        self.redraw()

    # -- touch
    def xy(self, e):
        return int(e.x / self.scale), int(e.y / self.scale)

    def on_press(self, e):
        self.dev.press(*self.xy(e))
        self.redraw()

    def on_move(self, e):
        self.dev.move(*self.xy(e))
        if self.dev.pressed and self.dev.pressed["ctl"] is not None and \
                self.dev.pressed["ctl"].key in ("drag_adjust", "rotate_adjust"):
            self.redraw()

    def on_release(self, e):
        self.dev.move(*self.xy(e))
        self.dev.release()
        self.redraw()

    def loop(self):
        now = time.monotonic()
        ms = int((now - self._last) * 1000)
        self._last = now
        before = (len(self.dev.uploads), self.dev.page)
        self.dev.tick(ms)
        if self.dev.pressed or self.dev.animated() or (len(self.dev.uploads), self.dev.page) != before:
            self.redraw()
        self.root.after(50, self.loop)

    def watch(self):
        try:
            s = self.dev.stamp()
            if s != self.stamp:
                self.stamp = s
                self.dev.reload()
                self.say("reloaded " + str(self.dev.folder))
                for w in self.dev.warnings:
                    self.say("WARN " + w)
                self.redraw()
        except OSError:
            pass
        self.root.after(1000, self.watch)


def make_device(a) -> Device:
    W = H = None
    if a.size:
        W, H = map(int, a.size.lower().split("x"))
    return Device.from_folder(Path(a.folder), W, H, bg_lib=a.bg_icl)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="DWIN_SET folder (or a project folder containing build/DWIN_SET)")
    ap.add_argument("--size", default=None, help="WIDTHxHEIGHT (default: from the page images)")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--bg-icl", type=int, default=None, help="ICL file number holding the pages (default: CFG)")
    ap.add_argument("--snapshot", help="render all pages to PNG files with this prefix and exit")
    a = ap.parse_args(argv)
    if a.snapshot:
        dev = make_device(a)
        for p in dev.pages():
            dev.set_page(p)
            dev.render(outlines=True).save(f"{a.snapshot}{p}.png")
            print(f"page {p}: {a.snapshot}{p}.png")
        print(*(["notes:"] + dev.notes if dev.notes else []), sep="\n  ")
        print(*dev.warnings, sep="\n")
        return
    App(a).root.mainloop()


if __name__ == "__main__":
    main()
