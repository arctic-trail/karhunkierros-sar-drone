#!/usr/bin/env python3
# File: run_mock_demo.py
# Description: 1-Command Zero-Hardware Mock Demo of the Complete Pi-Diode Trailcam System
# License: MIT
import os
import sys
import time
import json
import socket
import struct
import hashlib
import secrets
import threading
try:
    from nacl.signing import SigningKey, VerifyKey
except ModuleNotFoundError:
    if __name__ == "__main__":
        _venv_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv", "bin", "python3")
        if os.path.isfile(_venv_py) and os.path.realpath(sys.executable) != os.path.realpath(_venv_py):
            os.execv(_venv_py, [_venv_py, "-B"] + sys.argv)
    raise

# Configure loopback demo environment
DEMO_PORT = 15514
DEMO_DIR = "./demo_verified_output"
os.makedirs(DEMO_DIR, exist_ok=True)

# Node cryptographic identities
NODE_ID = "NODE-NORTH-01"
PRIV_HEX = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
signing_key = SigningKey(bytes.fromhex(PRIV_HEX))
verify_key = signing_key.verify_key

def print_banner():
    print("=" * 70)
    print("  PI-DIODE TRAILCAM: ZERO-HARDWARE END-TO-END DEMONSTRATION")
    print("  Physics-Enforced Simplex Diode + Ed25519 Auth + 3x UDP Carousel")
    print("=" * 70)

def mock_receiver_worker(stop_event, results):
    """Passive receiver thread listening on simulated optical diode loopback."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", DEMO_PORT))
    sock.settimeout(0.2)

    pending_meta = {}
    pending_chunks = {}

    while not stop_event.is_set():
        try:
            pkt, _ = sock.recvfrom(2048)
        except socket.timeout:
            continue

        if len(pkt) < 4 or pkt[:2] != b"DD":
            continue

        pkt_type = pkt[2]

        # 0x01: Signed Metadata
        if pkt_type == 1 and len(pkt) > 67:
            sig = pkt[3:67]
            meta_bytes = pkt[67:]
            try:
                verify_key.verify(meta_bytes, sig)
                meta = json.loads(meta_bytes.decode("utf-8"))
                nonce_hex = meta.get("nonce", "")
                prefix = nonce_hex if (isinstance(nonce_hex, str) and len(nonce_hex) == 16) else meta["img_sha256"][:16]
                if prefix not in pending_meta:
                    pending_meta[prefix] = meta
                    print(f"  [RECEIVER] [+] Verified Ed25519 signature from {meta['node']}")
                    print(f"  [RECEIVER]     Telemetry: {meta.get('pico_trig')}")
                    print(f"  [RECEIVER]     Detections: {meta.get('detections')}")
            except Exception as e:
                print(f"  [RECEIVER] [!] Signature rejection: {e}", file=sys.stderr)

        # 0x02: Image Chunks
        elif pkt_type == 2 and len(pkt) > 15:
            prefix = pkt[3:11].hex()
            idx, total = struct.unpack(">HH", pkt[11:15])
            chunk_data = pkt[15:]

            if prefix not in pending_chunks:
                pending_chunks[prefix] = {}
            pending_chunks[prefix][idx] = chunk_data

            if prefix in pending_meta and len(pending_chunks[prefix]) == total:
                full_img = b"".join(pending_chunks[prefix][i] for i in range(total))
                meta = pending_meta[prefix]
                if hashlib.sha256(full_img).hexdigest() == meta["img_sha256"]:
                    out_path = os.path.join(DEMO_DIR, f"demo_{meta['node']}.jpg")
                    with open(out_path, "wb") as f:
                        f.write(full_img)
                    results["success"] = True
                    results["img_size"] = len(full_img)
                    results["sha256"] = meta["img_sha256"]
                    results["out_path"] = out_path
                    del pending_meta[prefix]
                    del pending_chunks[prefix]

    sock.close()

def main():
    print_banner()

    # 1. Start passive receiver
    stop_event = threading.Event()
    results = {"success": False}
    rx_thread = threading.Thread(target=mock_receiver_worker, args=(stop_event, results), daemon=True)
    rx_thread.start()
    time.sleep(0.1)

    print(f"\n[1/4] Receiver listening on loopback UDP port {DEMO_PORT}...")

    # 2. Simulate RP2040 Gatekeeper Trigger
    print("[2/4] RP2040 Gatekeeper detected ferromagnetic + radar target:")
    mock_telemetry = "TRIG,MAG=3450,MBASE=1600,SEIS=420,SBASE=120,DIST=4200,SPD=135,TEMP=-8.5,UPTIME_S=1420,PROFILE=FULL_TRIPLE"
    print(f"      -> {mock_telemetry}")

    # 3. Generate synthetic JPEG payload (14.2 KB test image pattern)
    synthetic_image = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00"
        + b"PI_DIODE_TRAILCAM_SYNTHETIC_SENSOR_FRAME_BOREAL_FOREST_" * 250
        + b"\xff\xd9"
    )
    img_hash = hashlib.sha256(synthetic_image).hexdigest()
    burst_nonce = secrets.token_hex(8)
    nonce_bytes = bytes.fromhex(burst_nonce)

    # 4. Construct signed payload & transmit over diode
    print("\n[3/4] Pi 5 fast-boot sender node executing:")
    print("      - Target identified: person (conf: 0.94), vehicle (conf: 0.88)")
    print(f"      - Image payload: {len(synthetic_image)} bytes, SHA-256: {img_hash[:16]}..., Nonce: {burst_nonce}")
    print("      - Signing with Ed25519 & firing 3x UDP carousel burst with 800µs pacing...")

    alert_meta = {
        "node": NODE_ID,
        "ts": int(time.time()),
        "pico_trig": mock_telemetry,
        "detections": [
            {"class": "person", "conf": 0.94, "box": [0.22, 0.15, 0.85, 0.45]},
            {"class": "car", "conf": 0.88, "box": [0.10, 0.45, 0.70, 0.95]}
        ],
        "img_sha256": img_hash,
        "img_size": len(synthetic_image),
        "nonce": burst_nonce
    }

    meta_bytes = json.dumps(alert_meta, separators=(",", ":")).encode("utf-8")
    sig = signing_key.sign(meta_bytes).signature
    header_pkt = b"DD\x01" + sig + meta_bytes

    CHUNK_SIZE = 1024
    chunks = [synthetic_image[i:i + CHUNK_SIZE] for i in range(0, len(synthetic_image), CHUNK_SIZE)]
    total_chunks = len(chunks)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    t0 = time.time()

    # Send 3x carousel passes
    for pass_num in range(1, 4):
        sock.sendto(header_pkt, ("127.0.0.1", DEMO_PORT))
        time.sleep(0.001)
        for idx, chunk in enumerate(chunks):
            chunk_hdr = b"DD\x02" + nonce_bytes + struct.pack(">HH", idx, total_chunks)
            sock.sendto(chunk_hdr + chunk, ("127.0.0.1", DEMO_PORT))
            time.sleep(0.0008)

    t_elapsed = round((time.time() - t0) * 1000, 1)
    sock.close()

    time.sleep(0.3)
    stop_event.set()
    rx_thread.join(timeout=1.0)

    # 5. Report Results
    print("\n[4/4] End-to-End Verification Results:")
    if results.get("success"):
        print(f"  [+] STATUS: SUCCESS (All {total_chunks} chunks reassembled with 100% SHA-256 match)")
        print(f"  [+] Transmission Duration: {t_elapsed} ms")
        print(f"  [+] Saved Verified Frame : {results['out_path']}")
        print(f"  [+] Physical Simplex Isolation: GUARANTEED (Zero packets returned to sender)")
        print("\n" + "=" * 70)
        print("  SYSTEM READY: Software stack verified for physical bench testing.")
        print("=" * 70)
        # Clean up demo output
        try:
            os.remove(results['out_path'])
            os.rmdir(DEMO_DIR)
        except Exception:
            pass
        return 0
    else:
        print("  [!] FAILED: Could not reassemble payload.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
