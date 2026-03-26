"""Script execution tool: run arbitrary Python code inside FreeCAD."""

from typing import Annotated
from pydantic import Field

from tools._helpers import format_result


def register(mcp, bridge):

    @mcp.tool
    async def run_script(
        code: Annotated[
            str,
            Field(description=(
                "Python code to execute inside FreeCAD. "
                "FreeCAD, FreeCADGui, App, Gui are available. "
                "Set __result__ to return a value."
            )),
        ],
    ) -> str:
        """Execute arbitrary Python code inside FreeCAD's interpreter.

        The code runs with full access to FreeCAD and FreeCADGui modules.
        Set the variable `__result__` to pass a return value back.
        stdout and stderr are captured.
        """
        result = await bridge.execute(code)
        return format_result(result)
