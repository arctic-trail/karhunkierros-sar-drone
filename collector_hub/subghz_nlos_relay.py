#!/usr/bin/env python3
"""
File: collector_hub/subghz_nlos_relay.py
Description: 2 km Non-Line-of-Sight (NLOS) Sub-GHz FHSS / LoRa One-Way Relay Bridge
             for Scenario B1+ (Lake Cottage -> 200m Moss Fiber -> Hidden Vault -> 2km Forest -> Farmhouse).
License: MIT

Architecture:
  1. At the Lake Cottage: The 3-Zone Split-Pod Camera Node emits ZERO radio waves (100% immune
     to portable RF jammers and RF scanners near the cottage). It transmits the full signed
     JPEG over 150m–300m of 3mm moss-buried single-mode fiber up the hill/forest to a buried
     waterproof Dead-Drop Vault.
  2. At the Buried Vault (200m away, outside any portable jammer radius):
     `receiver_hub.py` verifies and stores the full-res JPEG on local SSD, then invokes this
     script via `ALERT_HOOK_SCRIPT`. This script compresses a compact target-crop thumbnail
     (<= 6 KB) so it can cross a 2 km non-line-of-sight wooded hill in 0.5–2.5 seconds over
     a COTS Sub-GHz FHSS/CSS serial transceiver (e.g., Digi XBee-PRO SX 868 MHz [EU/Finland]
     or Digi XBee-PRO 900HP [US], or Adafruit Feather RP2040 RFM95 LoRa).
  3. At the Farmhouse (2 km away):
     This script runs in `--mode rx-bridge`, reading frames from the Farmhouse Sub-GHz receiver,
     verifying CRC32 integrity, and injecting standard `DD\x01` / `DD\x02` UDP packets into the
     Farmhouse's local `receiver_hub.py` (UDP 127.0.0.1:5514) for live display on the dashboard.
"""
import os
import sys
import json
import time
import zlib
import struct
import socket
import hashlib
import argparse
from io import BytesIO

FRAME_MAGIC = b"NLOS"
MAX_THUMB_BYTES = 6144
CHUNK_SIZE = 200  # Sub-GHz packet-friendly chunk size (fits single XBee-PRO / LoRa MTU)


def compress_for_subghz_nlos(img_bytes, max_bytes=MAX_THUMB_BYTES):
    """
    Compresses a captured JPEG into a compact <= 6 KB valid JPEG thumbnail suitable for rapid
    1–3 second transmission across a 2 km non-line-of-sight Sub-GHz FHSS/LoRa link.
    Never truncates raw JPEG bytes mid-stream.
    """
    if len(img_bytes) <= max_bytes:
        return img_bytes

    # Primary encoder: Pillow (PIL) progressive downscale
    try:
        from PIL import Image
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        out = None
        for max_dim, qual in ((480, 60), (360, 52), (280, 45), (200, 38), (160, 30), (120, 24), (96, 20)):
            copy = img.copy()
            copy.thumbnail((max_dim, max_dim))
            buf = BytesIO()
            copy.save(buf, format="JPEG", quality=qual, optimize=True)
            out = buf.getvalue()
            if len(out) <= max_bytes:
                return out
        if out and out.startswith(b"\xff\xd8") and out.endswith(b"\xff\xd9") and len(out) <= max_bytes:
            return out
    except Exception:
        pass

    # Secondary encoder: OpenCV (cv2) decode + resize + imencode
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        decoded = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if decoded is not None:
            h, w = decoded.shape[:2]
            for scale, qual in ((0.5, 55), (0.35, 48), (0.25, 40), (0.18, 32), (0.12, 24)):
                nh, nw = max(32, int(h * scale)), max(32, int(w * scale))
                resized = cv2.resize(decoded, (nw, nh))
                ok, enc = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), qual])
                if ok:
                    candidate = enc.tobytes()
                    if len(candidate) <= max_bytes:
                        return candidate
    except Exception:
        pass

    raise ValueError(
        f"Unable to re-encode payload ({len(img_bytes)} bytes) into a valid JPEG <= {max_bytes} bytes; "
        f"refusing to truncate raw bytes."
    )


def _load_relay_signing_key_hex(explicit_hex=None):
    """Loads the relay signing key from explicit argument, environment, or node_key.json."""
    if explicit_hex:
        return explicit_hex
    env_hex = os.getenv("NODE_SIGNING_KEY_HEX") or os.getenv("PRIVATE_KEY_HEX")
    if env_hex:
        return env_hex
    for kf in (os.getenv("NODE_KEY_FILE", "/etc/trailcam/node_key.json"), "./node_key.json"):
        if kf and os.path.isfile(kf):
            try:
                with open(kf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("private_key_hex"):
                    return data["private_key_hex"]
            except Exception:
                pass
    if os.getenv("ALLOW_EXAMPLE_KEYS", "1") == "0":
        raise RuntimeError("No relay signing key provisioned while ALLOW_EXAMPLE_KEYS=0")
    return "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"


def build_nlos_serial_frames(alert_meta, img_bytes, signing_key_hex):
    """
    Builds a sequence of CRC32-framed `DD\x01` (signed metadata) and `DD\x02` (chunk)
    packets wrapped in `NLOS` serial frames for one-way Sub-GHz transmission.
    """
    from nacl.signing import SigningKey

    thumb_bytes = compress_for_subghz_nlos(img_bytes)
    thumb_sha256 = hashlib.sha256(thumb_bytes).hexdigest()
    nonce_hex = alert_meta.get("nonce") or os.urandom(8).hex()
    if len(nonce_hex) != 16:
        nonce_hex = hashlib.sha256(nonce_hex.encode("utf-8")).hexdigest()[:16]

    nlos_meta = {
        "node": alert_meta.get("node", "NODE-NORTH-01"),
        "ts": int(alert_meta.get("timestamp", alert_meta.get("ts", time.time()))),
        "nonce": nonce_hex,
        "img_sha256": thumb_sha256,
        "detections": alert_meta.get("detections", []),
        "pico_trig": alert_meta.get("pico_trig", ""),
        "camera_ok": alert_meta.get("camera_ok", True),
        "inference_backend": alert_meta.get("inference_backend", "subghz_nlos_relay"),
        "full_res_vaulted": True,
    }
    meta_bytes = json.dumps(nlos_meta, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sk = SigningKey(bytes.fromhex(signing_key_hex))
    sig = sk.sign(meta_bytes).signature
    dd01_pkt = b"DD\x01" + sig + meta_bytes

    nonce_bin = bytes.fromhex(nonce_hex)
    chunks = [thumb_bytes[i:i + CHUNK_SIZE] for i in range(0, len(thumb_bytes), CHUNK_SIZE)]
    total_chunks = len(chunks)

    dd_packets = [dd01_pkt]
    for idx, c_data in enumerate(chunks):
        header = b"DD\x02" + nonce_bin + struct.pack(">HH", idx, total_chunks)
        dd_packets.append(header + c_data)

    # Wrap each DD datagram in a self-synchronizing NLOS serial frame:
    # [b"NLOS" (4B)] [length: uint16 (2B)] [CRC32: uint32 (4B)] [dd_pkt (N B)]
    serial_frames = []
    for pkt in dd_packets:
        crc = zlib.crc32(pkt) & 0xFFFFFFFF
        frame = FRAME_MAGIC + struct.pack(">HI", len(pkt), crc) + pkt
        serial_frames.append(frame)

    return serial_frames, nlos_meta, thumb_bytes


def parse_nlos_serial_stream(stream_bytes):
    """
    Scans a raw serial byte stream from a Sub-GHz FHSS/LoRa receiver, validates
    `NLOS` headers and CRC32 checksums, and returns a list of valid `DD` UDP datagrams.
    Tolerates arbitrary channel noise bytes between frames.
    """
    valid_dd_packets = []
    idx = 0
    n = len(stream_bytes)
    while idx <= n - 10:
        pos = stream_bytes.find(FRAME_MAGIC, idx)
        if pos == -1 or pos > n - 10:
            break
        pkt_len, expected_crc = struct.unpack(">HI", stream_bytes[pos + 4:pos + 10])
        if pkt_len == 0 or pkt_len > 2048 or (pos + 10 + pkt_len) > n:
            idx = pos + 4
            continue
        candidate_pkt = stream_bytes[pos + 10:pos + 10 + pkt_len]
        actual_crc = zlib.crc32(candidate_pkt) & 0xFFFFFFFF
        if actual_crc == expected_crc and candidate_pkt[:2] == b"DD":
            valid_dd_packets.append(candidate_pkt)
            idx = pos + 10 + pkt_len
        else:
            idx = pos + 4
    return valid_dd_packets


def consume_nlos_stream_buffer(buf_bytes):
    """
    Extracts all complete, CRC32-verified DD datagrams from `buf_bytes` and returns
    `(valid_dd_packets, remaining_unparsed_tail_bytes)` for continuous streaming RX bridges.
    """
    valid_dd_packets = []
    idx = 0
    n = len(buf_bytes)
    while idx <= n - 10:
        pos = buf_bytes.find(FRAME_MAGIC, idx)
        if pos == -1:
            # Keep last 3 bytes in case 'NLO' was split across a read boundary
            return valid_dd_packets, buf_bytes[max(idx, n - 3):]
        if pos > n - 10:
            return valid_dd_packets, buf_bytes[pos:]
        pkt_len, expected_crc = struct.unpack(">HI", buf_bytes[pos + 4:pos + 10])
        if pkt_len == 0 or pkt_len > 2048:
            idx = pos + 4
            continue
        if pos + 10 + pkt_len > n:
            # Frame is still arriving over serial; retain from `pos` onward
            return valid_dd_packets, buf_bytes[pos:]
        candidate_pkt = buf_bytes[pos + 10:pos + 10 + pkt_len]
        actual_crc = zlib.crc32(candidate_pkt) & 0xFFFFFFFF
        if actual_crc == expected_crc and candidate_pkt[:2] == b"DD":
            valid_dd_packets.append(candidate_pkt)
            idx = pos + 10 + pkt_len
        else:
            idx = pos + 4
    return valid_dd_packets, buf_bytes[idx:]


def forward_stream_to_hub(stream_bytes, hub_ip="127.0.0.1", hub_port=5514):
    """Extracts verified NLOS frames and forwards inner DD packets to local receiver_hub.py."""
    packets = parse_nlos_serial_stream(stream_bytes)
    if not packets:
        return 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for pkt in packets:
            sock.sendto(pkt, (hub_ip, hub_port))
            time.sleep(0.0005)
    finally:
        sock.close()
    return len(packets)


def transmit_nlos_payload(payload_bytes, serial_port="/dev/ttyUSB0", baud=115200, udp_bridge_addr=None):
    """Writes NLOS-framed payload to the Sub-GHz serial transceiver (or optional UDP test bridge)."""
    sent = False
    if udp_bridge_addr:
        host, port = udp_bridge_addr
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Send in <= 1200B UDP datagrams so stream reassembler can test split-frame reassembly
            for i in range(0, len(payload_bytes), 1200):
                sock.sendto(payload_bytes[i:i + 1200], (host, int(port)))
                time.sleep(0.0005)
            sent = True
        finally:
            sock.close()
    if serial_port and os.path.exists(serial_port):
        import serial
        with serial.Serial(serial_port, baud, timeout=2.0) as ser:
            ser.write(payload_bytes)
            ser.flush()
            sent = True
    return sent


def run_rx_bridge(serial_port="/dev/ttyUSB0", baud=115200, hub_ip="127.0.0.1", hub_port=5514, listen_udp_port=0, max_packets=0):
    """
    Runs the Farmhouse Sub-GHz RX Bridge (`--mode rx-bridge` / `--mode rx-farmhouse`).
    Reads NLOS serial frames from the Sub-GHz transceiver (or local UDP test socket),
    verifies CRC32, and injects reconstructed `DD\x01` / `DD\x02` datagrams into `receiver_hub.py`.
    """
    rx_buf = b""
    forwarded_total = 0
    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    udp_in_sock = None
    if listen_udp_port and listen_udp_port > 0:
        udp_in_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_in_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_in_sock.bind(("127.0.0.1", int(listen_udp_port)))
        udp_in_sock.settimeout(0.5)

    ser = None
    if not udp_in_sock and serial_port and os.path.exists(serial_port):
        import serial
        ser = serial.Serial(serial_port, baud, timeout=0.5)

    try:
        while True:
            chunk = b""
            if udp_in_sock is not None:
                try:
                    chunk, _ = udp_in_sock.recvfrom(65535)
                except socket.timeout:
                    chunk = b""
            elif ser is not None:
                chunk = ser.read(4096)
            else:
                time.sleep(0.2)

            if chunk:
                rx_buf += chunk
                dd_pkts, rx_buf = consume_nlos_stream_buffer(rx_buf)
                for pkt in dd_pkts:
                    out_sock.sendto(pkt, (hub_ip, hub_port))
                    forwarded_total += 1
                    time.sleep(0.0005)
                if max_packets > 0 and forwarded_total >= max_packets:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        out_sock.close()
        if udp_in_sock:
            udp_in_sock.close()
        if ser:
            ser.close()
    return forwarded_total


def run_tx_vault_watcher(vault_dir, serial_port, baud, signing_key_hex, udp_bridge_addr=None, once=False):
    """
    Watches `vault_dir/alerts_journal.jsonl` in `--mode tx-vault` and transmits new alerts
    over the 2 km Sub-GHz NLOS link. Skips stale records older than 300s (receiver_hub replay window).
    """
    journal_path = os.path.join(vault_dir, "alerts_journal.jsonl")
    seen_nonces = set()
    relayed_count = 0

    while True:
        if os.path.isfile(journal_path):
            with open(journal_path, "r", encoding="utf-8") as jf:
                for line in jf:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    nonce = rec.get("nonce")
                    if not nonce or nonce in seen_nonces:
                        continue
                    rec_ts = int(rec.get("timestamp", 0) or 0)
                    if rec_ts > 0 and abs(time.time() - rec_ts) > 300:
                        seen_nonces.add(nonce)
                        continue
                    img_rel = os.path.basename(rec.get("image_file", ""))
                    jpg_path = os.path.join(vault_dir, img_rel)
                    if not os.path.isfile(jpg_path):
                        continue
                    with open(jpg_path, "rb") as imgf:
                        img_bytes = imgf.read()
                    frames, _, _ = build_nlos_serial_frames(rec, img_bytes, signing_key_hex)
                    payload = b"".join(frames) * 2
                    transmit_nlos_payload(payload, serial_port=serial_port, baud=baud, udp_bridge_addr=udp_bridge_addr)
                    seen_nonces.add(nonce)
                    relayed_count += 1
        if once:
            break
        time.sleep(1.0)
    return relayed_count


def main():
    parser = argparse.ArgumentParser(
        description="2 km NLOS Sub-GHz FHSS/LoRa One-Way Relay (Vault TX Hook/Watcher & Farmhouse RX Bridge)"
    )
    parser.add_argument("hook_args", nargs="*", help="Optional [jpg_path, alert_json] when called as ALERT_HOOK_SCRIPT")
    parser.add_argument(
        "--mode",
        choices=["tx-hook", "tx-vault", "rx-bridge", "rx-farmhouse"],
        default="tx-hook",
        help="Operating mode: tx-hook (per-alert hook), tx-vault (directory watcher), rx-bridge / rx-farmhouse (receiver daemon)",
    )
    parser.add_argument("--vault-dir", default=os.getenv("OUT_DIR", "./verified_alerts"), help="Vault directory for --mode tx-vault")
    parser.add_argument("--serial-port", default=os.getenv("SUBGHZ_SERIAL_PORT", "/dev/ttyUSB0"))
    parser.add_argument("--baud", type=int, default=int(os.getenv("SUBGHZ_BAUD", "115200")))
    parser.add_argument("--hub-ip", default="127.0.0.1")
    parser.add_argument("--hub-port", type=int, default=5514)
    parser.add_argument("--listen-udp-port", type=int, default=0, help="Optional local UDP port for testing rx-bridge without serial hardware")
    parser.add_argument("--bridge-udp-port", type=int, default=0, help="Optional local UDP target port for testing tx-hook/tx-vault")
    parser.add_argument("--once", action="store_true", help="Process current vault alerts once and exit (for --mode tx-vault)")
    parser.add_argument("--signing-key", default=None)
    args = parser.parse_args()

    udp_bridge_addr = ("127.0.0.1", args.bridge_udp_port) if args.bridge_udp_port > 0 else None

    if args.mode in ("rx-bridge", "rx-farmhouse"):
        run_rx_bridge(
            serial_port=args.serial_port,
            baud=args.baud,
            hub_ip=args.hub_ip,
            hub_port=args.hub_port,
            listen_udp_port=args.listen_udp_port,
        )
        return

    sk_hex = _load_relay_signing_key_hex(args.signing_key)

    if args.mode == "tx-vault":
        n_sent = run_tx_vault_watcher(
            vault_dir=args.vault_dir,
            serial_port=args.serial_port,
            baud=args.baud,
            signing_key_hex=sk_hex,
            udp_bridge_addr=udp_bridge_addr,
            once=args.once,
        )
        print(f"[+] Sub-GHz NLOS Vault Watcher relayed {n_sent} alert(s)")
        return

    if args.mode == "tx-hook" and len(args.hook_args) >= 2:
        jpg_path, alert_json_str = args.hook_args[0], args.hook_args[1]
        with open(jpg_path, "rb") as f:
            img_bytes = f.read()
        alert_meta = json.loads(alert_json_str)
        frames, _, _ = build_nlos_serial_frames(alert_meta, img_bytes, sk_hex)
        payload = b"".join(frames) * 2  # 2x carousel pass over Sub-GHz FHSS
        transmit_nlos_payload(payload, serial_port=args.serial_port, baud=args.baud, udp_bridge_addr=udp_bridge_addr)
        print(f"[+] Sub-GHz NLOS Relay queued {len(frames)} frames ({len(payload)} B w/ 2x pass)")


if __name__ == "__main__":
    main()

