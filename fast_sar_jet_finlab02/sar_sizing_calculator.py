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


def compute_cartridge_c_long_range_hybrid_and_blos_link(
    aux_battery_kg: float = 3.60,
    specific_energy_wh_kg: float = 282.0,
    base_avionics_batt_wh: float = 194.4,
    jet_fuel_kg: float = 2.65,
    electric_cruise_vtas_mps: float = 28.5,
    terminal_dash_vtas_mps: float = 111.1,  # 400.0 km/h (248.5 mph)
    relay_alt_m: float = 2000.0,
    aircraft_alt_m: float = 600.0,
    target_range_km: float = 180.0,
    max_extended_range_km: float = 240.0,
) -> Dict[str, float]:
    """
    Evaluates Cartridge C (Long-Range Hybrid Ferry + Sky-Diode-Relay Build D Airborne BLOS Link)
    installed in the 420 x 180 x 145 mm ventral CG bay (X_CG = 595.0 mm, 0.0 mm CG shift)
    for 113-240+ km (70-150+ mile) satellite-free reach and 400 km/h (248.5 mph) terminal dive/dash.
    """
    # 1. Mass & CG invariance inside the 5.00 kg ventral bay allowance (14.95 kg MTOW preserved)
    blos_pod_and_optics_kg = 1.40
    total_cartridge_c_kg = round(aux_battery_kg + blos_pod_and_optics_kg, 2)
    mtow_kg = round(7.30 + jet_fuel_kg + total_cartridge_c_kg, 2)

    # 2. Stage 1: Quiet Electric Folding-Prop Cruise (355 mm nose prop)
    aux_energy_wh = aux_battery_kg * specific_energy_wh_kg
    total_elec_wh = aux_energy_wh + base_avionics_batt_wh
    usable_cruise_wh = 0.82 * total_elec_wh  # 18% reserve for avionics & terminal lock

    # Aerodynamic drag at mid-weight (13.5 kg) and V = 28.5 m/s (102.6 km/h)
    rho = 1.225
    s_wing = 0.635
    ar = (2.20 ** 2) / s_wing
    k_ind = 1.0 / (math.pi * 0.84 * ar)
    q_cruise = 0.5 * rho * (electric_cruise_vtas_mps ** 2)
    w_mid_n = 13.5 * 9.80665
    d_cruise_n = q_cruise * s_wing * 0.025 + (k_ind * (w_mid_n ** 2)) / (q_cruise * s_wing)
    p_elec_cruise_w = (d_cruise_n * electric_cruise_vtas_mps) / 0.76 + 28.0

    elec_endurance_hr = usable_cruise_wh / p_elec_cruise_w
    elec_cruise_range_km = elec_endurance_hr * (electric_cruise_vtas_mps * 3.6)

    # 3. Stage 2: Dorsal Micro-Turbojet (Xicoy X132 / JetCat P100) High-Speed Dash & Steep Dive
    # Using untouched 2.65 kg Jet-A1 strake fuel tanks
    cfg_jet = SarJetConfiguration(
        name="Cartridge C Jet Stage (Xicoy X132 132N + 2.65 kg Jet-A1)",
        mtow_kg=mtow_kg,
        payload_kg=total_cartridge_c_kg,
        fuel_kg=jet_fuel_kg,
        wingspan_m=2.20,
        wing_area_m2=0.635,
        cd0=0.025,
        oswald_e=0.84,
        thrust_n=132.0,
        m_dot_idle_g_s=1.067,
        c_slope_g_per_n_s=0.0413,
        unit_cost_eur=4850.0,
    )
    jet_perf = compute_affine_breguet_sar_performance(cfg_jet, rho_kg_m3=rho)
    jet_dash_range_km = jet_perf["total_range_km"]
    combined_one_way_reach_km = elec_cruise_range_km + jet_dash_range_km
    combined_round_trip_radius_km = 0.48 * combined_one_way_reach_km

    # 4. Satellite-Free Airborne BLOS Link Budget (`sky-diode-relay` Build D at 2380.373 MHz)
    # Radio horizon d_LOS (km) = 4.12 * (sqrt(h_relay) + sqrt(h_aircraft))
    radio_horizon_km = 4.12 * (math.sqrt(relay_alt_m) + math.sqrt(aircraft_alt_m))
    freq_mhz = 2380.373  # Out-of-ISM guard band
    p_tx_dbm = 30.0      # Skyworks SE2576L-EK1 1.0 W PA
    g_tx_dbi = 9.5       # Tail directional patch antenna on aircraft
    g_rx_dbi = 14.0      # L-com HG2414P 14 dBi flat-panel on airborne relay
    loss_filter_coax_db = 1.8  # Mini-Circuits VBF-2435+ + RG-142 jumpers
    # Thermal noise floor in 250 kHz H.265 ROI video + MAVLink SDR channel with SKY65405 (1.2 dB NF)
    noise_floor_250khz_dbm = -174.0 + 10.0 * math.log10(250_000.0) + 1.2  # -118.82 dBm

    def calc_snr_db(dist_km: float) -> float:
        fspl_db = 20.0 * math.log10(dist_km) + 20.0 * math.log10(freq_mhz) + 32.44
        p_rx_dbm = p_tx_dbm + g_tx_dbi + g_rx_dbi - loss_filter_coax_db - fspl_db
        return round(p_rx_dbm - noise_floor_250khz_dbm, 2)

    snr_180km_db = calc_snr_db(target_range_km)
    snr_240km_db = calc_snr_db(max_extended_range_km)

    return {
        "cartridge_c_mass_kg": total_cartridge_c_kg,
        "mtow_kg": mtow_kg,
        "cg_shift_mm": 0.0,
        "total_electric_energy_wh": round(total_elec_wh, 1),
        "electric_cruise_power_w": round(p_elec_cruise_w, 1),
        "electric_cruise_range_km": round(elec_cruise_range_km, 1),
        "jet_dash_range_km": round(jet_dash_range_km, 1),
        "combined_hybrid_one_way_reach_km": round(combined_one_way_reach_km, 1),
        "combined_hybrid_one_way_reach_miles": round(combined_one_way_reach_km * 0.621371, 1),
        "combined_hybrid_round_trip_radius_km": round(combined_round_trip_radius_km, 1),
        "terminal_dive_dash_speed_kmh": round(terminal_dash_vtas_mps * 3.6, 1),
        "terminal_dive_dash_speed_mph": round(terminal_dash_vtas_mps * 2.23694, 1),
        "airborne_relay_radio_horizon_km": round(radio_horizon_km, 1),
        "airborne_relay_radio_horizon_miles": round(radio_horizon_km * 0.621371, 1),
        "sky_diode_snr_at_180km_db": snr_180km_db,
        "sky_diode_snr_at_240km_db": snr_240km_db,
        "vk7mo_coherent_snr_at_240km_db": round(snr_240km_db + 28.0, 1),
        "zero_starlink_dependency": True,
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

    cart_c = compute_cartridge_c_long_range_hybrid_and_blos_link()
    print("\n" + "=" * 80)
    print("CARTRIDGE C: LONG-RANGE HYBRID (70-150+ MI) + SKY-DIODE AIRBORNE BLOS LINK")
    print("=" * 80)
    for k, v in cart_c.items():
        print(f"  {k:38s}: {v}")


if __name__ == "__main__":
    main()
