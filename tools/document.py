"""Document management tools: list, create, open, close, save, set active, list objects, workbenches."""

from typing import Annotated
from pydantic import Field

from tools._helpers import format_result, doc_ref_expr


def register(mcp, bridge):

    @mcp.tool
    async def list_documents() -> str:
        """List all open FreeCAD documents with their object counts."""
        result = await bridge.execute("""
import json
docs = {}
for name, doc in FreeCAD.listDocuments().items():
    docs[name] = {
        "label": doc.Label,
        "object_count": len(doc.Objects),
        "file_name": doc.FileName or "(unsaved)",
        "is_active": (FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.Name == name),
    }
__result__ = json.dumps(docs, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result") or "No documents open."

    @mcp.tool
    async def create_document(
        name: Annotated[str, Field(description="Internal name for the document (no spaces)")] = "Unnamed",
        label: Annotated[str | None, Field(description="Display label (can contain spaces). Defaults to name.")] = None,
    ) -> str:
        """Create a new empty FreeCAD document."""
        label_code = f'doc.Label = """{label}"""' if label else ""
        result = await bridge.execute(f"""
doc = FreeCAD.newDocument("{name}")
{label_code}
__result__ = f"Created document '{{doc.Name}}' (label: '{{doc.Label}}')"
""")
        return format_result(result)

    @mcp.tool
    async def close_document(
        name: Annotated[str, Field(description="Internal name of the document to close")],
        save: Annotated[bool, Field(description="Save before closing")] = False,
    ) -> str:
        """Close a FreeCAD document, optionally saving it first."""
        save_code = f'FreeCAD.getDocument("{name}").save()' if save else ""
        result = await bridge.execute(f"""
{save_code}
FreeCAD.closeDocument("{name}")
__result__ = "Document '{name}' closed."
""")
        return format_result(result)

    @mcp.tool
    async def save_document(
        name: Annotated[str | None, Field(description="Document name. Uses active document if omitted.")] = None,
        path: Annotated[str | None, Field(description="File path to save to. Uses current path if omitted.")] = None,
    ) -> str:
        """Save a FreeCAD document to disk."""
        ref = doc_ref_expr(name)
        save_call = f'doc.saveAs("{path}")' if path else "doc.save()"
        result = await bridge.execute(f"""
doc = {ref}
if doc is None:
    __result__ = "No active document."
else:
    {save_call}
    __result__ = f"Saved '{{doc.Name}}' to {{doc.FileName}}"
""")
        return format_result(result)

    @mcp.tool
    async def open_document(
        path: Annotated[str, Field(description="Full file path to .FCStd file")],
    ) -> str:
        """Open an existing FreeCAD document from disk."""
        result = await bridge.execute(f"""
doc = FreeCAD.open("{path}")
__result__ = f"Opened '{{doc.Name}}' ({{len(doc.Objects)}} objects) from {{doc.FileName}}"
""")
        return format_result(result)

    @mcp.tool
    async def set_active_document(
        name: Annotated[str, Field(description="Internal name of the document to activate")],
    ) -> str:
        """Set the active FreeCAD document."""
        result = await bridge.execute(f"""
FreeCAD.setActiveDocument("{name}")
FreeCADGui.setActiveDocument("{name}")
__result__ = f"Active document is now '{{FreeCAD.ActiveDocument.Name}}'"
""")
        return format_result(result)

    @mcp.tool
    async def get_document_objects(
        name: Annotated[str | None, Field(description="Document name. Uses active document if omitted.")] = None,
    ) -> str:
        """List all objects in a FreeCAD document with their types and labels."""
        ref = doc_ref_expr(name)
        result = await bridge.execute(f"""
import json
doc = {ref}
if doc is None:
    __result__ = json.dumps({{"error": "No active document"}})
else:
    objects = []
    for obj in doc.Objects:
        objects.append({{
            "name": obj.Name,
            "label": obj.Label,
            "type": obj.TypeId,
        }})
    __result__ = json.dumps(objects, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result") or "No objects."

    # ------------------------------------------------------------------
    # Workbenches
    # ------------------------------------------------------------------

    @mcp.tool
    async def list_workbenches() -> str:
        """List all available FreeCAD workbenches and show which one is active."""
        result = await bridge.execute("""
import json
wbs = {}
active = FreeCADGui.activeWorkbench().name()
for name, wb in FreeCADGui.listWorkbenches().items():
    wbs[name] = {
        "label": getattr(wb, "MenuText", name),
        "is_active": (name == active),
    }
__result__ = json.dumps({"active": active, "workbenches": wbs}, indent=2)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result") or "{}"

    @mcp.tool
    async def activate_workbench(
        name: Annotated[str, Field(
            description="Workbench name, e.g. 'PartDesignWorkbench', 'PartWorkbench', "
            "'SketcherWorkbench', 'AssemblyWorkbench', 'DraftWorkbench', 'BIMWorkbench', "
            "'CAMWorkbench', 'FEMWorkbench', 'MeshWorkbench', 'OpenSCADWorkbench', "
            "'SurfaceWorkbench', 'TechDrawWorkbench', 'SpreadsheetWorkbench'"
        )],
    ) -> str:
        """Switch the active FreeCAD workbench.

        Common workbenches:
          PartDesignWorkbench - parametric solid modeling (Body/Sketch/Pad/Pocket)
          PartWorkbench - CSG primitives and booleans
          SketcherWorkbench - 2D constrained sketching
          AssemblyWorkbench - multi-body assembly with joints
          DraftWorkbench - 2D drafting
          BIMWorkbench - building/architecture
          CAMWorkbench - CNC toolpath generation
          FEMWorkbench - finite element analysis
          MeshWorkbench - mesh editing
          SpreadsheetWorkbench - spreadsheet/parameters
          TechDrawWorkbench - technical drawings
        """
        result = await bridge.execute(f"""
FreeCADGui.activateWorkbench("{name}")
active = FreeCADGui.activeWorkbench().name()
__result__ = f"Activated workbench: {{active}}"
""")
        return format_result(result)
