#!/usr/bin/env python3
# File: collector_hub/receiver_hub.py
# Description: Production-Hardened Passive UDP Optical Diode Receiver & Cryptographic Reassembler
# License: MIT
import os
import sys
import time
import json
import socket
import struct
import hashlib
import errno
import argparse
import subprocess
from collections import OrderedDict
try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
except ModuleNotFoundError:
    if __name__ == "__main__":
        _venv_py = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".venv", "bin", "python3")
        if os.path.isfile(_venv_py) and os.path.realpath(sys.executable) != os.path.realpath(_venv_py):
            os.execv(_venv_py, [_venv_py, "-B"] + sys.argv)
    raise

import base64

# ==============================================================================
# Configuration & Security Parameters
# ==============================================================================
UDP_PORT = int(os.getenv("UDP_PORT", "5514"))
OUT_DIR = os.getenv("OUT_DIR", "./verified_alerts")
CHUNK_TTL_SECONDS = 15.0     # Maximum time to hold partial frames in memory
MAX_CLOCK_SKEW_SEC = int(os.getenv("MAX_CLOCK_SKEW_SEC", "300"))  # Max clock drift threshold
STRICT_CLOCK_SKEW = os.getenv("STRICT_CLOCK_SKEW", "0") == "1"    # Drop vs warn on off-grid clock skew
MAX_CHUNKS_PER_FRAME = 1024  # Cap at 1 MB per image to prevent memory DoS
MAX_PENDING_FRAMES = 64      # Hard cap on concurrent partial frames in memory
MAX_DATAGRAM_BYTES = 65535   # Full UDP datagram capacity so multi-detection headers are never truncated
MAX_SAVED_ALERTS = int(os.getenv("MAX_SAVED_ALERTS", "0"))  # 0 = unlimited; >0 = circular cap for buried dead-drop vaults

# Map of authorized camera Node IDs to their 32-byte Ed25519 Public Keys
DEFAULT_EXAMPLE_PUBKEY_HEX = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
DEFAULT_EXAMPLE_PUBKEYS = {
    DEFAULT_EXAMPLE_PUBKEY_HEX,
}

KNOWN_NODE_PUBKEYS = {
    "NODE-NORTH-01": VerifyKey(bytes.fromhex(DEFAULT_EXAMPLE_PUBKEY_HEX)),
}

# ==============================================================================
# Replay Tracking & Buffer State
# ==============================================================================
# node_id -> {"last_ts": int, "seen_nonces": OrderedDict(nonce -> ts)}
node_security_state = {}

# prefix (16-char hex nonce) -> {"meta": dict, "raw_meta_bytes": bytes, "sig_hex": str, "pubkey_hex": str, "created_at": float}
pending_meta = {}

# prefix (16-char hex nonce) -> {"chunks": dict(int -> bytes), "total": int, "created_at": float}
pending_chunks = {}

# prefix -> {"nonce": str, "completed_at": float} (tracks durably committed carousel bursts)
completed_prefixes = OrderedDict()


def load_authorized_nodes(out_dir=None, allow_example_keys=None):
    """
    Loads provisioned node public keys from authorized_nodes.json.
    - When authorized_nodes.json exists, clears the default example key first so
      provisioning any real camera node immediately removes trust in the public example key.
    - When ALLOW_EXAMPLE_KEYS=0 (or allow_example_keys=False), strips all example keys and
      fails closed if no real node public keys are configured.
    """
    target_dir = out_dir or OUT_DIR
    if allow_example_keys is None:
        allow_example = os.getenv("ALLOW_EXAMPLE_KEYS", "1") != "0"
    else:
        allow_example = bool(allow_example_keys)

    reg_file = os.getenv("AUTHORIZED_NODES_FILE", os.path.join(target_dir, "authorized_nodes.json"))
    if os.path.isfile(reg_file):
        try:
            with open(reg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("authorized_nodes.json root must be a JSON object mapping node_id -> pubkey_hex")
        except Exception as e:
            print(f"[!] Fatal error loading {reg_file}: {e}", file=sys.stderr)
            raise RuntimeError(f"Invalid authorized_nodes.json ({reg_file}): {e}") from e

        # Clear pre-populated example identity before loading provisioned registry
        KNOWN_NODE_PUBKEYS.clear()
        for nid, pub_hex in data.items():
            if not isinstance(pub_hex, str) or len(pub_hex) != 64:
                raise RuntimeError(f"Invalid 64-char hex public key for node '{nid}' in {reg_file}")
            if not allow_example and pub_hex.lower() in DEFAULT_EXAMPLE_PUBKEYS:
                raise RuntimeError(f"Example public key for node '{nid}' is forbidden when ALLOW_EXAMPLE_KEYS=0")
            KNOWN_NODE_PUBKEYS[nid] = VerifyKey(bytes.fromhex(pub_hex))

        if not KNOWN_NODE_PUBKEYS:
            raise RuntimeError(f"No valid node keys found in {reg_file}")
    else:
        if not allow_example:
            # Remove any default example keys and fail closed if nothing remains
            to_del = [
                nid for nid, vk in KNOWN_NODE_PUBKEYS.items()
                if vk.encode().hex().lower() in DEFAULT_EXAMPLE_PUBKEYS
            ]
            for nid in to_del:
                del KNOWN_NODE_PUBKEYS[nid]
            if not KNOWN_NODE_PUBKEYS:
                raise RuntimeError(
                    f"Refusing to start collector without {reg_file} while ALLOW_EXAMPLE_KEYS=0."
                )


def load_seen_nonces_from_disk(out_dir=None):
    """
    Loads all persisted (node_id, nonce, ts) records from disk so anti-replay survives restarts
    without evicting older nonces after 500 alerts.
    """
    target_dir = out_dir or OUT_DIR
    cache_path = os.path.join(target_dir, "seen_nonces.jsonl")
    if not os.path.isfile(cache_path):
        return
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    nid = rec.get("node")
                    nonce = rec.get("nonce")
                    ts = int(rec.get("ts", 0))
                    if nid and nonce:
                        if nid not in node_security_state:
                            node_security_state[nid] = {"last_ts": ts, "seen_nonces": OrderedDict()}
                        seen = node_security_state[nid]["seen_nonces"]
                        seen[nonce] = ts
                        node_security_state[nid]["last_ts"] = max(node_security_state[nid]["last_ts"], ts)
                except Exception:
                    pass
    except Exception:
        pass


def _persist_seen_nonce(node_id, nonce, ts, out_dir=None):
    """Durably appends a verified nonce to disk cache in OUT_DIR (raises OSError on disk failure)."""
    target_dir = out_dir or OUT_DIR
    cache_path = os.path.join(target_dir, "seen_nonces.jsonl")
    os.makedirs(target_dir, exist_ok=True)
    with open(cache_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"node": node_id, "nonce": nonce, "ts": int(ts)}) + "\n")
        f.flush()
        os.fsync(f.fileno())


def commit_seen_nonce(node_id, ts, nonce, out_dir=None):
    """Commits a verified alert nonce to both persistent disk log and in-memory anti-replay set."""
    _persist_seen_nonce(node_id, nonce, ts, out_dir=out_dir)
    if node_id not in node_security_state:
        node_security_state[node_id] = {"last_ts": int(ts), "seen_nonces": OrderedDict()}
    state = node_security_state[node_id]
    state["seen_nonces"][nonce] = int(ts)
    state["last_ts"] = max(state["last_ts"], int(ts))


def write_receiver_heartbeat(port=UDP_PORT, out_dir=None):
    """Writes a lightweight heartbeat file so dashboard_server.py can verify receiver liveness."""
    target_dir = out_dir or OUT_DIR
    hb_path = os.path.join(target_dir, "receiver_heartbeat.json")
    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(hb_path, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "port": port, "updated_at": time.time()}, f)
    except OSError:
        pass


def cleanup_stale_buffers():
    """Sliding-window garbage collector to prevent memory leaks from dropped packets or orphaned metadata."""
    now = time.time()
    stale_chunk_prefixes = [
        p for p, data in pending_chunks.items()
        if now - data["created_at"] > CHUNK_TTL_SECONDS
    ]
    for p in stale_chunk_prefixes:
        del pending_chunks[p]
        if p in pending_meta:
            del pending_meta[p]

    stale_meta_prefixes = [
        p for p, data in pending_meta.items()
        if now - data["created_at"] > CHUNK_TTL_SECONDS
    ]
    for p in stale_meta_prefixes:
        del pending_meta[p]

    stale_completed = [
        p for p, data in completed_prefixes.items()
        if now - data["completed_at"] > CHUNK_TTL_SECONDS
    ]
    for p in stale_completed:
        del completed_prefixes[p]


def _enforce_queue_cap(store_dict, max_entries=MAX_PENDING_FRAMES):
    """Evicts oldest entries if store_dict is still at capacity after stale cleanup."""
    if len(store_dict) >= max_entries:
        cleanup_stale_buffers()
    while len(store_dict) >= max_entries and store_dict:
        oldest_key = min(store_dict, key=lambda k: store_dict[k].get("created_at", 0.0))
        del store_dict[oldest_key]


def _atomic_write_bytes(target_path, data_bytes):
    """Writes bytes to a temporary sibling file, fsyncs, and atomically replaces target_path."""
    parent = os.path.dirname(os.path.abspath(target_path))
    os.makedirs(parent, exist_ok=True)
    tmp_path = f"{target_path}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "wb") as f:
            f.write(data_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def _journal_contains_nonce(journal_path, node_id, nonce_val):
    """Checks whether alerts_journal.jsonl already has a committed row for (node_id, nonce_val)."""
    if not nonce_val or not os.path.isfile(journal_path):
        return False
    try:
        with open(journal_path, "r", encoding="utf-8") as jf:
            for line in jf:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("node") == node_id and rec.get("nonce") == nonce_val:
                        return True
                except Exception:
                    continue
    except OSError:
        return False
    return False


def try_reconstruct_image(prefix):
    """
    Reconstructs JPEG frame, verifies SHA-256 integrity, and durably commits:
      1. Atomic JPEG file (<node>_<ts>_<nonce8>.jpg)
      2. Atomic detached signature envelope (<node>_<ts>_<nonce8>.sig.json)
      3. Flushed & fsynced journal entry (alerts_journal.jsonl, deduplicated by nonce on retry)
      4. Flushed & fsynced replay nonce record (seen_nonces.jsonl)
    If ANY disk write fails (e.g. ENOSPC full disk), retains pending_meta and pending_chunks
    and does NOT mark the event completed or burn the nonce, allowing subsequent carousel
    passes or retries to complete once storage recovers.
    """
    if prefix not in pending_meta or prefix not in pending_chunks:
        return False

    try:
        meta_entry = pending_meta[prefix]
        meta = meta_entry["meta"]
        if not isinstance(meta, dict):
            raise TypeError("meta must be a dict")
        raw_meta_bytes = meta_entry.get("raw_meta_bytes")
        sig_hex = str(meta_entry.get("sig_hex", ""))
        pubkey_hex = str(meta_entry.get("pubkey_hex", ""))
        if raw_meta_bytes is None:
            raw_meta_bytes = json.dumps(meta, separators=(",", ":")).encode("utf-8")

        chunk_store = pending_chunks[prefix]
        total = int(chunk_store["total"])
        node_id = str(meta.get("node", "UNKNOWN"))
        ts = int(meta.get("ts", int(time.time())))
        nonce_val = str(meta.get("nonce", prefix))
        dets = meta.get("detections", [])
        if not isinstance(dets, list):
            dets = []
        total_dets = int(meta.get("total_detections", len(dets)))
    except (ValueError, TypeError, KeyError) as e:
        print(f"    [!] Malformed metadata in try_reconstruct_image for {prefix}: {e}", file=sys.stderr)
        pending_meta.pop(prefix, None)
        pending_chunks.pop(prefix, None)
        return False

    if total == 0:
        try:
            commit_seen_nonce(node_id, ts, nonce_val, out_dir=OUT_DIR)
        except OSError as e:
            print(f"    [!] Storage error persisting nonce for {prefix}: {e}", file=sys.stderr)
            return False
        completed_prefixes[prefix] = {"nonce": nonce_val, "completed_at": time.time()}
        del pending_meta[prefix]
        del pending_chunks[prefix]
        return True

    if len(chunk_store["chunks"]) == total and all(i in chunk_store["chunks"] for i in range(total)):
        full_img = b"".join(chunk_store["chunks"][i] for i in range(total))
        computed_sha256 = hashlib.sha256(full_img).hexdigest()

        if computed_sha256 == meta.get("img_sha256"):
            base_stem = f"{node_id}_{ts}_{nonce_val[:8]}"
            rel_name = f"{base_stem}.jpg"
            sig_rel_name = f"{base_stem}.sig.json"
            fname = os.path.join(OUT_DIR, rel_name)
            sig_fname = os.path.join(OUT_DIR, sig_rel_name)
            journal_path = os.path.join(OUT_DIR, "alerts_journal.jsonl")

            signed_payload_b64 = base64.b64encode(raw_meta_bytes).decode("ascii")
            sig_envelope = {
                "node": node_id,
                "timestamp": ts,
                "nonce": nonce_val,
                "image_file": rel_name,
                "image_sha256": computed_sha256,
                "image_bytes": len(full_img),
                "pubkey_hex": pubkey_hex,
                "signature_hex": sig_hex,
                "signed_payload_b64": signed_payload_b64,
            }

            alert_entry = {
                "timestamp": ts,
                "received_at": int(time.time()),
                "node": node_id,
                "nonce": nonce_val,
                "image_file": f"./verified_alerts/{rel_name}",
                "sig_file": f"./verified_alerts/{sig_rel_name}",
                "image_bytes": len(full_img),
                "image_sha256": computed_sha256,
                "detections": dets,
                "subject_kinematics": meta.get("subject_kinematics"),
                "total_detections": total_dets,
                "detections_truncated": bool(meta.get("detections_truncated", False)),
                "pico_trig": meta.get("pico_trig", ""),
                "camera_ok": meta.get("camera_ok", True),
                "inference_backend": meta.get("inference_backend", "unknown"),
                "clock_drift_warning": bool(meta.get("_clock_drift_warning", False)),
                "pubkey_hex": pubkey_hex,
                "signature_hex": sig_hex,
                "signed_payload_b64": signed_payload_b64,
                "verified": True,
            }

            try:
                os.makedirs(OUT_DIR, exist_ok=True)
                _atomic_write_bytes(fname, full_img)
                _atomic_write_bytes(sig_fname, (json.dumps(sig_envelope, indent=2) + "\n").encode("utf-8"))
                if not _journal_contains_nonce(journal_path, node_id, nonce_val):
                    with open(journal_path, "a", encoding="utf-8") as jf:
                        jf.write(json.dumps(alert_entry) + "\n")
                        jf.flush()
                        os.fsync(jf.fileno())
                commit_seen_nonce(node_id, ts, nonce_val, out_dir=OUT_DIR)
                print(f"    [+] Image verified ({len(full_img)} bytes) -> Saved to {fname}")
            except OSError as e:
                print(
                    f"    [!] Storage error committing verified alert {prefix} ({fname}): {e}. "
                    f"Retaining pending buffers for retry.",
                    file=sys.stderr,
                )
                return False

            # Optional circular disk retention cap for unattended buried Dead-Drop Collector Vaults
            if MAX_SAVED_ALERTS and MAX_SAVED_ALERTS > 0:
                enforce_storage_retention(OUT_DIR, MAX_SAVED_ALERTS)

            # Optional external dispatch hook (e.g. Telegram / Signal / Home Assistant / Decoupled Relay)
            hook_script = os.getenv("ALERT_HOOK_SCRIPT")
            if hook_script and os.path.exists(hook_script):
                try:
                    subprocess.Popen([hook_script, fname, json.dumps(alert_entry)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as e:
                    print(f"    [!] Alert hook error: {e}", file=sys.stderr)

            completed_prefixes[prefix] = {"nonce": nonce_val, "completed_at": time.time()}
            if len(completed_prefixes) > 256:
                completed_prefixes.popitem(last=False)
            del pending_meta[prefix]
            del pending_chunks[prefix]
            return True
        else:
            # Do NOT mark completed or delete pending_meta: clear corrupted chunks
            # so redundant Pass 2 / Pass 3 carousel packets can repair the frame!
            print(
                f"    [!] SHA-256 mismatch for {prefix} on current pass! "
                f"Retaining metadata and clearing chunks for next carousel pass repair.",
                file=sys.stderr
            )
            chunk_store["chunks"].clear()
            return False

    return False


def is_valid_fresh_packet(node_id, ts, nonce, strict_clock_skew=True, commit=True):
    """
    Enforces strict anti-replay protection, non-empty 16-char hex nonce validation,
    persistent disk nonce caching (with zero FIFO eviction), and configurable clock-skew handling.
    When commit=False (used during packet ingress before image reconstruction), validates
    freshness without prematurely burning the nonce before the alert is durably written to disk.
    """
    if not nonce or not isinstance(nonce, str) or len(nonce) != 16:
        print(f"[!] Replay/Format rejection: Missing or invalid 16-char hex nonce from {node_id}", file=sys.stderr)
        return False
    try:
        bytes.fromhex(nonce)
    except ValueError:
        print(f"[!] Replay/Format rejection: Non-hex nonce '{nonce}' from {node_id}", file=sys.stderr)
        return False

    now = time.time()
    if abs(now - ts) > MAX_CLOCK_SKEW_SEC:
        if strict_clock_skew:
            print(f"[!] Replay/ClockSkew rejection: Alert ts {ts} exceeds {MAX_CLOCK_SKEW_SEC}s drift", file=sys.stderr)
            return False
        else:
            print(
                f"[*] Notice: Cold-boot clock skew ({int(now - ts)}s) on {node_id}; "
                f"accepting based on cryptographic signature + unique nonce {nonce}.",
                file=sys.stderr
            )

    if node_id not in node_security_state:
        node_security_state[node_id] = {"last_ts": ts, "seen_nonces": OrderedDict()}

    state = node_security_state[node_id]
    seen = state["seen_nonces"]
    if nonce in seen:
        print(f"[!] Replay rejection: Duplicate nonce {nonce} detected for {node_id}!", file=sys.stderr)
        return False

    if commit:
        try:
            commit_seen_nonce(node_id, ts, nonce, out_dir=OUT_DIR)
        except OSError as e:
            print(f"[!] Storage error persisting nonce {nonce}: {e}", file=sys.stderr)
            return False
    return True


MAX_CHUNK_BYTES = 1024  # Hard cap on single Type 0x02 image chunk payload bytes


def process_datagram(pkt, now=None, strict_clock_skew=None):
    """Processes a single raw UDP datagram (Type 0x01 Metadata or Type 0x02 Image Chunk)."""
    if now is None:
        now = time.time()
    if strict_clock_skew is None:
        strict_clock_skew = STRICT_CLOCK_SKEW

    # Validate Diode sync preamble 'DD'
    if len(pkt) < 4 or pkt[:2] != b"DD":
        return False

    pkt_type = pkt[2]

    # ----------------------------------------------------------------------
    # Type 0x01: Signed Metadata Packet (Ed25519)
    # ----------------------------------------------------------------------
    if pkt_type == 1 and len(pkt) > 67:
        sig = pkt[3:67]
        meta_bytes = pkt[67:]
        try:
            meta = json.loads(meta_bytes.decode("utf-8"))
            if not isinstance(meta, dict):
                return False
            node_id = meta.get("node")
            if node_id not in KNOWN_NODE_PUBKEYS:
                print(f"[!] Rejected alert from unauthorized node: {node_id}", file=sys.stderr)
                return False

            vk = KNOWN_NODE_PUBKEYS[node_id]
            pubkey_hex = vk.encode().hex()
            if os.getenv("ALLOW_EXAMPLE_KEYS", "1") == "0" and pubkey_hex.lower() in DEFAULT_EXAMPLE_PUBKEYS:
                print(f"[!] Rejected example key for node {node_id} (ALLOW_EXAMPLE_KEYS=0)", file=sys.stderr)
                return False

            # Verify Ed25519 cryptographic signature over exact JSON bytes
            vk.verify(meta_bytes, sig)

            nonce = meta.get("nonce", "")
            img_prefix = str(meta.get("img_sha256", ""))[:16]
            # Primary correlation key is the 8-byte (16 hex char) per-burst nonce
            prefix = nonce if (isinstance(nonce, str) and len(nonce) == 16) else img_prefix

            # Deduplicate redundant Pass 2 / Pass 3 header packets from the same 3x carousel burst
            if prefix in pending_meta and pending_meta[prefix]["meta"].get("nonce") == nonce:
                try_reconstruct_image(prefix)
                return True
            if prefix in completed_prefixes and completed_prefixes[prefix].get("nonce") == nonce:
                return True

            # Anti-replay check for genuinely new alert bursts (commit=False until durable image+journal write)
            ts = int(meta.get("ts", int(now)))
            if abs(now - ts) > MAX_CLOCK_SKEW_SEC:
                meta["_clock_drift_warning"] = True
            if not is_valid_fresh_packet(node_id, ts, nonce, strict_clock_skew=strict_clock_skew, commit=False):
                return False

            if prefix and prefix not in pending_meta:
                _enforce_queue_cap(pending_meta, MAX_PENDING_FRAMES)
                pending_meta[prefix] = {
                    "meta": meta,
                    "raw_meta_bytes": meta_bytes,
                    "sig_hex": sig.hex(),
                    "pubkey_hex": pubkey_hex,
                    "created_at": now,
                }
                print(f"[+] VERIFIED ALERT from [{node_id}] | Detections: {meta.get('detections')} | Trigger: {meta.get('pico_trig')}")
                # Trigger reconstruction in case chunks arrived before this metadata packet
                try_reconstruct_image(prefix)
                return True

        except (BadSignatureError, Exception) as e:
            print(f"[!] Dropped corrupted or forged packet: {e}", file=sys.stderr)
            return False

    # ----------------------------------------------------------------------
    # Type 0x02: Image Binary Chunk Packet
    # ----------------------------------------------------------------------
    elif pkt_type == 2 and len(pkt) > 15:
        prefix = pkt[3:11].hex()
        # Ignore redundant Pass 2 / Pass 3 chunks for already-committed bursts
        if prefix in completed_prefixes:
            return True

        idx, total = struct.unpack(">HH", pkt[11:15])
        if total == 0 or total > MAX_CHUNKS_PER_FRAME or idx >= total:
            return False

        chunk_data = pkt[15:]
        if len(chunk_data) == 0 or len(chunk_data) > MAX_CHUNK_BYTES:
            return False

        if prefix not in pending_chunks:
            _enforce_queue_cap(pending_chunks, MAX_PENDING_FRAMES)
            pending_chunks[prefix] = {
                "chunks": {},
                "total": total,
                "created_at": now
            }

        pending_chunks[prefix]["chunks"][idx] = chunk_data
        pending_chunks[prefix]["total"] = total

        # Trigger reconstruction if all chunks and metadata are assembled
        return try_reconstruct_image(prefix)

    return False


# ==============================================================================
def run_hub(port=UDP_PORT, bind_addr="0.0.0.0", out_dir=OUT_DIR, max_clock_skew=MAX_CLOCK_SKEW_SEC, strict_clock_skew=STRICT_CLOCK_SKEW):
    global OUT_DIR, UDP_PORT, MAX_CLOCK_SKEW_SEC, STRICT_CLOCK_SKEW
    OUT_DIR = out_dir
    UDP_PORT = port
    MAX_CLOCK_SKEW_SEC = max_clock_skew
    STRICT_CLOCK_SKEW = strict_clock_skew
    os.makedirs(OUT_DIR, exist_ok=True)
    load_authorized_nodes(OUT_DIR)
    load_seen_nonces_from_disk(OUT_DIR)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass

    try:
        sock.bind((bind_addr, port))
    except OSError as e:
        if e.errno in (errno.EADDRINUSE, 48):
            print(f"[!] ERROR: UDP port {port} on {bind_addr} is already in use by another process.", file=sys.stderr)
            print(f"[*] TIP: Specify an alternate port using '--port <PORT>' or check running processes.", file=sys.stderr)
            sys.exit(1)
        raise

    # Optimize OS socket receive buffer to handle multi-chunk bursts
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
    except OSError:
        pass
    sock.settimeout(2.0)
    write_receiver_heartbeat(port=port, out_dir=OUT_DIR)

    print("==================================================")
    print("[*] PI-DIODE COLLECTOR HUB ACTIVE")
    print(f"[*] Listening on UDP {bind_addr}:{port}")
    print("[*] Physical Diode Isolation: ENFORCED")
    print(f"[*] Storage Directory: {OUT_DIR}")
    for nid, vk in KNOWN_NODE_PUBKEYS.items():
        if vk.encode().hex() in DEFAULT_EXAMPLE_PUBKEYS:
            print(f"[!] SECURITY WARNING: {nid} is using a default repository example key! Run generate_keys.py before field deployment.")
    print("==================================================")

    last_gc_time = time.time()

    while True:
        try:
            pkt, _ = sock.recvfrom(MAX_DATAGRAM_BYTES)
        except socket.timeout:
            now = time.time()
            write_receiver_heartbeat(port=port, out_dir=OUT_DIR)
            if now - last_gc_time > 5.0:
                cleanup_stale_buffers()
                last_gc_time = now
            continue
        except KeyboardInterrupt:
            print("\n[*] Receiver Hub shutting down cleanly.")
            break
        except Exception as e:
            print(f"[!] Socket read error: {e}", file=sys.stderr)
            continue

        # Periodic sliding-window buffer cleanup & heartbeat update
        now = time.time()
        if now - last_gc_time > 5.0:
            cleanup_stale_buffers()
            write_receiver_heartbeat(port=port, out_dir=OUT_DIR)
            last_gc_time = now

        try:
            process_datagram(pkt, now=now, strict_clock_skew=STRICT_CLOCK_SKEW)
        except Exception as e:
            print(f"[!] Unhandled error in process_datagram: {e}", file=sys.stderr)

    sock.close()


def enforce_storage_retention(out_dir=None, max_files=None):
    """
    Prunes the oldest saved .jpg files (and companion .sig.json envelopes) in out_dir
    when total count exceeds max_files.
    Designed for unattended off-grid 'Dead-Drop' Collector Vaults running for months.
    """
    target_dir = out_dir or OUT_DIR
    limit = max_files if max_files is not None else MAX_SAVED_ALERTS
    if not limit or limit <= 0 or not os.path.isdir(target_dir):
        return 0
    try:
        jpgs = [
            os.path.join(target_dir, f)
            for f in os.listdir(target_dir)
            if f.lower().endswith(".jpg")
        ]
        if len(jpgs) <= limit:
            return 0
        jpgs.sort(key=lambda p: (os.path.getmtime(p), p))
        to_remove = jpgs[: len(jpgs) - limit]
        removed = 0
        for p in to_remove:
            try:
                os.remove(p)
                removed += 1
                sig_p = p[:-4] + ".sig.json"
                if os.path.exists(sig_p):
                    os.remove(sig_p)
            except OSError:
                pass
        return removed
    except OSError:
        return 0


def export_dead_drop_bundle(bundle_path, out_dir=None):
    """
    Packages all verified JPEGs, detached .sig.json envelopes, alerts_journal.jsonl,
    seen_nonces.jsonl, and authorized_nodes.json from out_dir into a portable ZIP archive
    for rapid field extraction from an unattended Dead-Drop Collector Vault.
    """
    import zipfile
    target_dir = out_dir or OUT_DIR
    if not os.path.isdir(target_dir):
        raise FileNotFoundError(f"Alert directory not found: {target_dir}")
    count = 0
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(target_dir)):
            if fname.endswith((".jpg", ".jsonl", ".json")):
                full_p = os.path.join(target_dir, fname)
                if os.path.isfile(full_p):
                    zf.write(full_p, arcname=fname)
                    count += 1
    return count


def verify_stored_alert(alert_record, out_dir=None, pubkeys_map=None):
    """
    Independently verifies a stored alert record (from alerts_journal.jsonl or .sig.json)
    and its corresponding JPEG file on disk against the sender's Ed25519 public key.
    Returns True only if:
      1. The Ed25519 signature over the exact original signed JSON payload bytes is valid;
      2. The journal record fields (node, timestamp, nonce, image_sha256, detections) match
         the signed JSON payload (detecting any post-hoc journal tampering); and
      3. The JPEG file on disk matches the signed img_sha256 digest (detecting any image tampering).
    """
    target_dir = out_dir or OUT_DIR
    if isinstance(alert_record, str):
        # Path to .sig.json or .jpg
        sig_path = alert_record[:-4] + ".sig.json" if alert_record.lower().endswith(".jpg") else alert_record
        with open(sig_path, "r", encoding="utf-8") as f:
            alert_record = json.load(f)

    node_id = alert_record.get("node")
    sig_hex = alert_record.get("signature_hex", "")
    payload_b64 = alert_record.get("signed_payload_b64", "")
    if not node_id or not sig_hex or not payload_b64:
        return False

    try:
        sig_bytes = bytes.fromhex(sig_hex)
        raw_meta_bytes = base64.b64decode(payload_b64)
        signed_meta = json.loads(raw_meta_bytes.decode("utf-8"))
    except Exception:
        return False

    # Resolve public key from explicit map, KNOWN_NODE_PUBKEYS, or record pubkey_hex
    vk = None
    if pubkeys_map and node_id in pubkeys_map:
        key_val = pubkeys_map[node_id]
        vk = key_val if isinstance(key_val, VerifyKey) else VerifyKey(bytes.fromhex(key_val))
    elif node_id in KNOWN_NODE_PUBKEYS:
        vk = KNOWN_NODE_PUBKEYS[node_id]
    elif alert_record.get("pubkey_hex"):
        try:
            vk = VerifyKey(bytes.fromhex(alert_record["pubkey_hex"]))
        except Exception:
            return False

    if vk is None:
        return False

    # 1. Verify Ed25519 cryptographic signature over original signed JSON bytes
    try:
        vk.verify(raw_meta_bytes, sig_bytes)
    except Exception:
        return False

    # 2. Verify record fields were not altered relative to the signed payload
    if signed_meta.get("node") != node_id:
        return False
    if int(signed_meta.get("ts", -1)) != int(alert_record.get("timestamp", alert_record.get("ts", -2))):
        return False
    if signed_meta.get("nonce") != alert_record.get("nonce"):
        return False
    expected_sha256 = signed_meta.get("img_sha256")
    if expected_sha256 != alert_record.get("image_sha256"):
        return False
    if "detections" in alert_record and signed_meta.get("detections", []) != alert_record.get("detections", []):
        return False

    # 3. Verify JPEG file on disk matches the signed SHA-256 hash
    img_ref = alert_record.get("image_file", "")
    img_basename = os.path.basename(img_ref)
    img_path = os.path.join(target_dir, img_basename)
    if not os.path.isfile(img_path):
        return False
    try:
        with open(img_path, "rb") as imgf:
            img_bytes = imgf.read()
    except OSError:
        return False

    if hashlib.sha256(img_bytes).hexdigest() != expected_sha256:
        return False

    return True


def verify_exported_bundle(bundle_or_dir, pubkeys_map=None):
    """
    Verifies every alert in an alert directory or exported Dead-Drop .zip bundle.
    Returns (verified_count, failed_count).
    """
    import tempfile
    import shutil
    import zipfile

    cleanup_dir = None
    if os.path.isfile(bundle_or_dir) and bundle_or_dir.lower().endswith(".zip"):
        cleanup_dir = tempfile.mkdtemp(prefix="trailcam_verify_bundle_")
        with zipfile.ZipFile(bundle_or_dir, "r") as zf:
            zf.extractall(cleanup_dir)
        target_dir = cleanup_dir
    else:
        target_dir = bundle_or_dir

    try:
        local_keys = dict(pubkeys_map) if pubkeys_map else {}
        auth_file = os.path.join(target_dir, "authorized_nodes.json")
        if not local_keys and os.path.isfile(auth_file):
            with open(auth_file, "r", encoding="utf-8") as af:
                local_keys = json.load(af)

        journal_path = os.path.join(target_dir, "alerts_journal.jsonl")
        if not os.path.isfile(journal_path):
            return (0, 1)

        verified_count = 0
        failed_count = 0
        with open(journal_path, "r", encoding="utf-8") as jf:
            for line in jf:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    failed_count += 1
                    continue
                img_basename = os.path.basename(rec.get("image_file", ""))
                # Skip records whose JPEG was intentionally pruned by circular retention
                if not os.path.exists(os.path.join(target_dir, img_basename)) and MAX_SAVED_ALERTS > 0:
                    continue
                if verify_stored_alert(rec, out_dir=target_dir, pubkeys_map=local_keys):
                    verified_count += 1
                else:
                    failed_count += 1
        return (verified_count, failed_count)
    finally:
        if cleanup_dir:
            shutil.rmtree(cleanup_dir, ignore_errors=True)


def valid_port(value):
    try:
        p = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer")
    if not (1 <= p <= 65535):
        raise argparse.ArgumentTypeError(f"port {p} is out of range (must be 1-65535)")
    return p


def main():
    global MAX_SAVED_ALERTS
    parser = argparse.ArgumentParser(
        description="Production-Hardened Passive UDP Optical Diode Receiver & Cryptographic Reassembler"
    )
    parser.add_argument(
        "-p", "--port",
        type=valid_port,
        default=UDP_PORT,
        help=f"UDP port to listen on (default: {UDP_PORT})"
    )
    parser.add_argument(
        "-b", "--bind",
        type=str,
        default="0.0.0.0",
        help="Local IP address to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "-o", "--out-dir",
        type=str,
        default=OUT_DIR,
        help=f"Directory to store verified alert JPEGs and JSONL journal (default: {OUT_DIR})"
    )
    parser.add_argument(
        "-s", "--skew",
        type=int,
        default=MAX_CLOCK_SKEW_SEC,
        help=f"Max clock skew drift in seconds for replay warning/rejection (default: {MAX_CLOCK_SKEW_SEC})"
    )
    parser.add_argument(
        "--strict-clock-skew",
        action="store_true",
        default=STRICT_CLOCK_SKEW,
        help="Drop alerts exceeding max clock skew (enable when field nodes have RTC battery backup)"
    )
    parser.add_argument(
        "--max-alerts",
        type=int,
        default=MAX_SAVED_ALERTS,
        help="Circular cap on saved JPEGs for unattended Dead-Drop Vaults (0 = unlimited)"
    )
    parser.add_argument(
        "--export-bundle",
        type=str,
        default="",
        help="Export all verified JPEGs and journals from --out-dir into the specified .zip file and exit"
    )
    parser.add_argument(
        "--verify-bundle",
        type=str,
        default="",
        help="Cryptographically verify all stored alerts in a directory or exported .zip bundle and exit"
    )
    args = parser.parse_args()
    MAX_SAVED_ALERTS = args.max_alerts

    if args.export_bundle:
        n_files = export_dead_drop_bundle(args.export_bundle, out_dir=args.out_dir)
        print(f"[+] Exported {n_files} verified artifacts from '{args.out_dir}' to '{args.export_bundle}'")
        return

    if args.verify_bundle:
        ok, bad = verify_exported_bundle(args.verify_bundle)
        print(f"[*] Bundle Verification: {ok} verified, {bad} failed")
        sys.exit(0 if (ok > 0 and bad == 0) else 1)

    run_hub(
        port=args.port,
        bind_addr=args.bind,
        out_dir=args.out_dir,
        max_clock_skew=args.skew,
        strict_clock_skew=args.strict_clock_skew
    )


if __name__ == "__main__":
    main()



