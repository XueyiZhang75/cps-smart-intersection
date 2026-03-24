"""
TraCI Minimal Connection Test
Verifies that Python can connect to SUMO, read simulation state,
and retrieve traffic light information via TraCI.
"""

import traci

# ── Configuration ──────────────────────────────────────────────
# Switch to "sumo" for headless mode
SUMO_BINARY = "sumo-gui"
SUMO_CFG = r"E:\cps-smart-intersection\sumo\cfg\intersection_ped.sumocfg"

TOTAL_STEPS = 20
PRINT_EVERY = 5
# ───────────────────────────────────────────────────────────────

def main():
    traci.start([SUMO_BINARY, "-c", SUMO_CFG])
    try:
        print(f"[OK] Connected to SUMO via TraCI")
        print(f"  Simulation time: {traci.simulation.getTime()}")

        # Read traffic light IDs
        tl_ids = traci.trafficlight.getIDList()
        if not tl_ids:
            print("[WARN] No traffic lights found in network. Exiting.")
            return

        print(f"  Traffic light IDs: {list(tl_ids)}")
        tl_id = tl_ids[0]

        # Print initial TL state
        phase = traci.trafficlight.getPhase(tl_id)
        state = traci.trafficlight.getRedYellowGreenState(tl_id)
        phase_name = traci.trafficlight.getPhaseName(tl_id)
        print(f"  TL '{tl_id}' initial phase: {phase} ({phase_name})")
        print(f"  TL '{tl_id}' initial state: {state}")

        # Step simulation
        print(f"\n[RUN] Stepping {TOTAL_STEPS} times...")
        for step in range(1, TOTAL_STEPS + 1):
            traci.simulationStep()
            if step % PRINT_EVERY == 0:
                t = traci.simulation.getTime()
                p = traci.trafficlight.getPhase(tl_id)
                s = traci.trafficlight.getRedYellowGreenState(tl_id)
                n = traci.trafficlight.getPhaseName(tl_id)
                print(f"  step {step:3d} | time {t:6.1f} | phase {p} ({n}) | state {s}")

        print(f"\n[OK] TraCI connection test passed.")
    finally:
        traci.close()
        print("[OK] TraCI connection closed.")

if __name__ == "__main__":
    main()
