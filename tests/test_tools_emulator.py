from opendgus.tools import core as T


def test_emulator_tools_drive_the_built_project(tmp_path):
    T.SESSION.folder = None
    T.create_project(str(tmp_path / "p"), template="home_control", width=1024, height=600)
    shot = T.emulator_start()
    assert shot.png[:4] == b"\x89PNG"
    p = T.get_project()
    k = next(c for c in p["pages"][0]["controls"] if c.get("var") == "dev1")
    assert '"dev1": [0, 1]' in T.emulator_tap(k["x"] + 10, k["y"] + 10).caption
    tab = next(c for c in p["pages"][0]["controls"] if c.get("props", {}).get("label") == "Climate")
    assert '"page": 1' in T.emulator_tap(tab["x"] + 5, tab["y"] + 5).caption
    plus = next(c for c in p["pages"][1]["controls"] if c.get("props", {}).get("icon") == "plus")
    T.emulator_tap(plus["x"] + 10, plus["y"] + 10, hold_ms=1200)
    assert T.emulator_state()["variables"]["setpoint"] > 225          # repeated while held
    T.emulator_set_variable("temperature", 199)
    assert T.emulator_state()["variables"]["temperature"] == 199
