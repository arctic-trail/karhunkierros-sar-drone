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

import flight_simulator_6dof as flight_sim
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

        # Verify 3-Law Flight Envelope Protections & Blocked-Pitot Pitch/Power + SYNTH_IAS Backup
        fep = autonomy.FlightEnvelopeProtectionController()
        synth = fep.estimate_synthetic_airspeed_and_angles(
            mass_kg=14.95,
            rho_kg_m3=1.42,
            pitch_deg=2.2,
            roll_deg=0.0,
            climb_rate_mps=0.0,
            nz_g=1.0,
            ay_mps2=0.0,
            ax_body_mps2=0.0,
            n1_pct=74.0,
        )
        self.assertGreater(synth["v_synth_tas_mps"], 48.0)
        self.assertLess(synth["v_synth_tas_mps"], 75.0)

        # Mode A: Ram port iced open static (pitot drops to 18 m/s while V_SYNTH is ~62 m/s)
        law_a = fep.detect_pitot_blockage_and_select_law(
            pitot_ias_mps=18.0,
            pitot_qc_rate_pa_s=0.0,
            baro_ps_rate_pa_s=0.0,
            v_synth_ias_mps=synth["v_synth_ias_mps"],
            v_gnss_air_ias_mps=61.5,
            synth_healthy=True,
        )
        self.assertTrue(law_a["pitot_blocked"])
        self.assertEqual(law_a["active_control_law"], "ALTERNATE_LAW_SYNTH_IAS")
        self.assertEqual(law_a["fault_mode"], "RAM_PORT_ICED_LOW_IAS")

        # Mode B: Sealed ram+drain pressure trap during climb (d(qc)/dt mirrors -d(Ps)/dt) -> Direct Pitch-Power Law
        law_b = fep.detect_pitot_blockage_and_select_law(
            pitot_ias_mps=78.0,
            pitot_qc_rate_pa_s=85.0,
            baro_ps_rate_pa_s=-88.0,
            v_synth_ias_mps=54.0,
            synth_healthy=False,
            flight_phase="CLIMB",
            payload_attached=True,
        )
        self.assertTrue(law_b["pitot_blocked"])
        self.assertEqual(law_b["active_control_law"], "DIRECT_PITCH_POWER_LAW")
        self.assertEqual(law_b["fault_mode"], "SEALED_RAM_PRESSURE_TRAP_HIGH_IAS")
        self.assertEqual(law_b["pitch_power_reference"]["commanded_pitch_deg"], 6.5)
        self.assertEqual(law_b["pitch_power_reference"]["commanded_n1_pct"], 92.0)

        # Normal Law alpha_floor TOGA auto-thrust, G-limit, and bank-angle protection
        prot = fep.apply_normal_law_envelope_protections(
            cmd_pitch_deg=16.0,
            cmd_roll_deg=70.0,
            cmd_throttle_norm=0.45,
            alpha_hat_deg=13.2,
            beta_hat_deg=9.5,
            nz_g=3.9,
            vtas_mps=42.0,
            ice_detected=False,
        )
        self.assertIn("ALPHA_PROT_ACTIVE", prot["protections_triggered"])
        self.assertIn("ALPHA_FLOOR_TOGA_THRUST", prot["protections_triggered"])
        self.assertIn("LOAD_FACTOR_G_LIMIT_MAX", prot["protections_triggered"])
        self.assertIn("BANK_ANGLE_LIMIT", prot["protections_triggered"])
        self.assertIn("SIDESLIP_BETA_LIMIT", prot["protections_triggered"])
        self.assertEqual(prot["protected_throttle_norm"], 1.0)
        self.assertLessEqual(prot["protected_roll_deg"], 25.0)
        self.assertLess(prot["protected_pitch_deg"], 16.0)

        # 5. Quantitative 100,000-Flight (55,000 FH) FMEA & SORA Fault-Tree Verification
        fmea_100k = autonomy.compute_expected_failures_per_100k_flights()
        self.assertEqual(fmea_100k["basis_flights"], 100_000)
        self.assertEqual(len(fmea_100k["subsystems"]), 10)
        self.assertAlmostEqual(fmea_100k["total_primary_faults_per_100k_flights"], 362.79, delta=1.0)
        self.assertAlmostEqual(fmea_100k["total_unmitigated_crashes_per_100k_flights"], 238.03, delta=1.0)
        self.assertLessEqual(fmea_100k["total_residual_crashes_per_100k_flights"], 2.0)
        self.assertGreaterEqual(fmea_100k["crash_reduction_pct"], 99.0)
        self.assertLessEqual(fmea_100k["residual_crashes_per_flight_hour"], 3.0e-5)

        # 6. Dorsal S-Duct Distortion (DC60), Passive Blow-In Louvers & Compressor Surge-Margin Verification
        surge_cruise = node.evaluate_dorsal_inlet_distortion_and_surge_margin(
            alpha_deg=2.2,
            beta_deg=0.0,
            airspeed_ias_mps=55.8,
            throttle_cmd_norm=0.65,
            n1_pct=74.0,
        )
        self.assertFalse(surge_cruise["blow_in_louvers_open"])
        self.assertLess(surge_cruise["dc60_distortion_index"], 0.06)
        self.assertGreater(surge_cruise["surge_margin_pct"], 22.0)
        self.assertFalse(surge_cruise["surge_risk_detected"])

        # Slowed 25.5 m/s 100% TOGA go-around in 0.40 g/m3 freezing drizzle + 11 deg AoA + 6 deg sideslip:
        # Without passive blow-in louvers, 8W lip heater, and active surge-guard slew limiter -> surge risk
        surge_unprotected = node.evaluate_dorsal_inlet_distortion_and_surge_margin(
            alpha_deg=11.0,
            beta_deg=6.0,
            airspeed_ias_mps=25.5,
            throttle_cmd_norm=1.0,
            n1_pct=52.0,
            aux_blow_in_louvers_installed=False,
            lip_deicer_and_fod_bypass_active=False,
            icing_lwc_g_m3=0.40,
            surge_guard_slew_limiter_enabled=False,
        )
        self.assertTrue(surge_unprotected["surge_risk_detected"])
        self.assertLess(surge_unprotected["surge_margin_pct"], 5.0)

        # With +12 g passive blow-in louvers (+0 EUR), 8W E1 lip heater + 10mm FOD bypass, and surge-guard slew limiter
        surge_protected = node.evaluate_dorsal_inlet_distortion_and_surge_margin(
            alpha_deg=11.0,
            beta_deg=6.0,
            airspeed_ias_mps=25.5,
            throttle_cmd_norm=1.0,
            n1_pct=52.0,
            aux_blow_in_louvers_installed=True,
            lip_deicer_and_fod_bypass_active=True,
            icing_lwc_g_m3=0.40,
            surge_guard_slew_limiter_enabled=True,
        )
        self.assertTrue(surge_protected["blow_in_louvers_open"])
        self.assertFalse(surge_protected["surge_risk_detected"])
        self.assertGreater(surge_protected["surge_margin_pct"], 12.0)
        self.assertLess(surge_protected["dc60_distortion_index"], surge_unprotected["dc60_distortion_index"] * 0.55)

        # 7. Year-Round Arctic Edge-Case Hardening (Winter -35 C Baro, 0 C Slush, Chimney <95 C, Summer Rakka & Midnight Sun)
        yr_winter = node.evaluate_year_round_arctic_edge_cases(
            oat_c=-35.0,
            takeoff_surface_temp_c=-1.5,
            indicated_baro_agl_m=85.0,
            flight_time_s=45.0,
            turbine_state="COOLDOWN",
            turbine_egt_c=420.0,
            sun_elevation_deg=4.5,
            camera_to_sun_azimuth_diff_deg=12.0,
            lwir_hotspot_temp_c=31.5,
            starvis_visible_saturation_norm=0.98,
        )
        # #1 Cold-air baro over-reading at -35 C: 85 m indicated is 70.25 m true (+14.75 m error compensated)
        self.assertAlmostEqual(yr_winter["baro_cold_compensation"]["true_geometric_agl_m"], 70.25, delta=0.5)
        self.assertAlmostEqual(yr_winter["baro_cold_compensation"]["baro_cold_overread_error_m"], 14.75, delta=0.5)
        self.assertAlmostEqual(yr_winter["baro_cold_compensation"]["commanded_baro_target_for_true_agl_m"], 102.85, delta=0.6)
        # #2-#4 Warm fuel vent, P-static wicks, and tail-root <55 mm carbon linkage
        self.assertTrue(yr_winter["fuel_tank_warm_boundary_layer_vent_active"])
        self.assertTrue(yr_winter["p_static_carbon_wicks_and_1mohm_ground_bus"])
        self.assertTrue(yr_winter["tail_root_carbon_pushrod_zero_cte_and_krytox"])
        # #5 0 C slush takeoff ice-break micro-pulse at t=45 s
        self.assertTrue(yr_winter["slush_ice_break_micro_pulse_triggered"])
        # #6 Post-shutdown chimney heat-soak blower interlock keeps XPS foam < 58 C when EGT = 420 C
        self.assertTrue(yr_winter["chimney_heat_soak_blower_interlock_active"])
        self.assertLess(yr_winter["dorsal_xps_foam_peak_temp_c"], 58.0)
        # #8 Midnight-sun specular bog glare rejected
        self.assertTrue(yr_winter["midnight_sun_specular_glint_rejected"])
        self.assertFalse(yr_winter["valid_human_casualty_lock"])

        # #7 & #8 Summer +20 C Rakka insect-swarm Pitot chitin-bake prevention + true casualty lock away from sun azimuth
        yr_summer = node.evaluate_year_round_arctic_edge_cases(
            oat_c=20.0,
            takeoff_surface_temp_c=20.0,
            indicated_baro_agl_m=85.0,
            flight_time_s=180.0,
            turbine_state="COOLDOWN",
            turbine_egt_c=75.0,
            sun_elevation_deg=6.0,
            camera_to_sun_azimuth_diff_deg=85.0,
            lwir_hotspot_temp_c=33.0,
            starvis_visible_saturation_norm=0.42,
        )
        self.assertFalse(yr_summer["deicer_heaters_enabled"])  # Off at +20 C so insects aren't baked inside Pitot
        self.assertTrue(yr_summer["pitot_chitin_bake_prevented"])
        self.assertTrue(yr_summer["pitot_3vote_synth_ias_armed_year_round"])
        self.assertFalse(yr_summer["chimney_heat_soak_blower_interlock_active"])  # Cooled < 95 C
        self.assertFalse(yr_summer["midnight_sun_specular_glint_rejected"])
        self.assertTrue(yr_summer["valid_human_casualty_lock"])

        # Verify Iteration 2 loiter transition enforces EGT < 95 C chimney blower interlock
        loiter_hot = node.manage_hybrid_radar_loiter_transition(
            flight=flight,
            on_radar_station=True,
            battery_soc_pct=80.0,
            heated_bay_temp_c=15.0,
            relight_qualified=True,
            turbine_egt_c=380.0,
        )
        self.assertTrue(loiter_hot["chimney_cooldown_blower_active"])
        self.assertIn("EGT_BELOW_95C", loiter_hot["vendor_ecu_command"])

    def test_04_northern_flank_red_gap_closure(self):
        """Verify all 5 Red/Amber gaps close within low-cost 100% Non-Chinese COTS scope."""
        # 1. Gap I: FIN-LAB-02 350-400 km/h airframe & head-on corridor rendezvous geometry
        f02 = gap_solver.evaluate_finlab02_high_speed_airframe()
        geom = gap_solver.compute_corridor_rendezvous_geometry_timeline()
        self.assertGreater(f02.excess_thrust_at_400kmh_n, 40.0)
        self.assertLessEqual(f02.airframe_avionics_bom_usd, 5000.0)
        self.assertAlmostEqual(geom.t_gate1_rendezvous_s, 138.0, delta=2.0)
        self.assertAlmostEqual(geom.gate1_rendezvous_range_km, 12.4, delta=1.0)
        self.assertGreaterEqual(geom.cumulative_id_prob_three_gates, 0.85)
        self.assertLessEqual(geom.cost_per_mission_sortie_usd, 50000.0)

        # 2. Gap H: Heated 6.5 s launch shelter & 285 km/h cold-rated COTS fast-climber
        climber = gap_solver.evaluate_heated_nest_and_fast_climber()
        self.assertLessEqual(climber.nest_lid_open_s, 10.0)
        self.assertGreaterEqual(climber.dash_speed_kmh, 280.0)
        self.assertLess(climber.pn_miss_distance_m, 1.0)

        # 3. Gap A: -30 C 5-class acoustic & micro-Doppler library
        sig = gap_solver.evaluate_nordic_winter_signature_library()
        self.assertGreaterEqual(sig.clutter_vs_aircraft_accuracy, 0.95)
        self.assertLessEqual(sig.node_to_c2_latency_s, 2.0)

        # 4. Gap J: Non-RF rotorcraft corridor & substation sensing belt
        belt = gap_solver.evaluate_corridor_non_rf_sensing_belt()
        self.assertGreaterEqual(belt.corridor_detection_range_m, 500.0)
        self.assertGreaterEqual(belt.zero_rf_rotorcraft_detection_prob, 0.90)

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

        # 7. 3D APN closed-loop optical rendezvous & non-pyrotechnic Dyneema soft-net + parachute recovery
        apn = gap_solver.simulate_3d_apn_optical_rendezvous_and_soft_capture()
        self.assertLessEqual(apn.terminal_miss_distance_m, 0.85)
        self.assertTrue(apn.zero_firearms_zero_pyrotechnics)
        self.assertTrue(apn.captured_safely_without_lipo_puncture)

        # 8. [P12-URBAN], FIN-LAB-06B (Offshore Sea State 5), [P11-COAST-2KM] & [P21-SVALBARD]
        urban = gap_solver.evaluate_urban_border_corridor_profile()
        self.assertGreaterEqual(urban.urban_zero_rf_rotorcraft_range_m, 320.0)
        self.assertTrue(urban.china_free_verified)

        usv_b = gap_solver.evaluate_finlab06b_offshore_wave_piercing_usv()
        self.assertEqual(usv_b.max_sea_state, 5)
        self.assertGreaterEqual(usv_b.polar_night_endurance_hours, 140.0)
        self.assertTrue(usv_b.china_free_verified)

        bridge = gap_solver.evaluate_archipelago_2km_optical_strait_bridge()
        self.assertTrue(bridge.iec_60825_class1_eye_safe)
        self.assertGreaterEqual(bridge.snr_clear_10mbps_at_2km_db, 14.0)
        self.assertEqual(bridge.rf_emissions_w, 0.0)

        sv = gap_solver.evaluate_svalbard_permafrost_cairn_node()
        self.assertGreaterEqual(sv.total_battery_endurance_years, 2.0)
        self.assertTrue(sv.svalbard_treaty_art9_compliant)

        # 9. Charter 6-Gap (J, A, H, I, K, L) Hardware-Evidence & COTS Cost-Performance Evaluator
        reval = gap_solver.recalibrate_fin_sig_lib_on_real_trial_data()
        self.assertEqual(reval["evidence_tier"], "REAL_HARDWARE_TRIAL_REVALIDATED_4_OF_4")
        self.assertGreaterEqual(reval["real_trial_samples_ingested"], 5)
        self.assertGreaterEqual(reval["clutter_vs_aircraft_accuracy"], 0.95)

        charter = gap_solver.evaluate_charter_cots_cost_performance_and_trial_gates()
        self.assertTrue(charter["charter_scope_90_10_civilian_compliant"])
        self.assertTrue(charter["sovereign_11_points_excluded"])
        self.assertTrue(charter["all_6_charter_gaps_exit_criteria_met"])
        self.assertEqual(charter["honest_score_today_pts"], 56)
        self.assertEqual(charter["charter_6_gaps_points_gained"], 19)
        self.assertEqual(charter["civilian_ceiling_pts"], 85)
        self.assertLessEqual(
            charter["cost_performance_summary"]["arctic_trail_cots_surrogate_validation_usd"],
            1000.0,
        )
        self.assertGreaterEqual(
            charter["cost_performance_summary"]["cost_reduction_factor_vs_charter_min"],
            8000.0,
        )
        prof = autonomy.generate_arduplane_ark_fpv_param_profile()
        self.assertTrue(prof["allied_gap_l_boards_verified"])
        self.assertIn("Garmin LIDAR-Lite v4 LED", prof["allied_gap_l_boards"]["lidar_landing_altimeter"])

    def test_05_zero_chinese_components_and_opsec_linter(self):
        """Enforce zero Chinese components and zero forbidden region/PII/military strings across public files."""
        forbidden_tokens = [
            chr(110) + "ew " + chr(101) + "ngland",
            chr(107) + "alkilpi",
            "/" + chr(117) + "sers/",
            chr(97) + "ntigravity",
            "." + chr(103) + "emini",
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
            "cost_per_kill",
            "cumulative_pk",
            "counter_fpv",
            "combat_radius",
            "combat idle",
        ]
        checked_files = 0
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [
                d for d in dirs if d not in (".git", "_private", "__pycache__", "tests")
            ]
            for fname in files:
                if fname.endswith((".md", ".py", ".json", ".svg", ".html")):
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

        # Verify docs/images/ contains the 2 CAD blueprints + >=17 sar_design_* plates and zero viz_* legacy charts
        img_dir = os.path.join(REPO_ROOT, "docs", "images")
        self.assertTrue(os.path.isdir(img_dir))
        imgs = sorted(os.listdir(img_dir))
        for img in imgs:
            self.assertFalse(
                img.startswith("viz_"),
                f"Forbidden legacy chart image {img} found in docs/images/",
            )
            img_path = os.path.join(img_dir, img)
            self.assertGreater(os.path.getsize(img_path), 100_000, f"Image {img} too small")
        design_plates = [f for f in imgs if f.startswith("sar_design_")]
        cad_plates = [f for f in imgs if f.startswith("sar_cad_blueprint_")]
        self.assertEqual(len(cad_plates), 2)
        self.assertGreaterEqual(len(design_plates), 17)
        self.assertTrue(
            os.path.exists(
                os.path.join(REPO_ROOT, "docs", "ENGINEERING_DESIGN_AND_ARCHITECTURE.md")
            )
        )

    def test_06_6dof_end_to_end_flight_simulator(self):
        """Verify 6-DOF end-to-end flight dynamics simulator across all 6 configurations and environments."""
        arctic_env = flight_sim.EnvironmentConditions(
            surface_temp_c=-30.0,
            wind_speed_10m_mps=12.0,
            wind_dir_from_deg=45.0,
            turbulence_intensity="MODERATE",
            gust_amplitude_mps=7.0,
            icing_lwc_g_m3=0.25,
            deicer_enabled=True,
        )
        rows = flight_sim.compare_all_configurations(arctic_env)
        self.assertEqual(len(rows), 6)
        for r in rows:
            self.assertTrue(r["mission_success"], f"Config {r['config_id']} failed end-to-end mission")
            self.assertEqual(r["mil_std_level"], 1, f"Config {r['config_id']} failed MIL-STD-1797 Level 1")
            self.assertLessEqual(r["touchdown_vz_mps"], 4.5)
            self.assertLessEqual(r["capsule_cep_m"], 10.0)

        # Verify belly-skid landing and +15 C warm-weather comparison on VARIANT_H_EVO
        warm_env = flight_sim.EnvironmentConditions(
            surface_temp_c=15.0,
            wind_speed_10m_mps=4.0,
            turbulence_intensity="LIGHT",
            gust_amplitude_mps=2.0,
            icing_lwc_g_m3=0.0,
        )
        res_skid = flight_sim.run_end_to_end_6dof_mission(
            config_id="VARIANT_H_EVO",
            env=warm_env,
            launch_mode="DROP_TROLLEY",
            landing_mode="BELLY_SKID",
        )
        self.assertTrue(res_skid.mission_success)
        self.assertEqual(len(res_skid.phase_summary), 8)
        self.assertGreater(res_skid.landing_rollout_m, 5.0)
        self.assertEqual(res_skid.max_ice_accretion_mm, 0.0)

    def test_07_avionics_sensors_interference_and_fdir(self):
        """Verify 3-domain avionics, sensor interference, hardware failure modes, and FDIR recovery."""
        suite_rows = flight_sim.run_avionics_and_failure_mode_suite("VARIANT_H_EVO")
        self.assertEqual(len(suite_rows), 7)
        by_id = {r["preset_id"]: r for r in suite_rows}

        # 1. Clean nominal run has zero FDIR events
        self.assertTrue(by_id["NOMINAL_CLEAN"]["mission_success"])
        self.assertEqual(by_id["NOMINAL_CLEAN"]["fdir_events"], 0)
        self.assertEqual(by_id["NOMINAL_CLEAN"]["final_nav_mode"], "GNSS_INERTIAL_EKF3")

        # 2. EW GNSS Jam & Spoof triggers VIO_BARO_DEM_DEAD_RECKONING and 940 nm Sky-Diode optical link
        ew = by_id["EW_GNSS_JAM_AND_SPOOF"]
        self.assertTrue(ew["mission_success"])
        self.assertEqual(ew["final_nav_mode"], "VIO_BARO_DEM_DEAD_RECKONING")
        self.assertEqual(ew["final_comms_mode"], "SKY_DIODE_OPTICAL_940NM_SILENT")
        self.assertIn("GNSS_SPOOF_REJECTED_VIO", ew["fdir_codes"])

        # 3. IMU1 bias & Mag storm fails over to Bosch BMI088 (IMU2) and rejects mag yaw drift
        imu_row = by_id["IMU1_BIAS_AND_MAG_STORM"]
        self.assertTrue(imu_row["mission_success"])
        self.assertEqual(imu_row["final_active_imu"], "IMU2_BMI088_FAILOVER")
        self.assertIn("MAG_REJECTED_VIO_YAW", imu_row["fdir_codes"])

        # 4. EGT overtemp & Ruddervator jam clamps EGT < 760 C and reallocates control surfaces
        egt_row = by_id["EGT_OVERTEMP_AND_RUDDERVATOR_JAM"]
        self.assertTrue(egt_row["mission_success"])
        self.assertLess(egt_row["max_fadec_egt_c"], 760.0)
        self.assertIn("EGT_THERMAL_DERATE_ACTIVE", egt_row["fdir_codes"])
        self.assertIn("SERVO_JAM_REALLOCATED", egt_row["fdir_codes"])

        # 5. Full Arctic 12-fault stress test passes with FDIR active vs degrades when FDIR disabled
        stress_row = by_id["FULL_ARCTIC_MULTI_FAULT_STRESS"]
        self.assertTrue(stress_row["mission_success"])
        self.assertGreaterEqual(stress_row["fdir_events"], 9)
        self.assertLess(stress_row["capsule_cep_m"], 8.0)

        # Compare against FDIR disabled under spoofing + EGT overtemp
        no_fdir_cfg = flight_sim.InterferenceAndFaultConfig(
            preset_id="UNPROTECTED_SPOOF_AND_EGT",
            fdir_enabled=False,
            gnss_spoofing_active=True,
            gnss_spoof_start_s=25.0,
            gnss_spoof_offset_m=380.0,
            fault_egt_overtemp=True,
            fault_egt_start_s=28.0,
        )
        res_no_fdir = flight_sim.run_end_to_end_6dof_mission(
            config_id="VARIANT_H_EVO",
            faults=no_fdir_cfg,
        )
        self.assertGreater(
            res_no_fdir.avionics_health_summary["max_fadec_egt_c"],
            760.0,
            "Without FDIR thermal derate, EGT overtemp should exceed 760 C redline",
        )
        self.assertGreater(
            res_no_fdir.capsule_landing_error_cep_m,
            50.0,
            "Without EKF3 spoof rejection, GNSS spoofing should pull capsule drop off target",
        )

    def test_08_1000_simulation_envelope_expansion(self):
        """Verify the 1,000-simulation extreme envelope expansion suite (500 baseline vs 500 upgraded COTS runs)."""
        import monte_carlo_1000_envelope_expander as mc1000

        report = mc1000.run_1000_simulation_campaign(seed=20261021)
        self.assertEqual(report["total_simulations_executed"], 1000)

        b_sum = report["cohort_a_baseline_500"]
        e_sum = report["cohort_b_expanded_500"]
        self.assertEqual(b_sum["total_runs"], 500)
        self.assertEqual(e_sum["total_runs"], 500)
        self.assertEqual(b_sum["airframe_survival_rate_pct"], 100.0)
        self.assertEqual(e_sum["airframe_survival_rate_pct"], 100.0)
        self.assertGreaterEqual(e_sum["mission_completion_rate_pct"], 98.0)
        self.assertGreater(e_sum["mission_completion_rate_pct"] - b_sum["mission_completion_rate_pct"], 45.0)
        self.assertLess(e_sum["mean_takeoff_roll_m"], b_sum["mean_takeoff_roll_m"])
        self.assertGreater(e_sum["mean_ld_max"], b_sum["mean_ld_max"])
        self.assertGreater(e_sum["mean_practical_radius_km"], b_sum["mean_practical_radius_km"])
        self.assertGreater(e_sum["fiber_guillotine_events"], 0)

    def test_09_cartridge_c_long_range_blos_and_marsupial_suite(self):
        """Verify Cartridge C (113-240+ km / 70-150+ mi hybrid reach + airborne sky-diode BLOS link) & Marsupial sim."""
        import marsupial_dual_drone_sim as marsupial

        cart_c = sizing.compute_cartridge_c_long_range_hybrid_and_blos_link()
        self.assertEqual(cart_c["mtow_kg"], 14.95)
        self.assertEqual(cart_c["cg_shift_mm"], 0.0)
        self.assertGreaterEqual(cart_c["combined_hybrid_one_way_reach_km"], 240.0)
        self.assertGreaterEqual(cart_c["combined_hybrid_one_way_reach_miles"], 150.0)
        self.assertGreaterEqual(cart_c["terminal_dive_dash_speed_kmh"], 399.0)
        self.assertGreaterEqual(cart_c["airborne_relay_radio_horizon_km"], 250.0)
        self.assertGreaterEqual(cart_c["sky_diode_snr_at_180km_db"], 22.0)
        self.assertGreaterEqual(cart_c["sky_diode_snr_at_240km_db"], 20.0)
        self.assertTrue(cart_c["zero_starlink_dependency"])

        sled_c = sizing.compute_sled_c_long_endurance_4stroke_ferry()
        self.assertEqual(sled_c["mtow_kg"], 14.95)
        self.assertEqual(sled_c["cg_shift_mm"], 0.0)
        self.assertGreaterEqual(sled_c["prop_boom_radial_clearance_mm"], 35.0)
        self.assertGreaterEqual(sled_c["range_with_full_5kg_payload_km"], 1000.0)
        self.assertGreaterEqual(sled_c["max_ferry_range_km"], 2400.0)

        m_res = marsupial.simulate_full_marsupial_mission()
        self.assertTrue(m_res["fit_balance_and_aerodynamics"]["fits_internally_without_oml_change"])
        self.assertTrue(m_res["mid_air_separation_100hz"]["zero_rotor_strike_guaranteed"])
        self.assertTrue(m_res["joint_mission_summary"]["both_aircraft_recovered_safely"])

    def test_10_cnc_cut_sheets_and_arduplane_param_export(self):
        """Verify 1:1 mm CNC/Hot-Wire SVG/DXF cut-sheets and ArduPlane 4.5+ .param export."""
        import json

        cad_dir = os.path.join(REPO_ROOT, "cad")
        svg_path = os.path.join(cad_dir, "finlab02_foam_ribs_and_bulkheads_1to1.svg")
        dxf_path = os.path.join(cad_dir, "finlab02_foam_ribs_and_bulkheads_1to1.dxf")
        json_path = os.path.join(cad_dir, "cnc_foam_and_carbon_cut_schedule.json")
        param_path = os.path.join(cad_dir, "ark_fpv_arduplane_45_sar_jet.param")

        for p in (svg_path, dxf_path, json_path, param_path):
            self.assertTrue(os.path.exists(p), f"Missing CAD/param artifact: {p}")
            self.assertGreater(os.path.getsize(p), 1000, f"Artifact {p} too small")

        with open(json_path, "r", encoding="utf-8") as f:
            cut_meta = json.load(f)
        self.assertEqual(cut_meta["scale"], "1:1_MILLIMETERS")
        self.assertEqual(cut_meta["overall_wingspan_mm"], 2200.0)
        self.assertEqual(cut_meta["cg_x_mm"], 595.0)
        self.assertGreaterEqual(len(cut_meta["wing_and_tail_hotwire_ribs"]), 5)
        self.assertGreaterEqual(len(cut_meta["laser_cut_fuselage_bulkheads"]), 4)

        with open(param_path, "r", encoding="utf-8") as f:
            param_txt = f.read()
        self.assertIn("VTAIL_OUTPUT,3", param_txt)
        self.assertIn("PTCH_LIM_MAX_DEG,25", param_txt)
        self.assertIn("ROLL_LIMIT_DEG,55", param_txt)
        self.assertIn("EK3_SRC1_POSXY,3", param_txt)
        self.assertIn("CHUTE_ENABLED,1", param_txt)


if __name__ == "__main__":
    unittest.main()
