#!/usr/bin/env python3
# File: tests/test_dual_node_simulation.py
# Description: End-to-end integration test validating two field-camera identities over simulated diode transmissions
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
from nacl.signing import SigningKey, VerifyKey

# Configure test environment
TEST_PORT = 15514

# Node 1: North field camera
NODE1_ID = "NODE-NORTH-01"
NODE1_PRIV = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
NODE1_SIGN = SigningKey(bytes.fromhex(NODE1_PRIV))
NODE1_PUB = NODE1_SIGN.verify_key

# Node 2: South field camera (same hardware platform)
NODE2_ID = "NODE-SOUTH-02"
NODE2_PRIV = "3c2ca158d682d2f44522e4333fccc23c709171c687eadc24d48f4a4a2a146170"
NODE2_SIGN = SigningKey(bytes.fromhex(NODE2_PRIV))
NODE2_PUB = NODE2_SIGN.verify_key

KNOWN_KEYS = {
    NODE1_ID: NODE1_PUB,
    NODE2_ID: NODE2_PUB,
}

received_nodes = set()
reconstructed_images = {}

def receiver_thread_func(stop_event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", TEST_PORT))
    sock.settimeout(0.5)

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

        if pkt_type == 1 and len(pkt) > 67:
            sig = pkt[3:67]
            meta_bytes = pkt[67:]
            try:
                meta = json.loads(meta_bytes.decode("utf-8"))
                node_id = meta.get("node")
                if node_id in KNOWN_KEYS:
                    KNOWN_KEYS[node_id].verify(meta_bytes, sig)
                    nonce_hex = meta.get("nonce", "")
                    prefix = nonce_hex if (isinstance(nonce_hex, str) and len(nonce_hex) == 16) else meta["img_sha256"][:16]
                    if prefix not in pending_meta:
                        pending_meta[prefix] = meta
                        received_nodes.add(node_id)
            except Exception:
                pass

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
                    reconstructed_images[meta["node"]] = full_img
                    del pending_meta[prefix]
                    del pending_chunks[prefix]

    sock.close()

def send_simulated_alert(node_id, signing_key, mock_img_bytes, pico_trig, detections):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload_hash = hashlib.sha256(mock_img_bytes).hexdigest()
    burst_nonce = secrets.token_hex(8)
    nonce_bytes = bytes.fromhex(burst_nonce)

    meta = {
        "node": node_id,
        "ts": int(time.time()),
        "pico_trig": pico_trig,
        "detections": detections,
        "img_sha256": payload_hash,
        "img_size": len(mock_img_bytes),
        "nonce": burst_nonce
    }

    meta_bytes = json.dumps(meta, separators=(",", ":")).encode("utf-8")
    sig = signing_key.sign(meta_bytes).signature
    header_pkt = b"DD\x01" + sig + meta_bytes

    CHUNK_SIZE = 1024
    chunks = [mock_img_bytes[i:i + CHUNK_SIZE] for i in range(0, len(mock_img_bytes), CHUNK_SIZE)]
    total_chunks = len(chunks)

    # 3x carousel
    for _ in range(3):
        sock.sendto(header_pkt, ("127.0.0.1", TEST_PORT))
        time.sleep(0.001)
        for idx, chunk in enumerate(chunks):
            chunk_hdr = b"DD\x02" + nonce_bytes + struct.pack(">HH", idx, total_chunks)
            sock.sendto(chunk_hdr + chunk, ("127.0.0.1", TEST_PORT))
            time.sleep(0.0005)
    sock.close()

def test_dual_node_simulation():
    stop_event = threading.Event()
    recv_t = threading.Thread(target=receiver_thread_func, args=(stop_event,))
    recv_t.start()
    time.sleep(0.1)

    print("[1] Transmitting alert from north field camera (NODE-NORTH-01)...")
    north_img = os.urandom(8192)  # 8KB mock JPEG
    send_simulated_alert(
        NODE1_ID, NODE1_SIGN, north_img,
        "TRIG,MAG=3200,SEIS=850,DIST=4500,SPD=12",
        [{"class": "person", "conf": 0.94}]
    )

    time.sleep(0.2)

    print("[2] Transmitting alert from south field camera (NODE-SOUTH-02)...")
    south_img = os.urandom(4096)  # 4KB mock JPEG
    send_simulated_alert(
        NODE2_ID, NODE2_SIGN, south_img,
        "TRIG,DIRECT_WAKE",
        [{"class": "car", "conf": 0.88}]
    )

    time.sleep(0.5)
    stop_event.set()
    recv_t.join()

    # Assertions
    assert NODE1_ID in received_nodes, f"Failed to receive metadata from {NODE1_ID}"
    assert NODE2_ID in received_nodes, f"Failed to receive metadata from {NODE2_ID}"
    assert reconstructed_images.get(NODE1_ID) == north_img, f"Image corruption on {NODE1_ID}"
    assert reconstructed_images.get(NODE2_ID) == south_img, f"Image corruption on {NODE2_ID}"

    print(f"\n[+] SUCCESS: Both field cameras ({NODE1_ID}, {NODE2_ID}) successfully verified!")
    print(f"    - All Ed25519 signatures matched corresponding public keys")
    print(f"    - All binary image chunks reassembled with 100% SHA-256 integrity")

import unittest


class TestSharedDualNodeSuite(unittest.TestCase):
    def test_dual_camera_ed25519_and_chunk_reassembly(self):
        test_dual_node_simulation()


if __name__ == "__main__":
    test_dual_node_simulation()

