"""Rebuild the bundled third-party assets in src/opendgus/data (fonts + icon font) from their upstream releases.

    python tools/fetch_assets.py

- Inter 4.1 (SIL Open Font License 1.1)  https://github.com/rsms/inter
- Tabler Icons webfont 3.19.0 (MIT)       https://tabler.io/icons
"""
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "src" / "opendgus" / "data"
INTER = "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
TABLER = "https://unpkg.com/@tabler/icons-webfont@3.19.0/"
INTER_FILES = ["Inter-Light.ttf", "Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]


def get(url: str) -> bytes:
    with urllib.request.urlopen(url) as r:
        return r.read()


def main() -> None:
    fonts, icons = DATA / "fonts", DATA / "icons"
    fonts.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)

    z = zipfile.ZipFile(io.BytesIO(get(INTER)))
    for name in z.namelist():
        base = name.rsplit("/", 1)[-1]
        if base in INTER_FILES and "/ttf/" in name:
            (fonts / base).write_bytes(z.read(name))
        elif base == "LICENSE.txt":
            (fonts / "LICENSE-Inter.txt").write_bytes(z.read(name))

    (icons / "tabler-icons.ttf").write_bytes(get(TABLER + "dist/fonts/tabler-icons.ttf"))
    (icons / "LICENSE-tabler.txt").write_bytes(get(TABLER + "LICENSE"))
    css = get(TABLER + "dist/tabler-icons.css").decode("utf-8")
    pat = re.compile(r'\.ti-([a-z0-9-]+):before\s*\{\s*content:\s*"\\([0-9a-fA-F]+)"')
    names = {n: int(c, 16) for n, c in pat.findall(css)}
    (icons / "tabler-icons.json").write_text(json.dumps(names, separators=(",", ":"), sort_keys=True))
    print(f"fonts: {sorted(p.name for p in fonts.glob('*.ttf'))}\nicons: {len(names)} names")


if __name__ == "__main__":
    main()
