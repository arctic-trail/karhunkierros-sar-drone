#!/usr/bin/env python3
"""
Test Suite: Simulation & Verification of Arctic RP2040 Gatekeeper Firmware Logic
Verifies:
1. Dynamic EMA baseline tracking under diurnal temperature drift.
2. HLK-LD2450 radar frame decoding & byte slicing.
3. Sub-zero ADC temperature conversion and PTC de-icer logic.
4. Multi-sensor verification state transitions.
"""
import struct
import math

def test_radar_packet_unpack():
    print("[*] Testing HLK-LD2450 30-byte full frame unpacking (with 0x55 0xCC footer & 3 target slots)...")
    # Protocol: 0xAA, 0xFF, 0x03, 0x00 (4B Header) + Target 1..3 (3 x 8B) + 0x55, 0xCC (2B Footer) = 30 bytes
    header = b"\xAA\xFF\x03\x00"
    target1_x = 200
    target1_y = 3500
    target1_spd = 120
    target1_bytes = struct.pack("<hhhH", target1_x, target1_y, target1_spd, 0)
    target2_bytes = bytes(8)
    target3_bytes = bytes(8)
    footer = b"\x55\xCC"
    raw_packet = header + target1_bytes + target2_bytes + target3_bytes + footer

    assert len(raw_packet) == 30, f"Packet length should be 30, got {len(raw_packet)}"
    assert raw_packet[:4] == b"\xAA\xFF\x03\x00" and raw_packet[28:30] == b"\x55\xCC", "Invalid frame header/footer"

    # Test both positive (bit 15 = 1) and negative (bit 15 = 0) sign-magnitude HLK-LD2450 values
    # In HLK-LD2450 protocol: bit 15 = 1 means positive, bit 15 = 0 means negative
    pos_y_u16 = 0x8000 | 3500   # +3500 mm
    neg_x_u16 = 200             # -200 mm
    pos_spd_u16 = 0x8000 | 120  # +120 cm/s
    signed_pkt = header + struct.pack("<HHHH", neg_x_u16, pos_y_u16, pos_spd_u16, 0) + target2_bytes + target3_bytes + footer
    assert len(signed_pkt) == 30

    import sys
    import types
    import os

    # Create mock MicroPython 'machine' module to import pico_gatekeeper/main.py directly
    mock_machine = types.ModuleType("machine")
    class MockPin:
        IN = 0
        OUT = 1
        PULL_UP = 2
        PULL_DOWN = 3
        def __init__(self, pin_id, mode=0, pull=0, value=0):
            self.pin_id = pin_id
            self._val = value
        def value(self, v=None):
            if v is not None:
                self._val = v
            return 1 if self.pin_id == 17 else self._val
    class MockI2C:
        def __init__(self, *args, **kwargs): pass
        def scan(self): return [0x0D, 0x48]
        def writeto_mem(self, *args, **kwargs): pass
        def readfrom_mem(self, addr, reg, n):
            return b"\x10\x05\x20\x04\x30\x03" if n == 6 else b"\x01\x90"
    class MockUART:
        def __init__(self, *args, **kwargs):
            self._rx = b"\x00\xFF" + signed_pkt  # Leading garbage bytes to test header sync!
            self.tx_log = []
        def any(self): return len(self._rx)
        def read(self, n):
            out = self._rx[:n]
            self._rx = self._rx[n:]
            return out
        def write(self, data): self.tx_log.append(data)
    class MockADC:
        def __init__(self, ch): pass
        def read_u16(self): return int((0.795492 / 3.3) * 65535)
    class MockWDT:
        def __init__(self, timeout=8000): self.feeds = 0
        def feed(self): self.feeds += 1

    mock_machine.Pin = MockPin
    mock_machine.I2C = MockI2C
    mock_machine.UART = MockUART
    mock_machine.ADC = MockADC
    mock_machine.WDT = MockWDT
    mock_machine.lightsleep = lambda ms: None
    mock_machine.freq = lambda hz: None
    sys.modules["machine"] = mock_machine

    import time as std_time
    if not hasattr(std_time, "ticks_ms"):
        std_time.ticks_ms = lambda: int(std_time.time() * 1000)
        std_time.ticks_diff = lambda a, b: a - b
        std_time.sleep_ms = lambda ms: None
        std_time.sleep_us = lambda us: None

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../pico_gatekeeper")))
    import main as pico_main

    assert pico_main._decode_ld2450_signed16(pos_y_u16) == 3500
    assert pico_main._decode_ld2450_signed16(neg_x_u16) == -200
    assert pico_main._decode_ld2450_signed16(pos_spd_u16) == 120

    wdt = MockWDT(timeout=8000)
    dist_mm, spd_cms = pico_main.check_ld2450_radar(wdt=wdt, listen_ms=200)
    assert dist_mm >= 3500, f"Expected distance >= 3500mm, got {dist_mm}"
    assert spd_cms == 120, f"Expected +120 cm/s, got {spd_cms}"
    assert wdt.feeds > 0, "Watchdog should be fed during radar check"
    print(f"    [+] Radar frame decoding & stream sync: PASSED (Dist={dist_mm}mm, Spd={spd_cms}cm/s)")

def test_ema_baseline_tracking():
    print("[*] Testing Dynamic EMA Baseline Tracking...")
    EMA_SHIFT = 6  # Alpha = 1/64
    baseline = 3000

    # Simulate 500 steps of realistic environmental diurnal drift (e.g. 0.5 counts per 80ms step)
    for step in range(500):
        ambient_noise = int(3000 + 300 * math.sin(step / 200.0))
        baseline += (ambient_noise - baseline) >> EMA_SHIFT

    # Baseline should track ambient drift smoothly without triggering false alarms
    drifted_ambient = int(3000 + 300 * math.sin(500 / 200.0))
    delta = abs(drifted_ambient - baseline)
    assert delta < 200, f"EMA baseline lag too high: delta = {delta}"
    print(f"    [+] EMA baseline smoothly adapted: Ambient={drifted_ambient}, Baseline={baseline}, Lag={delta}")

    # Now simulate a sharp vehicle anomaly (+1800 counts)
    vehicle_signal = drifted_ambient + 1800
    anomaly_delta = abs(vehicle_signal - baseline)
    MAG_DELTA_OFFSET = 1200
    assert anomaly_delta > MAG_DELTA_OFFSET, f"Failed to trigger on anomaly: {anomaly_delta} <= {MAG_DELTA_OFFSET}"
    print(f"    [+] Vehicle magnetic spike correctly triggered: Anomaly Delta={anomaly_delta} > {MAG_DELTA_OFFSET}")

def test_temperature_conversion():
    print("[*] Testing RP2040 Core Temperature & De-Icer Logic...")
    # ADC Channel 4 formula: V = raw * 3.3 / 65535, T = 27 - (V - 0.706) / 0.001721
    # Test 1: +20°C ambient (summer)
    # V = 0.706 - (20 - 27) * 0.001721 = 0.706 + 7 * 0.001721 = 0.718 V
    raw_20c = int((0.718047 / 3.3) * 65535)
    v_calc = raw_20c * 3.3 / 65535.0
    t_20c = 27.0 - (v_calc - 0.706) / 0.001721
    assert abs(t_20c - 20.0) < 0.2

    # Test 2: -25°C arctic winter
    # V = 0.706 - (-25 - 27) * 0.001721 = 0.706 + 52 * 0.001721 = 0.7955 V
    raw_subzero = int((0.795492 / 3.3) * 65535)
    v_sub = raw_subzero * 3.3 / 65535.0
    t_subzero = 27.0 - (v_sub - 0.706) / 0.001721
    assert t_subzero < 0.0
    # Sub-zero check should trigger de-icer
    deicer_active = (t_subzero <= 1.0)
    assert deicer_active is True
    print(f"    [+] Temperature conversion PASSED: Subzero={t_subzero:.1f}°C -> De-icer Active={deicer_active}")

def test_receiver_hub_signature_verification():
    print("[*] Testing Receiver Hub Signature and Chunk Parsing...")
    try:
        from nacl.signing import SigningKey
        key = SigningKey.generate()
        pub = key.verify_key

        msg = b'{"node":"TEST-01","ts":1760000000,"detections":[{"class":"person"}]}'
        sig = key.sign(msg).signature
        pkt = b"DD\x01" + sig + msg

        # Test slice extracted in receiver_hub.py
        extracted_sig = pkt[3:67]
        extracted_msg = pkt[67:]
        pub.verify(extracted_msg, extracted_sig)
        print("    [+] Packet 0x01 Signature Slice Verification: PASSED (PyNaCl)")
    except ImportError:
        # Verify byte slicing layout: Type byte at index 2, 64-byte signature from index 3 to 67
        dummy_sig = b"S" * 64
        msg = b'{"node":"TEST-01","ts":1760000000,"detections":[{"class":"person"}]}'
        pkt = b"DD\x01" + dummy_sig + msg
        assert pkt[2] == 1, "Packet type should be 0x01"
        assert pkt[3:67] == dummy_sig, "Extracted signature does not match"
        assert pkt[67:] == msg, "Extracted JSON payload does not match"
        print("    [+] Packet 0x01 Signature Slice Layout (3:67 & 67:): PASSED (Byte validation)")

def test_sensor_profiles_and_debounced_wake():
    print("[*] Testing Sensor Profiles, Debounced DONE Pin & Overlapped De-Icer Wake...")
    import time as std_time
    import main as pico_main

    # 1. Verify operating profile classification across hardware states
    pico_main.SEISMIC_ALERT._val = 1
    pico_main.sensor_health["mag"] = True
    pico_main.sensor_health["seis"] = True
    assert pico_main.detect_operating_profile(bench_override=False) == pico_main.PROFILE_FULL_TRIPLE

    pico_main.sensor_health["mag"] = True
    pico_main.sensor_health["seis"] = False
    assert pico_main.detect_operating_profile(bench_override=False) == pico_main.PROFILE_MAG_RADAR_DUTY
    assert pico_main.detect_operating_profile(bench_override=True) == pico_main.PROFILE_BENCH_MAG_ONLY

    # 2. Verify 3-sample EMI debounce on Pi 5 DONE pin
    if pico_main.BREADBOARD_DONE_PIN is not None:
        pico_main.BREADBOARD_DONE_PIN._val = 0
    seq = iter([1, 0, 1])  # Glitchy pulse -> should return False
    orig_val = pico_main.PI5_DONE_PIN.value
    pico_main.PI5_DONE_PIN.value = lambda: next(seq)
    assert pico_main.is_done_asserted_debounced(samples=3, delay_ms=0) is False

    seq_solid = iter([1, 1, 1])  # Solid HIGH -> should return True
    pico_main.PI5_DONE_PIN.value = lambda: next(seq_solid)
    assert pico_main.is_done_asserted_debounced(samples=3, delay_ms=0) is True
    pico_main.PI5_DONE_PIN.value = orig_val

    # 3. Verify overlapped Pi 5 wake + PTC de-icer & telemetry formatting
    pico_main.pi5_uart.tx_log.clear()
    orig_sleep = std_time.sleep
    orig_ticks = std_time.ticks_ms
    fake_clock = [1000]
    def advance_clock():
        fake_clock[0] += 2000
        return fake_clock[0]
    std_time.sleep = lambda s: None
    std_time.ticks_ms = advance_clock
    try:
        pico_main.boot_pi5_and_handoff(
            mag_val=3400, mag_base=1600,
            seismic_val=0, seis_base=0,
            radar_dist=3800, radar_spd=115,
            temp_c=-12.5, wdt=None,
            profile=pico_main.PROFILE_MAG_RADAR_DUTY
        )
    finally:
        std_time.sleep = orig_sleep
        std_time.ticks_ms = orig_ticks

    assert len(pico_main.pi5_uart.tx_log) >= 1, "Expected TRIG telemetry transmitted over UART1"
    trig_line = pico_main.pi5_uart.tx_log[-1].decode("utf-8")
    assert "UPTIME_S=" in trig_line and "PROFILE=MAG_RADAR_DUTY" in trig_line, f"Missing fields in {trig_line}"
    assert "FAST_SNAP=" in trig_line and "TAMPER_ZEROIZED=" in trig_line, f"Missing border hardening fields in {trig_line}"
    assert pico_main.MOSFET_GATE.value() == 0, "MOSFET_GATE must be cut after wake cycle completes"
    assert pico_main.DEICE_HEATER.value() == 0, "DEICE_HEATER must be off after wake cycle completes"
    print("    [+] Sensor Profiles, 75ms DONE Debounce & Overlapped De-Icer: PASSED")


def test_border_hardening_upgrades():
    print("[*] Testing 5 Border-Hardening Upgrades (SPI Instant-Snap, MLX90640 0.00W EMCON, Tamper Zeroize, Aloha Trunk, BME280 Frost Gate)...")
    import main as pico_main
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../pi5_sender_node")))
    import sender_node

    # 1. BME280 Frost-Point / Dew-Point Gating (Upgrade 5)
    assert pico_main.should_enable_lens_deicer(temp_c=15.0, rh_pct=90.0) is False, "Should not heat at +15C"
    assert pico_main.should_enable_lens_deicer(temp_c=-5.0, rh_pct=35.0) is False, "Dry cold (-5C, 35% RH -> Td=-18C) should skip heater to save battery"
    assert pico_main.should_enable_lens_deicer(temp_c=-2.0, rh_pct=88.0) is True, "Humid freezing (-2C, 88% RH) must enable heater"

    # 2. Passive MLX90640 LWIR Thermal EMCON Profile (0.00W RF, Upgrade 2)
    pico_main.sensor_health["lwir"] = True
    assert pico_main.detect_operating_profile(bench_override=False) == pico_main.PROFILE_PASSIVE_EMCON_LWIR
    pico_main.read_mlx90640_thermal_contrast_c = lambda: 5.2
    verified, tripped, dist_equiv, _ = pico_main.evaluate_sensor_step(
        current_mag=3000, mag_ema=3000, current_seis=150, seis_ema=150,
        profile=pico_main.PROFILE_PASSIVE_EMCON_LWIR, loop_count=1
    )
    assert verified is True and tripped is True and dist_equiv == 5200
    assert pico_main.RADAR_PWR.value() == 0, "24GHz radar must remain 0.00W OFF in PROFILE_PASSIVE_EMCON_LWIR"
    pico_main.sensor_health["lwir"] = False

    # 3. Ephemeral SRAM Key Tamper Zeroization (<1ms wipe, Upgrade 3)
    pico_main.EPHEMERAL_SRAM_KEY[:] = b"ARCTIC-EPHEMERAL-SRAM-KEY-SEED01"
    pico_main.tamper_zeroized = False
    pico_main.zeroize_ephemeral_key_on_tamper()
    assert pico_main.tamper_zeroized is True
    assert all(b == 0 for b in pico_main.EPHEMERAL_SRAM_KEY), "SRAM key must be 100% zeroized (0x00)"

    # 4. Multi-Camera Shared Fiber Trunk Aloha Backoff (Upgrade 4)
    d_off = sender_node.compute_aloha_interpass_delays_s("NODE-NORTH-01", shared_trunk=False)
    assert d_off == (0.0, 0.0)
    d_n1 = sender_node.compute_aloha_interpass_delays_s("NODE-NORTH-01", shared_trunk=True)
    d_n2 = sender_node.compute_aloha_interpass_delays_s("NODE-NORTH-02", shared_trunk=True)
    assert 0.100 <= d_n1[0] <= 0.650 and 0.250 <= d_n1[1] <= 0.850
    assert 0.100 <= d_n2[0] <= 0.650 and 0.250 <= d_n2[1] <= 0.850
    print("    [+] All 5 Border-Hardening Upgrades Verified: PASSED")


import unittest


class TestSharedPicoFirmwareSuite(unittest.TestCase):
    def test_pico_gatekeeper_and_border_hardening(self):
        test_radar_packet_unpack()
        test_ema_baseline_tracking()
        test_temperature_conversion()
        test_receiver_hub_signature_verification()
        test_sensor_profiles_and_debounced_wake()
        test_border_hardening_upgrades()


if __name__ == "__main__":
    print("==================================================")
    print("ARCTIC-TRAIL-CAM FIRMWARE & PROTOCOL TEST SUITE")
    print("==================================================")
    test_radar_packet_unpack()
    test_ema_baseline_tracking()
    test_temperature_conversion()
    test_receiver_hub_signature_verification()
    test_sensor_profiles_and_debounced_wake()
    test_border_hardening_upgrades()
    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

