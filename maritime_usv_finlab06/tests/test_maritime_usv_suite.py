#!/usr/bin/env python3
"""
Automated Verification & Readiness Test Suite (`10/10` Suites) for
`arctic-maritime-usv` (`FIN-LAB-06` / Prototype P8 & Charter 06).

Run with:
    python3 -B -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from usv_hydrodynamics_6dof import (
    load_maritime_params,
    compute_gz_righting_arm_curve,
    compute_ittc1957_resistance_and_power_polar,
    simulate_subsea_cable_tracking_and_sonde_snr,
    run_p8_five_step_sea_trial_ladder,
)
from maritime_autonomy.baltic_maritime_autonomy import (
    MaritimeTrackObservation,
    GulfOfFinlandReliefScheduler,
    COLREGsMaritimeNavigator,
    FintrafficAISDarkShipCorrelator,
    WinterIceSeasonAdaptationPlanner,
    LittoralGNSSDeniedSkerryNavigator,
    generate_ardurover_ark_fpv_usv_param_profile,
)

REPO_DIR = Path(__file__).resolve().parent.parent
CAD_DIR = REPO_DIR / "cad"


class TestMaritimeUSVSuite(unittest.TestCase):
    """10-Suite Verification of Charter 06 (O1-O7) and Gap Map Prototype P8 / Mission M4."""

    def test_01_ssot_90_10_civilian_boundary_and_non_chinese_bom(self) -> None:
        params = load_maritime_params()
        civ = params["civilian_classification"]
        self.assertEqual(civ["kinetic_effectors_or_weapons"], 0)
        self.assertEqual(civ["chinese_bom_component_share_pct"], 0.0)

        bom = params["allied_cots_bom_finlab06a_eur"]
        total_eur = sum(item["cost_eur"] for item in bom.values())
        self.assertAlmostEqual(total_eur, 4650.0, places=2)
        for key, item in bom.items():
            origin_upper = item["origin"].upper()
            self.assertNotIn("CHINA", origin_upper, f"Chinese origin found in {key}")

        mass_bd = params["mass_breakdown_finlab06a_kg"]
        total_mass = sum(mass_bd.values())
        self.assertAlmostEqual(total_mass, 24.50, places=2)

    def test_02_3d_cad_step_stl_glb_and_1to1_cnc_cut_sheets_exist(self) -> None:
        required_files = [
            CAD_DIR / "finlab06a_catamaran_1850mm.step",
            CAD_DIR / "finlab06a_catamaran_1850mm.stl",
            CAD_DIR / "finlab06a_catamaran_1850mm.glb",
            CAD_DIR / "finlab06a_hull_frames_and_deck_1to1.svg",
            CAD_DIR / "finlab06a_hull_frames_and_deck_1to1.dxf",
            CAD_DIR / "cnc_hull_and_carbon_cut_schedule.json",
            CAD_DIR / "ark_fpv_ardurover_45_usv.param",
        ]
        for path in required_files:
            self.assertTrue(path.exists(), f"Missing CAD artifact: {path}")
            self.assertGreater(path.stat().st_size, 500, f"Empty CAD artifact: {path}")

        step_txt = (CAD_DIR / "finlab06a_catamaran_1850mm.step").read_text(encoding="utf-8")
        self.assertIn("ISO-10303-21;", step_txt)
        self.assertIn("AUTOMOTIVE_DESIGN", step_txt)

    def test_03_hydrostatics_p8_catamaran_30deg_heel_and_06b_180deg_self_righting(self) -> None:
        gz_a = compute_gz_righting_arm_curve("FIN_LAB_06A")
        self.assertTrue(gz_a["stable_at_30deg_heel"])
        self.assertGreaterEqual(gz_a["gm_t_m"], 1.40)
        self.assertGreater(gz_a["gz_at_30deg_m"], 0.50)

        gz_b = compute_gz_righting_arm_curve("FIN_LAB_06B")
        self.assertTrue(gz_b["self_righting_180deg"])
        self.assertEqual(gz_b["angle_of_vanishing_stability_deg"], 180.0)
        self.assertLessEqual(gz_b["roll_recovery_from_160deg_s"], 4.0)

    def test_04_ittc1957_resistance_and_p12_uuv_tether_sonde_snr_physics(self) -> None:
        polar_a = compute_ittc1957_resistance_and_power_polar("FIN_LAB_06A")
        row_3kn = next(r for r in polar_a["polar_rows"] if r["speed_knots"] == 3.0)
        self.assertGreater(row_3kn["total_resistance_n"], 5.0)
        self.assertLess(row_3kn["propulsion_bus_power_w"], 45.0)

        sonde = simulate_subsea_cable_tracking_and_sonde_snr(water_depth_m=40.0, sonde_altitude_m=1.5)
        self.assertGreater(sonde["magnetic_gradient_snr_gain_db"], 85.0)
        self.assertLessEqual(sonde["inshore_p8_cable_cep_m"], 0.42)
        self.assertLessEqual(sonde["offshore_tethered_sonde_cep_m"], 0.20)

    def test_05_prototype_p8_five_step_sea_trial_ladder_and_mission_m4(self) -> None:
        report = run_p8_five_step_sea_trial_ladder()
        self.assertTrue(report["all_5_ladder_steps_passed"])
        steps = report["steps"]
        self.assertEqual(len(steps), 5)
        self.assertGreater(steps["8.5_36h_gulf_of_finland_trial_mission_m4"]["simulated_availability_pct"], 75.0)
        self.assertLessEqual(steps["8.5_36h_gulf_of_finland_trial_mission_m4"]["cable_cep_m"], 0.42)
        self.assertEqual(steps["8.5_36h_gulf_of_finland_trial_mission_m4"]["ais_colregs_conflicts"], 0)

    def test_06_charter06_o1_six_station_24x7_persistence_scheduler(self) -> None:
        sched = GulfOfFinlandReliefScheduler(num_stations=6, total_hulls=14, relief_lead_time_h=6.0)
        res = sched.simulate_30day_campaign("FIN_LAB_06B")
        self.assertEqual(res["charter_o1_pass"], 1.0)
        self.assertGreaterEqual(res["station_availability_24x7_pct"], 90.0)
        self.assertGreater(res["availability_uplift_vs_tfxb_pp"], 65.0)

    def test_07_charter06_o2_colregs_rules_head_on_crossing_overtaking_and_fog(self) -> None:
        nav = COLREGsMaritimeNavigator(safe_dcpa_m=250.0, tcpa_horizon_s=600.0)

        # 1. Head-On (Rule 14): Ownship North (0 deg) at (0,0), Target South (180 deg) at (0, 1200)
        head_on = nav.evaluate_encounter(0, 0, 2.0, 0.0, "TANKER-01", 0, 1200, 4.0, 180.0)
        self.assertEqual(head_on.encounter_situation, "HEAD_ON")
        self.assertGreater(head_on.recommended_course_delta_deg, 0.0)  # Starboard turn

        # 2. Crossing Give-Way (Rule 15/16): Target on Starboard bow at (+800, +800) heading West (270 deg)
        crossing_gw = nav.evaluate_encounter(0, 0, 3.0, 0.0, "CARGO-02", 800, 800, 3.0, 270.0)
        self.assertEqual(crossing_gw.encounter_situation, "CROSSING_GIVE_WAY")
        self.assertGreater(crossing_gw.recommended_course_delta_deg, 0.0)

        # 3. Crossing Stand-On (Rule 17): Target on Port bow at (-800, +800) heading East (90 deg)
        crossing_so = nav.evaluate_encounter(0, 0, 3.0, 0.0, "FERRY-03", -800, 800, 3.0, 90.0)
        self.assertEqual(crossing_so.encounter_situation, "CROSSING_STAND_ON")
        self.assertEqual(crossing_so.recommended_course_delta_deg, 0.0)

        # 4. Overtaking (Rule 13): Ownship faster (4 m/s) directly astern of slower target (1.5 m/s) heading North
        overtake = nav.evaluate_encounter(0, 0, 4.0, 0.0, "TRAWLER-04", 0, 500, 1.5, 0.0)
        self.assertEqual(overtake.encounter_situation, "OVERTAKING")
        self.assertNotEqual(overtake.recommended_course_delta_deg, 0.0)

        # 5. Restricted Visibility (Rule 19): Dense Baltic sea fog (visibility = 400 m)
        fog = nav.evaluate_encounter(0, 0, 2.5, 0.0, "FOG-VESSEL-05", 50, 900, 3.5, 180.0, visibility_m=400.0)
        self.assertEqual(fog.encounter_situation, "RESTRICTED_VISIBILITY_SAFE_SPEED")
        self.assertLessEqual(fog.recommended_speed_factor, 0.50)

    def test_08_charter06_o3_ais_dark_ship_spoof_and_anchor_drag_correlator(self) -> None:
        corr = FintrafficAISDarkShipCorrelator()

        # Normal compliant merchant traffic outside cable zone -> None
        normal_obs = MaritimeTrackObservation(
            vessel_id="FINNLINES-OK",
            timestamp_s=100.0,
            east_m=2000.0,
            north_m=4500.0,
            speed_knots=14.5,
            course_deg=85.0,
            ais_broadcast_active=True,
            ais_reported_east_m=2005.0,
            ais_reported_north_m=4498.0,
            distance_to_cable_corridor_m=1800.0,
            hydrophone_band_40_600hz_db_re_1upa=55.0,
        )
        self.assertIsNone(corr.evaluate_observation(normal_obs))

        # Shadow-fleet tanker with spoofed AIS (>150 m offset), loitering over cable & dragging anchor
        rogue_obs = MaritimeTrackObservation(
            vessel_id="SHADOW-TANKER-X",
            timestamp_s=240.0,
            east_m=500.0,
            north_m=1200.0,
            speed_knots=1.8,
            course_deg=240.0,
            ais_broadcast_active=True,
            ais_reported_east_m=920.0,
            ais_reported_north_m=1200.0,
            distance_to_cable_corridor_m=85.0,
            hydrophone_band_40_600hz_db_re_1upa=78.5,
            hvdc_50_100hz_hum_db=80.0,
        )
        alert = corr.evaluate_observation(rogue_obs)
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert.severity, "CRITICAL")
        self.assertIn("AIS_GNSS_SPOOF_MISMATCH", alert.alert_type)
        self.assertIn("CABLE_CORRIDOR_LOW_SPEED_LOITER", alert.alert_type)
        self.assertIn("SEABED_ANCHOR_DRAG_ACOUSTIC_SIGNATURE", alert.alert_type)
        self.assertLessEqual(alert.detection_latency_s, 600.0)
        self.assertEqual(alert.finlab01_track_payload["schema"], "FIN-LAB-01-MARITIME-v1.0")

    def test_09_charter06_o4_winter_ice_season_adaptation_planner(self) -> None:
        planner = WinterIceSeasonAdaptationPlanner()
        open_mode = planner.plan_station_mode("GOF-01", ice_concentration_pct=2.0, ice_thickness_cm=0.0, significant_wave_height_m=1.1)
        self.assertEqual(open_mode["operational_mode"], "OPEN_WATER_NOMINAL_STATION")

        marginal_mode = planner.plan_station_mode("GOF-01", ice_concentration_pct=22.0, ice_thickness_cm=6.0, significant_wave_height_m=0.8)
        self.assertEqual(marginal_mode["operational_mode"], "MARGINAL_ICE_EDGE_PERIMETER_SHIFT")
        self.assertTrue(marginal_mode["corridor_coverage_maintained"])

        frozen_mode = planner.plan_station_mode("GOF-01", ice_concentration_pct=85.0, ice_thickness_cm=35.0, significant_wave_height_m=0.0)
        self.assertEqual(frozen_mode["operational_mode"], "FROZEN_WINTER_HANDOFF_TO_SEABED_AND_ICE_SKIMMER")
        self.assertTrue(frozen_mode["corridor_coverage_maintained"])

    def test_10_charter06_o5_littoral_gnss_denied_skerry_navigation_and_ardurover_profile(self) -> None:
        nav = LittoralGNSSDeniedSkerryNavigator()
        sim = nav.simulate_1hour_gnss_denied_transit(transit_speed_m_s=2.0, duration_s=3600.0, water_depth_m=42.0, visible_skerry_landmarks=3)
        self.assertTrue(sim["gnss_spoofing_detected_and_rejected"])
        self.assertTrue(sim["dvl_bottom_track_locked"])
        self.assertLessEqual(sim["gnss_denied_cep_1h_m"], 30.0)
        self.assertTrue(sim["charter_o5_pass"])

        param_txt = generate_ardurover_ark_fpv_usv_param_profile("FIN_LAB_06A")
        self.assertIn("FRAME_CLASS,2", param_txt)
        self.assertIn("SERVO1_FUNCTION,73", param_txt)
        self.assertIn("SERVO3_FUNCTION,74", param_txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
