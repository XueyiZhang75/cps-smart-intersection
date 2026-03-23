"""
Adaptive + Safety Shield Controller
Two-layer design:
  Upper: Adaptive scheduler (score-based phase selection)
  Lower: Safety shield (filters candidate actions before execution)

NOTE: This is a first-pass debug controller tuned for
intersection_ped_near.sumocfg. Ped demand detection relies on
walking-area waiting and is not generalized for all scenarios.
Weights and parameters are initial values, not final experiment config.
"""

import traci

# ── Configuration ──────────────────────────────────────────────
SUMO_BINARY = "sumo-gui"  # Switch to "sumo" for headless mode
SUMO_CFG = r"E:\cps-smart-intersection\sumo\cfg\intersection_ped_near.sumocfg"
TL_ID = "J0"
SIM_DURATION = 200  # seconds
# ───────────────────────────────────────────────────────────────

# ── Adaptive score weights ─────────────────────────────────────
W_Q = 2.0   # demand intensity weight
W_W = 3.0   # starvation penalty weight
W_C = 1.0   # switch cost weight
SCORE_EPSILON = 0.5   # tie-break: current phase advantage margin
WAIT_NORM = 102.0     # normalization for W_i (seconds)
# ───────────────────────────────────────────────────────────────

# ── Phase timing ───────────────────────────────────────────────
VEH_MIN_GREEN = 15
VEH_MAX_GREEN = 30
PED_MIN_GREEN = 10
PED_MAX_GREEN = 15
CLEARANCE_DUR = 3
# ───────────────────────────────────────────────────────────────

# ── Safety shield parameters ──────────────────────────────────
MIN_SWITCH_INTERVAL = 8  # seconds — minimum gap between phase switches
# ───────────────────────────────────────────────────────────────

# Shield action types
HOLD = "HOLD"
ENTER_CLEARANCE = "ENTER_CLEARANCE"
EXECUTE = "EXECUTE"

# 8-phase plan
#   State string: 20 chars
#     [0-3]   N2C vehicle    [4-7]   E2C vehicle
#     [8-11]  S2C vehicle    [12-15] W2C vehicle
#     [16] North arm crossing (c0)   [17] East arm crossing (c1)
#     [18] South arm crossing (c2)   [19] West arm crossing (c3)

PHASES = [
    {"name": "Vehicle_NS",             "state": "GGggrrrrGGggrrrrrrrr",
     "min_green": VEH_MIN_GREEN, "max_green": VEH_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_NS",     "state": "yyyyrrrryyyyrrrrrrrr",
     "duration": CLEARANCE_DUR, "clearance": True},
    {"name": "Vehicle_EW",             "state": "rrrrGGggrrrrGGggrrrr",
     "min_green": VEH_MIN_GREEN, "max_green": VEH_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_EW",     "state": "rrrryyyyrrrryyyyrrrr",
     "duration": CLEARANCE_DUR, "clearance": True},
    {"name": "Ped_EW",                 "state": "rrrrrrrrrrrrrrrrrGrG",
     "min_green": PED_MIN_GREEN, "max_green": PED_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_Ped_EW", "state": "rrrrrrrrrrrrrrrrrrrr",
     "duration": CLEARANCE_DUR, "clearance": True},
    {"name": "Ped_NS",                 "state": "rrrrrrrrrrrrrrrrGrGr",
     "min_green": PED_MIN_GREEN, "max_green": PED_MAX_GREEN, "clearance": False},
    {"name": "Clearance_after_Ped_NS", "state": "rrrrrrrrrrrrrrrrrrrr",
     "duration": CLEARANCE_DUR, "clearance": True},
]

VALID_STATES = {ph["state"] for ph in PHASES}

# Service phase indices in fixed priority order (for tie-break)
SERVICE_INDICES = [0, 2, 4, 6]

# Clearance phase that follows each service phase
CLEARANCE_AFTER = {
    0: 1,  # Vehicle_NS  -> Clearance_after_NS
    2: 3,  # Vehicle_EW  -> Clearance_after_EW
    4: 5,  # Ped_EW      -> Clearance_after_Ped_EW
    6: 7,  # Ped_NS      -> Clearance_after_Ped_NS
}

# ── Demand detection ──────────────────────────────────────────
LANES_NS = ["N2C_1", "S2C_1"]
LANES_EW = ["E2C_1", "W2C_1"]
PED_WAIT_AREAS_EW = [":J0_w0", ":J0_w2"]
PED_WAIT_AREAS_NS = [":J0_w1", ":J0_w3"]


def get_vehicle_queue(lanes):
    return sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes)


def get_ped_waiting_count(wait_areas):
    count = 0
    for pid in traci.person.getIDList():
        if traci.person.getRoadID(pid) in wait_areas:
            if traci.person.getWaitingTime(pid) > 0:
                count += 1
    return count


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


# ── Upper layer: Adaptive scheduler ──────────────────────────

def compute_scores(current_service_idx, current_time, last_served_time):
    """Score(i) = w_q * Q_i + w_w * W_i - w_c * C_i"""
    scores = {}
    for idx in SERVICE_INDICES:
        name = PHASES[idx]["name"]
        q_i = compute_demand(name)
        w_i = (current_time - last_served_time[name]) / WAIT_NORM
        c_i = 0.0 if idx == current_service_idx else 1.0
        score = W_Q * q_i + W_W * w_i - W_C * c_i
        scores[idx] = {"score": score, "Q": q_i, "W": round(w_i, 2), "C": c_i}
    return scores


def adaptive_select(current_service_idx, current_time, last_served_time,
                    exclude_current=False):
    """Return (best_service_idx, scores_dict)."""
    scores = compute_scores(current_service_idx, current_time, last_served_time)

    if exclude_current:
        # max_green forced: pick best among others
        best_idx = None
        best_score = -999
        for idx in SERVICE_INDICES:
            if idx != current_service_idx and scores[idx]["score"] > best_score:
                best_score = scores[idx]["score"]
                best_idx = idx
        return best_idx, scores

    # Normal selection with tie-break
    current_score = scores[current_service_idx]["score"]
    best_idx = SERVICE_INDICES[0]
    best_score = scores[best_idx]["score"]
    for idx in SERVICE_INDICES:
        if scores[idx]["score"] > best_score:
            best_score = scores[idx]["score"]
            best_idx = idx

    # Tie-break: current phase advantage
    if current_score >= best_score - SCORE_EPSILON:
        return current_service_idx, scores

    return best_idx, scores


# ── Lower layer: Safety shield ───────────────────────────────

def shield_filter(candidate_idx, current_idx, time_in_phase,
                  current_time, last_switch_time):
    """
    Filter the adaptive scheduler's candidate through safety rules.

    Returns (action, reason):
      HOLD             — reject, keep current phase
      ENTER_CLEARANCE  — approve switch, but must go through clearance first
      EXECUTE          — direct execution allowed (only after clearance)
    """
    phase = PHASES[current_idx]

    # Rule 1: min_green_guard (reject)
    if not phase["clearance"] and time_in_phase < phase["min_green"]:
        return HOLD, f"min_green not met ({time_in_phase}/{phase['min_green']})"

    # Rule 2: anti_oscillation (reject)
    elapsed = current_time - last_switch_time
    if elapsed < MIN_SWITCH_INTERVAL:
        return HOLD, f"anti-oscillation ({elapsed:.0f}s < {MIN_SWITCH_INTERVAL}s)"

    # Rule 3: valid_state_guard (reject)
    if PHASES[candidate_idx]["state"] not in VALID_STATES:
        return HOLD, "invalid state string"

    # Rule 4: clearance_enforcement (transition)
    if not phase["clearance"] and candidate_idx != current_idx:
        return ENTER_CLEARANCE, "clearance required before switch"

    # All rules passed
    return EXECUTE, "allowed"


# ── Formatting helpers ────────────────────────────────────────

def fmt_scores(scores):
    parts = []
    for idx in SERVICE_INDICES:
        parts.append(f"{scores[idx]['score']:+5.1f}")
    return "[" + " ".join(parts) + "]"


def short_name(idx):
    return PHASES[idx]["name"]


# ── Main control loop ────────────────────────────────────────

def main():
    traci.start([SUMO_BINARY, "-c", SUMO_CFG])
    try:
        # ── Sanity check ──
        current_state = traci.trafficlight.getRedYellowGreenState(TL_ID)
        print(f"[CHECK] TL '{TL_ID}' state length: {len(current_state)}")
        for i, ph in enumerate(PHASES):
            if len(ph["state"]) != len(current_state):
                print(f"[ERROR] Phase {i} '{ph['name']}' length mismatch. Aborting.")
                return
        print(f"[OK] All phase state lengths match.\n")

        # ── State initialization ──
        phase_idx = 0
        time_in_phase = 0
        last_served_time = {PHASES[i]["name"]: 0.0 for i in SERVICE_INDICES}
        last_switch_time = 0.0
        pending_target = None

        hdr = (f"{'Time':>6}  {'Ph':>2}  {'Name':<26}  {'Dur':>3}  "
               f"Scores [VNS VEW PEW PNS]  Shield           Action")
        print(hdr)
        print("-" * 110)

        while traci.simulation.getTime() < SIM_DURATION:
            phase = PHASES[phase_idx]
            traci.trafficlight.setRedYellowGreenState(TL_ID, phase["state"])
            traci.simulationStep()
            time_in_phase += 1
            t = traci.simulation.getTime()

            if phase["clearance"]:
                # ── Clearance phase: fixed duration, then enter pending target ──
                if time_in_phase >= phase["duration"]:
                    target = pending_target if pending_target is not None else SERVICE_INDICES[0]
                    print(f"{t:6.1f}  {phase_idx:>2}  {phase['name']:<26}  "
                          f"{time_in_phase:>3}s  {'':>25}  {'':>15}  "
                          f"clearance done -> {short_name(target)}")
                    phase_idx = target
                    pending_target = None
                    time_in_phase = 0
                    last_served_time[PHASES[phase_idx]["name"]] = t
                    last_switch_time = t

            else:
                # ── Service phase ──
                if time_in_phase >= phase["max_green"]:
                    # Forced switch: pick best other phase, go through clearance
                    candidate, scores = adaptive_select(
                        phase_idx, t, last_served_time, exclude_current=True)
                    clearance_idx = CLEARANCE_AFTER[phase_idx]
                    pending_target = candidate
                    score_str = fmt_scores(scores)
                    print(f"{t:6.1f}  {phase_idx:>2}  {phase['name']:<26}  "
                          f"{time_in_phase:>3}s  {score_str}  "
                          f"{'max_green forced':<15}  "
                          f"ENTER_CLEARANCE -> {short_name(candidate)}")
                    phase_idx = clearance_idx
                    time_in_phase = 0

                elif time_in_phase >= phase["min_green"]:
                    # Score-based decision
                    candidate, scores = adaptive_select(
                        phase_idx, t, last_served_time)

                    if candidate == phase_idx:
                        # Adaptive says stay — no shield needed
                        continue

                    # Adaptive wants to switch — run through shield
                    action, reason = shield_filter(
                        candidate, phase_idx, time_in_phase, t, last_switch_time)

                    score_str = fmt_scores(scores)

                    if action == HOLD:
                        print(f"{t:6.1f}  {phase_idx:>2}  {phase['name']:<26}  "
                              f"{time_in_phase:>3}s  {score_str}  "
                              f"HOLD({reason[:15]:<15})  "
                              f"keep {short_name(phase_idx)}")

                    elif action == ENTER_CLEARANCE:
                        clearance_idx = CLEARANCE_AFTER[phase_idx]
                        pending_target = candidate
                        print(f"{t:6.1f}  {phase_idx:>2}  {phase['name']:<26}  "
                              f"{time_in_phase:>3}s  {score_str}  "
                              f"{'PASS':>15}  "
                              f"ENTER_CLEARANCE -> {short_name(candidate)}")
                        phase_idx = clearance_idx
                        time_in_phase = 0

                    elif action == EXECUTE:
                        # Should not happen from service->service, but handle
                        pending_target = candidate
                        clearance_idx = CLEARANCE_AFTER[phase_idx]
                        phase_idx = clearance_idx
                        time_in_phase = 0

        print(f"\n[OK] Adaptive+Shield controller ran for {SIM_DURATION}s.")
    finally:
        traci.close()
        print("[OK] TraCI connection closed.")


if __name__ == "__main__":
    main()
