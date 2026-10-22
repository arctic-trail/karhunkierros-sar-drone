#!/usr/bin/env python3
# File: pi5_sender_node/sender_node.py
# Description: Production Fast-Boot Edge AI Sender Node with Hailo NPU, Cryptographic Diode & Fallback Safety
# License: MIT
import os
import sys
import time
import json
import socket
import struct
import hashlib
import secrets
import subprocess
from typing import Any

serial: Any = None
cv2: Any = None
np: Any = None
try:
    import serial  # type: ignore[import-not-found,no-redef]
except ImportError:
    pass
try:
    import cv2  # type: ignore[import-not-found,no-redef]
    import numpy as np  # type: ignore[import-not-found,no-redef]
except ImportError:
    pass
SigningKey: Any = None
try:
    from nacl.signing import SigningKey  # type: ignore[import-not-found,no-redef]
except ImportError:
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../collector_hub")))
        from receiver_hub import SigningKey  # type: ignore[import-not-found,no-redef]
    except Exception:
        pass

# ==============================================================================
# Node Identity & Network Constants
# ==============================================================================
NODE_ID = os.getenv("NODE_ID", "NODE-NORTH-01")
LOCAL_IP = os.getenv("LOCAL_IP", "10.10.0.10")
RECEIVER_IP = os.getenv("RECEIVER_IP", "10.10.0.100")
RECEIVER_MAC = os.getenv("RECEIVER_MAC", "ff:ff:ff:ff:ff:ff")  # Broadcast default for diode
UDP_PORT = int(os.getenv("UDP_PORT", "5514"))
DONE_GPIO = 23

DEFAULT_EXAMPLE_PRIVKEY_HEX = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
NODE_KEY_FILE = os.getenv("NODE_KEY_FILE", "/etc/trailcam/node_key.json")
MAX_META_PACKET_BYTES = 1400
MAX_DETECTIONS_IN_PACKET = 16


def load_signing_key(key_file=None, allow_example_keys=None):
    """
    Loads the node's 32-byte Ed25519 private key AND provisioned node_id from
    NODE_KEY_FILE (or PRIVATE_KEY_HEX / NODE_ID environment variables).
    Refuses the public repository example key when ALLOW_EXAMPLE_KEYS=0.
    """
    global NODE_ID
    priv_hex = os.getenv("PRIVATE_KEY_HEX")
    explicit_env_node = os.getenv("NODE_ID")

    candidates = []
    if key_file:
        candidates.append(key_file)
    else:
        env_kf = os.getenv("NODE_KEY_FILE")
        if env_kf:
            candidates.append(env_kf)
        candidates.extend([
            "/etc/trailcam/node_key.json",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "node_key.json"),
        ])

    for kf in candidates:
        if kf and os.path.isfile(kf):
            try:
                with open(kf, "r", encoding="utf-8") as f:
                    key_data = json.load(f)
                if not isinstance(key_data, dict):
                    raise ValueError("node_key.json must be a JSON object")
                if not priv_hex:
                    priv_hex = key_data.get("private_key_hex")
                file_node_id = key_data.get("node_id")
                if file_node_id and not explicit_env_node:
                    NODE_ID = str(file_node_id).strip()
                break
            except Exception as e:
                print(f"[!] Error reading {kf}: {e}", file=sys.stderr)
                raise RuntimeError(f"Invalid node_key.json ({kf}): {e}") from e

    if allow_example_keys is None:
        allow_example = os.getenv("ALLOW_EXAMPLE_KEYS", "1") != "0"
    else:
        allow_example = bool(allow_example_keys)

    if not priv_hex:
        if not allow_example:
            raise RuntimeError(
                "No node private key provisioned and ALLOW_EXAMPLE_KEYS=0. "
                "Provision a unique key with generate_keys.py."
            )
        priv_hex = DEFAULT_EXAMPLE_PRIVKEY_HEX

    if priv_hex.lower() == DEFAULT_EXAMPLE_PRIVKEY_HEX.lower():
        if not allow_example:
            raise RuntimeError(
                "Refusing to sign with default example key while ALLOW_EXAMPLE_KEYS=0. "
                "Provision a unique key with generate_keys.py."
            )
        print("[!] SECURITY NOTICE: Using default benchtop example key. Provision unique keys before deployment.", file=sys.stderr)

    if SigningKey is None:
        return None
    return SigningKey(bytes.fromhex(priv_hex))


def derive_ephemeral_key_from_trig(trig_line):
    """
    Zero-Disk Ephemeral Key Derivation & Zeroization:
    If the Pico 2 Gatekeeper provides an OTP/SRAM key seed over UART (`KEY_SEED=<64-hex>`),
    derives a deterministic Ed25519 SigningKey in RAM via BLAKE2b, overwrites the seed buffer
    in-place with zeros, and strips `KEY_SEED=...` from the telemetry string so the secret
    seed never touches disk or leaves the node.
    Returns (sanitized_trig_line, ephemeral_signing_key_or_None).
    """
    if not trig_line or "KEY_SEED=" not in trig_line:
        return trig_line, None

    parts = trig_line.split(",")
    clean_parts = []
    ephemeral_sk = None
    for part in parts:
        if part.startswith("KEY_SEED="):
            seed_hex = part.split("=", 1)[1].strip()
            try:
                seed_buf = bytearray.fromhex(seed_hex)
                if len(seed_buf) >= 16:
                    derived = bytearray(
                        hashlib.blake2b(seed_buf, digest_size=32, person=b"ARCTIC-DIODE-KEY").digest()
                    )
                    ephemeral_sk = SigningKey(bytes(derived))
                    for i in range(len(derived)):
                        derived[i] = 0
                for i in range(len(seed_buf)):
                    seed_buf[i] = 0
            except Exception:
                pass
        else:
            clean_parts.append(part)
    return ",".join(clean_parts), ephemeral_sk


signing_key = load_signing_key()

# Model Configuration (MS-COCO 80-class IDs mapped for Arctic security, motorized vehicles & Nordic wildlife)
HEF_PATH = os.getenv("HEF_PATH", "/usr/share/hailo-models/yolov8s_h8l.hef")
ONNX_PATH = os.getenv("ONNX_PATH", "/opt/trailcam/yolov8n.onnx")
TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle_atv_snowmobile",
    4: "aircraft_drone",
    5: "bus",
    6: "train_tracked_vehicle",
    7: "truck_tractor",
    8: "boat_watercraft",
    14: "bird",
    15: "cat_lynx",
    16: "dog_wolf_canid",
    17: "cervid_moose_horse",
    18: "deer_reindeer_sheep",
    19: "moose_bovid",
    21: "bear",
}
CONF_THRESHOLD = 0.45

# ==============================================================================
# Hardware & Network Setup
# ==============================================================================
def find_primary_ethernet_interface():
    """
    Detects primary wired Ethernet interface.
    Handles predictable interface naming: 'end0' on Pi 5 / Bookworm, 'eth0' on Pi 4.
    """
    explicit = os.getenv("DIODE_IFACE")
    if explicit:
        return explicit
    if os.path.exists("/sys/class/net"):
        for candidate in ["end0", "eth0", "enp1s0"]:
            if os.path.exists(f"/sys/class/net/{candidate}"):
                return candidate
        # Fallback to any non-loopback, non-wireless network interface
        for iface in sorted(os.listdir("/sys/class/net")):
            if iface != "lo" and not iface.startswith(("wl", "wlan")):
                return iface
    return "eth0"

def setup_unidirectional_network():
    """Configures static IP and permanent ARP so UDP transmits without any RX return link."""
    iface = find_primary_ethernet_interface()
    try:
        subprocess.run(["ip", "link", "set", iface, "up"], check=False)
        subprocess.run(["ip", "addr", "add", f"{LOCAL_IP}/24", "dev", iface], check=False)
        subprocess.run(
            ["ip", "neigh", "replace", RECEIVER_IP, "lladdr", RECEIVER_MAC, "nud", "permanent", "dev", iface],
            check=False
        )
    except Exception as e:
        print(f"[!] Network setup warning ({iface}): {e}", file=sys.stderr)
    return iface

def wait_for_ethernet_carrier(iface=None, timeout_s=3.0):
    """
    Waits for IEEE 802.3 1000BASE-T copper/optical auto-negotiation carrier lock
    (/sys/class/net/<iface>/carrier == '1') before firing UDP bursts on cold boot.
    """
    if iface is None:
        iface = find_primary_ethernet_interface()
    carrier_path = f"/sys/class/net/{iface}/carrier"
    if not os.path.exists(carrier_path):
        return True

    deadline = time.time() + timeout_s
    carrier_up = False
    while time.time() < deadline:
        try:
            with open(carrier_path, "r", encoding="utf-8") as f:
                if f.read().strip() == "1":
                    carrier_up = True
                    break
        except Exception:
            pass
        time.sleep(0.05)

    if carrier_up:
        time.sleep(0.05)  # 50ms PHY post-negotiation settle
        try:
            subprocess.run(
                ["ip", "neigh", "replace", RECEIVER_IP, "lladdr", RECEIVER_MAC, "nud", "permanent", "dev", iface],
                check=False
            )
        except Exception:
            pass
    return carrier_up

def read_pico_telemetry(max_lines=5):
    """
    Reads magnetic, seismic, LWIR thermal, and 24GHz radar trigger data from the Pico over UART.
    Reads up to `max_lines` lines so an initial truncated mid-frame fragment is flushed.
    """
    for dev in ["/dev/ttyAMA0", "/dev/serial0"]:
        if os.path.exists(dev):
            try:
                with serial.Serial(dev, 115200, timeout=0.25) as ser:
                    for _ in range(max_lines):
                        raw = ser.readline()
                        if not raw:
                            break
                        line = raw.decode("utf-8", errors="ignore").strip()
                        if line.startswith("TRIG,"):
                            return line
            except Exception:
                pass
    return "TRIG,DIRECT_WAKE"


def pulse_ir_illuminator_strobe(duration_ms=30):
    """
    NVG-Stealth 940nm IR Discipline:
    Instead of illuminating 940nm IR LEDs continuously during boot (visible to Gen-3 NVGs),
    pulses the optional IR strobe gate (GPIO 24) for a single <30ms camera exposure window,
    or keeps it 100% dark when EMCON_NO_IR=1.
    """
    if os.getenv("EMCON_NO_IR", "0") == "1":
        return False
    ir_gpio = int(os.getenv("IR_STROBE_GPIO", "24"))
    try:
        subprocess.run(
            ["pinctrl", "set", str(ir_gpio), "op", "dh"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(max(0.005, min(0.050, duration_ms / 1000.0)))
        subprocess.run(
            ["pinctrl", "set", str(ir_gpio), "op", "dl"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def compute_aloha_interpass_delays_s(node_id=NODE_ID, shared_trunk=None):
    """
    Computes decorrelated inter-pass Aloha backoff delays (100ms - 800ms) between
    Pass 1, Pass 2, and Pass 3 when multiple cameras share a passive optical splitter
    trunk (SHARED_FIBER_TRUNK=1), preventing burst collisions without 2-way comms.
    """
    if shared_trunk is None:
        shared_trunk = (os.getenv("SHARED_FIBER_TRUNK", "0") == "1")
    if not shared_trunk:
        return (0.0, 0.0)
    seed_int = int(hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:8], 16)
    base_ms_1 = 100 + (seed_int % 350) + secrets.randbelow(150)
    base_ms_2 = 250 + ((seed_int >> 8) % 400) + secrets.randbelow(150)
    return (round(base_ms_1 / 1000.0, 3), round(base_ms_2 / 1000.0, 3))


def transmit_over_diode(sock, alert_meta, jpeg_bytes, shared_trunk=None, custom_signing_key=None):
    """
    Sends signed JSON metadata + chunked JPEG over one-way UDP with
    calibrated packet pacing, 8-byte cryptographic nonce chunk correlation,
    bounded metadata packet size (<= MAX_META_PACKET_BYTES), 3x carousel repetition,
    and optional Aloha inter-pass jitter for shared fiber trunks.
    """
    payload_hash = hashlib.sha256(jpeg_bytes).hexdigest()
    nonce_hex = alert_meta.get("nonce")
    if not nonce_hex or len(nonce_hex) != 16:
        nonce_hex = secrets.token_hex(8)

    alert_meta["img_sha256"] = payload_hash
    alert_meta["img_size"] = len(jpeg_bytes)
    alert_meta["nonce"] = nonce_hex
    nonce_bytes = bytes.fromhex(nonce_hex)

    # Enforce strict protocol header size limits so DD\x01 metadata never exceeds MTU or UDP buffer
    if isinstance(alert_meta.get("detections"), list):
        orig_dets = list(alert_meta["detections"])
        # Prioritize highest-confidence detections first
        orig_dets.sort(key=lambda d: float(d.get("conf", 0.0)) if isinstance(d, dict) else 0.0, reverse=True)
        total_det_count = len(orig_dets)
        capped_dets = orig_dets[:MAX_DETECTIONS_IN_PACKET]
        if total_det_count > len(capped_dets):
            alert_meta["total_detections"] = total_det_count
            alert_meta["detections_truncated"] = True
        alert_meta["detections"] = capped_dets

        # Further trim if serialized DD\x01 packet exceeds MAX_META_PACKET_BYTES
        while len(alert_meta["detections"]) > 0:
            candidate_bytes = json.dumps(alert_meta, separators=(",", ":")).encode("utf-8")
            if 3 + 64 + len(candidate_bytes) <= MAX_META_PACKET_BYTES:
                break
            alert_meta["detections"].pop()
            alert_meta["total_detections"] = total_det_count
            alert_meta["detections_truncated"] = True

    meta_bytes = json.dumps(alert_meta, separators=(",", ":")).encode("utf-8")
    active_sk = custom_signing_key if custom_signing_key is not None else signing_key
    signature = active_sk.sign(meta_bytes).signature

    # Type 0x01: Signed Alert Header Datagram
    header_pkt = b"DD\x01" + signature + meta_bytes

    CHUNK_SIZE = 1024
    chunks = [jpeg_bytes[i:i + CHUNK_SIZE] for i in range(0, len(jpeg_bytes), CHUNK_SIZE)]
    total_chunks = len(chunks)
    interpass_delays = compute_aloha_interpass_delays_s(
        node_id=alert_meta.get("node", NODE_ID),
        shared_trunk=shared_trunk
    )

    # 3x Carousel Burst with calibrated micro-pacing to protect receiver kernel buffers
    for pass_idx in range(3):
        if pass_idx > 0 and interpass_delays[pass_idx - 1] > 0:
            time.sleep(interpass_delays[pass_idx - 1])
        sock.sendto(header_pkt, (RECEIVER_IP, UDP_PORT))
        time.sleep(0.0012)  # 1.2ms pacing for metadata
        for idx, chunk in enumerate(chunks):
            chunk_hdr = b"DD\x02" + nonce_bytes + struct.pack(">HH", idx, total_chunks)
            sock.sendto(chunk_hdr + chunk, (RECEIVER_IP, UDP_PORT))
            time.sleep(0.0008)  # 800us pacing between chunks (~10 Mbps line rate)


def signal_pico_done():
    """
    Guaranteed hardware power-down handshake via GPIO 23 with multi-driver fallback:
    1. Native Bookworm 'pinctrl' (preferred: latches RP1/BCM pad state directly)
    2. libgpiod 'gpioset' (probes gpiochip4 on Pi 5 and gpiochip0 on Pi 4)
    3. Legacy sysfs '/sys/class/gpio'
    """
    latched = False
    # Driver 1: pinctrl (Pi 5 / Pi 4 Bookworm standard)
    try:
        res = subprocess.run(
            ["pinctrl", "set", str(DONE_GPIO), "op", "dh"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if res.returncode == 0:
            latched = True
    except Exception:
        pass

    # Driver 2: libgpiod gpioset (only if pinctrl was unavailable)
    if not latched:
        for chip in ("gpiochip4", "gpiochip0"):
            try:
                res = subprocess.run(
                    ["gpioset", chip, f"{DONE_GPIO}=1"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                if res.returncode == 0:
                    latched = True
                    break
            except Exception:
                pass

    # Driver 3: sysfs fallback
    if not latched:
        try:
            val_path = f"/sys/class/gpio/gpio{DONE_GPIO}/value"
            if os.path.exists(val_path):
                with open(val_path, "w") as f:
                    f.write("1")
        except Exception:
            pass

    # Rapid crash-safe poweroff (skipped when BENCH_TEST_MODE=1 for interactive bench testing)
    if os.getenv("BENCH_TEST_MODE", "0") != "1":
        try:
            subprocess.run(["poweroff", "-f"], check=False)
        except Exception:
            pass
    else:
        print("[*] BENCH_TEST_MODE=1: Asserted DONE_GPIO (GPIO 23), skipping poweroff -f.")


def compute_crop_pixel_bounds(frame_shape, xmin, ymin, xmax, ymax, pad_px=40):
    """Computes clamped pixel crop coordinates (x1, y1, x2, y2) for a normalized box."""
    h, w = int(frame_shape[0]), int(frame_shape[1])
    x1 = max(0, int(xmin * w) - pad_px)
    y1 = max(0, int(ymin * h) - pad_px)
    x2 = min(w, int(xmax * w) + pad_px)
    y2 = min(h, int(ymax * h) + pad_px)
    if x2 <= x1 or y2 <= y1:
        return (0, 0, w, h)
    return (x1, y1, x2, y2)


def remap_detections_to_crop(detections, crop_bounds, frame_shape):
    """
    Transforms full-frame normalized detection bounding boxes [xmin, ymin, xmax, ymax]
    into normalized [0..1, 0..1] coordinates relative to the cropped JPEG image `(x1, y1, x2, y2)`.
    Preserves the original full-frame coordinates in `full_frame_box` so dashboard overlays
    align 100% accurately on the transmitted target crop.
    """
    if not detections or not crop_bounds:
        return detections
    h, w = float(frame_shape[0]), float(frame_shape[1])
    x1, y1, x2, y2 = [float(v) for v in crop_bounds]
    crop_w = max(1.0, x2 - x1)
    crop_h = max(1.0, y2 - y1)

    remapped = []
    for det in detections:
        if not isinstance(det, dict) or "box" not in det or len(det["box"]) != 4:
            remapped.append(det)
            continue
        bx1, by1, bx2, by2 = [float(v) for v in det["box"]]
        # Convert full-frame [0..1] -> full-frame pixels -> crop-relative [0..1]
        cx1 = max(0.0, min(1.0, (bx1 * w - x1) / crop_w))
        cy1 = max(0.0, min(1.0, (by1 * h - y1) / crop_h))
        cx2 = max(0.0, min(1.0, (bx2 * w - x1) / crop_w))
        cy2 = max(0.0, min(1.0, (by2 * h - y1) / crop_h))
        new_det = dict(det)
        new_det["full_frame_box"] = [round(bx1, 3), round(by1, 3), round(bx2, 3), round(by2, 3)]
        new_det["box"] = [round(cx1, 3), round(cy1, 3), round(cx2, 3), round(cy2, 3)]
        remapped.append(new_det)
    return remapped


def _encode_target_crop(m_frame, xmin, ymin, xmax, ymax, quality=75, return_bounds=False):
    """
    Extracts a padded target crop from the 1080p frame and encodes to JPEG.
    Note: Picamera2 'RGB888' on Raspberry Pi OS Bookworm outputs 3-channel arrays in OpenCV BGR
    memory order directly; channel swapping is only performed if CAMERA_COLOR_SWAP_RB=1 is set.
    """
    x1, y1, x2, y2 = compute_crop_pixel_bounds(m_frame.shape, xmin, ymin, xmax, ymax, pad_px=40)
    crop_view = m_frame[y1:y2, x1:x2]
    if os.getenv("CAMERA_COLOR_SWAP_RB", "0") == "1":
        crop_view = cv2.cvtColor(crop_view, cv2.COLOR_RGB2BGR)
    _, enc = cv2.imencode(".jpg", crop_view, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    jpeg_bytes = enc.tobytes()
    if return_bounds:
        return jpeg_bytes, (x1, y1, x2, y2)
    return jpeg_bytes


REFERENCE_SUBJECT_HEIGHTS_M = {
    "person": 1.75,
    "bicycle": 1.45,
    "car": 1.55,
    "motorcycle_atv_snowmobile": 1.25,
    "bus": 3.00,
    "train_tracked_vehicle": 3.20,
    "truck_tractor": 2.60,
    "boat_watercraft": 1.60,
    "cervid_moose_horse": 1.95,
    "deer_reindeer_sheep": 1.15,
    "moose_bovid": 1.95,
    "bear": 1.35,
}


def parse_pico_trig_fields(pico_trig):
    """
    Parses key=value fields from the Pico 2 Gatekeeper UART string
    (e.g., 'TRIG,MAG=3200,SEIS=850,DIST=4500,SPD=120,TEMP=-4.2,UPTIME_S=3600').
    Also supports compact bench strings such as 'RADAR+MAG:120'.
    """
    fields = {}
    if not pico_trig or not isinstance(pico_trig, str):
        return fields
    for token in pico_trig.strip().split(","):
        if "=" in token:
            k, v = token.split("=", 1)
            k = k.strip().upper()
            v = v.strip()
            try:
                fields[k] = float(v) if "." in v else int(v)
            except ValueError:
                fields[k] = v
    return fields


def estimate_subject_kinematics(
    detections,
    pico_telemetry,
    captured_pairs=None,
    frame_dt_s=0.05,
    cam_horiz_fov_deg=102.0,
    cam_vert_fov_deg=67.0,
    oblique_trail_deg=25.0,
):
    """
    Estimates where the detected subject was seen, where it is heading, and how fast
    by fusing:
      1. Full-frame optical bounding-box horizontal bearing offset & vertical angular size,
      2. HLK-LD2450 24 GHz FMCW radar range (DIST in mm) and radial speed (SPD in cm/s), and
      3. Multi-frame optical centroid shift across the 3-frame burst (when available).
    Returns a compact dictionary suitable for signing inside the DD\\x01 metadata packet.
    """
    import math

    trig = parse_pico_trig_fields(pico_telemetry)
    radar_dist_mm = float(trig.get("DIST", 0.0) or 0.0)
    if radar_dist_mm <= 0.0 and "RADAR_M" in trig:
        try:
            radar_dist_mm = float(trig["RADAR_M"]) * 1000.0
        except (ValueError, TypeError):
            radar_dist_mm = 0.0
    radar_spd_cms = float(trig.get("SPD", 0.0) or 0.0)

    primary_det = None
    if isinstance(detections, list) and detections:
        valid_dets = [d for d in detections if isinstance(d, dict)]
        if valid_dets:
            primary_det = max(valid_dets, key=lambda d: float(d.get("conf", 0.0)))

    subj_class = primary_det.get("class", "unknown") if primary_det else "unknown"
    subj_conf = round(float(primary_det.get("conf", 0.0)), 2) if primary_det else 0.0

    # Use full_frame_box if already remapped to crop, otherwise box/bbox
    box = None
    if primary_det:
        box = primary_det.get("full_frame_box") or primary_det.get("box") or primary_det.get("bbox")

    bearing_offset_deg = 0.0
    box_height_norm = 0.0
    box_xc = 0.5
    if isinstance(box, (list, tuple)) and len(box) == 4:
        bx1, by1, bx2, by2 = [float(v) for v in box]
        box_xc = max(0.0, min(1.0, 0.5 * (bx1 + bx2)))
        box_height_norm = max(0.02, min(1.0, abs(by2 - by1)))
        bearing_offset_deg = round((box_xc - 0.5) * float(cam_horiz_fov_deg), 2)

    # Distance estimation: prefer 24 GHz radar range; fall back to pinhole angular height
    if radar_dist_mm > 100.0:
        est_distance_m = round(radar_dist_mm / 1000.0, 2)
    elif box_height_norm > 0.03:
        ref_h = REFERENCE_SUBJECT_HEIGHTS_M.get(subj_class, 1.70)
        vert_fov_rad = math.radians(max(10.0, float(cam_vert_fov_deg)))
        subj_angle_rad = max(0.02, box_height_norm * vert_fov_rad)
        est_distance_m = round(max(2.0, min(80.0, ref_h / (2.0 * math.tan(subj_angle_rad / 2.0)))), 2)
    else:
        est_distance_m = 12.0

    # Radial velocity (m/s): HLK-LD2450 positive SPD = approaching or receding along radar axis
    radial_speed_mps = round(radar_spd_cms / 100.0, 2)

    # Transverse velocity (m/s): estimate from inter-frame centroid shift across burst if available
    transverse_speed_mps = 0.0
    if captured_pairs and len(captured_pairs) >= 2 and cv2 is not None:
        try:
            g_first = cv2.cvtColor(captured_pairs[0][0], cv2.COLOR_BGR2GRAY)
            g_last = cv2.cvtColor(captured_pairs[-1][0], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(cv2.GaussianBlur(g_first, (5, 5), 0), cv2.GaussianBlur(g_last, (5, 5), 0))
            _, thr = cv2.threshold(diff, 22, 255, cv2.THRESH_BINARY)
            moments = cv2.moments(thr)
            if moments["m00"] > 200:
                cx_last = (moments["m10"] / moments["m00"]) / float(g_last.shape[1])
                dx_norm = cx_last - box_xc
                total_dt = max(0.02, frame_dt_s * (len(captured_pairs) - 1))
                horiz_span_m = 2.0 * est_distance_m * math.tan(math.radians(cam_horiz_fov_deg / 2.0))
                transverse_speed_mps = round(max(-25.0, min(25.0, (dx_norm * horiz_span_m) / total_dt)), 2)
        except Exception:
            transverse_speed_mps = 0.0

    # Combine radial and transverse components (accounting for oblique trail mounting angle)
    if abs(radial_speed_mps) > 0.05 and abs(transverse_speed_mps) < 0.05:
        oblique_rad = math.radians(max(5.0, min(75.0, float(oblique_trail_deg))))
        ground_speed_mps = abs(radial_speed_mps) / max(0.5, math.cos(oblique_rad))
        sign_dir = 1.0 if radial_speed_mps >= 0 else -1.0
        transverse_speed_mps = round(sign_dir * ground_speed_mps * math.sin(oblique_rad), 2)
    else:
        ground_speed_mps = math.hypot(radial_speed_mps, transverse_speed_mps)

    # Default nominal movement speed by class ONLY if triggered without an explicit radar SPD field
    explicit_stationary_radar = ("SPD" in trig) and (abs(radar_spd_cms) < 1e-6) and (abs(transverse_speed_mps) < 0.05)
    if ground_speed_mps < 0.15 and primary_det is not None and not explicit_stationary_radar:
        default_speeds = {
            "person": 1.45,
            "bicycle": 4.50,
            "car": 8.33,
            "motorcycle_atv_snowmobile": 7.50,
            "truck_tractor": 6.50,
            "boat_watercraft": 5.00,
        }
        ground_speed_mps = default_speeds.get(subj_class, 1.40)
        oblique_rad = math.radians(float(oblique_trail_deg))
        radial_speed_mps = round(ground_speed_mps * math.cos(oblique_rad), 2)
        transverse_speed_mps = round(ground_speed_mps * math.sin(oblique_rad), 2)

    est_speed_mps = round(ground_speed_mps, 2)
    est_speed_kmh = round(est_speed_mps * 3.6, 1)

    # Relative heading angle in camera frame (0 deg = moving away along boresight, 180 deg = approaching camera)
    if est_speed_mps < 0.1:
        movement_direction = "stationary"
        rel_heading_deg = 0.0
    else:
        # Convert (radial, transverse) into relative movement bearing
        # Positive radial_speed_mps = approaching camera (180 deg relative to camera look vector)
        away_vel_m = -radial_speed_mps
        rel_heading_deg = round(math.degrees(math.atan2(transverse_speed_mps, away_vel_m)) % 360.0, 1)
        if abs(radial_speed_mps) >= abs(transverse_speed_mps):
            movement_direction = "approaching" if radial_speed_mps > 0 else "receding"
        else:
            movement_direction = "traversing_right" if transverse_speed_mps > 0 else "traversing_left"

    return {
        "primary_class": subj_class,
        "primary_conf": subj_conf,
        "bearing_offset_deg": bearing_offset_deg,
        "est_distance_m": est_distance_m,
        "radial_speed_mps": radial_speed_mps,
        "transverse_speed_mps": transverse_speed_mps,
        "est_speed_mps": est_speed_mps,
        "est_speed_kmh": est_speed_kmh,
        "relative_heading_deg": rel_heading_deg,
        "movement_direction": movement_direction,
    }


def estimate_all_subjects_kinematics(
    detections,
    pico_telemetry,
    captured_pairs=None,
    frame_dt_s=0.05,
    cam_horiz_fov_deg=102.0,
    cam_vert_fov_deg=67.0,
    oblique_trail_deg=25.0,
):
    """
    Computes independent kinematics dictionaries for EVERY detected object in `detections`
    (sorted by descending confidence), using the 24 GHz radar range for the primary/closest
    target and pinhole angular height + bounding-box bearing offset for secondary targets
    in the same frame.
    """
    if not isinstance(detections, list) or not detections:
        return []
    valid = [d for d in detections if isinstance(d, dict)]
    valid.sort(key=lambda d: float(d.get("conf", d.get("confidence", 0.0)) or 0.0), reverse=True)
    results = []
    for idx, det in enumerate(valid):
        # Primary detection uses radar DIST if present; secondary detections use pinhole box height
        # so two objects at different distances in the same frame are resolved independently.
        telem = pico_telemetry if idx == 0 else "TRIG,DIRECT_WAKE"
        kin = estimate_subject_kinematics(
            detections=[det],
            pico_telemetry=telem,
            captured_pairs=captured_pairs if idx == 0 else None,
            frame_dt_s=frame_dt_s,
            cam_horiz_fov_deg=cam_horiz_fov_deg,
            cam_vert_fov_deg=cam_vert_fov_deg,
            oblique_trail_deg=oblique_trail_deg,
        )
        kin["detection_index"] = idx
        results.append(kin)
    return results


# ==============================================================================
# Main Pipeline with Strict Fault Recovery
# ==============================================================================
def main():
    try:
        # Refresh node identity and key in case NODE_KEY_FILE / NODE_ID were configured at runtime
        active_signing_key = load_signing_key()
        iface = setup_unidirectional_network()
        raw_pico_telemetry = read_pico_telemetry()
        pico_telemetry, ephemeral_sk = derive_ephemeral_key_from_trig(raw_pico_telemetry)
        if ephemeral_sk is not None:
            active_signing_key = ephemeral_sk

        # Initialize Camera with Picamera2 using synchronized single-request capture
        picam2 = None
        captured_pairs = []

        try:
            from picamera2 import Picamera2  # type: ignore[import-not-found]
            picam2 = Picamera2()
            cfg_fn = getattr(picam2, "create_preview_configuration", None) or getattr(picam2, "create_still_configuration")
            config = cfg_fn(
                main={"size": (1920, 1080), "format": "RGB888"},
                lores={"size": (640, 640), "format": "RGB888"}
            )
            picam2.configure(config)
            picam2.start()
            # Lock IMX708 VCM voice-coil lens to Hyperfocal position (0.5 diopters = 2.0m center,
            # keeping 1.0m to infinity razor-sharp with 0ms PDAF hunting on foreground twigs/snow)
            if hasattr(picam2, "set_controls"):
                try:
                    lens_pos = float(os.getenv("CAM_LENS_POSITION", "0.5"))
                    picam2.set_controls({"AfMode": 0, "LensPosition": lens_pos})
                except Exception:
                    pass
            time.sleep(0.25)
            # Pulse 940nm IR strobe only during active exposure window (NVG stealth discipline)
            pulse_ir_illuminator_strobe(30)
            for _ in range(3):
                if hasattr(picam2, "capture_request"):
                    req = picam2.capture_request()
                    try:
                        lores_f = req.make_array("lores")
                        main_f = req.make_array("main")
                    finally:
                        req.release()
                else:
                    lores_f = picam2.capture_array("lores")
                    main_f = picam2.capture_array("main")
                captured_pairs.append((lores_f, main_f))
                time.sleep(0.05)
        except Exception as e:
            print(f"[!] Picamera2 initialization error: {e}", file=sys.stderr)
        finally:
            if picam2:
                try:
                    picam2.stop()
                except Exception:
                    pass

        camera_ok = bool(captured_pairs)
        main_frame = captured_pairs[-1][1] if captured_pairs else None

        # If camera failed, generate a clean zero-initialized test frame for operator feedback
        if main_frame is None:
            canvas = np.zeros((1080, 1920, 3), dtype=np.uint8)
            main_frame = cv2.putText(
                canvas,
                "CAMERA SENSOR ERROR", (200, 540),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 3
            )

        detections_found = []
        best_crop_jpeg = b""
        best_crop_bounds = None
        best_crop_frame_shape = main_frame.shape
        inference_backend = "camera_error" if not camera_ok else "full_frame"

        # Attempt Hailo NPU Inference across captured frames with Graceful CPU Fallback
        hailo_available = False
        if os.path.exists(HEF_PATH) and captured_pairs:
            try:
                from picamera2.devices import Hailo  # type: ignore[import-not-found]
                with Hailo(HEF_PATH) as hailo:
                    for lores_frame, m_frame in captured_pairs:
                        results = hailo.run(lores_frame)
                        hailo_available = True
                        inference_backend = "hailo"
                        best_score = -1.0
                        for class_id, bboxes in enumerate(results):
                            if class_id in TARGET_CLASSES and len(bboxes) > 0:
                                for box in bboxes:
                                    score = float(box[4])
                                    if score >= CONF_THRESHOLD:
                                        ymin, xmin, ymax, xmax = [float(v) for v in box[:4]]
                                        detections_found.append({
                                            "class": TARGET_CLASSES[class_id],
                                            "conf": round(score, 2),
                                            "box": [round(xmin, 3), round(ymin, 3), round(xmax, 3), round(ymax, 3)]
                                        })
                                        if score > best_score:
                                            best_score = score
                                            best_crop_jpeg, best_crop_bounds = _encode_target_crop(
                                                m_frame, xmin, ymin, xmax, ymax, return_bounds=True
                                            )
                                            best_crop_frame_shape = m_frame.shape
                        if detections_found:
                            break
            except Exception as e:
                hailo_available = False
                detections_found = []
                best_crop_jpeg = b""
                best_crop_bounds = None
                print(f"[!] Hailo NPU runtime failure (falling back to CPU): {e}", file=sys.stderr)

        # Fallback 1: CPU YOLOv8n ONNX inference via OpenCV DNN with NMSBoxes
        if not hailo_available and os.path.exists(ONNX_PATH) and captured_pairs:
            try:
                net = cv2.dnn.readNetFromONNX(ONNX_PATH)
                lores_frame, m_frame = captured_pairs[-1]
                # Picamera2 RGB888 is BGR in memory; swapRB=True produces RGB input expected by YOLOv8 ONNX
                swap_rb = os.getenv("CAMERA_COLOR_SWAP_RB", "1") == "1"
                blob = cv2.dnn.blobFromImage(lores_frame, 1.0 / 255.0, (640, 640), swapRB=swap_rb, crop=False)
                net.setInput(blob)
                preds = net.forward()
                inference_backend = "onnx_cpu"
                # YOLOv8 output shape: (1, 84, 8400) -> transpose to (8400, 84)
                if preds.ndim == 3 and preds.shape[1] < preds.shape[2]:
                    preds = np.transpose(preds[0], (1, 0))
                elif preds.ndim == 3:
                    preds = preds[0]

                boxes_xywh = []
                scores_list = []
                class_ids = []
                norm_boxes = []
                for row in preds:
                    scores = row[4:]
                    class_id = int(np.argmax(scores))
                    score = float(scores[class_id])
                    if class_id in TARGET_CLASSES and score >= CONF_THRESHOLD:
                        cx, cy, bw, bh = [float(v) for v in row[:4]]
                        xmin = max(0.0, (cx - bw / 2.0) / 640.0)
                        ymin = max(0.0, (cy - bh / 2.0) / 640.0)
                        xmax = min(1.0, (cx + bw / 2.0) / 640.0)
                        ymax = min(1.0, (cy + bh / 2.0) / 640.0)
                        boxes_xywh.append([int(xmin * 640), int(ymin * 640), int((xmax - xmin) * 640), int((ymax - ymin) * 640)])
                        scores_list.append(score)
                        class_ids.append(class_id)
                        norm_boxes.append((xmin, ymin, xmax, ymax))

                if boxes_xywh:
                    indices = cv2.dnn.NMSBoxes(boxes_xywh, scores_list, CONF_THRESHOLD, 0.45)
                    flat_indices = [int(i[0]) if isinstance(i, (list, tuple, np.ndarray)) else int(i) for i in indices]
                    best_score = -1.0
                    for idx in flat_indices:
                        xmin, ymin, xmax, ymax = norm_boxes[idx]
                        score = scores_list[idx]
                        cid = class_ids[idx]
                        detections_found.append({
                            "class": TARGET_CLASSES[cid],
                            "conf": round(score, 2),
                            "box": [round(xmin, 3), round(ymin, 3), round(xmax, 3), round(ymax, 3)]
                        })
                        if score > best_score:
                            best_score = score
                            best_crop_jpeg, best_crop_bounds = _encode_target_crop(
                                m_frame, xmin, ymin, xmax, ymax, return_bounds=True
                            )
                            best_crop_frame_shape = m_frame.shape
            except Exception as e:
                print(f"[!] CPU ONNX fallback warning: {e}", file=sys.stderr)

        # Fallback 2: Multi-frame inter-frame motion ROI crop if NPU/ONNX unavailable
        if not hailo_available and not best_crop_jpeg and len(captured_pairs) >= 2:
            try:
                g1 = cv2.cvtColor(captured_pairs[0][0], cv2.COLOR_BGR2GRAY)
                g2 = cv2.cvtColor(captured_pairs[-1][0], cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(cv2.GaussianBlur(g1, (5, 5), 0), cv2.GaussianBlur(g2, (5, 5), 0))
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts:
                    largest = max(cnts, key=cv2.contourArea)
                    if cv2.contourArea(largest) > 400:
                        rx, ry, rw, rh = cv2.boundingRect(largest)
                        xmin, ymin = rx / 640.0, ry / 640.0
                        xmax, ymax = (rx + rw) / 640.0, (ry + rh) / 640.0
                        detections_found.append({
                            "class": "motion_target",
                            "conf": 0.75,
                            "box": [round(xmin, 3), round(ymin, 3), round(xmax, 3), round(ymax, 3)]
                        })
                        inference_backend = "motion_roi"
                        best_crop_jpeg, best_crop_bounds = _encode_target_crop(
                            captured_pairs[-1][1], xmin, ymin, xmax, ymax, return_bounds=True
                        )
                        best_crop_frame_shape = captured_pairs[-1][1].shape
            except Exception:
                pass

        # Remap detection bounding boxes into the cropped image's coordinate frame
        if best_crop_jpeg and best_crop_bounds is not None:
            detections_found = remap_detections_to_crop(
                detections_found, best_crop_bounds, best_crop_frame_shape
            )

        # Fallback 3: if no target detected or NPU unavailable, encode a scaled full-frame snapshot
        if not best_crop_jpeg:
            fallback_bgr = cv2.resize(main_frame, (960, 540))
            if os.getenv("CAMERA_COLOR_SWAP_RB", "0") == "1":
                fallback_bgr = cv2.cvtColor(fallback_bgr, cv2.COLOR_RGB2BGR)
            if not camera_ok:
                status_text = "CAMERA SENSOR ERROR"
            elif hailo_available:
                status_text = "RADAR/SEIS TRIGGER (NO AI DETECTION)"
            else:
                status_text = "NPU OFFLINE - FULL VIEW"
            cv2.putText(fallback_bgr, status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            _, enc = cv2.imencode(".jpg", fallback_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
            best_crop_jpeg = enc.tobytes()

        # Ensure 1000BASE-T / optical carrier has completed auto-negotiation before firing UDP burst
        wait_for_ethernet_carrier(iface=iface, timeout_s=3.0)

        # Construct and fire alert payload over optical diode
        subject_kinematics = estimate_subject_kinematics(
            detections_found, pico_telemetry, captured_pairs=captured_pairs
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        alert_payload = {
            "node": NODE_ID,
            "ts": int(time.time()),
            "pico_trig": pico_telemetry,
            "detections": detections_found,
            "subject_kinematics": subject_kinematics,
            "hailo_active": hailo_available,
            "camera_ok": camera_ok,
            "inference_backend": inference_backend,
        }
        transmit_over_diode(sock, alert_payload, best_crop_jpeg, custom_signing_key=active_signing_key)
        sock.close()

    except Exception as e:
        print(f"[CRITICAL] Uncaught exception in sender pipeline: {e}", file=sys.stderr)
    finally:
        # ABSOLUTE SAFETY INVARIANT: Always assert DONE to cut Domain B power
        signal_pico_done()

if __name__ == "__main__":
    main()

