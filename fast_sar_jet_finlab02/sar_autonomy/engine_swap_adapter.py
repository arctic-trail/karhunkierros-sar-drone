#!/usr/bin/env python3
"""
Modular Propulsion Sled CG Solver & Unified ECU Hardware Abstraction Layer (HAL)
for swapping between a Turnkey Xicoy X45 / JetCat (Prototype Phase) and a
Tier 1B 54mm MW54 + STM32G4 OpenTurbine-EU Engine (Cost-Reduced Production Phase).
"""

from dataclasses import dataclass
from pi_turbine_autonomy import TurbineTelemetry


@dataclass
class EnginePackageSpec:
    name: str
    outer_diameter_mm: float
    length_mm: float
    bare_engine_mass_g: float
    ancillary_mass_g: float     # ECU/DRM + pump + valves + 2S ECU battery
    max_rpm: int
    max_thrust_n: float
    idle_burn_g_min: float
    full_burn_g_min: float
    spool_tau_s: float


def compute_zero_ballast_cg_swap(
    kingtech: EnginePackageSpec,
    tier1b: EnginePackageSpec,
    airframe_nose_arm_mm: float = -380.0,   # Nose battery bay relative to aerodynamic CG
    default_aft_engine_arm_mm: float = 210.0,  # Aft turbine mount relative to aerodynamic CG
):
    """
    Computes the exact rail slide offset (dx_engine) and nose ECU-battery placement
    so swapping from KingTech K45G4+ (610g total) to Tier 1B MW54 (820g total)
    preserves the exact Center of Gravity (0.0 mm CG shift) with zero dead-weight ballast.
    """
    # Split ancillary mass into Nose-mounted (ECU + 2S Li-Ion battery = 140g)
    # and Mid-mounted near CG (fuel pump + filter + solenoid = 70g)
    nose_mass_kt_g = 130.0
    nose_mass_t1b_g = 170.0  # Slightly heavier STM32G4 enclosure + MOSFETs + 2S1P 21700 pack

    aft_mass_kt_g = kingtech.bare_engine_mass_g
    aft_mass_t1b_g = tier1b.bare_engine_mass_g

    # Pitching moment contribution relative to target CG for KingTech baseline:
    # M_kt = aft_mass_kt * x_aft_kt + nose_mass_kt * x_nose_kt
    moment_kt_g_mm = aft_mass_kt_g * default_aft_engine_arm_mm + nose_mass_kt_g * airframe_nose_arm_mm

    # Solve for required aft rail position x_aft_t1b of the Tier 1B engine on the carbon slide rails
    # so that M_t1b == M_kt:
    required_aft_arm_t1b_mm = (moment_kt_g_mm - nose_mass_t1b_g * airframe_nose_arm_mm) / aft_mass_t1b_g
    rail_slide_forward_mm = default_aft_engine_arm_mm - required_aft_arm_t1b_mm

    return {
        "kingtech_aft_mass_g": aft_mass_kt_g,
        "tier1b_aft_mass_g": aft_mass_t1b_g,
        "default_aft_arm_mm": default_aft_engine_arm_mm,
        "tier1b_aft_arm_mm": round(required_aft_arm_t1b_mm, 1),
        "rail_slide_forward_mm": round(rail_slide_forward_mm, 1),
    }


class UnifiedTurbineHAL:
    """
    Hardware Abstraction Layer allowing the Raspberry Pi autonomy stack to switch
    between a Turnkey Xicoy/JetCat ECU and the open-source European
    STM32G4 OpenTurbine-EU FADEC without changing a single line of guidance/control code.
    """

    @staticmethod
    def parse_turnkey_ecu_frame(frame: dict) -> TurbineTelemetry:
        # Normalizes Turnkey Xicoy/JetCat (232,000 RPM max, 20-150 g/min) into standard telemetry
        pump_pct = float(frame.get("pump_pw_pct", 0.0))
        fuel_flow_g_s = (20.0 + 130.0 * (pump_pct / 100.0)) / 60.0
        return TurbineTelemetry(
            rpm=float(frame["rpm"]),
            egt_c=float(frame["egt_c"]),
            pump_pwm_pct=pump_pct,
            fuel_flow_g_s=round(fuel_flow_g_s, 3),
            state=frame.get("status", "RUNNING"),
        )

    @staticmethod
    def parse_stm32g4_openturbine_frame(frame: dict) -> TurbineTelemetry:
        # Normalizes Tier 1B MW54 STM32G4 OpenTurbine-EU (165,000 RPM max, 25.2-163 g/min)
        pump_pct = float(frame.get("pwm", 0.0))
        fuel_flow_g_s = (25.2 + 137.8 * (pump_pct / 100.0)) / 60.0
        return TurbineTelemetry(
            rpm=float(frame["shaft_rpm"]),
            egt_c=float(frame["tc_celsius"]),
            pump_pwm_pct=pump_pct,
            fuel_flow_g_s=round(fuel_flow_g_s, 3),
            state=frame.get("fsm_state", "RUNNING"),
        )


def main():
    kt_k45 = EnginePackageSpec(
        name="KingTech K45G4+",
        outer_diameter_mm=62.9,
        length_mm=158.0,
        bare_engine_mass_g=450.0,
        ancillary_mass_g=160.0,
        max_rpm=232000,
        max_thrust_n=45.0,
        idle_burn_g_min=20.0,
        full_burn_g_min=150.0,
        spool_tau_s=0.95,
    )
    tier1b_mw54 = EnginePackageSpec(
        name="Tier 1B 54mm MW54 COTS-Core",
        outer_diameter_mm=68.0,
        length_mm=172.0,
        bare_engine_mass_g=570.0,
        ancillary_mass_g=250.0,
        max_rpm=165000,
        max_thrust_n=48.0,
        idle_burn_g_min=25.2,
        full_burn_g_min=163.0,
        spool_tau_s=1.35,
    )

    cg_res = compute_zero_ballast_cg_swap(kt_k45, tier1b_mw54)
    print("=" * 85)
    print("MODULAR ENGINE SLED SWAP ANALYSIS: KINGTECH K45G4+ -> TIER 1B 54MM MW54")
    print("=" * 85)
    print(f"  KingTech K45G4+ Aft Mass : {cg_res['kingtech_aft_mass_g']:.0f} g @ +{cg_res['default_aft_arm_mm']:.1f} mm aft of CG")
    print(f"  Tier 1B MW54 Aft Mass    : {cg_res['tier1b_aft_mass_g']:.0f} g @ +{cg_res['tier1b_aft_arm_mm']:.1f} mm aft of CG")
    print(f"  Required Sled Rail Slide : {cg_res['rail_slide_forward_mm']:.1f} mm FORWARD (0 g ballast required)")
    print(f"  Clamp Collar Adapter     : 68.0 mm base cradle + 2.55 mm radial silicone/aluminum reducer shim for 62.9 mm K45G4+")

    kt_telem = UnifiedTurbineHAL.parse_turnkey_ecu_frame(
        {"rpm": 145000, "egt_c": 590, "pump_pw_pct": 52.0, "status": "RUNNING"}
    )
    t1b_telem = UnifiedTurbineHAL.parse_stm32g4_openturbine_frame(
        {"shaft_rpm": 112000, "tc_celsius": 615, "pwm": 52.0, "fsm_state": "RUNNING"}
    )
    print("\n  [Unified HAL Telemetry Check]")
    print(f"  Turnkey Xicoy/JetCat Frame -> {kt_telem}")
    print(f"  Tier 1B STM32G4 OpenTurbine-EU Frame -> {t1b_telem}")


if __name__ == "__main__":
    main()
