"""Screensaver pages: a splash image or an animated GIF shown by the controller after an idle time.

    apply(project, folder, "assets/splash.gif", timeout_s=120)

The screensaver is one page whose background is the first frame. Animations add one page per further frame
(consecutive ids, as DGUS image_animation needs) and an image_animation control on the screensaver page. A
full-screen basic_touch leaves the page even without a controller (to wake_page, or the home page); a controller
running the OpenDGUS idle manager returns to the page that was showing instead.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps, ImageSequence

from .model import Background, Control, Page, Project, Screensaver

MAX_FRAMES = 30
NAME = "Screensaver"


def _frames(path: Path, size: tuple[int, int], max_frames: int) -> tuple[list[Image.Image], Optional[int]]:
    """Frames scaled to cover the screen, and the GIF's frame time (ms) if it has one."""
    im = Image.open(path)
    n = getattr(im, "n_frames", 1)
    step = max(1, -(-n // max_frames))                  # keep long GIFs under the limit by skipping frames
    out, dur = [], None
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        if i % step:
            continue
        dur = dur or fr.info.get("duration")
        out.append(ImageOps.fit(fr.convert("RGB"), size, Image.LANCZOS))
    return out[:max_frames], (dur * step if dur else None)


def remove(project: Project) -> Project:
    ss = project.screensaver
    gone = {ss.page, *ss.frame_pages} - {None}
    project.pages = [p for p in project.pages if p.id not in gone]
    project.screensaver = Screensaver(timeout_s=ss.timeout_s, wake_page=ss.wake_page, brightness=ss.brightness)
    return project


def apply(project: Project, folder: Path, source: str, timeout_s: Optional[int] = None,
          frame_ms: Optional[int] = None, wake_page: Optional[int] = None, brightness: Optional[int] = None,
          max_frames: int = MAX_FRAMES) -> Project:
    """(Re)build the screensaver from an image or animated GIF (path relative to the project folder or absolute;
    files outside the folder are copied to assets/)."""
    folder = Path(folder)
    src = Path(source)
    full = src if src.is_absolute() else folder / src
    if not full.exists():
        raise FileNotFoundError(f"{source} not found")
    old = project.screensaver
    remove(project)
    W, H = project.display.width, project.display.height
    frames, gif_ms = _frames(full, (W, H), max_frames)
    out = folder / "assets" / "screensaver"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("frame_*.png"):
        f.unlink()
    rels = []
    for i, fr in enumerate(frames):
        name = f"frame_{i:02d}.png"
        fr.save(out / name)
        rels.append(f"assets/screensaver/{name}")
    first = max((p.id for p in project.pages), default=-1) + 1
    ids = list(range(first, first + len(rels)))
    home = min((p.id for p in project.pages), default=0)
    wake = wake_page if wake_page is not None else old.wake_page
    ms = frame_ms or gif_ms or old.frame_ms
    ms = max(8, min(2040, ms))
    controls = [Control(type="raw:basic_touch", x=0, y=0, w=W, h=H,
                        props={"pic_next": wake if wake is not None else home})]
    if len(ids) > 1:
        controls.insert(0, Control(type="raw:image_animation", x=0, y=0, w=W, h=H,
                                   props={"pic_begin": ids[0], "pic_end": ids[-1], "frame_time": max(1, round(ms / 8))}))
    project.pages.append(Page(id=ids[0], name=NAME, background=Background(color=None, image=rels[0]),
                              controls=controls))
    for i, (pid, rel) in enumerate(zip(ids[1:], rels[1:]), start=2):
        project.pages.append(Page(id=pid, name=f"{NAME} frame {i}", background=Background(color=None, image=rel)))
    try:
        rel_src = full.resolve().relative_to(folder.resolve()).as_posix()
    except ValueError:                                   # keep the project self-contained
        copy = out / f"source{full.suffix.lower()}"
        shutil.copyfile(full, copy)
        rel_src = f"assets/screensaver/{copy.name}"
    project.screensaver = Screensaver(
        enabled=True, timeout_s=timeout_s or old.timeout_s, page=ids[0], frame_pages=ids[1:], frame_ms=ms,
        source=rel_src, wake_page=wake, brightness=brightness if brightness is not None else old.brightness)
    return project
