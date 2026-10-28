"""Every template must compile cleanly (no errors, no warnings) at common resolutions, landscape and portrait."""
import pytest

from opendgus.compiler import compile_project
from opendgus.templates import TEMPLATES

SIZES = [(1024, 600), (800, 480), (480, 272), (480, 800)]


@pytest.mark.parametrize("name", sorted(TEMPLATES))
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_template_compiles_cleanly(name, size):
    p = TEMPLATES[name].build(*size)
    r = compile_project(p, None, write=False)
    assert r.ok, [str(i) for i in r.issues]
    assert not r.issues, [str(i) for i in r.issues]
    assert len(p.pages) >= 1 and p.variables


def test_registry_metadata():
    for name, mod in TEMPLATES.items():
        assert mod.TITLE and mod.DESCRIPTION, name
