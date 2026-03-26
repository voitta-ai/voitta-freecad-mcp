"""
HTTP client for communicating with the FreeCAD bridge server.
"""

import httpx
from typing import Any


class FreeCADBridge:
    """Sends commands to the FreeCAD bridge HTTP server."""

    def __init__(self, host: str, port: int, timeout: float = 600.0):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    async def _post(self, data: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/exec", json=data)
            resp.raise_for_status()
            return resp.json()

    async def execute(self, code: str) -> dict:
        """Execute Python code inside FreeCAD. Returns dict with success, stdout, stderr, result."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/exec",
                json={"action": "exec", "code": code},
            )
            resp.raise_for_status()
            return resp.json()

    async def screenshot(
        self,
        width: int = 800,
        height: int = 600,
        background: str = "Current",
    ) -> dict:
        """Capture a screenshot. Returns dict with image_base64, mime_type."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/exec",
                json={
                    "action": "screenshot",
                    "width": width,
                    "height": height,
                    "background": background,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_camera(self) -> dict:
        """Get current camera state."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/exec",
                json={"action": "get_camera"},
            )
            resp.raise_for_status()
            return resp.json()

    async def set_camera(
        self,
        preset: str | None = None,
        camera_string: str | None = None,
        camera_type: str | None = None,
    ) -> dict:
        """Set camera view."""
        payload: dict[str, Any] = {"action": "set_camera"}
        if preset:
            payload["preset"] = preset
        if camera_string:
            payload["camera_string"] = camera_string
        if camera_type:
            payload["camera_type"] = camera_type

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/exec",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
