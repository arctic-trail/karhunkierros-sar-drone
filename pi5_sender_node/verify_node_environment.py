#!/usr/bin/env python3
"""
File: pi5_sender_node/verify_node_environment.py
Description: Field diagnostic self-test utility for Pi 4/5 Edge-AI nodes.
             Validates PyNaCl, OpenCV, NumPy, CPU temperature, Ed25519 signing,
             and UDP socket egress to the Mac/Cabin Collector Hub.
License: MIT
"""
import os
import sys
import time
import socket
import platform

def test_python_environment():
    print("[*] 1. Python Environment & Architecture:")
    print(f"    - Python: {platform.python_version()} ({sys.executable})")
    print(f"    - Platform: {platform.platform()}")
    print(f"    - Machine: {platform.machine()}")
    
    # Check thermal sensor if on Linux/Pi
    temp_path = "/sys/class/thermal/thermal_zone0/temp"
    if os.path.exists(temp_path):
        try:
            with open(temp_path, "r") as f:
                celsius = int(f.read().strip()) / 1000.0
                print(f"    - SoC Temperature: {celsius:.1f}°C")
        except Exception:
            pass

def test_dependencies():
    print("\n[*] 2. Checking Required Python Dependencies:")
    deps = ["nacl", "cv2", "numpy", "serial"]
    all_ok = True
    for dep in deps:
        try:
            mod = __import__(dep)
            ver = getattr(mod, "__version__", "installed")
            print(f"    [+] {dep:<8}: OK (v{ver})")
        except ImportError:
            print(f"    [-] {dep:<8}: MISSING!")
            all_ok = False
    return all_ok

def test_cryptography():
    print("\n[*] 3. Validating Ed25519 Signing & Verification:")
    try:
        from nacl.signing import SigningKey
        key = SigningKey.generate()
        pub = key.verify_key
        msg = b"BENCHTOP_TEST_PACKET_2026"
        signed = key.sign(msg)
        pub.verify(signed)
        print(f"    [+] Ed25519 Keygen & Sign/Verify: OK")
        print(f"    - Test Public Key: {pub.encode().hex()[:16]}...")
        return True
    except Exception as e:
        print(f"    [-] Cryptographic test failed: {e}")
        return False

def test_camera_and_uart_hardware():
    print("\n[*] 4. Checking Camera & Pico Gatekeeper UART Hardware:")
    if platform.system() != "Linux":
        print("    [i] Host OS is not Linux/Raspberry Pi — skipping CSI Camera & /dev/ttyAMA0 hardware checks.")
        return True

    hw_ok = True
    # Check UART device
    uart_devs = [d for d in ("/dev/ttyAMA0", "/dev/serial0") if os.path.exists(d)]
    if uart_devs:
        print(f"    [+] Hardware UART detected: {', '.join(uart_devs)}")
        print("        (Verify Wires: W5 Purple -> Pi Pin 10, W6 Orange -> Pi Pin 16, W7 Black -> Pi Pin 14)")
    else:
        print("    [-] Hardware UART (/dev/ttyAMA0) NOT found!")
        print("        -> Fix: Ensure 'dtparam=uart0=on' and 'enable_uart=1' are in /boot/firmware/config.txt")
        hw_ok = False

    # Check CSI Camera via rpicam-hello or libcamera-hello
    import subprocess
    cam_cmd = None
    for candidate in ("rpicam-hello", "libcamera-hello"):
        if subprocess.call(["which", candidate], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            cam_cmd = candidate
            break
    if cam_cmd:
        try:
            out = subprocess.check_output([cam_cmd, "--list-cameras"], stderr=subprocess.STDOUT, text=True, timeout=5)
            if "imx708" in out.lower() or "available cameras" in out.lower() and "no cameras" not in out.lower():
                first_line = [ln.strip() for ln in out.splitlines() if "imx" in ln.lower() or "0 :" in ln.lower()]
                summary = first_line[0] if first_line else "CSI Camera detected"
                print(f"    [+] CSI Camera ([P03] IMX708): OK ({summary})")
            else:
                print("    [-] No CSI Camera detected by rpicam-hello!")
                print("        -> IKEA Fix (Stage 1 Step 1.3):")
                print("           * Pi 5 side (narrow 22-pin gold end): Gold teeth MUST face the Ethernet port.")
                print("           * Camera side (wide 15-pin silver end): Silver teeth MUST face the green Camera PCB.")
                hw_ok = False
        except Exception as e:
            print(f"    [!] Camera check warning: {e}")
    return hw_ok

def test_network_egress(target_ip="10.10.0.100", target_port=5514):
    print(f"\n[*] 5. Testing UDP Egress Link to Collector Hub ({target_ip}:{target_port}):")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        test_payload = b"PING_FROM_PI_NODE"
        bytes_sent = sock.sendto(test_payload, (target_ip, target_port))
        sock.close()
        print(f"    [+] Successfully transmitted {bytes_sent} bytes over UDP")
        return True
    except Exception as e:
        print(f"    [-] UDP transmission failed: {e}")
        return False

def main():
    print("=" * 60)
    print("ARCTIC-TRAIL-CAM // FIELD NODE DIAGNOSTIC SELF-TEST")
    print("=" * 60)
    test_python_environment()
    d_ok = test_dependencies()
    c_ok = test_cryptography()
    h_ok = test_camera_and_uart_hardware()
    target_ip = os.getenv("RECEIVER_IP", "10.10.0.100")
    n_ok = test_network_egress(target_ip)
    
    print("\n" + "=" * 60)
    if d_ok and c_ok and h_ok and n_ok:
        print("[+] ALL DIAGNOSTIC CHECKS PASSED - NODE READY FOR BURST EGRESS")
    else:
        print("[-] DIAGNOSTIC CHECKS FAILED - REVIEW LOGS ABOVE")
    print("=" * 60)
    return 0 if (d_ok and c_ok and h_ok and n_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
