# PyInstaller spec for the OpenDGUS Python sidecar.
#
# Builds ONE folder (dist/opendgus-backend/) holding three console programs that share a single
# _internal/ bundle:
#   opendgus-server  - editor backend spawned by the desktop app (opendgus.server:main)
#   opendgus-mcp     - MCP server for Claude Desktop / Codex / Antigravity (opendgus.mcp_server:main)
#   opendgus-load    - flash a build onto a display over serial (opendgus.device.dwinload:main)
#
# Build (from the repo root):
#   .venv/Scripts/python.exe -m PyInstaller packaging/opendgus-backend.spec --noconfirm \
#       --distpath packaging/dist --workpath packaging/build
# or `npm run dist:backend` in app/.
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")
ENTRIES = os.path.join(SPECPATH, "entries")

# opendgus discovers templates with pkgutil.iter_modules -> collect every submodule explicitly.
hiddenimports = collect_submodules("opendgus")
for pkg in (
    "uvicorn",  # protocols/lifespan/loops are imported by string
    "websockets",
    "wsproto",
    "httptools",
    "h11",
    "anyio",
    "starlette",
    "fastapi",
    "mcp.server", "mcp.shared", "mcp.types", "mcp.client",
    "pydantic",
    "pydantic_core",
    "sse_starlette",
    "serial.tools",
):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:  # optional backends that are not installed
        pass
hiddenimports += [
    "mcp",
    "anthropic",
    "openai",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "serial.tools.list_ports",
    "email.mime.multipart",
]

datas = [
    (os.path.join(SRC, "opendgus", "data"), os.path.join("opendgus", "data")),
]
datas += collect_data_files("anthropic")
datas += collect_data_files("openai")
datas += collect_data_files("mcp")

excludes = ["tkinter", "_tkinter", "matplotlib", "numpy", "IPython", "pytest", "PyInstaller"]


def analysis(script):
    return Analysis(
        [os.path.join(ENTRIES, script)],
        pathex=[SRC],
        binaries=[],
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        runtime_hooks=[],
        excludes=excludes,
        noarchive=False,
    )


def exe(a, name):
    pyz = PYZ(a.pure)
    return EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        debug=False,
        strip=False,
        upx=False,
        console=True,
        contents_directory="_internal",
    )


a_server = analysis("opendgus_server.py")
a_mcp = analysis("opendgus_mcp.py")
a_load = analysis("opendgus_load.py")

exe_server = exe(a_server, "opendgus-server")
exe_mcp = exe(a_mcp, "opendgus-mcp")
exe_load = exe(a_load, "opendgus-load")

coll = COLLECT(
    exe_server,
    a_server.binaries,
    a_server.datas,
    exe_mcp,
    a_mcp.binaries,
    a_mcp.datas,
    exe_load,
    a_load.binaries,
    a_load.datas,
    strip=False,
    upx=False,
    name="opendgus-backend",
)
