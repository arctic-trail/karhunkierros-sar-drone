#!/usr/bin/env python3
"""
File: run_guided_bench_doctor.py
Description: Interactive & Automated IKEA-Style Benchtop Hardware Doctor & Bring-Up Assistant.
             Walks a builder with zero electronics experience through verifying:
               [Stage 1] Pico 2 [P07] USB / BOOTSEL & QMC5883L [P08] I2C0 (0x0d)
               [Stage 2] Breadboard Hole-by-Hole Wiring (W1..W7) & Pi [P01] + Camera [P05]
               [Stage 3] Collector Ethernet / 1x2 Optical Fiber Diode [P13]-[P16] (10.10.0.100)
               [Stage 4] End-to-End Ed25519 Signed Alert + Live Web Dashboard Verification
             Includes pin-exact troubleshooting hints referencing the exact breadboard holes
             (e.g., Hole j5, Hole j3, Hole a6, Hole a7, Hole a11, Hole a4, Hole a13).
License: MIT
"""
import argparse
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

# Prevent OS file-copy utilities from creating resource-fork or bytecode junk files
os.environ["COPYFILE_DISABLE"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

OS_JUNK_NAMES = {".DS_Store", ".Spotlight-V100", ".fseventsd", ".Trashes", ".TemporaryItems", "Thumbs.db", "desktop.ini"}


def purge_os_junk_metadata(target_path):
    """
    Recursively delete any OS indexer or temporary junk artifacts from a folder or volume.
    """
    if not target_path or not os.path.exists(target_path):
        return 0
    removed = 0
    if os.path.isfile(target_path):
        return 0
    for root, dirs, files in os.walk(target_path, topdown=False):
        for fname in files:
            if fname in OS_JUNK_NAMES or fname.startswith("._"):
                try:
                    os.remove(os.path.join(root, fname))
                    removed += 1
                except OSError:
                    pass
        for dname in dirs:
            if dname in OS_JUNK_NAMES or dname.startswith("._"):
                shutil.rmtree(os.path.join(root, dname), ignore_errors=True)
                removed += 1
    return removed


def copy_clean_file_bytes(src_path, dst_path):
    """
    Copy raw file payload bytes without copying OS extended attributes or resource forks.
    """
    with open(src_path, "rb") as fsrc:
        payload = fsrc.read()
    with open(dst_path, "wb") as fdst:
        fdst.write(payload)
        fdst.flush()
        os.fsync(fdst.fileno())


def flash_pico_cleanly(uf2_path=None, bootsel_vol=None):
    """
    Flash MicroPython .uf2 onto Raspberry Pi Pico 2 (RP2350) / Pico (RP2040) cleanly.
    Prefers the all-in-one `arctic_trailcam_pico2_complete.uf2` (MicroPython + main.py + test_qmc5883l.py)
    flashed directly over raw USB PICOBOOT via `picotool load -v -x`.
    """
    if not uf2_path:
        bundled_uf2 = os.path.join(SCRIPT_DIR, "pico_gatekeeper", "arctic_trailcam_pico2_complete.uf2")
        if os.path.isfile(bundled_uf2):
            uf2_path = bundled_uf2
        else:
            candidates = sorted(
                glob.glob(os.path.expanduser("~/Downloads/RPI_PICO2*.uf2"))
                + glob.glob(os.path.expanduser("~/Downloads/RPI_PICO*.uf2"))
            )
            if candidates:
                uf2_path = candidates[-1]
    if not uf2_path or not os.path.isfile(uf2_path):
        print("  [!] No MicroPython .uf2 file found.")
        return False

    purge_os_junk_metadata(uf2_path)
    if bootsel_vol and os.path.isdir(bootsel_vol):
        purge_os_junk_metadata(bootsel_vol)

    picotool_bin = shutil.which("picotool")
    if picotool_bin:
        print(f"  [*] Flashing {os.path.basename(uf2_path)} directly over raw USB via picotool...")
        proc = subprocess.run(
            [picotool_bin, "load", "-v", "-x", uf2_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            print("  [✓] picotool hardware-verified flash & reboot succeeded!")
            return True

    if bootsel_vol and os.path.isdir(bootsel_vol):
        dst_uf2 = os.path.join(bootsel_vol, os.path.basename(uf2_path))
        print(f"  [*] Writing pure UF2 blocks to {dst_uf2}...")
        copy_clean_file_bytes(uf2_path, dst_uf2)
        return True
    return False


def stage_sd_card_cleanly(bootfs_dir="/mnt/bootfs"):
    """
    Pre-stage pi5_sender_node/ code onto the Raspberry Pi 5 MicroSD bootfs partition
    using pure byte copies so zero OS temporary files ever touch the SD card.
    """
    if not os.path.isdir(bootfs_dir):
        return False
    src_dir = os.path.join(SCRIPT_DIR, "pi5_sender_node")
    dst_dir = os.path.join(bootfs_dir, "pi5_sender_node")
    os.makedirs(dst_dir, exist_ok=True)
    staged_count = 0
    for fname in sorted(os.listdir(src_dir)):
        if fname.startswith(".") or fname.endswith(".pyc") or fname in OS_JUNK_NAMES:
            continue
        sfile = os.path.join(src_dir, fname)
        if os.path.isfile(sfile):
            copy_clean_file_bytes(sfile, os.path.join(dst_dir, fname))
            staged_count += 1
    removed = purge_os_junk_metadata(bootfs_dir)
    print(f"  [✓] Clean-staged {staged_count} files into {dst_dir} (purged {removed} OS junk artifacts).")
    return True


BREADBOARD_WIRING_TABLE = [
    ("W1 (RED M-M)",    "Breadboard Hole j5  (Pico Right Row 5 = Pin 36 3V3_OUT)", "Breadboard Hole f24 (QMC5883L Row 24 = VCC)"),
    ("W2 (BLACK M-M)",  "Breadboard Hole j3  (Pico Right Row 3 = Pin 38 GND)",     "Breadboard Hole g25 (QMC5883L Row 25 = GND)"),
    ("W3 (BLUE M-M)",   "Breadboard Hole a6  (Pico Left Row 6  = Pin 6  GP4 SDA)", "Breadboard Hole f27 (QMC5883L Row 27 = SDA)"),
    ("W4 (YELLOW M-M)", "Breadboard Hole a7  (Pico Left Row 7  = Pin 7  GP5 SCL)", "Breadboard Hole g26 (QMC5883L Row 26 = SCL)"),
    ("W5 (PURPLE M-F)", "Breadboard Hole a11 (Pico Left Row 11 = Pin 11 GP8 TX)",  "Pi Header Pin 10 (5th pin down on outer right edge = GPIO15 RX)"),
    ("W6 (ORANGE M-F)", "Breadboard Hole a4  (Pico Left Row 4  = Pin 4  GP2 DONE)","Pi Header Pin 16 (8th pin down on outer right edge = GPIO23)"),
    ("W7 (BLACK M-F)",  "Breadboard Hole a13 (Pico Left Row 13 = Pin 13 GND)",     "Pi Header Pin 14 (7th pin down on outer right edge = GND)"),
]


def banner(title):
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)


def check_pico_and_magnetometer(skip_hardware=False):
    banner("STAGE 1 & 2A CHECK: PICO 2 [P07] & QMC5883L MAGNETOMETER [P08]")
    result = {
        "bootsel_drive": None,
        "serial_ports": [],
        "i2c_0x0d_detected": False,
        "status": "HARDWARE_NOT_CONNECTED",
    }

    if skip_hardware:
        print("  [i] --self-test mode: Simulating Pico 2 [P07] + QMC5883L [P08] hole-by-hole check.")
        for wid, src, dst in BREADBOARD_WIRING_TABLE[:4]:
            print(f"      ✓ Verified {wid:<16}: {src}  -->  {dst}")
        result["status"] = "SIMULATED_OK"
        return result

    # 1. Check if Pico 2 is mounted as a BOOTSEL USB drive and auto-flash cleanly
    for vol in ("/mnt/RP2350", "/mnt/RPI-RP2", "/media/RP2350", "/media/RPI-RP2"):
        if os.path.isdir(vol):
            result["bootsel_drive"] = vol
            print(f"  [!] Detected Pico 2 [P07] in BOOTSEL mode at: {vol}")
            if flash_pico_cleanly(bootsel_vol=vol):
                time.sleep(3.0)
                break
            print("      -> ACTION NEEDED (Stage 1, Step 1.4):")
            print("         Flash the official Pico 2 MicroPython .uf2 file using `picotool load -v -x`.")
            result["status"] = "BOOTSEL_MODE"
            return result

    # 2. Check USB serial ports for a running MicroPython Pico 2
    ports = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    result["serial_ports"] = ports
    if not ports:
        print("  [i] No Pico 2 [P07] USB serial port (/dev/ttyACM* or /dev/ttyUSB*) plugged in right now.")
        print("      When you sit down at the bench with your breadboard [P09]:")
        print("      1. Unplug USB power first.")
        print("      2. Press Pico 2 [P07] across the center canyon into Rows 1–20 (Cols b & h, USB at Row 1 Top).")
        print("      3. Press QMC5883L [P08] into Rows 24–27 (Col j: Row 24=VCC, Row 25=GND, Row 26=SCL, Row 27=SDA).")
        print("      4. Plug the first 4 color-coded jumper wires [P10]:")
        for wid, src, dst in BREADBOARD_WIRING_TABLE[:4]:
            print(f"         • {wid:<16}: {src}  -->  {dst}")
        return result

    print(f"  [+] Found Pico 2 [P07] USB serial port(s): {', '.join(ports)}")
    mpremote_bin = shutil.which("mpremote")
    if not mpremote_bin:
        venv_mp = os.path.join(REPO_ROOT, ".venv", "bin", "mpremote")
        if os.path.isfile(venv_mp):
            mpremote_bin = venv_mp

    if mpremote_bin:
        try:
            proc = subprocess.run(
                [
                    mpremote_bin,
                    "exec",
                    "import machine; i2c=machine.I2C(0,sda=machine.Pin(4),scl=machine.Pin(5),freq=100000); print('I2C_SCAN:', [hex(x) for x in i2c.scan()])",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5,
            )
            out = proc.stdout.strip()
            print(f"  [+] Pico 2 I2C0 Bus Response: {out}")
            if "0x0d" in out.lower() or "0xd" in out.lower():
                print("  [✓] SUCCESS: QMC5883L Magnetometer [P08] detected at 0x0d!")
                result["i2c_0x0d_detected"] = True
                result["status"] = "HARDWARE_OK"
            else:
                print("  [!] QMC5883L [P08] was NOT detected at 0x0d on I2C0 (GP4/GP5).")
                print("      -> CHECK THESE 4 BREADBOARD HOLES (Unplug USB before moving wires):")
                for wid, src, dst in BREADBOARD_WIRING_TABLE[:4]:
                    print(f"         • {wid:<16}: {src}  -->  {dst}")
                result["status"] = "I2C_MISSING_0X0D"
        except Exception as exc:
            print(f"  [i] Could not query Pico 2 via mpremote ({exc}).")
    return result


def check_pi_and_camera(pi_host="trailcam-node.local", skip_hardware=False):
    banner("STAGE 2B CHECK: RASPBERRY PI [P01], CAMERA [P05] & UART WIRES (W5–W7)")
    result = {
        "host": pi_host,
        "ping_ok": False,
        "status": "PI_OFFLINE",
    }

    if skip_hardware:
        print("  [i] --self-test mode: Verifying Pi [P01] GPIO header pin mapping (W5, W6, W7):")
        for wid, src, dst in BREADBOARD_WIRING_TABLE[4:]:
            print(f"      ✓ Verified {wid:<16}: {src}  -->  {dst}")
        result["status"] = "SIMULATED_OK"
        return result

    try:
        ping_cmd = ["ping", "-c", "1", "-W", "1", pi_host]
        proc = subprocess.run(ping_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        result["ping_ok"] = (proc.returncode == 0)
    except Exception:
        result["ping_ok"] = False

    if not result["ping_ok"]:
        print(f"  [i] Raspberry Pi [P01] ('{pi_host}') is not currently powered on / reachable on the network.")
        print("      When connecting the Pi [P01] on the bench:")
        print("      1. Slide the flashed 64GB MicroSD card [P04] into the underside of the Pi")
        print("         with the SHINY GOLD TEETH facing UP toward the green Pi board.")
        print("      2. Connect the Camera Ribbon Cable [P06] with power OFF:")
        print("         • Lift the black plastic latch collar UP by only 2mm.")
        print("         • Pi 5 CAM/DISP 0 end (narrow 22-pin): shiny gold contacts face TOWARD the Ethernet port.")
        print("         • Camera [P05] end (wider 15-pin): shiny contacts face TOWARD the green camera board.")
        print("      3. Plug the 3 Male-to-Female jumper wires (W5, W6, W7) onto the OUTER RIGHT EDGE of the Pi header:")
        for wid, src, dst in BREADBOARD_WIRING_TABLE[4:]:
            print(f"         • {wid:<16}: {src}  -->  {dst}")
        return result

    print(f"  [✓] Raspberry Pi [P01] ('{pi_host}') is ONLINE!")
    result["status"] = "PI_ONLINE"
    return result


def check_network_and_fiber_diode():
    banner("STAGE 3 CHECK: COLLECTOR ETHERNET & 1x2 OPTICAL FIBER DIODE [P13]–[P16]")
    has_10_10 = False
    try:
        proc = subprocess.run(["ip", "addr"] if shutil.which("ip") else ["ifconfig"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        if "10.10.0.100" in proc.stdout:
            has_10_10 = True
    except Exception:
        pass

    if has_10_10:
        print("  [✓] Host Collector IP 10.10.0.100/24 is ACTIVE on a local Ethernet interface!")
    else:
        print("  [i] Host Collector IP 10.10.0.100/24 is not yet assigned to a local Ethernet interface.")
        print("      When connecting your Pi [P01] or Media Converter #2 [P13]:")
        print("      • Run: ip link show   (to find your Ethernet interface, e.g. eth0)")
        print("      • Run: sudo ip addr add 10.10.0.100/24 dev eth0 && sudo ip link set eth0 up")
    print("\n  [i] Stage 3 Click-by-Click 1x2 Optical Fiber Diode Reminder:")
    print("      • Power BOTH Media Converters [P13] ONLY with +5.0V DC USB-to-Barrel cables [P19] (NEVER 12V!).")
    print("      • [Click 1] Field Converter #1 TX  -->  Yellow 1x2 Splitter [P14] Input")
    print("      • [Click 2] Splitter Output Leg 1  -->  Field Converter #1 RX (local carrier-detect loopback)")
    print("      • [Click 3] Splitter Output Leg 2  -->  Blue Coupler [P15] --> Fiber [P16] --> Collector Converter #2 RX")
    print("      • [Click 4] Collector Converter #2 TX stays UNPLUGGED with its white dust cap ON!")
    return {"has_10_10_0_100": has_10_10}


def get_python_executable():
    venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python3")
    if os.path.isfile(venv_py):
        return venv_py
    return sys.executable


def run_end_to_end_pipeline_smoke_test():
    banner("STAGE 4 CHECK: END-TO-END SIGNED ALERT + LIVE DASHBOARD SMOKE TEST")
    py_exec = get_python_executable()
    demo_script = os.path.join(SCRIPT_DIR, "run_mock_demo.py")
    t0 = time.time()
    proc = subprocess.run(
        [py_exec, "-B", demo_script],
        cwd=SCRIPT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    dt = time.time() - t0
    ok = (proc.returncode == 0 and "STATUS: SUCCESS" in proc.stdout)
    if ok:
        print(f"  [✓] End-to-End Ed25519 Signing, 8-Byte Nonce Chunking & UDP Reassembly PASSED in {dt:.2f}s!")
    else:
        print(f"  [✗] End-to-End Smoke Test FAILED (exit={proc.returncode}):\n{proc.stdout}")
        return {"pipeline_ok": False}

    # Also verify dashboard_server.py API health & pagination on an ephemeral port
    import threading
    sys.path.insert(0, os.path.join(SCRIPT_DIR, "collector_hub"))
    import dashboard_server

    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = os.path.join(tmpdir, "alerts_journal.jsonl")
        hb_path = os.path.join(tmpdir, "receiver_heartbeat.json")
        img_name = "NODE-BENCH-01_1792080000_aabbccdd.jpg"
        with open(os.path.join(tmpdir, img_name), "wb") as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9")
        alert_rec = {
            "node": "NODE-BENCH-01",
            "timestamp": int(time.time()),
            "trigger": "MAG+RADAR",
            "verified": True,
            "camera_ok": True,
            "image_file": img_name,
            "detections": [{"class_name": "person", "confidence": 0.94, "bbox": [120, 80, 280, 420]}],
        }
        with open(journal_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(alert_rec) + "\n")
        with open(hb_path, "w", encoding="utf-8") as f:
            json.dump({"updated_at": time.time(), "udp_port": 5514, "status": "LISTENING"}, f)

        handler = dashboard_server.make_command_center_handler(tmpdir, verbose=False)
        srv = dashboard_server.ReusableHTTPServer(("127.0.0.1", 0), handler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/alerts?since_idx=0", timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            assert len(data["alerts"]) == 1 and data["alerts"][0]["camera_ok"] is True
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as hresp:
                hdata = json.loads(hresp.read().decode("utf-8"))
            assert hdata["receiver_online"] is True
            print(f"  [✓] Live Web Dashboard API (/api/alerts?since_idx=0 & /api/health) VERIFIED on 127.0.0.1:{port}!")
        finally:
            srv.shutdown()
            srv.server_close()

    return {"pipeline_ok": True, "duration_s": round(dt, 2)}


def main():
    parser = argparse.ArgumentParser(
        description="IKEA-Style Guided Benchtop Hardware Doctor & Prototype Bring-Up Assistant"
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run non-interactive self-test of wiring tables, cryptographic pipeline, and dashboard API",
    )
    parser.add_argument(
        "--pi-host",
        default="trailcam-node.local",
        help="Hostname or IP of the Raspberry Pi sender node (default: trailcam-node.local)",
    )
    parser.add_argument(
        "--start-hub",
        action="store_true",
        help="After running diagnostics, launch both receiver_hub.py (UDP 5514) and dashboard_server.py (HTTP 8123) together in this terminal",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="When used with --start-hub, automatically open http://127.0.0.1:8123 in the default web browser",
    )
    parser.add_argument(
        "--drone-bench",
        action="store_true",
        help="Run Wave 1/2/3 SAR Drone Companion peripheral bench check (UVC thermal/Starvis, USB speaker, UARTs, ArduCopter 4.5+ params)",
    )
    parser.add_argument(
        "--export-drone-params",
        default="",
        help="Optional filepath to export the 37-parameter ArduCopter 4.5+ Pixhawk 6C .param profile for QGroundControl",
    )
    args = parser.parse_args()

    print("=" * 76)
    print("  ARCTIC TRAIL CAM SYSTEM // IKEA-STYLE GUIDED BENCHTOP DOCTOR & BRING-UP CLI")
    print("=" * 76)
    print("  Documentation & Briefs:")
    print("    • Technical Architecture Guide: docs/AERIAL_OBSERVATION_DRONE_GUIDE.md")
    print("    • Design Stabilization Log:     docs/DESIGN_EVOLUTION_AND_STABILIZATION_LOG.md")
    print("    • Pro Bono SAR Brief (PDF):     docs/KARHUNKIERROS_PRO_BONO_SAR_BRIEF_FI.pdf")

    r1 = check_pico_and_magnetometer(skip_hardware=args.self_test)
    r2 = check_pi_and_camera(pi_host=args.pi_host, skip_hardware=args.self_test)
    r3 = check_network_and_fiber_diode()
    r4 = run_end_to_end_pipeline_smoke_test()

    r5 = None
    if args.drone_bench or args.export_drone_params or args.self_test:
        sys.path.insert(0, os.path.join(SCRIPT_DIR, "collector_hub"))
        import drone_observer
        r5 = drone_observer.run_sar_drone_companion_bench_check(
            export_param_path=args.export_drone_params or None
        )

    banner("FINAL BENCHTOP DOCTOR SUMMARY")
    print(f"  • Stage 1/2A (Pico 2 [P07] + QMC5883L [P08]): {r1['status']}")
    print(f"  • Stage 2B   (Raspberry Pi [P01] + Camera):   {r2.get('status', 'PI_OFFLINE')}")
    print(f"  • Stage 3    (Collector 10.10.0.100 Link):    {'ACTIVE' if r3['has_10_10_0_100'] else 'READY_TO_ASSIGN'}")
    print(f"  • Stage 4    (Signed Alert + UI Pipeline):    {'PASS (100%)' if r4['pipeline_ok'] else 'FAIL'}")
    if r5 is not None:
        print(f"  • Stage 5    (SAR Drone Wave 1/2/3 Bench):    {r5['bench_status']} ({r5['arducopter_param_profile']['parameter_count']} ArduCopter Params)")
    print("=" * 76)

    if args.start_hub and r4["pipeline_ok"]:
        py_exec = get_python_executable()
        alerts_dir = os.path.join(SCRIPT_DIR, "verified_alerts")
        os.makedirs(alerts_dir, exist_ok=True)
        env = dict(os.environ)
        env["ALLOW_EXAMPLE_KEYS"] = env.get("ALLOW_EXAMPLE_KEYS", "1")
        banner("STARTING COLLECTOR HUB (UDP 5514) + LIVE WEB DASHBOARD (HTTP 8123)")
        print("  [+] Launching receiver_hub.py (UDP 5514) and dashboard_server.py (http://127.0.0.1:8123)...")
        print("  [+] Press Ctrl+C at any time to stop both servers cleanly.\n")
        rx_proc = subprocess.Popen(
            [py_exec, "-B", os.path.join(SCRIPT_DIR, "collector_hub", "receiver_hub.py"), "--out-dir", alerts_dir],
            cwd=SCRIPT_DIR,
            env=env,
        )
        ui_proc = subprocess.Popen(
            [py_exec, "-B", os.path.join(SCRIPT_DIR, "collector_hub", "dashboard_server.py"), "--alerts-dir", alerts_dir, "--port", "8123"],
            cwd=SCRIPT_DIR,
            env=env,
        )
        if args.open_browser:
            import webbrowser
            time.sleep(0.8)
            webbrowser.open("http://127.0.0.1:8123")
        try:
            rx_proc.wait()
            ui_proc.wait()
        except KeyboardInterrupt:
            print("\n  [i] Stopping Collector Hub and Dashboard Server...")
            rx_proc.terminate()
            ui_proc.terminate()

    return 0 if r4["pipeline_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
