"""Font and icon lookup for rendering. Bundled: Inter (OFL) and Tabler Icons (MIT); system/asset TTFs also work."""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

DATA = Path(__file__).resolve().parents[1] / "data"
_WEIGHT_FILE = {"light": "Inter-Light.ttf", "regular": "Inter-Regular.ttf", "medium": "Inter-Medium.ttf",
                "semibold": "Inter-SemiBold.ttf", "bold": "Inter-Bold.ttf"}


def _system_font_dirs() -> list[Path]:
    if sys.platform == "win32":
        return [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"]
    if sys.platform == "darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"]


@lru_cache(maxsize=256)
def font_path(name: str | None, weight: str = "regular", base: str | None = None) -> str:
    """Resolve a font name to a TTF path.

    'Inter' / None -> bundled Inter in the requested weight; 'assets/x.ttf' -> relative to `base` (project folder);
    any other name -> a system font file whose name contains it (e.g. 'Roboto', 'segoeui')."""
    if not name or name.lower().startswith("inter"):
        if name and name.lower() != "inter":                 # "Inter Bold" style names
            weight = name.split(maxsplit=1)[1].lower().replace(" ", "") if " " in name else weight
        return str(DATA / "fonts" / _WEIGHT_FILE.get(weight, "Inter-Regular.ttf"))
    p = Path(name)
    if base and not p.is_absolute() and (Path(base) / p).exists():
        return str(Path(base) / p)
    if p.exists():
        return str(p)
    key = name.lower().replace(" ", "")
    for d in _system_font_dirs():
        if d.exists():
            for f in sorted(d.rglob("*.tt[fc]")):
                if key in f.stem.lower().replace(" ", ""):
                    return str(f)
    return str(DATA / "fonts" / _WEIGHT_FILE.get(weight, "Inter-Regular.ttf"))


@lru_cache(maxsize=512)
def load_font(name: str | None, size: int, weight: str = "regular", base: str | None = None):
    return ImageFont.truetype(font_path(name, weight, base), size)


@lru_cache(maxsize=1)
def icon_names() -> dict[str, int]:
    return json.loads((DATA / "icons" / "tabler-icons.json").read_text())


ALIASES = {"lightbulb": "bulb", "light": "bulb", "thermometer": "temperature", "temp": "temperature",
           "gear": "settings", "power": "power", "lock": "lock", "unlock": "lock-open", "fan": "propeller",
           "tv": "device-tv", "door": "door", "alarm": "alarm", "shield": "shield", "water": "droplet",
           "humidity": "droplet", "sun": "sun", "moon": "moon", "music": "music", "play": "player-play",
           "pause": "player-pause", "stop": "player-stop", "next": "player-skip-forward",
           "prev": "player-skip-back", "plus": "plus", "minus": "minus", "back": "arrow-left", "home": "home",
           "battery": "battery", "plug": "plug", "car": "car", "coffee": "coffee", "cloud": "cloud",
           "user": "user", "check": "check", "close": "x", "warning": "alert-triangle", "info": "info-circle"}


def icon_char(name: str) -> str:
    names = icon_names()
    key = ALIASES.get(name, name)
    if key not in names:
        close = [n for n in names if key in n][:8]
        raise KeyError(f"unknown icon {name!r}" + (f"; did you mean {close}?" if close else ""))
    return chr(names[key])


def icon_font(size: int):
    return ImageFont.truetype(str(DATA / "icons" / "tabler-icons.ttf"), size)


def search_icons(query: str, limit: int = 30) -> list[str]:
    q = query.lower()
    hits = [n for n in icon_names() if q in n]
    hits.sort(key=lambda n: (not n.startswith(q), len(n)))
    return hits[:limit]
