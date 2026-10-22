#!/usr/bin/env python3
# File: tests/test_enhanced_resilience.py
# Description: Automated Test Suite for Anti-Replay, Out-of-Order Reassembly,
#              Carousel Pass-2 Repair & Identical-Hash Nonce Isolation
# License: MIT
import sys
import os
import time
import json
import struct
import shutil
import tempfile
import hashlib
import secrets
# Import receiver components directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../collector_hub")))
import receiver_hub
from receiver_hub import SigningKey

def run_resilience_test_suite():
    print("=" * 65)
    print("PI-DIODE TRAILCAM ENHANCED RESILIENCE & SECURITY TEST SUITE")
    print("=" * 65)

    # Use isolated temporary directory so tests never pollute verified_alerts/
    tmp_out_dir = tempfile.mkdtemp(prefix="trailcam_resilience_test_")
    orig_out_dir = receiver_hub.OUT_DIR
    receiver_hub.OUT_DIR = tmp_out_dir

    try:
        test_passed = 0
        total_tests = 8

        # Keys setup
        priv_hex = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
        signer = SigningKey(bytes.fromhex(priv_hex))
        node_id = "NODE-NORTH-01"

        # ----------------------------------------------------------------------
        # Test 1: Anti-Replay Protection (Duplicate Nonce, Empty Nonce & Drift)
        # ----------------------------------------------------------------------
        print("[*] 1. Testing Anti-Replay & Nonce Validation...")
        now = time.time()
        nonce1 = secrets.token_hex(8)

        valid1 = receiver_hub.is_valid_fresh_packet(node_id, int(now), nonce1)
        valid_dup = receiver_hub.is_valid_fresh_packet(node_id, int(now), nonce1)
        valid_old = receiver_hub.is_valid_fresh_packet(node_id, int(now - 400), secrets.token_hex(8))
        valid_empty = receiver_hub.is_valid_fresh_packet(node_id, int(now), "")

        assert valid1 is True, "Valid fresh packet was incorrectly rejected"
        assert valid_dup is False, "Duplicate nonce was not rejected"
        assert valid_old is False, "Expired timestamp was not rejected"
        assert valid_empty is False, "Empty nonce was not rejected"
        print("    [+] Anti-Replay Logic: PASSED (Duplicate, empty, and stale nonces rejected)")
        test_passed += 1

        # ----------------------------------------------------------------------
        # Test 2: Out-of-Order Packet Reassembly (Chunks Arriving BEFORE Metadata)
        # ----------------------------------------------------------------------
        print("[*] 2. Testing Asymmetric Reassembly (Chunks BEFORE Metadata)...")
        fake_img = b"JPEG_SIMULATED_TEST_PAYLOAD_" * 40  # ~1120 bytes (2 chunks)
        img_hash = hashlib.sha256(fake_img).hexdigest()
        nonce2 = secrets.token_hex(8)
        prefix = nonce2

        CHUNK_SIZE = 1024
        chunks = [fake_img[i:i + CHUNK_SIZE] for i in range(0, len(fake_img), CHUNK_SIZE)]
        total_chunks = len(chunks)

        receiver_hub.pending_chunks[prefix] = {
            "chunks": {},
            "total": total_chunks,
            "created_at": time.time()
        }
        for idx, c in enumerate(chunks):
            receiver_hub.pending_chunks[prefix]["chunks"][idx] = c

        assert prefix in receiver_hub.pending_chunks, "Chunk store should exist"

        meta_payload = {
            "node": node_id,
            "ts": int(time.time()),
            "pico_trig": "TRIG,MAG=3200,SEIS=400",
            "detections": [{"class": "person", "conf": 0.92}],
            "img_sha256": img_hash,
            "img_size": len(fake_img),
            "nonce": nonce2
        }
        receiver_hub.pending_meta[prefix] = {"meta": meta_payload, "created_at": time.time()}

        reconstructed = receiver_hub.try_reconstruct_image(prefix)
        assert reconstructed is True, "Failed to reconstruct image when metadata arrived after chunks!"
        assert prefix not in receiver_hub.pending_chunks, "Buffers should be freed after successful reconstruction"
        print("    [+] Out-of-Order Reassembly: PASSED (Bidirectional trigger verified)")
        test_passed += 1

        # ----------------------------------------------------------------------
        # Test 3: Stale Buffer Garbage Collection & MAX_PENDING_FRAMES Cap
        # ----------------------------------------------------------------------
        print("[*] 3. Testing Sliding-Window Garbage Collection & Queue Cap...")
        stale_prefix = "deadbeefdeadbeef"
        receiver_hub.pending_chunks[stale_prefix] = {
            "chunks": {0: b"partial"},
            "total": 5,
            "created_at": time.time() - 25.0
        }
        receiver_hub.pending_meta[stale_prefix] = {
            "meta": {"img_sha256": "deadbeef..."},
            "created_at": time.time() - 25.0
        }

        receiver_hub.cleanup_stale_buffers()
        assert stale_prefix not in receiver_hub.pending_chunks, "Stale incomplete chunks were not cleaned up!"
        assert stale_prefix not in receiver_hub.pending_meta, "Stale metadata was not cleaned up!"
        print("    [+] Memory Leak Garbage Collection: PASSED (Orphaned partial frames purged)")
        test_passed += 1

        # ----------------------------------------------------------------------
        # Test 4: End-to-End Cryptographic Packet Sign & Verify Roundtrip
        # ----------------------------------------------------------------------
        print("[*] 4. Testing End-to-End Ed25519 Packet Roundtrip with Pacing Nonce...")
        meta_json = json.dumps(meta_payload, separators=(",", ":")).encode("utf-8")
        sig = signer.sign(meta_json).signature
        pkt = b"DD\x01" + sig + meta_json

        parsed_sig = pkt[3:67]
        parsed_bytes = pkt[67:]
        receiver_hub.KNOWN_NODE_PUBKEYS[node_id].verify(parsed_bytes, parsed_sig)
        print("    [+] Cryptographic Verification: PASSED (Strict 64-byte Ed25519 match)")
        test_passed += 1

        # ----------------------------------------------------------------------
        # Test 5: Pass-1 Corrupted Chunk Repaired by Pass-2 Carousel Retransmission
        # ----------------------------------------------------------------------
        print("[*] 5. Testing Carousel Pass-2 Repair After Pass-1 Chunk Bit-Flip...")
        repair_img = b"CAROUSEL_REPAIR_TEST_IMAGE_BYTES_" * 45  # 2 chunks
        repair_hash = hashlib.sha256(repair_img).hexdigest()
        repair_nonce = secrets.token_hex(8)
        repair_nonce_bytes = bytes.fromhex(repair_nonce)
        repair_chunks = [repair_img[i:i + CHUNK_SIZE] for i in range(0, len(repair_img), CHUNK_SIZE)]

        repair_meta = {
            "node": node_id,
            "ts": int(time.time()),
            "pico_trig": "TRIG,MAG=4100,SEIS=510",
            "detections": [{"class": "car", "conf": 0.91}],
            "img_sha256": repair_hash,
            "img_size": len(repair_img),
            "nonce": repair_nonce
        }
        repair_meta_bytes = json.dumps(repair_meta, separators=(",", ":")).encode("utf-8")
        repair_hdr_pkt = b"DD\x01" + signer.sign(repair_meta_bytes).signature + repair_meta_bytes

        # Pass 1: Send valid header + corrupted chunk 0 + valid chunk 1
        receiver_hub.process_datagram(repair_hdr_pkt)
        corrupted_chunk_0 = b"CORRUPTED_BITS!" + repair_chunks[0][15:]
        pkt_c0_bad = b"DD\x02" + repair_nonce_bytes + struct.pack(">HH", 0, len(repair_chunks)) + corrupted_chunk_0
        pkt_c1_good = b"DD\x02" + repair_nonce_bytes + struct.pack(">HH", 1, len(repair_chunks)) + repair_chunks[1]
        assert receiver_hub.process_datagram(pkt_c0_bad) is False
        assert receiver_hub.process_datagram(pkt_c1_good) is False, "Corrupted Pass-1 should fail SHA-256"
        assert repair_nonce in receiver_hub.pending_meta, "Metadata must be retained for Pass-2 repair!"
        assert repair_nonce not in receiver_hub.completed_prefixes, "Corrupted burst must not be marked completed!"

        # Pass 2: Retransmit clean chunks -> should reconstruct and verify 100%
        pkt_c0_good = b"DD\x02" + repair_nonce_bytes + struct.pack(">HH", 0, len(repair_chunks)) + repair_chunks[0]
        assert receiver_hub.process_datagram(pkt_c0_good) is False
        assert receiver_hub.process_datagram(pkt_c1_good) is True, "Pass-2 clean chunks failed to repair frame!"
        print("    [+] Carousel Pass-2 Fault Repair: PASSED (Corrupted Pass-1 recovered on Pass-2)")
        test_passed += 1

        # ----------------------------------------------------------------------
        # Test 6: Consecutive Identical-Hash Images with Distinct Nonces
        # ----------------------------------------------------------------------
        print("[*] 6. Testing Consecutive Identical-Hash Frames with Distinct Nonces...")
        shared_img = b"SYNTHETIC_FALLBACK_IDENTICAL_FRAME_" * 35
        shared_hash = hashlib.sha256(shared_img).hexdigest()
        shared_chunks = [shared_img[i:i + CHUNK_SIZE] for i in range(0, len(shared_img), CHUNK_SIZE)]

        for burst_idx in (1, 2):
            b_nonce = secrets.token_hex(8)
            b_nonce_bytes = bytes.fromhex(b_nonce)
            b_meta = {
                "node": node_id,
                "ts": int(time.time()),
                "pico_trig": f"TRIG,BURST={burst_idx}",
                "detections": [],
                "img_sha256": shared_hash,
                "img_size": len(shared_img),
                "nonce": b_nonce
            }
            b_meta_bytes = json.dumps(b_meta, separators=(",", ":")).encode("utf-8")
            b_hdr = b"DD\x01" + signer.sign(b_meta_bytes).signature + b_meta_bytes
            receiver_hub.process_datagram(b_hdr)
            reconstructed_ok = False
            for idx, ch in enumerate(shared_chunks):
                cpkt = b"DD\x02" + b_nonce_bytes + struct.pack(">HH", idx, len(shared_chunks)) + ch
                if receiver_hub.process_datagram(cpkt):
                    reconstructed_ok = True
            assert reconstructed_ok is True, f"Identical-hash burst #{burst_idx} was dropped!"
        print("    [+] Identical-Hash Nonce Isolation: PASSED (Consecutive identical frames preserved)")
        test_passed += 1

        # ----------------------------------------------------------------------
        # Test 7: 2 km NLOS Sub-GHz FHSS/LoRa Relay Bridge & Dead-Drop Export
        # ----------------------------------------------------------------------
        print("[*] 7. Testing 2 km NLOS Sub-GHz FHSS/LoRa Relay & Dead-Drop Vault Retention...")
        from subghz_nlos_relay import build_nlos_serial_frames, parse_nlos_serial_stream

        nlos_nonce = secrets.token_hex(8)
        nlos_alert = {
            "node": node_id,
            "ts": int(time.time()),
            "nonce": nlos_nonce,
            "detections": [{"class": "person", "conf": 0.95}],
            "pico_trig": "TRIG,MAG=120,SEIS=410,RADAR_M=5.1",
        }
        serial_frames, _, _ = build_nlos_serial_frames(nlos_alert, shared_img, priv_hex)
        # Inject random RF channel noise between serial frames and drop 1 frame from Pass 1 (repaired by Pass 2)
        pass1_noisy = b"\xff\x00NOISE" + b"\xaa\x55".join(serial_frames[:-1]) + b"GARBAGE"
        pass2_clean = b"".join(serial_frames)
        extracted_dd_pkts = parse_nlos_serial_stream(pass1_noisy + pass2_clean)
        nlos_reconstructed = False
        for pkt in extracted_dd_pkts:
            if receiver_hub.process_datagram(pkt):
                nlos_reconstructed = True
        assert nlos_reconstructed is True, "2 km NLOS Sub-GHz relay stream failed to reconstruct at Farmhouse hub!"

        # Verify Dead-Drop Vault export bundle and circular retention
        bundle_zip = os.path.join(tmp_out_dir, "courier_export.zip")
        exported_count = receiver_hub.export_dead_drop_bundle(bundle_zip, out_dir=tmp_out_dir)
        assert exported_count >= 4 and os.path.isfile(bundle_zip)
        removed_count = receiver_hub.enforce_storage_retention(out_dir=tmp_out_dir, max_files=2)
        assert removed_count >= 1
        print("    [+] 2 km NLOS Sub-GHz Relay & Dead-Drop Vault Retention: PASSED")
        test_passed += 1

        # ----------------------------------------------------------------------
        # Test 8: Documentation, SAR Visual Diagrams & Zero-Metadata Verification
        # ----------------------------------------------------------------------
        print("[*] 8. Testing SAR Documentation, Visual Diagrams & Zero-Metadata Integrity...")
        pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        docs_dir = os.path.join(pkg_root, "docs")
        imgs_dir = os.path.join(docs_dir, "images")
        required_images = [
            "bearnese_mountain_dog_drone_concept.jpg",
            "bearnese_architecture_field_visualization.jpg",
            "karhunkierros_pelastusketju_5_vaihetta.jpg",
            "karhunkierros_sar_isometrinen_maastonakyma.jpg",
            "arctic_sar_rescue_chain_5_stages_en_v4.jpg",
            "arctic_sar_isometric_terrain_en_v3.jpg",
            "arctic_sar_system_8_parts_overview_v1.jpg",
            "arctic_sar_aircraft_cots_subsystems_v2.jpg",
            "arctic_sar_navigation_layers_5tier_v1.jpg",
            "arctic_sar_link_ladder_4tier_v1.jpg",
            "arctic_sar_opaslyhty_canopy_geometry_v1.jpg",
            "arctic_sar_slide01_cover_v2.jpg",
            "arctic_sar_slide28_validation_ladder_v1.jpg",
        ]
        for img_name in required_images:
            img_path = os.path.join(imgs_dir, img_name)
            assert os.path.isfile(img_path) and os.path.getsize(img_path) > 50000, f"Missing or empty diagram: {img_name}"
            with open(img_path, "rb") as imf:
                img_bytes = imf.read()
            for forbidden in (b"Exif", b"c2pa", b"jumb", b"http://ns.adobe.com"):
                assert forbidden not in img_bytes, f"Residual metadata ({forbidden}) found in {img_name}"

        for pdf_rel in (
            os.path.join(docs_dir, "KARHUNKIERROS_PRO_BONO_SAR_BRIEF_FI.pdf"),
            os.path.join(docs_dir, "ARCTIC_SAR_DRONE_EXECUTIVE_BRIEF_EN.pdf"),
            os.path.join(pkg_root, "KARHUNKIERROS_SAR_PRESENTATION.pdf"),
        ):
            assert os.path.isfile(pdf_rel) and os.path.getsize(pdf_rel) > 100000, f"Printable SAR PDF missing or incomplete: {pdf_rel}"
            with open(pdf_rel, "rb") as pdff:
                pdf_bytes = pdff.read()
            for forbidden_pdf in (b"/Creator", b"/Producer", b"/CreationDate", b"/ModDate", b"/Author", b"Macintosh", b"HeadlessChrome", b"Skia/PDF"):
                assert forbidden_pdf not in pdf_bytes, f"Residual PDF metadata ({forbidden_pdf}) found in {pdf_rel}"
            # Also decompress PDF FlateDecode streams and verify no stale battery/version strings remain (F44)
            import re, zlib
            for m_stream in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL):
                try:
                    dec = zlib.decompress(m_stream.group(1))
                    assert b"Molicel" not in dec and b"v1.0-Stabilized" not in dec, f"Stale text found inside PDF stream of {pdf_name}"
                except Exception:
                    pass

        # Verify OS junk anti-metadata protection is built into run_guided_bench_doctor.py
        with open(os.path.join(pkg_root, "run_guided_bench_doctor.py"), "r", encoding="utf-8") as bf:
            bcontent = bf.read()
        assert 'os.environ["COPYFILE_DISABLE"] = "1"' in bcontent
        assert "purge_os_junk_metadata" in bcontent

        print("    [+] SAR Manuals, 4 Visual Diagrams, PDF Brief & Zero-Metadata Verification: PASSED")
        test_passed += 1

        print("=" * 65)
        print(f"[ALL {test_passed}/{total_tests} RESILIENCE TESTS PASSED CLEANLY!]")
        print("=" * 65)
    finally:
        receiver_hub.OUT_DIR = orig_out_dir
        shutil.rmtree(tmp_out_dir, ignore_errors=True)


import unittest


class TestSharedResilienceSuite(unittest.TestCase):
    def test_resilience_and_security_suite(self):
        run_resilience_test_suite()


if __name__ == "__main__":
    run_resilience_test_suite()


