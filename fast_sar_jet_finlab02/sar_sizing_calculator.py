#!/usr/bin/env python3
"""
sar_sizing_calculator.py — First-Principles Brayton-Cycle & Affine-Breguet Sizing Calculator
for the Arctic Trail Tier-3 Civilian Fast-SAR & FIN-LAB-02 High-Speed Responder Airframe.

100% Non-Chinese (EU / UK / CH / US Allied) COTS Architecture:
  - Turnkey Propulsion: German JetCat P100-RX-BL (100 N) or Spanish Xicoy X132 (132 N)
  - Flight Control: ARK FPV (USA, Allied STM32H7) + TE MS4525DO Heated Pitot + u-blox ZED-F9P (CH)
  - Companion AI: Raspberry Pi 5 (UK) + FLIR Lepton/Boson LWIR + Sony Starvis Night Vision
  - Airframe: 2.20 m Mouldless Carbon/XPS Cranked Wing + Twin-Boom 110° Inverted Lambda-Tail
    (Iteration 1 Fixed 16° SAR Baseline @ 14.95 kg MTOW; FIN-LAB-02 60° Fast Responder @ 350-400 km/h)
"""

from dataclasses import dataclass
import math
from typing import Dict


@dataclass(frozen=True)
class SarJetConfiguration:
    name: str
    mtow_kg: float
    payload_kg: float
    fuel_kg: float
    wingspan_m: float
    wing_area_m2: float
    cd0: float
    oswald_e: float
    thrust_n: float
    m_dot_idle_g_s: float
    c_slope_g_per_n_s: float
    unit_cost_eur: float


def compute_affine_breguet_sar_performance(cfg: SarJetConfiguration, rho_kg_m3: float = 1.225) -> Dict[str, float]:
    """
    Computes exact Affine-Idle-Burn Breguet optimal cruise speed V*, specific range,
    mission radius, and slowed 25.5 m/s parachute release pass drag/power.
    """
    ar = (cfg.wingspan_m ** 2) / cfg.wing_area_m2
    k_ind = 1.0 / (math.pi * cfg.oswald_e * ar)
    w_mid_n = (cfg.mtow_kg - 0.5 * cfg.fuel_kg) * 9.80665

    def drag_n(v_mps: float, mass_kg: float) -> float:
        q = 0.5 * rho_kg_m3 * (v_mps ** 2)
        w_n = mass_kg * 9.80665
        return q * cfg.wing_area_m2 * cfg.cd0 + (k_ind * (w_n ** 2)) / (q * cfg.wing_area_m2)

    def fuel_flow_g_s(v_mps: float, mass_kg: float) -> float:
        d = drag_n(v_mps, mass_kg)
        return cfg.m_dot_idle_g_s + cfg.c_slope_g_per_n_s * d

    # Scan airspeed 25..115 m/s for maximum specific range (m/g)
    best_v = 55.0
    best_sr_m_per_g = 0.0
    for v10 in range(250, 1150, 2):
        v = v10 / 10.0
        d = drag_n(v, cfg.mtow_kg - 0.5 * cfg.fuel_kg)
        if d <= cfg.thrust_n:
            sr = v / fuel_flow_g_s(v, cfg.mtow_kg - 0.5 * cfg.fuel_kg)
            if sr > best_sr_m_per_g:
                best_sr_m_per_g = sr
                best_v = v

    usable_fuel_g = 0.90 * cfg.fuel_kg * 1000.0  # 10% reserve
    total_range_km = (usable_fuel_g * best_sr_m_per_g) / 1000.0

    # Slowed 25.5 m/s parachute drop pass drag & electric loiter power
    d_drop_n = drag_n(25.5, cfg.mtow_kg)
    p_useful_w = d_drop_n * 25.5
    p_elec_mtow_w = p_useful_w / 0.72

    return {
        "aspect_ratio": round(ar, 2),
        "v_opt_mps": round(best_v, 1),
        "v_opt_kmh": round(best_v * 3.6, 1),
        "total_range_km": round(total_range_km, 1),
        "sar_drop_radius_km": round(0.48 * total_range_km, 1),
        "time_to_35km_min": round((35000.0 / best_v) / 60.0, 1),
        "drop_pass_drag_n": round(d_drop_n, 2),
        "loiter_useful_power_w": round(p_useful_w, 1),
        "loiter_elec_power_mtow_w": round(p_elec_mtow_w, 1),
    }


def main():
    variant_h_sar = SarJetConfiguration(
        name="Variant H Civilian SAR Baseline (16° Fixed Wing, 14.95 kg MTOW, JetCat P100-RX-BL)",
        mtow_kg=14.95,
        payload_kg=5.00,
        fuel_kg=2.65,
        wingspan_m=2.20,
        wing_area_m2=0.635,
        cd0=0.025,
        oswald_e=0.84,
        thrust_n=100.0,
        m_dot_idle_g_s=1.067,      # 80 mL/min = 64 g/min idle
        c_slope_g_per_n_s=0.0413,  # 390 mL/min = 312 g/min @ 100 N
        unit_cost_eur=4850.0,
    )
    res = compute_affine_breguet_sar_performance(variant_h_sar)
    print("=" * 80)
    print(f"ARCTIC TRAIL TIER-3 FAST-SAR SIZING SUMMARY: {variant_h_sar.name}")
    print("=" * 80)
    for k, v in res.items():
        print(f"  {k:28s}: {v}")


if __name__ == "__main__":
    main()
