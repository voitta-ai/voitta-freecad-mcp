"""Camera tools: get and set the 3D view camera."""

from typing import Annotated
from pydantic import Field


def register(mcp, bridge):

    @mcp.tool
    async def get_camera() -> str:
        """Get the current 3D view camera position and type."""
        result = await bridge.get_camera()
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return (
            f"Camera type: {result.get('camera_type')}\n"
            f"Camera string:\n{result.get('camera_string')}"
        )

    @mcp.tool
    async def set_camera(
        preset: Annotated[
            str | None,
            Field(description=(
                "Standard view preset: front, back, top, bottom, left, right, "
                "isometric, axometric, fit_all"
            )),
        ] = None,
        camera_type: Annotated[
            str | None,
            Field(description="Camera projection: 'Orthographic' or 'Perspective'"),
        ] = None,
        camera_string: Annotated[
            str | None,
            Field(description="Raw OpenInventor camera string for precise control"),
        ] = None,
    ) -> str:
        """Set the 3D view camera. Use preset for standard views, or camera_string for precise control."""
        result = await bridge.set_camera(
            preset=preset,
            camera_string=camera_string,
            camera_type=camera_type,
        )
        if not result.get("success"):
            return f"Error: {result.get('error')}"
        return "Camera updated."
