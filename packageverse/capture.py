"""
PackageVerse Live Capture — Real running app window streaming.

Enumerates running macOS apps, captures specific window screenshots at FPS,
and forwards browser clicks/keystrokes back to the real app via CGEventPost.
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
import threading
import subprocess
from dataclasses import dataclass, field
from typing import Optional

import Quartz
from PIL import Image


@dataclass
class RunningApp:
    """A real running application with at least one visible window."""
    pid: int
    name: str
    bundle_id: str = ""
    exe_path: str = ""
    window_id: int = 0
    window_title: str = ""
    window_bounds: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "name": self.name,
            "bundle_id": self.bundle_id,
            "exe_path": self.exe_path,
            "window_id": self.window_id,
            "window_title": self.window_title,
            "window_bounds": self.window_bounds,
        }


class WindowEnumerator:
    """Enumerate all running apps with visible windows using CGWindowList."""

    @staticmethod
    def list_running_apps() -> list[RunningApp]:
        apps: dict[str, RunningApp] = {}

        for window in Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        ):
            owner = window.get("kCGWindowOwnerName", "")
            wid = window.get("kCGWindowNumber", 0)
            title = window.get("kCGWindowName", "")
            layer = window.get("kCGWindowLayer", 0)
            bounds = window.get("kCGWindowBounds", {})
            pid = window.get("kCGWindowOwnerPID", 0)

            if layer != 0 or not owner:
                continue
            w = bounds.get("Width", 0)
            h = bounds.get("Height", 0)
            if w < 50 or h < 50:
                continue

            key = f"{owner}_{pid}"
            if key not in apps:
                apps[key] = RunningApp(
                    pid=pid,
                    name=owner,
                    window_id=wid,
                    window_title=title,
                    window_bounds={
                        "x": bounds.get("X", 0),
                        "y": bounds.get("Y", 0),
                        "w": w,
                        "h": h,
                    },
                )
            elif title and not apps[key].window_title:
                apps[key].window_title = title
                apps[key].window_id = wid
                apps[key].window_bounds = {
                    "x": bounds.get("X", 0),
                    "y": bounds.get("Y", 0),
                    "w": w,
                    "h": h,
                }

        try:
            import psutil
            for app in apps.values():
                try:
                    p = psutil.Process(app.pid)
                    app.exe_path = p.exe() or ""
                    app.bundle_id = p.name() or app.name
                except Exception:
                    pass
        except ImportError:
            pass

        return list(apps.values())


class WindowCapture:
    """Capture screenshots of a specific window using screencapture."""

    @staticmethod
    def capture_window_png(window_id: int) -> Optional[bytes]:
        """Capture a single window as PNG bytes via screencapture -l."""
        tmp = f"/tmp/pv_capture_{window_id}_{int(time.time()*1000)}.png"
        try:
            result = subprocess.run(
                ['screencapture', '-l', str(window_id), '-x', tmp],
                capture_output=True, timeout=5
            )
            if result.returncode == 0 and os.path.exists(tmp):
                with open(tmp, 'rb') as f:
                    return f.read()
        except Exception:
            pass
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
        return None

    @staticmethod
    def capture_window_jpeg(window_id: int, quality: int = 70) -> Optional[bytes]:
        """Capture a window and return as JPEG bytes (smaller for streaming)."""
        png_bytes = WindowCapture.capture_window_png(window_id)
        if not png_bytes:
            return None
        try:
            img = Image.open(io.BytesIO(png_bytes))
            if img.mode == "RGBA":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()
        except Exception:
            return png_bytes


class EventInjector:
    """Forward browser clicks/keystrokes to the real app window via CGEventPost."""

    @staticmethod
    def click_at(window_bounds: dict, click_x: float, click_y: float) -> bool:
        """Send a mouse click at relative position (0.0-1.0) within the window."""
        abs_x = window_bounds.get("x", 0) + click_x * window_bounds.get("w", 100)
        abs_y = window_bounds.get("y", 0) + click_y * window_bounds.get("h", 100)

        try:
            mouse_down = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseDown,
                (abs_x, abs_y), Quartz.kCGMouseButtonLeft
            )
            mouse_up = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseUp,
                (abs_x, abs_y), Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, mouse_down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, mouse_up)
            return True
        except Exception:
            return False

    @staticmethod
    def type_text(text: str) -> bool:
        """Send text as keystrokes to the currently focused app."""
        try:
            for char in text:
                key_code = EventInjector._char_to_keycode(char)
                if key_code is not None:
                    shift = char.isupper() or char in '!@#$%^&*()_+{}|:"<>?'
                    if shift:
                        shift_down = Quartz.CGEventCreateKeyboardEvent(None, 56, True)
                        Quartz.CGEventPost(Quartz.kCGHIDEventTap, shift_down)

                    key_down = Quartz.CGEventCreateKeyboardEvent(None, key_code, True)
                    key_up = Quartz.CGEventCreateKeyboardEvent(None, key_code, False)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_down)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, key_up)

                    if shift:
                        shift_up = Quartz.CGEventCreateKeyboardEvent(None, 56, False)
                        Quartz.CGEventPost(Quartz.kCGHIDEventTap, shift_up)
            return True
        except Exception:
            return False

    @staticmethod
    def _char_to_keycode(char: str) -> Optional[int]:
        keymap = {
            'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3, 'g': 5,
            'h': 4, 'i': 34, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45,
            'o': 31, 'p': 35, 'q': 12, 'r': 15, 's': 1, 't': 17, 'u': 32,
            'v': 9, 'w': 13, 'x': 7, 'y': 16, 'z': 6,
            ' ': 49, '\n': 36, '\t': 48, '1': 18, '2': 19, '3': 20,
            '4': 21, '5': 23, '6': 22, '7': 26, '8': 28, '9': 25, '0': 29,
            '.': 47, ',': 43, '/': 44, '-': 27, '=': 24,
        }
        return keymap.get(char.lower())


class ParkedApp:
    """A running app that has been 'parked' — made web-accessible."""

    def __init__(self, app: RunningApp):
        self.app = app
        self.park_id = f"park_{app.window_id}_{int(time.time())}"
        self.url = f"/parked/{self.park_id}"
        self.streaming = False
        self.fps = 10
        self._stream_thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[bytes] = None
        self._frame_lock = threading.Lock()
        self._frame_time = 0.0
        self.created_at = time.time()
        self.click_count = 0
        self.key_count = 0

    def start_streaming(self):
        if self.streaming:
            return
        self.streaming = True
        self._stream_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._stream_thread.start()

    def stop_streaming(self):
        self.streaming = False

    def _capture_loop(self):
        interval = 1.0 / self.fps
        while self.streaming:
            frame = WindowCapture.capture_window_jpeg(self.app.window_id, quality=65)
            if frame:
                with self._frame_lock:
                    self._latest_frame = frame
                    self._frame_time = time.time()
            time.sleep(interval)

    def get_frame(self) -> Optional[bytes]:
        with self._frame_lock:
            return self._latest_frame

    def click(self, rel_x: float, rel_y: float) -> bool:
        result = EventInjector.click_at(self.app.window_bounds, rel_x, rel_y)
        if result:
            self.click_count += 1
        return result

    def type(self, text: str) -> bool:
        result = EventInjector.type_text(text)
        if result:
            self.key_count += len(text)
        return result

    def to_dict(self) -> dict:
        return {
            "park_id": self.park_id,
            "url": self.url,
            "app": self.app.to_dict(),
            "streaming": self.streaming,
            "fps": self.fps,
            "created_at": self.created_at,
            "click_count": self.click_count,
            "key_count": self.key_count,
            "frame_age_ms": int((time.time() - self._frame_time) * 1000) if self._frame_time else 0,
        }
