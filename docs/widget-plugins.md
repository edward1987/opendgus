# Widget plugins

OpenDGUS loads widget plugins installed into the same Python environment as its backend. Installing the package is the opt-in step; project files never execute Python code from their own folder. Plugins use the `opendgus.widgets.v1` entry-point group.

```toml
[project.entry-points."opendgus.widgets.v1"]
my_widget = "my_package.widgets:MyWidget"
```

The entry point must resolve to a subclass of `opendgus.widgets.base.Widget` with a unique `key`, a `Props` subclass as `props_model`, and `draw()` / `expand()` methods. `expand()` returns `Record` objects using the supported DGUS control registry. The compiler and emulator use those same records, so a plugin cannot add behavior to the display by drawing pixels in the desktop preview alone. Set `verified` to `"csharp"` until the relevant control and plugin behavior have been tested on hardware.

```python
from opendgus.widgets.base import Props, Record, Widget

class MyProps(Props):
    color: str = "primary"

class MyWidget(Widget):
    key = "example_status"
    title = "Example status"
    category = "display"
    needs_var = True
    verified = "csharp"
    props_model = MyProps

    def expand(self, ctx, control):
        vp = ctx.require_var(control)
        return [Record("var_icon", {"vp": vp, "x": control.x, "y": control.y,
                                    "v_min": 0, "v_max": 1, "icon_min": 0, "icon_max": 1,
                                    "icon_lib": ctx.icon_lib, "mode": 1})]
```

The example illustrates registration only; a working icon widget must add its images with `ctx.icon()` before referencing their IDs. Plugin loading failures are recorded in `opendgus.widgets.PLUGIN_ERRORS`. A project with a missing widget produces a build error that names the missing plugin control.
