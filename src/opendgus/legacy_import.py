"""Conservative import of DGUS V7.651 projects with an explicit loss report."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .formats import controls as C
from .formats import spec as S
from .formats import specs as _specs  # noqa: F401
from .formats.legacy_project import load_hmi, load_tft
from .model import Background, Control, Display, Page, Project, Variable


def import_project(source: Path, destination: Path) -> dict:
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not (source / "DWprj.hmi").is_file() or not (source / "DWprj.tft").is_file():
        raise ValueError("choose a DGUS project folder containing DWprj.hmi and DWprj.tft")
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("the new project folder must be separate from the DGUS source")
    if (destination / "project.json").exists():
        raise ValueError("destination already contains an OpenDGUS project")
    hmi = load_hmi(source / "DWprj.hmi")
    doc, _, _ = load_tft(source / "DWprj.tft")
    size = re.fullmatch(r"(\d+)[xX](\d+)", hmi.get("INIT", {}).get("SCREENDSIZE", ""))
    width, height = (int(size[1]), int(size[2])) if size else (int(doc.get("Width", 800)), int(doc.get("Height", 480)))
    if not 1 <= width <= 4096 or not 1 <= height <= 4096:
        raise ValueError("invalid legacy screen size")
    names = hmi.get("IMG", {})
    page_ids = sorted(int(k) for k in names if k.isdecimal())
    if not page_ids:
        page_ids = [0]
    project = Project(name=source.name, display=Display.custom(width, height), pages=[])
    report: list[str] = []
    assets: list[tuple[Path, Path]] = []
    for pid in page_ids:
        image_name = names.get(str(pid), "")
        page = Page(id=pid, name=Path(image_name).stem if image_name else f"Page {pid}")
        if image_name:
            image = source / "DWIN_SET" / image_name
            if image.is_file() and image.resolve().parent == (source / "DWIN_SET").resolve():
                target = Path("assets") / f"legacy_{pid}_{image.name}"
                page.background = Background(image=target.as_posix())
                assets.append((image, target))
            else:
                report.append(f"page {pid}: background image {image_name!r} was not found")
            tft = source / "TFT" / f"{image_name}.tft"
            if tft.is_file():
                try:
                    page_doc, _, _ = load_tft(tft)
                    items = (page_doc.get("Items") or {}).get("items", [])
                    if items:
                        report.append(f"page {pid}: {len(items)} editable vendor objects retained only in the background; review imported controls")
                except Exception as exc:
                    report.append(f"page {pid}: could not read editable objects ({exc})")
        project.pages.append(page)

    variables: dict[int, Variable] = {}

    def add_record(raw: bytes, pid_hint: int | None = None) -> None:
        try:
            key, values = S.decode(raw)
            spec = S.REGISTRY[key]
            if any(f.role in ("icon", "icon_lib") for f in spec.fields):
                raise ValueError("uses an external icon library")
            if any(f.role == "font" and int(values.get(f.name, 0)) != 0 for f in spec.fields):
                raise ValueError("uses an external font library")
            pid = values.get("page", pid_hint)
            page = project.page(pid)
            x = int(values.get("x1", values.get("x", 0)))
            y = int(values.get("y1", values.get("y", 0)))
            w = max(1, int(values.get("x2", x + 100)) - x)
            h = max(1, int(values.get("y2", y + 50)) - y)
            vp = values.get("vp")
            var = None
            if isinstance(vp, int) and 0x1000 <= vp < 0x8000:
                if vp not in variables:
                    text = key in {"text_input", "text_display", "qr_code", "scroll_text"}
                    length = max(16, min(255, int(values.get("text_len", values.get("vp_len_max", 32))))) if text else 16
                    variables[vp] = Variable(name=f"legacy_{vp:04x}", type="text" if text else "int16",
                                             vp=vp, init="" if text else 0, length=length)
                var = variables[vp].name
            control = Control(type=f"raw:{key}", x=x, y=y, w=w, h=h, var=var, props=values)
            page.controls.append(control)
        except Exception as exc:
            report.append(f"{pid_hint if pid_hint is not None else 'touch'}: skipped a control ({exc})")

    build = source / "DWIN_SET"
    if (build / "13.bin").is_file():
        for raw in C.parse_13((build / "13.bin").read_bytes()):
            if raw != b"\xff" * len(raw):
                add_record(raw)
    else:
        report.append("13.bin not found: touch controls could not be imported")
    if (build / "14.bin").is_file():
        try:
            for pid, records in C.parse_14((build / "14.bin").read_bytes()).items():
                for raw in records:
                    add_record(raw, pid)
        except Exception as exc:
            report.append(f"14.bin could not be read ({exc})")
    else:
        report.append("14.bin not found: display controls could not be imported")
    project.variables = list(variables.values())
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "assets").mkdir(exist_ok=True)
    for source_image, target in assets:
        shutil.copyfile(source_image, destination / target)
    project.save(destination)
    return {"folder": str(destination), "pages": len(project.pages),
            "controls": sum(len(page.controls) for page in project.pages), "issues": report}
