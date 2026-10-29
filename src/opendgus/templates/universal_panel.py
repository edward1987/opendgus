"""Neutral control and monitoring starter for any device."""
from ..model import Control, Page, Rect, Text
from ._kit import Frame, new_project, var

TITLE = "Universal panel"
DESCRIPTION = "General monitoring and control: a live value, state, trend, choice and setpoint."


def build(width: int, height: int):
    f = Frame(width, height)
    p = new_project(TITLE, DESCRIPTION, width, height)
    p.variables = [var("reading", 0, doc="Live value from controller"),
                   var("status", 0, doc="0 idle, 1 running, 2 fault"),
                   var("mode", 0, doc="Selected mode"),
                   var("setpoint", 50, doc="Target value")]
    m = f.margin
    head = max(38, min(72, height // 7))
    nav_w = max(72, min(150, width // 4))
    nav_h = max(28, min(52, head - 10))
    title_size = max(18, min(34, head // 2))
    body_y = head + m
    body_h = height - body_y - m
    body_w = width - 2 * m
    top_h = max(60, body_h * 3 // 5)
    value_w = body_w * 2 // 3
    overview = Page(id=0, name="Overview", elements=[
        Text(text="Overview", x=m, y=0, w=width - nav_w - 3 * m, h=head, size=title_size, weight="bold", valign="middle"),
        Rect(x=m, y=body_y, w=value_w, h=top_h, fill="surface"),
        Rect(x=m + value_w + f.gap, y=body_y, w=max(1, body_w - value_w - f.gap), h=top_h, fill="surface"),
        Text(text="Live reading", x=m + f.gap, y=body_y + f.gap, w=value_w - 2 * f.gap,
             h=max(16, f.S(28)), size=max(12, f.S(20)), color="muted"),
    ], controls=[
        Control(type="button", x=width - nav_w - m, y=(head-nav_h)//2, w=nav_w, h=nav_h,
                props={"label": "Controls", "action": {"type": "page", "page": 1}}),
        Control(type="number", var="reading", x=m + f.gap, y=body_y + top_h // 3,
                w=max(1, value_w - 2*f.gap), h=min(70, max(24, top_h // 3)),
                props={"int_digits": 3}),
        Control(type="indicator", var="status", x=m + value_w + f.gap + 4, y=body_y + top_h // 3,
                w=max(1, body_w - value_w - f.gap - 8), h=max(24, top_h // 3),
                props={"states": [{"label": "Idle", "color": "muted"},
                                  {"label": "Run", "color": "success"},
                                  {"label": "Fault", "color": "danger"}]}),
        Control(type="progress", var="reading", x=m, y=body_y + top_h + f.gap,
                w=body_w, h=max(15, min(34, body_h - top_h - f.gap)), props={"max": 100}),
    ])
    control_y = body_y + max(4, body_h // 9)
    controls = Page(id=1, name="Controls", elements=[
        Text(text="Controls", x=m, y=0, w=width - nav_w - 3*m, h=head, size=title_size, weight="bold", valign="middle"),
        Text(text="Mode", x=m, y=body_y, w=body_w, h=max(18, body_h // 9), size=max(12, f.S(22)), color="muted"),
        Text(text="Setpoint", x=m, y=body_y + body_h // 2, w=body_w, h=max(18, body_h // 9), size=max(12, f.S(22)), color="muted"),
    ], controls=[
        Control(type="button", x=width - nav_w - m, y=(head-nav_h)//2, w=nav_w, h=nav_h,
                props={"label": "Overview", "action": {"type": "page", "page": 0}}),
        Control(type="choice", var="mode", x=m, y=control_y, w=body_w,
                h=max(28, body_h // 4), props={"options": ["Off", "Auto", "Manual"]}),
        Control(type="slider", var="setpoint", x=m, y=body_y + body_h * 2 // 3,
                w=body_w, h=max(28, body_h // 5)),
    ])
    p.pages = [overview, controls]
    return p
