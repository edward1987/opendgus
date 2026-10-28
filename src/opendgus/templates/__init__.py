"""Ready-made responsive project templates.

Any module in this package (not starting with '_') that defines TITLE, DESCRIPTION and build(width, height) -> Project
is registered automatically under its module name."""
import importlib
import pkgutil

TEMPLATES = {}
for _m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
    if _m.name.startswith("_"):
        continue
    _mod = importlib.import_module(f"{__name__}.{_m.name}")
    if all(hasattr(_mod, a) for a in ("TITLE", "DESCRIPTION", "build")):
        TEMPLATES[_m.name] = _mod
