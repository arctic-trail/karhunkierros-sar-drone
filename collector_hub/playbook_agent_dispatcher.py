#!/usr/bin/env python3
"""
Karhunkierros SAR — Structured Operations Playbook & JEV Agent Dispatcher
(`collector_hub/playbook_agent_dispatcher.py`)

Architecture Principle (Zero Offline Regex Parsing of Prose):
  - Trying to interpret free-text natural-language commands with regular expressions when an
    LLM is unavailable is fragile and unsafe in a life-safety SAR system.
  - Instead, when no External LLM API is active, this dispatcher provides ONLY:
      1. **Predefined Structured Playbook Profiles (`STRUCTURED_PLAYBOOK` / `OFFLINE_DETERMINISTIC`):**
         Pre-verified SAR mission profiles where all parameters (`search_altitude_agl_m`,
         `tracking_altitude_agl_m`, `preferred_target_type`, `drop_policy`, `drop_offset_m`,
         `rth_battery_floor_pct`, `human_cancel_veto_cooldown_s`) are provided as **structured,
         typed numeric/enum fields** validated by deterministic physical bounds (`L <= h <= U`,
         `>= 15 m` drop standoff, `>= 20%` battery reserve).
      2. **Direct Manual Control With No LLM (`MANUAL_HUMAN_ONLY`):**
         100% direct human control of sector scanning, target lock, and payload release.
  - Hardened with:
      * [RT1-01] Spatial-Temporal Expanding Veto Bubbles (`r(t) = min(150, 60 + 1.5*dt) + 2*sigma`)
                 + Monotonic `epoch_id` cancellation and permanent DROP veto latch.
      * [RT1-02] Structured Parameter Validator & Altitude Interval Feasibility Solver (`L <= U`).
      * [RT1-03] Pre-Filter Proposed State-Flip Thrash Breaker (`N_15(t) >= 3` flips in 15s)
                 and 8.0s Dwell Hysteresis (`theta_on >= 0.80`, `theta_off <= 0.50`).
      * [RT1-06] Ballistic Wind-Drift Impact Footprint Gate (`d_drift = 0.35 * W * sqrt(2h/g)`)
                 + Arctic Cold-Derated Headwind RTH Energy Reserve (`E_avail <= 1.25 * E_req`).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# 1. PRE-DEFINED STRUCTURED SAR OPERATIONS PLAYBOOKS (TYPED FIELDS, ZERO REGEX)
# =============================================================================

DEFAULT_PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY": {
        "id": "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY",
        "title": "1. Night Hiker Search & Opaslyhty Hut Escort (Default)",
        "summary": "Zero-overlap sector sweep at 55m AGL; preempt 1 drone on person detection (>=80% conf), auto-queue +42°C cask drop at 15m offset, escort to hut at 28m AGL.",
        "structured_params": {
            "search_altitude_agl_m": 55.0,
            "canopy_floor_m": 18.0,
            "altitude_ceiling_m": 120.0,
            "sector_overlap_pct": 0.0,
            "preempt_on_person": True,
            "preempt_on_vehicle": False,
            "preferred_target_type": "PERSON",
            "min_detection_confidence": 0.80,
            "tracking_altitude_agl_m": 28.0,
            "drop_policy": "AUTO_RELEASE_AT_OFFSET",
            "auto_queue_drop": True,
            "auto_release_drop": True,
            "require_human_drop_confirm": False,
            "drop_offset_m": 15.0,
            "drop_trigger_distance_m": 25.0,
            "return_to_scan_on_shelter_arrival": True,
            "shelter_arrival_radius_m": 15.0,
            "human_cancel_veto_cooldown_s": 300.0,
            "veto_bubble_radius_m": 60.0,
            "wildlife_min_altitude_m": 100.0,
            "rth_battery_floor_pct": 22.0,
        },
    },
    "PLAYBOOK_02_CAUTIOUS_HUMAN_CONFIRM_DROP": {
        "id": "PLAYBOOK_02_CAUTIOUS_HUMAN_CONFIRM_DROP",
        "title": "2. Cautious Search (Auto-Track Target, Require Human Confirm for Drop)",
        "summary": "Auto-locks lost person or vehicle with 1 drone while 3 scan, but NEVER releases payload without explicit human button confirmation.",
        "structured_params": {
            "search_altitude_agl_m": 55.0,
            "canopy_floor_m": 18.0,
            "altitude_ceiling_m": 120.0,
            "sector_overlap_pct": 0.0,
            "preempt_on_person": True,
            "preempt_on_vehicle": True,
            "preferred_target_type": "PERSON",
            "min_detection_confidence": 0.80,
            "tracking_altitude_agl_m": 30.0,
            "drop_policy": "QUEUE_REQUIRE_HUMAN_CONFIRM",
            "auto_queue_drop": True,
            "auto_release_drop": False,
            "require_human_drop_confirm": True,
            "drop_offset_m": 15.0,
            "drop_trigger_distance_m": 25.0,
            "return_to_scan_on_shelter_arrival": True,
            "shelter_arrival_radius_m": 15.0,
            "human_cancel_veto_cooldown_s": 600.0,
            "veto_bubble_radius_m": 60.0,
            "wildlife_min_altitude_m": 100.0,
            "rth_battery_floor_pct": 25.0,
        },
    },
    "PLAYBOOK_03_STRANDED_SNOWMOBILE_CORRIDOR": {
        "id": "PLAYBOOK_03_STRANDED_SNOWMOBILE_CORRIDOR",
        "title": "3. Stranded Snowmobile / Vehicle Corridor Escort",
        "summary": "Prioritizes stranded snowmobiles/vehicles (+34°C engine/exhaust), escorts along low-slope forestry route at 45m AGL to plowed road bridge.",
        "structured_params": {
            "search_altitude_agl_m": 65.0,
            "canopy_floor_m": 18.0,
            "altitude_ceiling_m": 120.0,
            "sector_overlap_pct": 0.0,
            "preempt_on_person": True,
            "preempt_on_vehicle": True,
            "preferred_target_type": "VEHICLE",
            "min_detection_confidence": 0.75,
            "tracking_altitude_agl_m": 45.0,
            "drop_policy": "QUEUE_REQUIRE_HUMAN_CONFIRM",
            "auto_queue_drop": True,
            "auto_release_drop": False,
            "require_human_drop_confirm": True,
            "drop_offset_m": 15.0,
            "drop_trigger_distance_m": 25.0,
            "return_to_scan_on_shelter_arrival": True,
            "shelter_arrival_radius_m": 15.0,
            "human_cancel_veto_cooldown_s": 300.0,
            "veto_bubble_radius_m": 60.0,
            "wildlife_min_altitude_m": 100.0,
            "rth_battery_floor_pct": 22.0,
        },
    },
    "PLAYBOOK_04_EW_DENIED_PASSIVE_RECON": {
        "id": "PLAYBOOK_04_EW_DENIED_PASSIVE_RECON",
        "title": "4. GNSS-Denied / Wildlife-Safe High-Standoff Sweep (Advisory Only)",
        "summary": "High-altitude 75m AGL sweep, strict >=100m Poronhoitolaki wildlife floor, no autonomous drop; switches AID to Advisory/Manual mode under EW.",
        "structured_params": {
            "search_altitude_agl_m": 75.0,
            "canopy_floor_m": 18.0,
            "altitude_ceiling_m": 120.0,
            "sector_overlap_pct": 0.0,
            "preempt_on_person": True,
            "preempt_on_vehicle": False,
            "preferred_target_type": "PERSON",
            "min_detection_confidence": 0.85,
            "tracking_altitude_agl_m": 35.0,
            "drop_policy": "MANUAL_ONLY",
            "auto_queue_drop": False,
            "auto_release_drop": False,
            "require_human_drop_confirm": True,
            "drop_offset_m": 15.0,
            "drop_trigger_distance_m": 25.0,
            "return_to_scan_on_shelter_arrival": True,
            "shelter_arrival_radius_m": 15.0,
            "human_cancel_veto_cooldown_s": 600.0,
            "veto_bubble_radius_m": 60.0,
            "wildlife_min_altitude_m": 100.0,
            "rth_battery_floor_pct": 28.0,
        },
    },
}


# =============================================================================
# 2. STRUCTURED TYPED PLAYBOOK PARAMETER VALIDATOR (ZERO REGEX PROSE PARSING)
# =============================================================================

@dataclass
class CompiledPlaybookRules:
    playbook_id: str
    title: str
    raw_markdown_sha256: str
    # Search rules
    search_altitude_agl_m: float = 55.0
    canopy_floor_m: float = 18.0
    altitude_ceiling_m: float = 120.0
    sector_overlap_pct: float = 0.0
    disjoint_sectors: bool = True
    # Preemption & Hysteresis rules ([RT1-03])
    preempt_on_person: bool = True
    preempt_on_vehicle: bool = False
    preferred_target_type: str = "PERSON"  # "PERSON" or "VEHICLE"
    min_detection_confidence: float = 0.80
    exit_detection_confidence: float = 0.50
    tracking_altitude_agl_m: float = 28.0
    min_dwell_s: float = 8.0
    # Payload drop rules
    drop_policy: str = "AUTO_RELEASE_AT_OFFSET"  # "AUTO_RELEASE_AT_OFFSET", "QUEUE_REQUIRE_HUMAN_CONFIRM", "MANUAL_ONLY"
    auto_queue_drop: bool = True
    auto_release_drop: bool = True
    require_human_drop_confirm: bool = False
    drop_offset_m: float = 15.0
    drop_trigger_distance_m: float = 25.0
    max_drop_wind_ms: float = 10.0
    # Post-escort completion rule
    return_to_scan_on_shelter_arrival: bool = True
    shelter_arrival_radius_m: float = 15.0
    # Hard safety & human-authority floors
    human_cancel_veto_cooldown_s: float = 300.0
    veto_bubble_radius_m: float = 60.0
    wildlife_min_altitude_m: float = 100.0
    rth_battery_floor_pct: float = 22.0
    parsed_clause_count: int = 8
    compile_warnings: List[str] = field(default_factory=list)


def build_structured_playbook_rules(
    playbook_id: str = "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY",
    structured_params: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
) -> CompiledPlaybookRules:
    """
    Deterministic Structured Playbook Validator (0 regex parsing of prose).
    Loads the predefined structured parameters for `playbook_id`, applies any typed
    `structured_params` overrides from the operator's structured form fields, and
    clamps every parameter to the certified physical safety envelope (`L <= h <= U`,
    `drop_offset_m >= 15.0`, `rth_battery_floor_pct >= 20.0`).
    """
    base_preset = DEFAULT_PLAYBOOKS.get(playbook_id, DEFAULT_PLAYBOOKS["PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY"])
    merged: Dict[str, Any] = dict(base_preset["structured_params"])
    if isinstance(structured_params, dict):
        for k, v in structured_params.items():
            if v is not None:
                merged[k] = v

    resolved_title = title or str(base_preset.get("title", "Structured SAR Playbook"))
    canonical_json = json.dumps(merged, sort_keys=True, default=str)
    sha = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]

    rules = CompiledPlaybookRules(
        playbook_id=playbook_id,
        title=resolved_title[:90],
        raw_markdown_sha256=sha,
    )

    # 1. Canopy floor & altitude ceiling interval feasibility (`L <= U`)
    raw_canopy = float(merged.get("canopy_floor_m", 18.0))
    rules.canopy_floor_m = max(15.0, min(35.0, raw_canopy))
    raw_ceiling = float(merged.get("altitude_ceiling_m", 120.0))
    rules.altitude_ceiling_m = max(20.0, min(150.0, raw_ceiling))

    lower_bound = max(28.0, rules.canopy_floor_m + 10.0)
    if lower_bound > rules.altitude_ceiling_m:
        rules.compile_warnings.append(
            f"INFEASIBLE_ALTITUDE_INTERVAL: L={lower_bound}m > U={rules.altitude_ceiling_m}m; reset ceiling to 120.0m."
        )
        rules.altitude_ceiling_m = 120.0

    # 2. Search altitude & overlap
    req_search_alt = float(merged.get("search_altitude_agl_m", 55.0))
    if req_search_alt < lower_bound:
        rules.compile_warnings.append(f"Clamped search altitude {req_search_alt}m up to {lower_bound}m canopy safety floor.")
        req_search_alt = lower_bound
    elif req_search_alt > rules.altitude_ceiling_m:
        rules.compile_warnings.append(f"Clamped search altitude {req_search_alt}m down to {rules.altitude_ceiling_m}m ceiling.")
        req_search_alt = rules.altitude_ceiling_m
    rules.search_altitude_agl_m = req_search_alt
    rules.sector_overlap_pct = max(0.0, min(50.0, float(merged.get("sector_overlap_pct", 0.0))))

    # 3. Target preemption & tracking altitude
    pref_tgt = str(merged.get("preferred_target_type", "PERSON")).upper().strip()
    if pref_tgt == "BOTH":
        rules.preferred_target_type = "PERSON"
        rules.preempt_on_person = True
        rules.preempt_on_vehicle = True
    elif pref_tgt == "VEHICLE":
        rules.preferred_target_type = "VEHICLE"
        rules.preempt_on_vehicle = bool(merged.get("preempt_on_vehicle", True))
        rules.preempt_on_person = bool(merged.get("preempt_on_person", True))
    else:
        rules.preferred_target_type = "PERSON"
        rules.preempt_on_person = bool(merged.get("preempt_on_person", True))
        rules.preempt_on_vehicle = bool(merged.get("preempt_on_vehicle", False))

    raw_conf = float(merged.get("min_detection_confidence", 0.80))
    if raw_conf > 1.0:
        raw_conf = raw_conf / 100.0
    rules.min_detection_confidence = max(0.55, min(0.99, raw_conf))
    rules.exit_detection_confidence = round(max(0.35, rules.min_detection_confidence - 0.30), 2)

    req_track_alt = float(merged.get("tracking_altitude_agl_m", 28.0))
    if req_track_alt < lower_bound:
        rules.compile_warnings.append(f"Clamped tracking altitude {req_track_alt}m up to {lower_bound}m canopy floor.")
        req_track_alt = lower_bound
    elif req_track_alt > rules.altitude_ceiling_m:
        req_track_alt = rules.altitude_ceiling_m
    rules.tracking_altitude_agl_m = req_track_alt

    # 4. Payload drop policy & mandatory >=15m human safety standoff
    drop_pol = str(merged.get("drop_policy", "")).upper().strip()
    if drop_pol == "AUTO_RELEASE_AT_OFFSET":
        rules.drop_policy = "AUTO_RELEASE_AT_OFFSET"
        rules.auto_queue_drop = True
        rules.auto_release_drop = True
        rules.require_human_drop_confirm = False
    elif drop_pol == "QUEUE_REQUIRE_HUMAN_CONFIRM":
        rules.drop_policy = "QUEUE_REQUIRE_HUMAN_CONFIRM"
        rules.auto_queue_drop = True
        rules.auto_release_drop = False
        rules.require_human_drop_confirm = True
    elif drop_pol == "MANUAL_ONLY":
        rules.drop_policy = "MANUAL_ONLY"
        rules.auto_queue_drop = False
        rules.auto_release_drop = False
        rules.require_human_drop_confirm = True
    else:
        rules.auto_queue_drop = bool(merged.get("auto_queue_drop", True))
        rules.auto_release_drop = bool(merged.get("auto_release_drop", True))
        rules.require_human_drop_confirm = bool(merged.get("require_human_drop_confirm", not rules.auto_release_drop))
        rules.drop_policy = (
            "AUTO_RELEASE_AT_OFFSET"
            if (rules.auto_release_drop and not rules.require_human_drop_confirm)
            else ("QUEUE_REQUIRE_HUMAN_CONFIRM" if rules.auto_queue_drop else "MANUAL_ONLY")
        )

    raw_off = float(merged.get("drop_offset_m", 15.0))
    if raw_off < 15.0:
        rules.compile_warnings.append(
            f"Requested {raw_off}m drop offset; enforced >=15.0m mandatory human safety standoff."
        )
        raw_off = 15.0
    rules.drop_offset_m = min(60.0, raw_off)
    rules.drop_trigger_distance_m = max(15.0, min(60.0, float(merged.get("drop_trigger_distance_m", 25.0))))

    # 5. Safety & Veto floors
    rules.return_to_scan_on_shelter_arrival = bool(merged.get("return_to_scan_on_shelter_arrival", True))
    rules.shelter_arrival_radius_m = max(8.0, min(40.0, float(merged.get("shelter_arrival_radius_m", 15.0))))
    rules.human_cancel_veto_cooldown_s = max(30.0, min(3600.0, float(merged.get("human_cancel_veto_cooldown_s", 300.0))))
    rules.veto_bubble_radius_m = max(30.0, min(200.0, float(merged.get("veto_bubble_radius_m", 60.0))))
    rules.wildlife_min_altitude_m = max(100.0, float(merged.get("wildlife_min_altitude_m", 100.0)))

    raw_batt = float(merged.get("rth_battery_floor_pct", 22.0))
    if raw_batt < 20.0:
        rules.compile_warnings.append(f"Clamped battery RTH floor {raw_batt}% up to 20.0% minimum reserve.")
        raw_batt = 20.0
    rules.rth_battery_floor_pct = min(55.0, raw_batt)
    rules.parsed_clause_count = len(merged)

    return rules


def compile_natural_language_playbook(
    structured_or_preset: Any = None,
    playbook_id: str = "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY",
    title: Optional[str] = None,
    structured_params: Optional[Dict[str, Any]] = None,
) -> CompiledPlaybookRules:
    """
    Backwards-compatible entry point that strictly delegates to `build_structured_playbook_rules`
    using structured dictionary parameters or preset IDs (never regex-parsing free text).
    """
    if isinstance(structured_or_preset, dict):
        merged_params = dict(structured_or_preset)
        if structured_params:
            merged_params.update(structured_params)
        return build_structured_playbook_rules(playbook_id=playbook_id, structured_params=merged_params, title=title)
    if isinstance(structured_or_preset, str) and structured_or_preset in DEFAULT_PLAYBOOKS:
        return build_structured_playbook_rules(playbook_id=structured_or_preset, structured_params=structured_params, title=title)
    return build_structured_playbook_rules(playbook_id=playbook_id, structured_params=structured_params, title=title)


# =============================================================================
# 3. SPATIAL-TEMPORAL VETO BUBBLES & EPOCH REGISTRY ([RT1-01] FIX)
# =============================================================================

@dataclass
class SpatialTemporalVetoBubble:
    bubble_id: str
    kind: str  # "LOCK" or "DROP"
    target_type: str
    center_x_m: float
    center_y_m: float
    base_radius_m: float
    v_expansion_ms: float
    max_radius_m: float
    created_ts: float
    until_ts: float  # float('inf') for DROP vetoes (never expire on a timer!)
    epoch_id: int

    def current_radius_m(self, now_ts: float) -> float:
        dt = max(0.0, now_ts - self.created_ts)
        return min(self.max_radius_m, self.base_radius_m + self.v_expansion_ms * dt)

    def contains_point(self, x_m: float, y_m: float, pos_sigma_m: float, now_ts: float) -> bool:
        if now_ts >= self.until_ts:
            return False
        dist = math.hypot(x_m - self.center_x_m, y_m - self.center_y_m)
        return dist <= (self.current_radius_m(now_ts) + 2.0 * max(0.0, pos_sigma_m))


class HumanVetoRegistry:
    """
    [RT1-01 Fix] Spatial-Temporal Veto Bubble & Monotonic Epoch Registry.
    - When the human cancels a target lock at `(x_m, y_m)`, creates a `SpatialTemporalVetoBubble`
      (`r_0 = 60 m`, expanding at `1.5 m/s` up to `150 m`) AND bumps `current_epoch`.
      * If the tracker drops track `#17` and respawns `#23` at the same spot 2 seconds later,
        `#23` is inside the spatial bubble and stays suppressed!
      * If a SECOND lost hiker appears 300 m away outside the bubble, they are NOT blocked!
    - Drop vetoes (`kind="DROP"`) have `until_ts = inf` and NEVER expire on a timer; only an
      explicit human re-arm clears a Drop veto.
    """

    def __init__(self) -> None:
        self.current_epoch: int = 1
        self.bubbles: List[SpatialTemporalVetoBubble] = []
        self.target_veto_until_ts: Dict[str, float] = {}
        self.drop_veto_latched: Dict[str, bool] = {}
        self.last_human_action_ts: float = 0.0
        self.last_human_action_desc: str = "None"

    def bump_epoch(self, reason: str = "Human Cancel") -> int:
        self.current_epoch += 1
        self.last_human_action_ts = time.time()
        self.last_human_action_desc = f"Epoch #{self.current_epoch}: {reason}"
        return self.current_epoch

    def record_human_target_cancel(
        self,
        target_id: str = "PERSON",
        cooldown_s: float = 300.0,
        x_m: float = 40.0,
        y_m: float = -45.0,
        base_radius_m: float = 60.0,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        now = time.time() if now_ts is None else now_ts
        self.current_epoch += 1
        until = now + max(30.0, float(cooldown_s))
        t_key = target_id.upper()
        self.target_veto_until_ts[t_key] = until

        bub = SpatialTemporalVetoBubble(
            bubble_id=f"VETO-LOCK-E{self.current_epoch}",
            kind="LOCK",
            target_type=t_key,
            center_x_m=float(x_m),
            center_y_m=float(y_m),
            base_radius_m=float(base_radius_m),
            v_expansion_ms=1.5,
            max_radius_m=150.0,
            created_ts=now,
            until_ts=until,
            epoch_id=self.current_epoch,
        )
        self.bubbles.append(bub)
        self.last_human_action_ts = now
        self.last_human_action_desc = (
            f"Epoch #{self.current_epoch}: Human canceled target lock on {t_key} at ({x_m:.0f}m, {y_m:.0f}m) "
            f"— 60m spatial bubble vetoed for {int(cooldown_s)}s"
        )
        return {
            "epoch_id": self.current_epoch,
            "bubble_id": bub.bubble_id,
            "target_id": t_key,
            "center_xy_m": [x_m, y_m],
            "base_radius_m": base_radius_m,
            "vetoed_until_ts": until,
            "cooldown_s": cooldown_s,
            "desc": self.last_human_action_desc,
        }

    def clear_human_target_veto(self, target_id: str = "ALL") -> int:
        self.current_epoch += 1
        t_key = target_id.upper()
        if t_key == "ALL":
            self.target_veto_until_ts.clear()
            self.bubbles = [b for b in self.bubbles if b.kind != "LOCK"]
        else:
            self.target_veto_until_ts.pop(t_key, None)
            self.bubbles = [b for b in self.bubbles if not (b.kind == "LOCK" and b.target_type == t_key)]
        self.last_human_action_ts = time.time()
        self.last_human_action_desc = f"Epoch #{self.current_epoch}: Human explicitly re-armed target lock ({t_key})"
        return self.current_epoch

    def is_target_vetoed_by_human(
        self,
        target_id: str,
        x_m: Optional[float] = None,
        y_m: Optional[float] = None,
        pos_sigma_m: float = 3.0,
        now_ts: Optional[float] = None,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        [RT1-01 & RT2-01 Fix] Area-wide, class-independent spatial-temporal veto check with
        fail-closed behavior when coordinates are missing while an active LOCK bubble exists.
        """
        now = time.time() if now_ts is None else now_ts
        active_lock_bubbles = [b for b in self.bubbles if b.kind == "LOCK" and now < b.until_ts]
        if not active_lock_bubbles:
            return False, 0.0, None

        # [RT2-01] Fail closed if an active spatial veto exists but candidate coordinates are missing/non-finite
        if x_m is None or y_m is None or not (math.isfinite(float(x_m)) and math.isfinite(float(y_m))):
            b0 = active_lock_bubbles[0]
            return True, round(b0.until_ts - now, 1), f"{b0.bubble_id}:FAIL_CLOSED_NO_XY"

        # Area-wide spatial check (independent of class label so PERSON<->VEHICLE flip cannot bypass veto)
        for b in active_lock_bubbles:
            if b.contains_point(float(x_m), float(y_m), pos_sigma_m, now):
                rem = round(b.until_ts - now, 1)
                return True, rem, b.bubble_id
        return False, 0.0, None

    def record_human_drop_cancel(
        self,
        target_id: str = "ALL",
        x_m: float = 40.0,
        y_m: float = -45.0,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """[RT1-01 Fix] Drop veto latches permanently (until_ts = inf) until explicit human re-arm."""
        now = time.time() if now_ts is None else now_ts
        self.current_epoch += 1
        t_key = target_id.upper()
        self.drop_veto_latched[t_key] = True
        self.drop_veto_latched["ALL"] = True
        bub = SpatialTemporalVetoBubble(
            bubble_id=f"VETO-DROP-E{self.current_epoch}",
            kind="DROP",
            target_type=t_key,
            center_x_m=float(x_m),
            center_y_m=float(y_m),
            base_radius_m=80.0,
            v_expansion_ms=0.0,
            max_radius_m=80.0,
            created_ts=now,
            until_ts=float("inf"),
            epoch_id=self.current_epoch,
        )
        self.bubbles.append(bub)
        self.last_human_action_ts = now
        self.last_human_action_desc = (
            f"Epoch #{self.current_epoch}: Human canceled pending drop — latched OFF until explicit human re-arm"
        )
        return {
            "epoch_id": self.current_epoch,
            "bubble_id": bub.bubble_id,
            "target_id": t_key,
            "drop_veto_latched": True,
            "desc": self.last_human_action_desc,
        }

    def clear_human_drop_veto(self, target_id: str = "ALL") -> int:
        self.current_epoch += 1
        t_key = target_id.upper()
        self.drop_veto_latched.pop(t_key, None)
        self.drop_veto_latched.pop("ALL", None)
        self.bubbles = [b for b in self.bubbles if b.kind != "DROP"]
        self.last_human_action_ts = time.time()
        self.last_human_action_desc = f"Epoch #{self.current_epoch}: Human explicitly re-armed payload drop"
        return self.current_epoch

    def is_drop_vetoed_by_human(self, target_id: str = "ALL") -> bool:
        return bool(self.drop_veto_latched.get(target_id.upper()) or self.drop_veto_latched.get("ALL"))

    def reset_all(self) -> int:
        self.current_epoch += 1
        self.bubbles.clear()
        self.target_veto_until_ts.clear()
        self.drop_veto_latched.clear()
        self.last_human_action_desc = f"Epoch #{self.current_epoch}: All human vetoes cleared"
        return self.current_epoch


# =============================================================================
# 4. HARD PHYSICAL SAFETY ENVELOPE VERIFIER (THE "V" IN JEV)
# =============================================================================

@dataclass
class SafetyVerificationResult:
    approved: bool
    action_type: str
    epoch_id: int
    modified_params: Dict[str, Any]
    rejection_reason: Optional[str] = None
    invariant_checks: List[str] = field(default_factory=list)


def compute_arctic_wind_adjusted_rth_floor_pct(
    base_floor_pct: float = 22.0,
    dist_home_m: float = 450.0,
    wind_speed_ms: float = 4.0,
    temp_c: float = -15.0,
    cruise_airspeed_ms: float = 13.0,
) -> Tuple[float, Dict[str, float]]:
    """
    [RT1-06 Fix] Compute Arctic cold-derated, headwind-adjusted battery RTH threshold:
      v_g,home = max(3.0, V_air - 1.3 * W_mean)
      k_temp(T_cell) = min(1.0, max(0.60, 1.0 - 0.008 * max(0, -T_cell)))
      Trigger RTH when E_avail <= 1.25 * E_req
    """
    gust_wind_ms = 1.3 * max(0.0, float(wind_speed_ms))
    vg_home_ms = max(3.0, float(cruise_airspeed_ms) - gust_wind_ms)
    k_temp = min(1.0, max(0.60, 1.0 - 0.008 * max(0.0, -float(temp_c))))
    # Nominal return energy fraction at 13 m/s in +15C is ~1.8% per km; scale by (13/vg_home)/k_temp * 1.25 safety factor
    rth_leg_pct = (dist_home_m / 1000.0) * 1.8 * (13.0 / vg_home_ms) / k_temp
    hover_descend_reserve_pct = (6.0 / k_temp)
    required_soc_pct = max(float(base_floor_pct), min(65.0, 1.25 * (rth_leg_pct + hover_descend_reserve_pct)))
    return round(required_soc_pct, 1), {
        "vg_home_ms": round(vg_home_ms, 2),
        "k_temp": round(k_temp, 3),
        "required_soc_pct": round(required_soc_pct, 1),
    }


def verify_action_safety_gate(
    action_type: str,
    params: Dict[str, Any],
    telemetry: Dict[str, Any],
    compiled_rules: CompiledPlaybookRules,
    veto_registry: HumanVetoRegistry,
    request_epoch: Optional[int] = None,
    now_ts: Optional[float] = None,
) -> SafetyVerificationResult:
    """
    Deterministic Formal Safety Kernel (The 'Verify' stage of Judge-Evaluate-Verify).
    Enforces:
      0. Monotonic `epoch_id` freshness (`request_epoch == veto_registry.current_epoch`)
      1. Spatial-Temporal Human Veto Bubbles (`[RT1-01]`)
      2. Boreal Tree Canopy & Wildlife Altitude Interval Feasibility (`L <= h <= U`, `[RT1-02]`)
      3. 15 m Human Standoff + Ballistic Wind-Drift Impact Footprint (`[RT1-06]`)
      4. Arctic Cold & Gust-Headwind Battery RTH Reserve (`[RT1-06]`)
    """
    now = time.time() if now_ts is None else now_ts
    safe_params = dict(params)
    checks: List[str] = []

    # Invariant 0: Monotonic Epoch Freshness ([RT1-01])
    if request_epoch is not None and int(request_epoch) < veto_registry.current_epoch:
        return SafetyVerificationResult(
            approved=False,
            action_type=action_type,
            epoch_id=veto_registry.current_epoch,
            modified_params=safe_params,
            rejection_reason=(
                f"STALE_EPOCH_REJECTED: Proposal epoch #{request_epoch} < current epoch #{veto_registry.current_epoch} "
                "(human canceled or changed mode while request was in flight)."
            ),
            invariant_checks=["FAIL: Monotonic Epoch Arbiter"],
        )
    checks.append(f"PASS: Epoch #{veto_registry.current_epoch} Fresh")

    # Invariant 1: Spatial-Temporal Human Veto Bubbles ([RT1-01])
    target_id = str(safe_params.get("target_type", compiled_rules.preferred_target_type)).upper()
    tx_m = safe_params.get("target_x_m", telemetry.get("target_x_m"))
    ty_m = safe_params.get("target_y_m", telemetry.get("target_y_m"))
    if action_type == "LOCK_TARGET":
        vetoed, rem_s, bub_id = veto_registry.is_target_vetoed_by_human(
            target_id, x_m=tx_m, y_m=ty_m, now_ts=now
        )
        if vetoed:
            return SafetyVerificationResult(
                approved=False,
                action_type=action_type,
                epoch_id=veto_registry.current_epoch,
                modified_params=safe_params,
                rejection_reason=f"HUMAN_VETO_BUBBLE_ACTIVE ({bub_id}): Target suppressed for {rem_s}s inside spatial bubble.",
                invariant_checks=[f"FAIL: Spatial Veto Bubble ({bub_id})"],
            )
        checks.append("PASS: Spatial Target Veto Clear")

    if action_type in ("QUEUE_DROP", "EXECUTE_DROP"):
        if veto_registry.is_drop_vetoed_by_human(target_id):
            return SafetyVerificationResult(
                approved=False,
                action_type=action_type,
                epoch_id=veto_registry.current_epoch,
                modified_params=safe_params,
                rejection_reason="HUMAN_DROP_VETO_LATCHED: Human canceled drop; latched OFF until explicit human re-arm.",
                invariant_checks=["FAIL: Permanent Human Drop Veto Latch"],
            )
        if action_type == "EXECUTE_DROP" and compiled_rules.require_human_drop_confirm:
            return SafetyVerificationResult(
                approved=False,
                action_type=action_type,
                epoch_id=veto_registry.current_epoch,
                modified_params=safe_params,
                rejection_reason="PLAYBOOK_REQUIRES_HUMAN_CONFIRM: Autonomous servo release prohibited by playbook.",
                invariant_checks=["FAIL: Playbook Human-Confirm Interlock"],
            )
        checks.append("PASS: Drop Authority & Veto Latch Clear")

    # Invariant 2: Altitude Interval Feasibility (`L <= h <= U`, [RT1-02])
    min_floor = max(28.0, compiled_rules.canopy_floor_m + 10.0)
    if telemetry.get("wildlife_detected", False):
        min_floor = max(min_floor, compiled_rules.wildlife_min_altitude_m)
    max_ceil = compiled_rules.altitude_ceiling_m

    if "altitude_agl_m" in safe_params:
        req_alt = float(safe_params["altitude_agl_m"])
        if min_floor > max_ceil:
            return SafetyVerificationResult(
                approved=False,
                action_type=action_type,
                epoch_id=veto_registry.current_epoch,
                modified_params=safe_params,
                rejection_reason=f"INFEASIBLE_ALTITUDE_CONSTRAINTS: L={min_floor}m > U={max_ceil}m.",
                invariant_checks=["FAIL: Altitude Interval Feasibility"],
            )
        clamped_alt = min(max_ceil, max(min_floor, req_alt))
        if clamped_alt != req_alt:
            safe_params["altitude_agl_m"] = clamped_alt
            checks.append(f"CLAMPED: Altitude {req_alt}m -> {clamped_alt}m ([{min_floor}m, {max_ceil}m])")
        else:
            checks.append(f"PASS: Altitude {req_alt}m within [{min_floor}m, {max_ceil}m]")

    # Invariant 3: 15m Human Standoff + Ballistic Wind-Drift Impact Footprint ([RT1-06])
    if action_type in ("QUEUE_DROP", "EXECUTE_DROP"):
        offset_m = float(safe_params.get("offset_m", compiled_rules.drop_offset_m))
        wind_ms = float(telemetry.get("wind_speed_ms", 4.0))
        drone_vg_ms = float(telemetry.get("drone_ground_speed_ms", 0.5))
        drop_h_m = float(safe_params.get("drop_height_m", 15.0))
        t_fall_s = math.sqrt(2.0 * max(5.0, drop_h_m) / 9.80665) * 1.08
        wind_drift_m = 0.35 * wind_ms * t_fall_s

        if offset_m < 15.0:
            return SafetyVerificationResult(
                approved=False,
                action_type=action_type,
                epoch_id=veto_registry.current_epoch,
                modified_params=safe_params,
                rejection_reason=f"UNSAFE_DROP_OFFSET: Requested {offset_m:.1f}m < 15.0m human safety standoff.",
                invariant_checks=["FAIL: 15m Human Drop Standoff"],
            )
        if action_type == "EXECUTE_DROP" and (wind_drift_m > 0.45 * offset_m or drone_vg_ms > 1.5):
            return SafetyVerificationResult(
                approved=False,
                action_type=action_type,
                epoch_id=veto_registry.current_epoch,
                modified_params=safe_params,
                rejection_reason=(
                    f"BALLISTIC_IMPACT_ENVELOPE_UNSAFE: Wind drift {wind_drift_m:.1f}m (limit {0.45*offset_m:.1f}m) "
                    f"or ground speed {drone_vg_ms:.1f}m/s > 1.5m/s."
                ),
                invariant_checks=["FAIL: Ballistic Wind-Drift Impact Footprint"],
            )
        checks.append(f"PASS: Drop offset {offset_m:.1f}m (wind drift {wind_drift_m:.1f}m safe)")

    # Invariant 4: Arctic Cold & Headwind-Adjusted Battery RTH Floor ([RT1-06])
    batt_pct = float(telemetry.get("battery_pct", 84.0))
    dynamic_rth_pct, rth_meta = compute_arctic_wind_adjusted_rth_floor_pct(
        base_floor_pct=compiled_rules.rth_battery_floor_pct,
        dist_home_m=float(telemetry.get("dist_home_m", 450.0)),
        wind_speed_ms=float(telemetry.get("wind_speed_ms", 4.0)),
        temp_c=float(telemetry.get("temp_c", -12.0)),
    )
    if batt_pct < dynamic_rth_pct and action_type not in ("RTB_LOW_BATTERY", "HOLD_STATION"):
        return SafetyVerificationResult(
            approved=False,
            action_type=action_type,
            epoch_id=veto_registry.current_epoch,
            modified_params=safe_params,
            rejection_reason=(
                f"BATTERY_BELOW_ARCTIC_RTH_FLOOR: Battery {batt_pct:.1f}% < wind/cold-adjusted RTH floor "
                f"{dynamic_rth_pct:.1f}% (vg_home={rth_meta['vg_home_ms']}m/s, k_temp={rth_meta['k_temp']})."
            ),
            invariant_checks=["FAIL: Arctic Wind/Cold Battery RTH Floor"],
        )
    checks.append(f"PASS: Battery {batt_pct:.1f}% >= {dynamic_rth_pct:.1f}% Arctic RTH floor")

    return SafetyVerificationResult(
        approved=True,
        action_type=action_type,
        epoch_id=veto_registry.current_epoch,
        modified_params=safe_params,
        rejection_reason=None,
        invariant_checks=checks,
    )


# =============================================================================
# 5. AUTONOMOUS JEV AGENT DISPATCHER & THRASH/LATENCY CIRCUIT-BREAKER ([RT1-03])
# =============================================================================

class PlaybookAgentDispatcher:
    """
    Manages the active Natural-Language Playbook, compiles it deterministically,
    manages External LLM API Key configuration (in-memory session or optional `0600`
    on-disk persistence in `_private/llm_api_credentials.json`), monitors LLM latency
    AND pre-filter state-flip thrashing (`[RT1-03]`), and runs the JEV
    (Judge -> Evaluate -> Verify) decision cycle.
    """

    def __init__(self, credentials_disk_path: Optional[str] = None) -> None:
        self.active_playbook_id: str = "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY"
        self.active_structured_params: Dict[str, Any] = dict(
            DEFAULT_PLAYBOOKS[self.active_playbook_id]["structured_params"]
        )
        self.compiled_rules: CompiledPlaybookRules = build_structured_playbook_rules(
            playbook_id=self.active_playbook_id,
            structured_params=self.active_structured_params,
            title=DEFAULT_PLAYBOOKS[self.active_playbook_id]["title"],
        )
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.credentials_disk_path: str = (
            credentials_disk_path
            if credentials_disk_path is not None
            else os.path.join(repo_root, "_private", "llm_api_credentials.json")
        )
        self.llm_provider: str = "openai"
        self.llm_model: str = "gpt-5.4-mini"
        self._runtime_api_key: str = ""
        self.api_key_saved_on_disk: bool = False
        self.requires_api_key_prompt: bool = False
        self._load_saved_api_key_from_disk()

        self.aid_mode: str = "OFFLINE_DETERMINISTIC"
        self.fallback_on_llm_unavailable: str = "OFFLINE_DETERMINISTIC"
        self.circuit_breaker_tripped: bool = False
        self.circuit_breaker_reason: str = "Normal (<1 ms Structured Parameter Playbook — Zero Regex)"
        self.veto_registry: HumanVetoRegistry = HumanVetoRegistry()
        # [RT1-03 & RT2-03 Fix] Dwell timer (`None` until first transition) & Thrash Counter
        self.last_accepted_state: str = "CONTINUE_COOPERATIVE_SCAN"
        self.last_accepted_transition_ts: Optional[float] = None
        self.proposed_state_history: List[Tuple[float, str]] = []  # (ts, proposed_action)
        self.decision_log: List[Dict[str, Any]] = []

    def _load_saved_api_key_from_disk(self) -> None:
        """Load optional saved LLM API key from `_private/llm_api_credentials.json` if present."""
        if not self.credentials_disk_path or not os.path.exists(self.credentials_disk_path):
            return
        try:
            with open(self.credentials_disk_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            key = str(data.get("api_key", "")).strip()
            if key:
                self._runtime_api_key = key
                self.llm_provider = str(data.get("provider", "openai")).strip() or "openai"
                self.llm_model = str(data.get("model", "gpt-5.4-mini")).strip() or "gpt-5.4-mini"
                self.api_key_saved_on_disk = True
        except Exception:
            pass

    def _get_effective_api_key(self) -> str:
        if self._runtime_api_key:
            return self._runtime_api_key
        return (
            os.getenv("SAR_LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or ""
        ).strip()

    def has_llm_api_key(self) -> bool:
        return bool(self._get_effective_api_key())

    def get_masked_api_key(self) -> str:
        key = self._get_effective_api_key()
        if not key:
            return "Not Configured"
        if len(key) <= 8:
            return f"{key[:2]}...{key[-2:]}"
        return f"{key[:5]}...{key[-4:]}"

    def configure_llm_api_key(
        self,
        api_key: str = "",
        provider: str = "openai",
        model: str = "gpt-5.4-mini",
        save_to_disk: bool = False,
        clear_key: bool = False,
        activate_cloud_mode: bool = True,
    ) -> Dict[str, Any]:
        """
        Configure or clear the External LLM API Key used by `CLOUD_LLM_JEV` mode.
        When `save_to_disk=True`, atomically persists the key to `_private/llm_api_credentials.json`
        with `0600` (owner read/write only) permissions inside the gitignored `_private/` folder.
        When `save_to_disk=False`, keeps the key in memory only for the current session and removes
        any previously persisted disk file.
        """
        if clear_key:
            self._runtime_api_key = ""
            self.api_key_saved_on_disk = False
            self.requires_api_key_prompt = False
            if self.credentials_disk_path and os.path.exists(self.credentials_disk_path):
                try:
                    os.remove(self.credentials_disk_path)
                except Exception:
                    pass
            if self.aid_mode == "CLOUD_LLM_JEV" and not self.has_llm_api_key():
                self.aid_mode = self.fallback_on_llm_unavailable
                self.circuit_breaker_tripped = False
                self.circuit_breaker_reason = f"API Key Cleared -> Switched to {self.aid_mode}"
            return self.get_status()

        clean_key = "".join(ch for ch in str(api_key).strip() if ch.isprintable() and not ch.isspace())
        clean_provider = str(provider or "openai").strip().lower()
        if clean_provider not in {"openai", "anthropic", "custom"}:
            clean_provider = "openai"
        clean_model = "".join(ch for ch in str(model or "gpt-5.4-mini").strip() if ch.isprintable())[:64]

        if clean_key:
            self._runtime_api_key = clean_key
            self.llm_provider = clean_provider
            self.llm_model = clean_model

        if save_to_disk and self._runtime_api_key:
            priv_dir = os.path.dirname(self.credentials_disk_path)
            os.makedirs(priv_dir, mode=0o700, exist_ok=True)
            tmp_path = f"{self.credentials_disk_path}.tmp.{os.getpid()}"
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "provider": self.llm_provider,
                        "model": self.llm_model,
                        "api_key": self._runtime_api_key,
                        "saved_at_epoch": round(time.time(), 2),
                    },
                    f,
                    indent=2,
                )
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.credentials_disk_path)
            try:
                os.chmod(self.credentials_disk_path, 0o600)
            except Exception:
                pass
            self.api_key_saved_on_disk = True
        elif not save_to_disk:
            self.api_key_saved_on_disk = False
            if self.credentials_disk_path and os.path.exists(self.credentials_disk_path):
                try:
                    os.remove(self.credentials_disk_path)
                except Exception:
                    pass

        if activate_cloud_mode and self.has_llm_api_key():
            self.aid_mode = "CLOUD_LLM_JEV"
            self.requires_api_key_prompt = False
            self.circuit_breaker_tripped = False
            storage_label = "Saved to Disk (0600)" if self.api_key_saved_on_disk else "Session Memory Only"
            self.circuit_breaker_reason = (
                f"External LLM JEV Active ({self.llm_provider}:{self.llm_model}, {storage_label})"
            )

        return self.get_status()

    def set_playbook(
        self,
        playbook_id: str,
        structured_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Selects a predefined structured playbook preset and optionally applies typed
        structured parameter overrides (`search_altitude_agl_m`, `tracking_altitude_agl_m`,
        `preferred_target_type`, `drop_policy`, `drop_offset_m`, `rth_battery_floor_pct`,
        `human_cancel_veto_cooldown_s`). Zero regex parsing of free text.
        """
        if playbook_id in DEFAULT_PLAYBOOKS:
            self.active_playbook_id = playbook_id
            base_params = dict(DEFAULT_PLAYBOOKS[playbook_id]["structured_params"])
            title = DEFAULT_PLAYBOOKS[playbook_id]["title"]
        else:
            self.active_playbook_id = "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY"
            base_params = dict(DEFAULT_PLAYBOOKS[self.active_playbook_id]["structured_params"])
            title = "Custom Structured Playbook" if structured_params else DEFAULT_PLAYBOOKS[self.active_playbook_id]["title"]

        if isinstance(structured_params, dict):
            for k, v in structured_params.items():
                if v is not None:
                    base_params[k] = v

        self.active_structured_params = base_params
        self.compiled_rules = build_structured_playbook_rules(
            playbook_id=self.active_playbook_id,
            structured_params=self.active_structured_params,
            title=title,
        )
        return self.get_status()

    def set_aid_mode(self, mode: str, fallback_policy: Optional[str] = None) -> Dict[str, Any]:
        valid_modes = {"OFFLINE_DETERMINISTIC", "CLOUD_LLM_JEV", "ADVISORY_ONLY", "MANUAL_HUMAN_ONLY"}
        if mode in valid_modes:
            self.aid_mode = mode
        if fallback_policy in {"OFFLINE_DETERMINISTIC", "MANUAL_HUMAN_ONLY", "ADVISORY_ONLY"}:
            self.fallback_on_llm_unavailable = fallback_policy

        if self.aid_mode == "CLOUD_LLM_JEV":
            has_api = self.has_llm_api_key()
            if not has_api:
                self.requires_api_key_prompt = True
                self.circuit_breaker_tripped = True
                self.aid_mode = self.fallback_on_llm_unavailable
                self.circuit_breaker_reason = (
                    f"External LLM API Key required -> Prompting operator (safe fallback: {self.aid_mode})"
                )
            else:
                self.requires_api_key_prompt = False
                self.circuit_breaker_tripped = False
                storage_label = "Saved to Disk" if self.api_key_saved_on_disk else "Session Key"
                self.circuit_breaker_reason = (
                    f"External LLM JEV Active ({self.llm_provider}:{self.llm_model}, {storage_label}, <=1,200 ms guard)"
                )
        elif self.aid_mode == "MANUAL_HUMAN_ONLY":
            self.requires_api_key_prompt = False
            self.circuit_breaker_tripped = False
            self.circuit_breaker_reason = "AID Turned OFF by Operator (100% Manual Human Control)"
        else:
            self.requires_api_key_prompt = False
            self.circuit_breaker_tripped = False
            self.proposed_state_history.clear()
            self.circuit_breaker_reason = f"Active Mode: {self.aid_mode} (<1 ms local execution)"

        return self.get_status()

    def _query_external_llm_api(
        self,
        telemetry: Dict[str, Any],
        timeout_s: float = 1.15,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Perform a bounded-latency (`<= 1.15 s`) HTTPS call to OpenAI or Anthropic using
        the configured API key to evaluate the active Natural-Language Playbook over
        current telemetry. Returns `(parsed_json_proposal, error_reason)`.
        """
        api_key = self._get_effective_api_key()
        if not api_key:
            return None, "No External LLM API Key configured"

        allowed_actions = [
            "CONTINUE_COOPERATIVE_SCAN",
            "LOCK_TARGET",
            "QUEUE_DROP",
            "EXECUTE_DROP",
            "RELEASE_SAFE_TARGET_RETURN_TO_SCAN",
            "RTB_LOW_BATTERY",
        ]
        sys_prompt = (
            "You are a deterministic SAR Drone JEV (Judge-Evaluate-Verify) Dispatcher. "
            "Follow the active Natural-Language Operations Playbook strictly. "
            "Respond ONLY with a single JSON object containing keys: "
            f'"action" (one of {allowed_actions}), "params" (object with optional target_type, '
            'altitude_agl_m, offset_m), "judge_assessment" (short string), and "evaluate_clause" (short string).'
        )
        user_prompt = json.dumps(
            {
                "structured_playbook": asdict(self.compiled_rules),
                "telemetry": telemetry,
            }
        )

        try:
            if self.llm_provider == "anthropic":
                url = "https://api.anthropic.com/v1/messages"
                body = json.dumps(
                    {
                        "model": self.llm_model or "claude-sonnet-4-6",
                        "max_tokens": 180,
                        "temperature": 0.0,
                        "system": sys_prompt,
                        "messages": [{"role": "user", "content": user_prompt}],
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                blocks = raw.get("content", [])
                txt = blocks[0].get("text", "{}") if blocks else "{}"
            else:
                url = "https://api.openai.com/v1/chat/completions"
                body = json.dumps(
                    {
                        "model": self.llm_model or "gpt-5.4-mini",
                        "temperature": 0.0,
                        "max_tokens": 180,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                choices = raw.get("choices", [])
                txt = choices[0].get("message", {}).get("content", "{}") if choices else "{}"

            parsed = json.loads(txt.strip())
            act = str(parsed.get("action", "")).upper().strip()
            if act not in allowed_actions:
                return None, f"LLM returned unsupported action '{act}'"
            return parsed, None
        except Exception as exc:
            return None, f"{type(exc).__name__}: {str(exc)[:120]}"

    def _record_and_check_thrashing(self, proposed_action: str, now_ts: float) -> Tuple[bool, int]:
        """
        [RT1-03 Fix] Count PROPOSED semantic state flips in the last 15.0 seconds BEFORE
        dwell filtering (`N_15(t) = sum 1[q_k != q_{k-1}]`).
        If `N_15(t) >= 3`, trip the thrash circuit-breaker!
        """
        self.proposed_state_history = [(ts, act) for (ts, act) in self.proposed_state_history if (now_ts - ts) <= 15.0]
        self.proposed_state_history.append((now_ts, proposed_action))
        flips = 0
        for idx in range(1, len(self.proposed_state_history)):
            if self.proposed_state_history[idx][1] != self.proposed_state_history[idx - 1][1]:
                flips += 1
        return flips >= 3, flips

    def evaluate_jev_step(self, telemetry: Dict[str, Any], now_ts: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes one complete JEV (Judge -> Evaluate -> Verify) cycle over the current
        mission telemetry and returns the verified decision + rationale.
        """
        t0 = time.perf_counter()
        now = time.time() if now_ts is None else now_ts
        req_epoch = telemetry.get("request_epoch", self.veto_registry.current_epoch)

        # If AID is turned OFF (`MANUAL_HUMAN_ONLY`), immediately return no-op
        if self.aid_mode == "MANUAL_HUMAN_ONLY":
            return {
                "aid_mode": self.aid_mode,
                "epoch_id": self.veto_registry.current_epoch,
                "executed": False,
                "action": "NO_OP_MANUAL_MODE",
                "judge_assessment": "AID is turned OFF (Manual Human Operator Mode).",
                "evaluate_clause": "None — Human has 100% direct control.",
                "verify_gate": {"approved": False, "invariant_checks": ["AID_OFF: Manual Human Control"]},
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # Check simulated or real LLM link health if in CLOUD_LLM_JEV mode
        sim_llm_offline = bool(telemetry.get("simulate_llm_offline", False))
        sim_llm_latency_ms = float(telemetry.get("simulate_llm_latency_ms", 0.0))
        invoke_live_llm = bool(telemetry.get("invoke_live_llm", False))
        live_llm_proposal: Optional[Dict[str, Any]] = None
        live_llm_err: Optional[str] = None
        if self.aid_mode == "CLOUD_LLM_JEV" and invoke_live_llm and not sim_llm_offline and sim_llm_latency_ms <= 1200.0:
            live_llm_proposal, live_llm_err = self._query_external_llm_api(telemetry, timeout_s=1.15)
            if live_llm_err is not None:
                sim_llm_offline = True

        if self.aid_mode == "CLOUD_LLM_JEV" and (sim_llm_offline or sim_llm_latency_ms > 1200.0):
            self.circuit_breaker_tripped = True
            prev_mode = self.aid_mode
            self.aid_mode = self.fallback_on_llm_unavailable
            self.veto_registry.bump_epoch(reason="AID Latency/Offline Circuit-Breaker")
            if "request_epoch" not in telemetry:
                req_epoch = self.veto_registry.current_epoch
            err_detail = f" ({live_llm_err})" if live_llm_err else f" (offline or latency {sim_llm_latency_ms:.0f}ms > 1200ms)"
            self.circuit_breaker_reason = (
                f"AID Circuit-Breaker Tripped{err_detail} -> Downgraded from {prev_mode} to {self.aid_mode}"
            )
            if self.aid_mode == "MANUAL_HUMAN_ONLY":
                return {
                    "aid_mode": self.aid_mode,
                    "epoch_id": self.veto_registry.current_epoch,
                    "circuit_breaker_tripped": True,
                    "circuit_breaker_reason": self.circuit_breaker_reason,
                    "executed": False,
                    "action": "AID_AUTO_SHUTOFF",
                    "judge_assessment": self.circuit_breaker_reason,
                    "evaluate_clause": "Circuit-breaker turned off AID to prevent degraded autonomy.",
                    "verify_gate": {"approved": False, "invariant_checks": ["CIRCUIT_BREAKER_SHUTOFF"]},
                    "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }

        rules = self.compiled_rules
        batt_pct = float(telemetry.get("battery_pct", 84.0))
        person_conf = float(telemetry.get("person_confidence", 0.94))
        vehicle_conf = float(telemetry.get("vehicle_confidence", 0.89))
        person_safe = bool(telemetry.get("person_at_shelter", False))
        vehicle_safe = bool(telemetry.get("vehicle_at_road", False))
        target_lock_active = bool(telemetry.get("target_lock_active", True))
        current_target_type = str(telemetry.get("guided_target_type", "PERSON")).upper()
        dist_to_target_m = float(telemetry.get("drone1_dist_to_target_m", 18.0))
        drop_status = str(telemetry.get("drop_status", "READY")).upper()

        # STAGE 1: JUDGE & STAGE 2: EVALUATE
        candidate_action = "CONTINUE_COOPERATIVE_SCAN"
        candidate_params: Dict[str, Any] = {
            "altitude_agl_m": rules.search_altitude_agl_m,
            "overlap_pct": rules.sector_overlap_pct,
        }
        judge_text = f"Fleet scanning at {rules.search_altitude_agl_m:.0f}m AGL ({rules.sector_overlap_pct:.0f}% overlap)."
        clause_text = "Search Allocation Clause: Maintain disjoint sector scan."

        dynamic_rth_pct, _ = compute_arctic_wind_adjusted_rth_floor_pct(
            base_floor_pct=rules.rth_battery_floor_pct,
            dist_home_m=float(telemetry.get("dist_home_m", 450.0)),
            wind_speed_ms=float(telemetry.get("wind_speed_ms", 4.0)),
            temp_c=float(telemetry.get("temp_c", -12.0)),
        )

        if batt_pct < dynamic_rth_pct:
            candidate_action = "RTB_LOW_BATTERY"
            candidate_params = {"altitude_agl_m": max(35.0, rules.search_altitude_agl_m)}
            judge_text = f"Battery {batt_pct:.1f}% below Arctic wind/cold RTH floor ({dynamic_rth_pct:.1f}%)."
            clause_text = f"Safety Clause: Trigger RTH when battery < {dynamic_rth_pct:.1f}%."

        elif target_lock_active and (
            (current_target_type == "PERSON" and person_safe)
            or (current_target_type == "VEHICLE" and vehicle_safe)
        ):
            if rules.return_to_scan_on_shelter_arrival:
                candidate_action = "RELEASE_SAFE_TARGET_RETURN_TO_SCAN"
                candidate_params = {"target_type": current_target_type, "altitude_agl_m": rules.search_altitude_agl_m}
                judge_text = f"Guided {current_target_type} reached safe shelter/roadhead."
                clause_text = "Shelter Escort Clause: Release target lock upon safe arrival and return to 4-sector scan."

        elif not target_lock_active:
            want_veh = rules.preempt_on_vehicle and vehicle_conf >= rules.min_detection_confidence and not vehicle_safe
            want_per = rules.preempt_on_person and person_conf >= rules.min_detection_confidence and not person_safe
            per_x = telemetry.get("person_x_m", telemetry.get("target_x_m", 40.0))
            per_y = telemetry.get("person_y_m", telemetry.get("target_y_m", -45.0))
            veh_x = telemetry.get("vehicle_x_m", telemetry.get("target_x_m", -165.0))
            veh_y = telemetry.get("vehicle_y_m", telemetry.get("target_y_m", -92.0))

            if rules.preferred_target_type == "VEHICLE" and want_veh:
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "VEHICLE",
                    "target_x_m": veh_x,
                    "target_y_m": veh_y,
                    "altitude_agl_m": rules.tracking_altitude_agl_m,
                }
                judge_text = f"Stranded vehicle detected (conf {vehicle_conf*100:.0f}% >= {rules.min_detection_confidence*100:.0f}%)."
                clause_text = f"Target Preemption Clause: Lock vehicle at {rules.tracking_altitude_agl_m:.0f}m AGL; 3 drones scan."
            elif want_per:
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "PERSON",
                    "target_x_m": per_x,
                    "target_y_m": per_y,
                    "altitude_agl_m": rules.tracking_altitude_agl_m,
                }
                judge_text = f"Lost hiker thermal signature detected (conf {person_conf*100:.0f}% >= {rules.min_detection_confidence*100:.0f}%)."
                clause_text = f"Target Preemption Clause: Assign Drone 1 to lock person at {rules.tracking_altitude_agl_m:.0f}m AGL."
            elif want_veh:
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "VEHICLE",
                    "target_x_m": veh_x,
                    "target_y_m": veh_y,
                    "altitude_agl_m": rules.tracking_altitude_agl_m,
                }
                judge_text = f"Vehicle thermal signature detected (conf {vehicle_conf*100:.0f}%)."
                clause_text = f"Target Preemption Clause: Assign Drone 1 to lock vehicle at {rules.tracking_altitude_agl_m:.0f}m AGL."

        elif target_lock_active and dist_to_target_m <= rules.drop_trigger_distance_m:
            if drop_status == "READY" and rules.auto_queue_drop:
                candidate_action = "QUEUE_DROP"
                candidate_params = {
                    "target_type": current_target_type,
                    "offset_m": rules.drop_offset_m,
                    "altitude_agl_m": rules.tracking_altitude_agl_m,
                }
                judge_text = f"Drone 1 within {dist_to_target_m:.1f}m of {current_target_type}; payload is READY."
                clause_text = (
                    f"Payload Drop Clause: Queue +42°C rescue cask at {rules.drop_offset_m:.0f}m safe offset "
                    f"({'auto-release' if rules.auto_release_drop else 'await human confirmation'})."
                )
            elif drop_status == "PENDING" and rules.auto_release_drop and not rules.require_human_drop_confirm:
                candidate_action = "EXECUTE_DROP"
                candidate_params = {
                    "target_type": current_target_type,
                    "offset_m": rules.drop_offset_m,
                    "altitude_agl_m": rules.tracking_altitude_agl_m,
                }
                judge_text = f"Pending drop stabilized at {rules.drop_offset_m:.0f}m offset from {current_target_type}."
                clause_text = "Payload Drop Clause: Auto-release rescue cask (Ch9 = 1900 µs)."

        # If live External LLM proposal succeeded within <=1.15s, apply its candidate proposal
        # (still strictly gated by Stage 3 Verify below!)
        if live_llm_proposal is not None:
            candidate_action = str(live_llm_proposal.get("action", candidate_action)).upper().strip()
            llm_params = live_llm_proposal.get("params")
            if isinstance(llm_params, dict):
                candidate_params.update(llm_params)
            judge_text = str(live_llm_proposal.get("judge_assessment", judge_text))[:180]
            clause_text = str(live_llm_proposal.get("evaluate_clause", clause_text))[:180]

        # [RT1-03 Fix] Check Pre-Filter Proposed State-Flip Thrashing (`N_15(t) >= 3`)
        proposed_override = telemetry.get("forced_llm_proposed_action")
        if proposed_override:
            candidate_action = str(proposed_override)
        thrash_tripped, flip_count = self._record_and_check_thrashing(candidate_action, now)
        if thrash_tripped:
            self.circuit_breaker_tripped = True
            self.aid_mode = "MANUAL_HUMAN_ONLY"
            self.veto_registry.bump_epoch(reason=f"AID Thrash Breaker ({flip_count} flips in 15s)")
            self.circuit_breaker_reason = (
                f"AID Thrash Circuit-Breaker Tripped ({flip_count} state flips in <=15s) -> "
                "Latched MANUAL_HUMAN_ONLY (Bumpless Hold)"
            )
            return {
                "aid_mode": self.aid_mode,
                "epoch_id": self.veto_registry.current_epoch,
                "circuit_breaker_tripped": True,
                "circuit_breaker_reason": self.circuit_breaker_reason,
                "executed": False,
                "action": "AID_THRASH_SHUTOFF",
                "judge_assessment": self.circuit_breaker_reason,
                "evaluate_clause": "Thrash protection latched manual control.",
                "verify_gate": {"approved": False, "invariant_checks": [f"FAIL: Thrash Breaker ({flip_count} flips/15s)"]},
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # STAGE 3: VERIFY (Formal Physical & Human-Authority Safety Gate)
        verify_res = verify_action_safety_gate(
            action_type=candidate_action,
            params=candidate_params,
            telemetry=telemetry,
            compiled_rules=rules,
            veto_registry=self.veto_registry,
            request_epoch=req_epoch,
            now_ts=now,
        )

        # [RT1-03 & RT2-03] Enforce 8.0s Dwell Gate on non-emergency state transitions (`None` safe on first transition)
        if (
            verify_res.approved
            and candidate_action != self.last_accepted_state
            and candidate_action not in ("RTB_LOW_BATTERY", "CONTINUE_COOPERATIVE_SCAN")
            and self.last_accepted_transition_ts is not None
            and (now - self.last_accepted_transition_ts) < rules.min_dwell_s
        ):
            dwell_rem = round(rules.min_dwell_s - (now - self.last_accepted_transition_ts), 1)
            verify_res.approved = False
            verify_res.rejection_reason = f"DWELL_HYSTERESIS_HOLD: {dwell_rem}s remaining before state change allowed."
            verify_res.invariant_checks.append(f"HOLD: 8.0s Dwell Gate ({dwell_rem}s left)")

        if verify_res.approved and candidate_action != self.last_accepted_state:
            self.last_accepted_state = candidate_action
            self.last_accepted_transition_ts = now

        is_advisory = self.aid_mode == "ADVISORY_ONLY"
        executed = verify_res.approved and not is_advisory and candidate_action != "CONTINUE_COOPERATIVE_SCAN"

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        record = {
            "timestamp": round(now, 2),
            "epoch_id": self.veto_registry.current_epoch,
            "aid_mode": self.aid_mode,
            "playbook_id": self.active_playbook_id,
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "circuit_breaker_reason": self.circuit_breaker_reason,
            "action": candidate_action if verify_res.approved else f"BLOCKED_{candidate_action}",
            "candidate_action": candidate_action,
            "params": verify_res.modified_params,
            "executed": executed,
            "advisory_only": is_advisory,
            "judge_assessment": judge_text,
            "evaluate_clause": clause_text,
            "verify_gate": asdict(verify_res),
            "latency_ms": elapsed_ms,
        }
        self.decision_log.append(record)
        if len(self.decision_log) > 40:
            self.decision_log = self.decision_log[-40:]
        return record

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_playbook_id": self.active_playbook_id,
            "structured_params": dict(self.active_structured_params),
            "compiled_rules": asdict(self.compiled_rules),
            "aid_mode": self.aid_mode,
            "epoch_id": self.veto_registry.current_epoch,
            "fallback_on_llm_unavailable": self.fallback_on_llm_unavailable,
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "circuit_breaker_reason": self.circuit_breaker_reason,
            "llm_api_key_configured": self.has_llm_api_key(),
            "llm_api_key_masked": self.get_masked_api_key(),
            "llm_api_key_saved_on_disk": self.api_key_saved_on_disk,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "requires_api_key_prompt": self.requires_api_key_prompt,
            "human_vetoes": {
                "epoch_id": self.veto_registry.current_epoch,
                "active_bubbles": [asdict(b) for b in self.veto_registry.bubbles],
                "target_veto_until_ts": self.veto_registry.target_veto_until_ts,
                "drop_veto_latched": self.veto_registry.drop_veto_latched,
                "last_human_action_desc": self.veto_registry.last_human_action_desc,
            },
            "available_playbooks": [
                {
                    "id": k,
                    "title": v["title"],
                    "summary": v["summary"],
                    "structured_params": v["structured_params"],
                }
                for k, v in DEFAULT_PLAYBOOKS.items()
            ],
            "recent_decisions": self.decision_log[-5:],
        }


GLOBAL_PLAYBOOK_DISPATCHER = PlaybookAgentDispatcher()


if __name__ == "__main__":
    disp = PlaybookAgentDispatcher()
    print("[+] Compiled Playbook Rules (SHA-256:", disp.compiled_rules.raw_markdown_sha256, "):")
    print("    Search Alt:", disp.compiled_rules.search_altitude_agl_m, "m | Track Alt:", disp.compiled_rules.tracking_altitude_agl_m, "m | Drop Offset:", disp.compiled_rules.drop_offset_m, "m")
    # Verify spatial bubble: cancel target at (40, -45), test track churn at (45, -42) vs second hiker at (350, 200)
    disp.veto_registry.record_human_target_cancel("PERSON", cooldown_s=300, x_m=40.0, y_m=-45.0)
    churn_step = disp.evaluate_jev_step({"target_lock_active": False, "person_confidence": 0.94, "target_x_m": 45.0, "target_y_m": -42.0}, now_ts=time.time() + 10.0)
    second_hiker_step = disp.evaluate_jev_step({"target_lock_active": False, "person_confidence": 0.94, "target_x_m": 350.0, "target_y_m": 200.0}, now_ts=time.time() + 20.0)
    print("[+] Respawned Track at (45,-42) ->", churn_step["action"], "| Reason:", churn_step["verify_gate"]["rejection_reason"])
    print("[+] Second Hiker 300m away at (350,200) ->", second_hiker_step["action"], "| Approved:", second_hiker_step["verify_gate"]["approved"])
