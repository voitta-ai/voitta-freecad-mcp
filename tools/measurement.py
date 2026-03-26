"""Measurement tools: distances and angles.

FreeCAD API notes:
- Vector.distanceToPoint(other) for point-to-point distance.
- Shape.distToShape(other) -> (dist, vectors, infos) for minimum distance.
- Vector.getAngle(other) for angle between vectors (radians).
- All units are mm / degrees.
"""

from typing import Annotated
from pydantic import Field

from tools._helpers import doc_ref_expr
from tools.geometry import _FACE_NORMAL_FN


def register(mcp, bridge):

    @mcp.tool
    async def measure_distance(
        point1: Annotated[str, Field(description="First point as 'x,y,z' in mm")],
        point2: Annotated[str, Field(description="Second point as 'x,y,z' in mm")],
    ) -> str:
        """Measure the straight-line distance between two 3D points (in mm)."""
        result = await bridge.execute(f"""
import json, FreeCAD as FC
p1 = FC.Vector([{point1}])
p2 = FC.Vector([{point2}])
dist = p1.distanceToPoint(p2)
diff = p2 - p1
__result__ = json.dumps({{
    "distance_mm": round(dist, 4),
    "point1": [round(v, 4) for v in p1],
    "point2": [round(v, 4) for v in p2],
    "delta": [round(diff.x, 4), round(diff.y, 4), round(diff.z, 4)],
}}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")

    @mcp.tool
    async def measure_between_objects(
        object1: Annotated[str, Field(description="First object name")],
        object2: Annotated[str, Field(description="Second object name")],
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Measure the minimum distance between two shape objects (in mm)."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import json
doc = {ref}
s1 = doc.getObject("{object1}").Shape
s2 = doc.getObject("{object2}").Shape
dist = s1.distToShape(s2)

__result__ = json.dumps({{
    "min_distance_mm": round(dist[0], 4),
    "point_on_shape1": [round(v, 4) for v in dist[1][0][0]],
    "point_on_shape2": [round(v, 4) for v in dist[1][0][1]],
}}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")

    @mcp.tool
    async def measure_angle(
        object_name: Annotated[str, Field(description="Object name that has a Shape")],
        face1_index: Annotated[int, Field(description="0-based index of first face")],
        face2_index: Annotated[int, Field(description="0-based index of second face")],
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Measure the dihedral angle between two faces (in degrees)."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import json, math, FreeCAD as FC
{_FACE_NORMAL_FN}
doc = {ref}
obj = doc.getObject("{object_name}")
f1 = obj.Shape.Faces[{face1_index}]
f2 = obj.Shape.Faces[{face2_index}]

n1 = _face_normal(f1)
n2 = _face_normal(f2)
if n1 is None or n2 is None:
    __result__ = json.dumps({{"error": "Cannot compute normal for one or both faces"}})
else:
    angle_rad = n1.getAngle(n2)
    angle_deg = math.degrees(angle_rad)
    __result__ = json.dumps({{
        "angle_degrees": round(angle_deg, 4),
        "angle_radians": round(angle_rad, 6),
        "face1_normal": [round(n1.x, 6), round(n1.y, 6), round(n1.z, 6)],
        "face2_normal": [round(n2.x, 6), round(n2.y, 6), round(n2.z, 6)],
        "type": "dihedral",
    }}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")
