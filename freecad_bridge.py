"""
FreeCAD Bridge Server

Run this script INSIDE FreeCAD's Python console or as a macro.
It starts a lightweight HTTP server that accepts Python code execution
requests from the MCP server.

Main-thread dispatch uses a queue polled by a repeating QTimer (same
pattern as neka-nat/freecad-mcp). The QTimer lives on the main thread
and is created there, so no cross-thread QObject issues.

Usage in FreeCAD:
    exec(open("/Users/roman/voitta-freecad-mcp/freecad_bridge.py").read())
"""

import json
import io
import sys
import os
import base64
import tempfile
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Event
from queue import Queue

# These are available when running inside FreeCAD
import FreeCAD
import FreeCADGui
from PySide import QtCore

BRIDGE_HOST = os.environ.get("FREECAD_BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("FREECAD_BRIDGE_PORT", "50006"))

# Task queue: HTTP threads put work here, main-thread timer drains it.
_task_queue = Queue()

# Polling timer -- created in start_bridge() on the main thread.
_poll_timer = None


def _drain_queue():
    """Called by QTimer on the main thread. Execute all pending tasks."""
    while not _task_queue.empty():
        fn, result_box, done = _task_queue.get_nowait()
        try:
            result_box["value"] = fn()
        except Exception:
            result_box["error"] = traceback.format_exc()
        finally:
            done.set()


def _run_on_main_thread(fn, timeout=300.0):
    """Enqueue *fn* for the main thread and block until it completes."""
    result_box = {}
    done = Event()

    _task_queue.put((fn, result_box, done))

    if not done.wait(timeout):
        raise TimeoutError("Main-thread callback did not complete in time")
    if "error" in result_box:
        raise RuntimeError(result_box["error"])
    return result_box.get("value")


class BridgeHandler(BaseHTTPRequestHandler):
    """Handles incoming requests from the MCP server."""

    def log_message(self, format, *args):
        FreeCAD.Console.PrintLog(f"[MCP Bridge] {format % args}\n")

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "version": FreeCAD.Version()})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length)
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        action = request.get("action")
        if action == "exec":
            self._handle_exec(request)
        elif action == "screenshot":
            self._handle_screenshot(request)
        elif action == "get_camera":
            self._handle_get_camera(request)
        elif action == "set_camera":
            self._handle_set_camera(request)
        else:
            self._send_json(400, {"error": f"unknown action: {action}"})

    # ------------------------------------------------------------------
    # exec
    # ------------------------------------------------------------------

    def _handle_exec(self, request):
        code = request.get("code", "")
        capture_stdout = request.get("capture_stdout", True)

        def _do():
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            old_stdout, old_stderr = sys.stdout, sys.stderr

            local_ns = {
                "FreeCAD": FreeCAD,
                "FreeCADGui": FreeCADGui,
                "App": FreeCAD,
                "Gui": FreeCADGui,
                "__result__": None,
            }

            try:
                if capture_stdout:
                    sys.stdout = stdout_capture
                    sys.stderr = stderr_capture

                exec(code, local_ns)

                return {
                    "success": True,
                    "stdout": stdout_capture.getvalue(),
                    "stderr": stderr_capture.getvalue(),
                    "result": local_ns.get("__result__"),
                }
            except Exception:
                return {
                    "success": False,
                    "error": traceback.format_exc(),
                    "stdout": stdout_capture.getvalue(),
                    "stderr": stderr_capture.getvalue(),
                }
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        try:
            resp = _run_on_main_thread(_do)
            self._send_json(200, resp)
        except Exception:
            self._send_json(200, {"success": False, "error": traceback.format_exc()})

    # ------------------------------------------------------------------
    # screenshot
    # ------------------------------------------------------------------

    def _handle_screenshot(self, request):
        width = request.get("width", 800)
        height = request.get("height", 600)
        background = request.get("background", "Current")

        def _do():
            FreeCADGui.updateGui()
            view = FreeCADGui.activeDocument().activeView()
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            view.saveImage(tmp.name, width, height, background)
            with open(tmp.name, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("ascii")
            os.unlink(tmp.name)
            return {
                "success": True,
                "image_base64": image_data,
                "mime_type": "image/png",
                "width": width,
                "height": height,
            }

        try:
            resp = _run_on_main_thread(_do)
            self._send_json(200, resp)
        except Exception:
            self._send_json(200, {"success": False, "error": traceback.format_exc()})

    # ------------------------------------------------------------------
    # get_camera
    # ------------------------------------------------------------------

    def _handle_get_camera(self, request):
        def _do():
            FreeCADGui.updateGui()
            view = FreeCADGui.activeDocument().activeView()
            return {
                "success": True,
                "camera_string": view.getCamera(),
                "camera_type": view.getCameraType(),
            }

        try:
            resp = _run_on_main_thread(_do)
            self._send_json(200, resp)
        except Exception:
            self._send_json(200, {"success": False, "error": traceback.format_exc()})

    # ------------------------------------------------------------------
    # set_camera
    # ------------------------------------------------------------------

    def _handle_set_camera(self, request):
        def _do():
            FreeCADGui.updateGui()
            view = FreeCADGui.activeDocument().activeView()

            preset = request.get("preset")
            if preset:
                presets = {
                    "front": view.viewFront,
                    "back": view.viewRear,
                    "top": view.viewTop,
                    "bottom": view.viewBottom,
                    "left": view.viewLeft,
                    "right": view.viewRight,
                    "isometric": view.viewIsometric,
                    "axometric": view.viewAxometric,
                    "fit_all": view.fitAll,
                }
                fn = presets.get(preset.lower())
                if fn is None:
                    return {
                        "success": False,
                        "error": f"Unknown preset: {preset}. Available: {list(presets.keys())}",
                    }
                fn()
                if preset.lower() != "fit_all":
                    view.fitAll()
            else:
                camera_string = request.get("camera_string")
                if camera_string:
                    view.setCamera(camera_string)

                camera_type = request.get("camera_type")
                if camera_type:
                    view.setCameraType(camera_type)

            FreeCADGui.updateGui()
            return {"success": True}

        try:
            resp = _run_on_main_thread(_do)
            self._send_json(200, resp)
        except Exception:
            self._send_json(200, {"success": False, "error": traceback.format_exc()})


def start_bridge(host=None, port=None):
    """Start the bridge HTTP server in a background thread."""
    global _poll_timer, _mcp_bridge_server

    host = host or BRIDGE_HOST
    port = port or BRIDGE_PORT

    # Stop previous instance if re-running the script
    if "_mcp_bridge_server" in globals() and _mcp_bridge_server is not None:
        FreeCAD.Console.PrintMessage("[MCP Bridge] Shutting down previous server...\n")
        _mcp_bridge_server.shutdown()
        _mcp_bridge_server = None

    if _poll_timer is not None:
        _poll_timer.stop()

    # Start the queue-drain timer on the main thread (50ms interval)
    _poll_timer = QtCore.QTimer()
    _poll_timer.timeout.connect(_drain_queue)
    _poll_timer.start(50)

    server = HTTPServer((host, port), BridgeHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    FreeCAD.Console.PrintMessage(
        f"[MCP Bridge] Listening on http://{host}:{port}\n"
    )
    return server


# Auto-start when executed inside FreeCAD
_mcp_bridge_server = start_bridge()
