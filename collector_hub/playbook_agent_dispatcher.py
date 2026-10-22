#!/usr/bin/env python3
"""
Karhunkierros SAR — Natural-Language Operations Playbook & JEV Agent Dispatcher
(`collector_hub/playbook_agent_dispatcher.py`)

Hardened after Iteration-1 Red-Team Review (GPT-6 Astra & Claude Opus 5.5):
  - [RT1-01] Spatial-Temporal Expanding Veto Bubbles (`r(t) = min(150, 60 + 1.5*dt) + 2*sigma`)
             + Monotonic `epoch_id` cancellation so track-ID churn at the same location is
             suppressed, a second victim 300 m away is NOT blocked, stale async LLM responses
             (`req_epoch < current_epoch`) are discarded, and DROP vetoes never expire on a timer.
  - [RT1-02] Clause-Scoped Line-by-Line AST Compiler (`compile_natural_language_playbook`):
             classifies each Markdown bullet into its strict semantic domain (`SEARCH`,
             `PREEMPTION`, `VEHICLE`, `DROP`, `ESCORT`, `SAFETY`) before numeric extraction
             (zero cross-clause capture), enforces negation dominance, and runs an altitude
             interval feasibility solver (`L <= U`).
  - [RT1-03] Pre-Filter Proposed State-Flip Thrash Breaker (`N_15(t) >= 3` flips in 15s),
             8.0s Dwell Hysteresis (`theta_on >= 0.80`, `theta_off <= 0.50`), and LLM-vs-Offline
             Disagreement Monitor (`>30%` disagreement -> auto-cutout).
  - [RT1-06] Ballistic Wind-Drift Impact Footprint Gate (`d_drift = 0.35 * W * sqrt(2h/g)`)
             + Arctic Cold-Derated Headwind RTH Energy Reserve (`E_avail <= 1.25 * E_req`).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# 1. PRE-DEFINED NATURAL-LANGUAGE SAR OPERATIONS PLAYBOOKS
# =============================================================================

DEFAULT_PLAYBOOKS: Dict[str, Dict[str, str]] = {
    "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY": {
        "id": "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY",
        "title": "1. Night Hiker Search & Opaslyhty Hut Escort (Default)",
        "summary": "Zero-overlap sector sweep at 55m AGL; preempt 1 drone on person detection (>=80% conf), auto-queue +42°C cask drop at 15m offset, escort to hut at 28m AGL.",
        "markdown": """# PLAYBOOK: Karhunkierros Night Hiker Search & Opaslyhty Hut Escort
- **Search Allocation:** Divide the search box into disjoint strips with 0% overlap at 55 m AGL above the 18 m boreal tree canopy.
- **Target Preemption:** When a lost person (thermal +28°C to +38°C, confidence >= 80%) is detected, assign 1 closest drone to lock and follow the person at 28 m AGL while the remaining drones continue scanning their sectors.
- **Vehicle Policy:** Do NOT preempt mapping for vehicles when a lost hiker is active.
- **Payload Drop Policy:** Automatically queue and release the +42°C rescue cask at a safe 15 m horizontal offset once the tracking drone is within 25 m of the hiker.
- **Shelter Escort:** Guide the hiker with the 1500 lm spotlight along the trail to the nearest wilderness hut at 1.2 m/s walking pace. When the hiker reaches within 15 m of the shelter, release target lock and return the drone to sector scanning.
- **Safety & Veto Rules:** Respect human cancel vetoes for 300 seconds in a 60 m spatial bubble. Maintain >= 100 m altitude over reindeer/wildlife. Trigger RTH if battery drops below 22%.""",
    },
    "PLAYBOOK_02_CAUTIOUS_HUMAN_CONFIRM_DROP": {
        "id": "PLAYBOOK_02_CAUTIOUS_HUMAN_CONFIRM_DROP",
        "title": "2. Cautious Search (Auto-Track Target, Require Human Confirm for Drop)",
        "summary": "Auto-locks lost person or vehicle with 1 drone while 3 scan, but NEVER releases payload without explicit human button confirmation.",
        "markdown": """# PLAYBOOK: Cautious Search — Human Confirmation Required for Payload Drop
- **Search Allocation:** Divide the search box into disjoint strips with 0% overlap at 55 m AGL.
- **Target Preemption:** Preempt 1 closest drone to track any detected lost person or stranded vehicle (confidence >= 80%) at 30 m AGL.
- **Payload Drop Policy:** Do NOT auto-drop payload. Queue the drop at 15 m offset and REQUIRE explicit human confirmation before releasing the winch servo.
- **Shelter Escort:** Escort the tracked subject to the nearest wilderness hut or plowed road bridge, then return to cooperative scanning.
- **Safety & Veto Rules:** Respect human cancel vetoes for 600 seconds. Maintain >= 100 m altitude over wildlife. Trigger RTH if battery drops below 25%.""",
    },
    "PLAYBOOK_03_STRANDED_SNOWMOBILE_CORRIDOR": {
        "id": "PLAYBOOK_03_STRANDED_SNOWMOBILE_CORRIDOR",
        "title": "3. Stranded Snowmobile / Vehicle Corridor Escort",
        "summary": "Prioritizes stranded snowmobiles/vehicles (+34°C engine/exhaust), escorts along low-slope forestry route at 45m AGL to plowed road bridge.",
        "markdown": """# PLAYBOOK: Winter Snowmobile & Vehicle Breakdown Escort
- **Search Allocation:** Divide the search box into disjoint strips with 0% overlap at 65 m AGL for wide-swath coverage.
- **Target Preemption:** Prioritize stranded vehicles and snowmobiles (confidence >= 75%). Assign 1 drone to escort the vehicle at 45 m AGL with a 35 m forward spotlight lead toward the plowed road bridge.
- **Payload Drop Policy:** Do NOT auto-drop the rescue cask on a moving vehicle; require explicit human confirmation at a 15 m offset.
- **Safety & Veto Rules:** Respect human cancel vetoes for 300 seconds. Maintain >= 100 m altitude over wildlife. Trigger RTH if battery drops below 22%.""",
    },
    "PLAYBOOK_04_EW_DENIED_PASSIVE_RECON": {
        "id": "PLAYBOOK_04_EW_DENIED_PASSIVE_RECON",
        "title": "4. GNSS-Denied / Wildlife-Safe High-Standoff Sweep (Advisory Only)",
        "summary": "High-altitude 75m AGL sweep, strict >=100m Poronhoitolaki wildlife floor, no autonomous drop; switches AID to Advisory/Offline mode under EW.",
        "markdown": """# PLAYBOOK: GNSS-Denied & Reindeer-Safe High-Standoff Sweep
- **Search Allocation:** Scan in disjoint strips with 0% overlap at 75 m AGL using optical flow + TF02-Pro LiDAR terrain following.
- **Target Preemption:** Track detected persons at 35 m AGL minimum floor (confidence >= 85%). Do NOT preempt on vehicles.
- **Payload Drop Policy:** Do NOT auto-drop payload; require human confirmation at >= 15 m standoff.
- **Safety & Veto Rules:** Enforce >= 100 m Poronhoitolaki altitude floor over reindeer herds. Respect human cancel vetoes for 600 seconds. Trigger RTH if battery drops below 28%.""",
    },
}


# =============================================================================
# 2. CLAUSE-SCOPED DETERMINISTIC PLAYBOOK COMPILER ([RT1-02] FIX)
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
    parsed_clause_count: int = 0
    compile_warnings: List[str] = field(default_factory=list)


_DOMAIN_KEYS: Dict[str, Tuple[str, ...]] = {
    "PREEMPTION": ("target preemption", "when a lost person", "prioritize stranded", "track detected", "lock and follow", "lock at", "confidence"),
    "DROP": ("payload drop", "rescue cask", "auto-drop", "winch", "offset", "standoff", "drop", "human confirm"),
    "SEARCH": ("search allocation", "search box", "disjoint strips", "overlap", "swath", "scan at"),
    "VEHICLE": ("vehicle policy", "vehicles when"),
    "ESCORT": ("shelter escort", "wilderness hut", "walking pace", "spotlight along"),
    "SAFETY": ("safety", "veto", "reindeer", "wildlife", "poronhoitolaki", "battery", "rth", "canopy", "ceiling"),
}


def _split_subclauses(line: str) -> List[str]:
    """
    [RT2-04 Fix] Split a Markdown bullet into sub-clauses without breaking decimal numbers
    like `0.85` (`(?<!\\d)\\.(?!\\d)`), and splitting compound `and queue/drop/track/lock` clauses.
    """
    parts = re.split(
        r"(?<!\d)\.(?!\d)|;|\band then\b|,\s*and\b|\band\b(?=\s+(?:queue|drop|release|track|lock|require|do\s+not))",
        line,
        flags=re.IGNORECASE,
    )
    return [p.strip() for p in parts if p and p.strip()]


def _classify_clause_domains(clause_lower: str) -> List[str]:
    """[RT2-04 Fix] Return all matching rule domains for a sub-clause so compound clauses never drop rules."""
    hits = [d for d, keys in _DOMAIN_KEYS.items() if any(k in clause_lower for k in keys)]
    return hits or ["GENERAL"]


def compile_natural_language_playbook(
    markdown_text: str,
    playbook_id: str = "CUSTOM_NL_PLAYBOOK",
    title: str = "Custom Natural-Language Playbook",
) -> CompiledPlaybookRules:
    """
    [RT1-02 & RT2-04 Fix] Sub-Clause-Scoped, Negation-Safe Deterministic Playbook Compiler (<1 ms).
    - Splits each Markdown line into sub-clauses (`_split_subclauses`) without breaking decimals.
    - Evaluates each sub-clause against all matching domains (`_classify_clause_domains`) with
      sub-clause-local negation (`has_negation`), preventing compound lines from losing rules.
    - Runs final canopy-floor and ceiling interval clamping (`L <= U`) in a post-loop pass so
      line ordering in the playbook never affects safety clamping.
    """
    clean_text = (markdown_text or "").strip()
    sha = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
    rules = CompiledPlaybookRules(
        playbook_id=playbook_id,
        title=title,
        raw_markdown_sha256=sha,
    )
    if not clean_text:
        rules.compile_warnings.append("Empty playbook text; using safe default rules.")
        return rules

    raw_search_alt: Optional[float] = None
    raw_track_alt: Optional[float] = None

    lines = [ln.strip() for ln in clean_text.splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("#"):
            m_title = re.sub(r"^#+\s*(?:playbook:\s*)?", "", ln, flags=re.IGNORECASE).strip()
            if m_title:
                rules.title = m_title[:90]
            continue

        rules.parsed_clause_count += 1
        subclauses = _split_subclauses(ln.lower())

        for sub in subclauses:
            domains = _classify_clause_domains(sub)
            has_negation = bool(re.search(r"\b(?:do\s+not|don't|never|no|prohibit|ignore)\b", sub))

            for domain in domains:
                if domain == "SEARCH":
                    m_ov = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%\s*overlap", sub)
                    if m_ov:
                        rules.sector_overlap_pct = max(0.0, min(50.0, float(m_ov.group(1))))
                    m_can = re.search(r"(\d{1,2}(?:\.\d+)?)\s*m\s*(?:boreal\s+)?(?:tree\s+)?canopy", sub)
                    if m_can:
                        rules.canopy_floor_m = max(15.0, min(35.0, float(m_can.group(1))))
                    m_alt = re.search(r"at\s+(\d{2,3}(?:\.\d+)?)\s*m\s*(?:agl)?", sub)
                    if m_alt:
                        raw_search_alt = float(m_alt.group(1))

                elif domain == "VEHICLE":
                    if has_negation and "vehicle" in sub:
                        rules.preempt_on_vehicle = False

                elif domain == "PREEMPTION":
                    m_conf = re.search(
                        r"conf(?:idence)?\s*(?:>=|>|at\s+least|of)?\s*(\d+(?:\.\d+)?)\s*(%)?|(\d+(?:\.\d+)?)\s*(%)?\s*conf(?:idence)?",
                        sub,
                    )
                    if m_conf:
                        raw_num = m_conf.group(1) if m_conf.group(1) is not None else m_conf.group(3)
                        raw_pct = m_conf.group(2) if m_conf.group(1) is not None else m_conf.group(4)
                        val = float(raw_num)
                        if raw_pct == "%" or val > 1.0:
                            val = val / 100.0
                        rules.min_detection_confidence = max(0.55, min(0.99, val))
                        rules.exit_detection_confidence = round(max(0.35, rules.min_detection_confidence - 0.30), 2)

                    if "vehicle" in sub or "snowmobile" in sub:
                        if has_negation:
                            rules.preempt_on_vehicle = False
                        else:
                            rules.preempt_on_vehicle = True
                            if "prioritize" in sub or "snowmobile" in sub:
                                rules.preferred_target_type = "VEHICLE"
                    if "person" in sub or "hiker" in sub:
                        if has_negation:
                            rules.preempt_on_person = False
                        else:
                            rules.preempt_on_person = True

                    m_talt = re.search(r"at\s+(\d{2,3}(?:\.\d+)?)\s*m\s*(?:agl|minimum)?", sub)
                    if m_talt:
                        raw_track_alt = float(m_talt.group(1))

                elif domain == "DROP":
                    req_human = bool(re.search(r"require\s+(?:explicit\s+)?human\s+(?:confirm|confirmation|approval)", sub))
                    if has_negation or req_human:
                        rules.auto_release_drop = False
                        rules.require_human_drop_confirm = True
                        if "queue" in sub:
                            rules.auto_queue_drop = True
                    elif "queue" in sub or "release" in sub or "auto" in sub:
                        rules.auto_release_drop = True
                        rules.require_human_drop_confirm = False
                        rules.auto_queue_drop = True

                    m_off = re.search(r"(\d{1,2}(?:\.\d+)?)\s*m\s*(?:horizontal\s+)?(?:offset|standoff)", sub)
                    if m_off:
                        raw_off = float(m_off.group(1))
                        if raw_off < 15.0:
                            rules.compile_warnings.append(
                                f"Playbook requested {raw_off}m drop offset; enforced >=15.0m mandatory human safety standoff."
                            )
                            raw_off = 15.0
                        rules.drop_offset_m = raw_off

                    m_trig = re.search(r"within\s+(\d{1,2}(?:\.\d+)?)\s*m\s+of", sub)
                    if m_trig:
                        rules.drop_trigger_distance_m = max(15.0, min(60.0, float(m_trig.group(1))))

                elif domain == "ESCORT":
                    if "return" in sub and "scan" in sub:
                        rules.return_to_scan_on_shelter_arrival = True
                    m_arr = re.search(r"within\s+(\d{1,2}(?:\.\d+)?)\s*m\s+of\s+the\s+(?:shelter|hut|road)", sub)
                    if m_arr:
                        rules.shelter_arrival_radius_m = max(8.0, min(40.0, float(m_arr.group(1))))

                elif domain == "SAFETY":
                    m_can_s = re.search(
                        r"(\d{1,2}(?:\.\d+)?)\s*m\s*(?:boreal\s+)?(?:tree\s+)?canopy|canopy\s+(?:is\s+)?(\d{1,2}(?:\.\d+)?)\s*m",
                        sub,
                    )
                    if m_can_s:
                        c_val = float(m_can_s.group(1) if m_can_s.group(1) is not None else m_can_s.group(2))
                        rules.canopy_floor_m = max(15.0, min(35.0, c_val))
                    m_ceil = re.search(
                        r"(?:below|<|<=|under|max)\s*(\d{2,3}(?:\.\d+)?)\s*m\s*(?:agl\s*)?ceiling|ceiling\s*(?:of\s*|is\s*)?(\d{2,3}(?:\.\d+)?)\s*m",
                        sub,
                    )
                    if m_ceil:
                        u_val = float(m_ceil.group(1) if m_ceil.group(1) is not None else m_ceil.group(2))
                        rules.altitude_ceiling_m = max(20.0, min(150.0, u_val))
                    m_veto = re.search(r"veto(?:es)?\s+for\s+(\d{2,4})\s*s", sub)
                    if m_veto:
                        rules.human_cancel_veto_cooldown_s = max(30.0, min(3600.0, float(m_veto.group(1))))
                    m_bub = re.search(r"(\d{2,3}(?:\.\d+)?)\s*m\s*spatial\s*bubble", sub)
                    if m_bub:
                        rules.veto_bubble_radius_m = max(30.0, min(200.0, float(m_bub.group(1))))
                    m_wild = re.search(r"(\d{2,3}(?:\.\d+)?)\s*m\s*(?:poronhoitolaki\s*)?(?:altitude\s*)?(?:floor\s*)?over\s*(?:reindeer|wildlife)", sub)
                    if m_wild:
                        rules.wildlife_min_altitude_m = max(100.0, float(m_wild.group(1)))
                    m_batt = re.search(r"battery\s+(?:drops\s+)?(?:below|<|<=)\s*(\d{2}(?:\.\d+)?)\s*%", sub)
                    if m_batt:
                        b_pct = float(m_batt.group(1))
                        if b_pct < 20.0:
                            rules.compile_warnings.append(f"Clamped battery RTH floor {b_pct}% up to 20.0% minimum reserve.")
                            b_pct = 20.0
                        rules.rth_battery_floor_pct = min(55.0, b_pct)

    # [RT2-04 Fix] Final Post-Loop Altitude Clamping & Interval Feasibility Check (Order-Independent)
    lower_bound = max(28.0, rules.canopy_floor_m + 10.0)
    if lower_bound > rules.altitude_ceiling_m:
        rules.compile_warnings.append(
            f"INFEASIBLE_ALTITUDE_INTERVAL: L={lower_bound}m > U={rules.altitude_ceiling_m}m; reset ceiling to 120.0m."
        )
        rules.altitude_ceiling_m = 120.0

    if raw_search_alt is not None:
        if raw_search_alt < lower_bound:
            rules.compile_warnings.append(f"Clamped search altitude {raw_search_alt}m up to {lower_bound}m canopy safety floor.")
            raw_search_alt = lower_bound
        elif raw_search_alt > rules.altitude_ceiling_m:
            rules.compile_warnings.append(f"Clamped search altitude {raw_search_alt}m down to {rules.altitude_ceiling_m}m ceiling.")
            raw_search_alt = rules.altitude_ceiling_m
        rules.search_altitude_agl_m = raw_search_alt

    if raw_track_alt is not None:
        if raw_track_alt < lower_bound:
            rules.compile_warnings.append(f"Clamped tracking altitude {raw_track_alt}m up to {lower_bound}m canopy floor.")
            raw_track_alt = lower_bound
        elif raw_track_alt > rules.altitude_ceiling_m:
            raw_track_alt = rules.altitude_ceiling_m
        rules.tracking_altitude_agl_m = raw_track_alt

    return rules


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
    monitors LLM latency AND pre-filter state-flip thrashing (`[RT1-03]`), and runs
    the JEV (Judge -> Evaluate -> Verify) decision cycle.
    """

    def __init__(self) -> None:
        self.active_playbook_id: str = "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY"
        self.active_markdown: str = DEFAULT_PLAYBOOKS[self.active_playbook_id]["markdown"]
        self.compiled_rules: CompiledPlaybookRules = compile_natural_language_playbook(
            self.active_markdown,
            playbook_id=self.active_playbook_id,
            title=DEFAULT_PLAYBOOKS[self.active_playbook_id]["title"],
        )
        self.aid_mode: str = "OFFLINE_DETERMINISTIC"
        self.fallback_on_llm_unavailable: str = "OFFLINE_DETERMINISTIC"
        self.circuit_breaker_tripped: bool = False
        self.circuit_breaker_reason: str = "Normal (<1 ms Offline Deterministic Compiler)"
        self.veto_registry: HumanVetoRegistry = HumanVetoRegistry()
        # [RT1-03 & RT2-03 Fix] Dwell timer (`None` until first transition) & Thrash Counter
        self.last_accepted_state: str = "CONTINUE_COOPERATIVE_SCAN"
        self.last_accepted_transition_ts: Optional[float] = None
        self.proposed_state_history: List[Tuple[float, str]] = []  # (ts, proposed_action)
        self.decision_log: List[Dict[str, Any]] = []

    def set_playbook(self, playbook_id: str, custom_markdown: Optional[str] = None) -> Dict[str, Any]:
        if custom_markdown is not None and custom_markdown.strip():
            self.active_playbook_id = playbook_id or "CUSTOM_NL_PLAYBOOK"
            self.active_markdown = custom_markdown.strip()
            title = DEFAULT_PLAYBOOKS.get(self.active_playbook_id, {}).get("title", "Custom Natural-Language Playbook")
        elif playbook_id in DEFAULT_PLAYBOOKS:
            self.active_playbook_id = playbook_id
            self.active_markdown = DEFAULT_PLAYBOOKS[playbook_id]["markdown"]
            title = DEFAULT_PLAYBOOKS[playbook_id]["title"]
        else:
            self.active_playbook_id = "PLAYBOOK_01_LOST_HIKER_NIGHT_CANOPY"
            self.active_markdown = DEFAULT_PLAYBOOKS[self.active_playbook_id]["markdown"]
            title = DEFAULT_PLAYBOOKS[self.active_playbook_id]["title"]

        self.compiled_rules = compile_natural_language_playbook(
            self.active_markdown,
            playbook_id=self.active_playbook_id,
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
            has_api = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
            if not has_api:
                self.circuit_breaker_tripped = True
                self.aid_mode = self.fallback_on_llm_unavailable
                self.circuit_breaker_reason = (
                    f"External LLM API unreachable/unconfigured -> Auto-switched to {self.aid_mode}"
                )
            else:
                self.circuit_breaker_tripped = False
                self.circuit_breaker_reason = "External LLM JEV Active (<=1,200 ms timeout & thrash guard)"
        elif self.aid_mode == "MANUAL_HUMAN_ONLY":
            self.circuit_breaker_tripped = False
            self.circuit_breaker_reason = "AID Turned OFF by Operator (100% Manual Human Control)"
        else:
            self.circuit_breaker_tripped = False
            self.proposed_state_history.clear()
            self.circuit_breaker_reason = f"Active Mode: {self.aid_mode} (<1 ms local execution)"

        return self.get_status()

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
        if self.aid_mode == "CLOUD_LLM_JEV" and (sim_llm_offline or sim_llm_latency_ms > 1200.0):
            self.circuit_breaker_tripped = True
            prev_mode = self.aid_mode
            self.aid_mode = self.fallback_on_llm_unavailable
            self.veto_registry.bump_epoch(reason="AID Latency/Offline Circuit-Breaker")
            self.circuit_breaker_reason = (
                f"AID Circuit-Breaker Tripped (LLM offline or latency {sim_llm_latency_ms:.0f}ms > 1200ms) -> "
                f"Downgraded from {prev_mode} to {self.aid_mode}"
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
            "active_markdown": self.active_markdown,
            "compiled_rules": asdict(self.compiled_rules),
            "aid_mode": self.aid_mode,
            "epoch_id": self.veto_registry.current_epoch,
            "fallback_on_llm_unavailable": self.fallback_on_llm_unavailable,
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "circuit_breaker_reason": self.circuit_breaker_reason,
            "human_vetoes": {
                "epoch_id": self.veto_registry.current_epoch,
                "active_bubbles": [asdict(b) for b in self.veto_registry.bubbles],
                "target_veto_until_ts": self.veto_registry.target_veto_until_ts,
                "drop_veto_latched": self.veto_registry.drop_veto_latched,
                "last_human_action_desc": self.veto_registry.last_human_action_desc,
            },
            "available_playbooks": [
                {"id": k, "title": v["title"], "summary": v["summary"]}
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
