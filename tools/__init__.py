"""FreeCAD MCP tools package.

Each module registers its tools onto an mcp instance via a register(mcp, bridge) function.
"""

from tools.document import register as register_document
from tools.inspection import register as register_inspection
from tools.screenshot import register as register_screenshot
from tools.camera import register as register_camera
from tools.geometry import register as register_geometry
from tools.measurement import register as register_measurement
from tools.primitives import register as register_primitives
from tools.partdesign import register as register_partdesign
from tools.transform import register as register_transform
from tools.assembly import register as register_assembly
from tools.script import register as register_script


def register_all(mcp, bridge):
    """Register every tool group onto *mcp*."""
    register_document(mcp, bridge)
    register_inspection(mcp, bridge)
    register_screenshot(mcp, bridge)
    register_camera(mcp, bridge)
    register_geometry(mcp, bridge)
    register_measurement(mcp, bridge)
    register_primitives(mcp, bridge)
    register_partdesign(mcp, bridge)
    register_transform(mcp, bridge)
    register_assembly(mcp, bridge)
    register_script(mcp, bridge)
