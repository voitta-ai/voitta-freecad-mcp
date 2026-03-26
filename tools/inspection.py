"""Tree and object inspection tools: get_tree, get_object_properties."""

from typing import Annotated
from pydantic import Field

from tools._helpers import doc_ref_expr


def register(mcp, bridge):

    @mcp.tool
    async def get_tree(
        name: Annotated[str | None, Field(description="Document name. Uses active document if omitted.")] = None,
    ) -> str:
        """Get the full object tree of a FreeCAD document.

        Returns a hierarchical JSON with every object, its type, label, visibility,
        shape info (volume, area, bounding box), and parent-child relationships.
        This is the primary tool for understanding what is in the document.
        """
        ref = doc_ref_expr(name)
        result = await bridge.execute(f"""
import json, math

doc = {ref}
if doc is None:
    __result__ = json.dumps({{"error": "No active document"}})
else:
    def shape_info(obj):
        info = {{}}
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            return info
        s = obj.Shape
        info["type"] = s.ShapeType
        if s.ShapeType == "Solid" or s.ShapeType == "Compound":
            try:
                info["volume_mm3"] = round(s.Volume, 4)
                info["area_mm2"] = round(s.Area, 4)
            except Exception:
                pass
        info["face_count"] = len(s.Faces)
        info["edge_count"] = len(s.Edges)
        info["vertex_count"] = len(s.Vertexes)
        bb = s.BoundBox
        info["bounding_box"] = {{
            "min": [round(bb.XMin, 4), round(bb.YMin, 4), round(bb.ZMin, 4)],
            "max": [round(bb.XMax, 4), round(bb.YMax, 4), round(bb.ZMax, 4)],
            "size": [round(bb.XLength, 4), round(bb.YLength, 4), round(bb.ZLength, 4)],
        }}
        return info

    def obj_entry(obj):
        entry = {{
            "name": obj.Name,
            "label": obj.Label,
            "type": obj.TypeId,
            "visible": obj.ViewObject.Visibility if hasattr(obj, "ViewObject") and obj.ViewObject else None,
        }}
        si = shape_info(obj)
        if si:
            entry["shape"] = si
        if hasattr(obj, "Placement"):
            p = obj.Placement
            entry["placement"] = {{
                "position": [round(p.Base.x, 4), round(p.Base.y, 4), round(p.Base.z, 4)],
                "rotation": list(round(v, 6) for v in p.Rotation.Q),
            }}
        children = []
        if hasattr(obj, "Group"):
            for child in obj.Group:
                children.append(obj_entry(child))
        entry["children"] = children
        return entry

    top_objects = [o for o in doc.Objects if len(o.InList) == 0]
    if not top_objects:
        top_objects = doc.Objects

    tree = {{
        "document": doc.Name,
        "label": doc.Label,
        "file": doc.FileName or "(unsaved)",
        "object_count": len(doc.Objects),
        "objects": [obj_entry(o) for o in top_objects],
    }}
    __result__ = json.dumps(tree, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result") or "Empty document."

    @mcp.tool
    async def get_object_properties(
        object_name: Annotated[str, Field(description="Internal name of the object")],
        document: Annotated[str | None, Field(description="Document name. Uses active if omitted.")] = None,
    ) -> str:
        """Get all properties of a specific object including shape details, parameters, and constraints."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import json
doc = {ref}
obj = doc.getObject("{object_name}")
if obj is None:
    __result__ = json.dumps({{"error": "Object '{object_name}' not found"}})
else:
    props = {{}}
    for p in obj.PropertiesList:
        try:
            val = getattr(obj, p)
            if hasattr(val, "Value"):
                props[p] = val.Value
            elif isinstance(val, (int, float, str, bool, list)):
                props[p] = val
            elif hasattr(val, "x") and hasattr(val, "y") and hasattr(val, "z"):
                props[p] = [round(val.x, 4), round(val.y, 4), round(val.z, 4)]
            else:
                props[p] = str(val)
        except Exception:
            props[p] = "<unreadable>"
    __result__ = json.dumps({{
        "name": obj.Name, "label": obj.Label, "type": obj.TypeId, "properties": props
    }}, indent=2, default=str)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result")
