"""Display profiles: resolution, flash, CPU and the derived build limits for DWIN T5L modules.

Facts come from DWIN product pages and the T5L DGUS II / COF / TA guides (see docs/display-profiles.md).
`verified` marks a profile whose key facts come from a DWIN source; others are inferred from the part number.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

# Usable JPEG bytes per picture inside an ICL (ICLGenerator IclFileBuilder limits)
JPEG_LIMIT = {"T5L0": 253942, "T5L1": 253942, "T5L2": 778230}


@dataclass(frozen=True)
class DisplayProfile:
    id: str
    name: str
    width: int                  # as designed (after rotation)
    height: int
    diagonal: float = 0.0
    touch: str = "C"            # C capacitive, R resistive, N none
    flash_mb: int = 16
    cpu: str = "T5L1"
    series: str = ""
    verified: bool = False
    notes: str = ""

    @property
    def background_icl(self) -> int:
        return 32 if self.flash_mb >= 16 else 23

    @property
    def slots(self) -> int:
        return self.flash_mb * 4          # 256 KB per file slot

    @property
    def jpeg_limit(self) -> int:
        return JPEG_LIMIT.get(self.cpu, JPEG_LIMIT["T5L1"])

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(background_icl=self.background_icl, slots=self.slots, jpeg_limit=self.jpeg_limit)
        return d


def _p(id, w, h, diag, touch, flash, cpu, series, verified=False, notes=""):
    return DisplayProfile(id, f"{id} ({w}x{h}, {diag}\")", w, h, diag, touch, flash, cpu, series, verified, notes)


PROFILES: dict[str, DisplayProfile] = {p.id: p for p in [
    _p("DMG48480C021_03W", 480, 480, 2.1, "C", 16, "T5L1", "round", True),
    _p("DMG48480C021_13W", 480, 480, 2.1, "C", 16, "T5L0", "round + rotary knob", False),
    _p("DMG40400C016_03W", 400, 400, 1.6, "C", 8, "T5L0", "round COF"),
    _p("DMG32240F028_01W", 320, 240, 2.8, "R", 8, "T5L0", "COF", True),
    _p("DMG48480F040_01W", 480, 480, 4.0, "C", 8, "T5L0", "COF", True),
    _p("DMG48270F043_01W", 480, 272, 4.3, "C", 8, "T5L0", "COF"),
    _p("DMG85480F050_01W", 480, 854, 5.0, "N", 8, "T5L0", "COF portrait"),
    _p("DMG10600F070_01W", 1024, 600, 7.0, "C", 16, "T5L0", "COF", True),
    _p("DMG48320C035_03W", 480, 320, 3.5, "C", 16, "T5L1", "commercial", True),
    _p("DMG48480C040_03W", 480, 480, 4.0, "C", 16, "T5L1", "commercial", True),
    _p("DMG80480C043_03W", 800, 480, 4.3, "C", 16, "T5L1", "commercial"),
    _p("DMG85480C050_03W", 480, 854, 5.0, "C", 16, "T5L2", "commercial portrait", True),
    _p("DMG80480C070_03W", 800, 480, 7.0, "C", 16, "T5L1", "commercial", True),
    _p("DMG80480C070_15W", 800, 480, 7.0, "R", 8, "T5L0", "commercial", True),
    _p("DMG10600C070_03W", 1024, 600, 7.0, "C", 16, "T5L2", "commercial", True),
    _p("DMG12800C070_03W", 800, 1280, 7.0, "C", 16, "T5L2", "commercial portrait", True),
    _p("DMG80600C080_01W", 800, 600, 8.0, "C", 16, "T5L1", "commercial", True),
    _p("DMG10768C080_03W", 1024, 768, 8.0, "C", 16, "T5L2", "commercial", True),
    _p("DMG12800C080_03W", 1280, 800, 8.0, "C", 16, "T5L2", "commercial"),
    _p("DMG10600C101_03W", 1024, 600, 10.1, "C", 16, "T5L2", "commercial", True),
    _p("DMG12720C101_03W", 1280, 720, 10.1, "C", 16, "T5L2", "commercial"),
    _p("DMG13768C156_03W", 1366, 768, 15.6, "C", 16, "T5L2", "commercial"),
    _p("EKT043", 480, 272, 4.3, "C", 16, "T5L1", "evaluation board", True),
    _p("EKT070A", 800, 480, 7.0, "C", 16, "T5L0", "evaluation board", True),
    _p("EKT070C", 1024, 600, 7.0, "C", 16, "T5L2", "evaluation board", True),
    _p("EKT070D", 1280, 800, 7.0, "C", 16, "T5L2", "evaluation board", True),
]}

COMMON_RESOLUTIONS = [(240, 240), (320, 240), (480, 272), (480, 320), (480, 480), (640, 480), (800, 480),
                      (800, 600), (854, 480), (1024, 600), (1024, 768), (1280, 720), (1280, 800), (1366, 768)]

_W = {"24": 240, "32": 320, "40": 400, "48": 480, "64": 640, "72": 720, "80": 800, "85": 854, "10": 1024,
      "12": 1280, "13": 1366, "14": 1440, "19": 1920}
_H = {"240": 240, "272": 272, "320": 320, "400": 400, "480": 480, "600": 600, "720": 720, "768": 768,
      "800": 800, "108": 1080}
_GRADE = {"M": "simple", "L": "simple", "C": "commercial", "T": "industrial", "K": "medical", "Q": "automotive",
          "S": "military", "F": "COF / integrated"}


def decode_part_number(pn: str) -> DisplayProfile:
    """Best-effort decode of a DWIN part number such as DMG10600C070_03WTC.

    Native panels like 12800 (800x1280) or 85480 (480x854) are portrait: the code lists the long side first."""
    s = pn.strip().upper()
    if s in PROFILES:
        return PROFILES[s]
    base = re.sub(r"(TC|TR|N|T)$", "", s.split("_")[0] + ("_" + s.split("_")[1] if "_" in s else ""))
    for k, p in PROFILES.items():
        if s.startswith(k) or base.startswith(k):
            return p
    m = re.match(r"DM[GT](\d{2})(\d{2,3})([A-Z])(\d{3})", s)
    if not m:
        raise ValueError(f"not a DWIN T5L part number: {pn}")
    wc, hc, grade, diag = m.groups()
    if wc not in _W or hc not in _H:
        raise ValueError(f"unknown resolution code {wc}{hc} in {pn}")
    w, h = _W[wc], _H[hc]
    if (wc, hc) in (("12", "800"), ("85", "480")):          # long-side-first portrait panels
        w, h = h, w
    suffix = s.split("_")[1] if "_" in s else ""
    touch = "C" if suffix.endswith("TC") else "R" if suffix.endswith("TR") else "N" if suffix.endswith("N") else "C"
    flash = 8 if grade == "F" and w * h <= 480 * 854 else 16
    cpu = "T5L0" if grade == "F" else ("T5L1" if w * h <= 800 * 600 else "T5L2")
    return DisplayProfile(s, f"{s} ({w}x{h}, {int(diag) / 10}\")", w, h, int(diag) / 10, touch, flash, cpu,
                          _GRADE.get(grade, grade), False, "decoded from part number; check flash/CPU")


def custom(width: int, height: int, flash_mb: int = 16, cpu: str | None = None) -> DisplayProfile:
    cpu = cpu or ("T5L1" if width * height <= 800 * 600 else "T5L2")
    return DisplayProfile(f"custom_{width}x{height}", f"Custom {width}x{height}", width, height, 0.0, "C",
                          flash_mb, cpu, "custom")
