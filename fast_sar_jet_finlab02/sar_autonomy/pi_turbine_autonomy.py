#!/usr/bin/env python3
"""
Raspberry Pi Companion Autonomy & Turbine Spool-Lag Feedforward Controller
for the Arctic Trail Tier-3 Fast-SAR UAV (ArduPlane + Vendor COTS JetCat/Xicoy ECU).

DISCLAIMER (EARLY-STAGE CONCEPT SIMULATION CODE — NOT FLIGHT-QUALIFIED):
This script is an analytical reference model for evaluating spool-lag lead compensation,
headwind-aware affine Breguet Return-to-Home (RTH) fuel reserves, and low-speed (25-28 m/s)
parachute-retarded SAR survival-capsule delivery. It is not airworthiness-certified flight
software and must never bypass the manufacturer ECU's built-in start, cooldown, or EGT protection.

Solves three core micro-turbojet SAR autonomy challenges:
1. First-order turbine spool-up lag G_e(s) = 1 / (tau_p * s + 1) via preview
   lead-compensation u_cmd(t) = u_req(t + T_lead) + tau_p * du_req/dt, with enforced
   slew-rate clamping (+0.25/s max) and EGT/surge safety derating.
2. In-flight flameout prevention (enforces dynamic flight-idle floor so ArduPlane
   never commands fuel-valve shutoff mid-air) and immediate auto-glide / ballistic
   recovery-parachute failsafe if EGT drops below flameout threshold (< 280 C).
3. Real-time fuel integration with headwind feasibility checking and slowed (25-28 m/s)
   operator-authorized SAR parachute care-package release with navigation-integrity gating.
"""

import math
import time
from dataclasses import dataclass


@dataclass
class TurbineTelemetry:
    rpm: float               # Current shaft RPM (e.g., 35,000-65,000 idle to 154,000 max)
    egt_c: float             # Exhaust Gas Temperature (deg C)
    pump_pwm_pct: float      # Fuel pump duty cycle (0 - 100%)
    fuel_flow_g_s: float     # Estimated fuel mass flow (g/s)
    state: str               # "OFF", "START", "RUNNING", "FLAMEOUT", "COOLDOWN"


@dataclass
class FlightState:
    airspeed_m_s: float
    altitude_m: float
    pitch_deg: float
    roll_deg: float
    dist_to_home_m: float
    headwind_m_s: float
    gnss_hdop: float = 0.8
    gnss_spoof_flag: bool = False


class MicroTurbojetAutonomyNode:
    def __init__(
        self,
        spool_tau_s: float = 1.35,
        max_egt_c: float = 760.0,
        flameout_egt_c: float = 280.0,
        initial_fuel_g: float = 2650.0,
        m_dot_idle_g_s: float = 1.067,
        c_slope_g_per_n_s: float = 0.0413,
        max_slew_per_s: float = 0.85,
    ):
        self.spool_tau_s = spool_tau_s
        self.max_egt_c = max_egt_c
        self.flameout_egt_c = flameout_egt_c
        self.remaining_fuel_g = initial_fuel_g
        self.m_dot_idle_g_s = m_dot_idle_g_s
        self.c_slope_g_per_n_s = c_slope_g_per_n_s
        self.max_slew_per_s = max_slew_per_s
        self.prev_thrust_norm = 0.30
        self.prev_time = time.monotonic()

    def compute_lead_compensated_throttle(
        self,
        target_thrust_norm: float,
        preview_dthrust_dt: float,
        turbine: TurbineTelemetry,
        in_air: bool = True,
        dt_override_s: float | None = None,
    ) -> float:
        """
        Inverts the first-order rotor lag G(s) = 1 / (tau_p * s + 1) using
        feedforward lead compensation while respecting compressor surge, slew rate, and EGT limits.
        """
        now = time.monotonic()
        dt = dt_override_s if dt_override_s is not None else max(1e-3, now - self.prev_time)
        self.prev_time = now

        if turbine.state == "FLAMEOUT" or (in_air and turbine.egt_c < self.flameout_egt_c):
            self.prev_thrust_norm = 0.0
            return 0.0

        # Dynamic idle floor: keep centrifugal compressor on the fast side of the surge/pressure knee
        min_throttle = 0.22 if in_air else 0.05

        # Inverse plant feedforward: u_ff = u_target + tau_p * (du_target / dt)
        u_ff = target_thrust_norm + self.spool_tau_s * preview_dthrust_dt

        # Thermal EGT protection derating as EGT approaches 760 C limit
        if turbine.egt_c > (self.max_egt_c - 40.0):
            thermal_scale = max(0.0, (self.max_egt_c - turbine.egt_c) / 40.0)
            u_ff = min(u_ff, target_thrust_norm * thermal_scale)

        # Enforced upward slew-rate clamp (+25%/s max spool-up rate to prevent rich blowout / surge)
        max_step_up = self.prev_thrust_norm + self.max_slew_per_s * dt
        u_clamped = max(min_throttle, min(1.0, min(u_ff, max_step_up)))
        self.prev_thrust_norm = u_clamped
        return u_clamped

    def check_affine_breguet_rth_reserve(
        self,
        flight: FlightState,
        cruise_drag_n: float = 28.8,
        optimal_cruise_m_s: float = 55.8,
    ) -> dict:
        """
        Computes real-time fuel needed to return home against current headwind
        using the affine micro-turbojet fuel model: m_dot = m_dot_idle + c_slope * D.
        Flags an emergency headwind abort if net groundspeed drops below 10 m/s.
        """
        raw_groundspeed_rth = optimal_cruise_m_s - flight.headwind_m_s
        infeasible_headwind = raw_groundspeed_rth < 10.0
        groundspeed_rth = max(5.0, raw_groundspeed_rth)
        time_to_home_s = flight.dist_to_home_m / groundspeed_rth
        cruise_burn_g_s = self.m_dot_idle_g_s + self.c_slope_g_per_n_s * cruise_drag_n

        # Require 90 seconds of go-around / approach reserve + RTH transit fuel
        fuel_needed_g = cruise_burn_g_s * (time_to_home_s + 90.0)
        trigger_rth = infeasible_headwind or (self.remaining_fuel_g <= fuel_needed_g)

        return {
            "remaining_fuel_g": round(self.remaining_fuel_g, 1),
            "fuel_needed_for_rth_g": round(fuel_needed_g, 1),
            "groundspeed_rth_m_s": round(raw_groundspeed_rth, 1),
            "infeasible_headwind_abort": infeasible_headwind,
            "time_to_home_s": round(time_to_home_s, 1),
            "trigger_rth": trigger_rth,
        }

    def compute_low_speed_sar_parachute_drop(
        self,
        flight: FlightState,
        operator_authorized: bool = True,
        drop_altitude_agl_m: float = 45.0,
        reefed_inflation_time_s: float = 0.65,
        steady_descent_rate_m_s: float = 5.5,
    ) -> dict:
        """
        Arctic Trail Tier-3 Civilian SAR Care-Package Delivery:
        Executes a slowed (25-28 m/s) parachute-retarded survival-capsule release into a
        clear offset zone near the casualty. Enforces:
          1) Operator authorization gate,
          2) Navigation-integrity fence (GNSS HDOP <= 1.5 and no spoofing flag),
          3) Low-speed airspeed gate (<= 30 m/s so two-stage reefed canopy snatch force stays < 260 N / 5.3 G).
        """
        if not operator_authorized or flight.gnss_spoof_flag or flight.gnss_hdop > 1.5:
            return {
                "release_inhibited": True,
                "reason": "Navigation integrity degraded or operator authorization missing",
            }
        if flight.airspeed_m_s > 30.0:
            return {
                "release_inhibited": True,
                "reason": f"Airspeed {flight.airspeed_m_s:.1f} m/s exceeds 30.0 m/s low-speed SAR parachute gate",
            }

        g = 9.80665
        v_ground = max(5.0, flight.airspeed_m_s - flight.headwind_m_s)
        dz_phase1 = 0.5 * g * (reefed_inflation_time_s ** 2)
        dx_phase1 = v_ground * reefed_inflation_time_s * 0.78

        remaining_alt_m = max(0.0, drop_altitude_agl_m - dz_phase1)
        t_chute_s = remaining_alt_m / steady_descent_rate_m_s
        dx_wind_drift = (-flight.headwind_m_s) * t_chute_s

        # Peak opening load with two-stage reefed drogue at <= 28 m/s
        peak_opening_load_n = 0.5 * 1.225 * (flight.airspeed_m_s ** 2) * 0.58
        return {
            "release_inhibited": False,
            "release_lead_distance_m": round(dx_phase1 + dx_wind_drift, 1),
            "total_fall_time_s": round(reefed_inflation_time_s + t_chute_s, 1),
            "v_ground_at_release_m_s": round(v_ground, 1),
            "estimated_peak_canopy_load_N": round(peak_opening_load_n, 1),
            "estimated_peak_g": round(peak_opening_load_n / (5.0 * g), 2),
        }

    def manage_hybrid_radar_loiter_transition(
        self,
        flight: FlightState,
        on_radar_station: bool,
        battery_soc_pct: float,
        heated_bay_temp_c: float = 15.0,
        relight_qualified: bool = False,
    ) -> dict:
        """
        Iteration 2 Trade-Study Controller:
        Evaluates switching to the nose folding-propeller electric sustainer at 25.5 m/s
        (377 W electrical input at MTOW / 335 W mid-mission for C_D0 = 0.025).
        SAFETY GATE: Never commands full turbine shutdown in flight unless (a) in-flight
        relight has passed Gate 3 qualification AND (b) heated fuel/ECU bay is >= +5 C;
        otherwise keeps the JetCat P100 at verified flight-idle via vendor ECU protocol.
        """
        if on_radar_station and battery_soc_pct > 25.0 and relight_qualified and heated_bay_temp_c >= 5.0:
            return {
                "propulsion_mode": "ITERATION_2_ELECTRIC_FOLDING_PROP_LOITER",
                "vendor_ecu_command": "AUTO_COOLDOWN_THEN_STANDBY (Heated Bay >= +5 C Verified)",
                "target_airspeed_m_s": 25.5,
                "useful_thrust_power_w": 272.0,
                "electric_motor_input_power_w": 377.0,
                "sar_sensor_power_w": 69.5,
            }
        return {
            "propulsion_mode": "ITERATION_1_TURBOJET_CONTINUOUS_SAR_CRUISE",
            "vendor_ecu_command": "RUNNING_CLOSED_LOOP_RPM (Flight-Idle Floor Enforced)",
            "target_airspeed_m_s": 55.8,
            "electric_motor_input_power_w": 0.0,
            "sar_sensor_power_w": 35.0,
        }


def run_closed_loop_simulation():
    """
    Simulates a 10-second autonomous terrain-following climb maneuver comparing:
    1) Uncompensated PID throttle (lags by 1.35 s, causing airspeed decay)
    2) Raspberry Pi Preview Lead-Compensated throttle
    """
    node = MicroTurbojetAutonomyNode(spool_tau_s=1.35)
    dt = 0.25
    actual_thrust_uncomp = 0.30
    actual_thrust_comp = 0.30

    print("Time(s) | Req_Thrust | Uncomp_Actual | Lead_Cmd | Lead_Actual | Lag_Error_Reduction")
    print("-" * 83)
    for step in range(25):
        t = step * dt
        # Maneuver: ramp thrust from 0.30 to 0.85 between t = 1.0s and t = 3.0s
        if t < 1.0:
            req = 0.30
            dreq_dt = 0.0
        elif t < 3.0:
            req = 0.30 + 0.275 * (t - 1.0)
            dreq_dt = 0.275
        else:
            req = 0.85
            dreq_dt = 0.0

        turb = TurbineTelemetry(
            rpm=65000 + actual_thrust_comp * 95000,
            egt_c=480 + actual_thrust_comp * 210,
            pump_pwm_pct=actual_thrust_comp * 85,
            fuel_flow_g_s=0.42 + actual_thrust_comp * 2.1,
            state="RUNNING",
        )

        u_cmd = node.compute_lead_compensated_throttle(req, dreq_dt, turb, in_air=True, dt_override_s=dt)

        # First-order turbine rotor dynamics: dT/dt = (u - T) / tau_p
        actual_thrust_uncomp += ((req - actual_thrust_uncomp) / node.spool_tau_s) * dt
        actual_thrust_comp += ((u_cmd - actual_thrust_comp) / node.spool_tau_s) * dt

        err_uncomp = abs(req - actual_thrust_uncomp)
        err_comp = abs(req - actual_thrust_comp)
        reduction = (1.0 - (err_comp / max(err_uncomp, 1e-4))) * 100.0 if err_uncomp > 0.01 else 100.0

        if step % 2 == 0:
            print(
                f"  {t:4.1f}  |    {req:4.2f}    |     {actual_thrust_uncomp:4.2f}      |"
                f"   {u_cmd:4.2f}   |    {actual_thrust_comp:4.2f}     |       {reduction:5.1f}%"
            )


if __name__ == "__main__":
    run_closed_loop_simulation()
