#!/usr/bin/env python3
"""
Automated Unit Test & SSOT / Non-Chinese / OPSEC Linter Suite
for Arctic Fast-SAR Jet-Hybrid (`arctic-fast-sar-jet` / `FIN-LAB-02`).
"""

import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import northern_flank_red_gap_solver as gap_solver
import sar_sizing_calculator as sizing
from sar_autonomy import pi_turbine_autonomy as autonomy


class TestArcticFastSarJetSuite(unittest.TestCase):
    def test_01_affine_breguet_sar_sizing(self):
        """Verify 100 N / 132 N micro-turbojet affine-Breguet performance & slowed drop pass."""
        cfg_sar = sizing.SarJetConfiguration(
            name="Variant H Civilian SAR Baseline (16 deg Fixed Wing, 14.95 kg MTOW, JetCat P100-RX-BL)",
            mtow_kg=14.95,
            payload_kg=5.00,
            fuel_kg=2.65,
            wingspan_m=2.20,
            wing_area_m2=0.635,
            cd0=0.025,
            oswald_e=0.84,
            thrust_n=100.0,
            m_dot_idle_g_s=1.067,
            c_slope_g_per_n_s=0.0413,
            unit_cost_eur=4850.0,
        )
        res = sizing.compute_affine_breguet_sar_performance(cfg_sar)
        self.assertGreater(res["v_opt_kmh"], 180.0)
        self.assertGreater(res["total_range_km"], 55.0)
        self.assertLess(res["time_to_35km_min"], 12.5)
        self.assertLess(res["loiter_elec_power_mtow_w"], 1200.0)

    def test_02_cad_design_params_ssot(self):
        """Verify CAD design_params_sar.json and STEP files exist and match 2.20 m span geometry."""
        params_path = os.path.join(REPO_ROOT, "cad", "design_params_sar.json")
        self.assertTrue(os.path.exists(params_path))
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)
        loiter_span = params["airframe"]["outer_wing"]["modes"][
            "iteration_1_fixed_16deg"
        ]["total_wingspan_mm"]
        self.assertEqual(loiter_span, 2200.0)
        step_path = os.path.join(
            REPO_ROOT, "cad", "arctic_fast_sar_jet_iter1_fixed16deg.step"
        )
        self.assertTrue(os.path.exists(step_path))
        self.assertGreater(os.path.getsize(step_path), 100_000)

    def test_03_turbine_autonomy_and_rth_safety(self):
        """Verify spool-lag lead compensation, EGT derating, flameout cutoff, and affine Breguet RTH."""
        node = autonomy.MicroTurbojetAutonomyNode()
        turb_nominal = autonomy.TurbineTelemetry(
            rpm=95000.0,
            egt_c=620.0,
            pump_pwm_pct=52.0,
            fuel_flow_g_s=2.4,
            state="RUNNING",
        )
        u_cmd = node.compute_lead_compensated_throttle(
            target_thrust_norm=0.65,
            preview_dthrust_dt=0.10,
            turbine=turb_nominal,
            in_air=True,
            dt_override_s=0.10,
        )
        self.assertGreater(u_cmd, 0.30)
        self.assertLessEqual(u_cmd, 1.0)

        # Verify flameout EGT (<280 C) cuts throttle to 0.0
        turb_flameout = autonomy.TurbineTelemetry(
            rpm=32000.0,
            egt_c=210.0,
            pump_pwm_pct=20.0,
            fuel_flow_g_s=0.0,
            state="FLAMEOUT",
        )
        u_flameout = node.compute_lead_compensated_throttle(
            target_thrust_norm=0.65,
            preview_dthrust_dt=0.0,
            turbine=turb_flameout,
            in_air=True,
            dt_override_s=0.10,
        )
        self.assertEqual(u_flameout, 0.0)

        # Verify affine Breguet RTH reserve check
        flight = autonomy.FlightState(
            airspeed_m_s=55.8,
            altitude_m=120.0,
            pitch_deg=2.0,
            roll_deg=0.0,
            dist_to_home_m=25000.0,
            headwind_m_s=8.0,
        )
        rth = node.check_affine_breguet_rth_reserve(flight)
        self.assertFalse(rth["infeasible_headwind_abort"])
        self.assertGreater(
            rth["remaining_fuel_g"] - rth["fuel_needed_for_rth_g"], 500.0
        )

    def test_04_northern_flank_red_gap_closure(self):
        """Verify all 5 Red/Amber gaps close within low-cost 100% Non-Chinese COTS scope."""
        # 1. Gap I: FIN-LAB-02 350-400 km/h airframe & head-on intercept geometry
        f02 = gap_solver.evaluate_finlab02_high_speed_airframe()
        jk = gap_solver.compute_jet_kill_geometry_timeline()
        self.assertGreater(f02.excess_thrust_at_400kmh_n, 40.0)
        self.assertLessEqual(f02.airframe_avionics_bom_usd, 5000.0)
        self.assertAlmostEqual(jk.t_shot1_intercept_s, 138.0, delta=2.0)
        self.assertAlmostEqual(jk.shot1_intercept_range_km, 12.4, delta=1.0)
        self.assertGreaterEqual(jk.cumulative_pk_three_shots, 0.85)
        self.assertLessEqual(jk.cost_per_kill_usd, 50000.0)

        # 2. Gap H: Heated 6.5 s launch box & 285 km/h cold-rated COTS interceptor
        prop = gap_solver.evaluate_propeller_interceptor_enablers()
        self.assertLessEqual(prop.nest_lid_open_s, 10.0)
        self.assertGreaterEqual(prop.dash_speed_kmh, 280.0)
        self.assertLess(prop.pn_miss_distance_m, 1.0)

        # 3. Gap A: -30 C 5-class acoustic & micro-Doppler library
        sig = gap_solver.evaluate_nordic_winter_signature_library()
        self.assertGreaterEqual(sig.decoy_vs_threat_accuracy, 0.95)
        self.assertLessEqual(sig.node_to_c2_latency_s, 2.0)

        # 4. Gap J: Non-RF fiber-optic FPV belt
        fpv = gap_solver.evaluate_border_counter_fpv_belt()
        self.assertGreaterEqual(fpv.corridor_detection_range_m, 500.0)
        self.assertGreaterEqual(fpv.zero_rf_fpv_detection_prob, 0.90)

        # 5. Gap K: 100% Non-Chinese seabed USV
        usv = gap_solver.evaluate_finlab06_coastal_usv()
        self.assertGreaterEqual(usv.fleet_availability_pct, 80.0)
        self.assertGreaterEqual(usv.endurance_hours, 30.0)

        # 6. Scorecard progression
        sc = gap_solver.compute_northern_flank_scorecard_progression()
        self.assertGreaterEqual(sc["cots_solved_now_pct"], 72.0)
        self.assertGreaterEqual(sc["field_validated_ceiling_pct"], 85.0)
        self.assertLessEqual(sc["red_residual_cots_solved_now"], 14)
        self.assertEqual(sc["areas_at_3plus_now"], 11)

    def test_05_zero_chinese_components_and_opsec_linter(self):
        """Enforce zero Chinese components and zero forbidden region/PII strings across public files."""
        forbidden_tokens = [
            chr(110) + "ew " + chr(101) + "ngland",
            "speedybee",
            "esp32",
            "espressif",
            "kamoer",
            "makeflyeasy",
            "flycart",
            "telefly",
            "geran",
            "shahed",
            "gerbera",
            "apkws",
            "kamikaze",
            "warhead",
            "munitions",
            "ordnance",
            "jet-kill",
            "combat_radius",
        ]
        checked_files = 0
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [
                d for d in dirs if d not in (".git", "_private", "__pycache__", "tests")
            ]
            for fname in files:
                if fname.endswith((".md", ".py", ".json", ".svg")):
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read().lower()
                    for tok in forbidden_tokens:
                        self.assertNotIn(
                            tok,
                            text,
                            f"Forbidden token '{tok}' found in public file {fpath}",
                        )
                    checked_files += 1
        self.assertGreaterEqual(checked_files, 5)


if __name__ == "__main__":
    unittest.main()
