"""
FreeCAD MCP Server

FastMCP-based MCP server that exposes FreeCAD operations to LLMs.
Communicates with FreeCAD via the bridge HTTP server running inside FreeCAD.

Usage:
    python server.py
"""

import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from bridge_client import FreeCADBridge
from tools import register_all

load_dotenv()

# --- Configuration ---

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "50005"))
FREECAD_BRIDGE_HOST = os.getenv("FREECAD_BRIDGE_HOST", "127.0.0.1")
FREECAD_BRIDGE_PORT = int(os.getenv("FREECAD_BRIDGE_PORT", "50006"))

# --- Server setup ---

mcp = FastMCP(
    "FreeCAD",
    instructions=(
        "FreeCAD MCP server for CAD manipulation. "
        "Use document tools to manage FreeCAD documents, "
        "screenshot/camera tools to observe the 3D view, "
        "and run_script to execute arbitrary FreeCAD Python code."
    ),
)

bridge = FreeCADBridge(FREECAD_BRIDGE_HOST, FREECAD_BRIDGE_PORT)

register_all(mcp, bridge)

# --- Entrypoint ---

if __name__ == "__main__":
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)
