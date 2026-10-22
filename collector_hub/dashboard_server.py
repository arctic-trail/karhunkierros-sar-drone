#!/usr/bin/env python3
"""
File: collector_hub/dashboard_server.py
Description: Production Local Web Server & Live Telemetry Bridge for the 3D Spatial Command Center UI.
             Serves collector_hub/ui/index.html and streams verified Ed25519 alerts from
             verified_alerts/alerts_journal.jsonl to the 3D WebGL Command Center.
License: MIT
"""
import os
import sys
import json
import time
import errno
import socket
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote, unquote_plus

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "ui")
REPO_DIR = os.path.dirname(BASE_DIR)
DEFAULT_ALERTS_DIR = os.getenv("OUT_DIR", os.path.join(REPO_DIR, "verified_alerts"))
DOCS_IMAGES_DIR = os.path.join(REPO_DIR, "docs", "images")
SERVER_START_TIME = time.time()


def valid_port(value):
    """Argparse validator ensuring port is an integer in the valid TCP range 1-65535."""
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer")
    if not (1 <= port <= 65535):
        raise argparse.ArgumentTypeError(f"port {port} is out of range (must be 1-65535)")
    return port


class ReusableHTTPServer(HTTPServer):
    """HTTPServer with SO_REUSEADDR enabled to allow immediate port reuse on restart."""
    allow_reuse_address = True


def make_command_center_handler(alerts_dir, verbose=False):
    """Factory creating a customized SimpleHTTPRequestHandler bound to specific asset directories."""

    class CommandCenterHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            # Serve UI assets directly from UI_DIR without mutating process cwd
            super().__init__(*args, directory=UI_DIR, **kwargs)

        def do_GET(self):
            parsed = urlparse(self.path)
            clean_path = unquote(parsed.path)
            query_params = {}
            if parsed.query:
                for kv in parsed.query.split("&"):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        query_params[unquote_plus(k)] = unquote_plus(v)

            # 1. API: Live verified alerts journal (supports ?since_idx=<N>&limit=<M> cursor pagination)
            if clean_path == "/api/alerts":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                journal_path = os.path.join(alerts_dir, "alerts_journal.jsonl")
                alerts = []
                if os.path.exists(journal_path):
                    try:
                        with open(journal_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    try:
                                        alerts.append(json.loads(line))
                                    except Exception:
                                        continue
                    except Exception:
                        pass

                total_count = len(alerts)
                try:
                    limit = max(1, min(500, int(query_params.get("limit", "50"))))
                except ValueError:
                    limit = 50

                if "since_idx" in query_params:
                    try:
                        since_idx = max(0, int(query_params["since_idx"]))
                    except ValueError:
                        since_idx = 0
                    sliced_alerts = alerts[since_idx:since_idx + limit]
                    next_idx = min(total_count, since_idx + len(sliced_alerts))
                    has_more = next_idx < total_count
                else:
                    sliced_alerts = alerts[-limit:]
                    next_idx = total_count
                    has_more = False

                payload = {
                    "timestamp": int(time.time()),
                    "total_count": total_count,
                    "next_idx": next_idx,
                    "has_more": has_more,
                    "alerts": sliced_alerts,
                    "node_count": 4,
                    "diode_enforced": True,
                    "storage_dir": alerts_dir,
                }
                self.wfile.write(json.dumps(payload).encode("utf-8"))
                return

            # 2. API: Server health & diagnostic status
            if clean_path in ("/api/status", "/api/health"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                # Calculate storage usage
                alerts_count = 0
                journal_path = os.path.join(alerts_dir, "alerts_journal.jsonl")
                active_nodes = set()
                if os.path.exists(journal_path):
                    try:
                        with open(journal_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    try:
                                        item = json.loads(line)
                                        alerts_count += 1
                                        if "node" in item:
                                            active_nodes.add(item["node"])
                                    except Exception:
                                        continue
                    except Exception:
                        pass

                # Check disk space
                statvfs = os.statvfs(alerts_dir) if os.path.exists(alerts_dir) else None
                free_gb = round((statvfs.f_bavail * statvfs.f_frsize) / (1024**3), 2) if statvfs else 0.0

                # True receiver liveness check: inspect receiver_heartbeat.json or UDP 5514 port bind state
                udp_live = False
                hb_path = os.path.join(alerts_dir, "receiver_heartbeat.json")
                if os.path.isfile(hb_path):
                    try:
                        with open(hb_path, "r", encoding="utf-8") as hbf:
                            hb = json.load(hbf)
                        if time.time() - float(hb.get("updated_at", 0)) < 10.0:
                            udp_live = True
                    except Exception:
                        pass

                if not udp_live:
                    try:
                        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        probe.bind(("0.0.0.0", 5514))
                        probe.close()
                        udp_live = False
                    except OSError as e:
                        if e.errno in (errno.EADDRINUSE, 48):
                            udp_live = True

                health = {
                    "status": "healthy",
                    "system": "PI-DIODE-TRAILCAM 3D COMMAND CENTER",
                    "uptime_sec": int(time.time() - SERVER_START_TIME),
                    "server_time": int(time.time()),
                    "receiver_udp_port": 5514,
                    "receiver_online": udp_live,
                    "alerts_recorded": alerts_count,
                    "active_nodes": sorted(list(active_nodes)),
                    "free_disk_gb": free_gb,
                    "alerts_dir": alerts_dir,
                }
                self.wfile.write(json.dumps(health).encode("utf-8"))
                return

            # 2b. API: Optional Aerial Observation Drone & 112 Police Guidance Telemetry
            if clean_path in ("/api/drone", "/api/drone/status"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                drone_status_file = os.path.join(alerts_dir, "drone_observer_status.json")
                req_action = query_params.get("action", "").strip().lower()
                drone_payload = None

                if req_action in ("approach", "standoff", "lantern-guide"):
                    try:
                        import drone_observer
                        raw_disp = query_params.get("display_text")
                        raw_aud = query_params.get("audio_text")
                        safe_disp = (
                            "".join(ch for ch in str(raw_disp) if ch not in "<>" and ch.isprintable())[:160]
                            if raw_disp is not None else None
                        )
                        safe_aud = (
                            "".join(ch for ch in str(raw_aud) if ch not in "<>" and ch.isprintable())[:160]
                            if raw_aud is not None else None
                        )
                        drone_payload = drone_observer.execute_approach_action(
                            status_path=drone_status_file,
                            preset_id=query_params.get("preset", "public_release_sar_cask"),
                            custom_display_text=safe_disp,
                            custom_audio_text=safe_aud,
                            return_to_standoff=(req_action == "standoff"),
                            lantern_guide=(req_action == "lantern-guide"),
                        )
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}
                elif req_action == "grid-search":
                    try:
                        import drone_observer
                        drone_payload = drone_observer.simulate_multi_drone_grid_search_mission(
                            drone_count=int(query_params.get("drones", "4")),
                            out_status_path=drone_status_file,
                        )
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}
                elif req_action == "sar-tourist-group":
                    try:
                        import drone_observer
                        drone_payload = drone_observer.simulate_wilderness_tourist_group_sar(
                            out_status_path=drone_status_file,
                        )
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}
                elif req_action == "dispatch-marketplace":
                    try:
                        import drone_observer
                        sub_act = query_params.get("sub_action", "simulate_multi_accept")
                        u_id = query_params.get("unit_id")
                        gov_mode = query_params.get("governance_mode")
                        auto_str = query_params.get("auto_accept")
                        auto_bool = (auto_str.lower() in ("1", "true", "yes")) if auto_str is not None else None
                        drone_payload = drone_observer.simulate_sar_dispatch_marketplace_lifecycle(
                            status_path=drone_status_file,
                            sub_action=sub_act,
                            unit_id=u_id,
                            governance_mode=gov_mode,
                            auto_accept_enabled=auto_bool,
                        )
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}
                elif req_action == "human-pilot":
                    try:
                        import drone_observer
                        sub_act = query_params.get("sub_action", "takeover_and_talk")
                        de = float(query_params.get("delta_east_m", "0.0"))
                        dn = float(query_params.get("delta_north_m", "0.0"))
                        da = float(query_params.get("delta_alt_m", "0.0"))
                        ctrl_mode = query_params.get("control_mode", "REMOTE_OPERATOR_GUIDED_NUDGE")
                        up_mode = query_params.get("uplink_mode", "AIRBORNE_PROP_NOTCHED_MIC_AND_VISUAL_GESTURE")
                        raw_msg = query_params.get("rescuer_message")
                        safe_msg = (
                            "".join(ch for ch in str(raw_msg) if ch not in "<>" and ch.isprintable())[:220]
                            if raw_msg is not None else None
                        )
                        raw_reply = query_params.get("hiker_reply")
                        safe_reply = (
                            "".join(ch for ch in str(raw_reply) if ch not in "<>" and ch.isprintable())[:220]
                            if raw_reply is not None else None
                        )
                        drone_payload = drone_observer.execute_human_pilot_and_voice_relay_action(
                            status_path=drone_status_file,
                            sub_action=sub_act,
                            delta_east_m=de,
                            delta_north_m=dn,
                            delta_alt_m=da,
                            control_mode=ctrl_mode,
                            uplink_mode=up_mode,
                            rescuer_message_fi=safe_msg,
                            hiker_reply_text=safe_reply,
                            deadman_brake_hold=(sub_act == "deadman_brake"),
                            manual_cask_drop=(sub_act == "drop_cask_mic"),
                            land_clearing_intercom=(sub_act == "land_clearing_intercom"),
                            takeoff_from_clearing=(sub_act == "takeoff_from_clearing"),
                        )
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}
                elif req_action == "finlab-suite":
                    try:
                        import drone_observer
                        drone_payload = drone_observer.run_complete_finlab_and_supply_chain_verification_suite()
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}
                elif req_action == "cnc-overwatch":
                    try:
                        import drone_observer
                        preempt_str = query_params.get("preempt", "1")
                        det_ppl_str = query_params.get("detect_people", "1")
                        det_veh_str = query_params.get("detect_vehicles", "1")
                        raw_msg = query_params.get("voice_msg")
                        safe_msg = (
                            "".join(ch for ch in str(raw_msg) if ch not in "<>" and ch.isprintable())[:220]
                            if raw_msg is not None else None
                        )
                        drone_payload = drone_observer.execute_cnc_overwatch_and_guidance_action(
                            status_path=drone_status_file,
                            task_mode=query_params.get("task_mode", "AUTO_OBSERVE_AND_SEARCH"),
                            preempt_mapping_on_detection=(preempt_str.lower() in ("1", "true", "yes")),
                            detect_lost_people=(det_ppl_str.lower() in ("1", "true", "yes")),
                            detect_lost_vehicles=(det_veh_str.lower() in ("1", "true", "yes")),
                            fleet_split_policy=query_params.get("split_policy", "SPLIT_1_FOLLOW_REST_MAP"),
                            subject_type=query_params.get("subject_type", "LOST_PERSON"),
                            guidance_mode=query_params.get("guidance_mode", "AUTONOMOUS_GUIDANCE"),
                            rc_delta_east_m=float(query_params.get("de", "0.0")),
                            rc_delta_north_m=float(query_params.get("dn", "0.0")),
                            rc_delta_alt_m=float(query_params.get("da", "0.0")),
                            custom_voice_message=safe_msg,
                        )
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}

                if drone_payload is None and os.path.isfile(drone_status_file):
                    try:
                        with open(drone_status_file, "r", encoding="utf-8") as df:
                            drone_payload = json.load(df)
                    except Exception:
                        drone_payload = None

                if drone_payload is None:
                    try:
                        import drone_observer
                        journal_path = os.path.join(alerts_dir, "alerts_journal.jsonl")
                        candidate_alert = None
                        prev_alert = None
                        if os.path.isfile(journal_path):
                            lines = []
                            with open(journal_path, "r", encoding="utf-8") as jf:
                                for raw_l in jf:
                                    raw_l = raw_l.strip()
                                    if raw_l:
                                        try:
                                            lines.append(json.loads(raw_l))
                                        except Exception:
                                            continue
                            for idx in range(len(lines) - 1, -1, -1):
                                ok, _, _ = drone_observer.should_dispatch_aerial_observer(lines[idx])
                                if ok:
                                    candidate_alert = lines[idx]
                                    if idx > 0:
                                        prev_alert = lines[idx - 1]
                                    break
                        if candidate_alert is None:
                            candidate_alert = {
                                "node": query_params.get("node", "NODE-NORTH-01"),
                                "timestamp": int(time.time()),
                                "verified": True,
                                "camera_ok": True,
                                "pico_trig": "TRIG,MAG=1850,SEIS=540,DIST=5200,SPD=155,TEMP=-4.0,UPTIME_S=7200",
                                "detections": [{"class": query_params.get("class", "person"), "conf": 0.94, "box": [0.42, 0.25, 0.58, 0.78]}],
                            }
                        drone_payload = drone_observer.simulate_complete_observation_mission(
                            candidate_alert,
                            previous_alert=prev_alert,
                            out_status_path=drone_status_file,
                        )
                    except Exception as e:
                        drone_payload = {"dispatched": False, "error": str(e)}

                self.wfile.write(json.dumps(drone_payload).encode("utf-8"))
                return

            # 2c. API: Live Field-Test Binary MAVLink v2 Telemetry & Command Bridge
            if clean_path.startswith("/api/field/"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    import mavlink_field_bridge
                    bridge = mavlink_field_bridge.GLOBAL_FIELD_BRIDGE
                    if clean_path == "/api/field/upload_mission":
                        res = bridge.upload_cooperative_sector_mission(
                            x_min_m=float(query_params.get("xMin", "-230")),
                            y_min_m=float(query_params.get("yMin", "-155")),
                            x_max_m=float(query_params.get("xMax", "230")),
                            y_max_m=float(query_params.get("yMax", "135")),
                            agl_m=float(query_params.get("agl", "55")),
                            ref_lat=float(query_params.get("lat", "66.3695")),
                            ref_lon=float(query_params.get("lon", "29.3155")),
                        )
                    elif clean_path == "/api/field/target":
                        act_str = query_params.get("active", "1").lower()
                        res = bridge.set_target_assignment(
                            active=(act_str in ("1", "true", "yes")),
                            target_type=query_params.get("type", "PERSON"),
                        )
                    elif clean_path == "/api/field/drop":
                        res = bridge.command_payload_drop(
                            action=query_params.get("action", "queue"),
                            target_x_m=float(query_params.get("x", "40")),
                            target_y_m=float(query_params.get("y", "50")),
                        )
                    else:
                        res = bridge.get_bridge_status()
                except Exception as e:
                    res = {"bridge_online": False, "error": str(e)}
                self.wfile.write(json.dumps(res).encode("utf-8"))
                return

            # 3. Serve verified image captures from alerts_dir (with canonical commonpath containment & image-only extension allowlist)
            if clean_path.startswith("/alerts/"):
                rel_file = os.path.basename(clean_path[len("/alerts/"):].lstrip("/"))
                ext = os.path.splitext(rel_file)[1].lower()
                if ext not in (".jpg", ".jpeg", ".png"):
                    self.send_error(403, "Forbidden: /alerts/ serves verified image files (.jpg/.jpeg/.png) only")
                    return
                real_base = os.path.realpath(alerts_dir)
                real_target = os.path.realpath(os.path.join(real_base, rel_file))
                if os.path.commonpath([real_target, real_base]) == real_base and os.path.isfile(real_target):
                    self.send_response(200)
                    mime = "image/png" if ext == ".png" else "image/jpeg"
                    self.send_header("Content-Type", mime)
                    self.send_header("Cache-Control", "public, max-age=3600")
                    self.end_headers()
                    with open(real_target, "rb") as f:
                        self.wfile.write(f.read())
                    return
                else:
                    self.send_error(404, "Alert image not found")
                    return

            # 4. Serve documentation preview images from docs/images (with canonical commonpath containment)
            if clean_path.startswith("/docs/images/"):
                rel_file = clean_path[len("/docs/images/"):].lstrip("/")
                real_base = os.path.realpath(DOCS_IMAGES_DIR)
                real_target = os.path.realpath(os.path.join(real_base, rel_file))
                if os.path.commonpath([real_target, real_base]) == real_base and os.path.isfile(real_target):
                    self.send_response(200)
                    mime = "image/png" if real_target.endswith(".png") else "image/jpeg"
                    self.send_header("Content-Type", mime)
                    self.end_headers()
                    with open(real_target, "rb") as f:
                        self.wfile.write(f.read())
                    return
                else:
                    self.send_error(404, "Documentation image not found")
                    return

            # 5. Root page -> index.html
            if clean_path in ("", "/", "/index.html"):
                index_path = os.path.join(UI_DIR, "index.html")
                if os.path.exists(index_path):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                    self.end_headers()
                    with open(index_path, "rb") as f:
                        self.wfile.write(f.read())
                    return

            # 6. Fallback to SimpleHTTPRequestHandler serving UI_DIR
            return super().do_GET()

        def list_directory(self, path):
            self.send_error(403, "Forbidden: directory listing is disabled")
            return None

        def log_message(self, format, *args):
            if verbose:
                super().log_message(format, *args)

    return CommandCenterHandler


def is_port_in_use(host, port):
    """Checks whether a TCP port is currently open and bound by another process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_available_port(host, preferred_port, fallback_ports=None):
    """Finds an available port starting from preferred_port, then probing fallback candidates."""
    if not is_port_in_use(host, preferred_port):
        return preferred_port

    if fallback_ports is None:
        fallback_ports = [8081, 8082, 8083, 8084, 8123, 8888, 9090]

    for p in fallback_ports:
        if p != preferred_port and not is_port_in_use(host, p):
            return p

    # Linear probe
    for p in range(preferred_port + 1, preferred_port + 50):
        if p <= 65535 and not is_port_in_use(host, p):
            return p

    raise OSError(f"No available ports found on {host} near {preferred_port}")


def run_dashboard(host="127.0.0.1", port=8080, alerts_dir=DEFAULT_ALERTS_DIR, auto_fallback=True, explicit_port=False, verbose=False):
    """Starts the 3D Command Center HTTP server with robust port management and error handling."""
    os.makedirs(alerts_dir, exist_ok=True)
    handler_class = make_command_center_handler(alerts_dir, verbose=verbose)

    target_port = port
    if is_port_in_use(host, target_port):
        if explicit_port or not auto_fallback:
            print(f"[!] ERROR: Port {target_port} is already in use by another process.", file=sys.stderr)
            print(f"[*] TIP: Specify a different port using '--port <PORT>' (e.g., --port 8123 or --port 8081).", file=sys.stderr)
            sys.exit(1)
        else:
            fallback = find_available_port(host, target_port)
            print(f"[*] NOTICE: Port {target_port} is currently in use by another process.")
            print(f"[*] Automatically switching to available port {fallback}...")
            target_port = fallback

    try:
        server = ReusableHTTPServer((host, target_port), handler_class)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"[!] ERROR: Port {target_port} is already in use ({e}).", file=sys.stderr)
            print(f"[*] Specify an alternate port using '--port <PORT>'.", file=sys.stderr)
            sys.exit(1)
        raise

    display_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host
    print("=================================================================")
    print("  ARCTIC-TRAIL-CAM // 3D SPATIAL COMMAND & TELEMETRY HUB")
    print("=================================================================")
    print(f"  [+] Web Interface   : http://{display_host}:{target_port}")
    print(f"  [+] Listening On    : {host}:{target_port}")
    print(f"  [+] Alerts Storage  : {alerts_dir}")
    print(f"  [+] Journal File    : {os.path.join(alerts_dir, 'alerts_journal.jsonl')}")
    print("=================================================================")
    print("  Press Ctrl+C to terminate the dashboard server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down 3D Command Center server.")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="Local Web Server & Live Telemetry Bridge for the 3D Spatial Command Center UI."
    )
    parser.add_argument(
        "-p", "--port",
        type=valid_port,
        default=None,
        help="Port to listen on (1-65535, default: 8080 or DASHBOARD_PORT env var)"
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        default=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        help="Host address to bind to (default: 127.0.0.1; pass 0.0.0.0 for LAN access)"
    )
    parser.add_argument(
        "--alerts-dir",
        type=str,
        default=DEFAULT_ALERTS_DIR,
        help=f"Directory where verified alert JPEGs & journal are stored (default: {DEFAULT_ALERTS_DIR})"
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable automatic port fallback if the default port 8080 is in use"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Log all HTTP requests to stdout"
    )

    args = parser.parse_args()

    env_port_str = os.getenv("DASHBOARD_PORT")
    explicit_port = args.port is not None

    if explicit_port:
        port = args.port
    elif env_port_str:
        try:
            port = valid_port(env_port_str)
            explicit_port = True
        except argparse.ArgumentTypeError:
            print(f"[!] Warning: DASHBOARD_PORT='{env_port_str}' is invalid; defaulting to 8080.", file=sys.stderr)
            port = 8080
    else:
        port = 8080

    run_dashboard(
        host=args.host,
        port=port,
        alerts_dir=args.alerts_dir,
        auto_fallback=not args.no_fallback,
        explicit_port=explicit_port,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()

