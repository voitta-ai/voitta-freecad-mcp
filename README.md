# FreeCAD MCP Server

MCP (Model Context Protocol) server that gives LLMs full control over FreeCAD — create geometry, manipulate documents, capture screenshots, and execute arbitrary FreeCAD Python scripts.

## Architecture

```
LLM  <-->  MCP Server (FastMCP, port 50005)  <-->  Bridge (HTTP, port 50006)  <-->  FreeCAD
```

Two-process design:

- **`server.py`** — MCP server using [FastMCP](https://github.com/jlowin/fastmcp). Runs as a standalone Python process. Exposes tools to LLMs via MCP protocol.
- **`freecad_bridge.py`** — Lightweight HTTP server that runs *inside* FreeCAD's Python console. Executes code on FreeCAD's main thread via a QTimer-polled queue.

The bridge is necessary because FreeCAD's GUI operations must run on the main thread.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the bridge inside FreeCAD

Open FreeCAD, then in the Python console:

```python
exec(open("/path/to/freecad_bridge.py").read())
```

This starts an HTTP server on port 50006 inside FreeCAD.

#### Auto-start the bridge on every FreeCAD launch (optional)

To avoid pasting into the console each session, register the bridge as a
startup script. FreeCAD scans every `Mod/` directory at launch and runs each
`InitGui.py` **once the GUI is up** — which is exactly what the bridge needs
(it imports `FreeCADGui` and arms a `QtCore.QTimer`, neither of which exists at
the earlier App-init / `user.py` stage).

Create `<user-app-data>/Mod/FreeCADBridge/InitGui.py`, where `<user-app-data>`
is what `FreeCAD.getUserAppDataDir()` prints in the Python console (e.g. on
macOS `~/Library/Application Support/FreeCAD/v1-1/`):

```python
import FreeCAD

_BRIDGE = "/path/to/freecad_bridge.py"
try:
    # Run in a dedicated namespace dict (globals IS locals). FreeCAD exec()'s
    # InitGui.py with *separate* globals/locals dicts; a bare exec() here would
    # inherit that split, so the bridge's module-level names (BRIDGE_HOST, ...)
    # would land in locals while its functions resolve __globals__ — raising
    # NameError at call time. One shared dict avoids that.
    ns = {"__name__": "freecad_bridge", "__file__": _BRIDGE}
    with open(_BRIDGE) as f:
        exec(compile(f.read(), _BRIDGE, "exec"), ns)
    FreeCAD.Console.PrintMessage("freecad-mcp bridge started from InitGui.py\n")
except Exception as e:
    FreeCAD.Console.PrintError("freecad-mcp bridge autostart failed: %s\n" % e)
```

Fully quit and reopen FreeCAD, then confirm the bridge is listening:

```bash
lsof -nP -iTCP:50006 -sTCP:LISTEN
```

### 3. Start the MCP server

```bash
python server.py
```

Runs on port 50005 by default.

### 4. Configure your MCP client

Point your MCP client (Claude Code, etc.) to `http://localhost:50005`.

## Configuration

Environment variables (or `.env` file):

| Variable | Default | Description |
|---|---|---|
| `MCP_HOST` | `0.0.0.0` | MCP server bind address |
| `MCP_PORT` | `50005` | MCP server port |
| `FREECAD_BRIDGE_HOST` | `127.0.0.1` | Bridge server address |
| `FREECAD_BRIDGE_PORT` | `50006` | Bridge server port |

## Tools

### Document Management
- `create_document`, `open_document`, `save_document`, `close_document`
- `list_documents`, `set_active_document`, `get_document_objects`

### Geometry & Part Design
- `create_body`, `create_sketch`, `create_pad`, `create_pocket`
- `create_box`, `create_cylinder`, `create_sphere`, `create_cone`, `create_torus`
- `create_fillet`, `create_chamfer`, `create_revolution`, `create_groove`
- `boolean_fuse`, `boolean_cut`, `boolean_common`

### Sketch Operations
- `sketch_add_line`, `sketch_add_rectangle`, `sketch_add_circle`, `sketch_add_arc`
- `sketch_add_constraint`

### Assembly
- `create_assembly`, `assembly_add_part`, `assembly_insert_object`
- `assembly_create_joint`, `assembly_delete_joint`, `assembly_list_joints`
- `assembly_ground_part`, `assembly_set_part_placement`, `assembly_solve`

### Inspection & Measurement
- `get_tree`, `get_object_properties`
- `get_face_info`, `get_edge_info`, `find_faces_by_criteria`, `find_edges_by_criteria`
- `measure_distance`, `measure_angle`, `measure_between_objects`

### Screenshot & Camera
- **`screenshot`** — Capture current view. Returns multiple images (default: Flat Lines + Hidden Line). Supports `styles` parameter for custom draw styles.
- **`screenshot_multiview`** — Capture standard views (front, top, right, isometric, etc.). Returns N images per view. Supports `styles` parameter.
- `get_camera`, `set_camera`

#### Draw Styles

Both screenshot tools accept a `styles` parameter:

```
styles="flat_lines"                    # single style
styles="flat_lines,wireframe"          # two styles
styles="flat_lines,hidden_line,wireframe"  # three styles
```

Available styles: `flat_lines` (6), `hidden_line` (3), `wireframe` (2), `shaded` (5), `no_shading` (4), `points` (1).

Default: `flat_lines,hidden_line`.

### Transform
- `set_placement`, `translate_object`, `rotate_object`
- `copy_object`, `delete_object`, `set_label`, `set_color`

### Script Execution
- **`run_script`** — Execute arbitrary FreeCAD Python code. Full access to `FreeCAD`, `Part`, `FreeCADGui`, etc. Set `__result__` to return data.

## File Structure

```
server.py           # MCP server entry point
freecad_bridge.py   # HTTP bridge (runs inside FreeCAD)
bridge_client.py    # Async HTTP client for the bridge
requirements.txt
tools/
  __init__.py       # Tool registration
  _helpers.py       # Shared utilities
  assembly.py       # Assembly tools
  camera.py         # Camera get/set
  document.py       # Document management
  geometry.py       # Boolean ops, fillets, chamfers
  inspection.py     # Tree, properties, face/edge queries
  measurement.py    # Distance, angle measurement
  partdesign.py     # Sketch, pad, pocket, revolution
  primitives.py     # Box, cylinder, sphere, cone, torus
  screenshot.py     # Screenshot capture with draw style control
  script.py         # Arbitrary script execution
  transform.py      # Placement, translate, rotate, copy, delete
```

## License

MIT
