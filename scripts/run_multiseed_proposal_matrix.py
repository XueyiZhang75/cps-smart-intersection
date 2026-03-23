"""
Proposal Full Matrix: S1-S7 × 4 Controllers × 20 Seeds = 560 Runs
Uses scenario_id to ensure uncertainty injection is properly activated.

Usage:
  python scripts/run_multiseed_proposal_matrix.py
"""

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_experiment import run
from core.scenario_loader import load_scenario

# ── Configuration ──────────────────────────────────────────────
PROJECT_ROOT = r"E:\cps-smart-intersection"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
SIM_DURATION = 300
SEEDS = list(range(20))

SCENARIO_IDS = [
    "S1_balanced",
    "S2_directional_surge",
    "S3_ped_heavy",
    "S4_delay_detection",
    "S5_false_ped_and_burst",
    "S6_detector_failure",
    "S7_combined_stress",
]

CONTROLLERS = ["fixed_time", "actuated", "adaptive_only", "adaptive_shield"]

# All possible fields in raw output (superset across all controllers/scenarios)
SHIELD_FIELDS = [
    "shield_hold_min_hold", "shield_hold_small_gain",
    "shield_override_starvation", "shield_override_demand",
]
UNCERTAINTY_FIELDS = [
    "delay_applied_steps", "delay_seconds",
    "false_ped_injected_count", "burst_mode",
    "failure_spoofed_steps", "failure_mode_used",
]
METRIC_FIELDS = [
    "average_vehicle_queue_length", "max_vehicle_queue_length",
    "average_vehicle_waiting_time", "max_vehicle_waiting_time",
    "average_ped_waiting_time", "max_ped_waiting_time",
    "switch_count", "switch_rate_per_300s",
    "unnecessary_switch_count", "unnecessary_switch_rate",
    "conflict_release_count", "dangerous_switch_attempt_count",
    "vehicle_wait_p95", "ped_wait_p95",
    "vehicle_starvation_count", "ped_starvation_count",
] + SHIELD_FIELDS + UNCERTAINTY_FIELDS

RAW_COLUMNS = ["scenario_id", "scenario_name", "controller_name", "seed",
               "sim_duration"] + METRIC_FIELDS

# Fields to compute mean/std for in summary
NUMERIC_SUMMARY_FIELDS = [
    "average_vehicle_queue_length", "max_vehicle_queue_length",
    "average_vehicle_waiting_time", "max_vehicle_waiting_time",
    "average_ped_waiting_time", "max_ped_waiting_time",
    "switch_count", "switch_rate_per_300s",
    "unnecessary_switch_count", "unnecessary_switch_rate",
    "conflict_release_count", "dangerous_switch_attempt_count",
    "vehicle_wait_p95", "ped_wait_p95",
    "vehicle_starvation_count", "ped_starvation_count",
] + SHIELD_FIELDS
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
    total = len(SCENARIO_IDS) * len(CONTROLLERS) * len(SEEDS)
    all_raw = []
    failures = []

    print(f"{'=' * 70}")
    print(f"  PROPOSAL FULL MATRIX")
    print(f"  {len(SCENARIO_IDS)} scenarios × {len(CONTROLLERS)} controllers × {len(SEEDS)} seeds = {total} runs")
    print(f"  duration={SIM_DURATION}s  headless=True")
    print(f"{'=' * 70}\n")

    idx = 0
    for scen_id in SCENARIO_IDS:
        scfg = load_scenario(scen_id)
        cfg_name = scfg["run_experiment_cfg"]
        unc_config = scfg.get("uncertainty", None)
        # Check if any uncertainty is actually enabled
        has_unc = any(unc_config.get(k, {}).get("enabled", False)
                      for k in ["delay_detection", "false_ped_request",
                                "burst_request", "detector_failure"]) if unc_config else False

        for controller in CONTROLLERS:
            for seed in SEEDS:
                idx += 1
                short_scen = scen_id.replace("_", " ").split(" ", 1)[-1][:16]
                print(f"[{idx:3d}/{total}] {short_scen:<16} | {controller:<16} | seed={seed:2d} ... ",
                      end="", flush=True)

                try:
                    result = run(
                        controller, cfg_name, SIM_DURATION,
                        use_gui=False, seed=seed,
                        uncertainty_config=unc_config if has_unc else None,
                        scenario_id=scen_id,
                    )
                    if result is None:
                        print("FAILED")
                        failures.append((scen_id, controller, seed, "returned None"))
                        continue

                    # Ensure all expected fields exist
                    result["scenario_id"] = scen_id
                    result["seed"] = seed
                    for f in METRIC_FIELDS:
                        if f not in result:
                            result[f] = 0

                    all_raw.append(result)
                    print("OK")

                except Exception as e:
                    print(f"ERROR: {e}")
                    failures.append((scen_id, controller, seed, str(e)))

    # ── Save raw ──
    os.makedirs(RESULTS_DIR, exist_ok=True)

    raw_json = os.path.join(RESULTS_DIR, "proposal_multiseed_raw.json")
    with open(raw_json, "w") as f:
        json.dump(all_raw, f, indent=2)

    raw_csv = os.path.join(RESULTS_DIR, "proposal_multiseed_raw.csv")
    with open(raw_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in all_raw:
            writer.writerow(r)

    # ── Compute summary ──
    groups = {}
    for r in all_raw:
        key = (r["scenario_id"], r["controller_name"])
        groups.setdefault(key, []).append(r)

    summary_rows = []
    for scen_id in SCENARIO_IDS:
        for ctrl in CONTROLLERS:
            key = (scen_id, ctrl)
            runs = groups.get(key, [])
            row = {"scenario_id": scen_id, "controller_name": ctrl, "n_runs": len(runs)}
            for metric in NUMERIC_SUMMARY_FIELDS:
                vals = [float(r.get(metric, 0)) for r in runs]
                m, s = mean_std(vals)
                row[f"{metric}_mean"] = round(m, 3)
                row[f"{metric}_std"] = round(s, 3)
            summary_rows.append(row)

    summary_cols = ["scenario_id", "controller_name", "n_runs"]
    for metric in NUMERIC_SUMMARY_FIELDS:
        summary_cols += [f"{metric}_mean", f"{metric}_std"]

    summary_json = os.path.join(RESULTS_DIR, "proposal_multiseed_summary.json")
    with open(summary_json, "w") as f:
        json.dump(summary_rows, f, indent=2)

    summary_csv = os.path.join(RESULTS_DIR, "proposal_multiseed_summary.csv")
    with open(summary_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary_cols, extrasaction="ignore")
        writer.writeheader()
        for r in summary_rows:
            writer.writerow(r)

    # ── Proposal main table (human-readable, organized by proposal order) ──
    main_table_path = os.path.join(RESULTS_DIR, "proposal_matrix_main_table.csv")
    # Columns grouped by proposal analysis order
    main_metrics = [
        # Safety
        ("conflict_release_count", "Conflict"),
        ("dangerous_switch_attempt_count", "DangerAttempt"),
        # Service
        ("vehicle_wait_p95", "VehP95"),
        ("ped_wait_p95", "PedP95"),
        ("vehicle_starvation_count", "VehStarve"),
        ("ped_starvation_count", "PedStarve"),
        # Efficiency
        ("average_vehicle_queue_length", "AvgVQ"),
        ("average_vehicle_waiting_time", "AvgVW"),
        ("average_ped_waiting_time", "AvgPW"),
        ("max_vehicle_waiting_time", "MaxVW"),
        ("max_ped_waiting_time", "MaxPW"),
        # Stability
        ("switch_rate_per_300s", "SwRate"),
        ("unnecessary_switch_rate", "UnnecRate"),
    ]
    main_header = ["Scenario", "Controller"]
    for _, short in main_metrics:
        main_header.append(short)

    with open(main_table_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(main_header)
        for r in summary_rows:
            row = [r["scenario_id"].replace("_", " "), r["controller_name"]]
            for metric_key, _ in main_metrics:
                m = r.get(f"{metric_key}_mean", 0)
                s = r.get(f"{metric_key}_std", 0)
                row.append(f"{m:.2f}±{s:.2f}")
            writer.writerow(row)

    # ── Print summary ──
    print(f"\n{'=' * 70}")
    print(f"  COMPLETE: {len(all_raw)}/{total} succeeded, {len(failures)} failed")
    print(f"{'=' * 70}")
    print(f"  Raw:     {raw_csv}")
    print(f"  Summary: {summary_csv}")
    print(f"  Table:   {main_table_path}")
    print()

    if failures:
        print("FAILURES:")
        for s, c, sd, reason in failures:
            print(f"  {s} | {c} | seed={sd}: {reason}")
        print()

    # Per-scenario completion
    for scen_id in SCENARIO_IDS:
        count = sum(1 for r in all_raw if r["scenario_id"] == scen_id)
        expected = len(CONTROLLERS) * len(SEEDS)
        status = "OK" if count == expected else f"INCOMPLETE ({count}/{expected})"
        print(f"  {scen_id:<30} {count}/{expected}  {status}")


if __name__ == "__main__":
    main()
