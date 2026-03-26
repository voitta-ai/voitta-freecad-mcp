"""Part primitive creation and boolean operations.

Covers Part::Box, Part::Cylinder, Part::Sphere, Part::Cone, Part::Torus,
and boolean Fuse/Cut/Common.  These are simple Part-level shapes (not
PartDesign features inside a Body).
"""

from typing import Annotated
from pydantic import Field

from tools._helpers import format_result, doc_ref_expr


def register(mcp, bridge):

    # ------------------------------------------------------------------
    # Box
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_box(
        name: Annotated[str, Field(description="Object name (no spaces)")] = "Box",
        length: Annotated[float, Field(description="Length along X in mm")] = 10.0,
        width: Annotated[float, Field(description="Width along Y in mm")] = 10.0,
        height: Annotated[float, Field(description="Height along Z in mm")] = 10.0,
        position: Annotated[str | None, Field(description="Position as 'x,y,z' in mm")] = None,
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Create a Part::Box primitive."""
        ref = doc_ref_expr(document)
        pos_code = ""
        if position:
            pos_code = f'obj.Placement.Base = FreeCAD.Vector({position})'
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.addObject("Part::Box", "{name}")
obj.Length = {length}
obj.Width = {width}
obj.Height = {height}
{pos_code}
doc.recompute()
__result__ = f"Created Box '{{obj.Name}}' {{obj.Length}}x{{obj.Width}}x{{obj.Height}} mm"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Cylinder
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_cylinder(
        name: Annotated[str, Field(description="Object name")] = "Cylinder",
        radius: Annotated[float, Field(description="Radius in mm")] = 5.0,
        height: Annotated[float, Field(description="Height in mm")] = 10.0,
        angle: Annotated[float, Field(description="Sweep angle in degrees (360 for full)")] = 360.0,
        position: Annotated[str | None, Field(description="Position as 'x,y,z' in mm")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a Part::Cylinder primitive."""
        ref = doc_ref_expr(document)
        pos_code = f'obj.Placement.Base = FreeCAD.Vector({position})' if position else ""
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.addObject("Part::Cylinder", "{name}")
obj.Radius = {radius}
obj.Height = {height}
obj.Angle = {angle}
{pos_code}
doc.recompute()
__result__ = f"Created Cylinder '{{obj.Name}}' R={{obj.Radius}} H={{obj.Height}} mm"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Sphere
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_sphere(
        name: Annotated[str, Field(description="Object name")] = "Sphere",
        radius: Annotated[float, Field(description="Radius in mm")] = 5.0,
        position: Annotated[str | None, Field(description="Position as 'x,y,z' in mm")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a Part::Sphere primitive."""
        ref = doc_ref_expr(document)
        pos_code = f'obj.Placement.Base = FreeCAD.Vector({position})' if position else ""
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.addObject("Part::Sphere", "{name}")
obj.Radius = {radius}
{pos_code}
doc.recompute()
__result__ = f"Created Sphere '{{obj.Name}}' R={{obj.Radius}} mm"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Cone
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_cone(
        name: Annotated[str, Field(description="Object name")] = "Cone",
        radius1: Annotated[float, Field(description="Bottom radius in mm")] = 5.0,
        radius2: Annotated[float, Field(description="Top radius in mm (0 for pointed)")] = 0.0,
        height: Annotated[float, Field(description="Height in mm")] = 10.0,
        position: Annotated[str | None, Field(description="Position as 'x,y,z' in mm")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a Part::Cone primitive."""
        ref = doc_ref_expr(document)
        pos_code = f'obj.Placement.Base = FreeCAD.Vector({position})' if position else ""
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.addObject("Part::Cone", "{name}")
obj.Radius1 = {radius1}
obj.Radius2 = {radius2}
obj.Height = {height}
{pos_code}
doc.recompute()
__result__ = f"Created Cone '{{obj.Name}}' R1={{obj.Radius1}} R2={{obj.Radius2}} H={{obj.Height}} mm"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Torus
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_torus(
        name: Annotated[str, Field(description="Object name")] = "Torus",
        radius1: Annotated[float, Field(description="Major radius (center to tube center) in mm")] = 10.0,
        radius2: Annotated[float, Field(description="Minor radius (tube radius) in mm")] = 2.0,
        position: Annotated[str | None, Field(description="Position as 'x,y,z' in mm")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a Part::Torus primitive."""
        ref = doc_ref_expr(document)
        pos_code = f'obj.Placement.Base = FreeCAD.Vector({position})' if position else ""
        result = await bridge.execute(f"""
doc = {ref}
obj = doc.addObject("Part::Torus", "{name}")
obj.Radius1 = {radius1}
obj.Radius2 = {radius2}
{pos_code}
doc.recompute()
__result__ = f"Created Torus '{{obj.Name}}' R1={{obj.Radius1}} R2={{obj.Radius2}} mm"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Boolean Operations
    # ------------------------------------------------------------------

    @mcp.tool
    async def boolean_fuse(
        name: Annotated[str, Field(description="Name for the fused object")] = "Fuse",
        shape1: Annotated[str, Field(description="First object name")] = "",
        shape2: Annotated[str, Field(description="Second object name")] = "",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Boolean union (fuse) of two Part shapes."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
fuse = doc.addObject("Part::Fuse", "{name}")
fuse.Shape1 = doc.getObject("{shape1}")
fuse.Shape2 = doc.getObject("{shape2}")
doc.recompute()
__result__ = f"Fused '{{fuse.Shape1.Name}}' + '{{fuse.Shape2.Name}}' -> '{{fuse.Name}}'"
""")
        return format_result(result)

    @mcp.tool
    async def boolean_cut(
        name: Annotated[str, Field(description="Name for the cut result")] = "Cut",
        base: Annotated[str, Field(description="Base object name (kept)")] = "",
        tool: Annotated[str, Field(description="Tool object name (subtracted)")] = "",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Boolean subtraction (cut) of two Part shapes. Subtracts tool from base."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
cut = doc.addObject("Part::Cut", "{name}")
cut.Base = doc.getObject("{base}")
cut.Tool = doc.getObject("{tool}")
doc.recompute()
__result__ = f"Cut '{{cut.Base.Name}}' - '{{cut.Tool.Name}}' -> '{{cut.Name}}'"
""")
        return format_result(result)

    @mcp.tool
    async def boolean_common(
        name: Annotated[str, Field(description="Name for the intersection result")] = "Common",
        shape1: Annotated[str, Field(description="First object name")] = "",
        shape2: Annotated[str, Field(description="Second object name")] = "",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Boolean intersection (common) of two Part shapes."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
common = doc.addObject("Part::Common", "{name}")
common.Shape1 = doc.getObject("{shape1}")
common.Shape2 = doc.getObject("{shape2}")
doc.recompute()
__result__ = f"Common '{{common.Shape1.Name}}' & '{{common.Shape2.Name}}' -> '{{common.Name}}'"
""")
        return format_result(result)
