import pytest
from pydantic import ValidationError

from opendgus.model import Control, Display, Page, Project, Rect, Text, Theme, Variable


def test_roundtrip_and_ids(tmp_path):
    p = Project(name="Demo", display=Display.from_profile("DMG10600C070_03WTC"))
    p.variables.append(Variable(name="temp", decimals=1, init=215))
    p.pages[0].elements += [Rect(x=10, y=10, w=200, h=100), Text(text="Hello", x=20, y=20)]
    p.pages[0].controls.append(Control(type="number", var="temp", x=20, y=60, w=150, h=60))
    p.save(tmp_path)
    q = Project.load(tmp_path)
    assert q.display.width == 1024 and q.display.cpu == "T5L2"
    assert [e.id for e in q.pages[0].elements] == ["e1", "e2"]
    assert q.pages[0].controls[0].id.startswith("c")
    assert q.model_dump() == Project.load(tmp_path / "project.json").model_dump()


def test_theme_resolve():
    t = Theme()
    assert t.resolve("primary") == "#38BDF8"
    assert t.resolve("#abcdef") == "#ABCDEF"
    assert t.resolve(None) is None
    with pytest.raises(ValueError):
        t.resolve("blue")
    with pytest.raises(ValidationError):
        Theme(colors={"primary": "red"})


def test_vp_allocation_skips_fixed():
    p = Project(variables=[Variable(name="a"), Variable(name="b", vp=0x5001, type="int32"),
                           Variable(name="c", type="text", length=10), Variable(name="d")])
    vps = p.allocate_vps()
    assert vps["b"] == 0x5001
    assert vps["a"] == 0x5000
    assert vps["c"] == 0x5003            # after b (2 words)
    assert vps["d"] == 0x5008            # text of 10 chars = 5 words


def test_rejects_unknown_fields_and_bad_values():
    with pytest.raises(ValidationError):
        Rect(x=0, y=0, colour="red")
    with pytest.raises(ValidationError):
        Variable(name="1bad")
    with pytest.raises(ValidationError):
        Page(id=-1)


def test_schema_available_for_ai():
    s = Project.json_schema()
    assert "pages" in s["properties"] and "$defs" in s


def test_get_project_always_lists_pages_and_variables(tmp_path):
    from opendgus.tools import core as T
    T.SESSION.folder = None
    T.create_project(str(tmp_path / "fresh"))
    d = T.get_project()
    assert d["pages"][0]["id"] == 0 and d["variables"] == [] and d["display"]["width"] == 800
