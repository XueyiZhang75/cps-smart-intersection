"""
Unified Experiment Runner
Runs any of the 4 controllers on a given SUMO config and outputs
standardized metrics in both terminal and JSON format.

Usage:
  python scripts/run_experiment.py --controller fixed_time
  python scripts/run_experiment.py --controller actuated --cfg intersection_ped_near --gui
  python scripts/run_experiment.py --controller adaptive_shield --duration 300
"""

import argparse
import json
import os
import sys
import traci

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Project paths ─────────────────────────────────────────────
PROJECT_ROOT = r"E:\cps-smart-intersection"
SUMO_CFG_DIR = os.path.join(PROJECT_ROOT, "sumo", "cfg")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
TL_ID = "J0"
# ───────────────────────────────────────────────────────────────

# ── Phase timing defaults ─────────────────────────────────────
VEH_MIN_GREEN = 15
VEH_MAX_GREEN = 30
PED_MIN_GREEN = 10
PED_MAX_GREEN = 15
CLEARANCE_DUR = 3
# ───────────────────────────────────────────────────────────────

# ── Adaptive score weights ────────────────────────────────────
W_Q = 2.0
W_W = 3.0
W_C = 1.0
SCORE_EPSILON = 0.5
WAIT_NORM = 102.0
# ───────────────────────────────────────────────────────────────

# ── Safety shield parameters ─────────────────────────────────
MIN_SWITCH_INTERVAL = 8
SHIELD_MIN_HOLD = 18          # min seconds in service phase before shield allows switch
SHIELD_SCORE_MARGIN = 1.0     # candidate must beat current by at least this much
SHIELD_STARVATION_LIMIT = 40  # seconds since last served → force allow
SHIELD_DEMAND_OVERRIDE = 3    # demand count → force allow
# ───────────────────────────────────────────────────────────────

# 8-phase plan (shared by all controllers)
PHASES = [
    {"name": "Vehicle_NS",             "state": "GGggrrrrGGggrrrrrrrr",
     "min_green": VEH_MIN_GREEN, "max_green": VEH_MAX_GREEN,
     "duration": VEH_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_NS",     "state": "yyyyrrrryyyyrrrrrrrr",
     "min_green": CLEARANCE_DUR, "max_green": CLEARANCE_DUR,
     "duration": CLEARANCE_DUR, "clearance": True},
    {"name": "Vehicle_EW",             "state": "rrrrGGggrrrrGGggrrrr",
     "min_green": VEH_MIN_GREEN, "max_green": VEH_MAX_GREEN,
     "duration": VEH_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_EW",     "state": "rrrryyyyrrrryyyyrrrr",
     "min_green": CLEARANCE_DUR, "max_green": CLEARANCE_DUR,
     "duration": CLEARANCE_DUR, "clearance": True},
    {"name": "Ped_EW",                 "state": "rrrrrrrrrrrrrrrrrGrG",
     "min_green": PED_MIN_GREEN, "max_green": PED_MAX_GREEN,
     "duration": PED_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_Ped_EW", "state": "rrrrrrrrrrrrrrrrrrrr",
     "min_green": CLEARANCE_DUR, "max_green": CLEARANCE_DUR,
     "duration": CLEARANCE_DUR, "clearance": True},
    {"name": "Ped_NS",                 "state": "rrrrrrrrrrrrrrrrGrGr",
     "min_green": PED_MIN_GREEN, "max_green": PED_MAX_GREEN,
     "duration": PED_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_Ped_NS", "state": "rrrrrrrrrrrrrrrrrrrr",
     "min_green": CLEARANCE_DUR, "max_green": CLEARANCE_DUR,
     "duration": CLEARANCE_DUR, "clearance": True},
]

# Fixed-time durations (overrides for fixed_time controller)
FIXED_DURATIONS = [30, 3, 30, 3, 15, 3, 15, 3]

SERVICE_INDICES = [0, 2, 4, 6]

# ── Conflict detection ────────────────────────────────────────
# A "conflict release" means the TL state applied to the junction does not
# match any state in the predefined PHASES table. Since every valid phase
# is designed to avoid conflicting movements, any deviation from the table
# is a potential safety violation.
#
# Additionally, within a single step, if the controller transitions directly
# from one service phase to another without an intervening clearance, that
# constitutes a "clearance skip" — a dangerous condition where conflicting
# green movements could overlap during the transition.

def check_conflict(applied_state_str, prev_phase_idx, new_phase_idx):
    """
    Check for two types of conflict:
    1. Invalid TL state: applied state not in VALID_STATES
    2. Clearance skip: direct service-to-service transition without clearance

    Returns (conflict_flag: bool, reason: str)
    """
    # Check 1: Is the applied state a known valid combination?
    if applied_state_str not in VALID_STATES:
        return True, "invalid_tl_state"

    # Check 2: Direct service-to-service jump (no clearance in between)?
    if (prev_phase_idx != new_phase_idx
            and prev_phase_idx in SERVICE_INDICES
            and new_phase_idx in SERVICE_INDICES):
        return True, "clearance_skip"

    return False, ""
CLEARANCE_AFTER = {0: 1, 2: 3, 4: 5, 6: 7}
VALID_STATES = {ph["state"] for ph in PHASES}

# ── Demand detection ──────────────────────────────────────────
VEHICLE_LANES = ["N2C_1", "S2C_1", "E2C_1", "W2C_1"]
LANES_NS = ["N2C_1", "S2C_1"]
LANES_EW = ["E2C_1", "W2C_1"]
PED_WAIT_AREAS_EW = [":J0_w0", ":J0_w2"]
PED_WAIT_AREAS_NS = [":J0_w1", ":J0_w3"]

# Module-level uncertainty layer: None = disabled (original behavior)
# Set by run() when --scenario_id provides uncertainty config.
_unc_layer = None


def get_vehicle_queue(lanes):
    if _unc_layer:
        return _unc_layer.get_vehicle_queue(lanes)
    return sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes)


def get_ped_waiting_count(wait_areas):
    if _unc_layer:
        return _unc_layer.get_ped_waiting_count(wait_areas)
    count = 0
    for pid in traci.person.getIDList():
        if traci.person.getRoadID(pid) in wait_areas:
            if traci.person.getWaitingTime(pid) > 0:
                count += 1
    return count


def has_vehicle_demand(lanes):
    if _unc_layer:
        return _unc_layer.has_vehicle_demand(lanes)
    return any(traci.lane.getLastStepVehicleNumber(l) > 0 for l in lanes)


def has_ped_demand(wait_areas):
    if _unc_layer:
        return _unc_layer.has_ped_demand(wait_areas)
    for pid in traci.person.getIDList():
        if traci.person.getRoadID(pid) in wait_areas:
            if traci.person.getWaitingTime(pid) > 0:
                return True
    return False


def compute_demand(phase_name):
    if phase_name == "Vehicle_NS":
        return get_vehicle_queue(LANES_NS)
    elif phase_name == "Vehicle_EW":
        return get_vehicle_queue(LANES_EW)
    elif phase_name == "Ped_EW":
        return get_ped_waiting_count(PED_WAIT_AREAS_EW)
    elif phase_name == "Ped_NS":
        return get_ped_waiting_count(PED_WAIT_AREAS_NS)
    return 0


def compute_scores(current_service_idx, current_time, last_served_time):
    scores = {}
    for idx in SERVICE_INDICES:
        name = PHASES[idx]["name"]
        q_i = compute_demand(name)
        w_i = (current_time - last_served_time[name]) / WAIT_NORM
        c_i = 0.0 if idx == current_service_idx else 1.0
        score = W_Q * q_i + W_W * w_i - W_C * c_i
        scores[idx] = score
    return scores


def adaptive_select(current_service_idx, current_time, last_served_time,
                    exclude_current=False):
    scores = compute_scores(current_service_idx, current_time, last_served_time)
    if exclude_current:
        best_idx = max((i for i in SERVICE_INDICES if i != current_service_idx),
                       key=lambda i: scores[i])
        return best_idx
    current_score = scores[current_service_idx]
    best_idx = max(SERVICE_INDICES, key=lambda i: scores[i])
    if current_score >= scores[best_idx] - SCORE_EPSILON:
        return current_service_idx
    return best_idx


# ══════════════════════════════════════════════════════════════
#  Controller implementations
# ══════════════════════════════════════════════════════════════

class ControllerState:
    """Shared mutable state for all controllers."""
    def __init__(self):
        self.phase_idx = 0
        self.time_in_phase = 0
        self.last_served_time = {PHASES[i]["name"]: 0.0 for i in SERVICE_INDICES}
        self.last_switch_time = 0.0
        self.pending_target = None
        self.prev_service_idx = 0  # for switch_count tracking
        # Shield debug counters (only used by adaptive_shield)
        self.shield_holds = {"min_hold": 0, "small_gain": 0}
        self.shield_overrides = {"starvation": 0, "demand": 0}
        # Per-step tracking (set by controllers, read by main loop)
        self.step_candidate_idx = None    # what controller wanted
        self.step_override_flag = False   # shield blocked/modified
        self.step_override_reason = ""    # why


def step_fixed_time(state):
    """Fixed-time: advance through phases at fixed durations."""
    state.time_in_phase += 1
    if state.time_in_phase >= FIXED_DURATIONS[state.phase_idx]:
        state.phase_idx = (state.phase_idx + 1) % len(PHASES)
        state.time_in_phase = 0


def step_actuated(state):
    """Actuated: demand-responsive switching after min_green."""
    state.time_in_phase += 1
    phase = PHASES[state.phase_idx]

    if phase["clearance"]:
        if state.time_in_phase >= phase["duration"]:
            state.phase_idx = (state.phase_idx + 1) % len(PHASES)
            state.time_in_phase = 0
    else:
        if state.time_in_phase >= phase["max_green"]:
            state.phase_idx = (state.phase_idx + 1) % len(PHASES)
            state.time_in_phase = 0
        elif state.time_in_phase >= phase["min_green"]:
            demands = {
                "Vehicle_NS": has_vehicle_demand(LANES_NS),
                "Vehicle_EW": has_vehicle_demand(LANES_EW),
                "Ped_EW": has_ped_demand(PED_WAIT_AREAS_EW),
                "Ped_NS": has_ped_demand(PED_WAIT_AREAS_NS),
            }
            current_name = phase["name"]
            other_demand = any(v for k, v in demands.items() if k != current_name)
            if other_demand:
                state.phase_idx = (state.phase_idx + 1) % len(PHASES)
                state.time_in_phase = 0


def step_adaptive_only(state, current_time):
    """Adaptive-only: score-based phase selection with jump."""
    state.time_in_phase += 1
    phase = PHASES[state.phase_idx]

    if phase["clearance"]:
        if state.time_in_phase >= phase["duration"]:
            if state.pending_target is not None:
                state.phase_idx = state.pending_target
                state.pending_target = None
            else:
                state.phase_idx = (state.phase_idx + 1) % len(PHASES)
            state.last_served_time[PHASES[state.phase_idx]["name"]] = current_time
            state.time_in_phase = 0
    else:
        if state.time_in_phase >= phase["max_green"]:
            best = adaptive_select(state.phase_idx, current_time,
                                   state.last_served_time, exclude_current=True)
            state.step_candidate_idx = best
            state.pending_target = best
            from_idx = state.phase_idx
            state.phase_idx = CLEARANCE_AFTER[from_idx]
            state.time_in_phase = 0
        elif state.time_in_phase >= phase["min_green"]:
            best = adaptive_select(state.phase_idx, current_time,
                                   state.last_served_time)
            state.step_candidate_idx = best
            if best != state.phase_idx:
                state.pending_target = best
                state.phase_idx = CLEARANCE_AFTER[state.phase_idx]
                state.time_in_phase = 0


def get_phase_name(idx):
    """Return the name of a phase by index."""
    return PHASES[idx]["name"]


def get_phase_score(idx, current_service_idx, current_time, last_served_time):
    """Return the score for a single service phase."""
    scores = compute_scores(current_service_idx, current_time, last_served_time)
    return scores.get(idx, 0.0)


def shield_decision(state, current_time, candidate):
    """
    Three-layer safety shield for adaptive_shield controller.

    Returns (allow_switch: bool, reason: str).

    Layer 1 (override — checked first, highest priority):
      Starvation or high demand → force allow, bypassing layers 2-3.

    Layer 2 (min hold):
      If time_in_phase < SHIELD_MIN_HOLD → HOLD.

    Layer 3 (small gain):
      If candidate score - current score < SHIELD_SCORE_MARGIN → HOLD.
    """
    candidate_name = get_phase_name(candidate)

    # ── Layer 1: Override — starvation or high demand force allow ──
    time_since_served = current_time - state.last_served_time[candidate_name]
    if time_since_served >= SHIELD_STARVATION_LIMIT:
        state.shield_overrides["starvation"] += 1
        return True, f"override:starvation ({time_since_served:.0f}s >= {SHIELD_STARVATION_LIMIT}s)"

    candidate_demand = compute_demand(candidate_name)
    if candidate_demand >= SHIELD_DEMAND_OVERRIDE:
        state.shield_overrides["demand"] += 1
        return True, f"override:demand ({candidate_demand} >= {SHIELD_DEMAND_OVERRIDE})"

    # ── Layer 2: Minimum hold time ──
    if state.time_in_phase < SHIELD_MIN_HOLD:
        state.shield_holds["min_hold"] += 1
        return False, f"hold:min_hold ({state.time_in_phase}s < {SHIELD_MIN_HOLD}s)"

    # ── Layer 3: Small gain rejection ──
    scores = compute_scores(state.phase_idx, current_time, state.last_served_time)
    current_score = scores[state.phase_idx]
    candidate_score = scores[candidate]
    margin = candidate_score - current_score
    if margin < SHIELD_SCORE_MARGIN:
        state.shield_holds["small_gain"] += 1
        return False, f"hold:small_gain (margin {margin:+.2f} < {SHIELD_SCORE_MARGIN})"

    return True, "allowed"


def step_adaptive_shield(state, current_time):
    """Adaptive + Safety Shield: score-based with three-layer shield filter."""
    state.time_in_phase += 1
    phase = PHASES[state.phase_idx]

    if phase["clearance"]:
        if state.time_in_phase >= phase["duration"]:
            target = state.pending_target if state.pending_target is not None \
                else SERVICE_INDICES[0]
            state.phase_idx = target
            state.pending_target = None
            state.last_served_time[PHASES[state.phase_idx]["name"]] = current_time
            state.last_switch_time = current_time
            state.time_in_phase = 0
    else:
        if state.time_in_phase >= phase["max_green"]:
            best = adaptive_select(state.phase_idx, current_time,
                                   state.last_served_time, exclude_current=True)
            state.step_candidate_idx = best
            state.pending_target = best
            state.phase_idx = CLEARANCE_AFTER[state.phase_idx]
            state.time_in_phase = 0
        elif state.time_in_phase >= phase["min_green"]:
            candidate = adaptive_select(state.phase_idx, current_time,
                                        state.last_served_time)
            state.step_candidate_idx = candidate
            if candidate == state.phase_idx:
                return  # adaptive says stay

            # Run through shield
            allow, reason = shield_decision(state, current_time, candidate)
            if not allow:
                state.step_override_flag = True
                state.step_override_reason = reason
                return  # HOLD

            # Shield approved: ENTER_CLEARANCE
            state.pending_target = candidate
            state.phase_idx = CLEARANCE_AFTER[state.phase_idx]
            state.time_in_phase = 0


# ══════════════════════════════════════════════════════════════
#  Metrics collection
# ══════════════════════════════════════════════════════════════

# Starvation thresholds (seconds)
VEHICLE_STARVATION_THRESHOLD = 90  # vehicle waiting > 90s = starvation event
PED_STARVATION_THRESHOLD = 60     # ped waiting > 60s = starvation event
# Unnecessary switch: target phase demand <= this at time of switch
UNNECESSARY_SWITCH_DEMAND_THRESHOLD = 1


class Metrics:
    def __init__(self):
        self.total_steps = 0
        self.total_vehicle_queue = 0
        self.max_vehicle_queue = 0
        self.max_vehicle_waiting_time = 0.0
        self.max_ped_waiting_time = 0.0
        self.sum_vehicle_wait_means = 0.0
        self.sum_ped_wait_means = 0.0
        self.switch_count = 0
        # D1: Safety compliance
        self.conflict_release_count = 0      # should be 0 with valid phase table
        self.dangerous_switch_attempt_count = 0
        # D2: Service guarantee — p95 sample pools
        self.all_veh_waits = []
        self.all_ped_waits = []
        self.vehicle_starvation_ids = set()  # track unique starved entities
        self.ped_starvation_ids = set()
        # D3: Stability
        self.unnecessary_switch_count = 0
        self.last_switch_target_demand = None  # set by main loop

    def collect(self, current_service_idx, prev_service_idx):
        """Called once per simulation step."""
        self.total_steps += 1

        # Vehicle queue
        queue = sum(traci.lane.getLastStepHaltingNumber(l) for l in VEHICLE_LANES)
        self.total_vehicle_queue += queue
        if queue > self.max_vehicle_queue:
            self.max_vehicle_queue = queue

        # Vehicle waiting time
        veh_ids = traci.vehicle.getIDList()
        veh_wait_sum = 0.0
        for vid in veh_ids:
            wt = traci.vehicle.getWaitingTime(vid)
            veh_wait_sum += wt
            self.all_veh_waits.append(wt)
            if wt > self.max_vehicle_waiting_time:
                self.max_vehicle_waiting_time = wt
            if wt > VEHICLE_STARVATION_THRESHOLD and vid not in self.vehicle_starvation_ids:
                self.vehicle_starvation_ids.add(vid)
        if veh_ids:
            self.sum_vehicle_wait_means += veh_wait_sum / len(veh_ids)

        # Pedestrian waiting time
        ped_ids = traci.person.getIDList()
        ped_wait_sum = 0.0
        for pid in ped_ids:
            wt = traci.person.getWaitingTime(pid)
            ped_wait_sum += wt
            self.all_ped_waits.append(wt)
            if wt > self.max_ped_waiting_time:
                self.max_ped_waiting_time = wt
            if wt > PED_STARVATION_THRESHOLD and pid not in self.ped_starvation_ids:
                self.ped_starvation_ids.add(pid)
        if ped_ids:
            self.sum_ped_wait_means += ped_wait_sum / len(ped_ids)

        # Switch count
        if (current_service_idx != prev_service_idx
                and current_service_idx in SERVICE_INDICES
                and prev_service_idx in SERVICE_INDICES):
            self.switch_count += 1

    def record_dangerous_attempt(self):
        self.dangerous_switch_attempt_count += 1

    def record_unnecessary_switch(self):
        self.unnecessary_switch_count += 1

    def summary(self):
        n = self.total_steps if self.total_steps > 0 else 1
        avg_q = self.total_vehicle_queue / n
        avg_veh_wait = self.sum_vehicle_wait_means / n
        avg_ped_wait = self.sum_ped_wait_means / n

        # p95 computation
        def p95(vals):
            if not vals:
                return 0.0
            s = sorted(vals)
            idx = int(len(s) * 0.95)
            return s[min(idx, len(s) - 1)]

        # Switch rate normalized to 300s
        sim_dur = max(n, 1)
        switch_rate = self.switch_count / sim_dur * 300

        return {
            "average_vehicle_queue_length": round(avg_q, 3),
            "max_vehicle_queue_length": self.max_vehicle_queue,
            "average_vehicle_waiting_time": round(avg_veh_wait, 1),
            "max_vehicle_waiting_time": round(self.max_vehicle_waiting_time, 1),
            "average_ped_waiting_time": round(avg_ped_wait, 1),
            "max_ped_waiting_time": round(self.max_ped_waiting_time, 1),
            "switch_count": self.switch_count,
            # D1: Safety compliance
            "conflict_release_count": self.conflict_release_count,
            "dangerous_switch_attempt_count": self.dangerous_switch_attempt_count,
            # D2: Service guarantee
            "vehicle_wait_p95": round(p95(self.all_veh_waits), 1),
            "ped_wait_p95": round(p95(self.all_ped_waits), 1),
            "vehicle_starvation_count": len(self.vehicle_starvation_ids),
            "ped_starvation_count": len(self.ped_starvation_ids),
            # D3: Stability
            "switch_rate_per_300s": round(switch_rate, 2),
            "unnecessary_switch_count": self.unnecessary_switch_count,
            "unnecessary_switch_rate": round(
                self.unnecessary_switch_count / max(self.switch_count, 1), 3),
        }


# ══════════════════════════════════════════════════════════════
#  Main experiment runner
# ══════════════════════════════════════════════════════════════

CONTROLLERS = {
    "fixed_time": step_fixed_time,
    "actuated": step_actuated,
    "adaptive_only": step_adaptive_only,
    "adaptive_shield": step_adaptive_shield,
}

CFGS = {
    "intersection_ped": "intersection_ped.sumocfg",
    "intersection_ped_near": "intersection_ped_near.sumocfg",
    "intersection_balanced": "intersection_balanced.sumocfg",
    "intersection_ped_heavy": "intersection_ped_heavy.sumocfg",
    "intersection_vehicle_heavy": "intersection_vehicle_heavy.sumocfg",
    "intersection_bursty_ped": "intersection_bursty_ped.sumocfg",
    "intersection_directional_surge": "intersection_directional_surge.sumocfg",
    "intersection_combined_stress": "intersection_combined_stress.sumocfg",
}


def _get_true_demand():
    """Read raw TraCI demand (bypassing uncertainty layer)."""
    return {
        "veh_queue_ns": sum(traci.lane.getLastStepHaltingNumber(l) for l in LANES_NS),
        "veh_queue_ew": sum(traci.lane.getLastStepHaltingNumber(l) for l in LANES_EW),
        "ped_wait_ew": sum(1 for p in traci.person.getIDList()
                           if traci.person.getRoadID(p) in PED_WAIT_AREAS_EW
                           and traci.person.getWaitingTime(p) > 0),
        "ped_wait_ns": sum(1 for p in traci.person.getIDList()
                           if traci.person.getRoadID(p) in PED_WAIT_AREAS_NS
                           and traci.person.getWaitingTime(p) > 0),
    }


def run(controller_name, cfg_name, sim_duration, use_gui, seed=None,
        uncertainty_config=None, scenario_id=None):
    global _unc_layer

    sumo_binary = "sumo-gui" if use_gui else "sumo"
    cfg_file = os.path.join(SUMO_CFG_DIR, CFGS[cfg_name])

    seed_str = f"  seed={seed}" if seed is not None else ""
    print(f"[CONFIG] controller={controller_name}  cfg={cfg_name}  "
          f"duration={sim_duration}s  gui={use_gui}{seed_str}")

    # Set up uncertainty layer if config provided
    if uncertainty_config:
        from core.uncertainty import UncertaintyLayer
        _unc_layer = UncertaintyLayer(uncertainty_config, seed=seed)
        print(f"[UNCERTAINTY] {_unc_layer.describe()}")
    else:
        _unc_layer = None

    step_fn = CONTROLLERS[controller_name]
    needs_time = controller_name in ("adaptive_only", "adaptive_shield")

    state = ControllerState()
    metrics = Metrics()

    # Step logger
    from core.experiment_logger import StepLogger
    label = scenario_id if scenario_id else cfg_name
    logger = StepLogger(controller_name, label, seed)

    cmd = [sumo_binary, "-c", cfg_file]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    traci.start(cmd)
    try:
        tl_state = traci.trafficlight.getRedYellowGreenState(TL_ID)
        for ph in PHASES:
            if len(ph["state"]) != len(tl_state):
                print(f"[ERROR] Phase state length mismatch. Aborting.")
                return None
        print(f"[OK] TL '{TL_ID}' state length: {len(tl_state)}\n")

        while traci.simulation.getTime() < sim_duration:
            # Apply current phase
            traci.trafficlight.setRedYellowGreenState(
                TL_ID, PHASES[state.phase_idx]["state"])
            traci.simulationStep()

            # Step uncertainty layer
            t = traci.simulation.getTime()
            if _unc_layer:
                _unc_layer.step(t)

            # Snapshot state before controller step
            prev_phase_idx = state.phase_idx
            prev_service = state.prev_service_idx
            prev_tip = state.time_in_phase

            # Reset per-step tracking
            state.step_candidate_idx = prev_phase_idx  # default: stay
            state.step_override_flag = False
            state.step_override_reason = ""

            # Step controller
            if needs_time:
                step_fn(state, t)
            else:
                step_fn(state)

            # Derive step events from before/after comparison
            new_phase_idx = state.phase_idx
            switch_event = (prev_phase_idx != new_phase_idx)
            entered_clearance = switch_event and PHASES[new_phase_idx]["clearance"]

            # Update service phase tracker
            if state.phase_idx in SERVICE_INDICES:
                state.prev_service_idx = state.phase_idx

            # ── Conflict detection (real check, not hardcoded) ──
            # Verify the TL state we just applied is valid, and no clearance was skipped
            applied_state = PHASES[prev_phase_idx]["state"]
            conflict, conflict_reason = check_conflict(applied_state, prev_phase_idx, new_phase_idx)
            if conflict:
                metrics.conflict_release_count += 1

            # ── Dangerous switch attempt ──
            # Definition: the controller attempted or executed a switch from a
            # service phase before min_green was satisfied. Includes:
            #   (a) Actual switches that happened before min_green (should be rare)
            #   (b) Shield-blocked attempts where the candidate would have switched
            #       before min_green (captured via override_reason containing "min_hold")
            dangerous = False
            # Note: prev_tip is BEFORE the step function's internal += 1.
            # The controller's actual decision time_in_phase = prev_tip + 1.
            controller_tip = prev_tip + 1
            if not PHASES[prev_phase_idx]["clearance"]:
                # Case (a): actual switch before min_green
                if switch_event and controller_tip < PHASES[prev_phase_idx]["min_green"]:
                    dangerous = True
                # Case (b): shield blocked a premature switch attempt
                if (state.step_override_flag
                        and "min_hold" in state.step_override_reason):
                    dangerous = True
            if dangerous:
                metrics.record_dangerous_attempt()

            # ── Unnecessary switch ──
            # Unified definition for all controllers:
            # A service-phase transition where the NEW service phase entered has
            # effective demand <= UNNECESSARY_SWITCH_DEMAND_THRESHOLD at the moment
            # of entry. Checked when a new service phase begins (not during clearance).
            unnecessary = False
            if (state.phase_idx in SERVICE_INDICES
                    and state.prev_service_idx != prev_service
                    and state.prev_service_idx in SERVICE_INDICES):
                # We just entered a new service phase
                entered_name = PHASES[state.prev_service_idx]["name"]
                entered_demand = compute_demand(entered_name)
                if entered_demand <= UNNECESSARY_SWITCH_DEMAND_THRESHOLD:
                    unnecessary = True
                    metrics.record_unnecessary_switch()

            # Collect metrics
            metrics.collect(state.prev_service_idx, prev_service)

            # Read observed demand (post-uncertainty) for logging
            obs_vq_ns = get_vehicle_queue(LANES_NS)
            obs_vq_ew = get_vehicle_queue(LANES_EW)
            obs_pw_ew = get_ped_waiting_count(PED_WAIT_AREAS_EW)
            obs_pw_ns = get_ped_waiting_count(PED_WAIT_AREAS_NS)
            obs_vd_ns = 1 if has_vehicle_demand(LANES_NS) else 0
            obs_vd_ew = 1 if has_vehicle_demand(LANES_EW) else 0
            obs_pd_ew = 1 if has_ped_demand(PED_WAIT_AREAS_EW) else 0
            obs_pd_ns = 1 if has_ped_demand(PED_WAIT_AREAS_NS) else 0

            # True demand (raw TraCI)
            true_d = _get_true_demand()

            # Uncertainty state
            delay_active = _unc_layer is not None and _unc_layer.delay is not None
            false_ped_active = _unc_layer is not None and _unc_layer.false_ped is not None
            failure_active = (_unc_layer is not None and _unc_layer.failure is not None
                              and _unc_layer.failure.is_active(t))
            failure_mode = _unc_layer.failure.mode if (
                _unc_layer and _unc_layer.failure) else ""
            phantom_count = (_unc_layer.false_ped.get_phantom_count(
                PED_WAIT_AREAS_EW + PED_WAIT_AREAS_NS)
                if _unc_layer and _unc_layer.false_ped else 0)

            # Starvation flags for this step
            veh_starve = any(
                traci.vehicle.getWaitingTime(v) > VEHICLE_STARVATION_THRESHOLD
                for v in traci.vehicle.getIDList())
            ped_starve = any(
                traci.person.getWaitingTime(p) > PED_STARVATION_THRESHOLD
                for p in traci.person.getIDList())

            # Determine final action label
            if state.step_override_flag:
                final_action = "hold_by_shield"
            elif switch_event:
                final_action = "switch"
            else:
                final_action = "hold"

            candidate_idx = state.step_candidate_idx
            logger.log({
                "sim_time": t,
                "controller_name": controller_name,
                "scenario_name": cfg_name,
                "scenario_id": scenario_id or "",
                "seed": seed if seed is not None else "",
                "current_phase_idx": prev_phase_idx,
                "current_phase_name": PHASES[prev_phase_idx]["name"],
                "time_in_phase": prev_tip,
                "candidate_phase_idx": candidate_idx if candidate_idx is not None else prev_phase_idx,
                "candidate_phase_name": PHASES[candidate_idx]["name"] if candidate_idx is not None else PHASES[prev_phase_idx]["name"],
                "final_action": final_action,
                "switch_event": int(switch_event),
                "entered_clearance": int(entered_clearance),
                "override_flag": int(state.step_override_flag),
                "override_reason": state.step_override_reason,
                "veh_queue_ns_obs": obs_vq_ns,
                "veh_queue_ew_obs": obs_vq_ew,
                "ped_wait_ew_obs": obs_pw_ew,
                "ped_wait_ns_obs": obs_pw_ns,
                "veh_demand_ns_obs": obs_vd_ns,
                "veh_demand_ew_obs": obs_vd_ew,
                "ped_demand_ew_obs": obs_pd_ew,
                "ped_demand_ns_obs": obs_pd_ns,
                "veh_queue_ns_true": true_d["veh_queue_ns"],
                "veh_queue_ew_true": true_d["veh_queue_ew"],
                "ped_wait_ew_true": true_d["ped_wait_ew"],
                "ped_wait_ns_true": true_d["ped_wait_ns"],
                "delay_active": int(delay_active),
                "false_ped_active": int(false_ped_active),
                "detector_failure_active": int(failure_active),
                "failure_mode": failure_mode,
                "phantom_ped_count": phantom_count,
                "dangerous_switch_attempt_flag": int(dangerous),
                "conflict_flag": int(conflict),
                "vehicle_starvation_flag": int(veh_starve),
                "ped_starvation_flag": int(ped_starve),
                "unnecessary_switch_flag": int(unnecessary),
            })

        sim_time = traci.simulation.getTime()
    finally:
        traci.close()
        logger.close()

    print(f"[LOG] Step log: {logger.filepath}")

    # Build results
    results = {
        "controller_name": controller_name,
        "scenario_name": cfg_name,
        "sim_duration": sim_time,
    }
    if scenario_id:
        results["scenario_id"] = scenario_id
    results.update(metrics.summary())

    # Append shield debug stats for adaptive_shield
    if controller_name == "adaptive_shield":
        results["shield_hold_min_hold"] = state.shield_holds["min_hold"]
        results["shield_hold_small_gain"] = state.shield_holds["small_gain"]
        results["shield_override_starvation"] = state.shield_overrides["starvation"]
        results["shield_override_demand"] = state.shield_overrides["demand"]

    # Append uncertainty debug stats
    if _unc_layer:
        results.update(_unc_layer.debug_summary())

    _unc_layer = None
    return results


def main():
    parser = argparse.ArgumentParser(description="Run intersection experiment")
    parser.add_argument("--controller", required=True,
                        choices=list(CONTROLLERS.keys()),
                        help="Controller type")
    parser.add_argument("--cfg", default="intersection_ped_near",
                        choices=list(CFGS.keys()),
                        help="SUMO config name")
    parser.add_argument("--duration", type=int, default=200,
                        help="Simulation duration in seconds")
    parser.add_argument("--gui", action="store_true",
                        help="Use sumo-gui instead of headless sumo")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for SUMO (controls flow jitter etc.)")
    parser.add_argument("--scenario_id", default=None,
                        help="Scenario config name (e.g., S4_delay_detection). "
                             "Loads YAML and enables uncertainty injection.")
    args = parser.parse_args()

    # Resolve scenario config if provided
    uncertainty_config = None
    cfg_name = args.cfg
    if args.scenario_id:
        from core.scenario_loader import load_scenario
        scfg = load_scenario(args.scenario_id)

        if not scfg["can_run_base_mapping"]:
            print(f"[ERROR] Scenario '{args.scenario_id}' has status='{scfg['status']}' "
                  f"and cannot be executed. Pending features: {scfg['pending_features']}")
            print(f"[ERROR] This scenario config exists but runtime logic is not yet implemented.")
            return

        cfg_name = scfg["run_experiment_cfg"]
        uncertainty_config = scfg.get("uncertainty", None)
        print(f"[SCENARIO] Loaded {args.scenario_id} -> base cfg={cfg_name}")

    results = run(args.controller, cfg_name, args.duration, args.gui,
                  args.seed, uncertainty_config,
                  scenario_id=args.scenario_id)

    if results is None:
        print("[ERROR] Experiment failed.")
        return

    # Print results
    print("\n" + "=" * 50)
    print("  EXPERIMENT RESULTS")
    print("=" * 50)
    for k, v in results.items():
        print(f"  {k:<32} {v}")
    print("=" * 50)

    # Save to JSON — use scenario_id for filename if provided, else base cfg
    os.makedirs(RESULTS_DIR, exist_ok=True)
    label = args.scenario_id if args.scenario_id else results["scenario_name"]
    filename = f"{results['controller_name']}_{label}.json"
    filepath = os.path.join(RESULTS_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Results saved to {filepath}")


if __name__ == "__main__":
    main()
