"""
Batch Experiment Runner
Runs the full formal experiment matrix (4 scenarios x 4 controllers)
and outputs aggregated results as JSON + CSV.

Usage:
  python scripts/run_batch_experiments.py
"""

import csv
import json
import os
import sys

# Ensure scripts/ is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_experiment import run

# ── Configuration ──────────────────────────────────────────────
PROJECT_ROOT = r"E:\cps-smart-intersection"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
SIM_DURATION = 300

SCENARIOS = [
    "intersection_balanced",
    "intersection_ped_heavy",
    "intersection_vehicle_heavy",
    "intersection_bursty_ped",
]

CONTROLLERS = [
    "fixed_time",
    "actuated",
    "adaptive_only",
    "adaptive_shield",
]

# Shield fields — present for all rows, 0 for non-shield controllers
SHIELD_FIELDS = [
    "shield_hold_min_hold",
    "shield_hold_small_gain",
    "shield_override_starvation",
    "shield_override_demand",
]

CSV_COLUMNS = [
    "scenario_name",
    "controller_name",
    "sim_duration",
    "average_vehicle_queue_length",
    "max_vehicle_queue_length",
    "average_vehicle_waiting_time",
    "max_vehicle_waiting_time",
    "average_ped_waiting_time",
    "max_ped_waiting_time",
    "switch_count",
] + SHIELD_FIELDS
# ───────────────────────────────────────────────────────────────


def main():
    total = len(SCENARIOS) * len(CONTROLLERS)
    all_results = []
    failures = []

    print(f"{'=' * 60}")
    print(f"  BATCH EXPERIMENT: {len(SCENARIOS)} scenarios x {len(CONTROLLERS)} controllers = {total} runs")
    print(f"  duration={SIM_DURATION}s  headless=True")
    print(f"{'=' * 60}\n")

    idx = 0
    for scenario in SCENARIOS:
        for controller in CONTROLLERS:
            idx += 1
            print(f"[{idx:2d}/{total}] {scenario} + {controller} ... ", end="", flush=True)

            try:
                result = run(controller, scenario, SIM_DURATION, use_gui=False)
                if result is None:
                    print("FAILED (returned None)")
                    failures.append((scenario, controller, "returned None"))
                    continue

                # Ensure shield fields exist for all rows
                for field in SHIELD_FIELDS:
                    if field not in result:
                        result[field] = 0

                all_results.append(result)
                avg_vq = result["average_vehicle_queue_length"]
                avg_vw = result["average_vehicle_waiting_time"]
                avg_pw = result["average_ped_waiting_time"]
                print(f"OK  (avg_vq={avg_vq:.2f} avg_vw={avg_vw:.1f}s avg_pw={avg_pw:.1f}s)")

            except Exception as e:
                print(f"ERROR: {e}")
                failures.append((scenario, controller, str(e)))

    # ── Save JSON ──
    os.makedirs(RESULTS_DIR, exist_ok=True)
    json_path = os.path.join(RESULTS_DIR, "batch_results_formal.json")
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)

    # ── Save CSV ──
    csv_path = os.path.join(RESULTS_DIR, "batch_results_formal.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    # ── Print summary ──
    print(f"\n{'=' * 60}")
    print(f"  BATCH COMPLETE: {len(all_results)}/{total} succeeded, {len(failures)} failed")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")
    print(f"{'=' * 60}\n")

    if failures:
        print("FAILURES:")
        for s, c, reason in failures:
            print(f"  {s} + {c}: {reason}")
        print()

    # ── Summary table ──
    hdr = (f"{'Scenario':<28} {'Controller':<18} "
           f"{'AvgVQ':>6} {'AvgVW':>6} {'AvgPW':>6} "
           f"{'MaxVW':>6} {'MaxPW':>6} {'SwCnt':>5}")
    print(hdr)
    print("-" * len(hdr))
    for r in all_results:
        print(f"{r['scenario_name']:<28} {r['controller_name']:<18} "
              f"{r['average_vehicle_queue_length']:>6.2f} "
              f"{r['average_vehicle_waiting_time']:>6.1f} "
              f"{r['average_ped_waiting_time']:>6.1f} "
              f"{r['max_vehicle_waiting_time']:>6.1f} "
              f"{r['max_ped_waiting_time']:>6.1f} "
              f"{r['switch_count']:>5d}")


if __name__ == "__main__":
    main()
