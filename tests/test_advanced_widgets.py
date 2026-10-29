"""End-to-end checks for approachable controls built from DGUS records."""
from opendgus.compiler import compile_project
from opendgus.emulator import Device
from opendgus.model import Control, Page, Project, Variable


def test_advanced_controls_compile_and_choice_sends_value(tmp_path):
    project = Project(
        variables=[Variable(name="message", type="text", length=64, init="OpenDGUS"),
                   Variable(name="mode")],
        pages=[Page(id=0, controls=[
            Control(type="live_text", var="message", x=20, y=20, w=260, h=50),
            Control(type="qr", var="message", x=300, y=20, w=150, h=150),
            Control(type="clock", x=20, y=90, w=240, h=50),
            Control(type="choice", var="mode", x=20, y=200, w=360, h=60,
                    props={"options": ["Manual", "Auto", "Off"]}),
            Control(type="curve", x=20, y=300, w=400, h=120, props={"channel": 2}),
        ])],
    )
    result = compile_project(project, tmp_path)
    assert result.ok, [str(issue) for issue in result.issues]
    device = Device.from_folder(tmp_path / "build" / "DWIN_SET")
    assert {c.key for c in device.show[0]} >= {"text_display", "qr_code", "rtc_text", "var_icon", "curve"}
    assert device.render().size == (project.display.width, project.display.height)
    device.tap(210, 230)
    assert device.var("mode") == 1
    assert device.uploads[-1]["vp"] == result.vps["mode"]


def test_live_text_and_qr_require_text_variables():
    project = Project(variables=[Variable(name="value")], pages=[Page(id=0, controls=[
        Control(type="live_text", var="value", x=10, y=10, w=100, h=40),
        Control(type="qr", var="value", x=10, y=60, w=100, h=100),
    ])])
    result = compile_project(project, write=False)
    assert not result.ok
    assert sum("needs a text variable" in str(issue) for issue in result.issues) == 2
