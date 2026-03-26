"""PartDesign workflow tools: Body, Sketch, Pad, Pocket, Revolution, Fillet, Chamfer.

Follows the standard FreeCAD PartDesign workflow:
  1. Create a Body
  2. Create a Sketch inside the Body (attached to a plane)
  3. Add geometry to the Sketch (lines, circles, arcs, rectangles)
  4. Add constraints to the Sketch
  5. Apply features: Pad, Pocket, Revolution, Groove
  6. Apply dress-ups: Fillet, Chamfer
"""

from typing import Annotated
from pydantic import Field

from tools._helpers import format_result, doc_ref_expr


def register(mcp, bridge):

    # ------------------------------------------------------------------
    # Body
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_body(
        name: Annotated[str, Field(description="Body name")] = "Body",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::Body. This is the container for all PartDesign features."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
body = doc.addObject("PartDesign::Body", "{name}")
doc.recompute()
__result__ = f"Created Body '{{body.Name}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Sketch
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_sketch(
        body_name: Annotated[str, Field(description="Body to attach the sketch to")],
        plane: Annotated[str, Field(description="Attachment plane: 'XY', 'XZ', or 'YZ'")] = "XY",
        name: Annotated[str, Field(description="Sketch name")] = "Sketch",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a Sketcher::SketchObject attached to a plane inside a Body.

        The plane can be 'XY' (top), 'XZ' (front), or 'YZ' (right).
        After creating, use sketch_add_line/circle/rectangle to add geometry,
        then sketch_add_constraint to constrain it.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
sketch = doc.addObject("Sketcher::SketchObject", "{name}")
body.addObject(sketch)

plane_map = {{
    "XY": (doc.getObject("XY_Plane"), body.Origin.OriginFeatures[3]),
    "XZ": (doc.getObject("XZ_Plane"), body.Origin.OriginFeatures[4]),
    "YZ": (doc.getObject("YZ_Plane"), body.Origin.OriginFeatures[5]),
}}
plane_key = "{plane}".upper()
if plane_key in plane_map:
    target = plane_map[plane_key]
    # Try standard origin planes first, fall back to origin features
    plane_obj = target[0] or target[1]
    sketch.AttachmentSupport = [(plane_obj, "")]
    sketch.MapMode = "FlatFace"
else:
    sketch.MapMode = "Deactivated"

doc.recompute()
__result__ = f"Created Sketch '{{sketch.Name}}' on {{plane_key}} plane in Body '{{body.Name}}'"
""")
        return format_result(result)

    @mcp.tool
    async def sketch_add_line(
        sketch_name: Annotated[str, Field(description="Sketch object name")],
        x1: Annotated[float, Field(description="Start X in mm")],
        y1: Annotated[float, Field(description="Start Y in mm")],
        x2: Annotated[float, Field(description="End X in mm")],
        y2: Annotated[float, Field(description="End Y in mm")],
        construction: Annotated[bool, Field(description="Construction line (not used for solid)")] = False,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Add a line segment to a sketch. Returns the geometry index."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import Part
doc = {ref}
sketch = doc.getObject("{sketch_name}")
idx = sketch.addGeometry(
    Part.LineSegment(FreeCAD.Vector({x1}, {y1}, 0), FreeCAD.Vector({x2}, {y2}, 0)),
    {construction}
)
doc.recompute()
__result__ = f"Added line [{{idx}}]: ({x1},{y1})->({x2},{y2})"
""")
        return format_result(result)

    @mcp.tool
    async def sketch_add_rectangle(
        sketch_name: Annotated[str, Field(description="Sketch object name")],
        x1: Annotated[float, Field(description="Corner 1 X in mm")],
        y1: Annotated[float, Field(description="Corner 1 Y in mm")],
        x2: Annotated[float, Field(description="Corner 2 X in mm")],
        y2: Annotated[float, Field(description="Corner 2 Y in mm")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Add a closed rectangle to a sketch (4 lines + coincident constraints).

        Returns the geometry indices of the 4 line segments.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import Part, Sketcher
doc = {ref}
sketch = doc.getObject("{sketch_name}")
x1, y1, x2, y2 = {x1}, {y1}, {x2}, {y2}
i0 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x1, y1, 0), FreeCAD.Vector(x2, y1, 0)), False)
i1 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x2, y1, 0), FreeCAD.Vector(x2, y2, 0)), False)
i2 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x2, y2, 0), FreeCAD.Vector(x1, y2, 0)), False)
i3 = sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(x1, y2, 0), FreeCAD.Vector(x1, y1, 0)), False)
sketch.addConstraint(Sketcher.Constraint("Coincident", i0, 2, i1, 1))
sketch.addConstraint(Sketcher.Constraint("Coincident", i1, 2, i2, 1))
sketch.addConstraint(Sketcher.Constraint("Coincident", i2, 2, i3, 1))
sketch.addConstraint(Sketcher.Constraint("Coincident", i3, 2, i0, 1))
doc.recompute()
__result__ = f"Added rectangle lines [{{i0}},{{i1}},{{i2}},{{i3}}]"
""")
        return format_result(result)

    @mcp.tool
    async def sketch_add_circle(
        sketch_name: Annotated[str, Field(description="Sketch object name")],
        cx: Annotated[float, Field(description="Center X in mm")],
        cy: Annotated[float, Field(description="Center Y in mm")],
        radius: Annotated[float, Field(description="Radius in mm")],
        construction: Annotated[bool, Field(description="Construction geometry")] = False,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Add a circle to a sketch. Returns the geometry index."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import Part
doc = {ref}
sketch = doc.getObject("{sketch_name}")
idx = sketch.addGeometry(
    Part.Circle(FreeCAD.Vector({cx}, {cy}, 0), FreeCAD.Vector(0, 0, 1), {radius}),
    {construction}
)
doc.recompute()
__result__ = f"Added circle [{{idx}}]: center=({cx},{cy}) R={radius}"
""")
        return format_result(result)

    @mcp.tool
    async def sketch_add_arc(
        sketch_name: Annotated[str, Field(description="Sketch object name")],
        cx: Annotated[float, Field(description="Center X in mm")],
        cy: Annotated[float, Field(description="Center Y in mm")],
        radius: Annotated[float, Field(description="Radius in mm")],
        start_angle: Annotated[float, Field(description="Start angle in radians")],
        end_angle: Annotated[float, Field(description="End angle in radians")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Add an arc of circle to a sketch. Returns the geometry index."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import Part
doc = {ref}
sketch = doc.getObject("{sketch_name}")
idx = sketch.addGeometry(
    Part.ArcOfCircle(
        Part.Circle(FreeCAD.Vector({cx}, {cy}, 0), FreeCAD.Vector(0, 0, 1), {radius}),
        {start_angle}, {end_angle}
    ),
    False
)
doc.recompute()
__result__ = f"Added arc [{{idx}}]: center=({cx},{cy}) R={radius}"
""")
        return format_result(result)

    @mcp.tool
    async def sketch_add_constraint(
        sketch_name: Annotated[str, Field(description="Sketch object name")],
        constraint_type: Annotated[str, Field(
            description="Constraint type: Coincident, Horizontal, Vertical, "
            "Perpendicular, Parallel, Tangent, Equal, Symmetric, "
            "Distance, DistanceX, DistanceY, Radius, Angle, "
            "PointOnObject, Fixed, Block"
        )],
        first_geo: Annotated[int, Field(description="First geometry index")] = 0,
        first_point: Annotated[int | None, Field(
            description="First point index: 1=start, 2=end, 3=center. Omit for whole-edge constraints."
        )] = None,
        second_geo: Annotated[int | None, Field(description="Second geometry index")] = None,
        second_point: Annotated[int | None, Field(description="Second point index")] = None,
        value: Annotated[float | None, Field(
            description="Dimension value (for Distance, DistanceX, DistanceY, Radius, Angle)"
        )] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Add a constraint to a sketch.

        Point indices: 0=whole edge, 1=start vertex, 2=end vertex, 3=center.
        Special geometry indices: -1=X axis, -2=Y axis, -3=origin.

        Examples:
          Coincident: first_geo=0, first_point=2, second_geo=1, second_point=1
          Horizontal: first_geo=0 (no points needed)
          Distance: first_geo=0, first_point=1, second_geo=0, second_point=2, value=25.0
          Radius: first_geo=0, value=5.0
        """
        ref = doc_ref_expr(document)
        # Build argument list for Sketcher.Constraint(...)
        args = [f'"{constraint_type}"', str(first_geo)]
        if first_point is not None:
            args.append(str(first_point))
        if second_geo is not None:
            args.append(str(second_geo))
            if second_point is not None:
                args.append(str(second_point))
        if value is not None:
            args.append(str(value))
        arg_str = ", ".join(args)

        result = await bridge.execute(f"""
import Sketcher
doc = {ref}
sketch = doc.getObject("{sketch_name}")
idx = sketch.addConstraint(Sketcher.Constraint({arg_str}))
doc.recompute()
__result__ = f"Added constraint [{{idx}}]: {constraint_type}"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Pad
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_pad(
        body_name: Annotated[str, Field(description="Body name")],
        sketch_name: Annotated[str, Field(description="Sketch to pad")],
        length: Annotated[float, Field(description="Pad length in mm")] = 10.0,
        name: Annotated[str, Field(description="Pad feature name")] = "Pad",
        symmetric: Annotated[bool, Field(description="Pad symmetrically (both directions)")] = False,
        reversed: Annotated[bool, Field(description="Pad in reverse direction")] = False,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::Pad (extrude a sketch into a solid)."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
pad = doc.addObject("PartDesign::Pad", "{name}")
body.addObject(pad)
pad.Profile = doc.getObject("{sketch_name}")
pad.Length = {length}
pad.Midplane = {symmetric}
pad.Reversed = {reversed}
doc.recompute()
vol = body.Shape.Volume if hasattr(body, "Shape") and body.Shape else 0
__result__ = f"Created Pad '{{pad.Name}}' length={length}mm, body volume={{vol:.1f}} mm3"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Pocket
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_pocket(
        body_name: Annotated[str, Field(description="Body name")],
        sketch_name: Annotated[str, Field(description="Sketch to pocket")],
        length: Annotated[float, Field(description="Pocket depth in mm")] = 5.0,
        name: Annotated[str, Field(description="Pocket feature name")] = "Pocket",
        pocket_type: Annotated[str, Field(
            description="Type: 'Length', 'ThroughAll', 'UpToFirst', 'UpToFace'"
        )] = "Length",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::Pocket (cut into existing solid using a sketch profile)."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
pocket = doc.addObject("PartDesign::Pocket", "{name}")
body.addObject(pocket)
pocket.Profile = doc.getObject("{sketch_name}")
pocket.Type = "{pocket_type}"
pocket.Length = {length}
doc.recompute()
vol = body.Shape.Volume if hasattr(body, "Shape") and body.Shape else 0
__result__ = f"Created Pocket '{{pocket.Name}}' depth={length}mm, body volume={{vol:.1f}} mm3"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Revolution
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_revolution(
        body_name: Annotated[str, Field(description="Body name")],
        sketch_name: Annotated[str, Field(description="Sketch to revolve")],
        angle: Annotated[float, Field(description="Revolution angle in degrees")] = 360.0,
        axis: Annotated[str, Field(
            description="Revolution axis: 'X', 'Y', or 'custom x,y,z'"
        )] = "X",
        name: Annotated[str, Field(description="Feature name")] = "Revolution",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::Revolution (revolve a sketch around an axis)."""
        ref = doc_ref_expr(document)
        axis_code = {
            "X": "rev.ReferenceAxis = (doc.getObject(body_name + '_Origin').OriginFeatures[0], [''])",
            "Y": "rev.ReferenceAxis = (doc.getObject(body_name + '_Origin').OriginFeatures[1], [''])",
        }.get(axis.upper(), f"rev.Axis = FreeCAD.Vector({axis})")

        result = await bridge.execute(f"""
doc = {ref}
body_name = "{body_name}"
body = doc.getObject(body_name)
rev = doc.addObject("PartDesign::Revolution", "{name}")
body.addObject(rev)
rev.Profile = doc.getObject("{sketch_name}")
rev.Angle = {angle}
try:
    {axis_code}
except Exception:
    pass
doc.recompute()
vol = body.Shape.Volume if hasattr(body, "Shape") and body.Shape else 0
__result__ = f"Created Revolution '{{rev.Name}}' angle={angle} deg, body volume={{vol:.1f}} mm3"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Groove (subtractive revolution)
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_groove(
        body_name: Annotated[str, Field(description="Body name")],
        sketch_name: Annotated[str, Field(description="Sketch to revolve-cut")],
        angle: Annotated[float, Field(description="Groove angle in degrees")] = 360.0,
        name: Annotated[str, Field(description="Feature name")] = "Groove",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::Groove (subtractive revolution)."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
groove = doc.addObject("PartDesign::Groove", "{name}")
body.addObject(groove)
groove.Profile = doc.getObject("{sketch_name}")
groove.Angle = {angle}
doc.recompute()
vol = body.Shape.Volume if hasattr(body, "Shape") and body.Shape else 0
__result__ = f"Created Groove '{{groove.Name}}' angle={angle} deg, body volume={{vol:.1f}} mm3"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Fillet
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_fillet(
        body_name: Annotated[str, Field(description="Body name")],
        base_object: Annotated[str, Field(description="Base feature name (e.g. 'Pad')")],
        edges: Annotated[str, Field(
            description="Comma-separated edge names, e.g. 'Edge1,Edge5,Edge9'"
        )],
        radius: Annotated[float, Field(description="Fillet radius in mm")] = 1.0,
        name: Annotated[str, Field(description="Feature name")] = "Fillet",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::Fillet on specified edges of a feature."""
        ref = doc_ref_expr(document)
        edge_list = [e.strip() for e in edges.split(",")]
        edge_strs = ", ".join(f'"{e}"' for e in edge_list)
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
fillet = doc.addObject("PartDesign::Fillet", "{name}")
body.addObject(fillet)
fillet.Base = (doc.getObject("{base_object}"), [{edge_strs}])
fillet.Radius = {radius}
doc.recompute()
__result__ = f"Created Fillet '{{fillet.Name}}' R={radius}mm on {len(edge_list)} edge(s)"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Chamfer
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_chamfer(
        body_name: Annotated[str, Field(description="Body name")],
        base_object: Annotated[str, Field(description="Base feature name")],
        edges: Annotated[str, Field(description="Comma-separated edge names, e.g. 'Edge1,Edge5'")],
        size: Annotated[float, Field(description="Chamfer size in mm")] = 1.0,
        name: Annotated[str, Field(description="Feature name")] = "Chamfer",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::Chamfer on specified edges of a feature."""
        ref = doc_ref_expr(document)
        edge_list = [e.strip() for e in edges.split(",")]
        edge_strs = ", ".join(f'"{e}"' for e in edge_list)
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
chamfer = doc.addObject("PartDesign::Chamfer", "{name}")
body.addObject(chamfer)
chamfer.Base = (doc.getObject("{base_object}"), [{edge_strs}])
chamfer.Size = {size}
doc.recompute()
__result__ = f"Created Chamfer '{{chamfer.Name}}' size={size}mm on {len(edge_list)} edge(s)"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # PartDesign Additive Primitives (inside a Body)
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_additive_cylinder(
        body_name: Annotated[str, Field(description="Body name")],
        radius: Annotated[float, Field(description="Radius in mm")] = 5.0,
        height: Annotated[float, Field(description="Height in mm")] = 10.0,
        name: Annotated[str, Field(description="Feature name")] = "AdditiveCylinder",
        position: Annotated[str | None, Field(description="Offset as 'x,y,z' in mm")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::AdditiveCylinder inside a Body."""
        ref = doc_ref_expr(document)
        pos_code = ""
        if position:
            pos_code = f'cyl.AttachmentOffset.Base = FreeCAD.Vector({position})'
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
cyl = doc.addObject("PartDesign::AdditiveCylinder", "{name}")
cyl.Radius = {radius}
cyl.Height = {height}
body.addObject(cyl)
{pos_code}
doc.recompute()
__result__ = f"Created AdditiveCylinder '{{cyl.Name}}' R={radius} H={height} mm"
""")
        return format_result(result)

    @mcp.tool
    async def create_subtractive_cylinder(
        body_name: Annotated[str, Field(description="Body name")],
        radius: Annotated[float, Field(description="Radius in mm")] = 5.0,
        height: Annotated[float, Field(description="Height in mm")] = 10.0,
        name: Annotated[str, Field(description="Feature name")] = "SubtractiveCylinder",
        position: Annotated[str | None, Field(description="Offset as 'x,y,z' in mm")] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a PartDesign::SubtractiveCylinder (drill hole) inside a Body."""
        ref = doc_ref_expr(document)
        pos_code = ""
        if position:
            pos_code = f'cyl.AttachmentOffset.Base = FreeCAD.Vector({position})'
        result = await bridge.execute(f"""
doc = {ref}
body = doc.getObject("{body_name}")
cyl = doc.addObject("PartDesign::SubtractiveCylinder", "{name}")
cyl.Radius = {radius}
cyl.Height = {height}
body.addObject(cyl)
{pos_code}
doc.recompute()
__result__ = f"Created SubtractiveCylinder '{{cyl.Name}}' R={radius} H={height} mm"
""")
        return format_result(result)
