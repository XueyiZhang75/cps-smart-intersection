"""
Multi-Seed Formal Experiment Runner
Runs 4 scenarios x 4 controllers x 20 seeds = 320 experiments.
Outputs raw per-run results and aggregated mean/std summaries.

Usage:
  python scripts/run_multiseed_formal_experiments.py
"""

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_experiment import run

# ── Configuration ──────────────────────────────────────────────
PROJECT_ROOT = r"E:\cps-smart-intersection"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
SIM_DURATION = 300
SEEDS = list(range(20))  # 0..19

SCENARIOS = [
    "intersection_balanced",
    "intersection_ped_heavy",
    "intersection_vehicle_heavy",
    "intersection_bursty_ped",
]
CONTROLLERS = ["fixed_time", "actuated", "adaptive_only", "adaptive_shield"]

SHIELD_FIELDS = [
    "shield_hold_min_hold", "shield_hold_small_gain",
    "shield_override_starvation", "shield_override_demand",
]

METRIC_FIELDS = [
    "average_vehicle_queue_length", "max_vehicle_queue_length",
    "average_vehicle_waiting_time", "max_vehicle_waiting_time",
    "average_ped_waiting_time", "max_ped_waiting_time",
    "switch_count",
] + SHIELD_FIELDS

RAW_COLUMNS = ["scenario_name", "controller_name", "seed", "sim_duration"] + METRIC_FIELDS
# ───────────────────────────────────────────────────────────────


def mean_std(values):
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    m = sum(values) / n
    if n == 1:
        return m, 0.0
    variance = sum((x - m) ** 2 for x in values) / (n - 1)
    return m, math.sqrt(variance)


def main():
    total = len(SCENARIOS) * len(CONTROLLERS) * len(SEEDS)
    all_raw = []
    failures = []

    print(f"{'=' * 70}")
    print(f"  MULTI-SEED FORMAL EXPERIMENT")
    print(f"  {len(SCENARIOS)} scenarios x {len(CONTROLLERS)} controllers x {len(SEEDS)} seeds = {total} runs")
    print(f"  duration={SIM_DURATION}s  headless=True")
    print(f"{'=' * 70}\n")

    idx = 0
    for scenario in SCENARIOS:
        for controller in CONTROLLERS:
            for seed in SEEDS:
                idx += 1
                tag = f"[{idx:3d}/{total}] {scenario.replace('intersection_',''):<16} | {controller:<16} | seed={seed:2d}"
                print(f"{tag} ... ", end="", flush=True)

                try:
                    result = run(controller, scenario, SIM_DURATION,
                                 use_gui=False, seed=seed)
                    if result is None:
                        print("FAILED")
                        failures.append((scenario, controller, seed, "returned None"))
                        continue

                    result["seed"] = seed
                    for f in SHIELD_FIELDS:
                        if f not in result:
                            result[f] = 0

                    all_raw.append(result)
                    print("OK")

                except Exception as e:
                    print(f"ERROR: {e}")
                    failures.append((scenario, controller, seed, str(e)))

    # ── Save raw results ──
    os.makedirs(RESULTS_DIR, exist_ok=True)

    raw_json = os.path.join(RESULTS_DIR, "formal_multiseed_raw.json")
    with open(raw_json, "w") as f:
        json.dump(all_raw, f, indent=2)

    raw_csv = os.path.join(RESULTS_DIR, "formal_multiseed_raw.csv")
    with open(raw_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in all_raw:
            writer.writerow(r)

    # ── Compute aggregated summary ──
    groups = {}
    for r in all_raw:
        key = (r["scenario_name"], r["controller_name"])
        if key not in groups:
            groups[key] = []
        groups[key].append(r)

    summary_rows = []
    for scenario in SCENARIOS:
        for controller in CONTROLLERS:
            key = (scenario, controller)
            runs = groups.get(key, [])
            row = {"scenario_name": scenario, "controller_name": controller,
                   "n_runs": len(runs)}
            for metric in METRIC_FIELDS:
                vals = [float(r.get(metric, 0)) for r in runs]
                m, s = mean_std(vals)
                row[f"{metric}_mean"] = round(m, 3)
                row[f"{metric}_std"] = round(s, 3)
            summary_rows.append(row)

    summary_cols = ["scenario_name", "controller_name", "n_runs"]
    for metric in METRIC_FIELDS:
        summary_cols.append(f"{metric}_mean")
        summary_cols.append(f"{metric}_std")

    summary_json = os.path.join(RESULTS_DIR, "formal_multiseed_summary.json")
    with open(summary_json, "w") as f:
        json.dump(summary_rows, f, indent=2)

    summary_csv = os.path.join(RESULTS_DIR, "formal_multiseed_summary.csv")
    with open(summary_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_cols, extrasaction="ignore")
        writer.writeheader()
        for r in summary_rows:
            writer.writerow(r)

    # ── Print summary ──
    print(f"\n{'=' * 70}")
    print(f"  COMPLETE: {len(all_raw)}/{total} succeeded, {len(failures)} failed")
    print(f"  Raw:     {raw_json}")
    print(f"           {raw_csv}")
    print(f"  Summary: {summary_json}")
    print(f"           {summary_csv}")
    print(f"{'=' * 70}\n")

    if failures:
        print("FAILURES:")
        for s, c, sd, reason in failures:
            print(f"  {s} | {c} | seed={sd}: {reason}")
        print()

    # ── Compact summary table ──
    hdr = (f"{'Scenario':<20} {'Controller':<18} "
           f"{'AvgVQ':>10} {'AvgVW':>10} {'AvgPW':>10} "
           f"{'MaxVW':>10} {'MaxPW':>10} {'SwCnt':>10}")
    print(hdr)
    print("-" * len(hdr))
    for r in summary_rows:
        def fmt(metric):
            m = r[f"{metric}_mean"]
            s = r[f"{metric}_std"]
            return f"{m:.2f}±{s:.2f}"
        scn = r["scenario_name"].replace("intersection_", "")
        print(f"{scn:<20} {r['controller_name']:<18} "
              f"{fmt('average_vehicle_queue_length'):>10} "
              f"{fmt('average_vehicle_waiting_time'):>10} "
              f"{fmt('average_ped_waiting_time'):>10} "
              f"{fmt('max_vehicle_waiting_time'):>10} "
              f"{fmt('max_ped_waiting_time'):>10} "
              f"{fmt('switch_count'):>10}")


if __name__ == "__main__":
    main()
