"""
PackageVerse HTTP Server — Real running-app capture and web streaming.

Endpoints:
  GET  /api/apps              — list running apps with visible windows
  POST /api/park              — park a running app (make it web-accessible)
  GET  /api/parked            — list all parked apps
  GET  /api/parked/:id        — get parked app status
  GET  /api/parked/:id/frame  — latest JPEG frame (for polling)
  GET  /api/parked/:id/stream — MJPEG stream (continuous frames)
  POST /api/parked/:id/click  — send click to app window
  POST /api/parked/:id/type   — send keystrokes to app
  POST /api/parked/:id/stop   — stop streaming, unpark
  GET  /api/health            — health check
  GET  /                      — serve frontend
"""

from __future__ import annotations

import json
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from typing import Any

from .capture import WindowEnumerator, WindowCapture, ParkedApp, RunningApp


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class ParkManager:
    """Manages parked apps — running apps made web-accessible."""

    def __init__(self):
        self.parked: dict[str, ParkedApp] = {}
        self._lock = threading.Lock()

    def list_running(self) -> list[dict]:
        apps = WindowEnumerator.list_running_apps()
        return [a.to_dict() for a in apps]

    def park(self, window_id: int) -> ParkedApp:
        apps = WindowEnumerator.list_running_apps()
        app = None
        for a in apps:
            if a.window_id == window_id:
                app = a
                break
        if not app:
            raise ValueError(f"No running app with window_id {window_id}")

        parked = ParkedApp(app)
        parked.start_streaming()
        with self._lock:
            self.parked[parked.park_id] = parked
        return parked

    def get(self, park_id: str) -> ParkedApp | None:
        with self._lock:
            return self.parked.get(park_id)

    def list_parked(self) -> list[dict]:
        with self._lock:
            return [p.to_dict() for p in self.parked.values()]

    def stop(self, park_id: str) -> bool:
        with self._lock:
            p = self.parked.get(park_id)
            if p:
                p.stop_streaming()
                del self.parked[park_id]
                return True
            return False


manager = ParkManager()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, code: int, data: Any):
        body = json.dumps(data, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_static(self, path: str):
        if path == "/":
            path = "/index.html"
        file_path = os.path.join(STATIC_DIR, path.lstrip("/"))
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            self._json(404, {"error": "not found"})
            return
        ext = os.path.splitext(file_path)[1].lower()
        ct = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }.get(ext, "application/octet-stream")
        with open(file_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/health":
            return self._json(200, {
                "status": "ok",
                "running_apps": len(manager.list_running()),
                "parked": len(manager.parked),
            })

        if path == "/api/apps":
            return self._json(200, {"apps": manager.list_running()})

        if path == "/api/parked":
            return self._json(200, {"parked": manager.list_parked()})

        parts = path.split("/")
        # /api/parked/:id
        if len(parts) == 4 and parts[1] == "api" and parts[2] == "parked":
            pid = parts[3]
            p = manager.get(pid)
            if not p:
                return self._json(404, {"error": "not parked"})
            return self._json(200, p.to_dict())

        # /api/parked/:id/frame — single JPEG
        if len(parts) == 5 and parts[1] == "api" and parts[2] == "parked" and parts[4] == "frame":
            pid = parts[3]
            p = manager.get(pid)
            if not p:
                return self._json(404, {"error": "not parked"})
            frame = p.get_frame()
            if not frame:
                return self._json(503, {"error": "no frame yet"})
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(frame)))
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(frame)
            return

        # /api/parked/:id/stream — MJPEG stream
        if len(parts) == 5 and parts[1] == "api" and parts[2] == "parked" and parts[4] == "stream":
            pid = parts[3]
            p = manager.get(pid)
            if not p:
                return self._json(404, {"error": "not parked"})
            return self._mjpeg_stream(p)

        # Static files
        if not path.startswith("/api"):
            return self._serve_static(path)

        self._json(404, {"error": "not found"})

    def _mjpeg_stream(self, p: ParkedApp):
        """Stream frames as multipart/x-mixed-replace MJPEG."""
        boundary = "frameboundary"
        self.send_response(200)
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={boundary}")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        while p.streaming:
            frame = p.get_frame()
            if frame:
                header = (
                    f"--{boundary}\r\n"
                    f"Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(frame)}\r\n\r\n"
                ).encode()
                try:
                    self.wfile.write(header)
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
            time.sleep(1.0 / p.fps)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/park":
            body = self._read_body()
            try:
                data = json.loads(body) if body else {}
                window_id = data.get("window_id")
                if not window_id:
                    return self._json(400, {"error": "window_id required"})
                parked = manager.park(int(window_id))
                return self._json(200, parked.to_dict())
            except ValueError as e:
                return self._json(404, {"error": str(e)})
            except Exception as e:
                return self._json(500, {"error": str(e)})

        parts = path.split("/")
        if len(parts) == 5 and parts[1] == "api" and parts[2] == "parked":
            pid = parts[3]
            action = parts[4]
            p = manager.get(pid)
            if not p:
                return self._json(404, {"error": "not parked"})

            try:
                body = self._read_body()
                data = json.loads(body) if body else {}

                if action == "click":
                    rel_x = float(data.get("x", 0.5))
                    rel_y = float(data.get("y", 0.5))
                    ok = p.click(rel_x, rel_y)
                    return self._json(200, {"ok": ok, "x": rel_x, "y": rel_y})

                elif action == "type":
                    text = data.get("text", "")
                    ok = p.type(text)
                    return self._json(200, {"ok": ok, "chars": len(text)})

                elif action == "stop":
                    manager.stop(pid)
                    return self._json(200, {"ok": True})

            except Exception as e:
                return self._json(500, {"error": str(e)})

        self._json(404, {"error": "not found"})


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def run_server(port: int = 8847):
    server = ThreadedServer(("0.0.0.0", port), Handler)
    print(f"PackageVerse on http://localhost:{port}")
    print(f"  Open browser -> see running apps -> click Park -> app is now web-accessible")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
