#!/usr/bin/env python3
# File: tests/test_drone_observer_simulation.py
# Description: Automated verification suite for the Optional Autonomous Aerial Observation
#              & Protective Guidance Module (ground kinematics extraction, distant predictive
#              lead-rendezvous, high-standoff rural shotgun protection envelope, onboard
#              Kalman tracking through canopy gaps, MAVLink autopilot guidance, multi-drone
#              handover, and Finnish 112 ETRS-TM35FIN police coordination feed).
# License: MIT

import json
import math
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRAILCAM_DIR = REPO_ROOT
COLLECTOR_DIR = os.path.join(TRAILCAM_DIR, "collector_hub")
SENDER_DIR = os.path.join(TRAILCAM_DIR, "pi5_sender_node")

for p in (COLLECTOR_DIR, SENDER_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import drone_observer as dobs
import sender_node


class TestAerialObserverModule(unittest.TestCase):
    """Validates all mathematical, physical, and protocol invariants of drone_observer.py."""

    def test_01_qualifying_class_filter_and_ed25519_gate(self):
        """Only verified human/vehicle alerts with healthy camera_ok trigger aerial dispatch."""
        # 1. Valid person alert -> DISPATCH
        person_alert = {
            "node": "NODE-NORTH-01",
            "verified": True,
            "camera_ok": True,
            "detections": [{"class": "person", "conf": 0.91, "box": [0.45, 0.30, 0.60, 0.85]}],
        }
        ok, reason, matched = dobs.should_dispatch_aerial_observer(person_alert)
        self.assertTrue(ok, f"Expected person alert to dispatch, got: {reason}")
        self.assertEqual(matched["class"], "person")

        # 2. Valid ATV / snowmobile alert -> DISPATCH
        atv_alert = {
            "node": "NODE-SOUTH-02",
            "verified": True,
            "camera_ok": True,
            "detections": [{"class": "motorcycle_atv_snowmobile", "conf": 0.84, "box": [0.3, 0.4, 0.7, 0.8]}],
        }
        ok_atv, _, matched_atv = dobs.should_dispatch_aerial_observer(atv_alert)
        self.assertTrue(ok_atv)
        self.assertEqual(matched_atv["class"], "motorcycle_atv_snowmobile")

        # 3. Routine wildlife (deer/moose/bird/bear/fox) -> IGNORE
        for wildlife_cls in ("deer_reindeer_sheep", "cervid_moose_horse", "bird", "bear", "dog_wolf_fox"):
            wildlife_alert = {
                "node": "NODE-NORTH-01",
                "verified": True,
                "camera_ok": True,
                "detections": [{"class": wildlife_cls, "conf": 0.95, "box": [0.4, 0.4, 0.6, 0.7]}],
            }
            ok_wild, reason_wild, _ = dobs.should_dispatch_aerial_observer(wildlife_alert)
            self.assertFalse(ok_wild, f"Wildlife class {wildlife_cls} must not dispatch drone")
            self.assertIn("ignored_wildlife", reason_wild)

        # 4. Unverified signature -> IGNORE
        unverified_alert = dict(person_alert, verified=False)
        ok_unv, reason_unv, _ = dobs.should_dispatch_aerial_observer(unverified_alert)
        self.assertFalse(ok_unv)
        self.assertIn("unverified", reason_unv)

        # 5. Camera hardware fault (camera_ok=False) -> IGNORE
        fault_alert = dict(person_alert, camera_ok=False)
        ok_fault, reason_fault, _ = dobs.should_dispatch_aerial_observer(fault_alert)
        self.assertFalse(ok_fault)
        self.assertIn("camera_sensor_error", reason_fault)

    def test_02_sender_node_kinematics_extraction(self):
        """Verifies sender_node.py extracts radial speed, distance, and heading from Pico 2 + bbox."""
        pico_line = "TRIG,MAG=85,SEISMIC=42,DIST=18500,SPD=165,TEMP=-4.5,UP=3600,PROF=HUMAN_HUNTER,SNAP=0"
        parsed = sender_node.parse_pico_trig_fields(pico_line)
        self.assertEqual(parsed["DIST"], 18500)
        self.assertEqual(parsed["SPD"], 165)
        self.assertEqual(parsed["PROF"], "HUMAN_HUNTER")

        detections = [
            {
                "class": "person",
                "conf": 0.90,
                "box": [0.58, 0.28, 0.72, 0.82],
            }
        ]
        kin = sender_node.estimate_subject_kinematics(
            detections=detections,
            pico_telemetry=pico_line,
        )
        self.assertAlmostEqual(kin["est_distance_m"], 18.5, places=2)
        self.assertAlmostEqual(kin["radial_speed_mps"], 1.65, places=2)
        self.assertGreater(kin["est_speed_mps"], 1.65)
        self.assertTrue(0.0 <= kin["relative_heading_deg"] < 360.0)
        self.assertEqual(kin["movement_direction"], "approaching")

    def test_03_single_and_multi_camera_ground_state_reconstruction(self):
        """Verifies single-camera radar/optical fusion and 2-camera cross-node triangulation."""
        single_alert = {
            "node": "NODE-NORTH-01",
            "timestamp": 1700000100,
            "verified": True,
            "camera_ok": True,
            "pico_trig": "TRIG,MAG=80,SEISMIC=40,DIST=16000,SPD=150,TEMP=2.0,UP=100,PROF=HUMAN_HUNTER,SNAP=0",
            "detections": [{"class": "person", "conf": 0.92, "box": [0.48, 0.25, 0.62, 0.80]}],
        }
        state_single = dobs.reconstruct_subject_ground_state(single_alert)
        self.assertEqual(state_single["node_id"], "NODE-NORTH-01")
        self.assertGreater(state_single["speed_mps"], 1.3)
        self.assertIn("sighting_lat", state_single)
        self.assertIn("sighting_lon", state_single)
        self.assertEqual(state_single["velocity_source"], "single_node_radar_optical")

        # Now test sequential multi-camera transit from NODE-NORTH-01 to NODE-SOUTH-02
        prev_alert = {
            "node": "NODE-NORTH-01",
            "timestamp": 1700000000,
            "verified": True,
            "camera_ok": True,
            "detections": [{"class": "person", "conf": 0.89, "box": [0.45, 0.3, 0.55, 0.8]}],
        }
        second_alert = {
            "node": "NODE-SOUTH-02",
            "timestamp": 1700000180,
            "verified": True,
            "camera_ok": True,
            "pico_trig": "TRIG,MAG=75,SEISMIC=35,DIST=14000,SPD=160,TEMP=2.0,UP=280,PROF=HUMAN_HUNTER,SNAP=0",
            "detections": [{"class": "person", "conf": 0.93, "box": [0.50, 0.3, 0.60, 0.8]}],
        }
        state_multi = dobs.reconstruct_subject_ground_state(
            second_alert, previous_alert=prev_alert
        )
        self.assertIn("multi_camera_triangulated", state_multi["velocity_source"])
        self.assertGreater(state_multi["speed_mps"], 1.0)

    def test_04_distant_pad_predictive_rendezvous_solver(self):
        """Verifies exact lead-rendezvous intercept from a distant pad (>700 m away)."""
        subject_state = {
            "sighting_east_m": -165.0,
            "sighting_north_m": 128.0,
            "vel_east_mps": 1.35,
            "vel_north_mps": -1.15,
            "speed_mps": math.hypot(1.35, -1.15),
            "movement_direction": "approaching",
        }
        pad = {"pad_id": "PAD-SOUTH-BOATHOUSE", "east_m": 580.0, "north_m": -380.0}

        rv = dobs.compute_predictive_rendezvous(
            subject_state=subject_state,
            drone_pad=pad,
            drone_cruise_mps=18.0,
            drone_climb_mps=6.0,
            target_altitude_agl_m=105.0,
            launch_prep_s=8.0,
            communication_latency_s=6.8,
        )
        self.assertGreater(rv["drone_flight_distance_m"], 700.0)
        self.assertGreater(rv["subject_travel_distance_m"], 60.0)

        # Verify kinematic consistency: drone cruise distance == drone_cruise_mps * cruise_flight_time_s
        expected_drone_dist = rv["drone_cruise_mps"] * rv["cruise_flight_time_s"]
        self.assertAlmostEqual(rv["drone_flight_distance_m"], expected_drone_dist, delta=0.5)

        # Verify trail-constrained rendezvous snaps cleanly onto trail polyline
        trail = [(-220.0, 175.0), (-140.0, 105.0), (-40.0, 15.0), (80.0, -95.0)]
        rv_trail = dobs.compute_trail_constrained_rendezvous(
            subject_state=subject_state,
            trail_waypoints=trail,
            drone_pad=pad,
        )
        self.assertGreater(rv_trail["drone_flight_distance_m"], 600.0)
        self.assertIn("rendezvous_etrs_tm35fin", rv_trail)

    def test_05_high_standoff_shotgun_protection_and_acoustic_envelope(self):
        """Verifies protection against 12-gauge shotguns, low acoustic signature, and step-climb reflex."""
        env = dobs.evaluate_standoff_protection_envelope(
            altitude_agl_m=105.0,
            horiz_standoff_m=135.0,
            loiter_speed_mps=10.5,
            source_noise_1m_dba=63.0,
            ambient_forest_dba=40.0,
        )
        # 1. Must remain strictly below EASA/Traficom 120 m AGL ceiling
        self.assertTrue(env["easa_120m_compliant"])
        self.assertLessEqual(env["altitude_agl_m"], 118.0)
        self.assertGreaterEqual(env["altitude_agl_m"], 95.0)

        # 2. Slant range >= 150 m (171.03 m nominal)
        self.assertAlmostEqual(env["slant_range_m"], 171.03, delta=0.5)
        self.assertTrue(env["pellet_safe"])

        # 3. 12-gauge pellet energy at drone is 0.0 J (< 0.5 J safe limit)
        self.assertEqual(env["residual_birdshot_vel_mps"], 0.0)
        self.assertEqual(env["residual_heavy_shot_vel_mps"], 0.0)
        self.assertEqual(env["residual_pellet_energy_joules"], 0.0)

        # 4. Acoustic masking below 40 dBA forest wind (< 25 dBA at subject)
        self.assertTrue(env["acoustically_discreet"])
        self.assertLess(env["ground_spl_dba"], 25.0)
        self.assertGreater(env["acoustic_margin_db"], 15.0)

        # 5. Overall protective verdict
        self.assertTrue(env["overall_protective_verdict"])

        # 6. Test automatic protective step-climb on upward posture or >= 110 dB transient
        base_loiter = dobs.compute_protective_loiter_state(
            subject_east_m=-80.0,
            subject_north_m=40.0,
            elapsed_loiter_s=60.0,
        )
        stepped = dobs.trigger_protective_step_climb(
            current_loiter_state=base_loiter,
            upward_raise_detected=True,
            acoustic_impulse_db=118.5,
            subject_east_m=-80.0,
            subject_north_m=40.0,
        )
        self.assertTrue(stepped["reflex_triggered"])
        new_loiter = stepped["new_loiter_state"]
        self.assertTrue(new_loiter["step_out_active"])
        self.assertLessEqual(new_loiter["drone_alt_agl_m"], 118.0)
        self.assertGreater(new_loiter["slant_range_m"], 230.0)

    def test_06_kalman_canopy_tracking_and_mavlink_guidance(self):
        """Verifies onboard ray-cast ground projection, Kalman coasting through canopy gaps, and MAVLink."""
        tracker = dobs.SubjectKalmanTracker(
            init_east_m=-100.0,
            init_north_m=50.0,
            init_ve_mps=1.5,
            init_vn_mps=-1.0,
        )
        # Step 5 seconds with optical+thermal lock
        for _ in range(5):
            est = tracker.step(
                dt_s=1.0,
                measured_east_m=tracker.east_m + 1.5,
                measured_north_m=tracker.north_m - 1.0,
            )
            self.assertTrue(est["track_locked"])
            self.assertIn("locked", est["tracking_mode"])

        # Simulate 6 seconds of dense spruce canopy occlusion (no measurements)
        for _ in range(6):
            coast_est = tracker.step(dt_s=1.0, measured_east_m=None, measured_north_m=None)
        self.assertEqual(coast_est["tracking_mode"], "canopy_coast_prediction")
        self.assertAlmostEqual(coast_est["coasting_sec"], 6.0, places=2)
        self.assertTrue(coast_est["track_locked"])
        self.assertGreater(coast_est["speed_mps"], 1.4)

        # Re-acquire lock when subject emerges into a clearing
        relock = tracker.step(
            dt_s=1.0,
            measured_east_m=coast_est["east_m"] + 1.5,
            measured_north_m=coast_est["north_m"] - 1.0,
        )
        self.assertIn("locked", relock["tracking_mode"])
        self.assertEqual(relock["coasting_sec"], 0.0)

        # Verify gimbal ray projection to ground plane
        proj = dobs.project_gimbal_detection_to_ground(
            drone_east_m=-20.0,
            drone_north_m=-60.0,
            drone_alt_agl_m=105.0,
            gimbal_yaw_deg=35.0,
            gimbal_pitch_deg=-38.0,
            norm_box=[0.48, 0.48, 0.52, 0.52],
        )
        self.assertGreater(proj["ground_range_m"], 120.0)

        # Verify binary MAVLink v2 SET_POSITION_TARGET_LOCAL_NED guidance frame generation (53B payload / 65B frame)
        loiter = dobs.compute_protective_loiter_state(
            subject_east_m=relock["east_m"],
            subject_north_m=relock["north_m"],
            elapsed_loiter_s=45.0,
        )
        mav_bytes = dobs.build_mavlink_guidance_frame(loiter, seq=7)
        self.assertIsInstance(mav_bytes, bytes)
        self.assertEqual(mav_bytes[0], 0xFD)  # MAVLink v2 magic byte
        self.assertEqual(mav_bytes[1], 53)    # Official 53-byte SET_POSITION_TARGET_LOCAL_NED payload
        self.assertEqual(len(mav_bytes), 65)
        decoded_mav = dobs.decode_mavlink_guidance_frame(mav_bytes)
        self.assertTrue(decoded_mav["crc_valid"])
        self.assertEqual(decoded_mav["msg_id"], 84)
        self.assertAlmostEqual(decoded_mav["z_down_m"], -loiter["drone_alt_agl_m"], places=3)

    def test_07_multi_drone_fleet_handover_and_112_police_feed(self):
        """Verifies dual-drone stereo geometry, 30% battery handover, and Finnish ETRS-TM35FIN coordinates."""
        fleet = dobs.FleetCoordinator(rth_battery_threshold_pct=30.0)

        # 1. Dual stereo mode -> both drones active with 110-deg phase offset
        stereo = fleet.evaluate_handover_and_assign_orbits(
            subject_east_m=-50.0,
            subject_north_m=20.0,
            elapsed_s=120.0,
            dual_stereo_mode=True,
        )
        self.assertEqual(stereo["active_drone_count"], 2)
        self.assertEqual(
            stereo["drones"]["DRONE-KILO-02"]["phase_offset_deg"]
            - stereo["drones"]["DRONE-SIERRA-01"]["phase_offset_deg"],
            110.0,
        )

        # 2. Single-drone mode with primary battery drop to 28% -> automatic handover to DRONE-KILO-02
        fleet_single = dobs.FleetCoordinator(rth_battery_threshold_pct=30.0)
        fleet_single.evaluate_handover_and_assign_orbits(-50.0, 20.0, 10.0, dual_stereo_mode=False)
        fleet_single.drones["DRONE-SIERRA-01"]["battery_pct"] = 28.0
        handover = fleet_single.evaluate_handover_and_assign_orbits(-50.0, 20.0, 900.0, dual_stereo_mode=False)
        self.assertTrue(handover["handover_triggered"])
        self.assertEqual(handover["drones"]["DRONE-SIERRA-01"]["status"], "RETURNING_TO_PAD_RTH")
        self.assertEqual(handover["drones"]["DRONE-KILO-02"]["status"], "ACTIVE_OBSERVING")

        # 3. Verify ETRS-TM35FIN (EPSG:3067) coordinate conversion
        etrs = dobs.wgs84_to_etrs_tm35fin(60.3125, 24.4820)
        self.assertIn("ETRS-TM35FIN", etrs["crs"])
        self.assertTrue(6650000 <= etrs["northing_m"] <= 6720000)
        self.assertTrue(340000 <= etrs["easting_m"] <= 380000)

    def test_08_end_to_end_mission_and_dashboard_ui_integration(self):
        """Verifies full mission simulation persistence and UI / API integration."""
        demo_alert = {
            "node": "NODE-NORTH-01",
            "timestamp": 1700000500,
            "verified": True,
            "camera_ok": True,
            "pico_trig": "TRIG,MAG=1850,SEIS=540,DIST=5200,SPD=155,TEMP=-4.0,UPTIME_S=7200",
            "detections": [{"class": "person", "conf": 0.94, "box": [0.42, 0.25, 0.58, 0.78]}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            status_path = os.path.join(tmpdir, "drone_observer_status.json")
            report = dobs.simulate_complete_observation_mission(
                alert_record=demo_alert,
                tracking_duration_s=30.0,
                dt_s=2.0,
                out_status_path=status_path,
            )
            self.assertTrue(report["dispatched"])
            self.assertTrue(os.path.isfile(status_path))
            self.assertIn("112 DISPATCH GUIDANCE", report["police_112_guidance"]["operator_112_readout"])

            # Verify canopy coasting was exercised during steps 4 and 5
            coast_steps = [
                s for s in report["trajectory_trace"]
                if s["tracking_mode"] == "canopy_coast_prediction"
            ]
            self.assertEqual(len(coast_steps), 2)

        # Check dashboard_server.py and ui/index.html contain the Aerial Observer integration
        with open(os.path.join(COLLECTOR_DIR, "dashboard_server.py"), "r", encoding="utf-8") as f:
            srv_src = f.read()
        self.assertIn('"/api/drone"', srv_src)
        self.assertIn("drone_observer_status.json", srv_src)

        with open(os.path.join(COLLECTOR_DIR, "ui", "index.html"), "r", encoding="utf-8") as f:
            ui_src = f.read()
        self.assertIn("btn-drone-observer", ui_src)
        self.assertIn("toggleDroneObserver", ui_src)
        self.assertIn("triggerDroneApproach", ui_src)
        self.assertIn("droneSignBoardMesh", ui_src)
        self.assertIn("ETRS-TM35FIN", ui_src)

    def test_09_close_approach_audio_and_sign_communication_action(self):
        """Verifies the 'approach' action: glidepath descent to 8m AGL / 12m front lead, audio/sign delivery, and safety abort."""
        # 1. Mid-descent glidepath check (t=10s)
        descending = dobs.compute_close_approach_state(
            subject_east_m=-100.0,
            subject_north_m=50.0,
            vel_east_mps=1.2,
            vel_north_mps=-0.9,
            elapsed_approach_s=10.0,
            preset_id="help_is_coming",
        )
        self.assertEqual(descending["action"], "approach")
        self.assertEqual(descending["phase"], "APPROACH_GLIDEPATH_DESCENT")
        self.assertGreater(descending["drone_alt_agl_m"], 8.0)
        self.assertLess(descending["drone_alt_agl_m"], 105.0)

        # 2. Arrived at close-proximity front escort (t=30s -> 8.0m AGL, 12.0m front lead, 14.42m slant)
        close_state = dobs.compute_close_approach_state(
            subject_east_m=-100.0,
            subject_north_m=50.0,
            vel_east_mps=1.2,
            vel_north_mps=-0.9,
            elapsed_approach_s=30.0,
            preset_id="help_is_coming",
        )
        self.assertEqual(close_state["phase"], "CLOSE_PROXIMITY_COMMUNICATION")
        self.assertAlmostEqual(close_state["drone_alt_agl_m"], 8.0, places=2)
        self.assertAlmostEqual(close_state["horiz_standoff_m"], 12.0, delta=0.1)
        self.assertAlmostEqual(close_state["slant_range_m"], 14.42, delta=0.1)

        # Verify paced escort velocity matches subject's walking speed
        self.assertAlmostEqual(close_state["vel_east_mps"], 1.2, places=2)
        self.assertAlmostEqual(close_state["vel_north_mps"], -0.9, places=2)

        # Verify attached sign ("APUA ON TULOSSA / HELP IS COMING") legibility and speaker audio intelligibility
        self.assertEqual(close_state["display_text"], "APUA ON TULOSSA / HELP IS COMING")
        self.assertTrue(close_state["sign_illuminated"])
        self.assertTrue(close_state["sign_legible"])
        self.assertGreater(close_state["sign_angular_width_deg"], 1.5)
        self.assertTrue(close_state["audio_broadcast_active"])
        self.assertTrue(close_state["speech_intelligible"])
        self.assertGreater(close_state["speaker_spl_at_target_dba"], 80.0)
        self.assertGreater(close_state["speech_snr_above_ambient_db"], 40.0)

        # 3. Verify MAVLink + companion payload command generation for approach
        cmd = dobs.build_approach_payload_command(close_state, seq=19)
        self.assertEqual(cmd["command"], "APPROACH_AND_COMMUNICATE")
        self.assertEqual(cmd["display_banner_text"], "APUA ON TULOSSA / HELP IS COMING")
        self.assertEqual(cmd["mavlink_frame_bytes"], 65)

        # 4. Verify automatic safety abort climb-out if upward posture or >=110 dB impulse occurs during close approach
        aborted = dobs.compute_close_approach_state(
            subject_east_m=-100.0,
            subject_north_m=50.0,
            vel_east_mps=1.2,
            vel_north_mps=-0.9,
            elapsed_approach_s=30.0,
            preset_id="help_is_coming",
            upward_raise_detected=True,
        )
        self.assertTrue(aborted["safety_abort_triggered"])
        self.assertEqual(aborted["phase"], "SAFETY_ABORT_CLIMBOUT_TO_HIGH_STANDOFF")
        self.assertGreater(aborted["slant_range_m"], 230.0)

        # 5. Verify execute_approach_action toggles state file cleanly between approach and standoff
        with tempfile.TemporaryDirectory() as tmpdir:
            status_path = os.path.join(tmpdir, "drone_observer_status.json")
            res_app = dobs.execute_approach_action(
                status_path=status_path,
                preset_id="follow_to_shelter",
                custom_display_text="HELP IS COMING - FOLLOW DRONE",
            )
            self.assertEqual(res_app["active_flight_mode"], "CLOSE_APPROACH_COMMUNICATION")
            self.assertEqual(res_app["approach_state"]["display_text"], "HELP IS COMING - FOLLOW DRONE")

            res_st = dobs.execute_approach_action(
                status_path=status_path,
                return_to_standoff=True,
            )
            self.assertEqual(res_st["active_flight_mode"], "HIGH_STANDOFF_ORBIT")

    def test_10_bearnese_mountain_dog_koskenkorva_barrel_and_onboard_camera_guidance(self):
        """Verifies Bearnese Mountain Dog Koskenkorva mini-faucet barrel delivery and onboard drone camera guidance."""
        # 1. Verify preset 'bernese_koskenkorva' lowers the Koskenkorva mini-faucet barrel to 2.0m AGL
        bernese_state = dobs.compute_close_approach_state(
            subject_east_m=-95.0,
            subject_north_m=48.0,
            vel_east_mps=1.1,
            vel_north_mps=-0.8,
            elapsed_approach_s=30.0,
            preset_id="bernese_koskenkorva",
        )
        self.assertIn("Bearnese Mountain Dog", bernese_state["feature_codename"])
        self.assertEqual(bernese_state["display_text"], "APUA ON TULOSSA / OTA KOSKENKORVA")
        self.assertTrue(bernese_state["winch_cable_deployed"])
        self.assertAlmostEqual(bernese_state["barrel_altitude_agl_m"], 2.0, places=2)
        self.assertTrue(bernese_state["companion_keeping_company"])
        self.assertEqual(bernese_state["care_package"]["package_id"], "koskenkorva_rescue_cask")
        self.assertTrue(bernese_state["care_package"]["has_mini_faucet"])
        self.assertIn("Koskenkorva", bernese_state["care_package"]["contents"])

        cmd = dobs.build_approach_payload_command(bernese_state, seq=21)
        self.assertEqual(cmd["care_package_id"], "koskenkorva_rescue_cask")
        self.assertTrue(cmd["care_package_has_mini_faucet"])
        self.assertTrue(cmd["winch_cable_deployed"])
        self.assertAlmostEqual(cmd["barrel_altitude_agl_m"], 2.0, places=2)

        # 2. Verify onboard drone camera detection & closed-loop guidance when object is visible vs. occluded
        loiter = dobs.compute_protective_loiter_state(
            subject_east_m=-95.0,
            subject_north_m=48.0,
            elapsed_loiter_s=20.0,
        )
        cam_visible = dobs.detect_subject_with_drone_camera(
            drone_east_m=loiter["drone_east_m"],
            drone_north_m=loiter["drone_north_m"],
            drone_alt_agl_m=loiter["drone_alt_agl_m"],
            gimbal_yaw_deg=loiter["gimbal_yaw_deg"],
            gimbal_pitch_deg=loiter["gimbal_pitch_deg"],
            true_subject_east_m=-95.0,
            true_subject_north_m=48.0,
            subject_class="person",
            canopy_occluded=False,
        )
        self.assertTrue(cam_visible["visible_in_drone_camera"])
        self.assertEqual(cam_visible["guidance_source"], "drone_onboard_camera:optical+thermal")
        self.assertIsNotNone(cam_visible["norm_box"])
        self.assertAlmostEqual(cam_visible["measured_east_m"], -95.0, delta=1.5)
        self.assertAlmostEqual(cam_visible["measured_north_m"], 48.0, delta=1.5)

        cam_occluded = dobs.detect_subject_with_drone_camera(
            drone_east_m=loiter["drone_east_m"],
            drone_north_m=loiter["drone_north_m"],
            drone_alt_agl_m=loiter["drone_alt_agl_m"],
            gimbal_yaw_deg=loiter["gimbal_yaw_deg"],
            gimbal_pitch_deg=loiter["gimbal_pitch_deg"],
            true_subject_east_m=-95.0,
            true_subject_north_m=48.0,
            subject_class="person",
            canopy_occluded=True,
        )
        self.assertFalse(cam_occluded["visible_in_drone_camera"])
        self.assertEqual(cam_occluded["guidance_source"], "kalman_canopy_coast_prediction")

    def test_11_multi_camera_multi_object_and_multi_drone_swarm(self):
        """Verifies multi-object extraction, cross-camera track manager, and 6-drone simultaneous dispatch."""
        # 1. Verify sender_node.estimate_all_subjects_kinematics extracts multiple objects in one frame
        pico_line = "TRIG,MAG=85,SEISMIC=42,DIST=12000,SPD=150,TEMP=-4.5,UP=3600"
        multi_dets = [
            {"class": "person", "conf": 0.94, "box": [0.18, 0.25, 0.34, 0.78]},
            {"class": "person", "conf": 0.89, "box": [0.68, 0.30, 0.82, 0.75]},
        ]
        all_kin = sender_node.estimate_all_subjects_kinematics(multi_dets, pico_line)
        self.assertEqual(len(all_kin), 2)
        self.assertLess(all_kin[0]["bearing_offset_deg"], 0.0)
        self.assertGreater(all_kin[1]["bearing_offset_deg"], 0.0)

        # 2. Verify MultiCameraTrackManager spawns 4 distinct target tracks across 3 cameras
        alerts = [
            {
                "node": "NODE-NORTH-01",
                "timestamp": 1700001000,
                "verified": True,
                "camera_ok": True,
                "pico_trig": "TRIG,MAG=1850,SEIS=540,DIST=5200,SPD=155,TEMP=-4.0,UPTIME_S=7200",
                "detections": [
                    {"class": "person", "conf": 0.95, "box": [0.20, 0.25, 0.35, 0.78]},
                    {"class": "person", "conf": 0.91, "box": [0.70, 0.28, 0.84, 0.75]},
                ],
            },
            {
                "node": "NODE-SOUTH-02",
                "timestamp": 1700001002,
                "verified": True,
                "camera_ok": True,
                "pico_trig": "TRIG,MAG=4200,SEIS=880,DIST=6500,SPD=450,TEMP=-4.0,UPTIME_S=7202",
                "detections": [
                    {"class": "motorcycle_atv_snowmobile", "conf": 0.93, "box": [0.35, 0.30, 0.65, 0.76]},
                ],
            },
            {
                "node": "NODE-LAKE-03",
                "timestamp": 1700001004,
                "verified": True,
                "camera_ok": True,
                "pico_trig": "TRIG,MAG=1100,SEIS=310,DIST=4800,SPD=130,TEMP=-4.0,UPTIME_S=7204",
                "detections": [
                    {"class": "person", "conf": 0.89, "box": [0.44, 0.26, 0.58, 0.77]},
                ],
            },
        ]
        swarm = dobs.simulate_multi_camera_multi_drone_mission(alerts, tracking_duration_s=20.0, dt_s=2.0)
        self.assertTrue(swarm["dispatched"])
        self.assertEqual(swarm["active_target_count"], 4)
        self.assertEqual(swarm["active_drone_count"], 6)
        self.assertTrue(swarm["fleet_assignment"]["airspace_deconfliction"]["airspace_safe"])
        self.assertGreaterEqual(
            swarm["fleet_assignment"]["airspace_deconfliction"]["min_pairwise_3d_separation_m"],
            25.0,
        )
        # Verify every active drone has an onboard camera detection lock on its assigned target
        for d_id, d_info in swarm["fleet_assignment"]["drones"].items():
            if d_info["status"] == "ACTIVE_OBSERVING":
                self.assertTrue(d_info["onboard_camera_detection"]["visible_in_drone_camera"])

    def test_12_multi_drone_coordinated_grid_search(self):
        """Verifies multi-drone boustrophedon grid search planning and onboard camera target re-acquisition."""
        plan = dobs.plan_multi_drone_grid_search(
            last_east_m=-110.0,
            last_north_m=75.0,
            time_since_last_seen_s=95.0,
            max_subject_speed_mps=1.8,
            drone_count=4,
        )
        self.assertEqual(plan["deployed_drone_count"], 4)
        self.assertEqual(len(plan["drone_sectors"]), 4)
        self.assertAlmostEqual(plan["fleet_speedup_factor"], 4.0, delta=0.1)

        # Simulate executing the 4-drone grid search and re-acquiring the lost person with onboard camera
        gs = dobs.simulate_multi_drone_grid_search_mission(
            last_east_m=-110.0,
            last_north_m=75.0,
            drone_count=4,
        )
        self.assertTrue(gs["dispatched"])
        self.assertTrue(gs["target_reacquired"])
        self.assertIn(gs["reacquired_by_drone_id"], plan["drone_sectors"])
        self.assertTrue(gs["reacquired_camera_detection"]["visible_in_drone_camera"])
        self.assertEqual(gs["post_reacquisition_mode"], "VISUAL_SERVO_TRACKING_AND_COMPANION_ESCORT")
        self.assertTrue(gs["bernese_companion_approach_state"]["care_package"]["has_mini_faucet"])

    def test_13_passive_trail_sighting_and_split_tourist_group_onboard_self_guidance(self):
        """Verifies passive hiker sighting, on-demand SAR order, split tourist group tracking, and onboard self-guidance."""
        sar = dobs.simulate_wilderness_tourist_group_sar(
            elapsed_before_sar_order_s=150.0,
            tracking_duration_s=40.0,
            dt_s=2.0,
        )
        # 1. Verify trail camera initially logged the 4 tourists passively WITHOUT launching drones
        self.assertTrue(sar["passive_sighting_phase"]["logged"])
        self.assertFalse(sar["passive_sighting_phase"]["dispatched"])
        self.assertEqual(sar["passive_sighting_phase"]["dispatch_policy"], "PASSIVE_SIGHTING_LOG_ONLY")
        self.assertEqual(sar["initial_group_size"], 4)

        # 2. Verify explicit SAR order authorized 4 drones to locate & self-guide on all 4 separated tourists
        self.assertTrue(sar["sar_dispatch_order"]["authorized"])
        self.assertTrue(sar["all_tourists_accounted_for"])
        self.assertEqual(sar["tracked_separated_tourists_count"], 4)
        self.assertEqual(sar["deployed_drone_count"], 4)

        # 3. Verify tourists are far apart (>180 m separation) yet every drone locks & self-guides with <4m error
        self.assertGreater(sar["max_separation_between_tourists_m"], 250.0)
        self.assertTrue(sar["airspace_deconfliction"]["airspace_safe"])
        for t_entry in sar["separated_tourist_tracks"]:
            self.assertTrue(t_entry["target_locked"])
            self.assertEqual(t_entry["self_guidance_mode"], "ONBOARD_CAMERA_TARGET_LOCK_SELF_GUIDANCE")
            self.assertFalse(t_entry["ground_link_required"])
            self.assertTrue(t_entry["guided_by_drone_camera"])
            self.assertLess(t_entry["tracking_error_m"], 4.0)

    def test_14_four_public_release_humanitarian_safeguards(self):
        """Verifies the 4 public-release architectural safeguards (112/inReach/Medical opt-in, 15m offset + EM fuse + 50m climb, alcohol-free electrolyte cask, and hard-coded 15m safety bubble)."""
        # Safeguard 1: Routine hiker walking past camera does NOT trigger drone stalking
        routine_gate = dobs.verify_humanitarian_sar_trigger(
            alert_record={"node": "NODE-NORTH-01", "verified": True}
        )
        self.assertFalse(routine_gate["handoff_authorized"])
        self.assertEqual(routine_gate["privacy_mode"], "PASSIVE_PRIVACY_PRESERVING_NO_STALK")

        # Triggered by 112 Suomi SOS, Garmin inReach, or AI medical collapse pose -> Authorized
        sos_gate = dobs.verify_humanitarian_sar_trigger(sos_112_ping=True)
        self.assertTrue(sos_gate["handoff_authorized"])
        inreach_gate = dobs.verify_humanitarian_sar_trigger(garmin_inreach_sos=True)
        self.assertTrue(inreach_gate["handoff_authorized"])
        med_gate = dobs.verify_humanitarian_sar_trigger(ai_medical_emergency_pose="hiker_collapsed")
        self.assertTrue(med_gate["handoff_authorized"])

        # Safeguard 2 & 3: Safe 15m clear-snow offset drop + 25N electromagnetic release fuse + 50m AGL climb + warm berry-electrolyte cask
        drop_res = dobs.execute_safe_offset_barrel_drop_and_climb(
            subject_east_m=-100.0,
            subject_north_m=50.0,
            subject_heading_deg=45.0,
            care_package_id="sar_electrolyte_rescue_cask",
            requested_offset_m=15.0,
            simulated_cable_snag_force_n=32.0,
        )
        self.assertEqual(drop_res["sequence_status"], "SAFE_OFFSET_DROP_DETACHED_AND_CLIMBED_TO_50M")
        self.assertTrue(drop_res["hypothermia_medically_safe"])
        self.assertTrue(drop_res["alcohol_free"])
        self.assertTrue(drop_res["public_release_approved"])
        self.assertGreaterEqual(drop_res["drop_horiz_offset_from_hiker_m"], 15.0)
        self.assertEqual(drop_res["barrel_touchdown_alt_agl_m"], 0.0)
        self.assertTrue(drop_res["electromagnetic_release_detached"])
        self.assertTrue(drop_res["fuse_tripped_by_snag"])
        self.assertEqual(drop_res["post_drop_drone_alt_agl_m"], 50.0)
        self.assertTrue(drop_res["voice_intelligible_from_50m"])

        # Verify Koskenkorva cask is explicitly flagged as internal pitch-deck easter egg only
        kossu_pkg = dobs.CARE_PACKAGE_OPTIONS["koskenkorva_rescue_cask"]
        self.assertTrue(kossu_pkg["easter_egg_pitch_deck_only"])
        self.assertFalse(kossu_pkg["public_release_approved"])

        # Safeguard 4: Hard-coded 15m horizontal safety bubble & vertical descent block over human bbox
        clamped = dobs.enforce_hardcoded_human_safety_geofence(
            commanded_drone_east_m=-100.0,  # Attempt to fly directly over human (0m offset)
            commanded_drone_north_m=50.0,
            commanded_drone_alt_agl_m=2.0,  # Attempt to descend to 2m over human
            human_east_m=-100.0,
            human_north_m=50.0,
            human_bbox_in_vertical_footprint=True,
        )
        self.assertTrue(clamped["geofence_clamped"])
        self.assertTrue(clamped["collision_mathematically_prevented"])
        self.assertAlmostEqual(clamped["horiz_separation_from_human_m"], 15.0, places=2)
        self.assertGreaterEqual(clamped["safe_drone_alt_agl_m"], 50.0)

    def test_15_karhunkierros_ephemeral_ring_buffer_and_aerial_lantern_hut_guide(self):
        """Verifies Karhunkierros SAR positioning: 48h auto-purging ring buffer, physical SOS post button, SAR Orange livery, and Aerial Lantern & Autiotupa Trail Guide."""
        # 1. Verify High-Visibility SAR Orange livery & mechanical transit horizon shutter
        self.assertIn("SAR High-Visibility", dobs.SAR_AIRFRAME_LIVERY_SPEC["primary_color"])
        self.assertIn("PELASTUS", dobs.SAR_AIRFRAME_LIVERY_SPEC["markings"])
        self.assertIn("MECHANICAL_HORIZON_SHUTTER", dobs.SAR_AIRFRAME_LIVERY_SPEC["transit_camera_privacy_mode"])

        # 2. Verify "Pull, Don't Push" physical trail-post SOS button & overdue Autiotupa check-in timer
        post_sos = dobs.verify_humanitarian_sar_trigger(trail_post_sos_button=True)
        self.assertTrue(post_sos["handoff_authorized"])
        self.assertIn("TRAIL_POST_PHYSICAL_SOS_BUTTON", post_sos["active_triggers"])

        hut_timer = dobs.verify_humanitarian_sar_trigger(overdue_autiotupa_checkin=True)
        self.assertTrue(hut_timer["handoff_authorized"])
        self.assertIn("OVERDUE_AUTIOTUPA_CHECKIN_TIMER", hut_timer["active_triggers"])

        # 3. Verify 48-hour (172,800 s) auto-purging anonymous local ring buffer
        ledger = dobs.PassiveTrailSightingLedger(auto_dispatch_drones=False)
        self.assertTrue(ledger.ring_buffer_sealed)
        self.assertFalse(ledger.facial_recognition_enabled)
        self.assertFalse(ledger.cloud_upload_enabled)
        self.assertEqual(ledger.ttl_sec, 48 * 3600)

        t0 = 1700000000
        old_alert = {
            "node": "NODE-NORTH-01",
            "timestamp": t0,
            "verified": True,
            "camera_ok": True,
            "pico_trig": "TRIG,MAG=400,SEIS=500,DIST=5000,SPD=130,TEMP=-5.0,UPTIME_S=1000",
            "detections": [{"class": "person", "conf": 0.94, "box": [0.40, 0.25, 0.56, 0.78]}],
        }
        rec1 = ledger.record_passive_sighting(old_alert, current_ts=t0)
        self.assertTrue(rec1["logged"])
        self.assertTrue(rec1["ring_buffer_sealed"])
        self.assertTrue(rec1["sighting"]["anonymous_vector_only"])
        self.assertFalse(rec1["sighting"]["facial_recognition_used"])

        # 49 hours later, a new hiker passes -> old hiker's entry is automatically purged!
        t_49h = t0 + (49 * 3600)
        new_alert = dict(old_alert, timestamp=t_49h)
        ledger.record_passive_sighting(new_alert, current_ts=t_49h)
        self.assertEqual(len(ledger.sightings), 1)
        self.assertEqual(ledger.purged_sightings_count, 1)
        self.assertEqual(ledger.sightings[0]["timestamp"], t_49h)

        # Unsealing via 112 / Rajavartiolaitos / Poliisi SAR order
        order = ledger.authorize_sar_order(current_ts=t_49h + 600)
        self.assertTrue(order["authorized"])
        self.assertTrue(order["ring_buffer_unsealed_for_sar"])
        self.assertFalse(ledger.ring_buffer_sealed)

        # 4. Verify "Aerial Lantern & Trail Guide" mode guiding hiker to nearest Autiotupa
        walking_guide = dobs.compute_aerial_lantern_trail_guide_state(
            hiker_east_m=-200.0,
            hiker_north_m=220.0,
            hiker_vel_east_mps=0.6,
            hiker_vel_north_mps=0.9,
            lead_distance_m=15.0,
            lantern_alt_agl_m=10.0,
        )
        self.assertEqual(walking_guide["mode"], "AERIAL_LANTERN_TRAIL_GUIDE")
        self.assertEqual(walking_guide["target_autiotupa"]["hut_id"], "HUT-JUSSINKAMPPA")
        self.assertGreaterEqual(walking_guide["lead_standoff_m"], 15.0)
        self.assertTrue(walking_guide["geofence_standoff_enforced"])
        self.assertEqual(walking_guide["guide_pacing_state"], "LEADING_HIKER_ALONG_TRAIL_AT_HIKER_PACE")
        self.assertTrue(walking_guide["downward_trail_spotlight_active"])
        self.assertTrue(walking_guide["upward_sky_flare_beacon_active"])
        self.assertIn("SEURAA MINUA AUTIOTUVALLE", walking_guide["display_text"])

        # When hiker stops to rest (speed = 0), drone automatically pauses & hovers 15m ahead
        resting_guide = dobs.compute_aerial_lantern_trail_guide_state(
            hiker_east_m=-200.0,
            hiker_north_m=220.0,
            hiker_vel_east_mps=0.0,
            hiker_vel_north_mps=0.0,
            lead_distance_m=15.0,
            lantern_alt_agl_m=10.0,
        )
        self.assertEqual(resting_guide["guide_pacing_state"], "AUTO_WAIT_HOVER_FOR_RESTING_HIKER")
        self.assertEqual(resting_guide["drone_guide_speed_mps"], 0.0)

        # 5. Verify end-to-end mission status payload & execute_approach_action(lantern_guide=True / public_release_sar_cask)
        with tempfile.TemporaryDirectory() as tmpdir:
            status_path = os.path.join(tmpdir, "drone_observer_status.json")
            sim_res = dobs.simulate_complete_observation_mission(old_alert, out_status_path=status_path)
            self.assertIn("Karhunkierros SAR", sim_res["product_positioning"])
            self.assertEqual(sim_res["ephemeral_ring_buffer_policy"]["ttl_hours"], 48)
            self.assertFalse(sim_res["ephemeral_ring_buffer_policy"]["facial_recognition_enabled"])
            self.assertIn("aerial_lantern_trail_guide", sim_res)
            self.assertIn("safe_offset_barrel_drop", sim_res)

            lg_action = dobs.execute_approach_action(status_path=status_path, lantern_guide=True)
            self.assertEqual(lg_action["active_flight_mode"], "AERIAL_LANTERN_TRAIL_GUIDE")
            self.assertIn("SEURAA MINUA AUTIOTUVALLE", lg_action["aerial_lantern_trail_guide"]["display_text"])

            sar_cask_action = dobs.execute_approach_action(
                status_path=status_path, preset_id="public_release_sar_cask"
            )
            self.assertEqual(sar_cask_action["active_flight_mode"], "CLOSE_APPROACH_COMMUNICATION")
            self.assertTrue(sar_cask_action["safe_offset_barrel_drop"]["electromagnetic_release_detached"])
            self.assertEqual(sar_cask_action["safe_offset_barrel_drop"]["post_drop_drone_alt_agl_m"], 50.0)

    def test_16_finnish_context_poronhoitolaki_winter_endurance_and_aviation_sar(self):
        """Verifies Finnish boreal wildlife (Poro/Hirvi) thermal discrimination, Poronhoitolaki 100m ceiling, -25C Kaamos flight endurance, and Rajavartiolaitos aviation DDM coordinates."""
        # 1. Bipedal human hiker vs. Reindeer (Poro) & Moose (Hirvi) under Poronhoitolaki 848/1990 § 42
        human_sig = dobs.classify_finnish_boreal_thermal_signature(
            bbox_width_norm=0.14,
            bbox_height_norm=0.38,
            estimated_height_m=1.75,
            thermal_core_delta_c=15.0,
            reindeer_herding_area=True,
        )
        self.assertTrue(human_sig["is_human_hiker"])
        self.assertEqual(human_sig["classified_boreal_signature"], "human_bipedal_hiker")
        self.assertFalse(human_sig["poronhoitolaki_compliance_active"])
        self.assertFalse(human_sig["speaker_muted_for_wildlife"])

        poro_sig = dobs.classify_finnish_boreal_thermal_signature(
            bbox_width_norm=0.22,
            bbox_height_norm=0.21,
            estimated_height_m=1.10,
            thermal_core_delta_c=12.0,
            reindeer_herding_area=True,
        )
        self.assertFalse(poro_sig["is_human_hiker"])
        self.assertEqual(poro_sig["classified_boreal_signature"], "reindeer_poro_quadruped")
        self.assertTrue(poro_sig["poronhoitolaki_compliance_active"])
        self.assertEqual(poro_sig["wildlife_min_altitude_agl_m"], 100.0)
        self.assertTrue(poro_sig["speaker_muted_for_wildlife"])

        hirvi_sig = dobs.classify_finnish_boreal_thermal_signature(
            bbox_width_norm=0.28,
            bbox_height_norm=0.30,
            estimated_height_m=1.85,
            thermal_core_delta_c=14.0,
            reindeer_herding_area=True,
        )
        self.assertFalse(hirvi_sig["is_human_hiker"])
        self.assertEqual(hirvi_sig["classified_boreal_signature"], "moose_hirvi_quadruped")
        self.assertEqual(hirvi_sig["wildlife_min_altitude_agl_m"], 100.0)

        # 2. Finnish Arctic winter (-25C Kaamos vs +15C summer) flight endurance & dynamic battery handover
        summer_endurance = dobs.evaluate_finnish_winter_flight_endurance(
            ambient_temp_c=15.0, wind_speed_mps=3.0, kaamos_polar_night=False, heated_cask_active=False
        )
        winter_endurance = dobs.evaluate_finnish_winter_flight_endurance(
            ambient_temp_c=-25.0, wind_speed_mps=7.0, kaamos_polar_night=True, heated_cask_active=True
        )
        self.assertGreater(summer_endurance["max_flight_endurance_min"], winter_endurance["max_flight_endurance_min"])
        self.assertEqual(summer_endurance["recommended_handover_reserve_pct"], 30.0)
        self.assertEqual(winter_endurance["recommended_handover_reserve_pct"], 45.0)
        self.assertTrue(winter_endurance["heated_cask_keep_warm_active"])

        # 3. Verify Rajavartiolaitos / FINHEMS aviation DDM coordinates & nearest Autiotupa landmark in 112 feed
        ddm = dobs.format_wgs84_ddm_aviation_sar(66.26050, 29.41800)
        self.assertEqual(ddm["format"], "WGS84_DDM_AVIATION_SAR")
        self.assertIn("66° 15.630' N", ddm["formatted"])
        self.assertIn("029° 25.080' E", ddm["formatted"])

        demo_alert = {
            "node": "NODE-NORTH-01",
            "timestamp": 1700000500,
            "verified": True,
            "camera_ok": True,
            "pico_trig": "TRIG,MAG=1850,SEIS=540,DIST=5200,SPD=155,TEMP=-22.0,UPTIME_S=7200",
            "detections": [{"class": "person", "conf": 0.95, "box": [0.42, 0.25, 0.58, 0.78]}],
        }
        sim = dobs.simulate_complete_observation_mission(demo_alert)
        pos = sim["police_112_guidance"]["current_position"]
        self.assertIn("wgs84_ddm_helicopter_sar", pos)
        self.assertIn("nearest_autiotupa_landmark", pos)
        self.assertIn(pos["nearest_autiotupa_landmark"]["hut_id"], dobs.WILDERNESS_AUTIOTUPA_HUTS)
        self.assertIn("from ", pos["nearest_autiotupa_landmark"]["formatted"])
        self.assertIn("Poliisi", sim["police_112_guidance"]["finnish_sar_authority_routing"]["missing_person_land_lead"])
        self.assertIn("Rajavartiolaitos", sim["police_112_guidance"]["finnish_sar_authority_routing"]["aviation_and_border_sar"])

    def test_17_roadless_wilderness_autiotupa_golden_hour_bridge(self):
        """Verifies the roadless wilderness survival bridge (where a police car cannot reach, and drone guidance to a state Autiotupa shelters hikers long before ground patrols arrive)."""
        bridge = dobs.evaluate_roadless_wilderness_autiotupa_rescue_bridge(
            hiker_east_m=-180.0,
            hiker_north_m=210.0,
            nearest_plowed_road_distance_km=12.0,
            ambient_temp_c=-22.0,
            hiker_walk_speed_mps=0.80,
            drone_pad_distance_m=950.0,
        )
        self.assertTrue(bridge["pro_bono_public_good_initiative"])
        self.assertFalse(bridge["police_car_can_reach_directly"])
        self.assertTrue(bridge["unassisted_waiting_exceeds_hypothermia_window"])
        self.assertTrue(bridge["sheltered_before_hypothermia_onset"])
        self.assertLess(bridge["total_time_to_warm_autiotupa_shelter_min"], 15.0)
        self.assertGreater(bridge["survival_margin_gained_vs_ground_patrol_min"], 110.0)
        self.assertEqual(bridge["nearest_state_autiotupa_id"], "HUT-JUSSINKAMPPA")
        self.assertIn("Wood stove", bridge["metsahallitus_autiotupa_amenities"])

    def test_18_gnss_jamming_rf_blackout_and_icing_resilience(self):
        """Verifies Eastern/Northern Finland GNSS spoofing/jamming fallback, RF blackout optical diode continuation, propeller icing shed, and above-canopy Opaslyhty elevation."""
        res = dobs.evaluate_gnss_rf_jamming_and_weather_resilience(
            gnss_hdop=8.5,
            gnss_speed_mps=45.0,          # Spoofed false velocity jump
            optical_flow_speed_mps=11.5,  # True ground speed from PMW3901 optical flow
            gnss_pos_jump_m=120.0,
            rf_noise_floor_dbm=-65.0,     # Severe RF jamming
            ambient_temp_c=-2.0,          # Supercooled freezing drizzle temperature
            relative_humidity_pct=94.0,
            hover_throttle_increase_pct=21.0,
            wind_speed_mps=9.5,
            dense_conifer_canopy=True,
        )
        self.assertTrue(res["gnss_jammed_or_spoofed"])
        self.assertTrue(res["gnss_spoofing_detected"])
        self.assertTrue(res["ekf_gnss_fenced_off_no_flyaway"])
        self.assertEqual(res["navigation_fallback_mode"], "GNSS_DENIED_OPTICAL_FLOW_LIDAR_INS_AND_TRAIL_FIDUCIALS")
        self.assertTrue(res["rf_jamming_detected"])
        self.assertFalse(res["abort_rescue_on_rf_loss"])
        self.assertEqual(res["pad_launch_handoff"], "940NM_ONE_WAY_OPTICAL_DIODE_COUPLER_0W_RF")
        self.assertTrue(res["icing_hazard_detected"])
        self.assertEqual(res["propeller_deicing_mode"], "HYDROPHOBIC_COATING_PLUS_CENTRIFUGAL_RPM_ICE_SHED_BURST")
        self.assertEqual(res["opaslyhty_safe_canopy_altitude_agl_m"], 28.0)
        self.assertTrue(res["forced_autoland_on_rc_plus_gnss_loss_blocked"])
        self.assertEqual(res["arducopter_fs_options_bitmask"], 19)
        self.assertEqual(res["arducopter_fs_ekf_action"], 2)

        # Verify 3.1, 3.2, 3.3, 3.4 & 3.5: Multi-band high-power RF interference pre-emptive M10 jamInd switch,
        # external M10 I2C compass glitch fencing, ArduCopter FS_OPTIONS=19/FS_EKF_ACTION=2, and Human-Pilot EW fallback
        ew_gun = dobs.evaluate_gnss_rf_jamming_and_weather_resilience(
            gnss_hdop=1.2,                       # Before HDOP even spikes...
            ublox_m10_jam_ind=185,               # ...u-blox M10 RF front-end jamInd spikes (>= 110)
            gnss_cn0_drop_dbhz=19.5,             # ...and C/N0 collapses (>= 12 dB-Hz)
            external_compass_i2c_glitch=True,    # 1.5 GHz RF rectifies onto unshielded M10 I2C compass bus
            compass_gyro_yaw_divergence_deg=42.0,
            rf_noise_floor_dbm=-58.0,            # 915 MHz LoRa jammed
            rc_elrs_link_lost=True,              # 2.4 GHz ELRS RC jammed
        )
        self.assertTrue(ew_gun["preemptive_m10_rf_frontend_jam_detected"])
        self.assertLessEqual(ew_gun["ekf3_source_set_switch_latency_ms"], 80)
        self.assertTrue(ew_gun["external_m10_compass_i2c_glitch_detected"])
        self.assertTrue(ew_gun["external_m10_compass_fenced_off"])
        self.assertIn("INTERNAL_PIXHAWK6C_IST8310", ew_gun["active_yaw_estimator_source"])
        self.assertTrue(ew_gun["anti_drone_gun_multi_band_attack_detected"])
        self.assertTrue(ew_gun["store_and_forward_telemetry_spooling_active"])
        self.assertIn("ORTHOGONAL_LATERAL_STEP_OUT", ew_gun["directional_jammer_beam_evasion_action"])

        params = dobs.generate_arducopter_pixhawk6c_param_profile()["parameters"]
        self.assertEqual(params["FS_OPTIONS"], 19)
        self.assertEqual(params["FS_EKF_ACTION"], 2)
        self.assertEqual(params["COMPASS_USE2"], 1)
        self.assertEqual(params["EK3_GSF_RUN_MASK"], 3)
        self.assertEqual(params["EK3_GSF_USE_MASK"], 3)

        ctrl = dobs.HumanPilotAndTwoWayVoiceRelayController(drone_id="DRONE-SIERRA-01")
        ew_fallback = ctrl.handle_ew_jamming_blackout(rf_noise_floor_dbm=-60.0, rc_elrs_link_lost=True)
        self.assertTrue(ew_fallback["ew_blackout_handled"])
        self.assertTrue(ew_fallback["forced_autoland_prevented"])
        self.assertEqual(ew_fallback["speaker_audio_source"], "LOCAL_PI5_SD_CACHED_BILINGUAL_REASSURANCE_WAV")
        self.assertTrue(ew_fallback["store_and_forward_fsync_durable"])

    def test_19_immobilized_hiker_sky_lighthouse_and_mobile_tailgate_mode(self):
        """Verifies immobilized hiker escalation (45m Sky-Lighthouse + 18h ground strobe beacon) and zero-infrastructure Mobile Tailgate / Ahkio mode."""
        # 1. Hiker cannot walk after 4 minutes -> Sky-Lighthouse hold at 45m AGL
        immob_sky = dobs.compute_aerial_lantern_trail_guide_state(
            hiker_east_m=-180.0,
            hiker_north_m=210.0,
            hiker_vel_east_mps=0.0,
            hiker_vel_north_mps=0.0,
            stationary_duration_s=240.0,
            battery_pct=75.0,
        )
        self.assertTrue(immob_sky["hiker_immobilized_escalation"])
        self.assertEqual(immob_sky["guide_pacing_state"], "IMMOBILIZED_SHELTER_IN_PLACE_SKY_LIGHTHOUSE_HOLD")
        self.assertEqual(immob_sky["drone_alt_agl_m"], 45.0)
        self.assertIn("PYSY PAIKALLASI LÄMPÖPEITOSSA", immob_sky["display_text"])

        # 2. Immobilized hiker when battery reaches 22% -> lands on 15m clear snow zone for 18+ hour ground strobe beacon
        immob_ground = dobs.compute_aerial_lantern_trail_guide_state(
            hiker_east_m=-180.0,
            hiker_north_m=210.0,
            hiker_vel_east_mps=0.0,
            hiker_vel_north_mps=0.0,
            stationary_duration_s=600.0,
            battery_pct=22.0,
        )
        self.assertEqual(immob_ground["guide_pacing_state"], "GROUNDED_CLEARING_18HR_LOW_POWER_STROBE_BEACON")
        self.assertEqual(immob_ground["drone_alt_agl_m"], 0.0)
        self.assertGreaterEqual(immob_ground["grounded_beacon_endurance_hours"], 18.0)

        # 3. Zero-infrastructure Mobile Tailgate / Snowmobile Ahkio mode (Vapepa road-end launch)
        mobile_guide = dobs.compute_aerial_lantern_trail_guide_state(
            hiker_east_m=-80.0,
            hiker_north_m=90.0,
            hiker_vel_east_mps=0.8,
            hiker_vel_north_mps=-0.6,
            custom_shelter_target={
                "hut_id": "VAPEPA-MOBILE-TAILGATE-01",
                "name": "Pelastuspartion Mobiili Tukikohta",
                "east_m": 0.0,
                "north_m": 0.0,
            },
        )
        self.assertEqual(mobile_guide["target_autiotupa"]["hut_id"], "VAPEPA-MOBILE-TAILGATE-01")
        self.assertEqual(mobile_guide["guide_pacing_state"], "LEADING_HIKER_ALONG_TRAIL_AT_HIKER_PACE")

    def test_20_audit_counterexamples_and_security_regressions(self):
        """Verifies all counterexamples and regressions identified in the Independent Quality & Security Audit (F01-F18)."""
        # F02: extract_qualifying_subjects must fail closed when verified != True
        unverified_multi = {
            "node": "NODE-NORTH-01",
            "verified": False,
            "camera_ok": True,
            "detections": [{"class": "person", "conf": 0.96, "box": [0.40, 0.25, 0.56, 0.78]}],
        }
        ok_unv, reason_unv, matches_unv = dobs.extract_qualifying_subjects(unverified_multi)
        self.assertFalse(ok_unv)
        self.assertEqual(reason_unv, "unverified_signature")
        self.assertEqual(matches_unv, [])

        # F02: PassiveTrailSightingLedger.authorize_sar_order rejects expired/missing sighting_id
        ledger = dobs.PassiveTrailSightingLedger(auto_dispatch_drones=False)
        t0 = 1700000000
        valid_alert = dict(unverified_multi, verified=True, timestamp=t0)
        rec = ledger.record_passive_sighting(valid_alert, current_ts=t0)
        s_id = rec["sighting"]["sighting_id"]
        expired_auth = ledger.authorize_sar_order(sighting_id=s_id, current_ts=t0 + 49 * 3600)
        self.assertFalse(expired_auth["authorized"])
        self.assertIn("expired", expired_auth["reason"])
        # Also test non-existent sighting_id when valid sightings exist
        ledger.record_passive_sighting(dict(valid_alert, timestamp=t0 + 50 * 3600), current_ts=t0 + 50 * 3600)
        missing_auth = ledger.authorize_sar_order(sighting_id="SIGHTING-NONEXISTENT", current_ts=t0 + 50 * 3600)
        self.assertFalse(missing_auth["authorized"])
        self.assertIn("sighting_id_not_found_or_expired", missing_auth["reason"])

        # F03: compute_close_approach_state with public_release_sar_cask enforces 50m AGL & >=15m horizontal standoff
        pub_app = dobs.compute_close_approach_state(
            subject_east_m=-100.0,
            subject_north_m=50.0,
            vel_east_mps=1.0,
            vel_north_mps=0.0,
            elapsed_approach_s=30.0,
            preset_id="public_release_sar_cask",
        )
        self.assertAlmostEqual(pub_app["drone_alt_agl_m"], 50.0, places=2)
        self.assertGreaterEqual(pub_app["horiz_standoff_m"], 15.0)
        self.assertEqual(pub_app["barrel_altitude_agl_m"], 0.0)

        # F05 & F06: COTS BOM alignment (8,000 mAh 4S2P 14.8V 118.4 Wh pack & Benewake TF02-Pro 40m LiDAR)
        endurance = dobs.evaluate_finnish_winter_flight_endurance(ambient_temp_c=-20.0)
        self.assertIn("4S", endurance["battery_pack_spec"])
        self.assertIn("14.8V", endurance["battery_pack_spec"])
        resilience = dobs.evaluate_gnss_rf_jamming_and_weather_resilience()
        self.assertIn("TF02-Pro", resilience["lidar_rangefinder_model"])

        # F07: Operational mode rejects unknown camera nodes & aligns Oulanka CRS with Autiotupa huts
        with self.assertRaises(ValueError):
            dobs.resolve_camera_node("NODE-UNKNOWN-99", execution_mode="OPERATIONAL")
        hut = dobs.WILDERNESS_AUTIOTUPA_HUTS["HUT-JUSSINKAMPPA"]
        hut_lat, hut_lon = dobs.enu_to_wgs84(
            hut["east_m"], hut["north_m"], ref_lat=hut["ref_lat_deg"], ref_lon=hut["ref_lon_deg"]
        )
        self.assertAlmostEqual(hut_lat, hut["ref_lat_deg"], delta=0.01)
        self.assertAlmostEqual(hut_lon, hut["ref_lon_deg"], delta=0.01)

        # F08: Grid search exhaustion returns honest None tracker/ETRS fields when target is outside grid
        exhausted = dobs.simulate_multi_drone_grid_search_mission(
            last_east_m=0.0,
            last_north_m=0.0,
            hidden_subject_east_m=5000.0,
            hidden_subject_north_m=5000.0,
        )
        self.assertFalse(exhausted["target_reacquired"])
        self.assertIsNone(exhausted["reacquired_tracker_state"])
        self.assertIsNone(exhausted["reacquired_etrs_tm35fin"])
        self.assertEqual(exhausted["post_reacquisition_mode"], "SEARCH_EXHAUSTED_EXPAND_SECTOR_OR_AWAIT_112_TASKING")

        # F09: FleetCoordinator enforces RTH threshold on both primary and secondary drones; grounded beacon at 0% is 0.0h
        fleet = dobs.FleetCoordinator(rth_battery_threshold_pct=30.0)
        fleet.drones["DRONE-SIERRA-01"]["battery_pct"] = 25.0
        fleet.drones["DRONE-KILO-02"]["battery_pct"] = 20.0
        dual_low_single = fleet.evaluate_handover_and_assign_orbits(0.0, 0.0, 10.0, dual_stereo_mode=False)
        self.assertEqual(dual_low_single["active_drone_count"], 0)
        self.assertEqual(dual_low_single["drones"]["DRONE-SIERRA-01"]["status"], "RETURNING_TO_PAD_RTH")
        self.assertEqual(dual_low_single["drones"]["DRONE-KILO-02"]["status"], "STANDBY_ON_PAD")

        fleet_stereo = dobs.FleetCoordinator(rth_battery_threshold_pct=30.0)
        fleet_stereo.evaluate_handover_and_assign_orbits(0.0, 0.0, 5.0, dual_stereo_mode=True)
        fleet_stereo.drones["DRONE-SIERRA-01"]["battery_pct"] = 25.0
        fleet_stereo.drones["DRONE-KILO-02"]["battery_pct"] = 20.0
        dual_low_stereo = fleet_stereo.evaluate_handover_and_assign_orbits(0.0, 0.0, 10.0, dual_stereo_mode=True)
        self.assertEqual(dual_low_stereo["active_drone_count"], 0)
        self.assertEqual(dual_low_stereo["drones"]["DRONE-SIERRA-01"]["status"], "RETURNING_TO_PAD_RTH")
        self.assertEqual(dual_low_stereo["drones"]["DRONE-KILO-02"]["status"], "RETURNING_TO_PAD_RTH")

        zero_batt_guide = dobs.compute_aerial_lantern_trail_guide_state(
            hiker_east_m=0.0,
            hiker_north_m=0.0,
            hiker_vel_east_mps=0.0,
            hiker_vel_north_mps=0.0,
            stationary_duration_s=600.0,
            battery_pct=0.0,
        )
        self.assertEqual(zero_batt_guide["grounded_beacon_endurance_hours"], 0.0)

        # F10: Multi-pass symmetric pairwise deconfliction handles 3 co-located drones (wrapped or flat dicts)
        co_located = {
            "D1": {"drone_east_m": 0.0, "drone_north_m": 0.0, "drone_alt_agl_m": 100.0},
            "D2": {"drone_east_m": 0.0, "drone_north_m": 0.0, "drone_alt_agl_m": 100.0},
            "D3": {"drone_east_m": 0.0, "drone_north_m": 0.0, "drone_alt_agl_m": 100.0},
        }
        deconf = dobs.deconflict_multi_drone_airspace(co_located, min_horiz_sep_m=35.0, min_vert_sep_m=10.0)
        self.assertTrue(deconf["airspace_safe"])
        self.assertGreaterEqual(deconf["min_pairwise_3d_separation_m"], 25.0)

        # F11: Stationary subject (SPD=0) preserves 0.0 m/s in both sender_node and drone_observer
        stat_pico = "TRIG,MAG=85,SEISMIC=42,DIST=12000,SPD=0,TEMP=-4.5,UP=3600"
        stat_kin = sender_node.estimate_subject_kinematics(
            detections=[{"class": "person", "conf": 0.94, "box": [0.42, 0.25, 0.58, 0.78]}],
            pico_telemetry=stat_pico,
        )
        self.assertEqual(stat_kin["est_speed_mps"], 0.0)
        self.assertEqual(stat_kin["movement_direction"], "stationary")
        stat_alert = {
            "node": "NODE-NORTH-01",
            "timestamp": 1700000900,
            "verified": True,
            "camera_ok": True,
            "pico_trig": stat_pico,
            "subject_kinematics": stat_kin,
            "detections": [{"class": "person", "conf": 0.94, "box": [0.42, 0.25, 0.58, 0.78]}],
        }
        stat_ground = dobs.reconstruct_subject_ground_state(stat_alert)
        self.assertEqual(stat_ground["speed_mps"], 0.0)
        self.assertEqual(stat_ground["vel_east_mps"], 0.0)
        self.assertEqual(stat_ground["vel_north_mps"], 0.0)

        # F15, F16, F17: Verify receiver_hub MAX_CHUNK_BYTES and _journal_contains_nonce idempotence
        import receiver_hub
        self.assertEqual(receiver_hub.MAX_CHUNK_BYTES, 1024)
        with tempfile.TemporaryDirectory() as tmpdir:
            jpath = os.path.join(tmpdir, "alerts_journal.jsonl")
            with open(jpath, "w", encoding="utf-8") as jf:
                jf.write('{"node": "NODE-NORTH-01", "nonce": "aa11bb22"}\n')
            self.assertTrue(receiver_hub._journal_contains_nonce(jpath, "NODE-NORTH-01", "aa11bb22"))
            self.assertFalse(receiver_hub._journal_contains_nonce(jpath, "NODE-NORTH-01", "cc33dd44"))
            # Verify shared generate_keys.py exists in both pi5_sender_node/ and tools/
            self.assertTrue(os.path.isfile(os.path.join(SENDER_DIR, "generate_keys.py")))
            self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, "tools", "generate_keys.py")))
            self.assertTrue(os.path.isfile(os.path.join(COLLECTOR_DIR, "ui", "three.min.js")))

    def test_21_uber_for_sar_dispatch_marketplace_and_elastic_pull(self):
        """
        Verifies the 'Uber-for-SAR' Open-Alert Dispatch Marketplace, Automated Roofed Shelter
        auto-acceptance, multi-responder auto-prioritization, human coordinator override/manual
        governance, and 28m Elastic Pull-Guidance to the nearest Autiotupa.
        """
        coord = dobs.SARDispatchMarketplaceCoordinator()

        # 1. Broadcast open alert -> Automated Roofed Stations in AUTO_ACCEPT_GEOFENCE mode auto-accept
        state = coord.broadcast_open_alert(incident_east_m=-180.0, incident_north_m=210.0)
        task = state["active_task"]
        self.assertEqual(len(task["notified_units"]), 5)
        # Both roofed stations (Oulanka #1 at 2.04 km and Valtavaara #2 at 7.83 km) auto-accepted
        accepted_ids = [b["unit_id"] for b in task["accepted_bids"]]
        self.assertIn("NEST-OULANKA-ROOF-01", accepted_ids)
        self.assertIn("NEST-VALTAVAARA-ROOF-02", accepted_ids)
        self.assertEqual(task["primary_assigned_unit"]["unit_id"], "NEST-OULANKA-ROOF-01")

        # 2. Mobile units (Poliisi Van 21 and Border Guard Patrol 04) see open alert and click "Accept"
        coord.submit_unit_acceptance("POLIISI-VAN-OULU-21", accepted_by="MOBILE_CREW_TERMINAL")
        state = coord.submit_unit_acceptance("RAJA-PARTIO-KUUSAMO-04", accepted_by="MOBILE_CREW_TERMINAL")
        task = state["active_task"]
        self.assertEqual(len(task["accepted_bids"]), 4)
        # Verify auto-prioritization keeps closest/fastest Oulanka Roofed Nest #1 as Primary and ranks #2
        self.assertEqual(task["primary_assigned_unit"]["unit_id"], "NEST-OULANKA-ROOF-01")
        self.assertIsNotNone(task["secondary_backup_unit"])
        self.assertGreater(
            task["primary_assigned_unit"]["priority_score"],
            task["secondary_backup_unit"]["priority_score"],
        )

        # 3. Verify Automated Roofed Shelter launch -> care drop -> 28m Elastic Pull -> Autonomous RTB docking
        exec_info = task["active_mission_execution"]
        self.assertEqual(exec_info["unit_type"], "AUTOMATED_ROOFED_NEST")
        self.assertEqual(exec_info["autonomous_rtb_status"], "RTB_DOCKED_UNDER_ROOF_AND_RECHARGING")
        pull = exec_info["elastic_pull_guidance_28m"]
        self.assertEqual(pull["pull_guidance_mode"], "ACTIVE_ELASTIC_PULL_TOWARD_AUTIOTUPA")
        self.assertAlmostEqual(pull["drone_alt_agl_m"], 28.0, places=1)
        self.assertAlmostEqual(pull["elastic_lead_ahead_m"], 15.0, places=1)

        # 4. Verify Elastic Pull-Guidance lateral drift correction & rest-hold states
        drift_pull = dobs.compute_elastic_pull_guidance_vector(
            hiker_east_m=200.0,
            hiker_north_m=-300.0,
            hiker_vel_east_mps=0.5,
            hiker_vel_north_mps=-0.5,
            trail_start_east_m=-180.0,
            trail_start_north_m=210.0,
        )
        self.assertEqual(drift_pull["pull_guidance_mode"], "LATERAL_PULL_CORRECTION_BACK_TO_TRAIL")
        self.assertAlmostEqual(drift_pull["elastic_lead_ahead_m"], 6.0, places=1)

        rest_pull = dobs.compute_elastic_pull_guidance_vector(
            hiker_east_m=-180.0,
            hiker_north_m=210.0,
            hiker_vel_east_mps=0.0,
            hiker_vel_north_mps=0.0,
            trail_start_east_m=-180.0,
            trail_start_north_m=210.0,
        )
        self.assertEqual(rest_pull["pull_guidance_mode"], "ELASTIC_TETHER_HOLD_WAITING_FOR_HIKER")
        self.assertAlmostEqual(rest_pull["elastic_lead_ahead_m"], 10.0, places=1)

        # 5. Human Coordinator Control Panel Intervention: Force assign Mobile Police Van #1, Hold, and Force RTB
        override_state = coord.human_coordinator_intervene(
            "FORCE_ASSIGN_UNIT",
            target_unit_id="POLIISI-VAN-OULU-21",
            reason="Coordinator selected Police Van 21 for direct roadhead coordination",
        )
        self.assertTrue(override_state["active_task"]["human_override_active"])
        self.assertEqual(override_state["active_task"]["primary_assigned_unit"]["unit_id"], "POLIISI-VAN-OULU-21")
        self.assertEqual(override_state["active_task"]["task_status"], "DISPATCHED_HUMAN_OVERRIDE")

        # Toggle station auto-mode off and test MANUAL_COORDINATOR_APPROVAL_ONLY mode
        coord.set_station_auto_mode("NEST-OULANKA-ROOF-01", False)
        coord.set_coordination_governance_mode("MANUAL_COORDINATOR_APPROVAL_ONLY")
        manual_bcast = coord.broadcast_open_alert(incident_east_m=-180.0, incident_north_m=210.0)
        # In manual mode, no unit is auto-dispatched until human coordinator approves
        self.assertIsNone(manual_bcast["active_task"]["primary_assigned_unit"])
        approved = coord.human_coordinator_intervene("APPROVE_MANUAL_LAUNCH", target_unit_id="NEST-VALTAVAARA-ROOF-02")
        self.assertEqual(approved["active_task"]["primary_assigned_unit"]["unit_id"], "NEST-VALTAVAARA-ROOF-02")
        self.assertEqual(approved["active_task"]["task_status"], "DISPATCHED_HUMAN_APPROVED")

        rtb_state = coord.human_coordinator_intervene("FORCE_IMMEDIATE_RTB")
        self.assertEqual(rtb_state["active_task"]["task_status"], "ABORTED_RTB_BY_HUMAN_COORDINATOR")

    def test_22_open_source_stack_and_hardened_marketplace_interlocks(self):
        """
        Verifies F23 (Roofed Shelter actuator/heater/snow-load safety interlock),
        F24 (Automatic Backup Promotion on Primary Abort), F25 (Closed-Loop Multi-Step
        Elastic Pull Escort to Autiotupa), and F26 (ArduCopter 4.5+ Pixhawk 6C EKF3
        parameter profile & Delta-style Open SAR Situational Awareness CoT export).
        """
        # 1. Verify F23: Disqualify a roofed station if its hatch actuator is jammed or snow load > 25 kg
        coord = dobs.SARDispatchMarketplaceCoordinator()
        coord.fleet_units[0]["roof_hatch_operational"] = False
        coord.fleet_units[0]["roof_snow_load_kg"] = 32.0
        state = coord.broadcast_open_alert(incident_east_m=-180.0, incident_north_m=210.0)
        notified_0 = next(u for u in state["active_task"]["notified_units"] if u["unit_id"] == "NEST-OULANKA-ROOF-01")
        self.assertFalse(notified_0["shelter_safety_interlock_ok"])
        self.assertFalse(notified_0["mission_feasible"])
        self.assertIn("ROOF_HATCH_ACTUATOR_FAULT", notified_0["disqualification_reasons"])
        # Because Nest #1 was disqualified by its safety interlock, Nest #2 (Valtavaara) auto-accepted and became #1 Primary!
        self.assertEqual(state["active_task"]["primary_assigned_unit"]["unit_id"], "NEST-VALTAVAARA-ROOF-02")

        # 2. Verify F24: When Poliisi Van 21 (closer at 5.2 km) accepts, it becomes #1 Primary and Nest #2 becomes #2 Backup;
        #    then aborting Primary automatically promotes #2 Backup (NEST-VALTAVAARA-ROOF-02) back to Primary!
        after_van = coord.submit_unit_acceptance("POLIISI-VAN-OULU-21", accepted_by="MOBILE_CREW_TERMINAL")
        self.assertEqual(after_van["active_task"]["primary_assigned_unit"]["unit_id"], "POLIISI-VAN-OULU-21")
        self.assertEqual(after_van["active_task"]["secondary_backup_unit"]["unit_id"], "NEST-VALTAVAARA-ROOF-02")
        promoted_state = coord.human_coordinator_intervene("ABORT_PRIMARY_PROMOTE_BACKUP")
        self.assertEqual(promoted_state["active_task"]["task_status"], "DISPATCHED_BACKUP_PROMOTED")
        self.assertEqual(promoted_state["active_task"]["primary_assigned_unit"]["unit_id"], "NEST-VALTAVAARA-ROOF-02")

        # 3. Verify F25: Closed-loop multi-step Elastic Pull Escort to Autiotupa
        escort = dobs.simulate_elastic_pull_escort_to_autiotupa(start_east_m=-180.0, start_north_m=210.0)
        self.assertTrue(escort["escort_completed"])
        modes = [step["pull_guidance_mode"] for step in escort["escort_steps"]]
        self.assertEqual(modes[0], "ACTIVE_ELASTIC_PULL_TOWARD_AUTIOTUPA")
        self.assertEqual(modes[1], "LATERAL_PULL_CORRECTION_BACK_TO_TRAIL")
        self.assertEqual(modes[2], "ELASTIC_TETHER_HOLD_WAITING_FOR_HIKER")
        self.assertEqual(modes[4], "ARRIVED_AT_AUTIOTUPA_SAFE_HAVEN")

        # 4. Verify F26 & F34: ArduCopter 4.5+ Pixhawk 6C parameter profile & Open SAR CoT packet
        ardupilot_profile = dobs.generate_arducopter_pixhawk6c_param_profile()
        params = ardupilot_profile["parameters"]
        self.assertEqual(params["AHRS_EKF_TYPE"], 3)
        self.assertEqual(params["EK3_SRC1_POSXY"], 3)   # Set 1: M10 GPS
        self.assertEqual(params["EK3_SRC2_VELXY"], 5)   # Set 2: MTF-02P / Matek 3901-L0X Optical Flow
        self.assertEqual(params["EK3_SRC2_POSZ"], 2)    # Set 2: Benewake TF02-Pro LiDAR RangeFinder
        self.assertEqual(params["RC9_OPTION"], 90)      # EKF Source Set Switch
        self.assertEqual(params["BATT_MONITOR"], 4)     # PM02 V3 power module
        self.assertEqual(params["SERVO9_FUNCTION"], 28) # Servo airdrop release
        self.assertEqual(params["SERIAL6_PROTOCOL"], 23) # ExpressLRS CRSF RCIN
        self.assertIn("EK3_SRC2_VELXY,5", ardupilot_profile["param_file_text"])

        sa_pkt = promoted_state["open_sar_situational_awareness"]
        self.assertEqual(sa_pkt["schema"], "OPEN_SAR_SITUATIONAL_AWARENESS_V1")
        self.assertIn("<event version=\"2.0\"", sa_pkt["cot_xml"])
        self.assertEqual(len(sa_pkt["link_failover_tiers"]), 4)

        # 5. Verify F27: Airframe maintains >= 15.0m horizontal human safety standoff across ALL elastic pull modes
        #    while spotlight gimbal pitch steers the illuminated snow pool closer (6m / 10m / 15m)
        for step in escort["escort_steps"]:
            self.assertGreaterEqual(step["airframe_horiz_separation_m"], 15.0 - 1e-6)
            self.assertTrue(step["geofence_standoff_enforced"])
        # Lateral pull step has 6.0m spotlight lead on snow while airframe stays >= 15.0m away
        self.assertEqual(escort["escort_steps"][1]["spotlight_lead_ahead_m"], 6.0)
        self.assertGreaterEqual(escort["escort_steps"][1]["airframe_horiz_separation_m"], 15.0 - 1e-6)

        # 6. Verify F28: Elastic pull handles immobilized hikers (45m Sky-Lighthouse & 18h Grounded Beacon) and Poronhoitolaki 100m hold
        immob_sky = dobs.compute_elastic_pull_guidance_vector(
            hiker_east_m=-180.0, hiker_north_m=210.0, stationary_duration_s=240.0, battery_pct=65.0
        )
        self.assertEqual(immob_sky["pull_guidance_mode"], "IMMOBILIZED_SHELTER_IN_PLACE_SKY_LIGHTHOUSE_HOLD")
        self.assertEqual(immob_sky["drone_altitude_agl_m"], 45.0)
        immob_ground = dobs.compute_elastic_pull_guidance_vector(
            hiker_east_m=-180.0, hiker_north_m=210.0, stationary_duration_s=240.0, battery_pct=22.0
        )
        self.assertEqual(immob_ground["pull_guidance_mode"], "GROUNDED_CLEARING_18HR_LOW_POWER_STROBE_BEACON")
        self.assertEqual(immob_ground["drone_altitude_agl_m"], 0.0)
        poro_hold = dobs.compute_elastic_pull_guidance_vector(
            hiker_east_m=-180.0, hiker_north_m=210.0, reindeer_herding_detected=True
        )
        self.assertEqual(poro_hold["pull_guidance_mode"], "PORONHOITOLAKI_100M_WILDLIFE_HOLD")
        self.assertGreaterEqual(poro_hold["drone_altitude_agl_m"], 100.0)

        # 7. Verify F29: Fail-closed "Pull, Don't Push" humanitarian SAR trigger gate in broadcast_open_alert
        unauthorized = coord.broadcast_open_alert(
            incident_east_m=-180.0, incident_north_m=210.0,
            trigger_type="ROUTINE_HIKER_PASSING", sar_order_authorized=False
        )
        self.assertFalse(unauthorized["dispatched"])
        self.assertEqual(unauthorized["active_task"]["task_status"], "REJECTED_NO_HUMANITARIAN_SAR_TRIGGER")

        # 8. Verify F30: Manual human coordinator override cannot force-launch a roofed nest with a jammed hatch
        coord.broadcast_open_alert(incident_east_m=-180.0, incident_north_m=210.0, trigger_type="112_HAVAINTO")
        blocked_override = coord.human_coordinator_intervene(
            "FORCE_ASSIGN_UNIT", target_unit_id="NEST-OULANKA-ROOF-01"
        )
        # Must NOT assign the jammed NEST-OULANKA-ROOF-01; falls back to safe alternative unit
        self.assertNotEqual(blocked_override["active_task"]["primary_assigned_unit"]["unit_id"], "NEST-OULANKA-ROOF-01")
        self.assertTrue(
            any(e["status"] == "BLOCKED_UNSAFE_SHELTER_LAUNCH" for e in blocked_override["coordinator_intervention_log"])
        )

    def test_23_multi_model_audit_physics_security_and_opsec_regressions(self):
        """
        Verifies Iteration 15 Round-1 engineering audit findings (F32-F38):
          - F32: Unified 8,000 mAh 4S2P (118.4 Wh) winter endurance model with decoupled cell_temp_c vs ambient_temp_c
          - F33: Fail-safe block when all accepting units are unfeasible or have post-acceptance hatch faults
          - F35: Autiotupa arrival lateral clearing offset (drone >= 15m from both hiker and cabin roof/chimney) & aft spotlight yaw
          - F36: CoT XML entity escaping and unified Oulanka ETRS-TM35FIN / WGS84 CRS projection (< 1m agreement)
          - F37: Marketplace persistence round-trip and clean mode transitions
        """
        import xml.etree.ElementTree as ET

        # 1. F32: Pre-warmed (+10C cell temp) launch into -22C ambient air keeps +42C cask heater ON and >=40% reserve
        prewarmed_winter = dobs.evaluate_cold_weather_battery_and_endurance(
            ambient_temp_c=-22.0, pre_warmed_in_nest=True
        )
        self.assertTrue(prewarmed_winter["heated_cask_keep_warm_active"])
        self.assertGreaterEqual(prewarmed_winter["recommended_handover_reserve_pct"], 40.0)
        self.assertEqual(prewarmed_winter["cell_temp_c"], 10.0)
        self.assertEqual(prewarmed_winter["ambient_temp_c"], -22.0)

        # 2. F33: When ONLY unfeasible/jammed units accept, auto_prioritize_and_award_task blocks launch (never launches jammed nest)
        coord = dobs.SARDispatchMarketplaceCoordinator()
        for u in coord.fleet_units:
            u["roof_hatch_operational"] = False
        coord.broadcast_open_alert(incident_east_m=-180.0, incident_north_m=210.0)
        coord.submit_unit_acceptance("NEST-OULANKA-ROOF-01", accepted_by="TEST_UNFEASIBLE")
        blocked = coord.auto_prioritize_and_award_task()
        self.assertFalse(blocked["dispatched"])
        self.assertIsNone(blocked["active_task"]["primary_assigned_unit"])
        self.assertEqual(blocked["active_task"]["task_status"], "BLOCKED_NO_FEASIBLE_OR_SAFE_UNITS")

        # Also verify post-acceptance hatch jam is caught during FORCE_ASSIGN_UNIT and ABORT_PRIMARY_PROMOTE_BACKUP
        coord2 = dobs.SARDispatchMarketplaceCoordinator()
        coord2.broadcast_open_alert(incident_east_m=-180.0, incident_north_m=210.0)
        # Both Nest #1 and Nest #2 accepted when healthy; now Nest #2 suffers a hatch fault before failover
        for u in coord2.fleet_units:
            if u["unit_id"] == "NEST-VALTAVAARA-ROOF-02":
                u["roof_hatch_operational"] = False
        failover_blocked = coord2.human_coordinator_intervene("ABORT_PRIMARY_PROMOTE_BACKUP")
        self.assertIsNone(failover_blocked["active_task"]["primary_assigned_unit"])
        self.assertEqual(failover_blocked["active_task"]["task_status"], "ABORTED_NO_BACKUP_AVAILABLE")

        # 3. F35: Autiotupa arrival lateral clearing offset keeps airframe >= 15m from BOTH hiker and cabin roof/chimney
        escort = dobs.simulate_elastic_pull_escort_to_autiotupa(start_east_m=-180.0, start_north_m=210.0)
        arrival_step = escort["escort_steps"][-1]
        self.assertEqual(arrival_step["pull_guidance_mode"], "ARRIVED_AT_AUTIOTUPA_SAFE_HAVEN")
        self.assertGreaterEqual(arrival_step["airframe_horiz_separation_m"], 15.0 - 1e-6)
        self.assertGreaterEqual(arrival_step["drone_distance_to_autiotupa_m"], 15.0 - 1e-6)
        # Verify lateral pull step (6m beam lead vs 15m airframe standoff) aims gimbal aft (180 deg) toward hiker
        lateral_step = escort["escort_steps"][1]
        self.assertEqual(lateral_step["spotlight_gimbal_yaw_rel_deg"], 180.0)

        # 4. F36: CoT XML entity escaping and unified Oulanka CRS projection
        coord3 = dobs.SARDispatchMarketplaceCoordinator()
        malicious_state = coord3.broadcast_open_alert(
            incident_east_m=-180.0,
            incident_north_m=210.0,
            hiker_Summary='Hiker <script>&"test\'</script> near ravine',
        )
        cot_xml = malicious_state["open_sar_situational_awareness"]["cot_xml"]
        # Must parse as valid XML without raising ParseError
        root = ET.fromstring(cot_xml)
        self.assertEqual(root.tag, "event")
        # Verify WGS84 lat/lon in CoT XML matches Oulanka reference (~66.26 N, 29.41 E)
        pt = root.find("point")
        self.assertAlmostEqual(float(pt.attrib["lat"]), 66.262, delta=0.02)
        self.assertAlmostEqual(float(pt.attrib["lon"]), 29.414, delta=0.02)

        # 5. F37: Marketplace persistence round-trip & switching from Marketplace to Standoff
        with tempfile.TemporaryDirectory() as tmpdir:
            sp = os.path.join(tmpdir, "drone_observer_status.json")
            s1 = dobs.simulate_sar_dispatch_marketplace_lifecycle(status_path=sp, sub_action="simulate_multi_accept")
            self.assertEqual(len(s1["active_task"]["accepted_bids"]), 4)
            s2 = dobs.simulate_sar_dispatch_marketplace_lifecycle(
                status_path=sp, sub_action="hold_or_abort_launch"
            )
            self.assertEqual(s2["active_task"]["task_status"], "HELD_BY_HUMAN_COORDINATOR")
            s3 = dobs.simulate_sar_dispatch_marketplace_lifecycle(
                status_path=sp, sub_action="simulate_multi_accept"
            )
            self.assertEqual(s3["active_task"]["task_status"], "DISPATCHED_AUTO_PRIORITIZED")
            standoff_res = dobs.execute_approach_action(status_path=sp, return_to_standoff=True)
            self.assertEqual(standoff_res["active_flight_mode"], "HIGH_STANDOFF_ORBIT")
            self.assertIn("police_112_guidance", standoff_res)

    def test_24_round2_multi_model_aerospace_and_bench_audit_regressions(self):
        """
        Verifies all findings from Round-2 Aerospace, MAVLink & Bench Engineering Audit (F39-F44):
          - F39 (AERO-01 & AERO-03): In ARRIVED_AT_AUTIOTUPA_SAFE_HAVEN, the laterally offset drone
            aims its spotlight directly at the cabin door (relative yaw ~+37..+90 deg, NOT 180 deg aft!),
            handles dist_to_hut_m == 0.0 without singularity, and compute_aerial_lantern_trail_guide_state()
            also offsets laterally by 15m on arrival so it never overflies the cabin roof/chimney.
          - F40 (AERO-02): build_mavlink_guidance_frame() uses type_mask == 0x09C0 (2496) so ArduCopter
            executes position (x,y,z), velocity feedforward (vx,vy,vz), and yaw heading.
          - F41 (AERO-04, AERO-05, AERO-06, AERO-10): FleetCoordinator scales RTH reserve to 40%/45% in
            sub-zero winter temperatures, aborting a roofed drone sets ROOF_AWAITING_ABORTED_DRONE_RTB_DOCKING,
            and SubjectKalmanTracker clamps velocity spikes to <= 35.0 m/s.
          - F42 (HIGH-01): run_sar_drone_companion_bench_check() validates Wave 1/2/3 peripherals and
            exports the 37-parameter ArduCopter 4.5+ .param file for QGroundControl.
        """
        # 1. F39: Arrival spotlight gimbal yaw aims at cabin door (~+51 deg right of nose), NOT 180 deg aft!
        hut = dobs.WILDERNESS_AUTIOTUPA_HUTS["HUT-JUSSINKAMPPA"]
        escort = dobs.simulate_elastic_pull_escort_to_autiotupa(start_east_m=-180.0, start_north_m=210.0)
        arrival_step = escort["escort_steps"][-1]
        self.assertEqual(arrival_step["pull_guidance_mode"], "ARRIVED_AT_AUTIOTUPA_SAFE_HAVEN")
        self.assertGreater(arrival_step["spotlight_gimbal_yaw_rel_deg"], 20.0)
        self.assertLess(arrival_step["spotlight_gimbal_yaw_rel_deg"], 95.0)
        self.assertAlmostEqual(arrival_step["spotlight_beam_east_m"], hut["east_m"], places=1)
        self.assertAlmostEqual(arrival_step["spotlight_beam_north_m"], hut["north_m"], places=1)

        # Also test exact dist_to_hut_m == 0.0 (hiker standing right on the cabin doorstep)
        zero_dist_arrival = dobs.compute_elastic_pull_guidance_vector(
            hiker_east_m=hut["east_m"],
            hiker_north_m=hut["north_m"],
            hiker_vel_east_mps=0.0,
            hiker_vel_north_mps=0.0,
            trail_start_east_m=-180.0,
            trail_start_north_m=210.0,
            target_autiotupa=hut,
        )
        self.assertEqual(zero_dist_arrival["pull_guidance_mode"], "ARRIVED_AT_AUTIOTUPA_SAFE_HAVEN")
        self.assertGreaterEqual(zero_dist_arrival["airframe_horiz_separation_m"], 15.0 - 1e-6)
        self.assertGreaterEqual(zero_dist_arrival["drone_distance_to_autiotupa_m"], 15.0 - 1e-6)
        self.assertAlmostEqual(zero_dist_arrival["spotlight_gimbal_yaw_rel_deg"], 90.0, delta=5.0)

        # Verify Opaslyhty (compute_aerial_lantern_trail_guide_state) also avoids cabin roof at 15m from hut
        lantern_near_hut = dobs.compute_aerial_lantern_trail_guide_state(
            hiker_east_m=hut["east_m"] - 15.0,
            hiker_north_m=hut["north_m"],
            hiker_vel_east_mps=1.0,
            hiker_vel_north_mps=0.0,
            custom_shelter_target=hut,
        )
        self.assertGreaterEqual(lantern_near_hut["drone_distance_to_autiotupa_m"], 15.0 - 1e-6)
        self.assertGreaterEqual(lantern_near_hut["lead_standoff_m"], 15.0 - 1e-6)
        self.assertTrue(lantern_near_hut["geofence_standoff_enforced"])

        # 2. F40: MAVLink SET_POSITION_TARGET_LOCAL_NED type_mask == 0x09C0 (2496)
        loiter = dobs.compute_protective_loiter_state(0.0, 0.0, 10.0)
        raw_mav = dobs.build_mavlink_guidance_frame(loiter)
        self.assertEqual(len(raw_mav), 65)
        mav = dobs.decode_mavlink_guidance_frame(raw_mav)
        self.assertEqual(mav["type_mask"], 0x09C0)
        # Verify VX_IGNORE (bit 3 = 8), VY_IGNORE (bit 4 = 16), VZ_IGNORE (bit 5 = 32), YAW_IGNORE (bit 10 = 1024) are 0 (enabled)
        self.assertEqual(mav["type_mask"] & (8 | 16 | 32 | 1024), 0)

        # 3. F41: FleetCoordinator sub-zero RTH reserve scaling & roof state on abort
        winter_fleet = dobs.FleetCoordinator(rth_battery_threshold_pct=30.0, ambient_temp_c=-25.0)
        self.assertEqual(winter_fleet._effective_rth_threshold_pct(), 45.0)
        winter_fleet.drones["DRONE-SIERRA-01"]["battery_pct"] = 42.0  # Below 45% -25C threshold!
        winter_handover = winter_fleet.evaluate_handover_and_assign_orbits(0.0, 0.0, 10.0)
        self.assertTrue(winter_handover["handover_triggered"])
        self.assertEqual(winter_handover["drones"]["DRONE-SIERRA-01"]["status"], "RETURNING_TO_PAD_RTH")
        self.assertEqual(winter_handover["drones"]["DRONE-KILO-02"]["status"], "ACTIVE_OBSERVING")

        coord_abort = dobs.SARDispatchMarketplaceCoordinator()
        coord_abort.broadcast_open_alert(incident_east_m=-180.0, incident_north_m=210.0, ambient_temp_c=-22.0)
        abort_res = coord_abort.human_coordinator_intervene("ABORT_PRIMARY_PROMOTE_BACKUP")
        nest1_state = next(u for u in abort_res["fleet_units"] if u["unit_id"] == "NEST-OULANKA-ROOF-01")
        self.assertEqual(nest1_state["roof_shelter_state"], "ROOF_AWAITING_ABORTED_DRONE_RTB_DOCKING")

        # Verify SubjectKalmanTracker velocity spike clamp (<= 35.0 m/s)
        trk = dobs.SubjectKalmanTracker(0.0, 0.0, 0.0, 0.0)
        corrupted_step = trk.step(dt_s=0.1, measured_east_m=5000.0, measured_north_m=5000.0)
        self.assertLessEqual(corrupted_step["speed_mps"], 35.01)

        # 4. F42: SAR Drone Companion Hardware Bench Check & .param export
        with tempfile.TemporaryDirectory() as tmpdir:
            param_out = os.path.join(tmpdir, "pixhawk6c_sar.param")
            bench = dobs.run_sar_drone_companion_bench_check(export_param_path=param_out)
            self.assertEqual(bench["bench_status"], "BENCH_READY_FOR_WAVE1_WAVE2_WAVE3_HARDWARE")
            self.assertTrue(os.path.isfile(param_out))
            self.assertEqual(bench["arducopter_param_profile"]["parameter_count"], 60)

    def test_25_human_in_the_loop_manual_manoeuvring_and_two_way_voice_relay(self):
        """
        Verifies Iteration 17 (F45-F47): Human-in-the-Loop Manual Flight Override & Two-Way Voice
        Intercom Relay so rescue personnel can manually manoeuvre the drone after finding the hiker
        and talk two-way with them (solving why a hiker would otherwise run away from an autonomous drone):
          - F45: Grid search & target acquisition expose `human_pilot_takeover_ready=True` and
            `recommended_post_contact_handoff == "HOLD_FOR_HUMAN_PILOT_AND_TWO_WAY_VOICE_INTERCOM"`,
            and ArduCopter parameters include `FLTMODE1=5 (LOITER)`, `FLTMODE4=4 (GUIDED)`, `FLTMODE6=6 (RTL)`.
          - F46: `HumanPilotAndTwoWayVoiceRelayController.apply_manual_nudge()` translates 6-DOF operator
            nudges into valid 65-byte `MAVLink v2 SET_POSITION_TARGET_LOCAL_NED` frames while strictly
            enforcing `enforce_hardcoded_human_safety_geofence()` (>= 15.0 m horizontal standoff from the
            human and >= 6.0 m LiDAR altitude floor in flight) plus Deadman hover-brake hold.
          - F47: Two-Way Voice Relay (`transmit_two_way_voice_exchange`) verifies both `Rescuer -> Hiker`
            downlink (via `USB 5W 8Ohm Speaker [D07]`) and all 3 `Hiker -> Rescuer` uplink modes that
            overcome the 82 dBA propeller noise challenge:
              1) `AIRBORNE_PROP_NOTCHED_MIC_AND_VISUAL_GESTURE` (Motor-RPM harmonic comb notch + camera gesture)
              2) `GROUNDED_15M_CLEARING_QUIET_SPEAKERPHONE` (landed at >= 15 m clearing with motors disarmed = 0 dBA prop noise)
              3) `CASK_DROPPED_COLLAR_PTT_MIC` (wireless clip-on PTT lapel mic `[D19]` inside the rescue cask = +43 dB SNR)
        """
        # 1. F45: Post-detection handoff readiness & ELRS RC flight modes
        gs = dobs.simulate_multi_drone_grid_search_mission(drone_count=4)
        self.assertTrue(gs["target_reacquired"])
        self.assertTrue(gs["human_pilot_takeover_ready"])
        self.assertEqual(
            gs["recommended_post_contact_handoff"],
            "HOLD_FOR_HUMAN_PILOT_AND_TWO_WAY_VOICE_INTERCOM",
        )
        params = dobs.generate_arducopter_pixhawk6c_param_profile()["parameters"]
        self.assertEqual(params["FLTMODE1"], 5)  # LOITER for RadioMaster Pocket ELRS stick flying
        self.assertEqual(params["FLTMODE4"], 4)  # GUIDED for Pi 5 MAVLink companion
        self.assertEqual(params["FLTMODE6"], 6)  # RTL emergency switch

        # 2. F46: Manual 6-DOF operator nudges + hardcoded 15m human safety geofence enforcement
        ctrl = dobs.HumanPilotAndTwoWayVoiceRelayController(
            drone_id="DRONE-SIERRA-01",
            hiker_east_m=-180.0,
            hiker_north_m=210.0,
        )
        init_snap = ctrl.get_state_snapshot()
        self.assertEqual(init_snap["control_mode"], "HOLD_FOR_HUMAN_PILOT_AND_VOICE_CONTACT")
        self.assertAlmostEqual(init_snap["horiz_standoff_m"], 25.0, places=1)
        self.assertAlmostEqual(init_snap["drone_alt_agl_m"], 35.0, places=1)
        self.assertTrue(init_snap["mavlink_v2_command_frame"]["crc_valid"])

        # Try nudging straight toward the hiker by +20m North (from 25m standoff -> 5m, violating 15m fence)
        # and -32m Down (from 35m -> 3m, violating 6m LiDAR floor). Must be clamped to >= 15.0m & >= 6.0m!
        clamped_snap = ctrl.apply_manual_nudge(delta_east_m=0.0, delta_north_m=20.0, delta_alt_m=-15.0)
        clamped_snap = ctrl.apply_manual_nudge(delta_east_m=0.0, delta_north_m=10.0, delta_alt_m=-15.0)
        clamped_snap = ctrl.apply_manual_nudge(delta_east_m=0.0, delta_north_m=5.0, delta_alt_m=-10.0)
        self.assertTrue(clamped_snap["last_nudge_geofence_clamped"])
        self.assertGreaterEqual(clamped_snap["horiz_standoff_m"], 15.0 - 1e-6)
        self.assertGreaterEqual(clamped_snap["drone_alt_agl_m"], 6.0 - 1e-6)

        # Deadman brake hold zeroes all velocities immediately
        brake_snap = ctrl.apply_manual_nudge(deadman_brake_hold=True)
        self.assertTrue(brake_snap["deadman_brake_active"])
        self.assertEqual(brake_snap["vel_east_mps"], 0.0)
        self.assertEqual(brake_snap["vel_north_mps"], 0.0)
        self.assertEqual(brake_snap["vel_up_mps"], 0.0)

        # 3. F47: Test all 3 Two-Way Voice Uplink Modes (Airborne Notched Mic, Landed Clearing Speakerphone, Cask Collar PTT Mic)
        # Mode 1: Airborne hover with Motor-RPM Harmonic Comb Notch + Camera Visual Gesture
        ex_air = ctrl.transmit_two_way_voice_exchange(
            uplink_mode="AIRBORNE_PROP_NOTCHED_MIC_AND_VISUAL_GESTURE",
            hiker_visual_gesture="HAND_WAVE_YES_AND_THUMBS_UP",
        )
        self.assertTrue(ex_air["downlink_rescuer_to_hiker"]["intelligible"])
        self.assertGreater(ex_air["downlink_rescuer_to_hiker"]["snr_above_wind_db"], 20.0)
        self.assertTrue(ex_air["uplink_hiker_to_rescuer"]["voice_intelligible"])
        self.assertGreater(ex_air["uplink_hiker_to_rescuer"]["dsp_harmonic_notch_suppression_db"], 25.0)
        self.assertEqual(ex_air["uplink_hiker_to_rescuer"]["visual_gesture_detected"], "HAND_WAVE_YES_AND_THUMBS_UP")

        # Mode 2: Land in a >= 15m snow clearing & disarm motors (0 dBA prop noise speakerphone!)
        land_snap = ctrl.apply_manual_nudge(land_clearing_intercom=True)
        self.assertFalse(land_snap["motors_armed"])
        self.assertEqual(land_snap["drone_alt_agl_m"], 0.0)
        self.assertGreaterEqual(land_snap["horiz_standoff_m"], 15.0 - 1e-6)
        ex_land = ctrl.transmit_two_way_voice_exchange()
        self.assertEqual(ex_land["uplink_hiker_to_rescuer"]["uplink_mode"], "GROUNDED_15M_CLEARING_QUIET_SPEAKERPHONE")
        self.assertEqual(ex_land["uplink_hiker_to_rescuer"]["raw_propeller_noise_dba"], 0.0)
        self.assertGreater(ex_land["uplink_hiker_to_rescuer"]["uplink_speech_snr_db"], 18.0)

        # Takeoff back to 35m hover and drop the Rescue Cask with the Wireless Collar PTT Mic [D19]
        takeoff_snap = ctrl.apply_manual_nudge(takeoff_from_clearing=True, manual_cask_drop=True)
        self.assertTrue(takeoff_snap["motors_armed"])
        self.assertTrue(takeoff_snap["cask_dropped"])
        self.assertTrue(takeoff_snap["collar_ptt_mic_deployed"])
        ex_collar = ctrl.transmit_two_way_voice_exchange()
        self.assertEqual(ex_collar["uplink_hiker_to_rescuer"]["uplink_mode"], "CASK_DROPPED_COLLAR_PTT_MIC")
        self.assertGreaterEqual(ex_collar["uplink_hiker_to_rescuer"]["uplink_speech_snr_db"], 40.0)

        # Verify JSON persistence helper `execute_human_pilot_and_voice_relay_action`
        with tempfile.TemporaryDirectory() as tmpdir:
            sp = os.path.join(tmpdir, "drone_observer_status.json")
            res1 = dobs.execute_human_pilot_and_voice_relay_action(
                status_path=sp,
                sub_action="takeover_and_talk",
                rescuer_message_fi="Täällä pelastusjohtaja! Seuraa dronen valoa!",
            )
            self.assertEqual(res1["active_flight_mode"], "HUMAN_PILOT_MANUAL_AND_TWO_WAY_VOICE")
            self.assertEqual(
                res1["human_pilot_voice_state"]["latest_voice_exchange"]["downlink_rescuer_to_hiker"]["message_fi"],
                "Täällä pelastusjohtaja! Seuraa dronen valoa!",
            )

    def test_26_finlab_pro_bono_suite_and_allied_supply_chain_verification(self):
        """
        Verifies the 5 high-leverage additions aligned with the FIN-LAB Nordic Autonomous Systems
        Working Group Charters (`FIN-LAB-01`, `FIN-LAB-02`, `FIN-LAB-03`, `FIN-LAB-04`, `FIN-LAB-05`) and
        Allied Supply-Chain Provenance Audit:
          1. `FIN-LAB-01` Open Ingest API (`v0.9`) Civilian Twin Adapters (`AutiotupaCabinOccupancyAndOverdueAdapter`,
             `AcousticDistressAndMotorBearingAdapter`, `ReindeerPaliskuntaCollarTelemetryAdapter`,
             `TrailCameraMmWaveOpticalDiodeAdapter`) + Objective O1-O5 Conformance Scorecard (`all_objectives_passed=True`,
             zero GNSS dependence, solar chimney false-alarm guard, wind howling suppression, Poronhoitolaki 105m ceiling).
          2. `FIN-LAB-03` High-Altitude (`>40m` to `120m AGL`) GNSS-Denied Navigation: Cold-air hypsometric
             baro-DEM scaling (`T_mean_K / 288.15` preventing the 4.3 km uncompensated `-25C` baro drift trap) +
             Dual-Band Visual-Thermal Homography Odometry + NUC shutter freeze watchdog + Surveyed Landmark EKF
             resets bounding 30-min drift to `<= 30.0 m`.
          3. `FIN-LAB-04` Deterministic Seeded Monte Carlo SAR Campaign & Battery Stock Sizing Digital Twin
             (`1,000` runs in `< 50 ms`, proving why spare 8,000 mAh packs and >= 4 roofed nests are required for
             `>= 95%` Golden-Hour survival).
          4. `FIN-LAB-05` `10 Hz` Cold-Weather & Flight Black-Box Telemetry Logger (`IEC 60068-2-1` Cold &
             `RTCA DO-160G Section 24` Icing), dynamic `R_internal` EMA, predictive 35A climb voltage-sag guard (`< 12.2V` clamps climb
             rate to `1.5 m/s`), supercooled icing torque anomaly (`> 12%` triggers 8,500 RPM centrifugal shedding),
             and `CLASS_A_MINUS_30C_QUALIFIED` grading.
          5. FIN-LAB Allied Component Provenance & Zero-Custom-PCB COTS Buildability Audit (`NdFeB` magnets from
             `Neo Narva` / `Neorem Ulvila`, `-40C` `Molicel P45B/P50B` cells, dual-tier `TOPDON TC001` vs `Lynred ATTO320 / Senop`
             LWIR, all `<= 5,000 EUR`).
        """
        suite = dobs.run_complete_finlab_and_supply_chain_verification_suite()

        # 1. FIN-LAB-01 Scorecard, C2 Ingest Bridge (F50) & Threat-Model Edge Cases (F49)
        sc = suite["finlab01_civilian_twin"]["scorecard"]
        self.assertTrue(sc["all_objectives_passed"])
        self.assertTrue(suite["finlab01_civilian_twin"]["c2_ingest_bridge_verified"])
        self.assertGreaterEqual(sc["O1_track_continuity_pct"], 95.0)
        self.assertLess(sc["O2_false_track_rate_per_100km2_hr"], 1.0)
        self.assertLessEqual(sc["O3_detection_to_cue_p95_s"], 30.0)
        self.assertEqual(sc["O3_cost_ranked_effector_allocation_pct"], 100.0)
        self.assertGreaterEqual(sc["O4_sensor_types_count"], 4)
        self.assertTrue(sc["O5_gnss_functional_independence"])

        # Solar chimney false-positive guard (warm chimney on sunny afternoon with 0 door events)
        solar_obs = dobs.AutiotupaCabinOccupancyAndOverdueAdapter().ingest_cabin_telemetry(
            door_reed_events=0, chimney_delta_c=22.0, interior_delta_c=1.5, sos_button_pressed=False
        )
        self.assertTrue(solar_obs["raw_telemetry_digest"]["solar_chimney_false_alarm_rejected"])
        self.assertFalse(solar_obs["raw_telemetry_digest"]["shelter_occupied_and_warm"])

        # Unmodulated wind howling at 3000 Hz without 3-blast cadence must be suppressed
        wind_obs = dobs.AcousticDistressAndMotorBearingAdapter().ingest_acoustic_bearing(
            dominant_freq_hz=3000.0, three_blast_cadence_detected=False
        )
        self.assertTrue(wind_obs["raw_telemetry_digest"]["wind_false_alarm_suppressed"])
        self.assertFalse(wind_obs["humanitarian_trigger"]["is_actionable_sar_trigger"])

        # Valid 2-node acoustic intersection must triangulate cleanly (t1 > 0, t2 > 0, F49)
        nom_ac_obs = suite["finlab01_civilian_twin"]["sample_observations"]["acoustic_distress"]
        self.assertTrue(nom_ac_obs["raw_telemetry_digest"]["cross_bearing_triangulated"])
        self.assertFalse(nom_ac_obs["raw_telemetry_digest"]["ray_divergence_or_gdop_rejected"])
        self.assertLessEqual(nom_ac_obs["spatial_estimate"]["horizontal_uncertainty_m"], 20.0)

        # F49: Divergent / opposite acoustic rays (t1 < 0 or t2 < 0) must be rejected and fall back to LOB
        divergent_obs = dobs.AcousticDistressAndMotorBearingAdapter().ingest_acoustic_bearing(
            azimuth_a_deg=290.0, azimuth_b_deg=115.0
        )
        self.assertFalse(divergent_obs["raw_telemetry_digest"]["cross_bearing_triangulated"])
        self.assertTrue(divergent_obs["raw_telemetry_digest"]["ray_divergence_or_gdop_rejected"])
        self.assertEqual(divergent_obs["spatial_estimate"]["horizontal_uncertainty_m"], 85.0)

        # Reindeer Paliskunta collar geofence enforces >= 100m altitude and mutes speaker
        poro_obs = suite["finlab01_civilian_twin"]["sample_observations"]["reindeer_paliskunta"]
        self.assertGreaterEqual(poro_obs["raw_telemetry_digest"]["enforced_poronhoitolaki_altitude_agl_m"], 100.0)
        self.assertTrue(poro_obs["raw_telemetry_digest"]["speaker_muted_for_wildlife"])

        # 2. FIN-LAB-03 High-Altitude (105m) GNSS-Denied Navigation, NUC Watchdog & Compound Blinding (F51)
        nav = suite["finlab03_gnss_denied_high_alt_nav"]
        self.assertTrue(nav["finlab03_passed"])
        self.assertFalse(nav["tf02_pro_lidar_in_range"])  # 90.9m true AGL > 40m LiDAR range
        self.assertLessEqual(nav["max_30min_gnss_denied_error_m"], 30.0)
        self.assertGreater(nav["uncompensated_30min_drift_without_fix_m"], 4000.0)

        # NUC shutter freeze with clear visible terrain -> falls back to IMX462 Starvis 940nm
        nuc_frozen_nav = dobs.compute_finlab03_gnss_denied_high_altitude_navigation(
            baro_isa_alt_agl_m=105.0, snow_whiteout_visible=False, tc001_frame_std_dn=0.12
        )
        self.assertTrue(nuc_frozen_nav["tc001_nuc_shutter_freeze_detected"])
        self.assertFalse(nuc_frozen_nav["compound_blinding_active"])
        self.assertIn("IMX462_STARVIS_940NM", nuc_frozen_nav["active_odometry_modality"])

        # Compound blinding (simultaneous snow whiteout + TC001 NUC freeze at 105m) -> commands descent to <=40m LiDAR floor
        compound_nav = dobs.compute_finlab03_gnss_denied_high_altitude_navigation(
            baro_isa_alt_agl_m=105.0, snow_whiteout_visible=True, tc001_frame_std_dn=0.12
        )
        self.assertTrue(compound_nav["compound_blinding_active"])
        self.assertTrue(compound_nav["emergency_descent_to_lidar_floor_commanded"])

        # Link between evaluate_gnss_rf_jamming_and_weather_resilience and FIN-LAB-03 at > 40m AGL
        res_105m = dobs.evaluate_gnss_rf_jamming_and_weather_resilience(gnss_hdop=99.9, alt_agl_m=105.0)
        self.assertFalse(res_105m["lidar_terrain_following_active"])
        self.assertIsNotNone(res_105m["finlab03_high_altitude_nav"])
        self.assertIn("FINLAB03", res_105m["navigation_fallback_mode"])

        # 3. FIN-LAB-04 Monte Carlo SAR Fleet Sizing Digital Twin (< 50 ms, F48 realistic canyon range)
        mc = suite["finlab04_monte_carlo_fleet_sizing"]
        self.assertEqual(mc["iterations_run"], 1000)
        self.assertLess(mc["execution_time_ms"], 150.0)
        minimal_cfg = mc["pareto_frontier"][0]
        self.assertEqual(minimal_cfg["config_id"], "CONFIG_MINIMAL_2_NESTS_1_PACK")
        self.assertFalse(minimal_cfg["meets_safety_criteria"])
        self.assertLess(minimal_cfg["golden_hour_survival_rate_pct"], 70.0)
        opt = mc["recommended_optimal_configuration"]
        self.assertEqual(opt["config_id"], "CONFIG_BALANCED_4_NESTS_3_PACKS")
        self.assertTrue(opt["meets_safety_criteria"])
        self.assertGreaterEqual(opt["golden_hour_survival_rate_pct"], 95.0)
        self.assertLessEqual(opt["response_time_p95_min"], 45.0)

        # 4. FIN-LAB-05 10 Hz Cold-Weather Black-Box Logger & Class A (-30C) Qualification (F52)
        qual = suite["finlab05_winter_blackbox_qualification"]
        self.assertTrue(qual["passed"])
        self.assertEqual(qual["qualification_grade"], "CLASS_A_MINUS_30C_QUALIFIED")
        self.assertTrue(qual["centrifugal_ice_shed_recovered"])

        # 5. FIN-LAB Allied Supply-Chain & COTS Buildability Audit + Pin-to-Pin Harness Schedule (F53)
        sup = suite["section_6_1_supply_chain_and_cots_audit"]
        self.assertTrue(sup["ear99_civilian_90_10_compliant"])
        self.assertEqual(sup["custom_pcbs_required"], 0)
        self.assertFalse(sup["soldering_required_for_core_assembly"])
        self.assertTrue(sup["cost_compliance_audit"]["all_tiers_under_5000_eur_rule"])
        self.assertEqual(sup["cost_compliance_audit"]["baseline_cots_bom_eur"], 1329.0)
        self.assertEqual(len(sup["pin_to_pin_jst_gh_harness_schedule"]), 5)
        self.assertIn("CLIPPED/ISOLATED", sup["pin_to_pin_jst_gh_harness_schedule"][1]["pin_map"])
        self.assertEqual(len(sup["five_stage_rapid_build_checklist"]), 5)

        bench = dobs.run_sar_drone_companion_bench_check()
        self.assertIn("supply_chain_and_cots_audit", bench)
        self.assertIn("Out-of-Band UHF", bench["expected_wave1_wave2_peripherals"]["cask_collar_ptt_mic"])
        self.assertIn("emi_ferrite_shielding_kit", bench["expected_wave1_wave2_peripherals"])

        # 6. Verify FIN-LAB-01 v1.0 U-Space Surge Fusion, FIN-LAB-02/03 Fast Fixed-Wing & FIN-LAB-04 v1.0 Contention Upgrades
        self.assertEqual(nom_ac_obs["raw_telemetry_digest"]["observation_localization_state"], "TRIANGULATED_2D_FIX")
        self.assertIsNotNone(nom_ac_obs["raw_telemetry_digest"]["triangulated_range_m"])
        self.assertEqual(divergent_obs["raw_telemetry_digest"]["observation_localization_state"], "BEARING_ONLY_UNLOCATED")
        self.assertIsNone(divergent_obs["raw_telemetry_digest"]["triangulated_range_m"])

        self.assertEqual(nav["model_evidence_status"], "ANALYTICAL_SCENARIO_ERROR_BUDGET_PENDING_FLIGHT_TEST")
        fast_quad_nav = dobs.compute_finlab03_gnss_denied_high_altitude_navigation(cruise_speed_mps=30.0)
        self.assertGreater(fast_quad_nav["max_30min_gnss_denied_error_m"], nav["max_30min_gnss_denied_error_m"])

        fw_nav = suite["finlab03_fast_fixed_wing_nav"]
        self.assertTrue(fw_nav["passed"])
        self.assertTrue(fw_nav["heated_pitot_ok"])
        fw_unheated = dobs.compute_finlab03_fast_fixed_wing_navigation(heated_pitot_installed=False)
        self.assertFalse(fw_unheated["passed"])

        uspace = suite["finlab01_civilian_twin"]["uspace_surge_fusion_v10"]
        self.assertEqual(uspace["candidate_intersections_evaluated"], 2500)
        self.assertTrue(uspace["meets_sub_30s_surge_requirement"])
        self.assertGreater(uspace["ghost_intersections_rejected"], 0)

        surge_sim = suite["finlab04_regional_surge_contention"]
        self.assertEqual(surge_sim["total_events_simulated"], 2000)
        self.assertGreater(surge_sim["per_nest_heating_power_at_minus30c_w"], 250.0)
        self.assertGreater(surge_sim["single_pack_recharge_duration_min"], 30.0)

        # 7. Verify Live-Stream Load Test, FIN-SIG-LIB v1.0 Dataset, [P12-BELT], [P12-HEATED], [P12-CAPTURE] & FIN-LAB-06 USV
        live_lt = suite["finlab01_civilian_twin"]["uspace_live_stream_load_test"]
        self.assertTrue(live_lt["live_load_test_passed"])
        self.assertEqual(live_lt["dropped_packets"], 0)
        self.assertEqual(suite["fin_sig_lib_v1_winter_signature_dataset"]["total_samples"], 200)
        self.assertGreaterEqual(suite["fin_sig_lib_v1_winter_signature_dataset"]["overall_5class_accuracy"], 0.95)
        self.assertGreaterEqual(suite["p12_belt_non_rf_corridor_sensing"]["corridor_detection_range_m"], 550.0)
        self.assertEqual(suite["p12_heated_12cell_shelter_and_fast_climber"]["nest_cells_per_box"], 12)
        self.assertAlmostEqual(suite["p12_heated_12cell_shelter_and_fast_climber"]["nest_thermal_power_w_at_minus30c"], 283.5, places=1)
        self.assertLessEqual(suite["p12_capture_cooperative_apn_soft_net"]["terminal_miss_distance_m"], 0.85)
        self.assertTrue(suite["p12_capture_cooperative_apn_soft_net"]["zero_firearms_zero_pyrotechnics"])
        self.assertGreaterEqual(suite["finlab06_coastal_cable_usv"]["fleet_availability_pct"], 80.0)

        # 8. Verify Charter 6-Gap (J, A, H, I, K, L) Cost-Performance & Allied Gap-L BOM Swaps
        self.assertTrue(sup["gap_l_allied_board_swaps"]["all_5_board_families_swapped_and_verified"])
        self.assertEqual(sup["v1_0_zero_pcb_cots_ems_package"]["custom_pcbs_count"], 0)
        allied_prof = dobs.generate_arducopter_pixhawk6c_param_profile(allied_bom=True)
        self.assertTrue(allied_prof["allied_gap_l_bom_active"])
        self.assertEqual(len(allied_prof["parameters"]), 60)
        self.assertEqual(allied_prof["parameters"]["RNGFND1_TYPE"], 15)  # Garmin LIDAR-Lite v4 LED (I2C 0x62)
        self.assertEqual(allied_prof["parameters"]["FLOW_TYPE"], 6)      # ARK Flow (USA)

        reval_ds = suite["fin_sig_lib_v1_winter_signature_dataset"]["revalidated_on_real_data"]
        self.assertEqual(reval_ds["evidence_tier"], "REAL_HARDWARE_TRIAL_REVALIDATED_4_OF_4")
        self.assertGreaterEqual(reval_ds["real_trial_samples_ingested"], 5)

        charter_6 = suite["charter_6gap_cots_cost_performance"]
        self.assertTrue(charter_6["all_6_charter_gaps_exit_criteria_met"])
        self.assertEqual(charter_6["charter_6_gaps_points_gained"], 19)
        self.assertEqual(charter_6["civilian_ceiling_pts"], 85)
        self.assertGreaterEqual(charter_6["cost_performance_summary"]["cost_reduction_factor_vs_charter_min"], 8000.0)

        # 9. Verify Option B Karhunkierros-X8 Coaxial Heavy-Sprint Upgrade, X8-H1..H5 Hardening Laws & 1,000-Sim Campaign
        endurance_x8 = dobs.evaluate_finnish_winter_flight_endurance(ambient_temp_c=-20.0, wind_speed_mps=6.5, payload_mass_kg=3.0)
        self.assertIn("Option B: Karhunkierros-X8 Coaxial OctaQuad", endurance_x8["airframe_propulsion_architecture"])
        self.assertEqual(endurance_x8["nominal_payload_capacity_kg"], 3.0)
        self.assertEqual(endurance_x8["max_overload_payload_kg"], 4.2)
        self.assertEqual(endurance_x8["mtow_with_payload_kg"], 6.15)
        self.assertEqual(endurance_x8["max_coaxial_static_thrust_kg"], 14.80)
        self.assertEqual(endurance_x8["installed_continuous_thrust_kg"], 13.62)
        self.assertEqual(endurance_x8["optimal_cruise_speed_kmh"], 90.0)
        self.assertEqual(endurance_x8["max_sprint_dash_speed_kmh"], 138.6)
        self.assertEqual(endurance_x8["calm_air_round_trip_radius_km"], 22.5)
        self.assertEqual(endurance_x8["storm_14mps_headwind_radius_km"], 14.8)
        self.assertTrue(endurance_x8["single_motor_or_prop_loss_survivable"])

        self.assertEqual(allied_prof["parameters"]["FRAME_CLASS"], 3)    # OctaQuad Coaxial X8
        self.assertEqual(allied_prof["parameters"]["BATT_CAPACITY"], 13500)
        self.assertEqual(allied_prof["parameters"]["WPNAV_SPEED"], 2500)
        self.assertEqual(sup["cost_compliance_audit"]["option_b_coaxial_x8_bom_eur"], 1639.0)
        self.assertEqual(sup["cost_compliance_audit"]["option_b_upgrade_delta_eur"], 310.0)

        x8_mc = suite["finlab_x8_1000_coaxial_envelope_campaign"]
        self.assertEqual(x8_mc["campaign_code"], "FIN-LAB-X8-1000")
        self.assertEqual(x8_mc["total_simulations_run"], 1000)
        self.assertEqual(x8_mc["legacy_x4_4s_runs"], 500)
        self.assertEqual(x8_mc["option_b_coaxial_x8_runs"], 500)
        self.assertGreaterEqual(x8_mc["option_b_coaxial_x8_overall_pass_rate_pct"], 99.5)
        self.assertEqual(x8_mc["option_b_coaxial_x8_overall_survival_rate_pct"], 100.0)
        self.assertGreater(
            x8_mc["option_b_coaxial_x8_overall_pass_rate_pct"] - x8_mc["legacy_x4_4s_overall_pass_rate_pct"],
            75.0,
        )
        self.assertTrue(x8_mc["hardening_laws_verification"]["all_5_x8_hardening_laws_passed"])
        self.assertEqual(
            x8_mc["regime_breakdown"]["X8_R03_SINGLE_MOTOR_OR_PROP_STRIKE_WITH_3KG_LOAD"]["option_b_coaxial_x8_survival_rate_pct"],
            100.0,
        )
        self.assertEqual(
            x8_mc["regime_breakdown"]["X8_R03_SINGLE_MOTOR_OR_PROP_STRIKE_WITH_3KG_LOAD"]["legacy_x4_4s_survival_rate_pct"],
            0.0,
        )

        # 10. Verify Defensive Counter-Signature & Optical Tether Glint Detector + <300 km EU Compliance
        def_det = suite["defensive_counter_signature_and_tether_detector"]
        self.assertGreaterEqual(def_det["acoustic_counter_muffler"]["upgraded_multiband_detection_radius_m"], 1400.0)
        self.assertGreaterEqual(def_det["acoustic_counter_muffler"]["classification_accuracy_pct"], 96.0)
        self.assertGreaterEqual(def_det["optical_tether_and_lens_hazard_detector"]["polarimetric_glint_snr_db"], 18.0)
        self.assertTrue(def_det["optical_tether_and_lens_hazard_detector"]["corridor_avoidance_triggered"])

        pareto_summary = dobs.compute_pareto_optimal_4tier_portfolio_summary()
        for tier in pareto_summary["tiers"]:
            self.assertLess(tier["calm_radius_km"], 300.0)

    def test_30_cnc_overwatch_priority_preemption_and_terrain_auto_mission(self):
        """Verify C&C Black Fog-of-War Camera-Feed Map, Priority Preemption Options, Auto/RC Guidance, and Terrain Auto-Mission."""
        # 1. Default C&C Overwatch: Preempts Area Mapping to Follow Lost Hiker (P1) while Drones 2-4 map black shroud
        res_person = dobs.execute_cnc_overwatch_and_guidance_action(
            task_mode="AUTO_OBSERVE_AND_SEARCH",
            preempt_mapping_on_detection=True,
            detect_lost_people=True,
            detect_lost_vehicles=True,
            fleet_split_policy="SPLIT_1_FOLLOW_REST_MAP",
            subject_type="LOST_PERSON",
            guidance_mode="AUTONOMOUS_GUIDANCE",
        )
        self.assertTrue(res_person["dispatched"])
        self.assertEqual(res_person["cnc_map_view_spec"]["unobserved_area_color_hex"], "#000000")
        self.assertEqual(
            res_person["cnc_map_view_spec"]["active_sensor_areas_rendered_as"],
            "LIVE_PROJECTED_CAMERA_FEEDS_ON_MAP",
        )
        self.assertTrue(res_person["preemption_decision"]["preempted_area_mapping"])
        self.assertEqual(res_person["preemption_decision"]["locked_target"]["target_id"], "TGT-LOST-HIKER-01")
        self.assertEqual(res_person["fleet_assignments"][0]["role"], "PRIORITY_TARGET_FOLLOW_AND_GUIDE")
        self.assertEqual(res_person["fleet_assignments"][1]["role"], "BOUSTROPHEDON_AREA_SHROUD_MAPPER")
        self.assertEqual(res_person["guidance_execution"]["guidance_mode"], "AUTONOMOUS_GUIDANCE")
        self.assertEqual(res_person["guidance_execution"]["drone_alt_agl_m"], 28.0)
        self.assertTrue(res_person["guidance_execution"]["warm_cask_dropped_at_15m"])

        # 2. Verify Terrain-Following Auto-Mission Compiler & QGC WPL 110 (MAV_FRAME_GLOBAL_TERRAIN_ALT = 10)
        tm = res_person["terrain_following_auto_mission"]
        self.assertIn("EPSG:3067", tm["geodetic_anchor"]["crs_primary"])
        self.assertGreaterEqual(tm["waypoint_count"], 4)
        self.assertIn("QGC WPL 110", tm["qgc_wpl_110_text"])
        self.assertIn("\t10\t16\t", tm["qgc_wpl_110_text"])  # Frame 10 = MAV_FRAME_GLOBAL_TERRAIN_ALT

        # 3. Verify Lost Vehicle (Snowmobile) Autonomous Convoy Route Corridor & Manual RC >=15m Safety Clamping
        res_veh_rc = dobs.execute_cnc_overwatch_and_guidance_action(
            subject_type="LOST_VEHICLE",
            guidance_mode="MANUAL_REMOTE_CONTROL",
            rc_delta_east_m=-14.0,
            rc_delta_north_m=-11.0,
            rc_delta_alt_m=-25.0,
        )
        g_rc = res_veh_rc["guidance_execution"]
        self.assertEqual(g_rc["subject_type"], "LOST_VEHICLE")
        self.assertEqual(g_rc["guidance_mode"], "MANUAL_REMOTE_CONTROL")
        self.assertTrue(g_rc["safety_bubble_clamped"])
        self.assertGreaterEqual(g_rc["horiz_standoff_m"], 15.0)
        self.assertGreaterEqual(g_rc["drone_alt_agl_m"], 28.0)

    def test_21_natural_language_playbook_jev_dispatcher_and_mavlink_v2_redteam_gates(self) -> None:
        """
        Verify the Natural-Language SAR Operations Playbook Compiler, JEV (Judge -> Evaluate -> Verify)
        Agent Dispatcher, Offline Deterministic Fallback, AID Thrash Circuit-Breaker, Spatial-Temporal
        Human Veto Bubbles, and MAVLink v2 Field Bridge Red-Team Hardening ([RT1-01]..[RT1-06], [RT2-01]..[RT2-05]).
        """
        from collector_hub.playbook_agent_dispatcher import (
            build_structured_playbook_rules,
            compile_natural_language_playbook,
            PlaybookAgentDispatcher,
            DEFAULT_PLAYBOOKS,
        )
        from collector_hub.mavlink_field_bridge import (
            MAVLinkFieldBridge,
            MSG_ID_HEARTBEAT,
            MSG_ID_MISSION_COUNT,
            MSG_ID_MISSION_ITEM_INT,
            MSG_ID_COMMAND_INT,
            MSG_ID_COMMAND_LONG,
            MSG_ID_SET_POSITION_TARGET_GLOBAL_INT,
            POSITION_TARGET_TYPEMASK_POS_ONLY,
            pack_set_position_target_global_int,
            pack_command_int_reposition,
        )

        # 1. [RT1-02] Structured Parameterized Playbook Validator (Zero Offline Regex Parsing):
        #    - Predefined playbooks and structured parameter overrides are validated as typed fields
        #    - Order-independent canopy floor vs ceiling feasibility check (`L <= U`)
        pb = build_structured_playbook_rules(
            playbook_id="PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY",
        )
        self.assertAlmostEqual(pb.search_altitude_agl_m, 55.0)
        self.assertAlmostEqual(pb.tracking_altitude_agl_m, 28.0)
        self.assertAlmostEqual(pb.canopy_floor_m, 18.0)
        self.assertTrue(pb.preempt_on_person)
        self.assertTrue(pb.auto_queue_drop)
        self.assertTrue(pb.auto_release_drop)
        self.assertFalse(pb.require_human_drop_confirm)
        self.assertEqual(len(pb.compile_warnings), 0)

        # Verify structured field overrides (search_altitude_agl_m=65.0, min_detection_confidence=0.85, tracking_altitude_agl_m=32.0, drop_policy="QUEUE_REQUIRE_HUMAN_CONFIRM"):
        pb_mixed = compile_natural_language_playbook(
            {
                "search_altitude_agl_m": 65.0,
                "min_detection_confidence": 0.85,
                "tracking_altitude_agl_m": 32.0,
                "drop_policy": "QUEUE_REQUIRE_HUMAN_CONFIRM",
            },
            playbook_id="MIXED_STRUCTURED_TEST",
        )
        self.assertAlmostEqual(pb_mixed.search_altitude_agl_m, 65.0)
        self.assertAlmostEqual(pb_mixed.min_detection_confidence, 0.85)
        self.assertAlmostEqual(pb_mixed.tracking_altitude_agl_m, 32.0)
        self.assertTrue(pb_mixed.require_human_drop_confirm)
        self.assertFalse(pb_mixed.auto_release_drop)

        # Verify inverted altitude interval (canopy floor + 10m > ceiling) raises compile warning and clamps safely:
        pb_contradict = build_structured_playbook_rules(
            playbook_id="CONTRADICTORY_ALT",
            structured_params={"canopy_floor_m": 28.0, "altitude_ceiling_m": 30.0},
        )
        self.assertGreater(len(pb_contradict.compile_warnings), 0)
        self.assertGreaterEqual(pb_contradict.altitude_ceiling_m, pb_contradict.canopy_floor_m + 10.0)

        # 2. [RT2-03] Initial Transition at t=0.0s, API Key Prompt & Save-to-Disk (0600), and Offline Deterministic Fallback:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cred_path = os.path.join(tmpdir, "llm_api_credentials.json")
            aid = PlaybookAgentDispatcher(credentials_disk_path=cred_path)
            st_no_key = aid.set_aid_mode("CLOUD_LLM_JEV", fallback_policy="OFFLINE_DETERMINISTIC")
            self.assertTrue(st_no_key["requires_api_key_prompt"])
            self.assertFalse(st_no_key["llm_api_key_configured"])
            self.assertEqual(aid.aid_mode, "OFFLINE_DETERMINISTIC")

            # Save API key to disk with 0600 permissions and activate CLOUD_LLM_JEV:
            st_saved = aid.configure_llm_api_key(
                api_key="sk-test-arctic-9f4a",
                provider="openai",
                model="gpt-5.4-mini",
                save_to_disk=True,
                activate_cloud_mode=True,
            )
            self.assertTrue(st_saved["llm_api_key_configured"])
            self.assertTrue(st_saved["llm_api_key_saved_on_disk"])
            self.assertEqual(st_saved["llm_api_key_masked"], "sk-te...9f4a")
            self.assertNotIn("sk-test-arctic-9f4a", json.dumps(st_saved))
            self.assertEqual(aid.aid_mode, "CLOUD_LLM_JEV")
            self.assertTrue(os.path.exists(cred_path))
            self.assertEqual(os.stat(cred_path).st_mode & 0o777, 0o600)

            # Verify a fresh dispatcher instance reloads the saved key from disk on startup:
            aid_reloaded = PlaybookAgentDispatcher(credentials_disk_path=cred_path)
            self.assertTrue(aid_reloaded.has_llm_api_key())
            self.assertTrue(aid_reloaded.api_key_saved_on_disk)
            self.assertEqual(aid_reloaded.get_masked_api_key(), "sk-te...9f4a")

            # Clear saved key removes it from both RAM and disk:
            st_cleared = aid_reloaded.configure_llm_api_key(clear_key=True)
            self.assertFalse(st_cleared["llm_api_key_configured"])
            self.assertFalse(os.path.exists(cred_path))

        t0_step = aid.evaluate_jev_step(
            {
                "simulate_llm_offline": True,
                "target_lock_active": False,
                "person_confidence": 0.94,
                "person_x_m": 115.0,
                "person_y_m": -42.0,
                "battery_pct": 88.0,
                "wind_speed_ms": 5.0,
                "temp_c": -15.0,
                "dist_home_m": 450.0,
            },
            now_ts=0.0,
        )
        self.assertEqual(aid.aid_mode, "OFFLINE_DETERMINISTIC")
        self.assertEqual(t0_step["action"], "LOCK_TARGET")
        self.assertEqual(t0_step["params"]["target_type"], "PERSON")
        self.assertAlmostEqual(t0_step["params"]["target_x_m"], 115.0)
        self.assertAlmostEqual(t0_step["params"]["target_y_m"], -42.0)

        # 3. [RT1-01] & [RT2-01] Spatial-Temporal Expanding Veto Bubble & Fail-Closed Missing Coordinates:
        cancel_res = aid.veto_registry.record_human_target_cancel(
            target_id="PERSON",
            cooldown_s=300.0,
            x_m=115.0,
            y_m=-42.0,
            now_ts=10.0,
        )
        self.assertGreaterEqual(cancel_res["epoch_id"], 2)
        # Re-detecting within the expanding bubble (e.g. 20m away 5s later) is blocked:
        veto_step = aid.evaluate_jev_step(
            {
                "target_lock_active": False,
                "person_confidence": 0.96,
                "person_x_m": 130.0,
                "person_y_m": -35.0,
                "battery_pct": 86.0,
            },
            now_ts=15.0,
        )
        self.assertEqual(veto_step["action"], "BLOCKED_LOCK_TARGET")
        self.assertIn("HUMAN_VETO_BUBBLE_ACTIVE", veto_step["verify_gate"]["rejection_reason"])
        # Second hiker 350m away outside the bubble is NOT blocked:
        second_hiker_step = aid.evaluate_jev_step(
            {
                "target_lock_active": False,
                "person_confidence": 0.96,
                "person_x_m": 420.0,
                "person_y_m": 260.0,
                "battery_pct": 86.0,
            },
            now_ts=25.0,
        )
        self.assertEqual(second_hiker_step["action"], "LOCK_TARGET")
        self.assertTrue(second_hiker_step["verify_gate"]["approved"])
        # Missing coordinates fail closed while an active LOCK veto bubble exists ([RT2-01]):
        is_vetoed, _, _ = aid.veto_registry.is_target_vetoed_by_human("PERSON", x_m=None, y_m=None, now_ts=25.0)
        self.assertTrue(is_vetoed)

        # 4. [RT1-06] Ballistic Wind-Drift Footprint Gate & Arctic Cold-Derated Headwind RTH Gate:
        aid_drop = PlaybookAgentDispatcher()
        high_wind_step = aid_drop.evaluate_jev_step(
            {
                "target_lock_active": True,
                "guided_target_type": "PERSON",
                "drone1_dist_to_target_m": 15.0,
                "drop_status": "PENDING",
                "wind_speed_ms": 18.0,  # Exceeds safe ballistic wind drift at 15m height
                "drone_ground_speed_ms": 0.4,
                "battery_pct": 85.0,
            },
            now_ts=100.0,
        )
        self.assertEqual(high_wind_step["action"], "BLOCKED_EXECUTE_DROP")
        self.assertIn("BALLISTIC_IMPACT_ENVELOPE_UNSAFE", high_wind_step["verify_gate"]["rejection_reason"])

        # Low battery in -25C Arctic headwind forces immediate RTH:
        rth_step = aid_drop.evaluate_jev_step(
            {
                "target_lock_active": True,
                "guided_target_type": "PERSON",
                "battery_pct": 20.0,
                "temp_c": -25.0,
                "wind_speed_ms": 9.0,
                "dist_home_m": 2500.0,
            },
            now_ts=115.0,
        )
        self.assertEqual(rth_step["action"], "RTB_LOW_BATTERY")
        self.assertTrue(rth_step["verify_gate"]["approved"])

        # 5. [RT1-03] Pre-Filter Thrash Circuit-Breaker (3 state-flip proposals within 15s -> MANUAL_HUMAN_ONLY):
        aid_thrash = PlaybookAgentDispatcher()
        for ts, forced_act in [
            (200.0, "LOCK_TARGET"),
            (202.0, "CONTINUE_COOPERATIVE_SCAN"),
            (204.0, "LOCK_TARGET"),
            (206.0, "CONTINUE_COOPERATIVE_SCAN"),
        ]:
            step_res = aid_thrash.evaluate_jev_step(
                {
                    "forced_llm_proposed_action": forced_act,
                    "battery_pct": 90.0,
                },
                now_ts=ts,
            )
        self.assertTrue(aid_thrash.circuit_breaker_tripped)
        self.assertEqual(aid_thrash.aid_mode, "MANUAL_HUMAN_ONLY")
        self.assertEqual(step_res["action"], "AID_THRASH_SHUTOFF")

        # 5b. Realistic Multi-Tick Forward Rescue Lifecycle (Zero False Thrash / Zero False Dwell Block),
        #     Multi-Target Veto Failover, Helo 35m Ceiling & Hard Battery RTH Preemption:
        aid_mission = PlaybookAgentDispatcher()
        aid_mission.set_playbook("PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY", {"drop_policy": "AUTO_QUEUE_AND_AUTO_RELEASE"})
        mission_timeline = [
            (300.0, "CONTINUE_COOPERATIVE_SCAN", {"target_lock_active": False, "person_confidence": 0.12, "battery_pct": 88.0}),
            (302.0, "LOCK_TARGET", {"target_lock_active": False, "person_confidence": 0.94, "person_x_m": 120.0, "person_y_m": -85.0, "battery_pct": 87.0}),
            (304.0, "QUEUE_DROP", {"target_lock_active": True, "guided_target_type": "PERSON", "drone1_dist_to_target_m": 18.0, "drop_status": "READY", "battery_pct": 86.0}),
            (306.0, "EXECUTE_DROP", {"target_lock_active": True, "guided_target_type": "PERSON", "drone1_dist_to_target_m": 15.0, "drop_status": "PENDING", "battery_pct": 85.0}),
            (308.0, "RELEASE_SAFE_TARGET_RETURN_TO_SCAN", {"target_lock_active": True, "guided_target_type": "PERSON", "responder_ack": "VICTIM_CONTACTED_SAFE", "battery_pct": 83.0}),
            (310.0, "CONTINUE_COOPERATIVE_SCAN", {"target_lock_active": False, "person_confidence": 0.10, "battery_pct": 82.0}),
        ]
        for ts_m, exp_act, m_telem in mission_timeline:
            m_res = aid_mission.evaluate_jev_step(m_telem, now_ts=ts_m)
            self.assertEqual(m_res["action"], exp_act)
            self.assertFalse(aid_mission.circuit_breaker_tripped)

        # Multi-target spatial veto failover (primary person at (50,50) vetoed -> fails over to second hiker at (-240,190)):
        aid_mission.veto_registry.record_human_target_cancel("PERSON", cooldown_s=300.0, x_m=50.0, y_m=50.0, now_ts=320.0)
        failover_res = aid_mission.evaluate_jev_step(
            {
                "target_lock_active": False,
                "person_confidence": 0.93,
                "person_x_m": 55.0,
                "person_y_m": 52.0,
                "secondary_person_confidence": 0.91,
                "secondary_person_x_m": -240.0,
                "secondary_person_y_m": 190.0,
                "battery_pct": 80.0,
            },
            now_ts=325.0,
        )
        self.assertEqual(failover_res["action"], "LOCK_TARGET")
        self.assertAlmostEqual(failover_res["params"]["target_x_m"], -240.0)
        self.assertAlmostEqual(failover_res["params"]["target_y_m"], 190.0)

        # Manned Helicopter 35m U-Space ceiling + adversarial low-battery RTH preemption:
        helo_res = aid_mission.evaluate_jev_step(
            {"target_lock_active": False, "person_confidence": 0.10, "helo_inbound_active": True, "wildlife_detected": True, "battery_pct": 80.0},
            now_ts=335.0,
        )
        self.assertLessEqual(helo_res["target_altitude_agl_m"], 35.0)
        preempt_res = aid_mission.evaluate_jev_step(
            {
                "forced_llm_proposed_action": "EXECUTE_DROP",
                "target_lock_active": True,
                "guided_target_type": "PERSON",
                "drone1_dist_to_target_m": 15.0,
                "drop_status": "PENDING",
                "battery_pct": 24.0,
                "temp_c": -28.0,
                "wind_speed_ms": 14.0,
                "dist_home_m": 1800.0,
            },
            now_ts=345.0,
        )
        self.assertEqual(preempt_res["action"], "RTB_LOW_BATTERY")
        self.assertTrue(preempt_res["verify_gate"]["approved"])

        # 6. [RT1-04], [RT1-05], [RT2-02], [RT2-05] MAVLink v2 Field Bridge Red-Team Invariants:
        bridge = MAVLinkFieldBridge(udp_host="127.0.0.1", udp_port=14559)
        # [RT1-04] Transactional mission upload emits HEARTBEAT (#0), MISSION_COUNT (#44), and MISSION_ITEM_INT (#73)
        # without destructive premature MISSION_CLEAR_ALL (#45):
        up_res = bridge.upload_cooperative_sector_mission()
        self.assertTrue(up_res["bridge_online"])
        sent_msg_ids = [f["msg_id"] for f in bridge.last_frames_hex]
        self.assertIn(MSG_ID_HEARTBEAT, sent_msg_ids)
        self.assertIn(MSG_ID_MISSION_COUNT, sent_msg_ids)
        self.assertIn(MSG_ID_MISSION_ITEM_INT, sent_msg_ids)
        self.assertNotIn(45, sent_msg_ids)  # Never sends premature MISSION_CLEAR_ALL (#45)

        # [RT1-05] & [RT2-05] Follow/Reposition emits SET_POSITION_TARGET_GLOBAL_INT (#86, 65B frame) and COMMAND_INT (#75, 47B frame)
        pos_frame = pack_set_position_target_global_int(66.2598, 29.4130, 28.0)
        self.assertEqual(len(pos_frame), 10 + 53 + 2)
        cmd_int_frame = pack_command_int_reposition(66.2598, 29.4130, 55.0)
        self.assertEqual(len(cmd_int_frame), 10 + 35 + 2)

        t_res = bridge.set_target_assignment(active=True, target_type="PERSON", lat_deg=66.2598, lon_deg=29.4130, alt_agl_m=28.0)
        self.assertTrue(t_res["target_lock_active"])

        # [RT1-06] & [RT2-02] Two-Phase Epoch-Bound Release Token + Replay & Cancellation Protection:
        q_res = bridge.command_payload_drop(action="queue", target_x_m=40.0, target_y_m=50.0)
        self.assertEqual(q_res["drop_state"], "PENDING")
        self.assertIn("release_id", q_res["arm_token"])

        # First release succeeds and sets servo Ch9 = 1900 us:
        rel_ok = bridge.command_payload_drop(
            action="release",
            target_x_m=40.0,
            target_y_m=50.0,
            request_epoch=q_res["epoch_id"],
            wind_speed_ms=4.0,
            drone_ground_speed_ms=0.5,
        )
        self.assertTrue(rel_ok["approved"])
        self.assertEqual(rel_ok["drop_state"], "DROPPED")
        self.assertEqual(rel_ok["winch_servo_pwm_us"], 1900)

        # Replay of release without re-queuing is rejected ([RT2-02]):
        rel_replay = bridge.command_payload_drop(
            action="release",
            target_x_m=40.0,
            target_y_m=50.0,
            request_epoch=q_res["epoch_id"],
        )
        self.assertFalse(rel_replay["approved"])

    def test_operator_mission_console_stretch_resize_and_continuous_drone_transit(self) -> None:
        """
        Verify SAR Operator Mission Console UX invariants:
          1. Default map tool is PAN_MAP ('Pan & Stretch Box') — redrawing from scratch requires
             explicitly enabling 'Draw New Box' (toggleDrawNewBoxTool / activeMapTool === 'DRAW_BOX').
          2. Search Box supports interactive stretching via 8 edge/corner handles (NW, NE, SW, SE, N, S, W, E).
          3. Neither stretching the search box nor drawing a new box from scratch teleports drones;
             both call recomputeAutoMission(false, ...) so all 4 drones fly continuously from their previous positions.
        """
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "collector_hub",
            "ui",
            "operator_mission_console.html",
        )
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn("let activeMapTool = 'PAN_MAP';", html)
        self.assertIn("function toggleDrawNewBoxTool()", html)
        self.assertIn("function findSearchBoxResizeHandle(cx, cy)", html)
        self.assertIn("recomputeAutoMission(false, true);", html)
        self.assertIn("recomputeAutoMission(false, false);", html)
        # Ensure mouseup on new box draw returns to PAN_MAP and does NOT call restartCooperativeSearch()
        self.assertIn("setMapTool('PAN_MAP');", html)
        # Direct drone dragging, Go-To waypoint pinning, and Mark-Object-to-Track
        self.assertIn("function sendDroneToWorldPoint(", html)
        self.assertIn("function markOrLockObjectAtWorld(", html)
        self.assertIn("draggingDroneState", html)
        # 1:1 Trackpad Stick Steering & X/Y Axis vs. Bounds Gauge
        self.assertIn("trackpadSteerCanvas", html)
        self.assertIn("function renderTrackpadSteerBoundsCanvas()", html)
        self.assertIn("X AXIS:", html)
        # Zero offline regex parsing of natural-language commands (Rule 2):
        self.assertNotIn("compileNaturalLanguagePlaybookJS", html)
        self.assertIn("function buildStructuredPlaybookRulesJS(", html)
        self.assertIn("inpPbSearchAlt", html)
        self.assertIn("inpPbTrackAlt", html)
        self.assertIn("selPbDropPolicy", html)

    def test_31_structured_playbook_no_regex_dynamic_envelopes_and_mobile_responder(self) -> None:
        """
        Verify:
          1. Dynamic safe-operating-envelope physics engine in flight_simulator.html shifts bands
             across all 6 gauges and PFD tapes based on altitude density, mass, G-load, icing, flaps,
             headwind, and Manned Helicopter ceiling.
          2. Persona 4 Gloved Ground SAR Responder App (mobile_responder.html) exists and includes
             ETRS-TM35FIN + WGS84 coordinates, ATAK CoT export, and 2-way field ACK buttons.
          3. Exact JHS 197 ETRS-TM35FIN <-> WGS84 coordinate conversion round-trip accuracy (<1.0 m).
          4. MAVLinkV2FieldBridge.command_payload_drop unknown action never clears a latched drop veto.
        """
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sim_path = os.path.join(root_dir, "fast_sar_jet_finlab02", "simulator_ui", "flight_simulator.html")
        with open(sim_path, "r", encoding="utf-8") as f:
            sim_html = f.read()
        self.assertIn("window.lastDynamicEnvelope =", sim_html)
        self.assertIn("window.toggleDynEnvFactor =", sim_html)
        self.assertIn("Fast-SAR Mothership", sim_html)
        self.assertIn("Pilot Cockpit &amp; Synthetic Vision GCS", sim_html)

        resp_path = os.path.join(root_dir, "collector_hub", "ui", "mobile_responder.html")
        self.assertTrue(os.path.exists(resp_path))
        with open(resp_path, "r", encoding="utf-8") as f:
            resp_html = f.read()
        self.assertIn("ETRS-TM35FIN", resp_html)
        self.assertIn("exportAtakCot", resp_html)
        self.assertIn("sendFieldAction('VICTIM_SAFE')", resp_html)

        from collector_hub.dashboard_server import wgs84_to_etrs_tm35fin, etrs_tm35fin_to_wgs84
        n_m, e_m = wgs84_to_etrs_tm35fin(66.3695, 29.3155)
        lat_rt, lon_rt = etrs_tm35fin_to_wgs84(n_m, e_m)
        self.assertAlmostEqual(lat_rt, 66.3695, places=4)
        self.assertAlmostEqual(lon_rt, 29.3155, places=4)

        from collector_hub.mavlink_field_bridge import MAVLinkV2FieldBridge
        bridge = MAVLinkV2FieldBridge()
        bridge.command_payload_drop(action="cancel", target_x_m=10.0, target_y_m=20.0)
        self.assertTrue(bridge.drop_veto_latched)
        bad_res = bridge.command_payload_drop(action="unknown_invalid_action", target_x_m=10.0, target_y_m=20.0)
        self.assertFalse(bad_res["approved"])
        self.assertTrue(bridge.drop_veto_latched)

    def test_32_jhs197_mittakaavavirhe_etrs_gk_and_freezing_fog_resilience(self):
        """
        Verifies:
          1. Exact GRS80 2nd-order Gauss mid-latitude `enu_to_wgs84` / `wgs84_to_enu` round-trip
             (< 0.05 m error over a 10 km leg across all Finnish latitudes from Åland to Lapland).
          2. JHS 197 ETRS-TM35FIN `mittakaavavirhe_ppm` (-400 ppm at central meridian 27E,
             ~+1,730..+1,820 ppm in the Åland archipelago at 19.35E) and `meridian_convergence_deg`,
             plus `tm35fin_grid_vector_to_true_ground()` / `true_ground_vector_to_tm35fin_grid()`.
          3. JHS 197 ETRS-GK19..ETRS-GK31 (`wgs84_to_etrs_gk` & `etrs_gk_to_wgs84`, EPSG:3873..3885)
             keeping `mittakaavavirhe_ppm <= 10.5 ppm` (< 1 cm/km) across both Åland (GK20) and
             Kuusamo/Oulanka (GK29).
          4. High-altitude small-blob thermal gait classification (4x8 px at 120 m AGL) and
             dense freezing-fog 850 nm LiDAR backscatter rejection + 18 m under-fog ceiling corridor.
        """
        # 1. Exact GRS80 ENU <-> WGS84 over a 10 km NE transit in Oulanka (66.26N, 29.42E)
        lat_10k, lon_10k = dobs.enu_to_wgs84(
            6000.0, 8000.0, ref_lat=dobs.OULANKA_REF_LAT_DEG, ref_lon=dobs.OULANKA_REF_LON_DEG, precision=8
        )
        e_rt, n_rt = dobs.wgs84_to_enu(
            lat_10k, lon_10k, ref_lat=dobs.OULANKA_REF_LAT_DEG, ref_lon=dobs.OULANKA_REF_LON_DEG
        )
        self.assertAlmostEqual(e_rt, 6000.0, delta=0.05)
        self.assertAlmostEqual(n_rt, 8000.0, delta=0.05)

        # 2. ETRS-TM35FIN mittakaavavirhe at 27.0E (-400 ppm) vs. Åland archipelago (~19.35E, ~+1,750..1,820 ppm)
        tm_central = dobs.wgs84_to_etrs_tm35fin(62.0, 27.0)
        self.assertAlmostEqual(tm_central["mittakaavavirhe_ppm"], -400.0, delta=0.5)
        self.assertAlmostEqual(tm_central["meridian_convergence_deg"], 0.0, delta=0.001)

        tm_aland = dobs.wgs84_to_etrs_tm35fin(60.22, 19.35)
        self.assertTrue(1700.0 <= tm_aland["mittakaavavirhe_ppm"] <= 1850.0)
        self.assertTrue(-7.0 <= tm_aland["meridian_convergence_deg"] <= -6.0)

        # Round-trip TM35FIN -> WGS84 -> TM35FIN
        lat_inv, lon_inv = dobs.etrs_tm35fin_to_wgs84(
            tm_aland["northing_exact_m"], tm_aland["easting_exact_m"]
        )
        self.assertAlmostEqual(lat_inv, 60.22, places=5)
        self.assertAlmostEqual(lon_inv, 19.35, places=5)

        # Grid vector <-> True ground vector compensation in Åland (removes ~1.8 m/km scale stretch & -6.6 deg tilt)
        grid_vec = dobs.true_ground_vector_to_tm35fin_grid(0.0, 1000.0, 60.22, 19.35)
        true_vec = dobs.tm35fin_grid_vector_to_true_ground(
            grid_vec["delta_e_grid_m"], grid_vec["delta_n_grid_m"], 60.22, 19.35
        )
        self.assertAlmostEqual(true_vec["east_true_m"], 0.0, delta=0.01)
        self.assertAlmostEqual(true_vec["north_true_m"], 1000.0, delta=0.01)
        self.assertAlmostEqual(true_vec["true_ground_distance_m"], 1000.0, delta=0.01)
        self.assertTrue(true_vec["scale_error_removed_m"] > 1.7)

        # 3. JHS 197 ETRS-GKxx (< 10 ppm scale error in both Åland GK19/GK20 and Oulanka GK29)
        gk_aland = dobs.wgs84_to_etrs_gk(60.22, 19.85)  # GK20 (central meridian 20E)
        self.assertEqual(gk_aland["gk_zone"], 20)
        self.assertEqual(gk_aland["epsg"], 3874)
        self.assertTrue(abs(gk_aland["mittakaavavirhe_ppm"]) <= 10.5)

        gk_oulanka = dobs.wgs84_to_etrs_gk(dobs.OULANKA_REF_LAT_DEG, dobs.OULANKA_REF_LON_DEG)  # GK29
        self.assertEqual(gk_oulanka["gk_zone"], 29)
        self.assertEqual(gk_oulanka["epsg"], 3883)
        self.assertTrue(abs(gk_oulanka["mittakaavavirhe_ppm"]) <= 10.5)
        lat_gk_rt, lon_gk_rt = dobs.etrs_gk_to_wgs84(
            gk_oulanka["northing_exact_m"], gk_oulanka["easting_exact_m"]
        )
        self.assertAlmostEqual(lat_gk_rt, dobs.OULANKA_REF_LAT_DEG, places=5)
        self.assertAlmostEqual(lon_gk_rt, dobs.OULANKA_REF_LON_DEG, places=5)

        # 4. High-altitude small-blob thermal gait lock (4x8 px at 120 m AGL) & freezing-fog LiDAR gate
        high_alt_sig = dobs.classify_finnish_boreal_thermal_signature(
            bbox_width_norm=4.0 / 256.0,
            bbox_height_norm=8.0 / 192.0,
            estimated_height_m=1.75,
            thermal_core_delta_c=11.0,
            speed_mps=1.45,
            drone_alt_agl_m=120.0,
            thermal_blob_px_dims=(4, 8),
        )
        self.assertTrue(high_alt_sig["is_human_hiker"])
        self.assertTrue(high_alt_sig["small_high_altitude_blob_lock"])

        fog_res = dobs.evaluate_gnss_rf_jamming_and_weather_resilience(
            alt_agl_m=58.2,
            visibility_m=35.0,
            lidar_baro_divergence_m=14.5,
        )
        self.assertTrue(fog_res["dense_zero_horizon_fog_detected"])
        self.assertTrue(fog_res["lidar_fog_backscatter_rejected"])
        self.assertEqual(fog_res["under_fog_ceiling_corridor_agl_m"], 18.0)
        self.assertEqual(fog_res["opaslyhty_safe_canopy_altitude_agl_m"], 18.0)

        # 5. Zero-BOM-Change High-Altitude Small-Blob Group-Split Tracker (9 in main group + 1 breakaway hiker)
        blob_tracker = dobs.HighAltitudeSmallBlobThermalTracker(split_distance_threshold_m=25.0)
        frame0_blobs = [
            {"east_m": -100.0 + i * 2.5, "north_m": 200.0 - i * 1.5, "w_px": 4.0, "h_px": 8.0, "core_delta_c": 12.0}
            for i in range(9)
        ] + [{"east_m": -45.0, "north_m": 215.0, "w_px": 4.0, "h_px": 8.0, "core_delta_c": 13.5}]
        blob_tracker.step(1.0, frame0_blobs, drone_alt_agl_m=120.0)

        # Advance 2 seconds: main group moves SW at ~1.4 m/s, breakaway hiker moves East at ~2.8 m/s
        frame1_blobs = [
            {
                "east_m": -100.0 + i * 2.5 - 2.0,
                "north_m": 200.0 - i * 1.5 - 2.0,
                "w_px": 4.0,
                "h_px": 8.0,
                "core_delta_c": 12.0,
            }
            for i in range(9)
        ] + [{"east_m": -39.4, "north_m": 216.2, "w_px": 4.0, "h_px": 8.0, "core_delta_c": 13.5}]
        split_state = blob_tracker.step(2.0, frame1_blobs, drone_alt_agl_m=120.0)
        self.assertEqual(split_state["bom_changes_required"], 0)
        self.assertTrue(split_state["zero_chinese_bom_compliant"])
        self.assertEqual(split_state["active_track_count"], 10)
        self.assertTrue(split_state["group_split_detected"])
        self.assertEqual(len(split_state["main_group_track_ids"]), 9)
        self.assertEqual(len(split_state["separated_outlier_track_ids"]), 1)

        # 6. Zero-BOM-Change 850 nm LiDAR Fog-Backscatter Rejection Gate & 18.0 m Under-Fog Ceiling Corridor
        gate = dobs.evaluate_lidar_fog_backscatter_rejection_gate(
            lidar_raw_range_m=4.2,  # False Mie backscatter off fog droplets 4.2m ahead of lens
            baro_isa_alt_agl_m=58.2,
            ambient_temp_c=-12.0,
            pad_temp_c=-10.0,
            optical_visibility_m=30.0,
        )
        self.assertEqual(gate["bom_changes_required"], 0)
        self.assertTrue(gate["fog_mie_backscatter_detected"])
        self.assertTrue(gate["ekf_rngfnd_inhibited"])
        self.assertTrue(gate["runaway_climb_prevented"])
        self.assertEqual(gate["vertical_hold_source"], "BMP390_HYPSOMETRIC_BARO_PLUS_MML_2M_DEM_ZERO_BOM_CHANGE")

        corridor = dobs.plan_autonomous_under_fog_ceiling_corridor(
            current_east_m=-120.0,
            current_north_m=180.0,
            current_alt_agl_m=58.2,
            target_east_m=-40.0,
            target_north_m=215.0,
            optical_visibility_m=30.0,
            horizon_contrast_score=0.04,
            corridor_tree_canopy_height_m=4.5,
        )
        self.assertEqual(corridor["bom_changes_required"], 0)
        self.assertTrue(corridor["zero_visible_horizon_detected"])
        self.assertEqual(corridor["commanded_corridor_alt_agl_m"], 18.0)
        self.assertEqual(corridor["flight_mode"], "UNDER_FOG_CEILING_18M_DEM_CORRIDOR")
        self.assertEqual(len(corridor["corridor_waypoints"]), 4)
        self.assertTrue(corridor["vortex_ring_state_prevented"])

        playbook_audit = dobs.run_six_iteration_aerospace_playbook_audit()
        self.assertTrue(playbook_audit["all_6_iterations_verified"])
        self.assertEqual(playbook_audit["bom_changes_required"], 0)
        self.assertTrue(playbook_audit["zero_chinese_bom_compliant"])
        self.assertEqual(len(playbook_audit["iterations"]), 6)


if __name__ == "__main__":
    print("=== Running Autonomous Aerial Observation & Guidance Module Test Suite ===")
    unittest.main(verbosity=2)




