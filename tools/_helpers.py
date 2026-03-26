"""Shared helpers used across tool modules."""


def format_result(result: dict) -> str:
    """Format a bridge response into a human-readable string."""
    if not result.get("success"):
        return f"Error: {result.get('error', 'unknown error')}"
    parts = []
    if result.get("stdout"):
        parts.append(result["stdout"].rstrip())
    if result.get("stderr"):
        parts.append(f"[stderr] {result['stderr'].rstrip()}")
    if result.get("result") is not None:
        parts.append(str(result["result"]))
    return "\n".join(parts) if parts else "OK"


def doc_ref_expr(name: str | None) -> str:
    """Return a Python expression string that resolves to a FreeCAD document."""
    if name:
        return f'FreeCAD.getDocument("{name}")'
    return "FreeCAD.ActiveDocument"
