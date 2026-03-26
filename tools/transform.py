"""Transform tools: move, rotate, set placement, mirror, copy objects."""

from typing import Annotated
from pydantic import Field

from tools._helpers import format_result, doc_ref_expr


def register(mcp, bridge):

    # ------------------------------------------------------------------
    # Set Placement
    # ------------------------------------------------------------------

    @mcp.tool
    async def set_placement(
        object_name: Annotated[str, Field(description="Object name")],
        position: Annotated[str | None, Field(description="Position as 'x,y,z' in mm")] = None,
        rotation: Annotated[str | None, Field(
            description="Rotation as 'axis_x,axis_y,axis_z,angle_deg' or Euler 'yaw,pitch,roll' in degrees"
        )] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Set the absolute placement of an object (position and/or rotation)."""
        ref = doc_ref_expr(document)
        pos_code = ""
        rot_code = ""
        if position:
            pos_code = f'obj.Placement.Base = FreeCAD.Vector({position})'
        if rotation:
            parts = [float(x) for x in rotation.split(",")]
            if len(parts) == 4:
                rot_code = (
                    f'obj.Placement.Rotation = FreeCAD.Rotation('
                    f'FreeCAD.Vector({parts[0]},{parts[1]},{parts[2]}), {parts[3]})'
                )
            elif len(parts) == 3:
                rot_code = (
                    f'obj.Placement.Rotation = FreeCAD.Rotation({parts[0]},{parts[1]},{parts[2]})'
                )
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.getObject("{object_name}")
{pos_code}
{rot_code}
doc.recompute()
p = obj.Placement
__result__ = f"Placement of '{{obj.Name}}': pos={{p.Base}}, rot={{p.Rotation.toEuler()}}"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Translate (relative move)
    # ------------------------------------------------------------------

    @mcp.tool
    async def translate_object(
        object_name: Annotated[str, Field(description="Object name")],
        vector: Annotated[str, Field(description="Translation vector as 'dx,dy,dz' in mm")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Move an object by a relative displacement vector."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.getObject("{object_name}")
v = FreeCAD.Vector({vector})
obj.Placement.Base = obj.Placement.Base + v
doc.recompute()
__result__ = f"Translated '{{obj.Name}}' by ({{v.x}},{{v.y}},{{v.z}}) -> now at {{obj.Placement.Base}}"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Rotate (relative)
    # ------------------------------------------------------------------

    @mcp.tool
    async def rotate_object(
        object_name: Annotated[str, Field(description="Object name")],
        axis: Annotated[str, Field(description="Rotation axis as 'x,y,z' (e.g. '0,0,1' for Z)")],
        angle: Annotated[float, Field(description="Rotation angle in degrees")],
        center: Annotated[str | None, Field(description="Center of rotation as 'x,y,z' in mm. Default: origin.")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Rotate an object around an axis by the given angle."""
        ref = doc_ref_expr(document)
        center_expr = f"FreeCAD.Vector({center})" if center else "FreeCAD.Vector(0,0,0)"
        result = await bridge.execute(f"""
import math
doc = {ref}
obj = doc.getObject("{object_name}")
rot = FreeCAD.Rotation(FreeCAD.Vector({axis}), {angle})
center = {center_expr}
new_placement = FreeCAD.Placement(center, rot).multiply(
    FreeCAD.Placement(-center, FreeCAD.Rotation())
).multiply(obj.Placement)
obj.Placement = new_placement
doc.recompute()
__result__ = f"Rotated '{{obj.Name}}' by {angle} deg around ({axis})"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Copy Object
    # ------------------------------------------------------------------

    @mcp.tool
    async def copy_object(
        source_name: Annotated[str, Field(description="Source object name")],
        new_name: Annotated[str | None, Field(description="Name for the copy")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a simple copy (Part::Feature) of a shape object."""
        ref = doc_ref_expr(document)
        name_code = f'"{new_name}"' if new_name else 'src.Name + "_Copy"'
        result = await bridge.execute(f"""
import Part
doc = {ref}
src = doc.getObject("{source_name}")
copy_name = {name_code}
copy = doc.addObject("Part::Feature", copy_name)
copy.Shape = Part.Shape(src.Shape)
copy.Placement = src.Placement
doc.recompute()
__result__ = f"Copied '{{src.Name}}' -> '{{copy.Name}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Delete Object
    # ------------------------------------------------------------------

    @mcp.tool
    async def delete_object(
        object_name: Annotated[str, Field(description="Object name to delete")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Delete an object from the document."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
doc.removeObject("{object_name}")
doc.recompute()
__result__ = "Deleted '{object_name}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Set Label
    # ------------------------------------------------------------------

    @mcp.tool
    async def set_label(
        object_name: Annotated[str, Field(description="Object internal name")],
        label: Annotated[str, Field(description="New display label")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Set the display label of an object."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.getObject("{object_name}")
obj.Label = "{label}"
__result__ = f"Set label of '{{obj.Name}}' to '{{obj.Label}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Set Color
    # ------------------------------------------------------------------

    @mcp.tool
    async def set_color(
        object_name: Annotated[str, Field(description="Object name")],
        color: Annotated[str, Field(
            description="Color as 'r,g,b' floats 0-1 (e.g. '1,0,0' for red) "
            "or hex '#FF0000'"
        )],
        transparency: Annotated[int, Field(description="Transparency 0-100")] = 0,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Set the shape color and transparency of an object."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.getObject("{object_name}")
color_str = "{color}"
if color_str.startswith("#"):
    h = color_str.lstrip("#")
    rgb = tuple(int(h[i:i+2], 16)/255.0 for i in (0, 2, 4))
else:
    rgb = tuple(float(x) for x in color_str.split(","))
obj.ViewObject.ShapeColor = rgb
obj.ViewObject.Transparency = {transparency}
FreeCADGui.updateGui()
__result__ = f"Set color of '{{obj.Name}}' to RGB{{rgb}}, transparency={transparency}"
""")
        return format_result(result)
