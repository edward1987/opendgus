"""Smart widgets (button, toggle, number, progress, indicator, slider...) and the widget registry."""
from . import basic  # noqa: F401
from . import advanced  # noqa: F401
from .base import WIDGETS, PLUGIN_ERRORS, Record, Widget, get, load_plugins  # noqa: F401

load_plugins()
