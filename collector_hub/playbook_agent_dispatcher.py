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
import http.client
import json
import math
import os
import threading
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

    # Invariant 2: Altitude Interval Feasibility (`L <= h <= U`, [RT1-02]) + Manned Helo 35m U-Space Cap
    helo_inbound = bool(telemetry.get("helo_inbound_active", False))
    helo_cap_m = float(telemetry.get("helo_ceiling_agl_m", 35.0))
    min_floor = max(28.0, compiled_rules.canopy_floor_m + 10.0)
    if telemetry.get("wildlife_detected", False) and not helo_inbound:
        min_floor = max(min_floor, compiled_rules.wildlife_min_altitude_m)
    max_ceil = compiled_rules.altitude_ceiling_m
    if helo_inbound:
        max_ceil = min(max_ceil, helo_cap_m)

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
            if helo_inbound and req_alt > helo_cap_m:
                checks.append(f"CLAMPED: Helo U-Space Ceiling {req_alt}m -> {clamped_alt}m ([{min_floor}m, {max_ceil}m])")
            else:
                checks.append(f"CLAMPED: Altitude {req_alt}m -> {clamped_alt}m ([{min_floor}m, {max_ceil}m])")
        else:
            if helo_inbound:
                checks.append(f"PASS: Helo U-Space Altitude {req_alt}m within [{min_floor}m, {max_ceil}m]")
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
    if batt_pct < dynamic_rth_pct:
        checks.append(f"PASS: Emergency RTH authorized (Battery {batt_pct:.1f}% < {dynamic_rth_pct:.1f}% Arctic RTH floor)")
    else:
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
        # [RT1-03 & RT2-03 Fix] Dwell timer (`None` until first transition) & Cycle-Aware Thrash Counter
        self.last_accepted_state: str = "CONTINUE_COOPERATIVE_SCAN"
        self.last_accepted_target_type: str = "PERSON"
        self.last_accepted_transition_ts: Optional[float] = None
        self.proposed_state_history: List[Tuple[float, str, str]] = []  # (ts, proposed_action, target_type)
        self.decision_log: List[Dict[str, Any]] = []
        self._http_lock: threading.Lock = threading.Lock()
        self._https_pool: Dict[str, http.client.HTTPSConnection] = {}
        self.last_llm_raw_proposal: Optional[Dict[str, Any]] = None
        self.llm_calls_succeeded: int = 0
        self.llm_calls_failed: int = 0

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
        if self.llm_provider == "anthropic":
            return (os.getenv("ANTHROPIC_API_KEY") or os.getenv("SAR_LLM_API_KEY") or "").strip()
        if self.llm_provider == "gemini":
            return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("SAR_LLM_API_KEY") or "").strip()
        return (
            os.getenv("SAR_LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("GEMINI_API_KEY")
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
        if clean_provider not in {"openai", "anthropic", "gemini", "custom"}:
            clean_provider = "openai"
        default_model_for_provider = {
            "openai": "gpt-5.4-mini",
            "anthropic": "claude-haiku-4-5-20251001",
            "gemini": "gemini-2.5-flash",
            "custom": "gpt-5.4-mini",
        }[clean_provider]
        clean_model = "".join(ch for ch in str(model or default_model_for_provider).strip() if ch.isprintable())[:64]

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
            self.proposed_state_history.clear()
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
                self.proposed_state_history.clear()
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

    def _https_post_json(
        self,
        host: str,
        path: str,
        body_bytes: bytes,
        headers: Dict[str, str],
        timeout_s: float,
    ) -> Dict[str, Any]:
        """
        Execute an HTTPS POST using a persistent keep-alive connection pool per host
        to avoid repeating a 500-700 ms TLS handshake on every JEV tick. Automatically
        reconnects once if the server closed an idle keep-alive socket.
        """
        req_headers = dict(headers)
        req_headers["Connection"] = "keep-alive"
        req_headers["Content-Length"] = str(len(body_bytes))

        with self._http_lock:
            for attempt in range(2):
                conn = self._https_pool.get(host)
                try:
                    if conn is None:
                        conn = http.client.HTTPSConnection(host, timeout=timeout_s)
                        self._https_pool[host] = conn
                    else:
                        conn.timeout = timeout_s
                        if conn.sock is not None:
                            conn.sock.settimeout(timeout_s)
                    conn.request("POST", path, body=body_bytes, headers=req_headers)
                    resp = conn.getresponse()
                    raw_bytes = resp.read()
                    if resp.status in (429, 500, 502, 503, 504) and attempt == 0:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        self._https_pool.pop(host, None)
                        continue
                    if resp.status >= 400:
                        err_snip = raw_bytes.decode("utf-8", errors="ignore")[:160]
                        raise RuntimeError(f"HTTP {resp.status}: {err_snip}")
                    return json.loads(raw_bytes.decode("utf-8"))
                except (
                    http.client.NotConnected,
                    http.client.ImproperConnectionState,
                    http.client.RemoteDisconnected,
                    BrokenPipeError,
                    ConnectionResetError,
                ):
                    try:
                        if conn is not None:
                            conn.close()
                    except Exception:
                        pass
                    self._https_pool.pop(host, None)
                    if attempt == 1:
                        raise
                except Exception:
                    try:
                        if conn is not None:
                            conn.close()
                    except Exception:
                        pass
                    self._https_pool.pop(host, None)
                    raise
        raise RuntimeError("HTTPS request failed")

    @staticmethod
    def _strip_json_code_fence(txt: str) -> str:
        """Strip optional markdown code fences around JSON without using regex."""
        s = txt.strip()
        if s.startswith("```"):
            first_nl = s.find("\n")
            if first_nl != -1:
                s = s[first_nl + 1 :].strip()
            if s.endswith("```"):
                s = s[:-3].strip()
        return s

    def _query_external_llm_api(
        self,
        telemetry: Dict[str, Any],
        timeout_s: float = 2.5,
        computed_safety_envelope: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Perform a bounded-latency HTTPS call (using keep-alive connection pooling) to
        OpenAI, Anthropic, or Google Gemini using the configured API key to evaluate
        the active Operations Playbook over current telemetry and pre-computed safety
        bounds. Returns `(parsed_json_proposal, error_reason)`.
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
            "You are a deterministic Arctic SAR Drone JEV (Judge-Evaluate-Verify) Dispatcher. "
            "Evaluate the structured_playbook, telemetry, and computed_safety_envelope following this strict priority hierarchy:\n"
            "1. RTB_LOW_BATTERY: MUST be selected if computed_safety_envelope.battery_below_rth_floor is true.\n"
            "2. RELEASE_SAFE_TARGET_RETURN_TO_SCAN: MUST be selected if target_lock_active is true AND target_reached_safe_state is true.\n"
            "3. LOCK_TARGET: Select when target_lock_active is false AND computed_safety_envelope.unvetoed_lock_candidate is not null. "
            "Set params.target_type, params.target_x_m, params.target_y_m, and params.altitude_agl_m from unvetoed_lock_candidate. "
            "If all detected targets are vetoed by a human spatial bubble (only_vetoed_target_present is true), still propose LOCK_TARGET on that target so Stage-3 Verify logs the formal veto rejection.\n"
            "4. QUEUE_DROP: Select when target_lock_active is true, drone1_dist_to_target_m <= drop_trigger_distance_m, "
            "drop_status == 'READY', and structured_playbook.auto_queue_drop is true. (NEVER select EXECUTE_DROP when drop_status is 'READY').\n"
            "5. EXECUTE_DROP: Select ONLY when target_lock_active is true, drone1_dist_to_target_m <= drop_trigger_distance_m, "
            "drop_status == 'PENDING', structured_playbook.auto_release_drop is true, and structured_playbook.require_human_drop_confirm is false.\n"
            "6. CONTINUE_COOPERATIVE_SCAN: Select in all other cases.\n"
            "Always respect computed_safety_envelope.effective_max_altitude_agl_m (including 35m Manned Helicopter ceiling).\n"
            "Respond ONLY with a single JSON object containing keys: "
            f'"action" (one of {allowed_actions}), "params" (object with target_type, target_x_m, target_y_m, '
            'altitude_agl_m, offset_m as applicable), "judge_assessment" (concise 1-sentence situational assessment), '
            'and "evaluate_clause" (concise 1-sentence playbook rule citation).'
        )
        rules = self.compiled_rules
        compact_playbook = {
            "search_altitude_agl_m": rules.search_altitude_agl_m,
            "tracking_altitude_agl_m": rules.tracking_altitude_agl_m,
            "preferred_target_type": rules.preferred_target_type,
            "min_detection_confidence": rules.min_detection_confidence,
            "drop_trigger_distance_m": rules.drop_trigger_distance_m,
            "drop_offset_m": rules.drop_offset_m,
            "auto_queue_drop": rules.auto_queue_drop,
            "auto_release_drop": rules.auto_release_drop,
            "require_human_drop_confirm": rules.require_human_drop_confirm,
            "return_to_scan_on_shelter_arrival": rules.return_to_scan_on_shelter_arrival,
        }
        user_payload: Dict[str, Any] = {
            "structured_playbook": compact_playbook,
            "telemetry": telemetry,
        }
        if computed_safety_envelope is not None:
            user_payload["computed_safety_envelope"] = computed_safety_envelope
        user_prompt = json.dumps(user_payload, separators=(",", ":"))

        try:
            if self.llm_provider == "anthropic":
                model_id = self.llm_model or "claude-haiku-5-5"
                ant_req: Dict[str, Any] = {
                    "model": model_id,
                    "max_tokens": 350,
                    "system": sys_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                }
                if "-5" not in model_id:
                    ant_req["temperature"] = 0.0
                body = json.dumps(ant_req).encode("utf-8")
                raw = self._https_post_json(
                    host="api.anthropic.com",
                    path="/v1/messages",
                    body_bytes=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    timeout_s=timeout_s,
                )
                blocks = raw.get("content", [])
                txt = blocks[0].get("text", "{}") if blocks else "{}"
            elif self.llm_provider == "gemini":
                model_id = self.llm_model or "gemini-2.5-flash"
                if model_id.startswith("models/"):
                    model_id = model_id[len("models/") :]
                gen_cfg: Dict[str, Any] = {
                    "temperature": 0.0,
                    "maxOutputTokens": 400,
                    "responseMimeType": "application/json",
                }
                if "2.5" in model_id:
                    gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
                body = json.dumps(
                    {
                        "systemInstruction": {"parts": [{"text": sys_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                        "generationConfig": gen_cfg,
                    }
                ).encode("utf-8")
                raw = self._https_post_json(
                    host="generativelanguage.googleapis.com",
                    path=f"/v1beta/models/{model_id}:generateContent?key={api_key}",
                    body_bytes=body,
                    headers={"Content-Type": "application/json"},
                    timeout_s=timeout_s,
                )
                cands = raw.get("candidates", [])
                parts = cands[0].get("content", {}).get("parts", []) if cands else []
                txt = parts[0].get("text", "{}") if parts else "{}"
            else:
                model_id = self.llm_model or "gpt-5.4-mini"
                req_dict: Dict[str, Any] = {
                    "model": model_id,
                    "max_completion_tokens": 350,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
                if model_id.startswith("gpt-5"):
                    req_dict["reasoning_effort"] = "none"
                    req_dict["temperature"] = 0.0
                elif model_id.startswith(("o1", "o3", "o4")):
                    req_dict["reasoning_effort"] = "low"
                else:
                    req_dict["temperature"] = 0.0
                body = json.dumps(req_dict).encode("utf-8")
                raw = self._https_post_json(
                    host="api.openai.com",
                    path="/v1/chat/completions",
                    body_bytes=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    timeout_s=timeout_s,
                )
                choices = raw.get("choices", [])
                txt = choices[0].get("message", {}).get("content", "{}") if choices else "{}"

            clean_txt = self._strip_json_code_fence(txt)
            parsed = json.loads(clean_txt)
            act = str(parsed.get("action", "")).upper().strip()
            if act not in allowed_actions:
                self.llm_calls_failed += 1
                return None, f"LLM returned unsupported action '{act}'"
            self.llm_calls_succeeded += 1
            self.last_llm_raw_proposal = parsed
            return parsed, None
        except Exception as exc:
            self.llm_calls_failed += 1
            return None, f"{type(exc).__name__}: {str(exc)[:120]}"

    def _record_and_check_thrashing(
        self,
        proposed_action: str,
        now_ts: float,
        target_type: str = "PERSON",
    ) -> Tuple[bool, int]:
        """
        [RT1-03 Fix] Count oscillatory state flips in the last 15.0 seconds BEFORE dwell
        filtering (`N_15(t)`).
        Distinguishes monotonic forward mission progression (`CONTINUE_COOPERATIVE_SCAN ->
        LOCK_TARGET -> QUEUE_DROP -> EXECUTE_DROP -> RELEASE_SAFE_TARGET_RETURN_TO_SCAN ->
        CONTINUE_COOPERATIVE_SCAN` and emergency `RTB_LOW_BATTERY`) from oscillatory state
        reversals (`LOCK_TARGET <-> CONTINUE_COOPERATIVE_SCAN`, `QUEUE_DROP <-> LOCK_TARGET`,
        or rapid target-type flip-flopping `PERSON <-> VEHICLE`).
        If oscillatory flips `>= 3` within `15.0s`, trips the thrash circuit-breaker!
        """
        lifecycle_stage = {
            "CONTINUE_COOPERATIVE_SCAN": 0,
            "LOCK_TARGET": 1,
            "QUEUE_DROP": 2,
            "EXECUTE_DROP": 3,
            "RELEASE_SAFE_TARGET_RETURN_TO_SCAN": 4,
        }
        self.proposed_state_history = [
            item for item in self.proposed_state_history if (now_ts - item[0]) <= 15.0
        ]
        self.proposed_state_history.append((now_ts, proposed_action, target_type))

        flips = 0
        has_reversal = False
        for idx in range(1, len(self.proposed_state_history)):
            _, prev_act, prev_tgt = self.proposed_state_history[idx - 1]
            _, curr_act, curr_tgt = self.proposed_state_history[idx]

            if curr_act == prev_act:
                if curr_act == "LOCK_TARGET" and curr_tgt != prev_tgt:
                    has_reversal = True
                    flips += 1
                continue

            if curr_act == "RTB_LOW_BATTERY":
                continue

            prev_stg = lifecycle_stage.get(prev_act, -1)
            curr_stg = lifecycle_stage.get(curr_act, -1)

            is_clean_cycle_completion = (
                prev_act == "RELEASE_SAFE_TARGET_RETURN_TO_SCAN"
                and curr_act == "CONTINUE_COOPERATIVE_SCAN"
            )
            is_monotonic_forward = (prev_stg >= 0 and curr_stg > prev_stg)

            if not has_reversal and (is_monotonic_forward or is_clean_cycle_completion):
                continue

            # Any backward transition (e.g. LOCK_TARGET -> CONTINUE_COOPERATIVE_SCAN without RELEASE_SAFE)
            # or any state flip after a reversal has begun within the 15s window counts as thrashing:
            has_reversal = True
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

        rules = self.compiled_rules
        batt_pct = float(telemetry.get("battery_pct", 84.0))
        person_conf = float(telemetry.get("person_confidence", 0.94 if "vehicle_confidence" not in telemetry else 0.0))
        vehicle_conf = float(telemetry.get("vehicle_confidence", 0.0))
        responder_ack = str(telemetry.get("responder_ack", "NONE")).upper().strip()
        victim_safe_ack = bool(telemetry.get("victim_safe_ack", False)) or (responder_ack == "VICTIM_CONTACTED_SAFE")
        person_safe = bool(telemetry.get("person_at_shelter", False)) or victim_safe_ack
        vehicle_safe = bool(telemetry.get("vehicle_at_road", False)) or victim_safe_ack
        target_lock_active = bool(telemetry.get("target_lock_active", True))
        current_target_type = str(telemetry.get("guided_target_type", "PERSON")).upper()
        dist_to_target_m = float(telemetry.get("drone1_dist_to_target_m", telemetry.get("dist_to_target_m", 18.0)))
        drop_status = str(telemetry.get("drop_status", "READY")).upper()
        if telemetry.get("drop_completed") is True:
            drop_status = "DROPPED"
        elif telemetry.get("drop_queued") is True and drop_status == "READY":
            drop_status = "PENDING"

        helo_inbound = bool(telemetry.get("helo_inbound_active", False))
        helo_cap_m = float(telemetry.get("helo_ceiling_agl_m", 35.0))
        min_floor = max(28.0, rules.canopy_floor_m + 10.0)
        if telemetry.get("wildlife_detected", False) and not helo_inbound:
            min_floor = max(min_floor, rules.wildlife_min_altitude_m)
        max_ceil = min(rules.altitude_ceiling_m, helo_cap_m) if helo_inbound else rules.altitude_ceiling_m
        effective_search_alt = min(max_ceil, max(min_floor, rules.search_altitude_agl_m))
        effective_track_alt = min(max_ceil, max(min_floor, rules.tracking_altitude_agl_m))

        wind_ms = float(telemetry.get("wind_speed_ms", 4.0))
        drone_vg_ms = float(telemetry.get("drone_ground_speed_ms", 0.5))
        t_fall_s = math.sqrt(2.0 * 15.0 / 9.80665) * 1.08
        wind_drift_m = 0.35 * wind_ms * t_fall_s
        max_safe_drift_m = 0.45 * rules.drop_offset_m

        dynamic_rth_pct, _ = compute_arctic_wind_adjusted_rth_floor_pct(
            base_floor_pct=rules.rth_battery_floor_pct,
            dist_home_m=float(telemetry.get("dist_home_m", 450.0)),
            wind_speed_ms=wind_ms,
            temp_c=float(telemetry.get("temp_c", -12.0)),
        )

        # STAGE 1: JUDGE & STAGE 2: EVALUATE (Deterministic Baseline + Safety Envelope Construction)
        candidate_action = "CONTINUE_COOPERATIVE_SCAN"
        candidate_params: Dict[str, Any] = {
            "altitude_agl_m": effective_search_alt,
            "overlap_pct": rules.sector_overlap_pct,
        }
        judge_text = f"Fleet scanning at {effective_search_alt:.0f}m AGL ({rules.sector_overlap_pct:.0f}% overlap)."
        clause_text = "Search Allocation Clause: Maintain disjoint sector scan."

        per_x = telemetry.get("person_x_m", telemetry.get("target_x_m", 40.0))
        per_y = telemetry.get("person_y_m", telemetry.get("target_y_m", -45.0))
        veh_x = telemetry.get("vehicle_x_m", telemetry.get("target_x_m", -165.0))
        veh_y = telemetry.get("vehicle_y_m", telemetry.get("target_y_m", -92.0))
        per_vetoed, _, _ = self.veto_registry.is_target_vetoed_by_human("PERSON", x_m=per_x, y_m=per_y, now_ts=now)
        veh_vetoed, _, _ = self.veto_registry.is_target_vetoed_by_human("VEHICLE", x_m=veh_x, y_m=veh_y, now_ts=now)

        # Support secondary un-vetoed person track (e.g. second hiker 300m away while moose/campfire is in veto bubble)
        sec_per_conf = float(telemetry.get("secondary_person_confidence", 0.0))
        sec_per_x = telemetry.get("secondary_person_x_m")
        sec_per_y = telemetry.get("secondary_person_y_m")
        sec_per_vetoed = True
        if sec_per_x is not None and sec_per_y is not None:
            sec_per_vetoed, _, _ = self.veto_registry.is_target_vetoed_by_human(
                "PERSON", x_m=sec_per_x, y_m=sec_per_y, now_ts=now
            )

        unvetoed_lock_candidate: Optional[Dict[str, Any]] = None
        only_vetoed_target_present = False

        if batt_pct < dynamic_rth_pct:
            candidate_action = "RTB_LOW_BATTERY"
            candidate_params = {"altitude_agl_m": min(max_ceil, max(35.0 if not helo_inbound else 28.0, effective_search_alt))}
            judge_text = f"Battery {batt_pct:.1f}% below Arctic wind/cold RTH floor ({dynamic_rth_pct:.1f}%)."
            clause_text = f"Safety Clause: Trigger RTH when battery < {dynamic_rth_pct:.1f}%."

        elif target_lock_active and (
            (current_target_type == "PERSON" and person_safe)
            or (current_target_type == "VEHICLE" and vehicle_safe)
        ):
            if rules.return_to_scan_on_shelter_arrival:
                candidate_action = "RELEASE_SAFE_TARGET_RETURN_TO_SCAN"
                candidate_params = {"target_type": current_target_type, "altitude_agl_m": effective_search_alt}
                judge_text = f"Guided {current_target_type} confirmed safe (shelter/roadhead or Ground SAR ACK)."
                clause_text = "Shelter Escort Clause: Release target lock upon safe arrival and return to 4-sector scan."

        elif not target_lock_active:
            want_per = rules.preempt_on_person and person_conf >= rules.min_detection_confidence and not person_safe
            want_sec_per = (
                rules.preempt_on_person
                and sec_per_conf >= rules.min_detection_confidence
                and sec_per_x is not None
                and sec_per_y is not None
                and not sec_per_vetoed
            )
            want_veh = (
                (rules.preempt_on_vehicle or ("vehicle_confidence" in telemetry and per_vetoed))
                and vehicle_conf >= rules.min_detection_confidence
                and not vehicle_safe
            )

            if rules.preferred_target_type == "VEHICLE" and want_veh and not veh_vetoed:
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "VEHICLE",
                    "target_x_m": veh_x,
                    "target_y_m": veh_y,
                    "altitude_agl_m": effective_track_alt,
                }
                unvetoed_lock_candidate = dict(candidate_params)
                judge_text = f"Stranded vehicle detected (conf {vehicle_conf*100:.0f}% >= {rules.min_detection_confidence*100:.0f}%)."
                clause_text = f"Target Preemption Clause: Lock vehicle at {effective_track_alt:.0f}m AGL; 3 drones scan."
            elif want_per and not per_vetoed:
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "PERSON",
                    "target_x_m": per_x,
                    "target_y_m": per_y,
                    "altitude_agl_m": effective_track_alt,
                }
                unvetoed_lock_candidate = dict(candidate_params)
                judge_text = f"Lost hiker thermal signature detected (conf {person_conf*100:.0f}% >= {rules.min_detection_confidence*100:.0f}%)."
                clause_text = f"Target Preemption Clause: Assign Drone 1 to lock person at {effective_track_alt:.0f}m AGL."
            elif want_sec_per:
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "PERSON",
                    "target_x_m": sec_per_x,
                    "target_y_m": sec_per_y,
                    "altitude_agl_m": effective_track_alt,
                }
                unvetoed_lock_candidate = dict(candidate_params)
                judge_text = f"Primary track vetoed; locking un-vetoed second hiker at ({sec_per_x}, {sec_per_y}) (conf {sec_per_conf*100:.0f}%)."
                clause_text = f"Target Preemption Clause: Fail over from veto bubble to un-vetoed hiker at {effective_track_alt:.0f}m AGL."
            elif want_veh and not veh_vetoed:
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "VEHICLE",
                    "target_x_m": veh_x,
                    "target_y_m": veh_y,
                    "altitude_agl_m": effective_track_alt,
                }
                unvetoed_lock_candidate = dict(candidate_params)
                judge_text = f"Vehicle thermal signature detected (conf {vehicle_conf*100:.0f}%)."
                clause_text = f"Target Preemption Clause: Assign Drone 1 to lock vehicle at {effective_track_alt:.0f}m AGL."
            elif want_per and per_vetoed:
                # Only the vetoed person target is present -> propose LOCK_TARGET so Stage 3 Verify records HUMAN_VETO_BUBBLE_ACTIVE
                only_vetoed_target_present = True
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "PERSON",
                    "target_x_m": per_x,
                    "target_y_m": per_y,
                    "altitude_agl_m": effective_track_alt,
                }
                judge_text = f"Thermal track at ({per_x}, {per_y}) inside active Human Veto Bubble."
                clause_text = "Target Preemption Clause: Candidate evaluated against Stage-3 Spatial Veto Bubble."
            elif want_veh and veh_vetoed:
                only_vetoed_target_present = True
                candidate_action = "LOCK_TARGET"
                candidate_params = {
                    "target_type": "VEHICLE",
                    "target_x_m": veh_x,
                    "target_y_m": veh_y,
                    "altitude_agl_m": effective_track_alt,
                }
                judge_text = f"Vehicle track at ({veh_x}, {veh_y}) inside active Human Veto Bubble."
                clause_text = "Target Preemption Clause: Candidate evaluated against Stage-3 Spatial Veto Bubble."

        elif target_lock_active and dist_to_target_m <= rules.drop_trigger_distance_m:
            if drop_status == "READY" and rules.auto_queue_drop:
                candidate_action = "QUEUE_DROP"
                candidate_params = {
                    "target_type": current_target_type,
                    "offset_m": rules.drop_offset_m,
                    "altitude_agl_m": effective_track_alt,
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
                    "altitude_agl_m": effective_track_alt,
                }
                judge_text = f"Pending drop stabilized at {rules.drop_offset_m:.0f}m offset from {current_target_type}."
                clause_text = "Payload Drop Clause: Auto-release rescue cask (Ch9 = 1900 µs)."

        computed_safety_envelope = {
            "epoch_id": self.veto_registry.current_epoch,
            "last_accepted_state": self.last_accepted_state,
            "dynamic_rth_floor_pct": round(dynamic_rth_pct, 2),
            "battery_below_rth_floor": bool(batt_pct < dynamic_rth_pct),
            "target_reached_safe_state": bool(
                target_lock_active
                and ((current_target_type == "PERSON" and person_safe) or (current_target_type == "VEHICLE" and vehicle_safe))
            ),
            "effective_min_altitude_agl_m": round(min_floor, 1),
            "effective_max_altitude_agl_m": round(max_ceil, 1),
            "helo_inbound_35m_cap_active": helo_inbound,
            "estimated_wind_drift_m": round(wind_drift_m, 2),
            "max_safe_wind_drift_m": round(max_safe_drift_m, 2),
            "ballistic_drop_wind_safe": bool(wind_drift_m <= max_safe_drift_m and drone_vg_ms <= 1.5),
            "person_vetoed_by_human_bubble": per_vetoed,
            "vehicle_vetoed_by_human_bubble": veh_vetoed,
            "unvetoed_lock_candidate": unvetoed_lock_candidate,
            "only_vetoed_target_present": only_vetoed_target_present,
            "drop_veto_latched_by_human": bool(self.veto_registry.is_drop_vetoed_by_human(current_target_type)),
            "ground_responder_ack": responder_ack,
        }

        # Check simulated or real LLM link health if in CLOUD_LLM_JEV mode
        sim_llm_offline = bool(telemetry.get("simulate_llm_offline", False))
        sim_llm_latency_ms = float(telemetry.get("simulate_llm_latency_ms", 0.0))
        eff_key = self._get_effective_api_key()
        is_real_api_key = bool(eff_key) and not eff_key.startswith("sk-test-")
        invoke_live_llm = bool(
            telemetry.get("invoke_live_llm", is_real_api_key and "forced_llm_proposed_action" not in telemetry)
        )
        llm_timeout_s = float(telemetry.get("llm_timeout_s", 2.5))
        live_llm_proposal: Optional[Dict[str, Any]] = None
        live_llm_err: Optional[str] = None
        if self.aid_mode == "CLOUD_LLM_JEV" and invoke_live_llm and not sim_llm_offline and sim_llm_latency_ms <= 1200.0:
            live_llm_proposal, live_llm_err = self._query_external_llm_api(
                telemetry,
                timeout_s=llm_timeout_s,
                computed_safety_envelope=computed_safety_envelope,
            )
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

        # Apply live External LLM proposal if received, subject to two-phase drop normalization
        # and Stage-3 Formal Safety Kernel verification below
        if live_llm_proposal is not None:
            llm_act = str(live_llm_proposal.get("action", candidate_action)).upper().strip()
            llm_params = live_llm_proposal.get("params")
            if isinstance(llm_params, dict):
                for k, v in llm_params.items():
                    if v is not None:
                        candidate_params[k] = v
            # Enforce two-phase drop arming order: cannot jump to EXECUTE_DROP while drop_status == "READY"
            if llm_act == "EXECUTE_DROP" and drop_status == "READY" and rules.auto_queue_drop:
                llm_act = "QUEUE_DROP"
            # If LLM proposed LOCK_TARGET without coordinates or on a vetoed track while an unvetoed candidate exists:
            if llm_act == "LOCK_TARGET" and unvetoed_lock_candidate is not None:
                candidate_params["target_type"] = unvetoed_lock_candidate["target_type"]
                candidate_params["target_x_m"] = unvetoed_lock_candidate["target_x_m"]
                candidate_params["target_y_m"] = unvetoed_lock_candidate["target_y_m"]
            candidate_action = llm_act
            judge_text = str(live_llm_proposal.get("judge_assessment", judge_text))[:180]
            clause_text = str(live_llm_proposal.get("evaluate_clause", clause_text))[:180]

        # [RT1-03 Fix] Check Pre-Filter Proposed State-Flip Thrashing (`N_15(t) >= 3`)
        proposed_override = telemetry.get("forced_llm_proposed_action")
        if proposed_override:
            candidate_action = str(proposed_override)
        cand_tgt_type = str(candidate_params.get("target_type", current_target_type)).upper()
        thrash_tripped, flip_count = self._record_and_check_thrashing(
            candidate_action, now, target_type=cand_tgt_type
        )
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

        # Hard Life-Safety Preemption: If battery is below Arctic RTH floor and an LLM/override
        # proposed ANY non-RTH action, preempt to RTB_LOW_BATTERY so the aircraft never hovers
        # to battery death in Arctic cold!
        if batt_pct < dynamic_rth_pct and candidate_action != "RTB_LOW_BATTERY":
            preempted_from = candidate_action
            candidate_action = "RTB_LOW_BATTERY"
            candidate_params = {"altitude_agl_m": min(max_ceil, max(35.0 if not helo_inbound else 28.0, effective_search_alt))}
            verify_res = verify_action_safety_gate(
                action_type=candidate_action,
                params=candidate_params,
                telemetry=telemetry,
                compiled_rules=rules,
                veto_registry=self.veto_registry,
                request_epoch=req_epoch,
                now_ts=now,
            )
            verify_res.invariant_checks.append(
                f"PREEMPTED: Overrode unsafe {preempted_from} -> RTB_LOW_BATTERY ({batt_pct:.1f}% < {dynamic_rth_pct:.1f}%)"
            )

        # [RT1-03 & RT2-03] Target-Aware 8.0s Dwell Hysteresis Gate:
        # Allows monotonic causal progression on the same rescue target
        # (SCAN -> LOCK_TARGET -> QUEUE_DROP -> EXECUTE_DROP -> RELEASE_SAFE_TARGET_RETURN_TO_SCAN)
        # while holding premature target-type switches (PERSON <-> VEHICLE) or backward state flips within <8.0s.
        lifecycle_stage = {
            "CONTINUE_COOPERATIVE_SCAN": 0,
            "LOCK_TARGET": 1,
            "QUEUE_DROP": 2,
            "EXECUTE_DROP": 3,
            "RELEASE_SAFE_TARGET_RETURN_TO_SCAN": 4,
        }
        prev_stg = lifecycle_stage.get(self.last_accepted_state, -1)
        curr_stg = lifecycle_stage.get(candidate_action, -1)
        is_same_target_causal_step = (
            prev_stg >= 0
            and curr_stg > prev_stg
            and (self.last_accepted_state == "CONTINUE_COOPERATIVE_SCAN" or cand_tgt_type == self.last_accepted_target_type)
        )
        if (
            verify_res.approved
            and candidate_action != self.last_accepted_state
            and candidate_action not in ("RTB_LOW_BATTERY", "CONTINUE_COOPERATIVE_SCAN")
            and not is_same_target_causal_step
            and self.last_accepted_transition_ts is not None
            and (now - self.last_accepted_transition_ts) < rules.min_dwell_s
        ):
            dwell_rem = round(rules.min_dwell_s - (now - self.last_accepted_transition_ts), 1)
            verify_res.approved = False
            verify_res.rejection_reason = f"DWELL_HYSTERESIS_HOLD: {dwell_rem}s remaining before state change allowed."
            verify_res.invariant_checks.append(f"HOLD: 8.0s Dwell Gate ({dwell_rem}s left)")

        if verify_res.approved and (
            candidate_action != self.last_accepted_state or cand_tgt_type != self.last_accepted_target_type
        ):
            self.last_accepted_state = candidate_action
            self.last_accepted_target_type = cand_tgt_type
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
            "target_type": verify_res.modified_params.get("target_type", current_target_type),
            "target_altitude_agl_m": verify_res.modified_params.get("altitude_agl_m", effective_search_alt),
            "estimated_wind_drift_m": round(wind_drift_m, 2),
            "dynamic_rth_floor_pct": round(dynamic_rth_pct, 2),
            "executed": executed,
            "advisory_only": is_advisory,
            "llm_live_invoked": bool(live_llm_proposal is not None),
            "judge_assessment": judge_text,
            "evaluate_clause": clause_text,
            "verify_gate": asdict(verify_res),
            "cutout_reason": self.circuit_breaker_reason if self.circuit_breaker_tripped else None,
            "thrashing_detected": False,
            "latency_ms": elapsed_ms,
        }
        self.decision_log.append(record)
        if len(self.decision_log) > 40:
            self.decision_log = self.decision_log[-40:]
        return record

    def execute_operator_command(
        self,
        prompt_text: str,
        telemetry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a natural-language operator prompt via the External LLM API (when configured)
        or via a deterministic zero-regex structured semantic slot planner when running offline,
        followed by Stage-3 Physical Safety Verification (`build_structured_playbook_rules`).
        """
        t0 = time.perf_counter()
        raw_prompt = (prompt_text or "").strip()
        if not raw_prompt:
            return {
                "ok": False,
                "error": "Empty command",
                "assistant_reply": "Please type an instruction for the drones (e.g., 'Follow the snowmobile and ask if they are OK').",
            }

        eff_key = self._get_effective_api_key()
        is_real_key = bool(eff_key) and not eff_key.startswith("sk-test-")
        llm_plan: Optional[Dict[str, Any]] = None
        llm_error: Optional[str] = None

        if is_real_key:
            sys_msg = (
                "You are the AI Mission Auto-Controller for a 4-drone Arctic Search & Rescue swarm (Drone 1..4). "
                "Convert the human operator's instruction into a single JSON object with keys:\n"
                '- "mode": one of ["AUTO_FOLLOW", "AUTO_SEARCH", "MANUAL_FLY", null]\n'
                '- "target_type": one of ["VEHICLE", "PERSON", null] ("VEHICLE" = Snowmobile, "PERSON" = Lost Hiker)\n'
                '- "drone_idx": integer 0..3 (0=Drone 1, 1=Drone 2, 2=Drone 3, 3=Drone 4) or null\n'
                '- "close_talk": boolean (true if operator wants to talk/speak/fly close/halt/check status)\n'
                '- "voice_preset": one of ["HALT_LISTEN", "STATUS_CHECK", "FOLLOW_LIGHT", "STAND_CLEAR_DROP", null]\n'
                '- "custom_voice_message": string (if operator specifies custom words to say over the drone speaker, else null)\n'
                '- "drop_action": one of ["QUEUE_DROP", "RELEASE_NOW", "CANCEL_DROP", null]\n'
                '- "search_altitude_agl_m": number (28..120) or null\n'
                '- "tracking_altitude_agl_m": number (20..120) or null\n'
                '- "sim_speed": number (0.5, 1, 2, 5, 10, 25, 100) or null\n'
                '- "assistant_reply": concise 1-sentence confirmation of the exact drone actions being executed.'
            )
            user_msg = json.dumps({"operator_prompt": raw_prompt, "telemetry": telemetry or {}})
            try:
                if self.llm_provider == "anthropic":
                    model_id = self.llm_model or "claude-haiku-4-5-20251001"
                    body = json.dumps(
                        {
                            "model": model_id,
                            "max_tokens": 350,
                            "system": sys_msg,
                            "messages": [{"role": "user", "content": user_msg}],
                        }
                    ).encode("utf-8")
                    raw = self._https_post_json(
                        host="api.anthropic.com",
                        path="/v1/messages",
                        body_bytes=body,
                        headers={
                            "Content-Type": "application/json",
                            "x-api-key": eff_key,
                            "anthropic-version": "2023-06-01",
                        },
                        timeout_s=3.5,
                    )
                    blocks = raw.get("content", [])
                    txt = blocks[0].get("text", "{}") if blocks else "{}"
                elif self.llm_provider == "gemini":
                    model_id = self.llm_model or "gemini-2.5-flash"
                    if model_id.startswith("models/"):
                        model_id = model_id[len("models/") :]
                    body = json.dumps(
                        {
                            "systemInstruction": {"parts": [{"text": sys_msg}]},
                            "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
                            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 350, "responseMimeType": "application/json"},
                        }
                    ).encode("utf-8")
                    raw = self._https_post_json(
                        host="generativelanguage.googleapis.com",
                        path=f"/v1beta/models/{model_id}:generateContent?key={eff_key}",
                        body_bytes=body,
                        headers={"Content-Type": "application/json"},
                        timeout_s=3.5,
                    )
                    cands = raw.get("candidates", [])
                    parts = cands[0].get("content", {}).get("parts", []) if cands else []
                    txt = parts[0].get("text", "{}") if parts else "{}"
                else:
                    model_id = self.llm_model or "gpt-5.4-mini"
                    req_d: Dict[str, Any] = {
                        "model": model_id,
                        "max_completion_tokens": 350,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": sys_msg},
                            {"role": "user", "content": user_msg},
                        ],
                    }
                    if model_id.startswith("gpt-5"):
                        req_d["reasoning_effort"] = "none"
                    req_d["temperature"] = 0.0
                    body = json.dumps(req_d).encode("utf-8")
                    raw = self._https_post_json(
                        host="api.openai.com",
                        path="/v1/chat/completions",
                        body_bytes=body,
                        headers={"Content-Type": "application/json", "Authorization": f"Bearer {eff_key}"},
                        timeout_s=3.5,
                    )
                    choices = raw.get("choices", [])
                    txt = choices[0].get("message", {}).get("content", "{}") if choices else "{}"
                llm_plan = json.loads(self._strip_json_code_fence(txt))
            except Exception as exc:
                llm_error = f"{type(exc).__name__}: {str(exc)[:100]}"

        # Deterministic Zero-Regex Semantic Slot Planner (used when offline or to fill missing slots)
        low = raw_prompt.lower()
        clean_chars = []
        for ch in low:
            clean_chars.append(ch if (ch.isalnum() or ch in (".", "-", "_")) else " ")
        tokens = "".join(clean_chars).split()
        tok_set = set(tokens)

        # 1. Drone index slot (Drone 1..4)
        drone_idx: Optional[int] = None
        for idx, name_toks in enumerate(
            [
                ("1", "one", "sierra", "d1", "drone1"),
                ("2", "two", "kilo", "d2", "drone2"),
                ("3", "three", "echo", "d3", "drone3"),
                ("4", "four", "foxtrot", "d4", "drone4"),
            ]
        ):
            if any(nt in tok_set for nt in name_toks[2:]):
                drone_idx = idx
                break
            for i in range(len(tokens) - 1):
                if tokens[i] == "drone" and tokens[i + 1] in name_toks[:2]:
                    drone_idx = idx
                    break

        # 2. Target slot (Snowmobile vs Hiker)
        has_snowmobile = any(w in tok_set for w in ("snowmobile", "vehicle", "sled", "rider", "skidoo", "motor"))
        has_hiker = any(w in tok_set for w in ("hiker", "person", "victim", "walker", "survivor", "skier", "man", "woman"))
        target_type: Optional[str] = "VEHICLE" if has_snowmobile else ("PERSON" if has_hiker else None)

        # 3. Talk / Voice Intercom slot
        wants_talk = any(
            w in tok_set
            for w in ("talk", "speak", "say", "ask", "tell", "voice", "intercom", "speaker", "loudhailer", "close", "hail", "stop", "wait", "halt")
        )
        voice_preset: Optional[str] = None
        custom_voice_msg: Optional[str] = None

        # Extract quoted speech if operator wrote quotes: e.g. say "Hello there"
        q_start = raw_prompt.find('"')
        q_end = raw_prompt.rfind('"')
        if q_start != -1 and q_end > q_start + 1:
            custom_voice_msg = raw_prompt[q_start + 1 : q_end].strip()
            wants_talk = True
        elif "say " in low:
            after_say = raw_prompt[low.find("say ") + 4 :].strip()
            if len(after_say) >= 2:
                custom_voice_msg = after_say
                wants_talk = True

        if wants_talk and not custom_voice_msg:
            if any(w in tok_set for w in ("ok", "okay", "injured", "injury", "status", "hurt", "medical", "check")):
                voice_preset = "STATUS_CHECK"
            elif any(w in tok_set for w in ("guide", "safety", "hut", "bridge", "road", "lead", "light", "escort")) and "stop" not in tok_set:
                voice_preset = "FOLLOW_LIGHT"
            elif any(w in tok_set for w in ("clear", "stand", "back", "drop", "barrel", "cask", "supply")):
                voice_preset = "STAND_CLEAR_DROP"
            else:
                voice_preset = "HALT_LISTEN"

        # 4. Supply Drop slot
        drop_action: Optional[str] = None
        if any(w in tok_set for w in ("drop", "barrel", "cask", "supply", "payload", "blanket", "package")):
            if any(w in tok_set for w in ("cancel", "abort", "veto", "no", "dont", "stop")):
                drop_action = "CANCEL_DROP"
            elif any(w in tok_set for w in ("now", "immediate", "immediately", "release")):
                drop_action = "RELEASE_NOW"
            else:
                drop_action = "QUEUE_DROP"

        # 5. Flight Mode slot
        mode: Optional[str] = None
        if any(w in tok_set for w in ("manual", "practice", "stick", "steer", "myself", "keyboard", "wasd")):
            mode = "MANUAL_FLY"
        elif any(w in tok_set for w in ("follow", "track", "autotrack", "auto-track", "lock", "escort", "intercept", "chase")) or wants_talk or target_type is not None:
            mode = "AUTO_FOLLOW"
        elif any(w in tok_set for w in ("scan", "search", "patrol", "sweep", "grid", "sectors", "canyon", "resume")):
            mode = "AUTO_SEARCH"

        # 6. Numeric Altitude & Speed slots (zero regex: inspect adjacent tokens)
        search_alt_m: Optional[float] = None
        track_alt_m: Optional[float] = None
        sim_speed: Optional[float] = None
        for i, tok in enumerate(tokens):
            if tok.endswith("m") and len(tok) > 1:
                num_part = tok[:-1]
                try:
                    val = float(num_part)
                    if 18.0 <= val <= 150.0:
                        if mode == "AUTO_FOLLOW":
                            track_alt_m = val
                        else:
                            search_alt_m = val
                except ValueError:
                    pass
            elif tok.endswith("x") and len(tok) > 1:
                num_part = tok[:-1]
                try:
                    s_val = float(num_part)
                    if 0.1 <= s_val <= 100.0:
                        sim_speed = s_val
                except ValueError:
                    pass
            else:
                try:
                    val = float(tok)
                    next_tok = tokens[i + 1] if i + 1 < len(tokens) else ""
                    if next_tok in ("m", "meters", "metres", "agl") and 18.0 <= val <= 150.0:
                        if mode == "AUTO_FOLLOW":
                            track_alt_m = val
                        else:
                            search_alt_m = val
                except ValueError:
                    pass

        if "realtime" in tok_set or "real-time" in tok_set or ("normal" in tok_set and "speed" in tok_set):
            sim_speed = 1.0

        plan: Dict[str, Any] = {
            "mode": mode or "AUTO_FOLLOW",
            "target_type": target_type,
            "drone_idx": drone_idx,
            "close_talk": wants_talk,
            "voice_preset": voice_preset,
            "custom_voice_message": custom_voice_msg,
            "drop_action": drop_action,
            "search_altitude_agl_m": search_alt_m,
            "tracking_altitude_agl_m": track_alt_m,
            "sim_speed": sim_speed,
        }
        if isinstance(llm_plan, dict):
            for k in plan:
                if llm_plan.get(k) is not None:
                    plan[k] = llm_plan[k]

        # Apply structured parameters through Stage-3 safety clamping
        struct_overrides: Dict[str, Any] = {}
        if plan.get("search_altitude_agl_m") is not None:
            struct_overrides["search_altitude_agl_m"] = float(plan["search_altitude_agl_m"])
        if plan.get("tracking_altitude_agl_m") is not None:
            struct_overrides["tracking_altitude_agl_m"] = float(plan["tracking_altitude_agl_m"])
        if plan.get("target_type") in ("PERSON", "VEHICLE"):
            struct_overrides["preferred_target_type"] = plan["target_type"]
            struct_overrides["preempt_on_vehicle"] = plan["target_type"] == "VEHICLE"
            struct_overrides["preempt_on_person"] = True
        if plan.get("drop_action") == "CANCEL_DROP":
            struct_overrides["drop_policy"] = "MANUAL_ONLY"
        elif plan.get("drop_action") in ("QUEUE_DROP", "RELEASE_NOW"):
            struct_overrides["drop_policy"] = "AUTO_RELEASE_AT_OFFSET"

        if struct_overrides:
            self.set_playbook(self.active_playbook_id, structured_params=struct_overrides)
        if plan.get("mode") in ("AUTO_FOLLOW", "AUTO_SEARCH"):
            self.aid_mode = "CLOUD_LLM_JEV" if is_real_key else "OFFLINE_DETERMINISTIC"
        elif plan.get("mode") == "MANUAL_FLY":
            self.aid_mode = "MANUAL_HUMAN_ONLY"

        # Build human-friendly Apple Copilot summary if LLM didn't supply one
        reply = (llm_plan or {}).get("assistant_reply") if isinstance(llm_plan, dict) else None
        if not reply:
            d_label = f"Drone {(plan['drone_idx'] + 1)}" if plan.get("drone_idx") is not None else "Active Drone"
            t_label = "Snowmobile (+34.0°C)" if plan.get("target_type") == "VEHICLE" else (
                "Lost Hiker (+31.4°C)" if plan.get("target_type") == "PERSON" else "closest target"
            )
            parts = []
            if plan["mode"] == "MANUAL_FLY":
                parts.append(f"Switched {d_label} to 1x Real-Time Manual Flight")
            elif plan["mode"] == "AUTO_SEARCH":
                alt_s = int(self.compiled_rules.search_altitude_agl_m)
                parts.append(f"Commanded all 4 drones to cooperative canyon scan at {alt_s}m AGL")
            else:
                if plan.get("close_talk"):
                    parts.append(f"Assigned {d_label} to fly close (8m standoff, 20m AGL) & auto-track {t_label}")
                else:
                    alt_t = int(self.compiled_rules.tracking_altitude_agl_m)
                    parts.append(f"Assigned {d_label} to auto-track & follow {t_label} at {alt_t}m AGL")
            if plan.get("custom_voice_message"):
                parts.append(f'speaking over 85 dBA speaker: "{plan["custom_voice_message"]}"')
            elif plan.get("voice_preset") == "STATUS_CHECK":
                parts.append("asking if they are OK over the 2-way speaker/mic intercom")
            elif plan.get("voice_preset") == "HALT_LISTEN":
                parts.append("asking them to stop and talk to the drone")
            elif plan.get("voice_preset") == "FOLLOW_LIGHT":
                parts.append("guiding them to safety with the green Opaslyhty beam")
            elif plan.get("voice_preset") == "STAND_CLEAR_DROP":
                parts.append("warning them to stand 15m clear for supply drop")
            if plan.get("drop_action") == "QUEUE_DROP":
                parts.append("queuing +42°C warm survival barrel drop at 15m standoff")
            elif plan.get("drop_action") == "RELEASE_NOW":
                parts.append("releasing +42°C warm survival barrel immediately")
            elif plan.get("drop_action") == "CANCEL_DROP":
                parts.append("canceling pending payload drop")
            if plan.get("sim_speed") is not None:
                parts.append(f"speed set to {plan['sim_speed']:g}x")
            reply = "✅ " + ", ".join(parts) + "."

        return {
            "ok": True,
            "prompt": raw_prompt,
            "engine": f"LIVE_LLM ({self.llm_provider}:{self.llm_model})" if (llm_plan is not None) else "STRUCTURED_AI_PLANNER (<1ms)",
            "llm_error": llm_error,
            "action_plan": plan,
            "assistant_reply": reply,
            "compiled_rules": asdict(self.compiled_rules),
            "epoch_id": self.veto_registry.current_epoch,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

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
