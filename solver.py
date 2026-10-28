#!/usr/bin/env python3
"""Live Coupled Multiphysics SSOT Solver & 5-Regime Verification Runner for Project Opaslyhty.

Executes `physics_verify_v01.py` (Iter 1 Baseline), `physics_verify_v02.py` (Iter 2 Intermediate),
and `physics_verify.py` (Iter 3 Golden) via `run_isolated_ssot_child`, verifies full 5-regime
aerospace closure across 3,000 Common-Random-Numbers (CRN) Monte Carlo draws, and writes
`verification_report.json` and `playbook_v4_execution_receipt.json`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.aerospace_ssot as rap  # noqa: E402


def build_five_regime_closure_report(ev_gold: dict) -> dict:
    """Extract 5-regime flight-envelope closure metrics from Golden Iteration 3 SSOT state."""
    st = ev_gold["nominal_state"]
    lcb = ev_gold["margins_lcb"]
    tail = ev_gold["metrics_tail_bound"]
    return {
        "REGIME_1_HOVER_LAUNCH": {
            "pass": bool(lcb["H_HOVER_TW_EFF"] >= 0.01 and lcb["H_ARM_VOLT_MARGIN"] >= 0.01),
            "hover_tw_eff": round(float(st["hover_tw_eff"]), 4),
            "hover_tw_tail_99pct": round(float(tail["H_HOVER_TW_EFF"]), 4),
            "p_hover_elec_w": round(float(st["p_hover_total_w"]), 2),
            "i_hover_a": round(float(st["i_hover_a"]), 2),
            "v_term_hover_eod_v": round(float(st["v_term_hover_v"]), 3),
            "arm_volt_margin_v": round(float(st["arm_volt_margin_v"]), 3),
            "mu_lcb": round(float(lcb["H_HOVER_TW_EFF"]), 4),
        },
        "REGIME_2_CROSSWIND_HOVER_TRIM": {
            "pass": bool(lcb["H_CROSSWIND_ROLL_TRIM"] >= 0.01),
            "v_crosswind_design_mps": 10.0,
            "roll_sat_pct_10mps": round(float(st["crosswind_roll_sat_pct"]), 3),
            "roll_sat_pct_tail_99pct": round(float(tail["H_CROSSWIND_ROLL_TRIM"]), 3),
            "mu_lcb": round(float(lcb["H_CROSSWIND_ROLL_TRIM"]), 4),
        },
        "REGIME_3_TRANSITION_CLIMB": {
            "pass": bool(lcb["H_TRANSITION_CLIMB_PS"] >= 0.01),
            "v_climb_design_mps": 4.5,
            "specific_excess_power_ps_mps": round(float(st["transition_ps_m_s"]), 3),
            "specific_excess_power_tail_99pct": round(float(tail["H_TRANSITION_CLIMB_PS"]), 3),
            "mu_lcb": round(float(lcb["H_TRANSITION_CLIMB_PS"]), 4),
        },
        "REGIME_4_CRUISE_ENDURANCE": {
            "pass": bool(
                lcb["H_CRUISE_ENDURANCE_M25C"] >= 0.01
                and lcb["H_HOVER_ENDURANCE_M25C"] >= 0.01
                and lcb["H_STATIC_MARGIN"] >= 0.01
            ),
            "v_cruise_mps": 10.0,
            "p_cruise_elec_w": round(float(st["p_cruise_total_w"]), 2),
            "i_cruise_a": round(float(st["i_cruise_a"]), 2),
            "t_cell_ss_c": round(float(st["t_cell_k"] - 273.15), 2),
            "r_cell_eff_mohm": round(float(st["r_cell_mohm"]), 2),
            "t_hover_usable_min": round(float(st["t_hover_usable_min"]), 2),
            "t_cruise_usable_min": round(float(st["t_cruise_usable_min"]), 2),
            "r_combat_km": round(float(st["r_combat_km"]), 2),
            "static_margin_pct": round(float(st["static_margin_pct"]), 2),
            "mu_lcb": round(float(lcb["H_CRUISE_ENDURANCE_M25C"]), 4),
        },
        "REGIME_5_DESCENT_TERMINAL_FAULT": {
            "pass": bool(lcb["H_DESCENT_CONTROL"] >= 0.005 and lcb["H_ALT_85M_ERR"] >= 0.01),
            "v_descent_safe_mps": 1.5,
            "v_tip_induced_hover_mps": round(float(st["vi_hover_m_s"]), 3),
            "vrs_avoidance_ratio_vz_over_vi0": round(float(st["vrs_ratio"]), 3),
            "descent_control_authority_pct": round(float(st["descent_control_margin_pct"]), 2),
            "descent_control_tail_99pct": round(float(tail["H_DESCENT_CONTROL"]), 2),
            "alt_est_err_85m_m": round(float(st["alt_error_85m_agl_m"]), 3),
            "mu_lcb": round(float(lcb["H_DESCENT_CONTROL"]), 4),
        },
    }


def run_coupled_verification() -> dict:
    """Run all 3 SSOT iterations (`v01`, `v02`, `v03`) and compile full verification report."""
    p_v01 = ROOT / "physics_verify_v01.py"
    p_v02 = ROOT / "physics_verify_v02.py"
    p_v03 = ROOT / "physics_verify.py"

    seed = 20261026
    ev_v01 = rap.run_isolated_ssot_child(
        p_v01, mode="evaluate", payload={"overrides": {}, "n": 3000, "seed": seed}
    )
    ev_v02 = rap.run_isolated_ssot_child(
        p_v02, mode="evaluate", payload={"overrides": {}, "n": 3000, "seed": seed}
    )
    ev_v03 = rap.run_isolated_ssot_child(
        p_v03, mode="evaluate", payload={"overrides": {}, "n": 3000, "seed": seed}
    )

    spec_v03, _, errs = rap.extract_ssot_ast(p_v03.read_text(encoding="utf-8"))
    if errs:
        raise RuntimeError("AST errors in physics_verify.py: " + "; ".join(errs))

    gain_report = rap.compute_physical_gain_report(spec_v03, ev_v01, ev_v03, min_gain_target=10.0)
    regimes = build_five_regime_closure_report(ev_v03)
    all_regimes_closed = all(r["pass"] for r in regimes.values())

    st1 = ev_v01["nominal_state"]
    st2 = ev_v02["nominal_state"]
    st3 = ev_v03["nominal_state"]

    report = {
        "project_id": "Opaslyhty_Karhunkierros_SAR_Quadcopter",
        "platform": "Holybro X500 V2 + Pixhawk 6C Mini + RPi 5 + Topdon TC001 LWIR + 4S2P Molicel P45B",
        "all_5_regimes_closed": all_regimes_closed,
        "feasible": bool(ev_v03["feasible"] and all_regimes_closed),
        "m_tow_kg": round(float(ev_v03["m_tow"]), 3),
        "bom_mass_kg": round(float(ev_v03["bom_mass_kg"]), 3),
        "cost_eur": round(float(ev_v03["cost_eur"]), 2),
        "n_custom_pcb": int(ev_v03["n_custom_pcb"]),
        "mu_min_lcb": round(float(ev_v03["mu_min"]), 4),
        "regimes": regimes,
        "iterations": {
            "iteration_1_v01_baseline": {
                "file": "physics_verify_v01.py",
                "feasible": bool(ev_v01["feasible"]),
                "violated_count": len(ev_v01["violated"]),
                "witness_outcomes": ev_v01["witness_outcomes"],
                "t_hover_usable_min": round(float(st1["t_hover_usable_min"]), 2),
                "t_cruise_usable_min": round(float(st1["t_cruise_usable_min"]), 2),
                "r_cell_eff_mohm": round(float(st1["r_cell_mohm"]), 2),
                "alt_est_err_85m_m": round(float(st1["alt_error_85m_agl_m"]), 2),
                "v_sense_err_v": round(float(st1["pm02_volt_sense_err_v"]), 3),
            },
            "iteration_2_v02_intermediate": {
                "file": "physics_verify_v02.py",
                "feasible": bool(ev_v02["feasible"]),
                "violated_count": len(ev_v02["violated"]),
                "witness_outcomes": ev_v02["witness_outcomes"],
                "t_hover_usable_min": round(float(st2["t_hover_usable_min"]), 2),
                "t_cruise_usable_min": round(float(st2["t_cruise_usable_min"]), 2),
                "r_cell_eff_mohm": round(float(st2["r_cell_mohm"]), 2),
                "alt_est_err_85m_m": round(float(st2["alt_error_85m_agl_m"]), 2),
                "v_sense_err_v": round(float(st2["pm02_volt_sense_err_v"]), 3),
            },
            "iteration_3_v03_golden": {
                "file": "physics_verify.py",
                "feasible": bool(ev_v03["feasible"]),
                "violated_count": len(ev_v03["violated"]),
                "witness_outcomes": ev_v03["witness_outcomes"],
                "t_hover_usable_min": round(float(st3["t_hover_usable_min"]), 2),
                "t_cruise_usable_min": round(float(st3["t_cruise_usable_min"]), 2),
                "r_combat_km": round(float(st3["r_combat_km"]), 2),
                "t_cell_ss_c": round(float(st3["t_cell_k"] - 273.15), 2),
                "r_cell_eff_mohm": round(float(st3["r_cell_mohm"]), 2),
                "alt_est_err_85m_m": round(float(st3["alt_error_85m_agl_m"]), 2),
                "v_sense_err_v": round(float(st3["pm02_volt_sense_err_v"]), 4),
            },
        },
        "solver": {
            "live_coupled_ssot_verified": True,
            "mc_draws": 3000,
            "crn_seed": seed,
            "verified_10x_100x_gain": gain_report,
        },
        "golden_evaluation": ev_v03,
    }

    (ROOT / "verification_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    receipt = {
        "project": "karhunkierros-sar-drone",
        "playbook_version": "7.0",
        "all_5_regimes_closed": all_regimes_closed,
        "iteration_history": [
            report["iterations"]["iteration_1_v01_baseline"],
            report["iterations"]["iteration_2_v02_intermediate"],
            report["iterations"]["iteration_3_v03_golden"],
        ],
        "verified_10x_100x_gain": gain_report,
    }
    (ROOT / "playbook_v4_execution_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    out = run_coupled_verification()
    print(json.dumps(out, indent=2, sort_keys=True))
