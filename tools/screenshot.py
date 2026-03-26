"""Screenshot tools: single view and multi-view capture.

Draw style indices (FreeCAD Std_DrawStyle command):
  0 = As Is       (per-object)
  1 = Points
  2 = Wireframe
  3 = Hidden Line  (clean technical drawing)
  4 = No Shading
  5 = Shaded       (smooth, no edges)
  6 = Flat Lines   (shaded + edges, best default)
"""

import base64
from typing import Annotated

from fastmcp.utilities.types import Image
from pydantic import Field


# Named constants for draw style indices
DRAW_STYLES = {
    "as_is": 0,
    "points": 1,
    "wireframe": 2,
    "hidden_line": 3,
    "no_shading": 4,
    "shaded": 5,
    "flat_lines": 6,
}

# Default pair: best for understanding geometry
DEFAULT_STYLES = [6, 3]   # Flat Lines + Hidden Line


def _resolve_styles(style_override: str | None) -> list[int]:
    """Resolve style parameter to list of Std_DrawStyle indices.

    Accepts:
      None          -> DEFAULT_STYLES (Flat Lines + Hidden Line)
      "wireframe"   -> single style [2]
      "flat_lines,wireframe,hidden_line" -> multiple [6, 2, 3]
      "6"           -> single by index [6]
      "6,2,3"       -> multiple by index
    """
    if style_override is None:
        return list(DEFAULT_STYLES)

    result = []
    for token in style_override.split(","):
        token = token.strip().lower()
        if token in DRAW_STYLES:
            result.append(DRAW_STYLES[token])
        elif token.isdigit() and 0 <= int(token) <= 6:
            result.append(int(token))
    return result if result else list(DEFAULT_STYLES)


def register(mcp, bridge):

    @mcp.tool
    async def screenshot(
        width: Annotated[int, Field(description="Image width in pixels")] = 800,
        height: Annotated[int, Field(description="Image height in pixels")] = 600,
        background: Annotated[
            str,
            Field(description="Background: 'Current', 'White', 'Black', or 'Transparent'"),
        ] = "Current",
        styles: Annotated[
            str | None,
            Field(description=(
                "Draw styles to capture. Comma-separated names or indices. "
                "Names: flat_lines, hidden_line, wireframe, shaded, no_shading, points. "
                "Default: flat_lines,hidden_line (2 images). "
                "Example: 'wireframe' (1 image), 'flat_lines,wireframe,hidden_line' (3 images)."
            )),
        ] = None,
    ) -> list[Image]:
        """Capture screenshot(s) of the active 3D view. Returns one image per requested draw style."""
        style_indices = _resolve_styles(styles)
        result = await bridge.execute(f"""
import base64, tempfile, os, json

FreeCADGui.updateGui()
view = FreeCADGui.activeDocument().activeView()

style_indices = {style_indices}

images = []
for idx in style_indices:
    FreeCADGui.runCommand('Std_DrawStyle', idx)
    FreeCADGui.updateGui()
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    view.saveImage(tmp.name, {width}, {height}, "{background}")
    with open(tmp.name, "rb") as f:
        images.append(base64.b64encode(f.read()).decode("ascii"))
    os.unlink(tmp.name)

# Restore to Flat Lines
FreeCADGui.runCommand('Std_DrawStyle', 6)
FreeCADGui.updateGui()

__result__ = json.dumps(images)
""")
        if not result.get("success"):
            raise ValueError(f"Screenshot failed: {result.get('error')}")
        import json as _json
        imgs = _json.loads(result["result"])
        return [Image(data=base64.b64decode(b64), format="png") for b64 in imgs]

    @mcp.tool
    async def screenshot_multiview(
        width: Annotated[int, Field(description="Width of each view in pixels")] = 600,
        height: Annotated[int, Field(description="Height of each view in pixels")] = 450,
        views: Annotated[
            str | None,
            Field(description=(
                "Comma-separated view names: front,back,top,bottom,left,right,isometric. "
                "Default: front,right,top,isometric"
            )),
        ] = None,
        background: Annotated[str, Field(description="Background: 'Current','White','Black','Transparent'")] = "White",
        styles: Annotated[
            str | None,
            Field(description=(
                "Draw styles per view. Comma-separated names or indices. "
                "Names: flat_lines, hidden_line, wireframe, shaded, no_shading, points. "
                "Default: flat_lines,hidden_line (2 images per view). "
                "Example: 'flat_lines' (1 per view), 'flat_lines,wireframe,hidden_line' (3 per view)."
            )),
        ] = None,
    ) -> list[Image]:
        """Capture multiple standard views. Returns N images per view (one per draw style)."""
        view_list = [v.strip() for v in (views or "front,right,top,isometric").split(",")]
        style_indices = _resolve_styles(styles)
        result = await bridge.execute(f"""
import base64, tempfile, os, json

view_names = {view_list}
width = {width}
height = {height}
background = "{background}"
style_indices = {style_indices}

FreeCADGui.updateGui()
view = FreeCADGui.activeDocument().activeView()
saved_camera = view.getCamera()

presets = {{
    "front": view.viewFront,
    "back": view.viewRear,
    "top": view.viewTop,
    "bottom": view.viewBottom,
    "left": view.viewLeft,
    "right": view.viewRight,
    "isometric": view.viewIsometric,
}}

images = []
for vname in view_names:
    fn = presets.get(vname.lower())
    if fn is None:
        continue
    fn()
    view.fitAll()
    FreeCADGui.updateGui()

    for idx in style_indices:
        FreeCADGui.runCommand('Std_DrawStyle', idx)
        FreeCADGui.updateGui()

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        view.saveImage(tmp.name, width, height, background)
        with open(tmp.name, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        os.unlink(tmp.name)
        images.append({{"view": vname, "style_idx": idx, "image_base64": b64}})

# Restore to Flat Lines + original camera
FreeCADGui.runCommand('Std_DrawStyle', 6)
view.setCamera(saved_camera)
FreeCADGui.updateGui()

__result__ = json.dumps(images)
""")
        if not result.get("success"):
            raise ValueError(f"Multiview failed: {result.get('error')}")

        import json as _json
        views_data = _json.loads(result["result"])
        output = []
        for v in views_data:
            if "image_base64" in v:
                output.append(Image(data=base64.b64decode(v["image_base64"]), format="png"))
        return output
