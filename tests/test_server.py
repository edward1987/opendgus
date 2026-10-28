from fastapi.testclient import TestClient

from opendgus.server import create_app
from opendgus.tools import SESSION

TOK = "test-token"


def client():
    return TestClient(create_app(TOK), headers={"X-OpenDGUS-Token": TOK})


def test_auth_required():
    c = TestClient(create_app(TOK))
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/tools").status_code == 401


def test_tools_and_editing_flow(tmp_path):
    SESSION.folder = None
    c = client()
    tools = {t["name"]: t for t in c.get("/api/tools").json()}
    assert "add_control" in tools and tools["add_control"]["input_schema"]["required"] == ["page", "type", "x",
                                                                                          "y", "w", "h"]
    r = c.post("/api/tools/create_project", json={"folder": str(tmp_path / "p"), "template": "home_control",
                                                  "width": 800, "height": 480})
    assert r.status_code == 200, r.text
    proj = c.get("/api/project").json()["project"]
    assert proj["display"]["width"] == 800 and len(proj["pages"]) == 2

    # editor saves a modified project
    proj["pages"][0]["name"] = "Renamed"
    assert c.put("/api/project", json=proj).json()["ok"]
    assert c.get("/api/project").json()["project"]["pages"][0]["name"] == "Renamed"
    bad = dict(proj, display={**proj["display"], "width": -5})
    assert c.put("/api/project", json=bad).status_code == 400

    png = c.get("/api/preview/0.png?scale=0.5")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png" and png.content[:4] == b"\x89PNG"

    err = c.post("/api/tools/add_control", json={"page": 0, "type": "nope", "x": 0, "y": 0, "w": 1, "h": 1})
    assert err.status_code == 400 and "unknown widget" in err.json()["error"]

    img = c.post("/api/tools/render_page", json={"page": 1, "scale": 0.25}).json()["result"]
    assert img["mime"] == "image/png" and len(img["image"]) > 100

    cat = c.get("/api/catalog").json()
    assert cat["spec_count"] == 47 and any(w["type"] == "toggle" for w in cat["widgets"])


def test_websocket_notifies_changes(tmp_path):
    SESSION.folder = None
    c = client()
    c.post("/api/tools/create_project", json={"folder": str(tmp_path / "w")})
    with c.websocket_connect(f"/ws?token={TOK}") as ws:
        assert ws.receive_json()["type"] == "project_changed"           # initial state
        c.post("/api/tools/add_page", json={"name": "Two"})
        assert ws.receive_json()["type"] == "project_changed"
