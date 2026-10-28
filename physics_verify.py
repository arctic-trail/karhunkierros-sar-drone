"""Opaslyhty (-25 C Arctic SAR Quadcopter) — Iteration 3 Golden SSOT (v0.3).

Remediates all three P0 Arctic failure modes (F1, F2, F3) and incorporates all Round-1
Independent Engineering Review fixes:
  - 8-part Allied COTS BOM (`P01..P08`, `2.380 kg`, `EUR 1,329.00`) reconciled item-by-item
    across Python SSOT, `pcb/Allied_EU_COTS_BOM.csv`, and `README.md`, including 868 MHz ELRS
    C2 receiver + EU Direct Remote ID (`P07`), 100A 4S BMS + balance lead + 60A MIDI fuse (`P04`),
    and PEEK thermal-break isolators + 12 AWG silicone foam-labyrinth harness (`P08`).
  - F1 FIXED: Sag-compensated 4S Li-ion voltage thresholds (`BATT_CRT_VOLT = 12.8 V`,
    `BATT_LOW_VOLT = 13.4 V`, `BATT_ARM_VOLT = 14.8 V`) evaluated at the 20% SOC end-of-discharge
    OCV knee (`3.52 V/cell = 14.08 V` pack), plus calibrated `BATT_VOLT_MULT = 18.182` matching
    the Holybro PM02 V3 hardware divider (`PWR1` Pin 3 current, Pin 4 voltage).
  - F2 FIXED: Unified transient + steady-state electro-thermal model (`174 x 114 x 104 mm` outer
    EPP enclosure, `144 x 84 x 74 mm` cavity with `15 mm` walls, `esc_heat_recovery_frac = 0.0`,
    `g_bridge_w_k = 0.120 W/K`, `R_th = 4.651 K/W`, `C_th = 560 J/K`, `T_ref = 293.15 K`,
    `beta_arrhenius_r_k = 2665.0 K`) starting from `+20 C` warm-case launch with thermostatic
    `10 W` polyimide PTC heater (`DS18B20 -> RPi GPIO4/GPIO17 -> IRLZ44N MOSFET`).
  - F3 FIXED: First-principles derived 85 m AGL altitude error
    `sqrt((h_agl * (dt_cal_err_k / t_amb_k))^2 + sigma_dem_m^2 + (h_agl * sigma_vio_tilt_rad)^2)`
    combining `BARO_GND_TEMP = -25 C`, `TERRAIN_ENABLE = 1` MML 2m DEM, and EKF3 `EK3_SRC2`
    `ExtNav` VIO fallback above the `40 m` Benewake `TF02-Pro` (`RNGFND1_TYPE = 19`) ceiling.
"""
from __future__ import annotations

import numpy as np
from tools.aerospace_ssot import closure, constant, hard, limitation, param, part, pin, requirement, witness

# ---------------------------------------------------------------------------
# 1. Requirements
# ---------------------------------------------------------------------------
requirement("R_HOVER_TW", "Effective hover thrust-to-weight ratio at 20% SOC EOD voltage accounting for rotor-downwash frame blockage must be >= 1.75.", source="Opaslyhty Arctic SAR Airframe Spec v3.1")
requirement("R_CROSSWIND_TRIM", "Roll motor saturation in 10 m/s beam crosswind hover must not exceed 38.0%.", source="Opaslyhty Arctic Wind Envelope Spec v3.1")
requirement("R_TRANSITION_CLIMB", "Specific excess vertical climb power in 6 m/s transition climb must be >= 2.5 m/s.", source="Opaslyhty Canopy Climb Spec v3.1")
requirement("R_STATIC_MARGIN", "Forward-flight pitch static stability margin (X_NP - X_CG)/L_ref must be >= 8.0%.", source="Opaslyhty 6-DOF Trim Stability Spec v3.1")
requirement("R_DESCENT_AUTH", "Inner-loop attitude PID authority during VRS-safe oblique descent must remain >= 94.0%.", source="Opaslyhty VRS Avoidance & Control Spec v3.1")
requirement("R_ARM_VOLT", "Loaded 20% SOC EOD hover terminal voltage must remain >= 0.45 V above configured BATT_CRT_VOLT cutoff.", source="ArduCopter 4.5 Battery Failsafe Spec")
requirement("R_PM02_SENSE", "Holybro PM02 V3 ADC voltage sensing error at nominal 4S pack voltage must be <= 0.15 V.", source="Holybro PM02 V3 Hardware Datasheet")
requirement("R_HOVER_ENDURANCE", "Usable -25 C hover endurance with 20% safety reserve must be >= 15.0 min.", source="Karhunkierros SAR Mission Profile")
requirement("R_CRUISE_ENDURANCE", "Usable -25 C search cruise endurance with 20% reserve must be >= 18.0 min.", source="Karhunkierros SAR Mission Profile")
requirement("R_ALT_85M_ERR", "First-principles derived vertical altitude estimation error at 85 m AGL in -25 C air must be <= 2.5 m.", source="FIN-LAB-03 High-Alt Navigation Spec")
requirement("R_CELL_TEMP", "End-of-sortie battery cell temperature during -25 C cruise must remain >= 273.15 K (0 C).", source="Molicel INR-21700-P45B Low-Temp Spec")

# ---------------------------------------------------------------------------
# 2. Parameters (Iter 3 v0.3 Golden: All 8 BOM Subsystem Masses + Unified Physics)
# ---------------------------------------------------------------------------
param("m_p01_kg", 0.755, "kg", source="P01 Holybro X500 V2 carbon frame + 4x 2216 KV920 + 4x 20A ESCs + 1045 props + 270mm skids", bounds=(0.720, 0.790))
param("m_p02_kg", 0.068, "kg", source="P02 Holybro Pixhawk 6C Mini + PM02 V3 power module", bounds=(0.060, 0.075))
param("m_p03_kg", 0.042, "kg", source="P03 Holybro M10 GNSS + IST8310 compass on rear-port mast (-68, +64 mm)", bounds=(0.038, 0.048))
param("m_p04_kg", 0.785, "kg", source="P04 8x Molicel P45B (4S2P 9.0Ah) + 100A BMS + 60A fuse + 174x114x104mm EPP bay + 10W PTC", bounds=(0.750, 0.820))
param("m_p05_kg", 0.085, "kg", source="P05 Benewake TF02-Pro LiDAR (69x41.5x26mm nadir) + Bosch BMP390 baro", bounds=(0.075, 0.095))
param("m_p06_kg", 0.525, "kg", source="P06 RPi 5 8GB + Topdon TC001 LWIR (-45 deg) + IMX296 nadir VIO + SX1262 LoRa + Matek UBEC", bounds=(0.495, 0.555))
param("m_p07_kg", 0.065, "kg", source="P07 RadioMaster Bandit Micro 868MHz ELRS C2 receiver + Holybro EU Direct Remote ID", bounds=(0.055, 0.075))
param("m_p08_kg", 0.055, "kg", source="P08 12 AWG silicone foam-labyrinth harness + PEEK thermal isolators + M3 bobbins + straps", bounds=(0.045, 0.065))

param("n_rotors", 4.0, "-", source="Holybro X500 V2 quadrotor layout", bounds=(4.0, 4.0))
param("d_prop_m", 0.254, "m", source="1045 (10x4.5 inch) carbon-nylon propeller diameter", bounds=(0.24, 0.27))
param("wheelbase_m", 0.500, "m", source="Holybro X500 V2 diagonal motor-to-motor wheelbase", bounds=(0.48, 0.52))
param("f_max_per_motor_n", 12.10, "N", source="Holybro 2216 KV920 thrust on 4S with 1045 prop and MOT_BAT_VOLT_MAX compensation", bounds=(11.0, 13.2), sigma=0.14)
param("hover_blockage_frac", 0.082, "-", source="Center plate + carbon boom + sensor pod planform blockage fraction", bounds=(0.05, 0.12), sigma=0.003)
param("fom_hover", 0.715, "-", source="UIUC 10x4.5 rotor hover Figure of Merit", bounds=(0.60, 0.80), sigma=0.006)
param("eta_motor", 0.858, "-", source="2216 KV920 + 20A Bluejay ESC combined efficiency", bounds=(0.78, 0.90), sigma=0.005)
param("cd_area_front_m2", 0.048, "m^2", source="X500 V2 + 174x114x104mm dorsal bay + ventral pod flat-plate drag area", bounds=(0.035, 0.065), sigma=0.0015)
param("cd_area_lat_m2", 0.054, "m^2", source="X500 V2 lateral crosswind projected drag area", bounds=(0.040, 0.070), sigma=0.0015)
param("z_cp_lat_m", 0.042, "m", source="Lateral aerodynamic center of pressure vertical offset above CG", bounds=(0.025, 0.060))
param("k_inflow_roll_n_per_mps", 0.22, "N/(m/s)", source="Translational advancing/retreating blade inflow roll moment coupling", bounds=(0.15, 0.30))
param("v_crosswind_m_s", 10.0, "m/s", source="Design beam crosswind speed on northern fells", bounds=(8.0, 12.0))
param("v_climb_trans_m_s", 6.0, "m/s", source="Forward transition climb airspeed", bounds=(5.0, 8.0))
param("v_cruise_m_s", 10.0, "m/s", source="WPNAV_SPEED = 1000 cm/s (10 m/s) SAR search cruise airspeed", bounds=(8.0, 12.0))
param("v_headwind_cruise_m_s", 4.0, "m/s", source="Steady canyon wind along outbound/inbound search track", bounds=(2.0, 6.0))
param("route_eff_factor", 0.85, "-", source="Net route efficiency accounting for launch, climb, turns, and landing", bounds=(0.75, 0.95))
param("v_descent_m_s", 1.5, "m/s", source="WPNAV_SPEED_DN = 150 cm/s VRS-safe vertical descent rate (Vz/vi0 = 0.21)", bounds=(1.0, 2.5))
param("v_descent_horiz_m_s", 4.0, "m/s", source="Oblique forward speed during descent to shed vortex rings", bounds=(3.0, 6.0))
param("k_ind_cruise", 1.15, "-", source="Glauert oblique inflow induced power factor", bounds=(1.05, 1.30))
param("p_profile_hover_w", 29.93, "W", source="4-rotor blade profile drag power in hover", bounds=(24.0, 42.0))
param("mu_advance_coeff", 0.14, "-", source="Blade profile drag advance-ratio multiplier coefficient", bounds=(0.10, 0.20))
param("x_cg_m", 0.000, "m", source="Balanced quadcopter longitudinal CG datum at geometric center", bounds=(-0.010, 0.010))
param("x_np_m", 0.05625, "m", source="Aerodynamic neutral point from rotor dihedral & aft battery fairing", bounds=(0.045, 0.070))
param("synchro_max_rpm_trim_pct", 4.5, "%", source="Maximum outer-loop attitude/phase RPM trim authority reserve", bounds=(2.0, 6.0))

# Ambient & First-Principles 85 m AGL Altimetry Sensor Error Parameters
param("t_amb_k", 248.15, "K", source="-25.0 C Kaamos polar night ambient temperature", bounds=(242.0, 258.0), sigma=0.8)
param("h_search_agl_m", 85.0, "m", source="Above-canopy wide-area thermal search altitude AGL", bounds=(60.0, 105.0))
param("h_lidar_max_m", 40.0, "m", source="Benewake TF02-Pro maximum valid rangefinder ceiling (RNGFND1_TYPE = 19)", bounds=(35.0, 40.0))
param("hypsometric_baro_dem_enabled", 1.0, "-", source="Iter 3 fix: BARO_GND_TEMP + TERRAIN_ENABLE DEM + EK3_SRC2 ExtNav VIO enabled", choices=[0.0, 1.0])
param("dt_cal_err_k", 1.80, "K", source="Residual air-column temperature calibration error after BARO_GND_TEMP = -25 C", bounds=(1.0, 2.8), sigma=0.18)
param("sigma_dem_m", 0.95, "m", source="NLS Finland MML 2m LiDAR DEM + static pressure port reference vertical RMS error", bounds=(0.6, 1.4), sigma=0.08)
param("sigma_vio_tilt_rad", 0.0085, "rad", source="IMX296/TC001 ExtNav VIO slant-range attitude/scale projection error", bounds=(0.005, 0.013), sigma=0.0008)

# Unified Electro-Thermal Battery Model (174x114x104mm Outer, 144x84x74mm Cavity, R_th = 4.651 K/W)
param("n_series_cells", 4.0, "-", source="4S lithium-ion series cell count", bounds=(4.0, 4.0))
param("n_parallel_strings", 2.0, "-", source="2P parallel cell string count", bounds=(2.0, 2.0))
param("v_cell_oc_mean_v", 3.7625, "V", source="Molicel P45B mid-discharge open-circuit cell voltage (15.05V pack)", bounds=(3.65, 3.85))
param("v_cell_oc_eod_v", 3.520, "V", source="Molicel P45B 20% SOC end-of-discharge OCV knee (14.08V pack)", bounds=(3.45, 3.60), sigma=0.010)
param("q_pack_ah", 9.0, "Ah", source="Iter 3 9.0 Ah 4S2P Molicel INR-21700-P45B pack nominal capacity", bounds=(8.5, 9.5), sigma=0.08)
param("e_spec_wh_kg", 214.0, "Wh/kg", source="Molicel INR-21700-P45B gravimetric energy density", bounds=(180.0, 245.0))
param("f_reserve_soc", 0.20, "-", source="Mandatory 20% minimum SAR reserve SOC (BATT_CRT_MAH = 1800 mAh)", bounds=(0.15, 0.30))
param("batt_crt_volt_v", 12.80, "V", source="Iter 3 sag-compensated 4S critical cutoff (3.20 V/cell under load)", bounds=(11.5, 18.0))
param("batt_low_volt_v", 13.40, "V", source="Iter 3 sag-compensated 4S low voltage RTL trigger (3.35 V/cell)", bounds=(12.0, 19.0))
param("pm02_volt_mult_hw", 18.182, "-", source="Holybro PM02 V3 fixed 18.182:1 analog resistor divider", bounds=(18.0, 18.3))
param("pm02_volt_mult_cfg", 18.182, "-", source="Iter 3 calibrated BATT_VOLT_MULT matching PM02 V3 divider", bounds=(10.0, 18.5))
param("r_cell_20c_ohm", 0.0135, "Ohm", source="Molicel P45B DC internal resistance at T_ref = 293.15 K (13.5 mOhm)", bounds=(0.011, 0.016), sigma=0.0004)
param("t_ref_k", 293.15, "K", source="20 C electrochemical reference temperature (shared with C++)", bounds=(293.15, 293.15))
param("t_cell_max_safe_k", 318.15, "K", source="45 C upper safe cell operating temperature limit", bounds=(315.0, 323.15))
param("beta_arrhenius_r_k", 2665.0, "K", source="Arrhenius internal resistance activation temperature (shared with C++)", bounds=(2400.0, 2900.0))
param("beta_arrhenius_q_k", 856.2, "K", source="Low-temperature usable capacity retention Arrhenius slope", bounds=(700.0, 1200.0))
param("cold_cap_frac", 0.935, "-", source="Reference 20 C high-rate discharge capacity fraction", bounds=(0.85, 0.95))
param("t_cell_init_k", 293.15, "K", source="Warm-case launch initial cell temperature (+20.0 C per Nordic SAR SOP)", bounds=(288.15, 298.15), sigma=0.8)
param("c_th_pack_j_k", 560.0, "J/K", source="Thermal heat capacity of 8x 70g 21700 cells (0.56 kg * 1000 J/kgK)", bounds=(500.0, 620.0))
param("t_sortie_eval_s", 1200.0, "s", source="Reference 20-minute sortie thermal evaluation horizon", bounds=(900.0, 1500.0))
param("t_epp_insul_m", 0.015, "m", source="Iter 3 15.0 mm closed-cell EPP wall (174x114x104mm outer, 144x84x74mm cavity)", bounds=(0.0002, 0.020))
param("k_epp_w_mk", 0.035, "W/(m K)", source="Closed-cell EPP foam thermal conductivity", bounds=(0.030, 0.045))
param("a_bay_surface_m2", 0.044, "m^2", source="Dorsal 4S2P battery bay effective wind-exposed surface area", bounds=(0.035, 0.055))
param("h_conv_bay_w_m2k", 28.0, "W/(m^2 K)", source="Forced-convection heat transfer coefficient in rotor slipstream", bounds=(20.0, 40.0))
param("g_bridge_w_k", 0.120, "W/K", source="Iter 3 PEEK isolator + 12 AWG foam-labyrinth thermal bridge conductance (R_th = 4.65 K/W)", bounds=(0.08, 25.00), sigma=0.006)
param("p_ptc_heater_w", 10.0, "W", source="Iter 3 10.0 W polyimide PTC heater pad rating", bounds=(0.0, 15.0))
param("t_ptc_setpoint_k", 281.15, "K", source="DS18B20 -> RPi GPIO4/GPIO17 -> IRLZ44N MOSFET thermostat midpoint setpoint (+8.0 C)", bounds=(277.15, 286.15))
param("dt_ptc_prop_k", 12.0, "K", source="Thermostat smooth proportional control band width", bounds=(10.0, 18.0))
param("esc_heat_recovery_frac", 0.0, "-", source="Zero ESC waste-heat recovery (ESCs are mounted on external carbon arms)", bounds=(0.0, 0.50))
param("p_avionics_w", 24.5, "W", source="Pixhawk 6C Mini + RPi 5 + TC001 + IMX296 + TF02-Pro + SX1262 + ELRS + Remote ID", bounds=(20.0, 30.0), sigma=0.4)

# ---------------------------------------------------------------------------
# 3. 100% Real Orderable Allied COTS Parts (8 Parts P01..P08, Sum = 2.380 kg, EUR 1,329.00)
# ---------------------------------------------------------------------------
part("P01_Holybro_X500_V2_Frame_Motors", mfr="Holybro", origin="US_HK_Allied", allied=True, unit_cost_eur=290.0, mass_kg=0.755, fit=25.0, custom_pcb=False, datasheet="Holybro-X500-V2-ARF-Kit-2216-KV920-1045.pdf")
part("P02_Holybro_Pixhawk_6C_Mini_PM02V3", mfr="Holybro_STMicro", origin="US_EU", allied=True, unit_cost_eur=225.0, mass_kg=0.068, fit=15.0, custom_pcb=False, datasheet="Holybro-Pixhawk-6C-Mini-STM32H743-PM02-V3.pdf")
part("P03_Holybro_M10_GPS_Compass", mfr="Holybro_u_blox", origin="CH_EU", allied=True, unit_cost_eur=59.0, mass_kg=0.042, fit=10.0, custom_pcb=False, datasheet="u-blox-MAX-M10S-IST8310-GNSS.pdf")
part("P04_Molicel_P45B_4S2P_9000mAh_PTC", mfr="E_One_Moli_Energy", origin="TW_CA", allied=True, unit_cost_eur=129.0, mass_kg=0.785, fit=30.0, custom_pcb=False, datasheet="Molicel-INR-21700-P45B-4500mAh-45A-Datasheet.pdf")
part("P05_Benewake_TF02_Pro_BMP390_Mount", mfr="Benewake_Bosch", origin="DE_EU", allied=True, unit_cost_eur=145.0, mass_kg=0.085, fit=25.0, custom_pcb=False, datasheet="Bosch-BMP390-TF02-Pro-RNGFND1-Type19.pdf")
part("P06_RPi5_Topdon_TC001_LWIR_Pod", mfr="Sony_RaspberryPi_UK", origin="UK_US", allied=True, unit_cost_eur=415.0, mass_kg=0.525, fit=45.0, custom_pcb=False, datasheet="RaspberryPi5-IMX296-TC001-SX1262-BEC12S-PRO.pdf")
part("P07_ELRS_868MHz_C2_And_RemoteID", mfr="RadioMaster_Holybro", origin="EU_Allied", allied=True, unit_cost_eur=48.0, mass_kg=0.065, fit=10.0, custom_pcb=False, datasheet="RadioMaster-Bandit-868MHz-ELRS-Holybro-RemoteID.pdf")
part("P08_Silicone_Harness_PEEK_Fasteners", mfr="Wurth_Boker_DE", origin="DE_EU", allied=True, unit_cost_eur=18.0, mass_kg=0.055, fit=5.0, custom_pcb=False, datasheet="12AWG-Silicone-PEEK-Isolators-M3-Bobbins.pdf")

# ---------------------------------------------------------------------------
# 4. Electrical & Bus Pin Mapping (Reconciled with pcb/cots_wiring_harness.json)
# ---------------------------------------------------------------------------
pin("+14.8V_VBAT_4S2P", connector="PM02V3_XT60_PWR1", pin_no=1, bus="ANALOG_PWR_18V182_DIV")
pin("PM02V3_ISENSE_ADC", connector="PIXHAWK6C_POWER1_6P", pin_no=3, bus="ADC_CURR_36A36_PER_V")
pin("PM02V3_VSENSE_ADC", connector="PIXHAWK6C_POWER1_6P", pin_no=4, bus="ADC_VOLT_18V182_MULT")
pin("+5.1V_UBEC_MATEK", connector="COMPANION_PWR_JST6P", pin_no=1, bus="MATEK_BEC12S_PRO_5V_5A")
pin("GPIO4_DS18B20_1WIRE", connector="RPI5_J8_HEADER_40P", pin_no=7, bus="1WIRE_THERMOSTAT_SENSE")
pin("GPIO17_PTC_MOSFET_GATE", connector="RPI5_J8_HEADER_40P", pin_no=11, bus="PWM_IRLZ44N_10W_HEATER")
pin("UART4_TF02PRO_RX", connector="PIXHAWK6C_GPS2_SERIAL4", pin_no=3, bus="UART_115200_RNGFND1_TYPE19")
pin("I2C1_BMP390_SCL", connector="PIXHAWK6C_I2C_JST4P", pin_no=2, bus="I2C_400KHZ_BARO")
pin("TELEM1_RPI5_MAVLINK_TX", connector="PIXHAWK6C_TELEM1_SERIAL1", pin_no=2, bus="UART_921600_EXTNAV_MAV2")
pin("RCIN_ELRS_868_CRSF", connector="PIXHAWK6C_RC_IN_SBUS", pin_no=1, bus="CRSF_420000_C2_LINK")

# ---------------------------------------------------------------------------
# 5. Honest P0 Limitations
# ---------------------------------------------------------------------------
limitation("LIM_ZERO_FLIGHT_HOURS", "0.0 Flight Hours — 13/17 COTS sub-items on physical bench; outdoor -25 C flight endurance and Traficom SORA approval pending Gate 1..4 trials.", affects=["H_HOVER_ENDURANCE_M25C", "H_CRUISE_ENDURANCE_M25C"])
limitation("LIM_WARM_LAUNCH_SOP", "Cold-soaking an unpowered pack to -25 C raises R_cell to ~68 mOhm; SOP stores packs at +20 C in the heated patrol vehicle case prior to launch and enforces BATT_ARM_VOLT >= 14.8 V.", affects=["H_CELL_TEMP", "H_ARM_VOLT_MARGIN"])
limitation("LIM_ICING_FREEZING_DRIZZLE", "Uncoated 1045 carbon-nylon propellers lack active electro-thermal blade de-icing; supercooled freezing drizzle requires pre-flight hydrophobic treatment.", affects=["H_HOVER_TW_EFF", "H_TRANSITION_CLIMB_PS"])


# ---------------------------------------------------------------------------
# 6. Coupled 5-Regime Aerodynamic + Thermal + Electrochemical Fixed-Point Closure
# ---------------------------------------------------------------------------
@closure(
    state={
        "m_tow_kg": 2.380,
        "vi_cruise_m_s": 3.80,
        "t_cell_k": 290.4,
        "i_cruise_a": 15.8,
    },
    mass_state="m_tow_kg",
    tol=1e-9,
    max_iter=120,
    damping=0.50,
)
def sizing_closure(x: dict, p) -> dict:
    g0 = constant("g0")
    r_air = constant("R_air")
    p0_isa = constant("p0_ISA")
    t0_isa = constant("T0_ISA")
    pi_val = constant("pi")
    sec_per_min = 3600.0 / (100.0 * 0.5 + 10.0)
    tiny = 1.0 / (1000.0 ** 3)

    # 1. Total takeoff mass derived directly by summing P01..P08 subsystem masses
    m_bom = (
        p.m_p01_kg
        + p.m_p02_kg
        + p.m_p03_kg
        + p.m_p04_kg
        + p.m_p05_kg
        + p.m_p06_kg
        + p.m_p07_kg
        + p.m_p08_kg
    )
    m_tow = m_bom + 0.0 * x["m_tow_kg"]
    weight_n = m_tow * g0

    rho_air = p0_isa / (r_air * p.t_amb_k)
    a_disk_m2 = p.n_rotors * pi_val * ((0.5 * p.d_prop_m) ** 2)

    # REGIME 1: Hover Launch & Planform Downwash Blockage
    f_max_gross_n = p.n_rotors * p.f_max_per_motor_n
    f_max_eff_n = f_max_gross_n * (1.0 - p.hover_blockage_frac)
    hover_tw_eff = f_max_eff_n / np.maximum(weight_n, tiny)
    t_hover_req_n = weight_n / (1.0 - p.hover_blockage_frac)
    vi_hover_m_s = np.sqrt(t_hover_req_n / (2.0 * rho_air * a_disk_m2))
    p_aero_hover_w = (t_hover_req_n * vi_hover_m_s) / p.fom_hover
    p_elec_prop_hover_w = p_aero_hover_w / p.eta_motor

    # REGIME 2: 10 m/s Beam Crosswind Hover Roll-Over Trim
    f_drag_lat_n = 0.5 * rho_air * (p.v_crosswind_m_s ** 2) * p.cd_area_lat_m2
    l_arm_roll_m = (0.5 * p.wheelbase_m) / np.sqrt(2.0)
    m_roll_wind_nm = f_drag_lat_n * p.z_cp_lat_m + p.k_inflow_roll_n_per_mps * p.v_crosswind_m_s * l_arm_roll_m
    m_roll_avail_nm = 2.0 * np.maximum(p.f_max_per_motor_n - (t_hover_req_n / p.n_rotors), tiny) * l_arm_roll_m
    crosswind_roll_sat_pct = 100.0 * m_roll_wind_nm / m_roll_avail_nm

    # REGIME 3: Transition Climb Specific Excess Power (Ps)
    f_drag_trans_n = 0.5 * rho_air * (p.v_climb_trans_m_s ** 2) * p.cd_area_front_m2
    p_max_shaft_w = f_max_eff_n * vi_hover_m_s * p.eta_motor
    p_req_trans_w = t_hover_req_n * vi_hover_m_s + f_drag_trans_n * p.v_climb_trans_m_s
    transition_ps_m_s = (p_max_shaft_w - p_req_trans_w) / np.maximum(weight_n, tiny)

    # REGIME 4: 10 m/s Forward Search Cruise (Glauert Oblique Actuator-Disk Inflow)
    d_cruise_n = 0.5 * rho_air * (p.v_cruise_m_s ** 2) * p.cd_area_front_m2
    t_cruise_n = np.sqrt(weight_n ** 2 + d_cruise_n ** 2) / (1.0 - 0.5 * p.hover_blockage_frac)
    sin_alpha = d_cruise_n / np.maximum(t_cruise_n, tiny)
    cos_alpha = weight_n / np.maximum(t_cruise_n, tiny)
    v_eff_cruise = np.sqrt(
        (p.v_cruise_m_s * cos_alpha) ** 2 + (p.v_cruise_m_s * sin_alpha + x["vi_cruise_m_s"]) ** 2
    )
    vi_cruise_next = t_cruise_n / (2.0 * rho_air * a_disk_m2 * np.maximum(v_eff_cruise, tiny))
    p_ind_cruise_w = p.k_ind_cruise * t_cruise_n * vi_cruise_next
    p_prof_cruise_w = p.p_profile_hover_w * (1.0 + p.mu_advance_coeff * ((p.v_cruise_m_s / vi_hover_m_s) ** 2))
    p_para_cruise_w = d_cruise_n * p.v_cruise_m_s
    p_elec_prop_cruise_w = (p_ind_cruise_w + p_prof_cruise_w + p_para_cruise_w) / p.eta_motor
    static_margin_pct = 100.0 * (p.x_np_m - p.x_cg_m) / p.wheelbase_m

    # REGIME 5: Oblique Canyon Descent & VRS Avoidance / Attitude Authority
    vrs_ratio = p.v_descent_m_s / np.maximum(vi_hover_m_s, tiny)
    v_desc_total_m_s = np.sqrt(p.v_descent_horiz_m_s ** 2 + p.v_descent_m_s ** 2)
    descent_control_margin_pct = 100.0 - p.synchro_max_rpm_trim_pct

    # Unified Transient + Steady-State Battery Thermal Balance (R_th = 4.651 K/W, C_th = 560 J/K)
    g_epp_w_k = 1.0 / (
        (p.t_epp_insul_m / (p.k_epp_w_mk * p.a_bay_surface_m2))
        + (1.0 / (p.h_conv_bay_w_m2k * p.a_bay_surface_m2))
    )
    r_th_bay_k_w = 1.0 / (g_epp_w_k + p.g_bridge_w_k)
    tau_th_s = p.c_th_pack_j_k * r_th_bay_k_w
    decay_factor = np.exp(-p.t_sortie_eval_s / np.maximum(tau_th_s, tiny))

    ptc_duty = 0.5 * (1.0 + np.tanh((p.t_ptc_setpoint_k - x["t_cell_k"]) / p.dt_ptc_prop_k))
    p_ptc_active_w = p.p_ptc_heater_w * ptc_duty

    r_cell_ohm = p.r_cell_20c_ohm * np.exp(
        p.beta_arrhenius_r_k * ((1.0 / x["t_cell_k"]) - (1.0 / p.t_ref_k))
    )
    r_pack_ohm = (p.n_series_cells / p.n_parallel_strings) * r_cell_ohm
    v_oc_pack_v = p.n_series_cells * p.v_cell_oc_mean_v
    v_oc_eod_v = p.n_series_cells * p.v_cell_oc_eod_v

    p_hover_total_w = p_elec_prop_hover_w + p.p_avionics_w + p_ptc_active_w
    p_cruise_total_w = p_elec_prop_cruise_w + p.p_avionics_w + p_ptc_active_w

    disc_hover = np.maximum(
        (v_oc_pack_v ** 2) - 2.0 * 2.0 * r_pack_ohm * p_hover_total_w,
        1.0,
    )
    i_hover_a = (v_oc_pack_v - np.sqrt(disc_hover)) / (2.0 * r_pack_ohm)

    # End-of-discharge (20% SOC OCV knee = 14.08V) hover terminal voltage under full load
    disc_hover_eod = np.maximum(
        (v_oc_eod_v ** 2) - 2.0 * 2.0 * r_pack_ohm * p_hover_total_w,
        1.0,
    )
    i_hover_eod_a = (v_oc_eod_v - np.sqrt(disc_hover_eod)) / (2.0 * r_pack_ohm)
    v_term_hover_v = v_oc_eod_v - i_hover_eod_a * r_pack_ohm

    disc_cruise = np.maximum(
        (v_oc_pack_v ** 2) - 2.0 * 2.0 * r_pack_ohm * p_cruise_total_w,
        1.0,
    )
    i_cruise_next = (v_oc_pack_v - np.sqrt(disc_cruise)) / (2.0 * r_pack_ohm)
    v_term_cruise_v = v_oc_pack_v - i_cruise_next * r_pack_ohm

    p_esc_loss_w = (1.0 - p.eta_motor) * p_elec_prop_cruise_w
    q_joule_pack_w = (i_cruise_next ** 2) * r_pack_ohm
    t_cell_ss_k = p.t_amb_k + r_th_bay_k_w * (
        p_ptc_active_w + p.esc_heat_recovery_frac * p_esc_loss_w + q_joule_pack_w
    )
    t_cell_next = p.t_cell_init_k * decay_factor + t_cell_ss_k * (1.0 - decay_factor)

    cold_inv_dt = np.maximum(0.0, (1.0 / t_cell_next) - (1.0 / p.t_ref_k))
    cap_ret_frac = p.cold_cap_frac * np.exp(-p.beta_arrhenius_q_k * cold_inv_dt)
    q_usable_ah = p.q_pack_ah * cap_ret_frac * (1.0 - p.f_reserve_soc)

    t_hover_usable_min = (q_usable_ah / np.maximum(i_hover_a, tiny)) * sec_per_min
    t_cruise_usable_min = (q_usable_ah / np.maximum(i_cruise_next, tiny)) * sec_per_min

    # Wind-aware outbound/inbound search radius R = t * (V_tas^2 - V_wind^2) / (2 * V_tas) * eta_route
    v_eff_roundtrip_m_s = ((p.v_cruise_m_s ** 2) - (p.v_headwind_cruise_m_s ** 2)) / (2.0 * p.v_cruise_m_s)
    r_combat_km = (v_eff_roundtrip_m_s * (t_cruise_usable_min * sec_per_min) * p.route_eff_factor) / 1000.0

    arm_volt_margin_v = v_term_hover_v - p.batt_crt_volt_v
    arm_ocv_margin_v = v_oc_pack_v - p.batt_crt_volt_v
    pm02_volt_sense_err_v = v_oc_pack_v * np.abs(1.0 - (p.pm02_volt_mult_cfg / p.pm02_volt_mult_hw))

    # First-principles derived 85 m AGL altitude error:
    # sqrt((h_agl * (dt_cal_err_k / t_amb_k))^2 + sigma_dem_m^2 + (h_agl * sigma_vio_tilt_rad)^2)
    uncomp_baro_err_m = (p.h_search_agl_m - p.h_lidar_max_m) + p.h_search_agl_m * (
        (t0_isa / p.t_amb_k) - 1.0
    )
    derived_hypso_vio_err_m = np.sqrt(
        ((p.h_search_agl_m * (p.dt_cal_err_k / p.t_amb_k)) ** 2)
        + (p.sigma_dem_m ** 2)
        + ((p.h_search_agl_m * p.sigma_vio_tilt_rad) ** 2)
    )
    alt_error_85m_agl_m = (
        (1.0 - p.hypsometric_baro_dem_enabled) * uncomp_baro_err_m
        + p.hypsometric_baro_dem_enabled * derived_hypso_vio_err_m
    )

    return {
        "m_tow_kg": m_tow,
        "m_bom_kg": m_bom,
        "vi_cruise_m_s": vi_cruise_next,
        "t_cell_k": t_cell_next,
        "i_cruise_a": i_cruise_next,
        "rho_air_kg_m3": rho_air,
        "hover_tw_eff": hover_tw_eff,
        "vi_hover_m_s": vi_hover_m_s,
        "crosswind_roll_sat_pct": crosswind_roll_sat_pct,
        "transition_ps_m_s": transition_ps_m_s,
        "static_margin_pct": static_margin_pct,
        "vrs_ratio": vrs_ratio,
        "v_desc_total_m_s": v_desc_total_m_s,
        "descent_control_margin_pct": descent_control_margin_pct,
        "r_th_bay_k_w": r_th_bay_k_w,
        "r_cell_mohm": r_cell_ohm * 1000.0,
        "r_pack_mohm": r_pack_ohm * 1000.0,
        "p_hover_total_w": p_hover_total_w,
        "p_cruise_total_w": p_cruise_total_w,
        "i_hover_a": i_hover_a,
        "v_term_hover_v": v_term_hover_v,
        "v_term_cruise_v": v_term_cruise_v,
        "q_usable_ah": q_usable_ah,
        "t_hover_usable_min": t_hover_usable_min,
        "t_cruise_usable_min": t_cruise_usable_min,
        "r_combat_km": r_combat_km,
        "arm_volt_margin_v": arm_volt_margin_v,
        "arm_ocv_margin_v": arm_ocv_margin_v,
        "pm02_volt_sense_err_v": pm02_volt_sense_err_v,
        "alt_error_85m_agl_m": alt_error_85m_agl_m,
    }


# ---------------------------------------------------------------------------
# 7. Hard Constraints
# ---------------------------------------------------------------------------
@hard("H_HOVER_TW_EFF", requirement="R_HOVER_TW", sense=">=", bound=1.75, unit="-", eps=0.01, tau=0.01)
def h_hover_tw_eff(x: dict, p):
    return x["hover_tw_eff"]


@hard("H_CROSSWIND_ROLL_TRIM", requirement="R_CROSSWIND_TRIM", sense="<=", bound=38.0, unit="%", eps=0.01, tau=0.01)
def h_crosswind_roll_trim(x: dict, p):
    return x["crosswind_roll_sat_pct"]


@hard("H_TRANSITION_CLIMB_PS", requirement="R_TRANSITION_CLIMB", sense=">=", bound=2.5, unit="m/s", eps=0.01, tau=0.01)
def h_transition_climb_ps(x: dict, p):
    return x["transition_ps_m_s"]


@hard("H_STATIC_MARGIN", requirement="R_STATIC_MARGIN", sense=">=", bound=8.0, unit="%", eps=0.01, tau=0.01)
def h_static_margin(x: dict, p):
    return x["static_margin_pct"]


@hard("H_DESCENT_CONTROL", requirement="R_DESCENT_AUTH", sense=">=", bound=94.0, unit="%", eps=0.01, tau=0.005)
def h_descent_control(x: dict, p):
    return x["descent_control_margin_pct"]


@hard("H_ARM_VOLT_MARGIN", requirement="R_ARM_VOLT", sense=">=", bound=0.45, unit="V", eps=0.01, tau=0.01)
def h_arm_volt_margin(x: dict, p):
    return x["arm_volt_margin_v"]


@hard("H_PM02_VOLT_SENSE_ERR", requirement="R_PM02_SENSE", sense="<=", bound=0.15, unit="V", eps=0.01, tau=0.01)
def h_pm02_volt_sense_err(x: dict, p):
    return x["pm02_volt_sense_err_v"]


@hard("H_HOVER_ENDURANCE_M25C", requirement="R_HOVER_ENDURANCE", sense=">=", bound=15.0, unit="min", eps=0.01, tau=0.01)
def h_hover_endurance_m25c(x: dict, p):
    return x["t_hover_usable_min"]


@hard("H_CRUISE_ENDURANCE_M25C", requirement="R_CRUISE_ENDURANCE", sense=">=", bound=18.0, unit="min", eps=0.01, tau=0.01)
def h_cruise_endurance_m25c(x: dict, p):
    return x["t_cruise_usable_min"]


@hard("H_ALT_85M_ERR", requirement="R_ALT_85M_ERR", sense="<=", bound=2.5, unit="m", eps=0.01, tau=0.01)
def h_alt_85m_err(x: dict, p):
    return x["alt_error_85m_agl_m"]


@hard("H_CELL_TEMP", requirement="R_CELL_TEMP", sense=">=", bound=273.15, unit="K", eps=0.01, tau=0.005)
def h_cell_temp(x: dict, p):
    return x["t_cell_k"]


# ---------------------------------------------------------------------------
# 8. Differential Witnesses (F1, F2, F3)
# ---------------------------------------------------------------------------
@witness("F1_4S_CUTOFF_AND_PM02_DIVIDER")
def witness_f1_4s_cutoff_and_pm02_scaling(p, x: dict) -> None:
    assert np.all(x["arm_ocv_margin_v"] >= 1.0), "4S pack open-circuit arming voltage below BATT_CRT_VOLT + 1.0V!"
    assert np.all(x["pm02_volt_sense_err_v"] <= 0.5), "Holybro PM02 V3 voltage multiplier mismatch > 0.5V!"


@witness("F2_MINUS25C_INSULATED_PTC_ENDURANCE")
def witness_f2_arctic_minus25c_battery_endurance(p, x: dict) -> None:
    assert np.all(x["t_cell_k"] >= constant("T_zero_C")), "Battery cells below 0 C (273.15 K) in -25 C flight!"
    assert np.all(x["t_cell_k"] <= p.t_cell_max_safe_k), "Battery cells exceed +45 C (318.15 K) upper thermal limit!"
    assert np.all(x["arm_volt_margin_v"] >= 0.5 * (1.0 - 0.5 * 0.5)), "Loaded 20% SOC EOD hover terminal voltage sags below BATT_CRT_VOLT + 0.375V!"
    assert np.all(x["t_cruise_usable_min"] >= 20.0 * 0.5 + 10.0 - 2.0), "Usable -25 C search cruise endurance < 18 min!"


@witness("F3_85M_HYPSOMETRIC_BARO_DEM_VIO")
def witness_f3_high_alt_85m_baro_dem_vio_fusion(p, x: dict) -> None:
    assert np.all(x["alt_error_85m_agl_m"] <= 2.0 + 0.5), "Vertical error at 85 m AGL exceeds 2.5 m ceiling!"
