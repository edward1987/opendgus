from pathlib import Path
import shutil

from PIL import Image

from opendgus.compiler import compile_project
from opendgus.formats import controls as C
from opendgus.formats import spec as S
from opendgus.formats import specs as _specs  # noqa: F401
from opendgus.legacy_import import import_project
from opendgus.model import Project


def test_imports_background_and_supported_raw_controls(tmp_path):
    source, dest = tmp_path / "vendor", tmp_path / "new"
    (source / "DWIN_SET").mkdir(parents=True)
    source.joinpath("DWprj.hmi").write_text("[INIT]\nSCREENDSIZE=800X480\n[IMG]\n0=00_main.jpg\n")
    sample = Path(__file__).parents[1] / "vendor/tools/Terminal-Assistant_V6.0/Terminal Assistant_V6.0/DWprj.tft"
    shutil.copyfile(sample, source / "DWprj.tft")
    Image.new("RGB", (800, 480), "#202030").save(source / "DWIN_SET/00_main.jpg")
    touch = S.encode("return_key", screen=(800, 480), page=0, x1=10, y1=20, x2=110, y2=70,
                     vp=0x5000, key_code=5)
    (source / "DWIN_SET/13.bin").write_bytes(C.build_13([touch]))
    (source / "DWIN_SET/14.bin").write_bytes(C.build_14({0: []}))
    result = import_project(source, dest)
    project = Project.load(dest)
    assert result["pages"] == 1 and result["controls"] == 1
    assert project.pages[0].background.image == "assets/legacy_0_00_main.jpg"
    assert project.pages[0].controls[0].type == "raw:return_key"
    assert project.variables[0].vp == 0x5000
    compiled = compile_project(project, dest, write=False)
    assert compiled.ok, [str(issue) for issue in compiled.issues]
