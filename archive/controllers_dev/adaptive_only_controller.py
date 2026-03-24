"""
Adaptive-Only Controller (No Safety Shield)
Controls J0 by scoring all candidate service phases and selecting the best.
Uses demand intensity, starvation penalty, and switch cost.

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

# ── Score weights ──────────────────────────────────────────────
W_Q = 2.0   # demand intensity weight
W_W = 3.0   # starvation penalty weight
W_C = 1.0   # switch cost weight
SCORE_EPSILON = 0.5   # tie-break: current phase advantage margin
WAIT_NORM = 102.0     # normalization for W_i (one full cycle, seconds)
# ───────────────────────────────────────────────────────────────

# ── Phase timing ───────────────────────────────────────────────
VEH_MIN_GREEN = 15
VEH_MAX_GREEN = 30
PED_MIN_GREEN = 10
PED_MAX_GREEN = 15
CLEARANCE_DUR = 3
# ───────────────────────────────────────────────────────────────

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

# Service phase indices (non-clearance) in fixed priority order for tie-break
SERVICE_INDICES = [0, 2, 4, 6]  # Vehicle_NS, Vehicle_EW, Ped_EW, Ped_NS

# Clearance phase that precedes each service phase
# To reach service phase i, we first run its preceding clearance
CLEARANCE_BEFORE = {
    0: 7,  # Vehicle_NS preceded by Clearance_after_Ped_NS
    2: 1,  # Vehicle_EW preceded by Clearance_after_NS
    4: 3,  # Ped_EW preceded by Clearance_after_EW
    6: 5,  # Ped_NS preceded by Clearance_after_Ped_EW
}

# ── Demand detection ──────────────────────────────────────────
# Vehicle lanes (_1 is vehicle lane, _0 is sidewalk)
LANES_NS = ["N2C_1", "S2C_1"]
LANES_EW = ["E2C_1", "W2C_1"]

# Ped walking areas (derived from signal semantics):
#   Ped_EW phase controls c1 (East, idx17) fed by w2, and c3 (West, idx19) fed by w0
#   Ped_NS phase controls c0 (North, idx16) fed by w1, and c2 (South, idx18) fed by w3
PED_WAIT_AREAS_EW = [":J0_w0", ":J0_w2"]
PED_WAIT_AREAS_NS = [":J0_w1", ":J0_w3"]


def get_vehicle_queue(lanes):
    """Q_i for vehicle phases: number of halting vehicles."""
    return sum(traci.lane.getLastStepHaltingNumber(l) for l in lanes)


def get_ped_waiting_count(wait_areas):
    """Q_i for ped phases: number of persons waiting on specified walking areas."""
    count = 0
    for pid in traci.person.getIDList():
        if traci.person.getRoadID(pid) in wait_areas:
            if traci.person.getWaitingTime(pid) > 0:
                count += 1
    return count


def compute_demand(phase_name):
    """Return Q_i (demand intensity) for a service phase."""
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
    """
    Score(i) = w_q * Q_i + w_w * W_i - w_c * C_i

    Q_i: demand intensity (halting vehicles or waiting peds)
    W_i: (current_time - last_served_time[i]) / WAIT_NORM
    C_i: 0 if i == current phase, 1 otherwise (switch cost)
    """
    scores = {}
    for idx in SERVICE_INDICES:
        name = PHASES[idx]["name"]
        q_i = compute_demand(name)
        w_i = (current_time - last_served_time[name]) / WAIT_NORM
        c_i = 0.0 if idx == current_service_idx else 1.0
        score = W_Q * q_i + W_W * w_i - W_C * c_i
        scores[idx] = {"score": score, "Q": q_i, "W": round(w_i, 2), "C": c_i}
    return scores


def select_best_phase(scores, current_service_idx):
    """
    Select highest-scoring service phase with tie-break rules:
    1. Current phase gets SCORE_EPSILON advantage (prefer staying)
    2. Among non-current candidates with equal scores, first in
       SERVICE_INDICES order wins (fixed priority tie-break)
    """
    current_score = scores[current_service_idx]["score"]

    # Find best score among all candidates
    best_idx = SERVICE_INDICES[0]
    best_score = scores[best_idx]["score"]
    for idx in SERVICE_INDICES:
        if scores[idx]["score"] > best_score:
            best_score = scores[idx]["score"]
            best_idx = idx

    # Tie-break layer 1: current phase advantage
    if current_score >= best_score - SCORE_EPSILON:
        return current_service_idx

    return best_idx


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
        phase_idx = 0        # start at Vehicle_NS
        time_in_phase = 0
        last_served_time = {PHASES[i]["name"]: 0.0 for i in SERVICE_INDICES}
        pending_target = None  # service phase to jump to after clearance

        header = f"{'Time':>6}  {'Ph':>2}  {'Name':<26}  {'Dur':>3}  "
        header += "Scores [VNS VEW PEW PNS]  Decision"
        print(header)
        print("-" * 95)

        while traci.simulation.getTime() < SIM_DURATION:
            phase = PHASES[phase_idx]
            traci.trafficlight.setRedYellowGreenState(TL_ID, phase["state"])
            traci.simulationStep()
            time_in_phase += 1
            t = traci.simulation.getTime()

            should_switch = False
            decision = ""
            score_str = ""

            if phase["clearance"]:
                # Clearance: fixed duration, then go to pending target
                if time_in_phase >= phase["duration"]:
                    should_switch = True
                    decision = "clearance done"
            else:
                # Service phase
                if time_in_phase >= phase["max_green"]:
                    # Max green: forced switch — score to pick next
                    scores = compute_scores(phase_idx, t, last_served_time)
                    # Exclude current phase from selection (forced to leave)
                    best_idx = None
                    best_score = -999
                    for idx in SERVICE_INDICES:
                        if idx != phase_idx and scores[idx]["score"] > best_score:
                            best_score = scores[idx]["score"]
                            best_idx = idx
                    pending_target = best_idx
                    score_str = fmt_scores(scores)
                    should_switch = True
                    decision = f"max_green -> {PHASES[best_idx]['name']}"
                elif time_in_phase >= phase["min_green"]:
                    # Between min and max: score-based decision
                    scores = compute_scores(phase_idx, t, last_served_time)
                    best_idx = select_best_phase(scores, phase_idx)
                    score_str = fmt_scores(scores)
                    if best_idx != phase_idx:
                        pending_target = best_idx
                        should_switch = True
                        decision = f"better option -> {PHASES[best_idx]['name']}"

            if should_switch:
                print(f"{t:6.1f}  {phase_idx:>2}  {phase['name']:<26}  "
                      f"{time_in_phase:>3}s  {score_str}  {decision}")

                if phase["clearance"]:
                    # After clearance, jump to pending target
                    if pending_target is not None:
                        phase_idx = pending_target
                        pending_target = None
                    else:
                        # Fallback: next service phase in sequence
                        phase_idx = (phase_idx + 1) % len(PHASES)
                    # Update last_served_time when entering new service phase
                    last_served_time[PHASES[phase_idx]["name"]] = t
                else:
                    # Enter clearance before the target service phase
                    if pending_target is not None:
                        phase_idx = CLEARANCE_BEFORE[pending_target]
                    else:
                        phase_idx = (phase_idx + 1) % len(PHASES)

                time_in_phase = 0

        print(f"\n[OK] Adaptive-only controller ran for {SIM_DURATION}s.")
    finally:
        traci.close()
        print("[OK] TraCI connection closed.")


def fmt_scores(scores):
    """Format scores dict into a compact string."""
    parts = []
    for idx in SERVICE_INDICES:
        s = scores[idx]
        parts.append(f"{s['score']:+5.1f}")
    return "[" + " ".join(parts) + "]"


if __name__ == "__main__":
    main()
