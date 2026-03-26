"""Geometry query tools: face/edge info and filtering by criteria.

FreeCAD API notes:
- Face normals use f.normalAt(u, v) which works on all surface types.
- Surface/curve types use .TypeId (e.g. "Part::GeomPlane") stripped to short names.
- All units are mm (FreeCAD internal unit).
"""

from typing import Annotated
from pydantic import Field

from tools._helpers import doc_ref_expr


# -- FreeCAD-side helper snippets (injected into exec calls) ------------------

_FACE_DETAIL_FN = """
def _face_detail(f, idx):
    info = {
        "index": idx,
        "area_mm2": round(f.Area, 4),
        "centroid": [round(c, 4) for c in f.CenterOfGravity],
        "surface_type": f.Surface.TypeId.replace("Part::Geom", ""),
    }
    try:
        uv = f.Surface.parameter(f.CenterOfGravity)
        n = f.normalAt(uv[0], uv[1])
        info["normal"] = [round(n.x, 6), round(n.y, 6), round(n.z, 6)]
    except Exception:
        try:
            n = f.normalAt(0, 0)
            info["normal"] = [round(n.x, 6), round(n.y, 6), round(n.z, 6)]
        except Exception:
            pass
    if hasattr(f.Surface, "Radius"):
        info["radius_mm"] = round(f.Surface.Radius, 4)
    if hasattr(f.Surface, "Center"):
        info["center"] = [round(v, 4) for v in f.Surface.Center]
    info["edge_count"] = len(f.Edges)
    info["vertex_count"] = len(f.Vertexes)
    return info
"""

_EDGE_DETAIL_FN = """
def _edge_detail(e, idx):
    curve = e.Curve
    info = {
        "index": idx,
        "length_mm": round(e.Length, 4),
        "curve_type": curve.TypeId.replace("Part::Geom", ""),
        "start": [round(v, 4) for v in e.Vertexes[0].Point] if e.Vertexes else None,
        "end": [round(v, 4) for v in e.Vertexes[-1].Point] if len(e.Vertexes) > 1 else None,
    }
    if hasattr(curve, "Radius"):
        info["radius_mm"] = round(curve.Radius, 4)
    if hasattr(curve, "Direction"):
        info["direction"] = [round(v, 6) for v in curve.Direction]
    if hasattr(curve, "Center"):
        info["center"] = [round(v, 4) for v in curve.Center]
    if hasattr(curve, "Axis"):
        info["axis"] = [round(v, 6) for v in curve.Axis]
    return info
"""

_FACE_NORMAL_FN = """
def _face_normal(f):
    try:
        uv = f.Surface.parameter(f.CenterOfGravity)
        return f.normalAt(uv[0], uv[1])
    except Exception:
        try:
            return f.normalAt(0, 0)
        except Exception:
            return None
"""


def register(mcp, bridge):

    @mcp.tool
    async def get_face_info(
        object_name: Annotated[str, Field(description="Object name that has a Shape")],
        face_index: Annotated[int | None, Field(description="0-based face index. Omit to list all faces.")] = None,
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Get detailed info about faces of a shape: surface type, area, normal, centroid.

        Omit face_index to get a summary of all faces. Provide it to get details of one face.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import json
{_FACE_DETAIL_FN}
doc = {ref}
obj = doc.getObject("{object_name}")
shape = obj.Shape
face_index = {face_index!r}

if face_index is not None:
    f = shape.Faces[face_index]
    __result__ = json.dumps(_face_detail(f, face_index), indent=2)
else:
    faces = [_face_detail(f, i) for i, f in enumerate(shape.Faces)]
    __result__ = json.dumps({{"object": obj.Name, "face_count": len(faces), "faces": faces}}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")

    @mcp.tool
    async def get_edge_info(
        object_name: Annotated[str, Field(description="Object name that has a Shape")],
        edge_index: Annotated[int | None, Field(description="0-based edge index. Omit to list all edges.")] = None,
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Get detailed info about edges of a shape: curve type, length, start/end points.

        Omit edge_index to get a summary of all edges. Provide it to get details of one edge.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import json
{_EDGE_DETAIL_FN}
doc = {ref}
obj = doc.getObject("{object_name}")
shape = obj.Shape
edge_index = {edge_index!r}

if edge_index is not None:
    e = shape.Edges[edge_index]
    __result__ = json.dumps(_edge_detail(e, edge_index), indent=2)
else:
    edges = [_edge_detail(e, i) for i, e in enumerate(shape.Edges)]
    __result__ = json.dumps({{"object": obj.Name, "edge_count": len(edges), "edges": edges}}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")

    @mcp.tool
    async def find_faces_by_criteria(
        object_name: Annotated[str, Field(description="Object name that has a Shape")],
        surface_type: Annotated[str | None, Field(description="Filter: 'Plane','Cylinder','Cone','Sphere','Toroid'")] = None,
        area_min: Annotated[float | None, Field(description="Minimum face area in mm^2")] = None,
        area_max: Annotated[float | None, Field(description="Maximum face area in mm^2")] = None,
        normal_direction: Annotated[str | None, Field(description="Filter faces by normal direction, e.g. '0,0,1' for Z-up. Tolerance ~5 degrees.")] = None,
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Find faces matching criteria. All criteria are ANDed together."""
        ref = doc_ref_expr(document)
        normal_vec = f"[{normal_direction}]" if normal_direction else "None"
        result = await bridge.execute(f"""
import json, math
{_FACE_NORMAL_FN}
doc = {ref}
obj = doc.getObject("{object_name}")
shape = obj.Shape

surface_type = {surface_type!r}
area_min = {area_min!r}
area_max = {area_max!r}
normal_vec = {normal_vec}
angle_tol = math.radians(5)

matches = []
for i, f in enumerate(shape.Faces):
    stype = f.Surface.TypeId.replace("Part::Geom", "")
    if surface_type and surface_type.lower() not in stype.lower():
        continue
    if area_min is not None and f.Area < area_min:
        continue
    if area_max is not None and f.Area > area_max:
        continue
    fn = _face_normal(f)
    if normal_vec is not None:
        if fn is None:
            continue
        import FreeCAD as FC
        n = FC.Vector(normal_vec)
        if n.Length > 0:
            n.normalize()
            angle = n.getAngle(fn)
            if angle > angle_tol and abs(math.pi - angle) > angle_tol:
                continue
    info = {{
        "index": i,
        "area_mm2": round(f.Area, 4),
        "centroid": [round(c, 4) for c in f.CenterOfGravity],
        "surface_type": stype,
    }}
    if fn is not None:
        info["normal"] = [round(fn.x, 6), round(fn.y, 6), round(fn.z, 6)]
    matches.append(info)

__result__ = json.dumps({{"object": obj.Name, "match_count": len(matches), "faces": matches}}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")

    @mcp.tool
    async def find_edges_by_criteria(
        object_name: Annotated[str, Field(description="Object name that has a Shape")],
        curve_type: Annotated[str | None, Field(description="Filter: 'Line','Circle','BSplineCurve','Ellipse'")] = None,
        length_min: Annotated[float | None, Field(description="Minimum edge length in mm")] = None,
        length_max: Annotated[float | None, Field(description="Maximum edge length in mm")] = None,
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Find edges matching criteria. All criteria are ANDed together."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import json
doc = {ref}
obj = doc.getObject("{object_name}")
shape = obj.Shape

curve_type = {curve_type!r}
length_min = {length_min!r}
length_max = {length_max!r}

matches = []
for i, e in enumerate(shape.Edges):
    ctype = e.Curve.TypeId.replace("Part::Geom", "")
    if curve_type and curve_type.lower() not in ctype.lower():
        continue
    if length_min is not None and e.Length < length_min:
        continue
    if length_max is not None and e.Length > length_max:
        continue
    info = {{
        "index": i,
        "length_mm": round(e.Length, 4),
        "curve_type": ctype,
    }}
    if e.Vertexes:
        info["start"] = [round(v, 4) for v in e.Vertexes[0].Point]
    if len(e.Vertexes) > 1:
        info["end"] = [round(v, 4) for v in e.Vertexes[-1].Point]
    matches.append(info)

__result__ = json.dumps({{"object": obj.Name, "match_count": len(matches), "edges": matches}}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")
