"""
Actuated Controller (Baseline 2)
Controls J0 with demand-responsive phase switching after minimum green.
Simplified ped demand detection — tuned for intersection_ped_near.sumocfg.
"""

import traci

# ── Configuration ──────────────────────────────────────────────
SUMO_BINARY = "sumo-gui"  # Switch to "sumo" for headless mode
SUMO_CFG = r"E:\cps-smart-intersection\sumo\cfg\intersection_ped_near.sumocfg"
TL_ID = "J0"
SIM_DURATION = 200  # seconds
# ───────────────────────────────────────────────────────────────

# 8-phase plan
#   State string: 20 chars
#     [0-3]   N2C vehicle    [4-7]   E2C vehicle
#     [8-11]  S2C vehicle    [12-15] W2C vehicle
#     [16] North arm crossing (c0)   [17] East arm crossing (c1)
#     [18] South arm crossing (c2)   [19] West arm crossing (c3)

PHASES = [
    {"name": "Vehicle_NS",             "state": "GGggrrrrGGggrrrrrrrr",
     "min_green": 15, "max_green": 30, "clearance": False},
    {"name": "Clearance_after_NS",     "state": "yyyyrrrryyyyrrrrrrrr",
     "duration": 3, "clearance": True},
    {"name": "Vehicle_EW",             "state": "rrrrGGggrrrrGGggrrrr",
     "min_green": 15, "max_green": 30, "clearance": False},
    {"name": "Clearance_after_EW",     "state": "rrrryyyyrrrryyyyrrrr",
     "duration": 3, "clearance": True},
    {"name": "Ped_EW",                 "state": "rrrrrrrrrrrrrrrrrGrG",
     "min_green": 10, "max_green": 15, "clearance": False},
    {"name": "Clearance_after_Ped_EW", "state": "rrrrrrrrrrrrrrrrrrrr",
     "duration": 3, "clearance": True},
    {"name": "Ped_NS",                 "state": "rrrrrrrrrrrrrrrrGrGr",
     "min_green": 10, "max_green": 15, "clearance": False},
    {"name": "Clearance_after_Ped_NS", "state": "rrrrrrrrrrrrrrrrrrrr",
     "duration": 3, "clearance": True},
]

# ── Demand detection ──────────────────────────────────────────
# Vehicle: check vehicle lane (_1, since _0 is sidewalk)
LANES_NS = ["N2C_1", "S2C_1"]
LANES_EW = ["E2C_1", "W2C_1"]

# Ped: derived from signal semantics
#   Ped_EW phase controls c1 (East, idx17) and c3 (West, idx19)
#     c3 fed by w0, c1 fed by w2 → check w0, w2
#   Ped_NS phase controls c0 (North, idx16) and c2 (South, idx18)
#     c0 fed by w1, c2 fed by w3 → check w1, w3
PED_WAIT_AREAS_EW = [":J0_w0", ":J0_w2"]
PED_WAIT_AREAS_NS = [":J0_w1", ":J0_w3"]


def has_vehicle_demand(lanes):
    return any(traci.lane.getLastStepVehicleNumber(l) > 0 for l in lanes)


def has_ped_demand(wait_areas):
    """Check if any person is waiting on the specified walking areas."""
    for pid in traci.person.getIDList():
        edge = traci.person.getRoadID(pid)
        if edge in wait_areas and traci.person.getWaitingTime(pid) > 0:
            return True
    return False


def get_other_demand(current_phase_idx):
    """Check if any other service phase has demand."""
    demands = {
        "Vehicle_NS": has_vehicle_demand(LANES_NS),
        "Vehicle_EW": has_vehicle_demand(LANES_EW),
        "Ped_EW":     has_ped_demand(PED_WAIT_AREAS_EW),
        "Ped_NS":     has_ped_demand(PED_WAIT_AREAS_NS),
    }
    current_name = PHASES[current_phase_idx]["name"]
    other = {k: v for k, v in demands.items() if k != current_name}
    return demands, any(other.values())


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

        # ── Control loop ──
        phase_idx = 0
        time_in_phase = 0

        print(f"{'Time':>6}  {'Ph':>2}  {'Name':<26}  {'Dur':>3}  Reason")
        print("-" * 75)

        while traci.simulation.getTime() < SIM_DURATION:
            phase = PHASES[phase_idx]
            traci.trafficlight.setRedYellowGreenState(TL_ID, phase["state"])
            traci.simulationStep()
            time_in_phase += 1

            should_switch = False
            reason = ""

            if phase["clearance"]:
                # Clearance phases: fixed duration, always switch
                if time_in_phase >= phase["duration"]:
                    should_switch = True
                    reason = "clearance done"
            else:
                # Service phases: min/max green with demand check
                if time_in_phase >= phase["max_green"]:
                    should_switch = True
                    reason = "max_green reached"
                elif time_in_phase >= phase["min_green"]:
                    demands, other_has_demand = get_other_demand(phase_idx)
                    if other_has_demand:
                        should_switch = True
                        active = [k for k, v in demands.items() if v and k != phase["name"]]
                        reason = f"other demand: {', '.join(active)}"

            if should_switch:
                t = traci.simulation.getTime()
                print(f"{t:6.1f}  {phase_idx:>2}  {phase['name']:<26}  {time_in_phase:>3}s  {reason}")
                phase_idx = (phase_idx + 1) % len(PHASES)
                time_in_phase = 0

        print(f"\n[OK] Actuated controller ran for {SIM_DURATION}s.")
    finally:
        traci.close()
        print("[OK] TraCI connection closed.")


if __name__ == "__main__":
    main()
