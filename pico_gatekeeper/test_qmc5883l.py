# File: pico_gatekeeper/test_qmc5883l.py
# Description: Quick 5-second I2C & Magnetometer Benchtop Verification Script
# Target: Raspberry Pi Pico / Pico 2 (MicroPython)
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
from machine import Pin, I2C
import time
import math
import struct

# Initialize I2C0 on GP4 (SDA) and GP5 (SCL)
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)

print("\n" + "=" * 50)
print("  QMC5883L MAGNETOMETER HARDWARE VERIFICATION")
print("=" * 50)

# 1. Scan I2C bus
devices = i2c.scan()
hex_devs = [hex(d) for d in devices]
print(f"[*] I2C Bus Scan: Detected devices: {hex_devs}")

QMC_ADDR = 0x0D
MAG_THRESHOLD_DELTA = 1200

if QMC_ADDR not in devices:
    print(f"[!] ERROR: QMC5883L (0x0d) NOT detected on I2C0!")
    print("    Check your 4 breadboard jumper wires (Stage 2 Step 2.2):")
    print("      - Wire W1 (Red):    Hole j5  (Pico Pin 36 3V3) -> Hole f24 (Sensor VCC)")
    print("      - Wire W2 (Black):  Hole j3  (Pico Pin 38 GND) -> Hole g25 (Sensor GND)")
    print("      - Wire W3 (Blue):   Hole b6  (Pico Pin 6 GP4)  -> Hole f27 (Sensor SDA)")
    print("      - Wire W4 (Yellow): Hole a7  (Pico Pin 7 GP5)  -> Hole g26 (Sensor SCL)")
else:
    print("[+] SUCCESS: Found QMC5883L at 0x0d on I2C0 bus!")
    
    # 2. Configure QMC5883L (Continuous mode, 200Hz ODR, 8G range, 512 OSR)
    try:
        i2c.writeto_mem(QMC_ADDR, 0x0A, b'\x80') # Soft reset
        time.sleep_ms(10)
        i2c.writeto_mem(QMC_ADDR, 0x0B, b'\x01') # Set SET/RESET period
        i2c.writeto_mem(QMC_ADDR, 0x09, b'\x1D') # Mode: 512 OSR, 8G, 200Hz, Continuous
        print("[+] QMC5883L initialized in continuous measurement mode.")
        print("[*] Streaming live magnetic field... (Wave a steel screwdriver [T02] near the sensor!)\n")
        
        baseline_mag = None
        while True:
            # Check data ready (DRDY) flag
            status = i2c.readfrom_mem(QMC_ADDR, 0x06, 1)[0]
            if status & 0x01: # Data ready
                raw = i2c.readfrom_mem(QMC_ADDR, 0x00, 6)
                x, y, z = struct.unpack('<hhh', raw)
                mag = math.sqrt(x*x + y*y + z*z)
                if baseline_mag is None:
                    baseline_mag = mag
                delta = abs(mag - baseline_mag)
                if delta < (MAG_THRESHOLD_DELTA * 0.5):
                    baseline_mag = (0.98 * baseline_mag) + (0.02 * mag)
                bar = "#" * min(30, int(mag / 150))
                trig = " <-- [MAG TRIGGER]" if delta >= MAG_THRESHOLD_DELTA else ""
                print(f"  X:{x:6d}  Y:{y:6d}  Z:{z:6d}  |  |B|:{mag:6.0f} (d:{delta:5.0f}) [{bar:<30}]{trig}")
            time.sleep_ms(150)
    except KeyboardInterrupt:
        print("\n[*] Test stopped by user.")
    except Exception as e:
        print(f"[!] Read error: {e}")
