"""
Fixed-Time Controller (Baseline 1)
Controls J0 traffic light with an explicit 8-phase fixed cycle via TraCI.
"""

import traci

# ── Configuration ──────────────────────────────────────────────
SUMO_BINARY = "sumo-gui"  # Switch to "sumo" for headless mode
#SUMO_CFG = r"E:\cps-smart-intersection\sumo\cfg\intersection_ped.sumocfg"
SUMO_CFG = r"E:\cps-smart-intersection\sumo\cfg\intersection_ped_near.sumocfg"
TL_ID = "J0"
SIM_DURATION = 150  # seconds
# ───────────────────────────────────────────────────────────────

# 8-phase fixed-time plan (total cycle = 102s)
#   State string: 20 chars
#     [0-3]   N2C vehicle (right/straight/left/u-turn)
#     [4-7]   E2C vehicle
#     [8-11]  S2C vehicle
#     [12-15] W2C vehicle
#     [16] North arm crossing    [17] East arm crossing
#     [18] South arm crossing    [19] West arm crossing

PHASES = [
    {"name": "Vehicle_NS",            "duration": 30, "state": "GGggrrrrGGggrrrrrrrr"},
    {"name": "Clearance_after_NS",    "duration":  3, "state": "yyyyrrrryyyyrrrrrrrr"},
    {"name": "Vehicle_EW",            "duration": 30, "state": "rrrrGGggrrrrGGggrrrr"},
    {"name": "Clearance_after_EW",    "duration":  3, "state": "rrrryyyyrrrryyyyrrrr"},
    {"name": "Ped_EW",                "duration": 15, "state": "rrrrrrrrrrrrrrrrrGrG"},
    {"name": "Clearance_after_Ped_EW","duration":  3, "state": "rrrrrrrrrrrrrrrrrrrr"},
    {"name": "Ped_NS",                "duration": 15, "state": "rrrrrrrrrrrrrrrrGrGr"},
    {"name": "Clearance_after_Ped_NS","duration":  3, "state": "rrrrrrrrrrrrrrrrrrrr"},
]


def main():
    traci.start([SUMO_BINARY, "-c", SUMO_CFG])
    try:
        # ── Sanity check: verify state length matches network ──
        current_state = traci.trafficlight.getRedYellowGreenState(TL_ID)
        print(f"[CHECK] TL ID:        {TL_ID}")
        print(f"[CHECK] Current state: {current_state}")
        print(f"[CHECK] State length:  {len(current_state)}")
        for i, ph in enumerate(PHASES):
            if len(ph["state"]) != len(current_state):
                print(f"[ERROR] Phase {i} '{ph['name']}' state length {len(ph['state'])} "
                      f"!= network state length {len(current_state)}. Aborting.")
                return
        print(f"[OK] All phase state lengths match ({len(current_state)} chars).\n")

        # ── Fixed-time control loop ──
        phase_idx = 0
        time_in_phase = 0
        phase = PHASES[phase_idx]

        print(f"{'Time':>6}  {'Phase':>3}  {'Name':<26}  State")
        print("-" * 70)

        while traci.simulation.getTime() < SIM_DURATION:
            # Set TL state every step (TraCI explicit control)
            traci.trafficlight.setRedYellowGreenState(TL_ID, phase["state"])
            traci.simulationStep()
            time_in_phase += 1

            # ── Pedestrian monitoring (every 5s) ──
            t = traci.simulation.getTime()
            if t % 5 == 0:
                persons = traci.person.getIDList()
                if persons:
                    print(f"  [PED] t={t:.0f}s | active persons: {list(persons)}")
                    for pid in persons:
                        edge = traci.person.getRoadID(pid)
                        lane = traci.person.getLaneID(pid)
                        print(f"         {pid}: edge={edge}, lane={lane}")
                else:
                    print(f"  [PED] t={t:.0f}s | no active persons")

            # Check if current phase duration is reached
            if time_in_phase >= phase["duration"]:
                t = traci.simulation.getTime()
                print(f"{t:6.1f}  {phase_idx:>3}  {phase['name']:<26}  {phase['state']}  (done)")
                phase_idx = (phase_idx + 1) % len(PHASES)
                phase = PHASES[phase_idx]
                time_in_phase = 0

        print(f"\n[OK] Fixed-time controller ran for {SIM_DURATION}s.")
    finally:
        traci.close()
        print("[OK] TraCI connection closed.")


if __name__ == "__main__":
    main()
