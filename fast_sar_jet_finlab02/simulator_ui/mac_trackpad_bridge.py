#!/usr/bin/env python3
"""
macOS Hardware Multitouch Trackpad Bridge for FIN-LAB-02 6-DoF FPV Flight Simulator.

Reads raw normalized capacitive finger positions (x in [0..1], y in [0..1]) directly
from the physical MacBook / Magic Trackpad via Apple's MultitouchSupport.framework:
  - Finger OFF trackpad (0 active contacts) -> stick in the middle (0.0, 0.0)
  - Finger in the MIDDLE of trackpad (0.5, 0.5) -> stick in the middle (0.0, 0.0)
  - Finger ANYWHERE on trackpad -> stick points to that exact direction & magnitude,
    with the physical trackpad's 4 sides ([0..1] left/right/top/bottom edges) as bounds.

Serves:
  - GET http://127.0.0.1:8765/trackpad-stream  (120 Hz Server-Sent Events stream, CORS *)
  - GET http://127.0.0.1:8765/trackpad         (JSON snapshot, CORS *)
  - GET http://127.0.0.1:8765/flight_simulator.html
"""

import ctypes
import ctypes.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time

CF_PATH = ctypes.util.find_library("CoreFoundation") or "CoreFoundation"
MT_PATH = ctypes.util.find_library("MultitouchSupport") or "MultitouchSupport"


class MTPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]


class MTVector(ctypes.Structure):
    _fields_ = [("position", MTPoint), ("velocity", MTPoint)]


class MTTouch(ctypes.Structure):
    _fields_ = [
        ("frame", ctypes.c_int32),
        ("timestamp", ctypes.c_double),
        ("identifier", ctypes.c_int32),
        ("state", ctypes.c_int32),
        ("finger_id", ctypes.c_int32),
        ("hand_id", ctypes.c_int32),
        ("normalized", MTVector),
        ("size", ctypes.c_float),
        ("unk1", ctypes.c_int32),
        ("angle", ctypes.c_float),
        ("major_axis", ctypes.c_float),
        ("minor_axis", ctypes.c_float),
        ("absolute", MTVector),
        ("unk2", ctypes.c_int32 * 2),
        ("density", ctypes.c_float),
    ]


MTContactCallback = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.POINTER(MTTouch),
    ctypes.c_int,
    ctypes.c_double,
    ctypes.c_int,
)

TRACKPAD_STATE = {
    "touching": False,
    "n_fingers": 0,
    "pad_x": 0.5,      # [0.0 = left edge .. 0.5 = center .. 1.0 = right edge]
    "pad_y": 0.5,      # [0.0 = bottom edge .. 0.5 = center .. 1.0 = top edge]
    "stick_x": 0.0,    # [-1.0 .. +1.0] mapped with trackpad sides as bounds
    "stick_y": 0.0,    # [-1.0 .. +1.0] mapped with trackpad sides as bounds (-1 = top edge, +1 = bottom edge)
    "last_frame_ts": 0.0,
}
STATE_LOCK = threading.Lock()

# Physical trackpad usable edge margin (so finger near the physical edge reaches 100% bound)
EDGE_MARGIN_X = 0.07
EDGE_MARGIN_Y = 0.07
CENTER_DEADZONE = 0.035


def map_pad_to_stick(pad_x: float, pad_y: float):
    """Map normalized trackpad [0..1] to [-1..+1] with center deadzone and trackpad sides as bounds."""
    half_span_x = max(0.1, 0.5 - EDGE_MARGIN_X)
    half_span_y = max(0.1, 0.5 - EDGE_MARGIN_Y)

    dx = pad_x - 0.5
    dy = 0.5 - pad_y  # +dy when finger is pulled toward bottom edge (pull nose up), -dy when pushed toward top edge

    if abs(dx) < CENTER_DEADZONE:
        sx = 0.0
    else:
        sign_x = 1.0 if dx > 0 else -1.0
        sx = sign_x * min(1.0, (abs(dx) - CENTER_DEADZONE) / (half_span_x - CENTER_DEADZONE))

    if abs(dy) < CENTER_DEADZONE:
        sy = 0.0
    else:
        sign_y = 1.0 if dy > 0 else -1.0
        sy = sign_y * min(1.0, (abs(dy) - CENTER_DEADZONE) / (half_span_y - CENTER_DEADZONE))

    return round(sx, 4), round(sy, 4)


def _mt_callback(dev, data_ptr, n_fingers, timestamp, frame):
    now = time.monotonic()
    active_touches = []
    if n_fingers > 0 and data_ptr:
        for i in range(n_fingers):
            t = data_ptr[i]
            # States 3 (make touch) and 4 (active touching) represent physical finger contact on glass
            if t.state in (3, 4):
                px = float(t.normalized.position.x)
                py = float(t.normalized.position.y)
                if 0.0 <= px <= 1.0 and 0.0 <= py <= 1.0:
                    active_touches.append((px, py, float(t.size)))

    with STATE_LOCK:
        if active_touches:
            # Primary finger contact (largest contact patch or first active finger)
            active_touches.sort(key=lambda item: item[2], reverse=True)
            px, py, _ = active_touches[0]
            sx, sy = map_pad_to_stick(px, py)
            TRACKPAD_STATE["touching"] = True
            TRACKPAD_STATE["n_fingers"] = len(active_touches)
            TRACKPAD_STATE["pad_x"] = round(px, 4)
            TRACKPAD_STATE["pad_y"] = round(py, 4)
            TRACKPAD_STATE["stick_x"] = sx
            TRACKPAD_STATE["stick_y"] = sy
            TRACKPAD_STATE["last_frame_ts"] = now
        else:
            TRACKPAD_STATE["touching"] = False
            TRACKPAD_STATE["n_fingers"] = 0
            TRACKPAD_STATE["pad_x"] = 0.5
            TRACKPAD_STATE["pad_y"] = 0.5
            TRACKPAD_STATE["stick_x"] = 0.0
            TRACKPAD_STATE["stick_y"] = 0.0
            TRACKPAD_STATE["last_frame_ts"] = now
    return 0


_CALLBACK_REF = MTContactCallback(_mt_callback)


def start_multitouch_listener():
    cf = ctypes.CDLL(CF_PATH)
    mt = ctypes.CDLL(MT_PATH)

    cf.CFArrayGetCount.argtypes = [ctypes.c_void_p]
    cf.CFArrayGetCount.restype = ctypes.c_long
    cf.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
    cf.CFArrayGetValueAtIndex.restype = ctypes.c_void_p

    mt.MTDeviceCreateList.restype = ctypes.c_void_p
    mt.MTRegisterContactFrameCallback.argtypes = [ctypes.c_void_p, MTContactCallback]
    mt.MTDeviceStart.argtypes = [ctypes.c_void_p, ctypes.c_int]

    dev_list = mt.MTDeviceCreateList()
    n_dev = cf.CFArrayGetCount(dev_list) if dev_list else 0
    devices = []
    for i in range(n_dev):
        dev = cf.CFArrayGetValueAtIndex(dev_list, i)
        mt.MTRegisterContactFrameCallback(dev, _CALLBACK_REF)
        mt.MTDeviceStart(dev, 0)
        devices.append(dev)
    return devices


def get_current_snapshot():
    now = time.monotonic()
    with STATE_LOCK:
        # If no active touch frame arrived in the last 140 ms, mark finger as lifted off trackpad
        if TRACKPAD_STATE["touching"] and (now - TRACKPAD_STATE["last_frame_ts"]) > 0.14:
            TRACKPAD_STATE["touching"] = False
            TRACKPAD_STATE["n_fingers"] = 0
            TRACKPAD_STATE["pad_x"] = 0.5
            TRACKPAD_STATE["pad_y"] = 0.5
            TRACKPAD_STATE["stick_x"] = 0.0
            TRACKPAD_STATE["stick_y"] = 0.0
        return dict(TRACKPAD_STATE)


class TrackpadHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return  # Keep stdout clean

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/trackpad-stream"):
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    snap = get_current_snapshot()
                    payload = f"data: {json.dumps(snap)}\n\n".encode("utf-8")
                    self.wfile.write(payload)
                    self.wfile.flush()
                    time.sleep(1.0 / 60.0)
            except (BrokenPipeError, ConnectionResetError, OSError):
                return
        elif self.path.startswith("/trackpad"):
            snap = get_current_snapshot()
            body = json.dumps(snap).encode("utf-8")
            self.send_response(200)
            self._send_cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            sim_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flight_simulator.html")
            if os.path.exists(sim_html):
                with open(sim_html, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self._send_cors()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()


def main():
    devices = start_multitouch_listener()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), TrackpadHTTPHandler)
    print(f"macOS Hardware Trackpad Bridge listening on http://127.0.0.1:8765 (devices={len(devices)})", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
