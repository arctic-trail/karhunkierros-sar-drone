#!/usr/bin/env python3
"""
flight_simulator_6dof.py — First-Principles 6-DOF End-to-End Flight Dynamics,
Aerodynamics, Propulsion, Environmental & Mission Simulator for the Arctic Trail
Tier-3 Fast-SAR Jet & FIN-LAB-02 High-Speed Responder Family.

Simulates the complete end-to-end mission lifecycle at 100 Hz (4th-order Runge-Kutta
integration of the coupled 6-DOF rigid-body + variable-mass equations of motion):
  Phase 1: LAUNCH         — Detachable 3-wheel drop-trolley runway roll OR 3.5g catapult rail launch
  Phase 2: CLIMB          — Full-power turbojet TECS climb to transit altitude (120–400 m AGL)
  Phase 3: HIGH_SPEED_DASH— 270–420+ km/h turbojet dash under 3D wind shear, Dryden turbulence & icing
  Phase 4: LOITER_SEARCH  — Jet spool-down, folding nose electric prop deployment & 26–30 m/s SAR search
  Phase 5: PAYLOAD_DROP   — 25.5 m/s low pass, 5.0 kg survival capsule release (+CG/mass jump) &
                            simultaneous 3-DOF drogue-ballute capsule trajectory to ground impact CEP
  Phase 6: COLD_RELIGHT   — -30 °C FADEC kerostart turbine relight during electric flight & RTB climb
  Phase 7: RTB_CRUISE     — High-speed return-to-base transit & approach deceleration
  Phase 8: LANDING        — Dorsal recovery parachute + belly airbag impact OR belly-skid flare landing

Supported Airframe Configurations (plus custom live parameterization):
  1. VARIANT_H_EVO        — Iteration 1 Baseline (2.20 m constant-chord hybrid dorsal-jet + nose prop)
  2. FIN_LAB_02_FAST      — Initiative #3 High-Speed Corridor Responder (1.28 m 60° swept wing, 400+ km/h)
  3. VARIANT_H_TWINBOOM   — Iteration 2A Twin-Boom Inverted-V-Tail Hybrid Pusher/Jet
  4. VARIANT_H_CANARD     — Iteration 2B Forward-Canard Stall-Resistant Long-Range Cruiser
  5. VARIANT_H_STEALTH_VG — Iteration 3 Variable-Geometry Swing-Wing (22° Loiter <-> 50° Dash)
  6. FAST_CLIMBER_285     — Initiative #9 Cold-Rated 285 km/h COTS Fast-Climber & Soft-Net Responder
"""

from dataclasses import asdict, dataclass, field
import json
import math
from typing import Dict, List, Optional, Tuple

G_ACCEL = 9.80665          # m/s^2 standard gravity
R_AIR = 287.05287          # J/(kg*K) specific gas constant for dry air
GAMMA_AIR = 1.40           # ratio of specific heats for dry air


# ==============================================================================
# 1. AIRFRAME, PROPULSION & AERODYNAMIC CONFIGURATION DATACLASS
# ==============================================================================
@dataclass(frozen=True)
class AircraftConfiguration:
    config_id: str
    name: str
    description: str
    # Geometry & Inertia
    wingspan_m: float               # b (m)
    wing_area_m2: float             # S (m^2)
    mean_chord_m: float             # c_bar (m)
    sweep_deg: float                # quarter-chord sweep Lambda (deg)
    variable_sweep: bool            # True for Variant H-StealthVG (22 deg -> 50 deg)
    sweep_max_deg: float            # Max dash sweep if variable_sweep is True
    ixx_kg_m2: float                # Roll moment of inertia (kg*m^2)
    iyy_kg_m2: float                # Pitch moment of inertia (kg*m^2)
    izz_kg_m2: float                # Yaw moment of inertia (kg*m^2)
    # Mass breakdown
    empty_mass_kg: float            # Dry airframe + avionics + propulsion + battery mass (kg)
    fuel_mass_kg: float             # Initial Jet-A1 / kerosene fuel mass (kg)
    payload_mass_kg: float          # Droppable CG survival capsule / sensor pod mass (kg)
    battery_capacity_wh: float      # 6S Li-Ion/LiPo battery energy (Wh) for avionics & electric loiter
    # Longitudinal Aerodynamic Derivatives (per rad unless noted)
    cl0: float                      # Zero-alpha lift coefficient
    cl_alpha: float                 # Low-Mach lift-curve slope dCL/d(alpha) (1/rad)
    cl_q: float                     # Pitch-rate lift derivative dCL/d(q*c/2V)
    cl_de: float                    # Elevator lift effectiveness dCL/d(delta_e)
    cl_max_clean: float             # Clean 1g stall CL_max
    alpha_stall_deg: float          # Stall angle of attack (deg)
    cd0_clean: float                # Zero-lift parasitic drag coefficient
    oswald_e: float                 # Oswald span efficiency factor e
    cm0: float                      # Zero-alpha pitching moment coefficient about nominal CG
    cm_alpha: float                 # Longitudinal static stability dCm/d(alpha) (< 0 for stable)
    cm_q: float                     # Pitch damping derivative dCm/d(q*c/2V) (< 0)
    cm_de: float                    # Elevator control power dCm/d(delta_e) (< 0)
    static_margin_pct: float        # Nominal static margin (% MAC) at MTOW
    # Lateral-Directional Aerodynamic Derivatives (per rad)
    cy_beta: float                  # Sideforce due to sideslip dCY/d(beta) (< 0)
    cy_dr: float                    # Rudder/ruddervator sideforce derivative
    cl_beta: float                  # Dihedral effect dCl/d(beta) (< 0 for positive roll stability)
    cl_p: float                     # Roll damping derivative dCl/d(p*b/2V) (< 0)
    cl_r: float                     # Roll due to yaw rate dCl/d(r*b/2V)
    cl_da: float                    # Aileron roll control power dCl/d(delta_a)
    cn_beta: float                  # Weathercock directional stability dCn/d(beta) (> 0)
    cn_p: float                     # Adverse/proverse yaw due to roll rate
    cn_r: float                     # Yaw damping derivative dCn/d(r*b/2V) (< 0)
    cn_dr: float                    # Rudder/ruddervator yaw control power (< 0)
    # Propulsion & Recovery Parameters
    engine_name: str
    max_jet_thrust_sl_n: float      # Sea-level static max turbojet thrust (N)
    idle_jet_thrust_n: float        # Idle residual thrust (N)
    jet_z_offset_m: float           # Vertical offset of dorsal jet thrust line above CG (m, negative = above)
    m_dot_idle_g_s: float           # Idle fuel mass flow (g/s)
    c_slope_g_per_n_s: float        # Thrust-specific fuel flow slope (g/(N*s))
    has_electric_loiter: bool       # True if equipped with folding nose electric tractor prop
    max_electric_power_w: float     # Max shaft power of nose electric loiter motor (W)
    prop_efficiency: float          # Nose tractor propulsive efficiency in loiter
    recovery_chute_area_m2: float   # Dorsal recovery parachute reference area (m^2)
    recovery_chute_cd: float        # Parachute drag coefficient
    target_dash_mps: float          # Nominal mission dash true airspeed (m/s)
    target_loiter_mps: float        # Nominal mission loiter true airspeed (m/s)

    @property
    def mtow_kg(self) -> float:
        return round(self.empty_mass_kg + self.fuel_mass_kg + self.payload_mass_kg, 3)

    @property
    def aspect_ratio(self) -> float:
        return (self.wingspan_m ** 2) / self.wing_area_m2


# Catalog of standard configurations
AIRCRAFT_CATALOG: Dict[str, AircraftConfiguration] = {
    "VARIANT_H_EVO": AircraftConfiguration(
        config_id="VARIANT_H_EVO",
        name="Iteration 1 Baseline: Variant H-Evo (2.20 m Hybrid Dorsal-Jet + Electric Loiter)",
        description=(
            "14.95 kg MTOW mouldless carbon/XPS straight-tapered 16° wing (2.20 m span, 0.635 m²) "
            "with dorsal JetCat P100-RX-BL (100 N) for 200–270 km/h dash and 850 W folding nose "
            "electric tractor propeller for silent 26 m/s radar/LWIR loiter and 5.0 kg capsule drop."
        ),
        wingspan_m=2.20,
        wing_area_m2=0.635,
        mean_chord_m=0.289,
        sweep_deg=16.0,
        variable_sweep=False,
        sweep_max_deg=16.0,
        ixx_kg_m2=1.42,
        iyy_kg_m2=1.88,
        izz_kg_m2=2.95,
        empty_mass_kg=7.30,
        fuel_mass_kg=2.65,
        payload_mass_kg=5.00,
        battery_capacity_wh=222.0,  # 6S2P Molicel P45B (21.6V, 10.3Ah)
        cl0=0.22,
        cl_alpha=4.85,
        cl_q=7.2,
        cl_de=0.42,
        cl_max_clean=1.38,
        alpha_stall_deg=14.5,
        cd0_clean=0.025,
        oswald_e=0.84,
        cm0=0.035,
        cm_alpha=-0.68,
        cm_q=-12.5,
        cm_de=-1.18,
        static_margin_pct=14.0,
        cy_beta=-0.42,
        cy_dr=0.16,
        cl_beta=-0.085,
        cl_p=-0.48,
        cl_r=0.11,
        cl_da=0.22,
        cn_beta=0.115,
        cn_p=-0.035,
        cn_r=-0.165,
        cn_dr=-0.095,
        engine_name="JetCat P100-RX-BL (100 N, Germany) + 850 W Folding Nose Tractor",
        max_jet_thrust_sl_n=100.0,
        idle_jet_thrust_n=3.5,
        jet_z_offset_m=-0.085,
        m_dot_idle_g_s=1.067,
        c_slope_g_per_n_s=0.0413,
        has_electric_loiter=True,
        max_electric_power_w=850.0,
        prop_efficiency=0.74,
        recovery_chute_area_m2=5.20,
        recovery_chute_cd=1.42,
        target_dash_mps=68.0,       # 245 km/h efficient fast cruise / up to 78 m/s max dash
        target_loiter_mps=26.5,     # 95.4 km/h electric loiter
    ),
    "FIN_LAB_02_FAST": AircraftConfiguration(
        config_id="FIN_LAB_02_FAST",
        name="Initiative #3: FIN-LAB-02 High-Speed Corridor Responder (1.28 m 60° Swept, 400+ km/h)",
        description=(
            "11.20 kg MTOW low-drag 60° cranked-delta/swept high-speed responder (1.28 m span, 0.42 m²) "
            "powered by Spanish Xicoy X132 (132 N) or German JetCat P160-RXi-B (160 N) achieving "
            "360–425 km/h level dash at -30 °C with US$1,320 China-free COTS airframe+avionics BOM."
        ),
        wingspan_m=1.28,
        wing_area_m2=0.420,
        mean_chord_m=0.328,
        sweep_deg=60.0,
        variable_sweep=False,
        sweep_max_deg=60.0,
        ixx_kg_m2=0.68,
        iyy_kg_m2=1.35,
        izz_kg_m2=1.82,
        empty_mass_kg=6.70,
        fuel_mass_kg=3.00,
        payload_mass_kg=1.50,
        battery_capacity_wh=148.0,
        cl0=0.08,
        cl_alpha=3.45,
        cl_q=4.8,
        cl_de=0.36,
        cl_max_clean=1.12,
        alpha_stall_deg=18.5,       # Vortex-lift high-alpha delta stall
        cd0_clean=0.0185,
        oswald_e=0.78,
        cm0=0.020,
        cm_alpha=-0.52,
        cm_q=-8.4,
        cm_de=-0.92,
        static_margin_pct=11.5,
        cy_beta=-0.38,
        cy_dr=0.14,
        cl_beta=-0.095,
        cl_p=-0.38,
        cl_r=0.09,
        cl_da=0.19,
        cn_beta=0.105,
        cn_p=-0.025,
        cn_r=-0.145,
        cn_dr=-0.085,
        engine_name="Xicoy X132 (132 N, Spain) / JetCat P160-RXi-B (Germany)",
        max_jet_thrust_sl_n=132.0,
        idle_jet_thrust_n=4.2,
        jet_z_offset_m=-0.065,
        m_dot_idle_g_s=1.20,
        c_slope_g_per_n_s=0.0405,
        has_electric_loiter=False,
        max_electric_power_w=0.0,
        prop_efficiency=0.0,
        recovery_chute_area_m2=4.50,
        recovery_chute_cd=1.42,
        target_dash_mps=111.11,     # 400 km/h high-speed corridor dash
        target_loiter_mps=45.0,     # 162 km/h slowed turbine observation pass
    ),
    "VARIANT_H_TWINBOOM": AircraftConfiguration(
        config_id="VARIANT_H_TWINBOOM",
        name="Iteration 2A Trade Study: Variant H-TwinBoom (Inverted-V Tail, 2.30 m Span)",
        description=(
            "15.20 kg MTOW twin-tail-boom architecture with 110° inverted Lambda-tail shielding "
            "the dorsal JetCat P100-RX exhaust plume and providing an unobstructed 600 mm CG belly bay."
        ),
        wingspan_m=2.30,
        wing_area_m2=0.660,
        mean_chord_m=0.287,
        sweep_deg=12.0,
        variable_sweep=False,
        sweep_max_deg=12.0,
        ixx_kg_m2=1.58,
        iyy_kg_m2=2.25,
        izz_kg_m2=3.35,
        empty_mass_kg=7.60,
        fuel_mass_kg=2.60,
        payload_mass_kg=5.00,
        battery_capacity_wh=222.0,
        cl0=0.25,
        cl_alpha=5.05,
        cl_q=8.4,
        cl_de=0.46,
        cl_max_clean=1.44,
        alpha_stall_deg=15.0,
        cd0_clean=0.0275,
        oswald_e=0.86,
        cm0=0.040,
        cm_alpha=-0.82,
        cm_q=-14.8,
        cm_de=-1.32,
        static_margin_pct=16.5,
        cy_beta=-0.48,
        cy_dr=0.19,
        cl_beta=-0.092,
        cl_p=-0.52,
        cl_r=0.12,
        cl_da=0.23,
        cn_beta=0.135,
        cn_p=-0.038,
        cn_r=-0.195,
        cn_dr=-0.115,
        engine_name="JetCat P100-RX-BL (100 N) + 850 W Nose Electric Tractor",
        max_jet_thrust_sl_n=100.0,
        idle_jet_thrust_n=3.5,
        jet_z_offset_m=-0.055,
        m_dot_idle_g_s=1.067,
        c_slope_g_per_n_s=0.0413,
        has_electric_loiter=True,
        max_electric_power_w=850.0,
        prop_efficiency=0.75,
        recovery_chute_area_m2=5.40,
        recovery_chute_cd=1.42,
        target_dash_mps=65.0,
        target_loiter_mps=25.0,
    ),
    "VARIANT_H_CANARD": AircraftConfiguration(
        config_id="VARIANT_H_CANARD",
        name="Iteration 2B Trade Study: Variant H-Canard (Forward Lifting Canard + Rear Swept Wing)",
        description=(
            "14.80 kg MTOW tail-first canard configuration where the forward canard stalls 2.5° before "
            "the main rear wing, providing passive pitch-down stall protection during slow 25 m/s drops."
        ),
        wingspan_m=2.10,
        wing_area_m2=0.610,
        mean_chord_m=0.290,
        sweep_deg=24.0,
        variable_sweep=False,
        sweep_max_deg=24.0,
        ixx_kg_m2=1.35,
        iyy_kg_m2=2.05,
        izz_kg_m2=2.85,
        empty_mass_kg=7.20,
        fuel_mass_kg=2.60,
        payload_mass_kg=5.00,
        battery_capacity_wh=222.0,
        cl0=0.24,
        cl_alpha=4.72,
        cl_q=6.8,
        cl_de=0.48,
        cl_max_clean=1.35,
        alpha_stall_deg=13.5,       # Canard limits nose-up alpha before main wing stall
        cd0_clean=0.0235,
        oswald_e=0.81,
        cm0=0.030,
        cm_alpha=-0.58,
        cm_q=-11.2,
        cm_de=-1.25,
        static_margin_pct=12.0,
        cy_beta=-0.40,
        cy_dr=0.15,
        cl_beta=-0.080,
        cl_p=-0.45,
        cl_r=0.10,
        cl_da=0.21,
        cn_beta=0.108,
        cn_p=-0.030,
        cn_r=-0.155,
        cn_dr=-0.090,
        engine_name="JetCat P100-RX-BL (100 N) + 850 W Rear/Nose Electric Loiter",
        max_jet_thrust_sl_n=100.0,
        idle_jet_thrust_n=3.5,
        jet_z_offset_m=-0.060,
        m_dot_idle_g_s=1.067,
        c_slope_g_per_n_s=0.0413,
        has_electric_loiter=True,
        max_electric_power_w=850.0,
        prop_efficiency=0.74,
        recovery_chute_area_m2=5.20,
        recovery_chute_cd=1.42,
        target_dash_mps=72.0,
        target_loiter_mps=26.0,
    ),
    "VARIANT_H_STEALTH_VG": AircraftConfiguration(
        config_id="VARIANT_H_STEALTH_VG",
        name="Iteration 3 Trade Study: Variant H-StealthVG (Variable-Geometry Swing-Wing 22°–50°)",
        description=(
            "15.40 kg MTOW variable-sweep chined airframe that launches and loiters at Lambda=22° "
            "(2.20 m span, AR=7.9) and sweeps to Lambda=50° (1.52 m span, CD0=0.0195) for 370 km/h dash."
        ),
        wingspan_m=2.20,
        wing_area_m2=0.610,
        mean_chord_m=0.277,
        sweep_deg=22.0,
        variable_sweep=True,
        sweep_max_deg=50.0,
        ixx_kg_m2=1.48,
        iyy_kg_m2=1.96,
        izz_kg_m2=3.05,
        empty_mass_kg=7.75,         # +0.45 kg worm-gear pivot mechanism penalty
        fuel_mass_kg=2.65,
        payload_mass_kg=5.00,
        battery_capacity_wh=222.0,
        cl0=0.20,
        cl_alpha=4.75,
        cl_q=6.9,
        cl_de=0.40,
        cl_max_clean=1.36,
        alpha_stall_deg=14.8,
        cd0_clean=0.024,            # Drops to 0.0195 when swept to 50 deg
        oswald_e=0.83,
        cm0=0.032,
        cm_alpha=-0.64,
        cm_q=-11.8,
        cm_de=-1.15,
        static_margin_pct=13.5,
        cy_beta=-0.39,
        cy_dr=0.15,
        cl_beta=-0.088,
        cl_p=-0.46,
        cl_r=0.10,
        cl_da=0.21,
        cn_beta=0.110,
        cn_p=-0.032,
        cn_r=-0.160,
        cn_dr=-0.092,
        engine_name="Xicoy X132 (132 N, S-Duct) + 850 W Folding Nose Electric Tractor",
        max_jet_thrust_sl_n=126.7,  # 132 N minus 4% dorsal S-duct pressure recovery loss
        idle_jet_thrust_n=4.0,
        jet_z_offset_m=-0.040,
        m_dot_idle_g_s=1.20,
        c_slope_g_per_n_s=0.0415,
        has_electric_loiter=True,
        max_electric_power_w=850.0,
        prop_efficiency=0.74,
        recovery_chute_area_m2=5.20,
        recovery_chute_cd=1.42,
        target_dash_mps=102.8,      # 370 km/h swept dash
        target_loiter_mps=26.5,     # 95.4 km/h unswept electric loiter
    ),
    "FAST_CLIMBER_285": AircraftConfiguration(
        config_id="FAST_CLIMBER_285",
        name="Initiative #9: 285 km/h Cold-Rated Allied COTS Fast-Climber & Soft-Net Responder",
        description=(
            "3.80 kg MTOW high-thrust-to-weight electric cruciform/bullet fast-climber launched from "
            "a +15 °C heated shelter, dashing at 285 km/h (79.2 m/s) with 2.5x2.5 m Dyneema soft-net."
        ),
        wingspan_m=0.95,
        wing_area_m2=0.190,
        mean_chord_m=0.200,
        sweep_deg=28.0,
        variable_sweep=False,
        sweep_max_deg=28.0,
        ixx_kg_m2=0.14,
        iyy_kg_m2=0.28,
        izz_kg_m2=0.32,
        empty_mass_kg=2.95,
        fuel_mass_kg=0.0,
        payload_mass_kg=0.85,       # 2.5x2.5 m Dyneema soft-net + 1.2 m^2 recovery parachute assembly
        battery_capacity_wh=310.0,  # High-C pre-warmed +15 °C Molicel P45B pack
        cl0=0.12,
        cl_alpha=4.20,
        cl_q=5.5,
        cl_de=0.38,
        cl_max_clean=1.22,
        alpha_stall_deg=15.5,
        cd0_clean=0.022,
        oswald_e=0.80,
        cm0=0.018,
        cm_alpha=-0.60,
        cm_q=-9.5,
        cm_de=-1.05,
        static_margin_pct=13.0,
        cy_beta=-0.44,
        cy_dr=0.16,
        cl_beta=-0.075,
        cl_p=-0.42,
        cl_r=0.08,
        cl_da=0.24,
        cn_beta=0.120,
        cn_p=-0.020,
        cn_r=-0.150,
        cn_dr=-0.095,
        engine_name="Quad STM32G4/OptiMOS High-Speed Brushless Drive (62 N peak thrust)",
        max_jet_thrust_sl_n=62.0,
        idle_jet_thrust_n=0.0,
        jet_z_offset_m=0.0,
        m_dot_idle_g_s=0.0,
        c_slope_g_per_n_s=0.0,
        has_electric_loiter=True,
        max_electric_power_w=2400.0,
        prop_efficiency=0.78,
        recovery_chute_area_m2=1.80,
        recovery_chute_cd=1.40,
        target_dash_mps=79.2,       # 285 km/h fast-climber dash
        target_loiter_mps=34.0,     # 122 km/h terminal APN alignment
    ),
}


# ==============================================================================
# 2. ENVIRONMENTAL CONDITIONS (ISA + ARCTIC COLD + 3D WIND + DRYDEN + ICING)
# ==============================================================================
@dataclass(frozen=True)
class EnvironmentConditions:
    surface_temp_c: float = -25.0           # Ambient surface temperature (°C), e.g., +15 to -40 °C
    surface_pressure_pa: float = 101325.0   # Sea-level / ground barometric pressure (Pa)
    wind_speed_10m_mps: float = 8.0         # Mean wind speed at 10 m AGL (m/s)
    wind_dir_from_deg: float = 45.0         # Meteorological wind direction FROM (deg, 0=North, 90=East)
    wind_shear_exponent: float = 0.16       # Hellmann boundary-layer exponent over boreal forest/snow
    turbulence_intensity: str = "MODERATE"  # "NONE", "LIGHT", "MODERATE", "SEVERE"
    gust_amplitude_mps: float = 6.0         # Discrete (1 - cos) vertical/headwind gust peak (m/s)
    gust_start_s: float = 85.0              # Mission time when discrete gust hits (s)
    gust_duration_s: float = 6.0            # Duration of discrete (1 - cos) gust (s)
    icing_lwc_g_m3: float = 0.20            # Supercooled cloud Liquid Water Content (g/m^3, 0 = dry)
    deicer_enabled: bool = True             # True = 10W pitot + wing leading-edge de-icing active
    runway_friction_mu: float = 0.06        # Rolling friction coefficient (0.04 asphalt, 0.08 packed snow)


def compute_atmosphere(alt_agl_m: float, env: EnvironmentConditions) -> Dict[str, float]:
    """
    Computes exact temperature, static pressure, air density, speed of sound,
    and dynamic viscosity at altitude alt_agl_m for an Arctic or standard profile.
    """
    h = max(0.0, alt_agl_m)
    t0_k = env.surface_temp_c + 273.15
    # Tropospheric lapse rate (-0.0065 K/m standard, or shallow thermal inversion in polar night)
    lapse_k_per_m = -0.0045 if env.surface_temp_c <= -15.0 else -0.0065
    temp_k = max(205.0, t0_k + lapse_k_per_m * h)
    pressure_pa = env.surface_pressure_pa * ((temp_k / t0_k) ** (-G_ACCEL / (lapse_k_per_m * R_AIR)))
    rho_kg_m3 = pressure_pa / (R_AIR * temp_k)
    speed_of_sound_mps = math.sqrt(GAMMA_AIR * R_AIR * temp_k)
    # Sutherland's formula for dynamic viscosity mu (Pa*s)
    mu_pa_s = 1.458e-6 * (temp_k ** 1.5) / (temp_k + 110.4)
    return {
        "temp_k": temp_k,
        "temp_c": temp_k - 273.15,
        "pressure_pa": pressure_pa,
        "rho_kg_m3": rho_kg_m3,
        "speed_of_sound_mps": speed_of_sound_mps,
        "mu_pa_s": mu_pa_s,
    }


def compute_3d_wind_ned(
    t_s: float,
    alt_agl_m: float,
    env: EnvironmentConditions,
) -> Tuple[float, float, float]:
    """
    Computes the 3D wind velocity vector (W_N, W_E, W_D) in the NED inertial frame (m/s)
    combining boundary-layer wind shear, deterministic multi-frequency Dryden spectral
    turbulence, and a discrete (1 - cos) gust encounter.
    """
    h_eff = max(1.5, alt_agl_m)
    w_mag = env.wind_speed_10m_mps * ((h_eff / 10.0) ** env.wind_shear_exponent)
    # Wind blows FROM wind_dir_from_deg -> velocity vector points TOWARD (wind_dir + 180)
    dir_to_rad = math.radians(env.wind_dir_from_deg + 180.0)
    wn = w_mag * math.cos(dir_to_rad)
    we = w_mag * math.sin(dir_to_rad)
    wd = 0.0

    # Dryden-style multi-sinusoid continuous atmospheric turbulence
    turb_scale = {
        "NONE": 0.0,
        "LIGHT": 0.8,
        "MODERATE": 2.1,
        "SEVERE": 4.8,
    }.get(env.turbulence_intensity.upper(), 1.5)

    if turb_scale > 0.0:
        ug = turb_scale * (
            0.55 * math.sin(0.41 * t_s + 0.3)
            + 0.30 * math.sin(1.13 * t_s + 1.1)
            + 0.15 * math.cos(2.77 * t_s)
        )
        vg = turb_scale * (
            0.50 * math.cos(0.53 * t_s + 0.7)
            + 0.35 * math.sin(1.49 * t_s + 2.0)
            + 0.15 * math.sin(3.11 * t_s)
        )
        # Vertical turbulence diminishes near the ground (h < 15 m)
        vert_atten = min(1.0, h_eff / 15.0)
        wg = turb_scale * 0.65 * vert_atten * (
            0.60 * math.sin(0.89 * t_s + 0.4)
            + 0.40 * math.cos(2.31 * t_s + 1.5)
        )
        wn += ug
        we += vg
        wd += wg

    # Discrete (1 - cos) gust encounter (CS-23 / MIL-STD-1797)
    if env.gust_amplitude_mps != 0.0 and env.gust_start_s <= t_s <= (env.gust_start_s + env.gust_duration_s):
        tau = (t_s - env.gust_start_s) / max(0.1, env.gust_duration_s)
        gust_shape = 0.5 * (1.0 - math.cos(2.0 * math.pi * tau))
        # Gust hits both horizontal headwind component and vertical updraft (wd < 0 is upward in NED)
        wn -= 0.70 * env.gust_amplitude_mps * gust_shape * math.cos(dir_to_rad)
        we -= 0.70 * env.gust_amplitude_mps * gust_shape * math.sin(dir_to_rad)
        wd -= 0.50 * env.gust_amplitude_mps * gust_shape

    return wn, we, wd


# ==============================================================================
# 3. AERODYNAMICS, STABILITY DERIVATIVES & MODAL EIGENVALUE ANALYZER
# ==============================================================================
def compute_aerodynamic_coefficients(
    cfg: AircraftConfiguration,
    alpha_rad: float,
    beta_rad: float,
    p_rad_s: float,
    q_rad_s: float,
    r_rad_s: float,
    de_rad: float,
    da_rad: float,
    dr_rad: float,
    vtas_mps: float,
    mach: float,
    alt_agl_m: float,
    sweep_current_deg: float,
    ice_thickness_mm: float,
    trolley_attached: bool,
    nose_prop_deployed: bool,
    fuel_remaining_kg: float,
    payload_attached: bool,
) -> Dict[str, float]:
    """
    Computes full 6-DOF dimensionless aerodynamic force and moment coefficients
    (CL, CD, CY, Cl, Cm, Cn) including:
      - Prandtl-Glauert subsonic compressibility scaling up to M = 0.65
      - Variable-sweep aspect-ratio, lift-slope, CD0, and aerodynamic-center shifts
      - High-alpha post-stall Viterna-Corrigan model
      - Ground-effect induced-drag reduction (h/b)
      - Real-time ice accretion drag/stall degradation
      - Dynamic CG shift from fuel burn and belly payload release
    """
    v_safe = max(5.0, vtas_mps)
    # 1. Variable-sweep interpolation factor (0.0 at unswept, 1.0 at max dash sweep)
    if cfg.variable_sweep and cfg.sweep_max_deg > cfg.sweep_deg:
        sweep_frac = max(0.0, min(1.0, (sweep_current_deg - cfg.sweep_deg) / (cfg.sweep_max_deg - cfg.sweep_deg)))
    else:
        sweep_frac = 0.0

    # Effective wingspan & aspect ratio under sweep
    b_eff = cfg.wingspan_m * (1.0 - 0.31 * sweep_frac)
    ar_eff = (b_eff ** 2) / cfg.wing_area_m2

    # 2. Prandtl-Glauert compressibility & sweep scaling on CL_alpha
    pg_beta = math.sqrt(max(0.35, 1.0 - min(0.82, mach) ** 2))
    sweep_cos = math.cos(math.radians(sweep_current_deg))
    cl_alpha_eff = (cfg.cl_alpha * (sweep_cos ** 0.5) / pg_beta) * (
        math.cos(math.radians(cfg.sweep_deg)) ** -0.5
    )

    # 3. Ice accretion penalties on CL_max, stall angle, and CD0
    ice_cl_loss = min(0.38, 0.085 * ice_thickness_mm)
    ice_cd_add = 0.0045 * ice_thickness_mm + 0.0008 * (ice_thickness_mm ** 2)
    alpha_stall_rad = math.radians(max(8.5, cfg.alpha_stall_deg - 1.25 * ice_thickness_mm))
    cl_max_eff = max(0.65, cfg.cl_max_clean - ice_cl_loss - 0.14 * sweep_frac)

    # 4. Lift coefficient with smooth Viterna-Corrigan post-stall transition
    q_hat = (q_rad_s * cfg.mean_chord_m) / (2.0 * v_safe)
    p_hat = (p_rad_s * b_eff) / (2.0 * v_safe)
    r_hat = (r_rad_s * b_eff) / (2.0 * v_safe)

    cl_linear = cfg.cl0 + cl_alpha_eff * alpha_rad + cfg.cl_q * q_hat + cfg.cl_de * de_rad
    if abs(alpha_rad) <= alpha_stall_rad:
        cl = min(cl_max_eff, max(-0.85, cl_linear))
        stalled = False
    else:
        # Post-stall region: smooth Viterna-Corrigan blend into flat-plate sin(2*alpha)
        stalled = True
        sign_a = 1.0 if alpha_rad >= 0.0 else -1.0
        excess_a = abs(alpha_rad) - alpha_stall_rad
        blend = math.exp(-3.5 * excess_a)
        cl_flat_plate = 1.15 * math.sin(2.0 * alpha_rad)
        cl = sign_a * cl_max_eff * blend + (1.0 - blend) * cl_flat_plate + cfg.cl_de * de_rad * 0.5

    # 5. Drag coefficient (CD0 + wave + ice + trolley + prop + ground-effect induced drag)
    cd0_eff = cfg.cd0_clean * (1.0 - 0.185 * sweep_frac)
    cd_trolley = 0.0085 if trolley_attached else 0.0
    cd_prop = 0.0032 if (cfg.has_electric_loiter and nose_prop_deployed) else 0.0
    cd_wave = 0.08 * max(0.0, mach - 0.32) ** 3
    # Ground-effect factor on induced drag (McCormick / Wieselsberger formula)
    h_over_b = max(0.05, alt_agl_m) / b_eff
    ge_factor = ((16.0 * h_over_b) ** 2) / (1.0 + (16.0 * h_over_b) ** 2)
    k_ind = 1.0 / (math.pi * cfg.oswald_e * ar_eff)
    cd_post_stall = 1.85 * (math.sin(max(0.0, abs(alpha_rad) - alpha_stall_rad)) ** 2) if stalled else 0.0
    cd = (
        cd0_eff
        + ice_cd_add
        + cd_trolley
        + cd_prop
        + cd_wave
        + ge_factor * k_ind * (cl ** 2)
        + 0.18 * (beta_rad ** 2)
        + 0.035 * (de_rad ** 2)
        + cd_post_stall
    )

    # 6. Dynamic CG & Aerodynamic Center shift -> Pitching Moment Cm
    # Fuel tanks straddle CG with slight forward bias (+0.012 m); payload bay is at CG (+0.005 m)
    fuel_frac = fuel_remaining_kg / max(0.01, cfg.fuel_mass_kg) if cfg.fuel_mass_kg > 0 else 0.0
    delta_sm_fuel = -0.012 * (1.0 - fuel_frac)   # Slight aft shift as forward UAT/tank burns
    delta_sm_payload = 0.008 if not payload_attached else 0.0
    # Sweeping wings aft shifts AC rearward (+0.045 c_bar), increasing pitch stability |Cm_alpha|
    delta_sm_sweep = 0.045 * sweep_frac
    effective_static_margin = (cfg.static_margin_pct / 100.0) + delta_sm_fuel + delta_sm_payload + delta_sm_sweep
    cm_alpha_eff = -cl_alpha_eff * effective_static_margin

    cm = (
        cfg.cm0
        - 0.018 * sweep_frac
        + cm_alpha_eff * alpha_rad
        + cfg.cm_q * q_hat
        + cfg.cm_de * de_rad
    )

    # 7. Lateral-Directional Coefficients (CY, Cl, Cn)
    cy = cfg.cy_beta * beta_rad + cfg.cy_dr * dr_rad
    cl_mom = (
        cfg.cl_beta * (1.0 + 0.25 * sweep_frac) * beta_rad
        + cfg.cl_p * p_hat
        + cfg.cl_r * r_hat
        + cfg.cl_da * da_rad
        + 0.015 * dr_rad
    )
    cn_mom = (
        cfg.cn_beta * beta_rad
        + cfg.cn_p * p_hat
        + cfg.cn_r * r_hat
        + cfg.cn_dr * dr_rad
        - 0.012 * da_rad
    )

    return {
        "CL": cl,
        "CD": cd,
        "CY": cy,
        "Cl": cl_mom,
        "Cm": cm,
        "Cn": cn_mom,
        "L_over_D": cl / max(1e-4, cd),
        "static_margin_pct": round(effective_static_margin * 100.0, 2),
        "stalled": float(stalled),
        "b_eff_m": b_eff,
        "ar_eff": ar_eff,
    }


def compute_dynamic_stability_modes(
    cfg: AircraftConfiguration,
    vtas_mps: float,
    alt_agl_m: float,
    env: EnvironmentConditions,
) -> Dict[str, float]:
    """
    Computes the classical longitudinal (Short-Period, Phugoid) and lateral-directional
    (Dutch Roll, Roll Subsidence, Spiral) modal natural frequencies, damping ratios,
    time constants, and MIL-STD-1797 flying-qualities level at a given flight condition.
    """
    atm = compute_atmosphere(alt_agl_m, env)
    rho = atm["rho_kg_m3"]
    v = max(20.0, vtas_mps)
    q_dyn = 0.5 * rho * (v ** 2)
    mass = cfg.mtow_kg
    s = cfg.wing_area_m2
    c = cfg.mean_chord_m
    b = cfg.wingspan_m

    # Dimensional longitudinal stability derivatives
    z_alpha = -(q_dyn * s * (cfg.cl_alpha + cfg.cd0_clean)) / mass
    m_alpha = (q_dyn * s * c * cfg.cm_alpha) / cfg.iyy_kg_m2
    m_q = (q_dyn * s * (c ** 2) * cfg.cm_q) / (2.0 * v * cfg.iyy_kg_m2)

    # Short-period natural frequency & damping ratio
    wn_sp = math.sqrt(max(0.2, -m_alpha + (z_alpha / v) * m_q))
    zeta_sp = -(m_q + (z_alpha / v)) / (2.0 * wn_sp)
    zeta_sp = max(0.15, min(1.5, zeta_sp))

    # Phugoid natural frequency & damping ratio (Lanchester approximation + CD/CL damping)
    cl_trim = (mass * G_ACCEL) / max(1.0, q_dyn * s)
    ar = (b ** 2) / s
    cd_trim = cfg.cd0_clean + (cl_trim ** 2) / (math.pi * cfg.oswald_e * ar)
    wn_ph = G_ACCEL * math.sqrt(2.0) / v
    zeta_ph = cd_trim / (math.sqrt(2.0) * max(0.15, cl_trim))

    # Dutch Roll natural frequency & damping ratio
    y_beta = (q_dyn * s * cfg.cy_beta) / mass
    n_beta = (q_dyn * s * b * cfg.cn_beta) / cfg.izz_kg_m2
    n_r = (q_dyn * s * (b ** 2) * cfg.cn_r) / (2.0 * v * cfg.izz_kg_m2)
    wn_dr = math.sqrt(max(0.2, n_beta + (y_beta * n_r) / v))
    zeta_dr = -(n_r + (y_beta / v)) / (2.0 * wn_dr)

    # Roll subsidence time constant tau_roll (s)
    l_p = (q_dyn * s * (b ** 2) * cfg.cl_p) / (2.0 * v * cfg.ixx_kg_m2)
    tau_roll_s = -1.0 / min(-0.2, l_p)

    # Spiral stability parameter (Cl_beta * Cn_r - Cn_beta * Cl_r)
    spiral_param = cfg.cl_beta * cfg.cn_r - cfg.cn_beta * cfg.cl_r
    spiral_stable = spiral_param > 0.0

    # MIL-STD-1797 Category B/C Short-Period & Dutch-Roll Level 1 check
    level_1 = (0.30 <= zeta_sp <= 2.0) and (zeta_dr >= 0.08) and (wn_dr >= 0.4) and (tau_roll_s <= 1.4)

    return {
        "short_period_wn_rad_s": round(wn_sp, 3),
        "short_period_zeta": round(zeta_sp, 3),
        "phugoid_wn_rad_s": round(wn_ph, 3),
        "phugoid_period_s": round((2.0 * math.pi) / wn_ph, 2),
        "phugoid_zeta": round(zeta_ph, 3),
        "dutch_roll_wn_rad_s": round(wn_dr, 3),
        "dutch_roll_zeta": round(zeta_dr, 3),
        "roll_time_constant_s": round(tau_roll_s, 3),
        "spiral_stability_margin": round(spiral_param, 5),
        "spiral_stable": spiral_stable,
        "mil_std_1797_level": 1 if level_1 else 2,
    }


# ==============================================================================
# 4. END-TO-END 6-DOF MISSION SIMULATION ENGINE (8 PHASES, RK4 AT 100 HZ)
# ==============================================================================
@dataclass
class TelemetrySample:
    t_s: float
    phase: str
    x_north_m: float
    y_east_m: float
    alt_agl_m: float
    vtas_mps: float
    vtas_kmh: float
    vground_mps: float
    mach: float
    alpha_deg: float
    beta_deg: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    climb_rate_mps: float
    load_factor_g: float
    thrust_jet_n: float
    thrust_elec_n: float
    drag_n: float
    lift_n: float
    elevator_deg: float
    aileron_deg: float
    rudder_deg: float
    sweep_deg: float
    mass_kg: float
    fuel_kg: float
    battery_soc_pct: float
    ice_mm: float
    static_margin_pct: float
    gnss_denied_cep_m: float
    capsule_alt_m: float


@dataclass
class MissionSimulationResult:
    config_id: str
    config_name: str
    environment: Dict[str, float]
    launch_mode: str
    landing_mode: str
    mission_success: bool
    total_duration_s: float
    total_distance_km: float
    max_speed_mps: float
    max_speed_kmh: float
    max_mach: float
    max_altitude_m: float
    max_load_factor_g: float
    min_load_factor_g: float
    takeoff_roll_m: float
    takeoff_time_s: float
    loiter_power_avg_w: float
    capsule_drop_time_s: float
    capsule_landing_error_cep_m: float
    capsule_pitch_transient_deg: float
    cold_relight_time_s: float
    chute_snatch_force_n: float
    chute_snatch_g: float
    touchdown_vertical_speed_mps: float
    landing_rollout_m: float
    fuel_burned_kg: float
    fuel_remaining_kg: float
    battery_remaining_soc_pct: float
    max_ice_accretion_mm: float
    final_gnss_denied_cep_m: float
    stability_modes_cruise: Dict[str, float]
    phase_summary: List[Dict[str, object]]
    telemetry: List[TelemetrySample]


def run_end_to_end_6dof_mission(
    config_id: str = "VARIANT_H_EVO",
    env: Optional[EnvironmentConditions] = None,
    launch_mode: str = "DROP_TROLLEY",       # "DROP_TROLLEY" or "CATAPULT"
    landing_mode: str = "PARACHUTE_AIRBAG",  # "PARACHUTE_AIRBAG" or "BELLY_SKID"
    cruise_altitude_m: float = 180.0,
    dash_leg_seconds: float = 45.0,
    loiter_leg_seconds: float = 35.0,
    dt_s: float = 0.02,                      # 50 Hz RK4 integration step
    downsample_every: int = 25,              # Record telemetry at 2 Hz for compact plots
    custom_overrides: Optional[Dict[str, float]] = None,
) -> MissionSimulationResult:
    """
    Executes a complete end-to-end 8-phase 6-DOF flight dynamics simulation from
    launch (t=0) through climb, high-speed dash, electric loiter transition,
    survival capsule drop (plus 3-DOF capsule ballistics), cold-soak turbine relight,
    RTB cruise, and parachute/belly-skid landing.
    """
    if env is None:
        env = EnvironmentConditions()

    base_cfg = AIRCRAFT_CATALOG.get(config_id, AIRCRAFT_CATALOG["VARIANT_H_EVO"])
    if custom_overrides:
        cfg_dict = asdict(base_cfg)
        for k, v in custom_overrides.items():
            if k in cfg_dict:
                cfg_dict[k] = v
        cfg = AircraftConfiguration(**cfg_dict)
    else:
        cfg = base_cfg

    # Initial state variables
    t = 0.0
    x_n, y_e, alt_agl = 0.0, 0.0, 0.0
    # Body-frame velocities (u, v, w) in m/s
    u_b = 2.0 if launch_mode.upper() == "DROP_TROLLEY" else 8.0
    v_b = 0.0
    w_b = 0.0
    # Euler angles (phi, theta, psi) in rad and body angular rates (p, q, r) in rad/s
    phi = 0.0
    theta = math.radians(2.5 if launch_mode.upper() == "DROP_TROLLEY" else 12.0)
    psi = 0.0
    p_rate, q_rate, r_rate = 0.0, 0.0, 0.0

    # Subsystem & configuration states
    fuel_kg = cfg.fuel_mass_kg
    payload_attached = cfg.payload_mass_kg > 0.0
    trolley_attached = (launch_mode.upper() == "DROP_TROLLEY")
    nose_prop_deployed = not (cfg.max_jet_thrust_sl_n > 0.0 and cfg.fuel_mass_kg > 0.0)
    sweep_deg = cfg.sweep_deg
    ice_mm = 0.0

    # Cold-soaked battery capacity derating (Arrhenius / Peukert internal resistance model)
    temp_derate = max(0.62, min(1.0, 1.0 - 0.0085 * max(0.0, 15.0 - env.surface_temp_c)))
    usable_batt_wh = cfg.battery_capacity_wh * temp_derate
    batt_used_wh = 0.0

    # Propulsion dynamic state
    f_jet_actual = cfg.idle_jet_thrust_n
    f_elec_actual = 0.0
    chute_deployed = False
    chute_inflation_frac = 0.0
    relight_timer_s = 0.0

    # Dropped survival capsule 3-DOF trajectory state
    capsule_dropped = False
    cap_x, cap_y, cap_alt = 0.0, 0.0, 0.0
    cap_vn, cap_ve, cap_vd = 0.0, 0.0, 0.0
    target_cap_x, target_cap_y = 0.0, 0.0
    capsule_drop_time_s = 0.0
    capsule_cep_m = 0.0
    capsule_pitch_transient_deg = 0.0
    pitch_at_drop_deg = 0.0

    # Phase & metric trackers
    phase = "1_LAUNCH"
    phase_start_t = 0.0
    phase_summary: List[Dict[str, object]] = []
    telemetry: List[TelemetrySample] = []

    takeoff_roll_m = 0.0
    takeoff_time_s = 0.0
    liftoff_recorded = False
    cold_relight_time_s = 0.0
    chute_snatch_force_n = 0.0
    chute_snatch_g = 0.0
    touchdown_vz_mps = 0.0
    landing_touchdown_x = 0.0
    landing_rollout_m = 0.0
    loiter_power_samples: List[float] = []

    max_speed_mps = 0.0
    max_mach = 0.0
    max_alt_m = 0.0
    max_g = 1.0
    min_g = 1.0
    total_dist_m = 0.0
    gnss_cep_m = 1.5

    def transition_phase(new_phase: str, current_t: float, note: str) -> None:
        nonlocal phase, phase_start_t
        phase_summary.append({
            "phase": phase,
            "start_s": round(phase_start_t, 1),
            "end_s": round(current_t, 1),
            "duration_s": round(current_t - phase_start_t, 1),
            "alt_end_m": round(alt_agl, 1),
            "vtas_end_mps": round(math.sqrt(u_b**2 + v_b**2 + w_b**2), 1),
            "note": note,
        })
        phase = new_phase
        phase_start_t = current_t

    max_steps = int(420.0 / dt_s)
    for step in range(max_steps):
        atm = compute_atmosphere(alt_agl, env)
        rho = atm["rho_kg_m3"]
        a_sound = atm["speed_of_sound_mps"]
        wn, we, wd = compute_3d_wind_ned(t, alt_agl, env)

        # Current total vehicle mass
        current_payload_kg = cfg.payload_mass_kg if payload_attached else 0.0
        trolley_mass_kg = 1.15 if trolley_attached else 0.0
        mass_kg = cfg.empty_mass_kg + fuel_kg + current_payload_kg + trolley_mass_kg

        # Stall speed at current weight & air density
        v_stall = math.sqrt((2.0 * mass_kg * G_ACCEL) / (rho * cfg.wing_area_m2 * cfg.cl_max_clean))

        # Transform NED wind into body frame via Euler angles
        cp, sp = math.cos(phi), math.sin(phi)
        ct, st = math.cos(theta), math.sin(theta)
        cy_psi, sy_psi = math.cos(psi), math.sin(psi)

        # Inertial velocity in NED
        vn = (
            ct * cy_psi * u_b
            + (sp * st * cy_psi - cp * sy_psi) * v_b
            + (cp * st * cy_psi + sp * sy_psi) * w_b
        )
        ve = (
            ct * sy_psi * u_b
            + (sp * st * sy_psi + cp * cy_psi) * v_b
            + (cp * st * sy_psi - sp * cy_psi) * w_b
        )
        vd = -st * u_b + sp * ct * v_b + cp * ct * w_b
        climb_rate_mps = -vd
        vground_mps = math.sqrt(vn ** 2 + ve ** 2)

        # Air-relative velocity in NED -> projected to Body frame
        vr_n = vn - wn
        vr_e = ve - we
        vr_d = vd - wd
        u_air = ct * cy_psi * vr_n + ct * sy_psi * vr_e - st * vr_d
        v_air = (sp * st * cy_psi - cp * sy_psi) * vr_n + (sp * st * sy_psi + cp * cy_psi) * vr_e + sp * ct * vr_d
        w_air = (cp * st * cy_psi + sp * sy_psi) * vr_n + (cp * st * sy_psi - sp * cy_psi) * vr_e + cp * ct * vr_d

        vtas = math.sqrt(max(1.0, u_air ** 2 + v_air ** 2 + w_air ** 2))
        mach = vtas / a_sound
        alpha_rad = math.atan2(w_air, max(2.0, u_air))
        beta_rad = math.asin(max(-0.5, min(0.5, v_air / max(2.0, vtas))))

        # ----------------------------------------------------------------------
        # 8-PHASE AUTONOMOUS MISSION STATE MACHINE & TECS/L1 AUTOPILOT TARGETS
        # ----------------------------------------------------------------------
        cmd_vtas = cfg.target_dash_mps
        cmd_alt = cruise_altitude_m
        cmd_psi = 0.0
        jet_throttle = 0.0
        elec_throttle = 0.0

        if phase == "1_LAUNCH":
            jet_throttle = 1.0
            elec_throttle = 1.0 if cfg.fuel_mass_kg == 0.0 else 0.0
            cmd_vtas = 1.35 * v_stall
            cmd_alt = 25.0
            if alt_agl >= 2.0 and not liftoff_recorded:
                liftoff_recorded = True
                takeoff_roll_m = math.sqrt(x_n ** 2 + y_e ** 2)
                takeoff_time_s = t
                if trolley_attached:
                    trolley_attached = False
            if alt_agl >= 15.0 and vtas >= 1.25 * v_stall:
                transition_phase(
                    "2_CLIMB",
                    t,
                    f"{launch_mode} liftoff in {takeoff_roll_m:.1f} m ({takeoff_time_s:.1f} s); trolley released",
                )

        elif phase == "2_CLIMB":
            cmd_vtas = min(cfg.target_dash_mps, max(1.45 * v_stall, 52.0))
            thr_climb = max(0.40, min(1.0, 0.90 + 0.05 * (cmd_vtas - vtas)))
            jet_throttle = thr_climb if cfg.max_jet_thrust_sl_n > 0.0 and cfg.fuel_mass_kg > 0.0 else 0.0
            elec_throttle = thr_climb if cfg.fuel_mass_kg == 0.0 else 0.0
            cmd_alt = cruise_altitude_m
            if alt_agl >= 0.94 * cruise_altitude_m:
                transition_phase("3_HIGH_SPEED_DASH", t, f"Reached {alt_agl:.1f} m transit altitude")

        elif phase == "3_HIGH_SPEED_DASH":
            nose_prop_deployed = False
            cmd_vtas = cfg.target_dash_mps
            cmd_alt = cruise_altitude_m
            cmd_psi = 0.0
            # Closed-loop auto-throttle to track target_dash_mps up to physical thrust limit
            thr_cmd = max(0.20, min(1.0, 0.72 + 0.055 * (cmd_vtas - vtas)))
            jet_throttle = thr_cmd if cfg.max_jet_thrust_sl_n > 0.0 and cfg.fuel_mass_kg > 0.0 else 0.0
            elec_throttle = thr_cmd if cfg.fuel_mass_kg == 0.0 else 0.0
            if cfg.variable_sweep:
                sweep_deg = min(cfg.sweep_max_deg, sweep_deg + 14.0 * dt_s)
            if (t - phase_start_t) >= dash_leg_seconds:
                transition_phase(
                    "4_LOITER_SEARCH",
                    t,
                    f"Completed {vtas * 3.6:.0f} km/h corridor dash",
                )

        elif phase == "4_LOITER_SEARCH":
            if cfg.variable_sweep:
                sweep_deg = max(cfg.sweep_deg, sweep_deg - 14.0 * dt_s)
            if cfg.has_electric_loiter and cfg.fuel_mass_kg > 0.0:
                jet_throttle = 0.0   # Shut down / idle turbine for silent acoustic/LWIR search
                nose_prop_deployed = True
                cmd_vtas = cfg.target_loiter_mps
                elec_throttle = max(0.0, min(1.0, 0.42 + 0.09 * (cmd_vtas - vtas)))
            else:
                cmd_vtas = cfg.target_loiter_mps
                jet_throttle = max(0.12, min(0.65, 0.28 + 0.045 * (cmd_vtas - vtas)))
            cmd_alt = max(85.0, 0.55 * cruise_altitude_m)
            # Gentle S-turn search weave
            cmd_psi = math.radians(25.0 * math.sin(0.18 * (t - phase_start_t)))
            if (t - phase_start_t) >= loiter_leg_seconds:
                transition_phase("5_PAYLOAD_DROP", t, "Target acquired in LWIR/Starvis; commencing drop pass")

        elif phase == "5_PAYLOAD_DROP":
            cmd_alt = 65.0
            cmd_vtas = cfg.target_loiter_mps
            cmd_psi = 0.0
            if cfg.has_electric_loiter and cfg.fuel_mass_kg > 0.0:
                jet_throttle = 0.0
                nose_prop_deployed = True
                elec_throttle = max(0.0, min(1.0, 0.42 + 0.09 * (cmd_vtas - vtas)))
            else:
                jet_throttle = max(0.15, min(0.60, 0.28 + 0.045 * (cmd_vtas - vtas)))

            if payload_attached and (t - phase_start_t) >= 6.0:
                # Release the survival capsule / soft-net package!
                payload_attached = False
                capsule_dropped = True
                capsule_drop_time_s = t
                pitch_at_drop_deg = math.degrees(theta)
                cap_x, cap_y, cap_alt = x_n, y_e, alt_agl
                cap_vn, cap_ve, cap_vd = vn, ve, vd
                # Compute CCRP ballistic/drogue lead point using onboard wind-shear profile estimate
                # (leaves only unpredicted Dryden turbulence & gust perturbations as true CEP dispersion)
                dir_to_rad = math.radians(env.wind_dir_from_deg + 180.0)
                sim_cx, sim_cy, sim_calt = x_n, y_e, alt_agl
                sim_vx, sim_vy, sim_vz = vn, ve, vd
                cap_m = max(0.8, cfg.payload_mass_kg)
                sim_t = 0.0
                while sim_calt > 0.0 and sim_t < 30.0:
                    cda = 0.24 if sim_t >= 0.6 else 0.025
                    h_c = max(1.5, sim_calt)
                    w_prof = env.wind_speed_10m_mps * ((h_c / 10.0) ** env.wind_shear_exponent)
                    wn_mean = w_prof * math.cos(dir_to_rad)
                    we_mean = w_prof * math.sin(dir_to_rad)
                    rx, ry, rz = sim_vx - wn_mean, sim_vy - we_mean, sim_vz
                    vrel = math.sqrt(rx * rx + ry * ry + rz * rz + 1e-4)
                    fd = 0.5 * rho * vrel * vrel * cda
                    sim_vx += (-fd * (rx / vrel) / cap_m) * dt_s
                    sim_vy += (-fd * (ry / vrel) / cap_m) * dt_s
                    sim_vz += (G_ACCEL - fd * (rz / vrel) / cap_m) * dt_s
                    sim_cx += sim_vx * dt_s
                    sim_cy += sim_vy * dt_s
                    sim_calt = max(0.0, sim_calt - sim_vz * dt_s)
                    sim_t += dt_s
                target_cap_x = sim_cx
                target_cap_y = sim_cy

            if payload_attached is False:
                capsule_pitch_transient_deg = max(
                    capsule_pitch_transient_deg,
                    abs(math.degrees(theta) - pitch_at_drop_deg),
                )
            if (t - phase_start_t) >= 14.0:
                transition_phase(
                    "6_COLD_RELIGHT",
                    t,
                    f"Released {cfg.payload_mass_kg:.1f} kg payload at {alt_agl:.1f} m AGL",
                )

        elif phase == "6_COLD_RELIGHT":
            relight_timer_s += dt_s
            cmd_alt = cruise_altitude_m
            cmd_vtas = 0.85 * cfg.target_dash_mps
            cmd_psi = math.pi  # Turn 180 deg for Return-To-Base (RTB)
            # Cold-soak kerostart takes ~2.6 s at -25 C before turbine spools to climb thrust
            relight_delay = 2.6 if (cfg.has_electric_loiter and cfg.fuel_mass_kg > 0.0) else 0.4
            if relight_timer_s < relight_delay:
                jet_throttle = 0.08
                elec_throttle = 0.85 if cfg.has_electric_loiter else 0.0
            else:
                if cold_relight_time_s == 0.0:
                    cold_relight_time_s = relight_timer_s
                thr_relight = max(0.35, min(0.95, 0.75 + 0.045 * (cmd_vtas - vtas)))
                jet_throttle = thr_relight if cfg.max_jet_thrust_sl_n > 0.0 and cfg.fuel_mass_kg > 0.0 else 0.0
                elec_throttle = thr_relight if cfg.fuel_mass_kg == 0.0 else 0.0
                nose_prop_deployed = False
            if relight_timer_s >= 14.0:
                transition_phase(
                    "7_RTB_CRUISE",
                    t,
                    f"FADEC cold relight verified in {cold_relight_time_s:.2f} s; RTB climb complete",
                )

        elif phase == "7_RTB_CRUISE":
            cmd_alt = 60.0
            cmd_vtas = 0.78 * cfg.target_dash_mps
            thr_rtb = max(0.18, min(0.85, 0.58 + 0.045 * (cmd_vtas - vtas)))
            jet_throttle = thr_rtb if cfg.max_jet_thrust_sl_n > 0.0 and cfg.fuel_mass_kg > 0.0 else 0.0
            elec_throttle = thr_rtb if cfg.fuel_mass_kg == 0.0 else 0.0
            if cfg.variable_sweep:
                sweep_deg = min(cfg.sweep_max_deg, sweep_deg + 12.0 * dt_s)
            cmd_psi = math.pi
            if (t - phase_start_t) >= 28.0:
                transition_phase("8_LANDING", t, f"Arrived at recovery zone; initiating {landing_mode} recovery")

        elif phase == "8_LANDING":
            if cfg.variable_sweep:
                sweep_deg = max(cfg.sweep_deg, sweep_deg - 18.0 * dt_s)
            cmd_psi = math.pi
            if landing_mode.upper() == "PARACHUTE_AIRBAG":
                jet_throttle = 0.0
                elec_throttle = 0.0
                cmd_vtas = 1.20 * v_stall
                cmd_alt = 0.0
                if (t - phase_start_t) >= 2.5 and not chute_deployed:
                    chute_deployed = True
            else:
                # BELLY_SKID flare landing
                cmd_vtas = 1.22 * v_stall
                cmd_alt = 0.0
                if alt_agl > 6.0:
                    jet_throttle = 0.15 if cfg.fuel_mass_kg > 0.0 else 0.0
                    elec_throttle = 0.20 if cfg.has_electric_loiter else 0.0
                else:
                    jet_throttle = 0.0
                    elec_throttle = 0.0

        # ----------------------------------------------------------------------
        # UPDATE DROPPED CAPSULE 3-DOF BALLISTIC + DROGUE TRAJECTORY
        # ----------------------------------------------------------------------
        if capsule_dropped and cap_alt > 0.0:
            cap_mass = max(0.8, cfg.payload_mass_kg)
            # Static-line drogue ballute opens 0.6 s after release (Cd*A = 0.24 m^2)
            drogue_cda = 0.24 if (t - capsule_drop_time_s) >= 0.6 else 0.025
            wn_c, we_c, wd_c = compute_3d_wind_ned(t, cap_alt, env)
            rel_cn = cap_vn - wn_c
            rel_ce = cap_ve - we_c
            rel_cd = cap_vd - wd_c
            v_cap_rel = math.sqrt(rel_cn ** 2 + rel_ce ** 2 + rel_cd ** 2 + 1e-4)
            f_drag_cap = 0.5 * rho * (v_cap_rel ** 2) * drogue_cda
            cap_vn += (-f_drag_cap * (rel_cn / v_cap_rel) / cap_mass) * dt_s
            cap_ve += (-f_drag_cap * (rel_ce / v_cap_rel) / cap_mass) * dt_s
            cap_vd += (G_ACCEL - f_drag_cap * (rel_cd / v_cap_rel) / cap_mass) * dt_s
            cap_x += cap_vn * dt_s
            cap_y += cap_ve * dt_s
            cap_alt = max(0.0, cap_alt - cap_vd * dt_s)
            if cap_alt == 0.0 and capsule_cep_m == 0.0:
                capsule_cep_m = math.sqrt((cap_x - target_cap_x) ** 2 + (cap_y - target_cap_y) ** 2)

        # ----------------------------------------------------------------------
        # PROPULSION DYNAMICS (SPOOL LAG, COLD AIR DENSITY BOOST & RAM DRAG)
        # ----------------------------------------------------------------------
        if cfg.max_jet_thrust_sl_n > 0.0 and fuel_kg > 0.0:
            # Cold air density boosts mass flow slightly, while inlet momentum ram drag subtracts m_dot_air * V
            density_ratio = min(1.16, (rho / 1.225) ** 0.65)
            ram_loss_n = 0.065 * vtas * jet_throttle
            f_jet_target = (
                cfg.idle_jet_thrust_n
                + jet_throttle * (cfg.max_jet_thrust_sl_n * density_ratio - cfg.idle_jet_thrust_n)
                - ram_loss_n
            )
            f_jet_target = max(0.0, f_jet_target)
            tau_spool = 1.15 if f_jet_target >= f_jet_actual else 0.75
            f_jet_actual += ((f_jet_target - f_jet_actual) / tau_spool) * dt_s
            # Fuel burn (g/s -> kg)
            if jet_throttle > 0.01:
                m_dot_g_s = cfg.m_dot_idle_g_s + cfg.c_slope_g_per_n_s * f_jet_actual
                fuel_kg = max(0.0, fuel_kg - (m_dot_g_s / 1000.0) * dt_s)
            else:
                f_jet_actual = 0.0
        else:
            f_jet_actual = 0.0

        # Electric tractor / fast-climber propulsion
        p_elec_w = 0.0
        if cfg.has_electric_loiter and elec_throttle > 0.01 and batt_used_wh < usable_batt_wh:
            p_elec_w = elec_throttle * cfg.max_electric_power_w
            f_elec_target = (p_elec_w * cfg.prop_efficiency) / max(12.0, vtas)
            f_elec_actual += ((f_elec_target - f_elec_actual) / 0.15) * dt_s
            batt_used_wh += ((p_elec_w + 35.0) / 3600.0) * dt_s
        else:
            f_elec_actual = 0.0
            # Avionics + heated pitot baseline draw (38 W + 12 W if de-icer active)
            avionics_w = 38.0 + (12.0 if env.deicer_enabled else 0.0)
            batt_used_wh += (avionics_w / 3600.0) * dt_s
        # Record steady-state loiter shaft/electrical power requirement in Phase 4
        if phase == "4_LOITER_SEARCH" and (t - phase_start_t) >= 18.0:
            if cfg.has_electric_loiter and cfg.fuel_mass_kg > 0.0:
                loiter_power_samples.append(max(245.0, p_elec_w + 38.0))
            elif cfg.fuel_mass_kg == 0.0:
                loiter_power_samples.append(max(210.0, p_elec_w + 38.0))
            else:
                loiter_power_samples.append(max(850.0, f_jet_actual * vtas))

        # Ice accretion rate when flying in supercooled moisture (-25 C <= T <= 0 C)
        if -25.0 <= atm["temp_c"] <= 0.0 and env.icing_lwc_g_m3 > 0.0 and alt_agl > 10.0:
            accretion_mm_s = 0.0042 * env.icing_lwc_g_m3 * (vtas / 60.0)
            if env.deicer_enabled:
                accretion_mm_s *= 0.12  # Electro-thermal / piezo de-icing sheds 88% of rime ice
            ice_mm = min(6.0, ice_mm + accretion_mm_s * dt_s)

        # ----------------------------------------------------------------------
        # AUTOPILOT CONTROL TARGETS (CASCADED TECS PITCH & L1 HEADING/BANK)
        # ----------------------------------------------------------------------
        alt_err = cmd_alt - alt_agl

        if phase == "1_LAUNCH" and alt_agl < 1.0:
            if launch_mode.upper() == "CATAPULT":
                theta_cmd = math.radians(13.5)
            else:
                theta_cmd = math.radians(9.5) if vtas >= 1.12 * v_stall else math.radians(2.0)
        elif phase == "8_LANDING" and landing_mode.upper() == "BELLY_SKID":
            if alt_agl > 4.5:
                gamma_cmd = math.radians(-3.5)
                theta_cmd = gamma_cmd + alpha_rad
            else:
                theta_cmd = math.radians(5.5) - 0.12 * vd
        elif chute_deployed:
            theta_cmd = math.radians(-4.0)
        else:
            climb_cmd_mps = max(-10.0, min(14.0, 0.22 * alt_err))
            gamma_cmd = math.asin(max(-0.30, min(0.35, climb_cmd_mps / max(15.0, vtas))))
            stall_guard = min(0.0, 0.035 * (vtas - 1.18 * v_stall))
            theta_cmd = max(math.radians(-15.0), min(math.radians(24.0), gamma_cmd + alpha_rad + stall_guard))

        psi_err_outer = (cmd_psi - psi + math.pi) % (2.0 * math.pi) - math.pi
        phi_cmd = max(math.radians(-32.0), min(math.radians(32.0), 1.15 * psi_err_outer)) if alt_agl > 5.0 else 0.0

        # Track nominal control deflections at start of step for telemetry
        # Sign convention: cm_de < 0 (positive de = trailing-edge down = nose-down moment).
        # Therefore, when theta < theta_cmd (nose too low), we need de < 0 (trailing-edge up -> nose-up moment):
        # de = de_trim + K_theta * (theta - theta_cmd) + K_q * q_rate
        q_bar_step = 0.5 * rho * (vtas ** 2)
        q_scale_step = min(1.15, 520.0 / max(180.0, q_bar_step))
        de_trim_step = -(cfg.cm0 + cfg.cm_alpha * alpha_rad + (f_jet_actual * cfg.jet_z_offset_m) / max(25.0, q_bar_step * cfg.wing_area_m2 * cfg.mean_chord_m)) / cfg.cm_de
        de_rad = max(math.radians(-22.0), min(math.radians(22.0), de_trim_step + q_scale_step * (1.35 * (theta - theta_cmd) + 0.38 * q_rate)))
        da_rad = max(math.radians(-20.0), min(math.radians(20.0), q_scale_step * (1.10 * (phi_cmd - phi) - 0.24 * p_rate)))
        dr_rad = max(math.radians(-18.0), min(math.radians(18.0), q_scale_step * (0.95 * beta_rad + 0.28 * r_rate)))

        # ----------------------------------------------------------------------
        # 6-DOF FORCES, MOMENTS & RK4 INTEGRATION OF EQUATIONS OF MOTION
        # ----------------------------------------------------------------------
        def derivatives(state_vec: Tuple[float, ...]) -> Tuple[float, ...]:
            sx, sy, salt, su, sv, sw, sphi, stheta, spsi, sp_r, sq_r, sr_r = state_vec
            sphi = max(-1.2, min(1.2, sphi))
            stheta = max(-1.1, min(1.1, stheta))
            sp_r = max(-6.0, min(6.0, sp_r))
            sq_r = max(-6.0, min(6.0, sq_r))
            sr_r = max(-6.0, min(6.0, sr_r))

            c_phi, s_phi = math.cos(sphi), math.sin(sphi)
            c_th, s_th = math.cos(stheta), math.sin(stheta)
            c_ps, s_ps = math.cos(spsi), math.sin(spsi)

            # Inertial NED velocities
            s_vn = c_th * c_ps * su + (s_phi * s_th * c_ps - c_phi * s_ps) * sv + (c_phi * s_th * c_ps + s_phi * s_ps) * sw
            s_ve = c_th * s_ps * su + (s_phi * s_th * s_ps + c_phi * c_ps) * sv + (c_phi * s_th * s_ps - s_phi * c_ps) * sw
            s_vd = -s_th * su + s_phi * c_th * sv + c_phi * c_th * sw

            # Relative airspeed in body frame
            r_n, r_e, r_d = s_vn - wn, s_ve - we, s_vd - wd
            ua = c_th * c_ps * r_n + c_th * s_ps * r_e - s_th * r_d
            va = (s_phi * s_th * c_ps - c_phi * s_ps) * r_n + (s_phi * s_th * s_ps + c_phi * c_ps) * r_e + s_phi * c_th * r_d
            wa = (c_phi * s_th * c_ps + s_phi * s_ps) * r_n + (c_phi * s_th * s_ps - s_phi * c_ps) * r_e + c_phi * c_th * r_d

            v_air_tot = min(220.0, math.sqrt(max(1.0, ua ** 2 + va ** 2 + wa ** 2)))
            s_mach = v_air_tot / a_sound
            s_alpha = math.atan2(wa, max(2.0, ua))
            s_beta = math.asin(max(-0.5, min(0.5, va / max(2.0, v_air_tot))))

            q_bar = 0.5 * rho * (v_air_tot ** 2)
            # Dynamic-pressure scheduled SAS + attitude control inside RK4 sub-steps
            # Note: cn_dr < 0 (positive dr gives negative Cn), so for beta > 0 we want dr > 0 or dr < 0:
            # With cn_beta > 0, yaw damper against r_rate > 0 requires dr > 0 (since cn_dr < 0 -> delta_Cn < 0).
            q_scale = min(1.15, 520.0 / max(180.0, q_bar))
            jet_pitch_trim = (f_jet_actual * cfg.jet_z_offset_m) / max(25.0, q_bar * cfg.wing_area_m2 * cfg.mean_chord_m)
            s_de_trim = -(cfg.cm0 + cfg.cm_alpha * s_alpha + jet_pitch_trim) / cfg.cm_de
            s_de = max(math.radians(-22.0), min(math.radians(22.0), s_de_trim + q_scale * (1.35 * (stheta - theta_cmd) + 0.38 * sq_r)))
            s_da = max(math.radians(-20.0), min(math.radians(20.0), q_scale * (1.10 * (phi_cmd - sphi) - 0.24 * sp_r)))
            s_dr = max(math.radians(-18.0), min(math.radians(18.0), q_scale * (0.95 * s_beta + 0.28 * sr_r)))

            aero = compute_aerodynamic_coefficients(
                cfg=cfg,
                alpha_rad=s_alpha,
                beta_rad=s_beta,
                p_rad_s=sp_r,
                q_rad_s=sq_r,
                r_rad_s=sr_r,
                de_rad=s_de,
                da_rad=s_da,
                dr_rad=s_dr,
                vtas_mps=v_air_tot,
                mach=s_mach,
                alt_agl_m=max(0.0, salt),
                sweep_current_deg=sweep_deg,
                ice_thickness_mm=ice_mm,
                trolley_attached=trolley_attached,
                nose_prop_deployed=nose_prop_deployed,
                fuel_remaining_kg=fuel_kg,
                payload_attached=payload_attached,
            )

            lift_f = q_bar * cfg.wing_area_m2 * aero["CL"]
            drag_f = q_bar * cfg.wing_area_m2 * aero["CD"]
            side_f = q_bar * cfg.wing_area_m2 * aero["CY"]

            # Rotate stability-axis (Lift, Drag) into Body-axis (X_aero, Z_aero)
            ca, sa = math.cos(s_alpha), math.sin(s_alpha)
            fx_aero = -drag_f * ca + lift_f * sa
            fz_aero = -drag_f * sa - lift_f * ca
            fy_aero = side_f

            # Total propulsion + catapult + parachute forces in body frame
            fx_prop = f_jet_actual + f_elec_actual
            if phase == "1_LAUNCH" and launch_mode.upper() == "CATAPULT" and t < 0.60:
                fx_prop += 3.5 * mass_kg * G_ACCEL

            # Dorsal recovery parachute force when deployed
            if chute_deployed:
                chute_cda = cfg.recovery_chute_area_m2 * cfg.recovery_chute_cd * chute_inflation_frac
                f_chute = 0.5 * rho * (v_air_tot ** 2) * chute_cda
                fx_aero -= f_chute * (ua / v_air_tot)
                fy_aero -= f_chute * (va / v_air_tot)
                fz_aero -= f_chute * (wa / v_air_tot)

            # Ground contact normal force & rolling/skid friction when salt <= 0
            fx_gnd, fz_gnd = 0.0, 0.0
            if salt <= 0.05 and (phase == "1_LAUNCH" or phase == "8_LANDING"):
                weight_minus_lift = max(0.0, mass_kg * G_ACCEL * c_th + fz_aero)
                fz_gnd = -weight_minus_lift
                mu_eff = env.runway_friction_mu if trolley_attached else 0.28
                if su > 0.2:
                    fx_gnd = -mu_eff * weight_minus_lift

            fx_tot = fx_aero + fx_prop + fx_gnd - mass_kg * G_ACCEL * s_th
            fy_tot = fy_aero + mass_kg * G_ACCEL * c_th * s_phi
            fz_tot = fz_aero + fz_gnd + mass_kg * G_ACCEL * c_th * c_phi

            du = (fx_tot / mass_kg) - sq_r * sw + sr_r * sv
            dv = (fy_tot / mass_kg) - sr_r * su + sp_r * sw
            dw = (fz_tot / mass_kg) - sp_r * sv + sq_r * su

            # Body moments (L, M, N) including dorsal turbojet pitch moment (-F_jet * z_jet)
            l_mom = q_bar * cfg.wing_area_m2 * aero["b_eff_m"] * aero["Cl"]
            m_mom = (
                q_bar * cfg.wing_area_m2 * cfg.mean_chord_m * aero["Cm"]
                + f_jet_actual * cfg.jet_z_offset_m
            )
            n_mom = q_bar * cfg.wing_area_m2 * aero["b_eff_m"] * aero["Cn"]

            if chute_deployed:
                # Parachute riser pendulum damping scaled to vehicle inertia
                l_mom = -8.0 * cfg.ixx_kg_m2 * sphi - 4.5 * cfg.ixx_kg_m2 * sp_r
                m_mom = -9.0 * cfg.iyy_kg_m2 * (stheta + math.radians(4.0)) - 5.0 * cfg.iyy_kg_m2 * sq_r
                n_mom = -4.0 * cfg.izz_kg_m2 * sr_r

            dp = max(-25.0, min(25.0, (l_mom - (cfg.izz_kg_m2 - cfg.iyy_kg_m2) * sq_r * sr_r) / cfg.ixx_kg_m2))
            dq = max(-25.0, min(25.0, (m_mom - (cfg.ixx_kg_m2 - cfg.izz_kg_m2) * sp_r * sr_r) / cfg.iyy_kg_m2))
            dr = max(-25.0, min(25.0, (n_mom - (cfg.iyy_kg_m2 - cfg.ixx_kg_m2) * sp_r * sq_r) / cfg.izz_kg_m2))

            # Euler kinematics
            t_th = math.tan(max(-1.2, min(1.2, stheta)))
            sec_th = 1.0 / max(0.25, c_th)
            dphi = sp_r + (s_phi * sq_r + c_phi * sr_r) * t_th
            dtheta = c_phi * sq_r - s_phi * sr_r
            dpsi = (s_phi * sq_r + c_phi * sr_r) * sec_th

            dalt = -s_vd
            return (s_vn, s_ve, dalt, du, dv, dw, dphi, dtheta, dpsi, dp, dq, dr)

        # Parachute inflation ramp (1.1 s reefed canopy opening to prevent excessive snatch G)
        if chute_deployed and chute_inflation_frac < 1.0:
            chute_inflation_frac = min(1.0, chute_inflation_frac + (dt_s / 1.10))
            f_snatch_now = (
                0.5
                * rho
                * (vtas ** 2)
                * cfg.recovery_chute_area_m2
                * cfg.recovery_chute_cd
                * chute_inflation_frac
            )
            if f_snatch_now > chute_snatch_force_n:
                chute_snatch_force_n = f_snatch_now
                chute_snatch_g = f_snatch_now / (mass_kg * G_ACCEL)

        # 4th-Order Runge-Kutta (RK4) integration step
        y0 = (x_n, y_e, alt_agl, u_b, v_b, w_b, phi, theta, psi, p_rate, q_rate, r_rate)
        k1 = derivatives(y0)
        y1 = tuple(y0[i] + 0.5 * dt_s * k1[i] for i in range(12))
        k2 = derivatives(y1)
        y2 = tuple(y0[i] + 0.5 * dt_s * k2[i] for i in range(12))
        k3 = derivatives(y2)
        y3 = tuple(y0[i] + dt_s * k3[i] for i in range(12))
        k4 = derivatives(y3)

        yn = tuple(
            y0[i] + (dt_s / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])
            for i in range(12)
        )
        x_n, y_e, alt_agl, u_b, v_b, w_b, phi, theta, psi, p_rate, q_rate, r_rate = yn

        # Ground contact clamping & landing completion detection
        if alt_agl <= 0.0:
            if phase == "8_LANDING" and touchdown_vz_mps == 0.0:
                touchdown_vz_mps = abs(k1[2])
                landing_touchdown_x = math.sqrt(x_n ** 2 + y_e ** 2)
            alt_agl = 0.0
            phi = 0.0
            p_rate = 0.0
            if phase == "1_LAUNCH":
                # 3-wheel drop-trolley / catapult rail holds minimum nose-up incidence on the ground
                min_gnd_theta = math.radians(2.5 if launch_mode.upper() == "DROP_TROLLEY" else 11.0)
                if theta < min_gnd_theta:
                    theta = min_gnd_theta
                    q_rate = max(0.0, q_rate)
                # Prevent downward inertial velocity into the runway surface
                w_max_gnd = u_b * math.tan(theta)
                if w_b > w_max_gnd:
                    w_b = w_max_gnd
            elif phase == "8_LANDING":
                theta = max(0.0, theta * 0.90)
                q_rate = 0.0
                w_b = 0.0
                if landing_mode.upper() == "PARACHUTE_AIRBAG":
                    # Airbag stroke absorbs vertical impact; aircraft stops immediately on canopy release
                    u_b = max(0.0, u_b - 18.0 * dt_s)
                else:
                    # Belly-skid snow slide-out deceleration
                    u_b = max(0.0, u_b - 4.2 * dt_s)
                    landing_rollout_m = abs(math.sqrt(x_n ** 2 + y_e ** 2) - landing_touchdown_x)
            else:
                if w_b > 0.0:
                    w_b = 0.0

        # Evaluate current aero for telemetry & G-load tracking
        aero_now = compute_aerodynamic_coefficients(
            cfg=cfg,
            alpha_rad=alpha_rad,
            beta_rad=beta_rad,
            p_rad_s=p_rate,
            q_rad_s=q_rate,
            r_rad_s=r_rate,
            de_rad=de_rad,
            da_rad=da_rad,
            dr_rad=dr_rad,
            vtas_mps=vtas,
            mach=mach,
            alt_agl_m=alt_agl,
            sweep_current_deg=sweep_deg,
            ice_thickness_mm=ice_mm,
            trolley_attached=trolley_attached,
            nose_prop_deployed=nose_prop_deployed,
            fuel_remaining_kg=fuel_kg,
            payload_attached=payload_attached,
        )
        q_bar_now = 0.5 * rho * (vtas ** 2)
        lift_now_n = q_bar_now * cfg.wing_area_m2 * aero_now["CL"]
        drag_now_n = q_bar_now * cfg.wing_area_m2 * aero_now["CD"]
        load_factor_g = (lift_now_n / (mass_kg * G_ACCEL)) if alt_agl > 0.1 else 1.0

        # Track extrema and distance
        total_dist_m += vground_mps * dt_s
        max_speed_mps = max(max_speed_mps, vtas)
        max_mach = max(max_mach, mach)
        max_alt_m = max(max_alt_m, alt_agl)
        max_g = max(max_g, load_factor_g)
        min_g = min(min_g, load_factor_g)

        # GNSS-denied navigation drift model (FIN-LAB-03 heated pitot + baro-DEM + LWIR odometry)
        gnss_cep_m = min(24.5, 1.5 + 0.00058 * total_dist_m + (1.8 if not env.deicer_enabled else 0.0))

        batt_soc_pct = max(0.0, 100.0 * (1.0 - batt_used_wh / max(1.0, usable_batt_wh)))

        if step % downsample_every == 0:
            telemetry.append(
                TelemetrySample(
                    t_s=round(t, 2),
                    phase=phase,
                    x_north_m=round(x_n, 1),
                    y_east_m=round(y_e, 1),
                    alt_agl_m=round(alt_agl, 2),
                    vtas_mps=round(vtas, 2),
                    vtas_kmh=round(vtas * 3.6, 1),
                    vground_mps=round(vground_mps, 2),
                    mach=round(mach, 3),
                    alpha_deg=round(math.degrees(alpha_rad), 2),
                    beta_deg=round(math.degrees(beta_rad), 2),
                    roll_deg=round(math.degrees(phi), 2),
                    pitch_deg=round(math.degrees(theta), 2),
                    yaw_deg=round(math.degrees(psi) % 360.0, 1),
                    climb_rate_mps=round(climb_rate_mps, 2),
                    load_factor_g=round(load_factor_g, 2),
                    thrust_jet_n=round(f_jet_actual, 2),
                    thrust_elec_n=round(f_elec_actual, 2),
                    drag_n=round(drag_now_n, 2),
                    lift_n=round(lift_now_n, 2),
                    elevator_deg=round(math.degrees(de_rad), 2),
                    aileron_deg=round(math.degrees(da_rad), 2),
                    rudder_deg=round(math.degrees(dr_rad), 2),
                    sweep_deg=round(sweep_deg, 1),
                    mass_kg=round(mass_kg, 2),
                    fuel_kg=round(fuel_kg, 3),
                    battery_soc_pct=round(batt_soc_pct, 1),
                    ice_mm=round(ice_mm, 3),
                    static_margin_pct=aero_now["static_margin_pct"],
                    gnss_denied_cep_m=round(gnss_cep_m, 2),
                    capsule_alt_m=round(cap_alt, 2),
                )
            )

        t += dt_s
        if phase == "8_LANDING" and alt_agl == 0.0 and u_b <= 0.5:
            phase_summary.append({
                "phase": phase,
                "start_s": round(phase_start_t, 1),
                "end_s": round(t, 1),
                "duration_s": round(t - phase_start_t, 1),
                "alt_end_m": 0.0,
                "vtas_end_mps": 0.0,
                "note": f"Touchdown at Vz={touchdown_vz_mps:.2f} m/s ({landing_mode}); full stop",
            })
            break

    # Ensure capsule finished falling if aircraft landed first
    while capsule_dropped and cap_alt > 0.0:
        cap_alt = max(0.0, cap_alt - 6.5 * dt_s)
        cap_x += wn * dt_s
        cap_y += we * dt_s
        if cap_alt == 0.0 and capsule_cep_m == 0.0:
            capsule_cep_m = math.sqrt((cap_x - target_cap_x) ** 2 + (cap_y - target_cap_y) ** 2)

    stability_cruise = compute_dynamic_stability_modes(
        cfg=cfg,
        vtas_mps=cfg.target_dash_mps,
        alt_agl_m=cruise_altitude_m,
        env=env,
    )

    loiter_p_avg = (
        sum(loiter_power_samples) / len(loiter_power_samples)
        if loiter_power_samples
        else 0.0
    )

    return MissionSimulationResult(
        config_id=cfg.config_id,
        config_name=cfg.name,
        environment=asdict(env),
        launch_mode=launch_mode.upper(),
        landing_mode=landing_mode.upper(),
        mission_success=(alt_agl == 0.0 and phase == "8_LANDING"),
        total_duration_s=round(t, 1),
        total_distance_km=round(total_dist_m / 1000.0, 2),
        max_speed_mps=round(max_speed_mps, 1),
        max_speed_kmh=round(max_speed_mps * 3.6, 1),
        max_mach=round(max_mach, 3),
        max_altitude_m=round(max_alt_m, 1),
        max_load_factor_g=round(max_g, 2),
        min_load_factor_g=round(min_g, 2),
        takeoff_roll_m=round(takeoff_roll_m, 1),
        takeoff_time_s=round(takeoff_time_s, 1),
        loiter_power_avg_w=round(loiter_p_avg, 1),
        capsule_drop_time_s=round(capsule_drop_time_s, 1),
        capsule_landing_error_cep_m=round(capsule_cep_m, 2),
        capsule_pitch_transient_deg=round(capsule_pitch_transient_deg, 2),
        cold_relight_time_s=round(cold_relight_time_s, 2),
        chute_snatch_force_n=round(chute_snatch_force_n, 1),
        chute_snatch_g=round(chute_snatch_g, 2),
        touchdown_vertical_speed_mps=round(max(0.35, touchdown_vz_mps), 2),
        landing_rollout_m=round(landing_rollout_m, 1),
        fuel_burned_kg=round(cfg.fuel_mass_kg - fuel_kg, 3),
        fuel_remaining_kg=round(fuel_kg, 3),
        battery_remaining_soc_pct=round(max(0.0, 100.0 * (1.0 - batt_used_wh / max(1.0, usable_batt_wh))), 1),
        max_ice_accretion_mm=round(ice_mm, 3),
        final_gnss_denied_cep_m=round(gnss_cep_m, 2),
        stability_modes_cruise=stability_cruise,
        phase_summary=phase_summary,
        telemetry=telemetry,
    )


def compare_all_configurations(env: Optional[EnvironmentConditions] = None) -> List[Dict[str, object]]:
    """
    Runs all 6 configurations in AIRCRAFT_CATALOG end-to-end under identical
    environmental conditions and returns a comparative summary table.
    """
    if env is None:
        env = EnvironmentConditions(
            surface_temp_c=-30.0,
            wind_speed_10m_mps=10.0,
            wind_dir_from_deg=45.0,
            turbulence_intensity="MODERATE",
            gust_amplitude_mps=6.5,
            icing_lwc_g_m3=0.25,
            deicer_enabled=True,
        )
    summary_rows: List[Dict[str, object]] = []
    for cid in AIRCRAFT_CATALOG:
        launch = "CATAPULT" if cid in ("FIN_LAB_02_FAST", "FAST_CLIMBER_285") else "DROP_TROLLEY"
        res = run_end_to_end_6dof_mission(
            config_id=cid,
            env=env,
            launch_mode=launch,
            landing_mode="PARACHUTE_AIRBAG",
        )
        summary_rows.append({
            "config_id": cid,
            "name": res.config_name,
            "mtow_kg": AIRCRAFT_CATALOG[cid].mtow_kg,
            "launch_mode": res.launch_mode,
            "takeoff_roll_m": res.takeoff_roll_m,
            "max_speed_kmh": res.max_speed_kmh,
            "max_mach": res.max_mach,
            "loiter_power_w": res.loiter_power_avg_w,
            "capsule_cep_m": res.capsule_landing_error_cep_m,
            "touchdown_vz_mps": res.touchdown_vertical_speed_mps,
            "short_period_zeta": res.stability_modes_cruise["short_period_zeta"],
            "dutch_roll_zeta": res.stability_modes_cruise["dutch_roll_zeta"],
            "mil_std_level": res.stability_modes_cruise["mil_std_1797_level"],
            "mission_success": res.mission_success,
        })
    return summary_rows


def main() -> None:
    print("=" * 105)
    print("ARCTIC TRAIL TIER-3 FAST-SAR JET — 6-DOF END-TO-END FLIGHT DYNAMICS SIMULATOR (-30 °C ARCTIC STORM)")
    print("=" * 105)
    arctic_storm = EnvironmentConditions(
        surface_temp_c=-30.0,
        wind_speed_10m_mps=12.0,
        wind_dir_from_deg=45.0,
        turbulence_intensity="MODERATE",
        gust_amplitude_mps=7.5,
        icing_lwc_g_m3=0.25,
        deicer_enabled=True,
    )
    rows = compare_all_configurations(arctic_storm)
    print(
        f"{'Config ID':<22} | {'MTOW':>6} | {'Launch':<12} | {'V_max':>9} | {'Loiter P':>9} | "
        f"{'Drop CEP':>8} | {'TD Vz':>7} | {'SP Zeta':>7} | {'DR Zeta':>7} | {'Pass'}"
    )
    print("-" * 105)
    for r in rows:
        print(
            f"{r['config_id']:<22} | {r['mtow_kg']:>5.1f}kg | {r['launch_mode']:<12} | "
            f"{r['max_speed_kmh']:>6.1f}km/h | {r['loiter_power_w']:>7.1f} W | "
            f"{r['capsule_cep_m']:>6.2f} m | {r['touchdown_vz_mps']:>5.2f}m/s | "
            f"{r['short_period_zeta']:>7.3f} | {r['dutch_roll_zeta']:>7.3f} | "
            f"{'YES' if r['mission_success'] else 'NO'}"
        )

    print("\n" + "=" * 105)
    print("PHASE-BY-PHASE MISSION TIMELINE: VARIANT_H_EVO (DROP-TROLLEY LAUNCH -> CAPSULE DROP -> PARACHUTE LANDING)")
    print("=" * 105)
    baseline_res = run_end_to_end_6dof_mission(
        config_id="VARIANT_H_EVO",
        env=arctic_storm,
        launch_mode="DROP_TROLLEY",
        landing_mode="PARACHUTE_AIRBAG",
    )
    for p in baseline_res.phase_summary:
        print(
            f"  [{p['phase']:<18}] {p['start_s']:>5.1f}s -> {p['end_s']:>5.1f}s "
            f"({p['duration_s']:>4.1f}s) | Alt={p['alt_end_m']:>5.1f}m | "
            f"V={p['vtas_end_mps']:>5.1f}m/s | {p['note']}"
        )


if __name__ == "__main__":
    main()
