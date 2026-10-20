# File: pico_gatekeeper/main.py
# Description: Production Arctic-Spec RP2040 Sensor-Fusion Gatekeeper & Power Controller
# Target: Raspberry Pi Pico (RP2040) / MicroPython
# License: MIT
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
from machine import Pin, I2C, UART, ADC, WDT, lightsleep
import time
import struct

# ==============================================================================
# 1. GPIO Pin Assignments & Electrical Interfaces
# ==============================================================================
# Domain B High-Power MOSFET Gate (Active-High 3.3V)
MOSFET_GATE = Pin(15, Pin.OUT, value=0)

# Raspberry Pi 5 Completion Handshake (Active-High via 10k series resistor)
# Primary: GP17 (Physical Pin 22 on Carrier PCB J4)
# Secondary: GP2 (Physical Pin 4 on Benchtop Breadboard)
PI5_DONE_PIN = Pin(17, Pin.IN, Pin.PULL_DOWN)
try:
    BREADBOARD_DONE_PIN = Pin(2, Pin.IN, Pin.PULL_DOWN)
except Exception:
    BREADBOARD_DONE_PIN = None

# 24 GHz FMCW Radar Power Switch (High-Side Transistor / P-FET via GP6)
RADAR_PWR = Pin(6, Pin.OUT, value=0)

# PTC Viewport De-Icing Heater Gate (Active-High)
# Primary: GP16 (Physical Pin 21 on Carrier PCB J7)
# Secondary: GP22 (Physical Pin 29 on Benchtop Breadboard)
DEICE_HEATER = Pin(16, Pin.OUT, value=0)
try:
    DEICE_HEATER_ALT = Pin(22, Pin.OUT, value=0)
except Exception:
    DEICE_HEATER_ALT = None

# ADS1115 Active-Low Comparator / Alert Pin
SEISMIC_ALERT = Pin(14, Pin.IN, Pin.PULL_UP)

# Vault Lid / Trunk Umbilical Anti-Tamper Reed Switch (Closed=0 Normal, Open=1 Tamper)
TAMPER_SWITCH_PIN = Pin(12, Pin.IN, Pin.PULL_UP)

# Optional Arducam Mega / HM01B0 SPI Instant-Snap Camera Chip-Select (<150ms First-Frame Buffer)
SPI_CAM_CS = Pin(13, Pin.OUT, value=1)

# Onboard Status LED (Pico / Pico 2 auto-detect)
try:
    STATUS_LED = Pin("LED", Pin.OUT, value=0)
except Exception:
    STATUS_LED = Pin(25, Pin.OUT, value=0)

# Internal RP2040 Die Temperature Sensor (ADC Channel 4)
ADC_TEMP = ADC(4)

# ==============================================================================
# 2. Peripheral Communication Buses
# ==============================================================================
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5

i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100000)
radar_uart = UART(0, baudrate=256000, tx=Pin(0), rx=Pin(1))
pi5_uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))

QMC_ADDR = 0x0D
ADS_ADDR = 0x48
MLX90640_ADDR = 0x33          # Passive 32x24 Long-Wave IR Thermal Array (0.00W RF EMCON)
BME280_ADDR = 0x76            # Ambient Temp + Humidity Sensor for Frost-Point De-Icer Gating

# Global sensor health flags
sensor_health = {"mag": False, "seis": False, "lwir": False, "env": False}

# Volatile SRAM Ephemeral Key Seed (Zeroized in <1ms if TAMPER_SWITCH_PIN opens)
EPHEMERAL_SRAM_KEY = bytearray(b"ARCTIC-EPHEMERAL-SRAM-KEY-SEED01")
tamper_zeroized = False
last_instant_snap_len = 0

# ==============================================================================
# 3. Operating Profiles & Dynamic EMA Tracking Parameters
# ==============================================================================
PROFILE_FULL_TRIPLE = "FULL_TRIPLE"              # Mag (0x0D) + Seis (0x48) + 24GHz Radar
PROFILE_MAG_RADAR_DUTY = "MAG_RADAR_DUTY"        # Mag (0x0D) + 24GHz Radar (periodic sniff for humans/wildlife)
PROFILE_PASSIVE_EMCON_LWIR = "PASSIVE_EMCON_LWIR"  # 0.00W RF Passive Mode: Mag/Seis + MLX90640 LWIR (Radar OFF)
PROFILE_BENCH_MAG_ONLY = "BENCH_MAG_ONLY"        # Indoor bench override (single-sensor QMC5883L wake)

BENCH_MAG_ONLY = False        # Set True (or pull GP14 low at boot w/o ADS1115) for mag-only bench tests
EMCON_PASSIVE_ONLY = False    # Set True to force 0.00W RF (disables 24GHz radar micro-sweeps)
LWIR_DELTA_TEMP_C = 3.5       # Passive thermal contrast threshold (+3.5C above forest background)
RADAR_SNIFF_INTERVAL_LOOPS = 38  # ~3.0s periodic 350ms radar sniff when geophone (0x48) is absent
DONE_DEBOUNCE_SAMPLES = 3     # Consecutive high reads required on DONE pin (3 x 25ms = 75ms)
DONE_DEBOUNCE_DELAY_MS = 25

MAG_DELTA_OFFSET = 1200       # Ferromagnetic anomaly threshold above ambient
SEIS_DELTA_OFFSET = 380       # Ground vibration amplitude threshold above ambient
SEIS_SAMPLE_COUNT = 16        # Number of samples per RMS seismic evaluation window
EMA_SHIFT = 6                 # Alpha = 1 / 64 for adaptive baseline

# Anti-Thrashing & Storm Suppression Guardrails
STORM_TRIGGER_LIMIT = 3       # Max unverified triggers before activating storm mode
STORM_WINDOW_MS = 120000      # 2-minute evaluation window
STORM_COOLDOWN_MS = 900000    # 15-minute backoff period with raised thresholds
unverified_triggers = []
storm_mode_active = False
storm_start_ms = 0
BOOT_TICKS_MS = time.ticks_ms()


def detect_operating_profile(bench_override=None, emcon_override=None):
    """
    Determines active gatekeeper sensor profile based on discovered I2C peripherals
    and bench jumper / EMCON configuration flags:
    - PROFILE_BENCH_MAG_ONLY: BENCH_MAG_ONLY is True or GP14 jumpered low without ADS1115.
    - PROFILE_PASSIVE_EMCON_LWIR: MLX90640 (0x33) thermal array present or EMCON_PASSIVE_ONLY=True (0.00W RF).
    - PROFILE_FULL_TRIPLE: Both QMC5883L (0x0D) and ADS1115 (0x48) present on I2C0.
    - PROFILE_MAG_RADAR_DUTY: QMC5883L (0x0D) + HLK-LD2450 Radar (no geophone yet).
    """
    use_bench = BENCH_MAG_ONLY if bench_override is None else bench_override
    if use_bench:
        return PROFILE_BENCH_MAG_ONLY
    use_emcon = EMCON_PASSIVE_ONLY if emcon_override is None else emcon_override
    if use_emcon or sensor_health.get("lwir", False):
        return PROFILE_PASSIVE_EMCON_LWIR
    if not sensor_health["seis"] and SEISMIC_ALERT.value() == 0:
        return PROFILE_BENCH_MAG_ONLY
    if sensor_health["mag"] and sensor_health["seis"]:
        return PROFILE_FULL_TRIPLE
    return PROFILE_MAG_RADAR_DUTY


def is_done_asserted_debounced(samples=DONE_DEBOUNCE_SAMPLES, delay_ms=DONE_DEBOUNCE_DELAY_MS):
    """
    Requires the Pi 5 DONE signal (Carrier GP17 or Breadboard GP2) to remain high
    for `samples` consecutive reads to reject capacitive EMI switching transients.
    """
    for i in range(samples):
        high = (PI5_DONE_PIN.value() == 1) or (BREADBOARD_DONE_PIN is not None and BREADBOARD_DONE_PIN.value() == 1)
        if not high:
            return False
        if i + 1 < samples and delay_ms > 0:
            time.sleep_ms(delay_ms)
    return True

# ==============================================================================
# 4. Bus Recovery & Sensor Interface Functions
# ==============================================================================
def recover_i2c_bus():
    """
    Recovers from I2C bus lockup if a peripheral is stuck holding SDA low.
    Clocks SCL 9 times with SDA released, then issues a STOP condition.
    """
    global i2c
    try:
        scl = Pin(I2C_SCL_PIN, Pin.OUT)
        sda = Pin(I2C_SDA_PIN, Pin.IN)
        for _ in range(9):
            scl.value(0)
            time.sleep_us(10)
            scl.value(1)
            time.sleep_us(10)
        # Re-initialize MicroPython I2C bus
        i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100000)
    except Exception:
        pass

def read_rp2040_temperature_c():
    """Reads internal RP2040 core temperature to detect sub-zero frost conditions."""
    try:
        raw_val = ADC_TEMP.read_u16()
        voltage = raw_val * 3.3 / 65535.0
        temp_c = 27.0 - (voltage - 0.706) / 0.001721
        return round(temp_c, 1)
    except Exception:
        return 0.0

def init_sensors():
    """Initializes magnetometer, ADC, and verifies bus health with fault isolation."""
    global sensor_health
    try:
        devices = i2c.scan()
    except Exception:
        recover_i2c_bus()
        try:
            devices = i2c.scan()
        except Exception:
            devices = []

    # Configure Magnetometer
    if QMC_ADDR in devices:
        try:
            i2c.writeto_mem(QMC_ADDR, 0x0B, b'\x01')
            i2c.writeto_mem(QMC_ADDR, 0x09, b'\x15')
            sensor_health["mag"] = True
        except Exception:
            sensor_health["mag"] = False
    else:
        sensor_health["mag"] = False

    # Configure Geophone ADS1115 ADC
    if ADS_ADDR in devices:
        try:
            i2c.writeto_mem(ADS_ADDR, 0x01, b'\x0A\xA0')
            sensor_health["seis"] = True
        except Exception:
            sensor_health["seis"] = False
    else:
        sensor_health["seis"] = False

    # Discover optional Melexis MLX90640 Passive LWIR Thermal Array (0x33) for 0.00W RF EMCON
    if MLX90640_ADDR in devices:
        sensor_health["lwir"] = _validate_mlx90640_alive()
    else:
        sensor_health["lwir"] = False

    # Discover optional BME280 Ambient Temp/Humidity Sensor (0x76 / 0x77) for Frost-Point De-Icer Gating
    if (BME280_ADDR in devices) or (0x77 in devices):
        bme_addr = BME280_ADDR if (BME280_ADDR in devices) else 0x77
        try:
            # Configure ctrl_hum (0xF2 = 0x01 1x oversampling) and ctrl_meas (0xF4 = 0x27)
            i2c.writeto_mem(bme_addr, 0xF2, b"\x01")
            i2c.writeto_mem(bme_addr, 0xF4, b"\x27")
            sensor_health["env"] = True
        except Exception:
            sensor_health["env"] = False
    else:
        sensor_health["env"] = False

    return sensor_health["mag"] or sensor_health["seis"] or sensor_health["lwir"]


def _i2c_read_mem16(dev_addr, reg16, nbytes):
    """Reads `nbytes` from a 16-bit register address (`addrsize=16`) such as MLX90640 RAM."""
    try:
        return i2c.readfrom_mem(dev_addr, reg16, nbytes, addrsize=16)
    except TypeError:
        # Fallback for simplified mock I2C objects in unit tests that omit addrsize kwarg
        if hasattr(i2c, "writeto") and hasattr(i2c, "readfrom"):
            i2c.writeto(dev_addr, struct.pack(">H", reg16), False)
            return i2c.readfrom(dev_addr, nbytes)
        return i2c.readfrom_mem(dev_addr, reg16, nbytes)


def _validate_mlx90640_alive():
    """Verifies MLX90640 responds at 16-bit pixel RAM address 0x0400 with non-zero, non-stuck words."""
    try:
        raw = _i2c_read_mem16(MLX90640_ADDR, 0x0400, 16)
        if not raw or len(raw) < 16:
            return False
        vals = struct.unpack(">8h", raw[:16])
        if all(v == 0 for v in vals) or all(v == -1 for v in vals):
            return False
        return True
    except Exception:
        return False


def zeroize_ephemeral_key_on_tamper():
    """
    Overwrites the 32-byte volatile SRAM key seed with 0x00 within <1ms when the
    vault lid reed switch or trunk umbilical tamper loop opens.
    """
    global tamper_zeroized
    for idx in range(len(EPHEMERAL_SRAM_KEY)):
        EPHEMERAL_SRAM_KEY[idx] = 0x00
    tamper_zeroized = True
    return True


def read_mlx90640_thermal_contrast_c():
    """
    Reads peak-to-median thermal contrast (in deg C) from a passive MLX90640 (0x33)
    32x24 far-infrared subarray on I2C0 using 16-bit register addressing (addrsize=16)
    without emitting any RF or IR photons (0.00W RF).
    If the sensor fails or returns stuck all-zero/0xFFFF data, marks sensor_health['lwir']=False
    and returns None so the gatekeeper falls back to magnetic/seismic/radar sensing.
    """
    if not sensor_health.get("lwir", False):
        return None
    try:
        raw = _i2c_read_mem16(MLX90640_ADDR, 0x0400, 16)
        if not raw or len(raw) < 16:
            sensor_health["lwir"] = False
            return None
        vals = struct.unpack(">8h", raw[:16])
        if all(v == 0 for v in vals) or all(v == -1 for v in vals):
            sensor_health["lwir"] = False
            return None
        ambient_raw = sum(vals) // len(vals)
        peak_raw = max(vals)
        # Convert raw IR counts to approximate surface temperature delta (deg C)
        return round(max(0.0, (peak_raw - ambient_raw) * 0.125), 2)
    except Exception:
        sensor_health["lwir"] = False
        return None


def read_bme280_humidity_pct():
    """
    Reads ambient relative humidity (% RH) from an optional BME280 (0x76 / 0x77) on I2C0
    to gate the 3.6W window de-icer in dry sub-zero conditions. Returns None if absent.
    """
    if not sensor_health.get("env", False):
        return None
    for addr in (BME280_ADDR, 0x77):
        try:
            raw = i2c.readfrom_mem(addr, 0xFD, 2)
            if raw and len(raw) == 2:
                adc_h = (raw[0] << 8) | raw[1]
                if adc_h in (0, 0x8000, 0xFFFF):
                    return None
                # Linearized uncalibrated/default BME280 ADC humidity mapping (0..100% RH)
                rh = max(5.0, min(100.0, (adc_h / 512.0)))
                return round(rh, 1)
        except Exception:
            pass
    return None


def should_enable_lens_deicer(temp_c, rh_pct=None):
    """
    Frost-point / dew-point gated PTC heater controller:
    - If a BME280 humidity reading (`rh_pct`) is available, computes the Magnus-Tetens
      dew/frost point and only energizes the 3.6W window heater when `temp_c <= 1.0C`
      AND (`rh_pct >= 75.0` or `temp_c - dew_point_c <= 2.5C`), saving battery in dry cold.
    - Falls back to `temp_c <= 1.0C` when no humidity sensor is installed.
    """
    if temp_c > 1.0:
        return False
    if rh_pct is None:
        return True
    if rh_pct >= 75.0:
        return True
    # Approximate dew/frost depression: Td ~= T - ((100 - RH) / 5.0)
    dew_point_c = temp_c - ((100.0 - max(1.0, min(100.0, float(rh_pct)))) / 5.0)
    return (temp_c - dew_point_c) <= 2.5


INSTANT_SNAP_BUF = bytearray(256)


def capture_spi_instant_frame(spi_bus=None):
    """
    Triggers an immediate <150ms first-frame snapshot on an optional Arducam Mega SPI
    or HM01B0 camera wired directly to the Pico 2 (CS=GP13) at t=0.0s while the Pi 5 cold-boots.
    Reads the Arducam FIFO length registers (0x42..0x44) and bursts the initial header/frame
    bytes into `INSTANT_SNAP_BUF`, returning the captured frame byte count.
    """
    global last_instant_snap_len
    try:
        if spi_bus is None:
            try:
                from machine import SPI
                spi_bus = SPI(1, baudrate=4000000, polarity=0, phase=0)
            except Exception:
                spi_bus = None

        SPI_CAM_CS.value(0)
        time.sleep_us(20)
        if spi_bus is not None:
            # 1. Arducam ARDUCHIP_FIFO (0x04 | 0x80 = 0x84): clear FIFO (0x01) + start capture (0x02)
            spi_bus.write(b"\x84\x03")
            SPI_CAM_CS.value(1)
            time.sleep_ms(5)
            # 2. Read 24-bit FIFO size from registers 0x42, 0x43, 0x44
            fifo_len = 0
            for shift, reg in ((0, 0x42), (8, 0x43), (16, 0x44)):
                SPI_CAM_CS.value(0)
                spi_bus.write(bytes([reg]))
                b_val = spi_bus.read(1)
                SPI_CAM_CS.value(1)
                if b_val:
                    fifo_len |= (b_val[0] << shift)
            if 0 < fifo_len <= 524288:
                # 3. Burst read initial header/thumbnail slice from BURST_FIFO_READ (0x3C)
                SPI_CAM_CS.value(0)
                spi_bus.write(b"\x3C")
                read_len = min(len(INSTANT_SNAP_BUF), fifo_len)
                snap_head = spi_bus.read(read_len)
                SPI_CAM_CS.value(1)
                if snap_head:
                    INSTANT_SNAP_BUF[:len(snap_head)] = snap_head
                last_instant_snap_len = fifo_len
                return last_instant_snap_len
        SPI_CAM_CS.value(1)
        return last_instant_snap_len
    except Exception:
        try:
            SPI_CAM_CS.value(1)
        except Exception:
            pass
        return 0


def read_magnetometer():
    """Reads 3-axis magnetic vector magnitude |Bx| + |By| + |Bz|."""
    if not sensor_health["mag"]:
        return 0
    try:
        d = i2c.readfrom_mem(QMC_ADDR, 0x00, 6)
        x, y, z = struct.unpack('<hhh', d)
        return abs(x) + abs(y) + abs(z)
    except Exception:
        recover_i2c_bus()
        return 0


def read_seismic_rms(samples=SEIS_SAMPLE_COUNT):
    """Samples differential ground particle velocity from ADS1115."""
    if not sensor_health["seis"]:
        return 0
    total = 0
    valid_samples = 0
    try:
        for _ in range(samples):
            d = i2c.readfrom_mem(ADS_ADDR, 0x00, 2)
            val = struct.unpack('>h', d)[0]
            total += abs(val)
            valid_samples += 1
            time.sleep_ms(4)  # 250 SPS conversion rate
        return total // valid_samples if valid_samples > 0 else 0
    except Exception:
        recover_i2c_bus()
        return 0


def _decode_ld2450_signed16(raw_u16):
    """
    HLK-LD2450 encodes signed 16-bit integers in sign-magnitude format:
    Bit 15 = 1 -> positive value (raw & 0x7FFF)
    Bit 15 = 0 -> negative value -(raw & 0x7FFF)
    """
    mag = raw_u16 & 0x7FFF
    return mag if (raw_u16 & 0x8000) else -mag


LD2450_HEADER = b"\xAA\xFF\x03\x00"
LD2450_FOOTER = b"\x55\xCC"
LD2450_FRAME_LEN = 30


def parse_ld2450_buffer(rx_buf):
    """
    Scans `rx_buf` for complete 30-byte HLK-LD2450 frames:
      - Bytes 0..3:   Header `0xAA 0xFF 0x03 0x00`
      - Bytes 4..11:  Target 1 (x_u16, y_u16, spd_u16, res_u16)
      - Bytes 12..19: Target 2 (x_u16, y_u16, spd_u16, res_u16)
      - Bytes 20..27: Target 3 (x_u16, y_u16, spd_u16, res_u16)
      - Bytes 28..29: Footer `0x55 0xCC`
    Evaluates all 3 target slots and returns `(dist_mm, speed_cms, remaining_buf)`.
    Preserves partial frames across split UART reads and rejects false `AA FF` occurrences.
    """
    search_idx = 0
    n = len(rx_buf)
    while search_idx <= n - 4:
        hdr_idx = rx_buf.find(LD2450_HEADER, search_idx)
        if hdr_idx == -1:
            # Keep last 3 bytes in case 4-byte header was split across UART read boundary
            return 0, 0, rx_buf[max(search_idx, n - 3):]

        if n - hdr_idx < LD2450_FRAME_LEN:
            # Complete 30-byte frame has not finished arriving yet; retain from hdr_idx
            return 0, 0, rx_buf[hdr_idx:]

        frame = rx_buf[hdr_idx:hdr_idx + LD2450_FRAME_LEN]
        if frame[28:30] != LD2450_FOOTER:
            # False header match in payload/noise; advance past hdr_idx and keep scanning
            search_idx = hdr_idx + 2
            continue

        # Valid 30-byte frame: inspect all 3 target slots (offsets 4, 12, 20)
        best_dist = 0
        best_spd = 0
        for slot_off in (4, 12, 20):
            x_u16, y_u16, spd_u16 = struct.unpack("<HHH", frame[slot_off:slot_off + 6])
            x_mm = _decode_ld2450_signed16(x_u16)
            y_mm = _decode_ld2450_signed16(y_u16)
            spd = _decode_ld2450_signed16(spd_u16)
            dist_mm = int((x_mm * x_mm + y_mm * y_mm) ** 0.5)
            if dist_mm > 500:
                if best_dist == 0 or abs(spd) > abs(best_spd):
                    best_dist = dist_mm
                    best_spd = spd

        search_idx = hdr_idx + LD2450_FRAME_LEN
        if best_dist > 500:
            return best_dist, best_spd, rx_buf[search_idx:]

    return 0, 0, rx_buf[search_idx:]


def check_ld2450_radar(wdt=None, listen_ms=1200):
    """
    Powers 24 GHz Doppler radar briefly (GP6=1) to confirm moving target range & speed.
    Scans stream for complete 30-byte frames (header 0xAA 0xFF 0x03 0x00 + footer 0x55 0xCC)
    across all 3 target slots and feeds hardware watchdog during sample acquisition.
    """
    RADAR_PWR.value(1)
    time.sleep_ms(250)
    start = time.ticks_ms()
    target_dist_mm = 0
    target_speed_cms = 0
    rx_buf = b""

    while time.ticks_diff(time.ticks_ms(), start) < listen_ms:
        if wdt:
            wdt.feed()
        avail = radar_uart.any()
        if avail > 0:
            chunk = radar_uart.read(min(avail, 64))
            if chunk:
                rx_buf += chunk
                dist_mm, spd_cms, rx_buf = parse_ld2450_buffer(rx_buf)
                if len(rx_buf) > 180:
                    rx_buf = rx_buf[-60:]
                if dist_mm > 500:
                    target_dist_mm = dist_mm
                    target_speed_cms = spd_cms
                    break
        time.sleep_ms(15)

    RADAR_PWR.value(0)
    return target_dist_mm, target_speed_cms


# ==============================================================================
# 5. Cold-Boot & Parallel De-Icing Handoff State Machine
# ==============================================================================
def _set_deice_heater(state):
    """Drives both primary (GP16) and breadboard/secondary (GP22) PTC heater gates."""
    DEICE_HEATER.value(1 if state else 0)
    if DEICE_HEATER_ALT:
        DEICE_HEATER_ALT.value(1 if state else 0)


def trigger_deicing_if_subzero(wdt=None, duration_ms=4000, rh_pct=None):
    """Standalone helper pulsing the PTC lens heater ring if frost/dew conditions are met."""
    temp_c = read_rp2040_temperature_c()
    if rh_pct is None:
        rh_pct = read_bme280_humidity_pct()
    if should_enable_lens_deicer(temp_c, rh_pct=rh_pct):
        _set_deice_heater(True)
        steps = max(1, duration_ms // 500)
        for _ in range(steps):
            if wdt:
                wdt.feed()
            time.sleep_ms(500)
        _set_deice_heater(False)
    return temp_c


def boot_pi5_and_handoff(
    mag_val, mag_base, seismic_val, seis_base,
    radar_dist, radar_spd, temp_c, wdt=None, profile=PROFILE_FULL_TRIPLE, rh_pct=None
):
    """
    Executes Domain B high-side power-latching sequence with:
    1. Immediate MOSFET_GATE=1 assertion at t=0.0s + <150ms SPI Instant-Snap capture.
    2. Frost-point gated PTC heater overlap (t=250ms..4250ms) in parallel with Pi 5 kernel boot.
    3. Tamper-zeroization flag + monotonic UPTIME_S telemetry streaming and 3-sample debounced DONE.
    """
    STATUS_LED.value(1)

    if rh_pct is None:
        rh_pct = read_bme280_humidity_pct()

    # 1. Immediately Latch Domain B High-Side Power Rail & Snap <150ms SPI Pre-Roll Frame at t = 0.0s
    MOSFET_GATE.value(1)
    snap_bytes = capture_spi_instant_frame()
    start_ms = time.ticks_ms()
    MAX_TIMEOUT_MS = 35000  # Software handoff ceiling
    DEICE_DURATION_MS = 4250
    heater_active = False

    if should_enable_lens_deicer(temp_c, rh_pct=rh_pct):
        # 250ms stagger so buck converter input capacitor inrush settles before PTC load
        time.sleep_ms(250)
        if wdt:
            wdt.feed()
        _set_deice_heater(True)
        heater_active = True

    uptime_s = max(0, time.ticks_diff(start_ms, BOOT_TICKS_MS) // 1000)
    tamper_flag = 1 if tamper_zeroized else 0
    rh_str = f",RH={rh_pct}" if rh_pct is not None else ""
    telemetry_line = (
        f"TRIG,MAG={mag_val},MBASE={mag_base},SEIS={seismic_val},SBASE={seis_base},"
        f"DIST={radar_dist},SPD={radar_spd},TEMP={temp_c}{rh_str},UPTIME_S={uptime_s},"
        f"PROFILE={profile},FAST_SNAP={snap_bytes},TAMPER_ZEROIZED={tamper_flag}\n"
    )

    try:
        # 2. Stream telemetry & wait for debounced Pi 5 DONE handshake
        while time.ticks_diff(time.ticks_ms(), start_ms) < MAX_TIMEOUT_MS:
            if wdt:
                wdt.feed()
            elapsed_ms = time.ticks_diff(time.ticks_ms(), start_ms)

            # Turn off overlapped PTC heater once 4.0s window completes (just before shutter)
            if heater_active and elapsed_ms >= DEICE_DURATION_MS:
                _set_deice_heater(False)
                heater_active = False

            # Only stream UART after 1500ms to avoid interrupting early Pi bootloader
            if elapsed_ms >= 1500:
                pi5_uart.write(telemetry_line.encode('utf-8'))

            if elapsed_ms > 3500 and is_done_asserted_debounced():
                # Wait 2.5s in 500ms increments while feeding watchdog for clean Pi halt
                for _ in range(5):
                    if wdt:
                        wdt.feed()
                    time.sleep_ms(500)
                break
            time.sleep_ms(150)
    finally:
        # Guarantee heater and Domain B power are de-asserted
        _set_deice_heater(False)
        MOSFET_GATE.value(0)
        STATUS_LED.value(0)

    # 3. Enforce cooldown delay before resuming detection
    for _ in range(8):
        if wdt:
            wdt.feed()
        time.sleep(1)


# ==============================================================================
# 6. Main Arctic Gatekeeper Control Loop
# ==============================================================================
def evaluate_sensor_step(
    current_mag, mag_ema, current_seis, seis_ema,
    profile, loop_count, multiplier=1.0, wdt=None
):
    """
    Evaluates a single gatekeeper sensing step across all four supported hardware profiles
    (including 0.00W RF Passive EMCON via MLX90640 LWIR thermal contrast).
    If MLX90640 faults at runtime, automatically falls back to magnetic/seismic/radar sensing.
    Returns (verified, tier1_tripped, radar_dist, radar_spd).
    """
    mag_delta = abs(current_mag - mag_ema)
    seis_delta = abs(current_seis - seis_ema)

    mag_tripped = sensor_health["mag"] and (mag_delta > int(MAG_DELTA_OFFSET * multiplier))
    seis_tripped = sensor_health["seis"] and (seis_delta > int(SEIS_DELTA_OFFSET * multiplier))
    tier1_tripped = mag_tripped or seis_tripped

    radar_dist = 0
    radar_spd = 0

    if profile == PROFILE_BENCH_MAG_ONLY:
        if tier1_tripped:
            return True, True, 0, 0
        return False, False, 0, 0

    if profile == PROFILE_PASSIVE_EMCON_LWIR:
        # Strict 0.00W RF mode: never energize the 24 GHz radar; confirm via passive LWIR thermal contrast
        lwir_dt = read_mlx90640_thermal_contrast_c()
        if lwir_dt is None:
            # MLX90640 faulted at runtime: if EMCON_PASSIVE_ONLY is not forced, fall back to standard profile
            if not EMCON_PASSIVE_ONLY:
                fallback_prof = PROFILE_FULL_TRIPLE if sensor_health.get("seis") else PROFILE_MAG_RADAR_DUTY
                return evaluate_sensor_step(
                    current_mag, mag_ema, current_seis, seis_ema,
                    fallback_prof, loop_count, multiplier=multiplier, wdt=wdt
                )
            lwir_dt = 0.0
        lwir_tripped = lwir_dt >= (LWIR_DELTA_TEMP_C * multiplier)
        if lwir_tripped or (mag_tripped and seis_tripped):
            return True, (tier1_tripped or lwir_tripped), int(lwir_dt * 1000), 0
        return False, tier1_tripped, 0, 0

    if tier1_tripped:
        radar_dist, radar_spd = check_ld2450_radar(wdt=wdt, listen_ms=1200)
        verified = (radar_dist > 0) or (mag_tripped and seis_tripped)
        return verified, True, radar_dist, radar_spd

    # In PROFILE_MAG_RADAR_DUTY (no geophone installed yet), perform a brief periodic
    # radar sniff every RADAR_SNIFF_INTERVAL_LOOPS to detect non-ferromagnetic
    # humans and wildlife that produce zero magnetic signature.
    if profile == PROFILE_MAG_RADAR_DUTY and (loop_count % RADAR_SNIFF_INTERVAL_LOOPS == 0):
        radar_dist, radar_spd = check_ld2450_radar(wdt=wdt, listen_ms=350)
        if radar_dist > 0:
            return True, False, radar_dist, radar_spd

    return False, False, 0, 0


def main():
    # Downclock RP2040/RP2350 core (48 MHz minimum PLL on standard MicroPython;
    # fallback to 18 MHz if custom low-power build supports crystal sysclk)
    try:
        import machine
        for target_hz in (18000000, 48000000):
            try:
                machine.freq(target_hz)
                break
            except Exception:
                pass
    except Exception:
        pass

    global storm_mode_active, storm_start_ms, unverified_triggers

    init_sensors()
    active_profile = detect_operating_profile()
    time.sleep(1)

    # Initialize hardware watchdog (RP2040 max timeout is 8388 ms)
    wdt = None
    try:
        wdt = WDT(timeout=8000)
    except Exception:
        wdt = None

    # Initial baseline measurements
    mag_ema = read_magnetometer()
    seis_ema = read_seismic_rms(16)
    if mag_ema == 0:
        mag_ema = 3500
    if seis_ema == 0:
        seis_ema = 150

    loop_count = 0
    # Auto-arm tamper switch only if a closed reed loop to GND (0) is detected at boot
    tamper_armed = (TAMPER_SWITCH_PIN.value() == 0)

    while True:
        if wdt:
            wdt.feed()

        # Check hardware vault-lid / umbilical tamper loop (if armed at boot)
        if tamper_armed and (not tamper_zeroized) and (TAMPER_SWITCH_PIN.value() == 1):
            zeroize_ephemeral_key_on_tamper()
            temp_c = read_rp2040_temperature_c()
            rh_pct = read_bme280_humidity_pct()
            boot_pi5_and_handoff(
                mag_ema, mag_ema, seis_ema, seis_ema,
                0, 0, temp_c, wdt=wdt, profile=active_profile, rh_pct=rh_pct
            )

        # Check if Storm Mode has expired
        now_ms = time.ticks_ms()
        if storm_mode_active and time.ticks_diff(now_ms, storm_start_ms) > STORM_COOLDOWN_MS:
            storm_mode_active = False
            unverified_triggers = []

        # Scale thresholds up by 2.5x during storm conditions to protect battery
        multiplier = 2.5 if storm_mode_active else 1.0

        # Sample Tier 1 sensors
        current_mag = read_magnetometer()
        current_seis = read_seismic_rms(8)
        loop_count += 1

        verified, tier1_tripped, radar_dist, radar_spd = evaluate_sensor_step(
            current_mag, mag_ema,
            current_seis, seis_ema,
            active_profile, loop_count,
            multiplier=multiplier,
            wdt=wdt
        )

        if verified:
            # Target verified: clear unverified storm counter
            unverified_triggers = []
            temp_c = read_rp2040_temperature_c()
            rh_pct = read_bme280_humidity_pct()
            boot_pi5_and_handoff(
                current_mag, mag_ema,
                current_seis, seis_ema,
                radar_dist, radar_spd,
                temp_c,
                wdt=wdt,
                profile=active_profile,
                rh_pct=rh_pct
            )
            new_mag = read_magnetometer()
            new_seis = read_seismic_rms(16)
            if new_mag > 0:
                mag_ema = new_mag
            if new_seis > 0:
                seis_ema = new_seis
        elif tier1_tripped:
            # False alarm / unverified Tier-1 trip (wind or root sway): track for anti-thrashing
            unverified_triggers.append(now_ms)
            unverified_triggers = [t for t in unverified_triggers if time.ticks_diff(now_ms, t) < STORM_WINDOW_MS]
            if len(unverified_triggers) >= STORM_TRIGGER_LIMIT:
                storm_mode_active = True
                storm_start_ms = now_ms
        else:
            # Smoothly adapt EMA baseline with step clamps to prevent parked-vehicle blind spots
            if sensor_health["mag"] and current_mag > 0:
                diff_m = max(-256, min(256, current_mag - mag_ema))
                mag_ema += diff_m >> EMA_SHIFT
            if sensor_health["seis"] and current_seis > 0:
                diff_s = max(-128, min(128, current_seis - seis_ema))
                seis_ema += diff_s >> EMA_SHIFT

        if loop_count % 50 == 0:
            STATUS_LED.value(1)
            time.sleep_ms(10)
            STATUS_LED.value(0)

        # Micro-power sleep (feeds watchdog on wake every 80ms)
        lightsleep(80)

if __name__ == "__main__":
    main()

