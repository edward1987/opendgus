# Designing screens with AI through MCP

OpenDGUS includes an MCP server, so an AI assistant can design DWIN screens for you. It creates pages, adds widgets,
looks at the rendered result and fixes the layout, and builds the files. The project folder on disk is the shared
state: if the OpenDGUS editor has the same project open, you see the AI's changes live.

## Where the `opendgus-mcp` program is

The easiest way to get the right snippet is in the editor: **AI tab → plug button ("Connect an AI app (MCP)")**. It
shows the config for Claude Desktop, Codex and Antigravity with the real path on your computer and a copy button.

| How OpenDGUS was installed | MCP command |
|---|---|
| Windows installer (per user, default folder) | `%LOCALAPPDATA%\Programs\OpenDGUS\resources\backend\opendgus-mcp.exe` |
| Windows installer (custom folder) | `<install folder>\resources\backend\opendgus-mcp.exe` |
| Windows portable `.exe` | runs from a temporary folder, so the **Connect an AI app** dialog first copies the server to `%APPDATA%\OpenDGUS\mcp-server\<version>\opendgus-mcp.exe` and shows that path |
| macOS (`.dmg`, dragged to Applications) | `/Applications/OpenDGUS.app/Contents/Resources/backend/opendgus-mcp` |
| Linux AppImage | mounts at a temporary path, so the dialog copies the server to `~/.config/OpenDGUS/mcp-server/<version>/opendgus-mcp` and shows that path |
| From source | `C:\path\to\opendgus\.venv\Scripts\opendgus-mcp.exe` (Linux/macOS: `/path/to/opendgus/.venv/bin/opendgus-mcp`) |
| `pip install opendgus` | `opendgus-mcp` |

The installed program needs no Python: it is the same self-contained bundle the editor uses. The examples below use
`C:\path\to\opendgus-mcp.exe`; replace it with the path from the table.
Set the environment variable `OPENDGUS_PROJECT` to open a project at start-up (optional).

## Claude Desktop
Edit `%APPDATA%\Claude\claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`), then fully
restart Claude Desktop:
```json
{
  "mcpServers": {
    "opendgus": {
      "command": "C:\\path\\to\\opendgus-mcp.exe",
      "env": { "OPENDGUS_PROJECT": "C:\\Users\\me\\Documents\\my-screen" }
    }
  }
}
```

## OpenAI Codex (CLI, desktop app, IDE extension)
The easiest way: **AI tab → plug button → Codex → Add to Codex**. OpenDGUS then:
- writes the `[mcp_servers.opendgus]` block into `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`), replacing an
  old OpenDGUS block and keeping a backup of the file as `config.toml.opendgus-backup`;
- installs the skill `~/.codex/skills/opendgus/SKILL.md`. Codex lists skills in its prompt, while MCP tools may be
  "deferred" (hidden until the model looks for them), so without the skill Codex may not realise OpenDGUS is there.

The dialog also shows whether the registered program still exists, and **Update Codex** fixes it. The Codex CLI,
desktop app and IDE extension share this config. Start a new Codex chat afterwards; `/mcp` lists the servers.

By hand:
```bash
codex mcp add opendgus -- C:\path\to\opendgus-mcp.exe
```
or in `~/.codex/config.toml`:
```toml
[mcp_servers.opendgus]
command = 'C:\path\to\opendgus-mcp.exe'
startup_timeout_sec = 30
```

**If Codex says it doesn't know OpenDGUS:**
- `codex mcp list` should show `opendgus` as enabled, with a path that exists. A path under `AppData\Local\Temp`
  belongs to a portable copy that has been closed; press **Update Codex** in the dialog.
- Run the program by hand: it should wait for input without printing an error. A `PackageNotFoundError` or similar
  means its folder is incomplete.
- Mention OpenDGUS in the request, for example *"use OpenDGUS to …"*.

## Google Antigravity
Agent panel → `…` → MCP Servers → Manage → View raw config (`~/.gemini/config/mcp_config.json`):
```json
{
  "mcpServers": {
    "opendgus": { "command": "C:\\path\\to\\opendgus-mcp.exe" }
  }
}
```

## Any other client (HTTP)
```bash
opendgus-mcp --http 8765        # streamable HTTP at http://127.0.0.1:8765/mcp
```

## What the AI can do
| Group | Tools |
|---|---|
| Discover | `list_display_profiles`, `decode_display_part_number`, `list_widgets`, `get_widget_schema`, `list_dgus_controls`, `search_icons`, `list_templates` |
| Project | `create_project`, `open_project`, `get_project`, `set_display`, `set_theme`, `apply_template` |
| Data | `add_variable`, `update_variable`, `delete_variable` |
| Pages | `add_page`, `update_page`, `delete_page`, `duplicate_page` |
| Content | `add_element`, `add_control`, `update_item`, `delete_item`, `arrange` |
| Check and build | `render_page` (returns an image the AI can look at), `validate`, `build` |
| Hardware | `list_serial_ports`, `device_info`, `device_read_variable`, `device_write_variable`, `device_upload` (overwrites the display; the AI must pass `confirm=true`, and should only do so after you agree) |

Resources: `opendgus://guide` (layout rules for AI designers) and `opendgus://widgets` (all widget schemas).
Prompt: `design_screen` takes a description and a size.

Example request: *"Create a 800x480 thermostat UI with a big setpoint, +/- buttons, a humidity gauge and a heating
toggle, in /home/me/thermostat."*
