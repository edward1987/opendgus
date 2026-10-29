"""Generic status grid and details starter."""
from ..model import Control, Page, Rect, Text
from ._kit import Frame, new_project, var

TITLE = "Status dashboard"
DESCRIPTION = "Reusable status tiles, live text, clock and QR for any connected device."


def build(width: int, height: int):
    f = Frame(width, height)
    p = new_project(TITLE, DESCRIPTION, width, height)
    p.variables = [*[var(f"state_{i}", 0) for i in range(4)],
                   var("message", "Ready", type="text"), var("qr_content", "OpenDGUS", type="text")]
    m = f.margin
    head = max(38, height // 8)
    gap = max(6, f.gap)
    body_y = head + m
    tile_w = (width - 2*m - gap) // 2
    tile_h = (height - body_y - m - gap) // 2
    els = [Text(text="Status", x=m, y=0, w=width//2, h=head, size=max(18, head//2),
                weight="bold", valign="middle")]
    ctrls = [Control(type="button", x=width - m - max(80, width//4), y=4,
                     w=max(80, width//4), h=head-8,
                     props={"label": "Details", "action": {"type": "page", "page": 1}})]
    for i in range(4):
        x = m + (i % 2) * (tile_w + gap)
        y = body_y + (i // 2) * (tile_h + gap)
        els.append(Rect(x=x, y=y, w=tile_w, h=tile_h, fill="surface"))
        els.append(Text(text=f"Channel {i+1}", x=x+gap, y=y+gap, w=tile_w-2*gap,
                        h=max(16, tile_h//3), size=max(12, min(22, tile_h//4)), color="muted"))
        ctrls.append(Control(type="indicator", var=f"state_{i}", x=x+gap,
                             y=y+tile_h//2, w=tile_w-2*gap, h=max(18, tile_h//3),
                             props={"states": [{"label": "OK", "color": "success"},
                                               {"label": "Alert", "color": "danger"}]}))
    detail_y = body_y + max(18, (height-body_y-m)//4)
    detail = Page(id=1, name="Details", elements=[
        Text(text="Details", x=m, y=0, w=width//2, h=head, size=max(18, head//2), weight="bold", valign="middle"),
        Text(text="Controller message", x=m, y=body_y, w=width-2*m, h=max(18, head//2),
             size=max(12, head//3), color="muted"),
    ], controls=[
        Control(type="button", x=width-m-max(80, width//4), y=4, w=max(80, width//4), h=head-8,
                props={"label": "Status", "action": {"type": "page", "page": 0}}),
        Control(type="live_text", var="message", x=m, y=detail_y, w=width//2-m,
                h=max(28, head//2)),
        Control(type="clock", x=m, y=detail_y + max(38, head), w=width//2-m, h=max(26, head//2)),
        Control(type="qr", var="qr_content", x=width//2, y=detail_y,
                w=min(width//2-m, height-detail_y-m), h=min(width//2-m, height-detail_y-m)),
    ])
    p.pages = [Page(id=0, name="Status", elements=els, controls=ctrls), detail]
    return p
