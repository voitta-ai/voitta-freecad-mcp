"""Assembly tools: create assemblies, insert parts, ground parts, create joints, solve.

Follows the FreeCAD Assembly workbench workflow (based on Assembly::AssemblyObject,
Assembly::JointGroup, and JointObject from the FreeCAD source).

Typical workflow:
  1. create_assembly -> creates AssemblyObject + JointGroup
  2. assembly_add_part -> add Part::Box / Body / etc inside the assembly
  3. assembly_ground_part -> fix one part in space
  4. assembly_create_joint -> connect two parts with a joint (Fixed, Revolute, etc.)
  5. assembly_solve -> run the constraint solver

Joint types (integer index):
  0=Fixed, 1=Revolute, 2=Cylindrical, 3=Slider, 4=Ball,
  5=Distance, 6=Parallel, 7=Perpendicular, 8=Angle,
  9=RackPinion, 10=Screw, 11=Gears, 12=Belt
"""

from typing import Annotated
from pydantic import Field

from tools._helpers import format_result, doc_ref_expr


# Maps readable names to JointObject type indices
JOINT_TYPE_MAP = {
    "Fixed": 0,
    "Revolute": 1,
    "Cylindrical": 2,
    "Slider": 3,
    "Ball": 4,
    "Distance": 5,
    "Parallel": 6,
    "Perpendicular": 7,
    "Angle": 8,
    "RackPinion": 9,
    "Screw": 10,
    "Gears": 11,
    "Belt": 12,
}


def register(mcp, bridge):

    # ------------------------------------------------------------------
    # Create Assembly
    # ------------------------------------------------------------------

    @mcp.tool
    async def create_assembly(
        name: Annotated[str, Field(description="Assembly name")] = "Assembly",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create an Assembly::AssemblyObject with its JointGroup.

        This is the top-level container for multi-body assembly.
        Parts are added inside the assembly, then connected with joints.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
assembly = doc.addObject("Assembly::AssemblyObject", "{name}")
joint_group = assembly.newObject("Assembly::JointGroup", "Joints")
doc.recompute()
__result__ = f"Created Assembly '{{assembly.Name}}' with JointGroup '{{joint_group.Name}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Add Part to Assembly
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_add_part(
        assembly_name: Annotated[str, Field(description="Assembly object name")],
        part_type: Annotated[str, Field(
            description="Part type to create: 'Part::Box', 'Part::Cylinder', "
            "'Part::Sphere', 'Part::Cone', 'Part::Torus'"
        )] = "Part::Box",
        part_name: Annotated[str, Field(description="Name for the new part")] = "Part",
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Add a new primitive part directly inside an assembly.

        The part is created as a child of the assembly (assembly.newObject).
        Set dimensions afterwards using run_script or set_placement.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
assembly = doc.getObject("{assembly_name}")
part = assembly.newObject("{part_type}", "{part_name}")
doc.recompute()
__result__ = f"Added {{part.TypeId}} '{{part.Name}}' to Assembly '{{assembly.Name}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Insert Existing Object into Assembly
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_insert_object(
        assembly_name: Annotated[str, Field(description="Assembly object name")],
        object_name: Annotated[str, Field(description="Existing object to insert (will be linked)")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Insert an existing document object into an assembly as an App::Link.

        Use this when you have a Body or Part already in the document
        and want to include it in an assembly.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
assembly = doc.getObject("{assembly_name}")
source = doc.getObject("{object_name}")
link = assembly.newObject("App::Link", source.Name + "_Link")
link.setLink(source)
doc.recompute()
__result__ = f"Inserted '{{source.Name}}' into Assembly '{{assembly.Name}}' as link '{{link.Name}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Ground a Part
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_ground_part(
        assembly_name: Annotated[str, Field(description="Assembly object name")],
        part_name: Annotated[str, Field(description="Part name to ground (fix in space)")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Ground (fix in space) a part inside an assembly.

        At least one part must be grounded for the assembly solver to work.
        This creates a GroundedJoint that prevents the part from moving.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import JointObject
doc = {ref}
assembly = doc.getObject("{assembly_name}")

# Find the JointGroup
joint_group = None
for obj in assembly.Group:
    if obj.TypeId == "Assembly::JointGroup":
        joint_group = obj
        break
if joint_group is None:
    joint_group = assembly.newObject("Assembly::JointGroup", "Joints")

part = doc.getObject("{part_name}")
ground = joint_group.newObject("App::FeaturePython", "GroundedJoint")
JointObject.GroundedJoint(ground, part)
if FreeCAD.GuiUp:
    JointObject.ViewProviderGroundedJoint(ground.ViewObject)
doc.recompute()
__result__ = f"Grounded '{{part.Name}}' in Assembly '{{assembly.Name}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Create Joint
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_create_joint(
        assembly_name: Annotated[str, Field(description="Assembly object name")],
        joint_type: Annotated[str, Field(
            description="Joint type: Fixed, Revolute, Cylindrical, Slider, Ball, "
            "Distance, Parallel, Perpendicular, Angle, RackPinion, Screw, Gears, Belt"
        )],
        part1_name: Annotated[str, Field(description="First part name")],
        element1: Annotated[str, Field(
            description="First element reference, e.g. 'Face6' or 'Edge1'"
        )],
        vertex1: Annotated[str, Field(
            description="First vertex for orientation, e.g. 'Vertex7'"
        )],
        part2_name: Annotated[str, Field(description="Second part name")],
        element2: Annotated[str, Field(
            description="Second element reference, e.g. 'Face6' or 'Edge1'"
        )],
        vertex2: Annotated[str, Field(
            description="Second vertex for orientation, e.g. 'Vertex7'"
        )],
        name: Annotated[str, Field(description="Joint name")] = "Joint",
        distance: Annotated[float | None, Field(
            description="Distance value for Distance joint type"
        )] = None,
        angle: Annotated[float | None, Field(
            description="Angle value in degrees for Angle joint type"
        )] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Create a joint between two parts in an assembly.

        Each connector is specified by a part, a face/edge element, and a vertex
        for orientation. Use get_face_info/get_edge_info to find element names.

        The element names use FreeCAD's topological naming: Face1..FaceN, Edge1..EdgeN,
        Vertex1..VertexN (1-based, unlike the 0-based indices in get_face_info).

        Example: assembly_create_joint(assembly_name="Assembly", joint_type="Fixed",
          part1_name="Box", element1="Face6", vertex1="Vertex7",
          part2_name="Box001", element2="Face6", vertex2="Vertex7")
        """
        jtype = JOINT_TYPE_MAP.get(joint_type, 0)
        ref = doc_ref_expr(document)

        extra_props = ""
        if distance is not None:
            extra_props += f"\njoint.Distance = {distance}"
        if angle is not None:
            extra_props += f"\nimport math\njoint.Angle = {angle}"

        result = await bridge.execute(f"""
import JointObject
doc = {ref}
assembly = doc.getObject("{assembly_name}")

# Find the JointGroup
joint_group = None
for obj in assembly.Group:
    if obj.TypeId == "Assembly::JointGroup":
        joint_group = obj
        break
if joint_group is None:
    joint_group = assembly.newObject("Assembly::JointGroup", "Joints")

joint_obj = joint_group.newObject("App::FeaturePython", "{name}")
JointObject.Joint(joint_obj, {jtype})
if FreeCAD.GuiUp:
    JointObject.ViewProviderJoint(joint_obj.ViewObject)

part1 = doc.getObject("{part1_name}")
part2 = doc.getObject("{part2_name}")

refs = [
    [part1, ["{element1}", "{vertex1}"]],
    [part2, ["{element2}", "{vertex2}"]],
]
joint_obj.Proxy.setJointConnectors(joint_obj, refs)
{extra_props}
doc.recompute()
__result__ = f"Created {{joint_obj.JointType}} joint '{{joint_obj.Name}}' between '{{part1.Name}}' and '{{part2.Name}}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Solve Assembly
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_solve(
        assembly_name: Annotated[str, Field(description="Assembly object name")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Run the assembly constraint solver.

        This recomputes the assembly, solving all joint constraints
        to position the parts correctly.
        """
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
assembly = doc.getObject("{assembly_name}")
assembly.recompute(True)
doc.recompute()
__result__ = f"Assembly '{{assembly.Name}}' solved"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # List Joints
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_list_joints(
        assembly_name: Annotated[str, Field(description="Assembly object name")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """List all joints in an assembly with their types and connected parts."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
import json
doc = {ref}
assembly = doc.getObject("{assembly_name}")

joints = []
for obj in assembly.Group:
    if obj.TypeId == "Assembly::JointGroup":
        for j in obj.Group:
            info = {{"name": j.Name, "label": j.Label}}
            if hasattr(j, "ObjectToGround") and j.ObjectToGround:
                info["type"] = "Grounded"
                info["part"] = j.ObjectToGround.Name
            elif hasattr(j, "JointType"):
                info["type"] = j.JointType
                if hasattr(j, "Reference1") and j.Reference1:
                    info["reference1"] = str(j.Reference1)
                if hasattr(j, "Reference2") and j.Reference2:
                    info["reference2"] = str(j.Reference2)
                if hasattr(j, "Distance"):
                    info["distance"] = j.Distance
                if hasattr(j, "Angle"):
                    info["angle"] = j.Angle
            else:
                info["type"] = "Unknown"
            joints.append(info)

# Also list parts in the assembly
parts = []
for obj in assembly.Group:
    if obj.TypeId != "Assembly::JointGroup":
        parts.append({{"name": obj.Name, "label": obj.Label, "type": obj.TypeId}})

__result__ = json.dumps({{"assembly": assembly.Name, "parts": parts, "joints": joints}}, indent=2, default=str)
""")
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return result.get("result") or "{}"

    # ------------------------------------------------------------------
    # Delete Joint
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_delete_joint(
        assembly_name: Annotated[str, Field(description="Assembly object name")],
        joint_name: Annotated[str, Field(description="Joint object name to delete")],
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Delete a joint from an assembly."""
        ref = doc_ref_expr(document)
        result = await bridge.execute(f"""
doc = {ref}
doc.removeObject("{joint_name}")
doc.recompute()
__result__ = "Deleted joint '{joint_name}'"
""")
        return format_result(result)

    # ------------------------------------------------------------------
    # Set Part Placement in Assembly
    # ------------------------------------------------------------------

    @mcp.tool
    async def assembly_set_part_placement(
        part_name: Annotated[str, Field(description="Part name inside the assembly")],
        position: Annotated[str, Field(description="Position as 'x,y,z' in mm")],
        rotation: Annotated[str | None, Field(
            description="Rotation as 'yaw,pitch,roll' in degrees"
        )] = None,
        document: Annotated[str | None, Field(description="Document name")] = None,
    ) -> str:
        """Set the placement of a part inside an assembly (before solving)."""
        ref = doc_ref_expr(document)
        rot_code = ""
        if rotation:
            rot_code = f"FreeCAD.Rotation({rotation})"
        else:
            rot_code = "FreeCAD.Rotation()"
        result = await bridge.execute(f"""
doc = {ref}
part = doc.getObject("{part_name}")
part.Placement = FreeCAD.Placement(FreeCAD.Vector({position}), {rot_code})
doc.recompute()
__result__ = f"Set placement of '{{part.Name}}' to pos={{part.Placement.Base}}"
""")
        return format_result(result)
