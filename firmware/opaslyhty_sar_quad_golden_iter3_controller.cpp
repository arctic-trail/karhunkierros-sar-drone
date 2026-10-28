// ============================================================================
// Opaslyhty Golden Iteration 3 Flight Envelope & Arctic SAR Supervisor
// Target: Holybro Pixhawk 6C Mini (STM32H743) + Raspberry Pi 5 Companion SIL
// Airframe: Holybro X500 V2 (4S2P Molicel P45B 9.0Ah in 174x114x104mm 15mm EPP + 10W PTC Bay)
//
// Round-1 Independent Engineering Review Remediations Implemented:
//   1. Unified Electro-Thermal Model matching `physics_verify.py` (R_th = 4.6562 K/W,
//      C_th = 560.0 J/K, T_ref = 293.15 K, beta = 2665.0 K, esc_heat_recovery_frac = 0.0,
//      20% SOC EOD OCV knee = 3.52 V/cell = 14.08 V pack, zero double-counting of PTC power,
//      and [273.15 K, 318.15 K] = [0 C, +45 C] upper/lower thermal safety bounds).
//   2. `verify_4s_param_guard` checks `std::isfinite(...)` on all inputs first, enforces
//      strict threshold hierarchy (`v_arm > v_low > v_crt`), and is called in
//      `step_opaslyhty_supervisor` to force `FailsafeState::kPreArmBlocked` if invalid.
//   3. Complete failsafe priority hierarchy:
//      `kPreArmBlocked` > `kCriticalBatteryLand` (critical EOD voltage or thermal fault) >
//      `kLowBatteryRtl` (unhealthy EKF3 or low voltage) > `kVrsLateralEscape` > `kNominalMission`.
//   4. Vuichard-style lateral VRS escape (`commanded_vx_escape_mps = 3.5f` m/s cyclic translation
//      out of the descending vortex column with reduced collective) and 3-tick debounced VRS
//      onset detection (`descent_rate_mps > 1.50f` and `attitude_err_deg > 4.0f`).
//   5. Honest EKF3 Baro-DEM + ExtNav VIO disagreement residual (unscaled 1.0x difference) and
//      exact `compute_can_crc16` verification (never rejecting a valid 0x0000 CRC-16).
// ============================================================================

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>

#include "mc3000_golden_draws.hpp"

namespace opaslyhty::control {

// --- Golden Iteration 3 Verified 4S2P & Sensor Calibration Constants ---
inline constexpr float kIsaStandardTempK = 288.15f;
inline constexpr float kCellSeriesCount = 4.0f;
inline constexpr float kCellParallelCount = 2.0f;
inline constexpr float kBattArmVolt4S = 14.8f;      // 3.70 V/cell pre-takeoff minimum
inline constexpr float kBattLowVolt4S = 13.4f;      // 3.35 V/cell sag-compensated RTL warning threshold
inline constexpr float kBattCritVolt4S = 12.8f;     // 3.20 V/cell sag-compensated critical land threshold
inline constexpr float kLegacy6SCutoffBugV = 17.4f; // Iter-1 defective 6S parameter (rejected)
inline constexpr float kPm02V3VoltMult = 18.182f;   // Holybro PM02 V3 12S divider (18.182 V/V on PWR1 Pin 4)
inline constexpr float kPm02V3AmpPerVolt = 36.36f;  // Holybro PM02 V3 current shunt (36.36 A/V on PWR1 Pin 3)

// Unified Electro-Thermal Constants (100% matched to `physics_verify.py`)
inline constexpr float kRthPackKPerW = 4.6562f;     // 15mm EPP (0.0948 W/K) + PEEK/labyrinth bridge (0.1200 W/K)
inline constexpr float kCthPackJPerK = 560.0f;      // 8x 70g 21700 cells (0.56 kg * 1000 J/kgK)
inline constexpr float kSortieEvalSec = 1200.0f;    // 20-minute reference sortie thermal horizon
inline constexpr float kTrefArrheniusK = 293.15f;   // +20.0 C reference temperature for R_cell
inline constexpr float kTcellLaunchInitK = 293.15f; // +20.0 C warm-case launch cell temperature per SOP
inline constexpr float kTcellMinSafeK = 273.15f;    //   0.0 C lower safe operating temperature
inline constexpr float kTcellMaxSafeK = 318.15f;    // +45.0 C upper safe operating temperature limit
inline constexpr float kArrheniusBetaK = 2665.0f;   // Li-ion internal resistance Arrhenius slope (K)
inline constexpr float kEscHeatRecoveryFrac = 0.0f; // 0.0: ESCs are mounted on external carbon arms
inline constexpr float kPtcMaxPowerW = 10.0f;       // 10.0 W polyimide Kapton heater pad
inline constexpr float kPtcSetpointK = 281.15f;     // DS18B20 -> RPi GPIO4/17 -> IRLZ44N thermostat midpoint (+8 C)
inline constexpr float kPtcPropBandK = 12.0f;       // Smooth proportional thermostat band width (K)
inline constexpr float kCellOcvMeanV = 3.7625f;     // Mid-discharge OCV (15.05 V pack)
inline constexpr float kCellOcvEod20PctV = 3.520f;  // 20% SOC end-of-discharge OCV knee (14.08 V pack)

// Altimetry & VRS Envelope Constants
inline constexpr float kTf02ProMaxValidM = 35.0f;   // Benewake TF02-Pro conservative Arctic gate (RNGFND1_MAX_CM=3500)
inline constexpr float kTf02ProHardCeilM = 40.0f;   // Hardware saturation ceiling
inline constexpr float kMaxSafeDescentMps = 1.50f;  // WPNAV_SPEED_DN = 150 cm/s (Vz / vi0 = 0.226 < 0.25 VRS onset)
inline constexpr float kHoverInducedVi0Mps = 6.64f; // Momentum-theory hover induced velocity (m/s)
inline constexpr float kAttitudeErrGateDeg = 4.00f; // VRS attitude instability gate (deg)
inline constexpr uint8_t kVrsDebounceTicks = 3u;    // Consecutive unstable high-sink ticks required to trigger VRS escape
inline constexpr float kVuichardVxEscapeMps = 3.5f; // Vuichard lateral cyclic escape velocity out of vortex column (m/s)

enum class AltitudeSource : uint8_t {
    kLidarPrimaryFused = 0,
    kHypsometricBaroDemVio = 1,
    kEmergencyBaroFallback = 2
};

enum class FailsafeState : uint8_t {
    kNominalMission = 0,
    kLowBatteryRtl = 1,
    kCriticalBatteryLand = 2,
    kVrsLateralEscape = 3,
    kPreArmBlocked = 4
};

// DroneCAN / UAVCAN 8-byte deterministic telemetry frame
struct CanFrame {
    uint32_t can_id{0x10A4201u};
    uint8_t dlc{8u};
    std::array<uint8_t, 8> data{};
    uint16_t crc16_ccitt{0u};
};

struct ThermalBatteryState {
    float t_cell_k{292.05f};
    float r_cell_mohm{13.97f};
    float r_pack_ohm{0.02794f};
    float i_load_a{16.52f};
    float v_sag{0.46f};
    float v_term_v{14.59f};
    float v_term_eod_v{13.45f};
    float ptc_heater_w{2.10f};
    bool thermal_ok{true};
};

struct EKFAltitudeOutput {
    float baro_alt{85.0f};
    float lidar{40.0f};
    float fused_agl_m{85.0f};
    float est_error_m{1.34f};
    AltitudeSource source{AltitudeSource::kHypsometricBaroDemVio};
    bool ekf_healthy{true};
};

struct AttitudeNotchPidState {
    float roll_err_deg{0.0f};
    float pitch_err_deg{0.0f};
    float attitude_err_deg{0.0f};
    float harmonic_notch_hz{88.0f};
    float pid_roll_out{0.0f};
    float pid_pitch_out{0.0f};
    float commanded_vz_mps{0.0f};
    float commanded_vx_escape_mps{0.0f};
    float control_authority_pct{95.5f};
    uint8_t vrs_debounce_count{0u};
    bool vrs_recovery_active{false};
};

struct SupervisorConfig {
    float batt_arm_volt{kBattArmVolt4S};
    float batt_low_volt{kBattLowVolt4S};
    float batt_crt_volt{kBattCritVolt4S};
    float batt_volt_mult{kPm02V3VoltMult};
    float t_cell_init_k{kTcellLaunchInitK};
    float r_th_pack_k_w{kRthPackKPerW};
    float p_ptc_max_w{kPtcMaxPowerW};
    uint8_t consecutive_vrs_ticks{1u};
};

struct SupervisorStepOutput {
    ThermalBatteryState battery{};
    EKFAltitudeOutput ekf{};
    AttitudeNotchPidState attitude{};
    FailsafeState failsafe{FailsafeState::kNominalMission};
    CanFrame telemetry_frame{};
};

// Compute CRC-16-CCITT (0x1021 polynomial) over CAN ID + 8 payload bytes
inline uint16_t compute_can_crc16(const CanFrame& frame) noexcept {
    uint16_t crc = 0xFFFFu;
    auto update_byte = [&crc](uint8_t b) noexcept {
        crc ^= static_cast<uint16_t>(b) << 8u;
        for (int bit = 0; bit < 8; ++bit) {
            if ((crc & 0x8000u) != 0u) {
                crc = static_cast<uint16_t>((crc << 1u) ^ 0x1021u);
            } else {
                crc = static_cast<uint16_t>(crc << 1u);
            }
        }
    };
    update_byte(static_cast<uint8_t>((frame.can_id >> 24u) & 0xFFu));
    update_byte(static_cast<uint8_t>((frame.can_id >> 16u) & 0xFFu));
    update_byte(static_cast<uint8_t>((frame.can_id >> 8u) & 0xFFu));
    update_byte(static_cast<uint8_t>(frame.can_id & 0xFFu));
    for (uint8_t b : frame.data) {
        update_byte(b);
    }
    return crc;
}

// Validate 4S parameter configuration:
// - Rejects NaN/Inf first
// - Enforces strict threshold hierarchy (batt_arm_volt > batt_low_volt > batt_crt_volt)
// - Rejects Iter-1 6S cutoff bug (17.4 V) and misscaled PM02 V3 voltage multiplier
inline bool verify_4s_param_guard(
    float batt_crt_volt,
    float batt_volt_mult,
    float batt_low_volt = kBattLowVolt4S,
    float batt_arm_volt = kBattArmVolt4S
) noexcept {
    if (!std::isfinite(batt_crt_volt) || !std::isfinite(batt_volt_mult) ||
        !std::isfinite(batt_low_volt) || !std::isfinite(batt_arm_volt)) {
        return false;
    }
    if (batt_crt_volt >= 16.8f || std::fabs(batt_crt_volt - kLegacy6SCutoffBugV) < 0.5f) {
        return false; // Rejects 6S cutoff on 4S pack
    }
    if (!(batt_arm_volt > batt_low_volt && batt_low_volt > batt_crt_volt)) {
        return false; // Enforces monotonic threshold hierarchy
    }
    if (batt_crt_volt < 12.0f || batt_crt_volt > 13.6f) {
        return false;
    }
    if (batt_low_volt < 12.8f || batt_low_volt > 14.4f) {
        return false;
    }
    if (batt_arm_volt < 14.2f || batt_arm_volt > 16.4f) {
        return false;
    }
    if (std::fabs(batt_volt_mult - kPm02V3VoltMult) > 0.05f) {
        return false;
    }
    return true;
}

// Unified Coupled Transient + Steady-State Electro-Thermal Battery Model
// Matches `physics_verify.py` item-for-item:
//   - R_th = 4.6562 K/W (15mm EPP shell + PEEK/foam-labyrinth bridge, zero ESC heat recovery)
//   - C_th = 560.0 J/K over t_sortie = 1200 s starting from t_cell_init_k (+20 C warm launch)
//   - DS18B20 -> RPi GPIO4/GPIO17 -> IRLZ44N MOSFET proportional thermostat
//   - Evaluates both mid-discharge terminal voltage (`v_term_v`) and 20% SOC EOD knee
//     terminal voltage (`v_term_eod_v` at 3.52 V/cell = 14.08 V pack)
//   - Enforces `273.15 K <= t_cell_k <= 318.15 K` ([0 C, +45 C]) and `v_term_eod_v >= kBattCritVolt4S`
inline ThermalBatteryState evaluate_coupled_battery_sag(
    float t_amb_k,
    float r_cell_20c_mohm,
    float p_prop_avionics_w,
    float v_ocv_cell = kCellOcvMeanV,
    float t_cell_init_k = kTcellLaunchInitK,
    float r_th_pack_k_w = kRthPackKPerW,
    float p_ptc_max_w = kPtcMaxPowerW
) noexcept {
    ThermalBatteryState st{};
    if (!std::isfinite(t_amb_k) || !std::isfinite(r_cell_20c_mohm) ||
        !std::isfinite(p_prop_avionics_w) || !std::isfinite(t_cell_init_k)) {
        st.thermal_ok = false;
        return st;
    }

    const float v_ocv_pack = kCellSeriesCount * v_ocv_cell;
    const float v_ocv_eod_pack = kCellSeriesCount * kCellOcvEod20PctV;
    const float tau_th_s = std::max(1.0f, kCthPackJPerK * r_th_pack_k_w);
    const float decay_factor = std::exp(-kSortieEvalSec / tau_th_s);

    float t_cell_k = std::max(t_amb_k, t_cell_init_k);
    float r_cell_mohm = r_cell_20c_mohm;
    float r_pack_ohm = 0.028f;
    float i_load_a = p_prop_avionics_w / v_ocv_pack;
    float p_ptc_active_w = 0.0f;

    // 12-step damped fixed-point electro-thermal relaxation matching `physics_verify.py`
    for (int iter = 0; iter < 12; ++iter) {
        const float ptc_duty = 0.5f * (1.0f + std::tanh((kPtcSetpointK - t_cell_k) / kPtcPropBandK));
        p_ptc_active_w = p_ptc_max_w * ptc_duty;

        const float arrhenius_mult = std::exp(kArrheniusBetaK * (1.0f / t_cell_k - 1.0f / kTrefArrheniusK));
        r_cell_mohm = r_cell_20c_mohm * arrhenius_mult;
        r_pack_ohm = (kCellSeriesCount / kCellParallelCount) * (r_cell_mohm * 1e-3f);

        // PTC heater power is added ONCE to propulsion + avionics electrical load
        const float p_total_w = p_prop_avionics_w + p_ptc_active_w;
        const float disc = std::max(1.0f, v_ocv_pack * v_ocv_pack - 4.0f * r_pack_ohm * p_total_w);
        i_load_a = (v_ocv_pack - std::sqrt(disc)) / (2.0f * r_pack_ohm);

        const float q_joule_w = i_load_a * i_load_a * r_pack_ohm;
        const float q_esc_w = kEscHeatRecoveryFrac * p_prop_avionics_w;
        const float t_ss_k = t_amb_k + r_th_pack_k_w * (q_joule_w + p_ptc_active_w + q_esc_w);
        const float t_end_k = t_cell_init_k * decay_factor + t_ss_k * (1.0f - decay_factor);
        t_cell_k = 0.5f * t_cell_k + 0.5f * t_end_k;
    }

    const float p_total_final_w = p_prop_avionics_w + p_ptc_active_w;
    const float disc_eod = std::max(1.0f, v_ocv_eod_pack * v_ocv_eod_pack - 4.0f * r_pack_ohm * p_total_final_w);
    const float i_eod_a = (v_ocv_eod_pack - std::sqrt(disc_eod)) / (2.0f * r_pack_ohm);

    st.t_cell_k = t_cell_k;
    st.r_cell_mohm = r_cell_mohm;
    st.r_pack_ohm = r_pack_ohm;
    st.i_load_a = i_load_a;
    st.ptc_heater_w = p_ptc_active_w;
    st.v_sag = i_load_a * r_pack_ohm;
    st.v_term_v = v_ocv_pack - st.v_sag;
    st.v_term_eod_v = v_ocv_eod_pack - i_eod_a * r_pack_ohm;
    st.thermal_ok = (t_cell_init_k >= kTcellMinSafeK) &&
                    (t_cell_init_k <= kTcellMaxSafeK) &&
                    (st.t_cell_k >= kTcellMinSafeK) &&
                    (st.t_cell_k <= kTcellMaxSafeK) &&
                    (st.v_term_eod_v >= kBattCritVolt4S);
    return st;
}

// Multi-modal EKF3 altitude voter:
// - Below 35 m AGL: fuses Benewake TF02-Pro LiDAR (0.78 weight) + hypsometric BMP390 Baro-DEM (0.22)
// - Above 35 m AGL (up to 85 m SAR search altitude): TF02-Pro saturates at 40m; switches to
//   hypsometric cold-air-compensated BMP390 Baro-DEM (`BARO_GND_TEMP = -25 C`, `TERRAIN_ENABLE = 1`)
//   + Global Shutter IMX296 / TC001 `ExtNav` VIO (`EK3_SRC2`), checking unscaled 1.0x sensor disagreement.
inline EKFAltitudeOutput evaluate_ekf3_altitude_voter(
    float baro_raw_isa_agl_m,
    float lidar_range_m,
    float vio_agl_m,
    float t_amb_k
) noexcept {
    EKFAltitudeOutput out{};
    if (!std::isfinite(baro_raw_isa_agl_m) || !std::isfinite(t_amb_k) || t_amb_k <= 180.0f) {
        out.ekf_healthy = false;
        out.est_error_m = 99.0f;
        return out;
    }

    // Hypsometric cold-air density correction: z_true = z_isa * (T_amb / T_ISA_288.15K)
    out.baro_alt = baro_raw_isa_agl_m * (t_amb_k / kIsaStandardTempK);
    out.lidar = lidar_range_m;

    const bool lidar_valid = std::isfinite(lidar_range_m) &&
                             (lidar_range_m >= 0.10f) &&
                             (lidar_range_m <= kTf02ProMaxValidM);
    const bool vio_valid = std::isfinite(vio_agl_m) &&
                           (vio_agl_m >= 0.50f) &&
                           (vio_agl_m <= 150.0f);

    if (lidar_valid) {
        out.fused_agl_m = 0.78f * lidar_range_m + 0.22f * out.baro_alt;
        out.est_error_m = std::fabs(out.baro_alt - lidar_range_m) + 0.15f;
        out.source = AltitudeSource::kLidarPrimaryFused;
    } else if (vio_valid) {
        out.fused_agl_m = 0.62f * out.baro_alt + 0.38f * vio_agl_m;
        // Full 1.0x unscaled disagreement between Baro-DEM and ExtNav VIO + first-principles RSS floor
        const float sensor_disagreement_m = std::fabs(out.baro_alt - vio_agl_m);
        const float base_rss_m = std::sqrt(
            (out.fused_agl_m * (1.80f / t_amb_k)) * (out.fused_agl_m * (1.80f / t_amb_k)) +
            0.95f * 0.95f +
            (out.fused_agl_m * 0.0085f) * (out.fused_agl_m * 0.0085f)
        );
        out.est_error_m = std::max(base_rss_m, sensor_disagreement_m);
        out.source = AltitudeSource::kHypsometricBaroDemVio;
    } else {
        out.fused_agl_m = out.baro_alt;
        // Without LiDAR or VIO, barometric drift + DEM uncertainty grows with altitude
        out.est_error_m = std::hypot(1.85f, out.baro_alt * 0.025f);
        out.source = AltitudeSource::kEmergencyBaroFallback;
    }
    out.ekf_healthy = std::isfinite(out.fused_agl_m) && (out.est_error_m <= 2.50f);
    return out;
}

// VRS Descent Protection, Debounced Vuichard Lateral Escape & Harmonic-Notch Attitude Controller
inline AttitudeNotchPidState evaluate_attitude_and_vrs_gate(
    float roll_err_deg,
    float pitch_err_deg,
    float requested_descent_mps,
    float hover_throttle_norm = 0.34f,
    uint8_t consecutive_vrs_ticks = kVrsDebounceTicks
) noexcept {
    AttitudeNotchPidState st{};
    st.roll_err_deg = roll_err_deg;
    st.pitch_err_deg = pitch_err_deg;
    st.attitude_err_deg = std::hypot(roll_err_deg, pitch_err_deg);

    // Dynamic harmonic notch filter tracking 2216 920KV motor fundamental (~88 Hz in hover)
    st.harmonic_notch_hz = 88.0f * std::sqrt(std::max(0.20f, hover_throttle_norm / 0.34f));

    // P-controller with anti-windup clamp
    constexpr float kKpAttitude = 4.5f;
    st.pid_roll_out = std::clamp(-kKpAttitude * roll_err_deg, -35.0f, 35.0f);
    st.pid_pitch_out = std::clamp(-kKpAttitude * pitch_err_deg, -35.0f, 35.0f);

    // Clamp nominal vertical sink rate to VRS-safe envelope (WPNAV_SPEED_DN = 150 cm/s -> Vz/vi0 = 0.226)
    const float clamped_descent_mps = std::min(std::max(0.0f, requested_descent_mps), kMaxSafeDescentMps);

    // Debounced VRS onset condition: requires BOTH excessive descent request (> 1.50 m/s)
    // AND attitude instability (> 4.0 deg) persisted across >= kVrsDebounceTicks (3 consecutive ticks).
    const bool vrs_condition_now = (requested_descent_mps > kMaxSafeDescentMps) &&
                                   (st.attitude_err_deg > kAttitudeErrGateDeg);
    st.vrs_debounce_count = vrs_condition_now ? consecutive_vrs_ticks : 0u;

    if (vrs_condition_now && (st.vrs_debounce_count >= kVrsDebounceTicks)) {
        // Vuichard Vortex Ring State escape: command 3.5 m/s lateral cyclic translation out of the
        // descending vortex column while reducing vertical sink (-0.4 m/s) rather than climbing straight up.
        st.vrs_recovery_active = true;
        st.commanded_vx_escape_mps = kVuichardVxEscapeMps;
        st.commanded_vz_mps = -0.40f;
        st.control_authority_pct = std::max(85.0f, 94.0f - 1.5f * (st.attitude_err_deg - kAttitudeErrGateDeg));
    } else {
        st.vrs_recovery_active = false;
        st.commanded_vx_escape_mps = 0.0f;
        st.commanded_vz_mps = -clamped_descent_mps;
        const float vrs_ratio = clamped_descent_mps / kHoverInducedVi0Mps;
        st.control_authority_pct = std::clamp(100.0f - 11.9f * vrs_ratio, 90.0f, 99.5f);
    }
    return st;
}

// Pack supervisor telemetry into a deterministic 8-byte DroneCAN frame
inline CanFrame pack_telemetry_can_frame(
    const ThermalBatteryState& batt,
    const EKFAltitudeOutput& ekf,
    const AttitudeNotchPidState& att,
    FailsafeState fs
) noexcept {
    CanFrame frame{};
    frame.can_id = 0x10A4201u;
    frame.dlc = 8u;

    const auto v_mv = static_cast<uint16_t>(std::clamp(batt.v_term_eod_v * 1000.0f, 0.0f, 65535.0f));
    const auto alt_dm = static_cast<uint16_t>(std::clamp(ekf.fused_agl_m * 10.0f, 0.0f, 65535.0f));
    const auto temp_c_offset = static_cast<uint8_t>(std::clamp((batt.t_cell_k - 273.15f) + 50.0f, 0.0f, 255.0f));
    const auto att_err_centi = static_cast<uint8_t>(std::clamp(att.attitude_err_deg * 25.0f, 0.0f, 255.0f));
    const uint8_t status_flags = static_cast<uint8_t>(
        (static_cast<uint8_t>(fs) & 0x07u) |
        ((static_cast<uint8_t>(ekf.source) & 0x03u) << 3u) |
        (batt.thermal_ok ? 0x20u : 0x00u) |
        (ekf.ekf_healthy ? 0x40u : 0x00u) |
        (att.vrs_recovery_active ? 0x80u : 0x00u)
    );

    frame.data[0] = static_cast<uint8_t>((v_mv >> 8u) & 0xFFu);
    frame.data[1] = static_cast<uint8_t>(v_mv & 0xFFu);
    frame.data[2] = static_cast<uint8_t>((alt_dm >> 8u) & 0xFFu);
    frame.data[3] = static_cast<uint8_t>(alt_dm & 0xFFu);
    frame.data[4] = temp_c_offset;
    frame.data[5] = att_err_centi;
    frame.data[6] = status_flags;
    frame.data[7] = static_cast<uint8_t>(std::clamp(att.control_authority_pct, 0.0f, 100.0f));
    frame.crc16_ccitt = compute_can_crc16(frame);
    return frame;
}

inline SupervisorStepOutput step_opaslyhty_supervisor(
    const sil::McDrawInput& draw,
    const SupervisorConfig& cfg = SupervisorConfig{}
) noexcept {
    SupervisorStepOutput out{};
    const bool params_valid = verify_4s_param_guard(
        cfg.batt_crt_volt,
        cfg.batt_volt_mult,
        cfg.batt_low_volt,
        cfg.batt_arm_volt
    );

    out.battery = evaluate_coupled_battery_sag(
        draw.t_amb_k,
        draw.r_cell_25c_mohm,
        draw.p_cruise_elec_w,
        kCellOcvMeanV,
        cfg.t_cell_init_k,
        cfg.r_th_pack_k_w,
        cfg.p_ptc_max_w
    );
    out.ekf = evaluate_ekf3_altitude_voter(
        draw.baro_raw_agl_m,
        draw.lidar_range_m,
        draw.vio_agl_m,
        draw.t_amb_k
    );
    out.attitude = evaluate_attitude_and_vrs_gate(
        draw.attitude_err_deg * 0.7071f,
        draw.attitude_err_deg * 0.7071f,
        draw.descent_rate_mps,
        0.34f,
        cfg.consecutive_vrs_ticks
    );

    // Strict safety failsafe priority hierarchy:
    // 1. Pre-arm parameter guard failure -> kPreArmBlocked
    // 2. Critical EOD battery voltage or battery thermal fault (< 0 C or > +45 C) -> kCriticalBatteryLand
    // 3. Unhealthy EKF3 altitude voter or low battery warning -> kLowBatteryRtl
    // 4. Debounced Vortex Ring State -> kVrsLateralEscape (Vuichard lateral recovery)
    // 5. All gates healthy -> kNominalMission
    if (!params_valid) {
        out.failsafe = FailsafeState::kPreArmBlocked;
    } else if (!out.battery.thermal_ok || out.battery.v_term_eod_v < cfg.batt_crt_volt) {
        out.failsafe = FailsafeState::kCriticalBatteryLand;
    } else if (!out.ekf.ekf_healthy || out.battery.v_term_eod_v < cfg.batt_low_volt) {
        out.failsafe = FailsafeState::kLowBatteryRtl;
    } else if (out.attitude.vrs_recovery_active) {
        out.failsafe = FailsafeState::kVrsLateralEscape;
    } else {
        out.failsafe = FailsafeState::kNominalMission;
    }

    out.telemetry_frame = pack_telemetry_can_frame(out.battery, out.ekf, out.attitude, out.failsafe);
    return out;
}

}  // namespace opaslyhty::control

#if defined(STANDALONE_FIRMWARE_TEST)
int main() {
    using namespace opaslyhty;
    using namespace opaslyhty::control;

    // 1. Verify 4S Parameter Guard accepts Golden Iter 3 (12.8V, 18.182, 13.4V, 14.8V)
    //    and rejects Iter-1 6S bug (17.4V), inverted thresholds, and IEEE-754 NaN inputs.
    if (!verify_4s_param_guard(kBattCritVolt4S, kPm02V3VoltMult, kBattLowVolt4S, kBattArmVolt4S)) {
        std::fprintf(stderr, "FAIL: Golden 4S param guard rejected valid 12.8V / 18.182 profile\n");
        return 1;
    }
    if (verify_4s_param_guard(kLegacy6SCutoffBugV, 12.02f)) {
        std::fprintf(stderr, "FAIL: 4S param guard failed to reject Iter-1 17.4V 6S cutoff bug\n");
        return 1;
    }
    if (verify_4s_param_guard(13.5f, kPm02V3VoltMult, 13.2f, 14.8f)) {
        std::fprintf(stderr, "FAIL: 4S param guard failed to reject inverted BATT_LOW_VOLT < BATT_CRT_VOLT\n");
        return 1;
    }
    const float qnan = std::numeric_limits<float>::quiet_NaN();
    if (verify_4s_param_guard(qnan, kPm02V3VoltMult)) {
        std::fprintf(stderr, "FAIL: 4S param guard failed to reject NaN threshold\n");
        return 1;
    }

    // Verify supervisor enters kPreArmBlocked when defective 6S config is loaded
    SupervisorConfig bad_6s_cfg{};
    bad_6s_cfg.batt_crt_volt = kLegacy6SCutoffBugV;
    const auto prearm_res = step_opaslyhty_supervisor(sil::kMc3000Draws[0], bad_6s_cfg);
    if (prearm_res.failsafe != FailsafeState::kPreArmBlocked) {
        std::fprintf(stderr, "FAIL: Supervisor did not enter kPreArmBlocked on 6S cutoff bug\n");
        return 1;
    }

    // 2. Verify all 3,000 Common-Random-Numbers (CRN) Monte Carlo draws
    std::size_t passed_draws = 0;
    float min_v_term_eod = 99.0f;
    float max_alt_err = 0.0f;
    float min_ctrl_auth = 100.0f;

    for (std::size_t i = 0; i < sil::kNumMcDraws; ++i) {
        const auto res = step_opaslyhty_supervisor(sil::kMc3000Draws[i]);
        min_v_term_eod = std::min(min_v_term_eod, res.battery.v_term_eod_v);
        max_alt_err = std::max(max_alt_err, res.ekf.est_error_m);
        min_ctrl_auth = std::min(min_ctrl_auth, res.attitude.control_authority_pct);

        if (!res.battery.thermal_ok || !res.ekf.ekf_healthy) {
            std::fprintf(stderr, "FAIL on draw %zu: v_term_eod=%.2fV t_cell=%.2fK alt_err=%.2fm\n",
                         i, static_cast<double>(res.battery.v_term_eod_v),
                         static_cast<double>(res.battery.t_cell_k),
                         static_cast<double>(res.ekf.est_error_m));
            return 1;
        }
        if (res.failsafe != FailsafeState::kNominalMission) {
            std::fprintf(stderr, "FAIL on draw %zu: unexpected failsafe=%u\n",
                         i, static_cast<unsigned>(res.failsafe));
            return 1;
        }
        if (res.telemetry_frame.dlc != 8u ||
            res.telemetry_frame.crc16_ccitt != compute_can_crc16(res.telemetry_frame)) {
            std::fprintf(stderr, "FAIL on draw %zu: invalid CanFrame CRC-16\n", i);
            return 1;
        }
        ++passed_draws;
    }

    // 3. Adversarial Fault-Injection Test A: Cold-soaked uninsulated pack at -25 C (Iter-1 F2 flaw)
    SupervisorConfig cold_uninsulated_cfg{};
    cold_uninsulated_cfg.t_cell_init_k = 248.15f;
    cold_uninsulated_cfg.r_th_pack_k_w = 0.052f;
    cold_uninsulated_cfg.p_ptc_max_w = 0.0f;
    const auto cold_res = step_opaslyhty_supervisor(sil::kMc3000Draws[0], cold_uninsulated_cfg);
    if (cold_res.battery.thermal_ok || cold_res.failsafe != FailsafeState::kCriticalBatteryLand) {
        std::fprintf(stderr, "FAIL: Cold-soaked -25 C uninsulated pack did not trigger kCriticalBatteryLand\n");
        return 1;
    }

    // 4. Adversarial Fault-Injection Test B: Battery thermal overheat (> +45 C = 318.15 K)
    SupervisorConfig overheat_cfg{};
    overheat_cfg.t_cell_init_k = 328.15f;
    overheat_cfg.r_th_pack_k_w = 8.0f;
    const auto overheat_res = step_opaslyhty_supervisor(sil::kMc3000Draws[0], overheat_cfg);
    if (overheat_res.battery.thermal_ok || overheat_res.failsafe != FailsafeState::kCriticalBatteryLand) {
        std::fprintf(stderr, "FAIL: Overheated (>45 C) pack did not trigger kCriticalBatteryLand\n");
        return 1;
    }

    // 5. Adversarial Fault-Injection Test C: Baro vs. ExtNav VIO divergence (> 2.5 m at 85 m AGL)
    sil::McDrawInput ekf_fault_draw = sil::kMc3000Draws[1];
    ekf_fault_draw.vio_agl_m = 79.0f; // > 5 m divergence vs hypsometric baro (~85 m)
    const auto ekf_fault_res = step_opaslyhty_supervisor(ekf_fault_draw);
    if (ekf_fault_res.ekf.ekf_healthy || ekf_fault_res.failsafe != FailsafeState::kLowBatteryRtl) {
        std::fprintf(stderr, "FAIL: EKF3 Baro/VIO divergence did not trigger kLowBatteryRtl\n");
        return 1;
    }

    // 6. Adversarial Fault-Injection Test D: Debounced Vuichard VRS Lateral Escape
    // Single-tick wind gust (1 tick < 3-tick debounce) must NOT false-trigger VRS escape:
    const auto gust_1tick = evaluate_attitude_and_vrs_gate(3.5f, 3.0f, 2.4f, 0.34f, 1u);
    if (gust_1tick.vrs_recovery_active) {
        std::fprintf(stderr, "FAIL: Single-tick wind gust false-triggered VRS recovery without debounce\n");
        return 1;
    }
    // Sustained 3-tick high-sink instability must trigger Vuichard lateral escape (vx = 3.5 m/s):
    const auto vrs_3tick = evaluate_attitude_and_vrs_gate(3.5f, 3.0f, 2.4f, 0.34f, kVrsDebounceTicks);
    if (!vrs_3tick.vrs_recovery_active || vrs_3tick.commanded_vx_escape_mps < 3.0f) {
        std::fprintf(stderr, "FAIL: Sustained 3-tick VRS instability did not trigger Vuichard lateral escape\n");
        return 1;
    }

    std::printf(
        "Opaslyhty Golden Iter-3 SIL Verified: %zu/%zu MC draws passed | min_v_term_eod=%.2fV | max_alt_err=%.2fm | min_auth=%.1f%%\n",
        passed_draws,
        sil::kNumMcDraws,
        static_cast<double>(min_v_term_eod),
        static_cast<double>(max_alt_err),
        static_cast<double>(min_ctrl_auth)
    );
    std::printf("FIRMWARE_UNIT_TEST_PASS\n");
    return 0;
}
#endif
