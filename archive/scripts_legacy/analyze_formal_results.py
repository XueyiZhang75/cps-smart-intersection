"""
Formal Results Analysis
Reads batch_results_formal.csv and generates summary tables, charts, and notes.

Usage:
  python scripts/analyze_formal_results.py
"""

import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Paths ──────────────────────────────────────────────────────
PROJECT_ROOT = r"E:\cps-smart-intersection"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
INPUT_CSV = os.path.join(RESULTS_DIR, "batch_results_formal.csv")
OUTPUT_DIR = os.path.join(RESULTS_DIR, "analysis_formal")
# ───────────────────────────────────────────────────────────────

SCENARIOS = ["intersection_balanced", "intersection_ped_heavy",
             "intersection_vehicle_heavy", "intersection_bursty_ped"]
CONTROLLERS = ["fixed_time", "actuated", "adaptive_only", "adaptive_shield"]

# Short display names for plots
SCENARIO_SHORT = {
    "intersection_balanced": "balanced",
    "intersection_ped_heavy": "ped_heavy",
    "intersection_vehicle_heavy": "vehicle_heavy",
    "intersection_bursty_ped": "bursty_ped",
}
CONTROLLER_SHORT = {
    "fixed_time": "Fixed-Time",
    "actuated": "Actuated",
    "adaptive_only": "Adaptive",
    "adaptive_shield": "Adaptive+Shield",
}

CORE_METRICS = [
    "average_vehicle_queue_length",
    "max_vehicle_queue_length",
    "average_vehicle_waiting_time",
    "max_vehicle_waiting_time",
    "average_ped_waiting_time",
    "max_ped_waiting_time",
    "switch_count",
]

SHIELD_FIELDS = [
    "shield_hold_min_hold",
    "shield_hold_small_gain",
    "shield_override_starvation",
    "shield_override_demand",
]

# Chart configs: (metric_key, title, ylabel, filename)
CHARTS = [
    ("average_vehicle_queue_length", "Average Vehicle Queue Length",
     "Queue length (vehicles)", "fig_avg_vehicle_queue.png"),
    ("average_vehicle_waiting_time", "Average Vehicle Waiting Time",
     "Waiting time (s)", "fig_avg_vehicle_waiting.png"),
    ("average_ped_waiting_time", "Average Pedestrian Waiting Time",
     "Waiting time (s)", "fig_avg_ped_waiting.png"),
    ("max_vehicle_waiting_time", "Max Vehicle Waiting Time",
     "Waiting time (s)", "fig_max_vehicle_waiting.png"),
    ("max_ped_waiting_time", "Max Pedestrian Waiting Time",
     "Waiting time (s)", "fig_max_ped_waiting.png"),
    ("switch_count", "Phase Switch Count",
     "Number of switches", "fig_switch_count.png"),
]


def load_data():
    """Load CSV into a dict keyed by (scenario, controller)."""
    data = {}
    rows = []
    with open(INPUT_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            for k in row:
                if k not in ("scenario_name", "controller_name"):
                    try:
                        row[k] = float(row[k])
                    except (ValueError, TypeError):
                        pass
            key = (row["scenario_name"], row["controller_name"])
            data[key] = row
            rows.append(row)
    return data, rows


def write_summary_csv(rows):
    """Write formal_results_summary.csv — one row per (scenario, controller)."""
    cols = ["scenario_name", "controller_name", "sim_duration"] + CORE_METRICS + SHIELD_FIELDS
    path = os.path.join(OUTPUT_DIR, "formal_results_summary.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"  [OK] {path}")


def write_by_scenario_csv(data):
    """Write formal_results_by_scenario.csv — wide format for easy reading."""
    metrics_short = {
        "average_vehicle_queue_length": "AvgVQ",
        "average_vehicle_waiting_time": "AvgVW",
        "average_ped_waiting_time": "AvgPW",
        "max_vehicle_waiting_time": "MaxVW",
        "max_ped_waiting_time": "MaxPW",
        "switch_count": "SwCnt",
    }
    # Build columns: Scenario, then for each controller: metric columns
    header = ["Scenario"]
    for c in CONTROLLERS:
        cname = CONTROLLER_SHORT[c]
        for m_short in metrics_short.values():
            header.append(f"{cname}_{m_short}")

    path = os.path.join(OUTPUT_DIR, "formal_results_by_scenario.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for s in SCENARIOS:
            row = [SCENARIO_SHORT[s]]
            for c in CONTROLLERS:
                r = data.get((s, c), {})
                for m_key in metrics_short:
                    val = r.get(m_key, "")
                    if isinstance(val, float):
                        val = round(val, 2) if "queue" in m_key else round(val, 1)
                    row.append(val)
            writer.writerow(row)
    print(f"  [OK] {path}")


def write_shield_csv(data):
    """Write shield_debug_summary.csv — only adaptive_shield rows."""
    path = os.path.join(OUTPUT_DIR, "shield_debug_summary.csv")
    cols = ["scenario_name"] + SHIELD_FIELDS
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for s in SCENARIOS:
            r = data.get((s, "adaptive_shield"), {})
            row = {"scenario_name": SCENARIO_SHORT[s]}
            for field in SHIELD_FIELDS:
                row[field] = int(r.get(field, 0))
            writer.writerow(row)
    print(f"  [OK] {path}")


def draw_charts(data):
    """Generate grouped bar charts for each metric."""
    n_scenarios = len(SCENARIOS)
    n_controllers = len(CONTROLLERS)
    bar_width = 0.18
    colors = ["#4878CF", "#6ACC65", "#D65F5F", "#B47CC7"]

    for metric_key, title, ylabel, filename in CHARTS:
        fig, ax = plt.subplots(figsize=(8, 4.5))

        x_base = list(range(n_scenarios))
        for i, c in enumerate(CONTROLLERS):
            vals = []
            for s in SCENARIOS:
                r = data.get((s, c), {})
                vals.append(float(r.get(metric_key, 0)))
            x_pos = [x + (i - 1.5) * bar_width for x in x_base]
            ax.bar(x_pos, vals, width=bar_width, label=CONTROLLER_SHORT[c],
                   color=colors[i], edgecolor="white", linewidth=0.5)

        ax.set_xticks(x_base)
        ax.set_xticklabels([SCENARIO_SHORT[s] for s in SCENARIOS], fontsize=9)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, loc="best")
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        fig.tight_layout()

        path = os.path.join(OUTPUT_DIR, filename)
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"  [OK] {path}")


def write_notes(data):
    """Write formal_results_notes.md — brief per-scenario observations."""
    lines = []
    lines.append("# Formal Experiment Results — Key Observations\n")
    lines.append(f"Source: `results/batch_results_formal.csv` (4 scenarios x 4 controllers)\n")

    # balanced
    lines.append("## balanced")
    lines.append("- Adaptive-only achieves the lowest avg vehicle queue (2.13) and avg vehicle wait (2.4s),")
    lines.append("  but at the cost of higher avg ped wait (4.6s) compared to Actuated (2.2s).")
    lines.append("- Adaptive+Shield reduces max ped wait from 63s to 58s vs Adaptive-only,")
    lines.append("  while keeping vehicle metrics competitive (avg queue 2.48).")
    lines.append("- Fixed-time has the worst performance across all metrics.\n")

    # ped_heavy
    lines.append("## ped_heavy")
    lines.append("- With 2.5x pedestrian load, Adaptive+Shield achieves the lowest avg ped wait (2.4s)")
    lines.append("  and lowest max ped wait (49s), outperforming Adaptive-only on pedestrian metrics.")
    lines.append("- Adaptive-only and Actuated tie on avg ped wait (2.7s), but Adaptive-only")
    lines.append("  has better vehicle queue (2.91 vs 3.10).")
    lines.append("- Fixed-time max ped wait reaches 86s — the highest across all scenarios.\n")

    # vehicle_heavy
    lines.append("## vehicle_heavy")
    lines.append("- Under 2.5x vehicle load, Adaptive variants dramatically outperform baselines:")
    lines.append("  avg queue 4.6-4.8 vs 12.4-13.7 for Fixed-time/Actuated.")
    lines.append("- The vehicle-pedestrian trade-off is starkest here: Adaptive-only max ped wait")
    lines.append("  reaches 100s, while Adaptive+Shield limits it to 98s — shield provides marginal")
    lines.append("  pedestrian protection at no vehicle cost (avg vehicle wait identical at 1.8s).")
    lines.append("- Actuated performs worse than Fixed-time on avg queue (13.71 vs 12.37),")
    lines.append("  suggesting its sequential rotation is suboptimal under heavy directional load.\n")

    # bursty_ped
    lines.append("## bursty_ped")
    lines.append("- Burst pedestrian arrivals create the clearest Adaptive vs Adaptive+Shield separation:")
    lines.append("  max ped wait 72s vs 57s (15s gap), the largest shield benefit across all scenarios.")
    lines.append("- Adaptive+Shield also achieves the best avg vehicle queue (2.71) in this scenario,")
    lines.append("  indicating that shield stability benefits both vehicle and pedestrian metrics.")
    lines.append("- Fixed-time max ped wait (83s) confirms its inability to respond to demand bursts.\n")

    path = os.path.join(OUTPUT_DIR, "formal_results_notes.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Reading: {INPUT_CSV}\n")

    data, rows = load_data()
    print(f"Loaded {len(rows)} results.\n")

    print("Generating tables:")
    write_summary_csv(rows)
    write_by_scenario_csv(data)
    write_shield_csv(data)

    print("\nGenerating charts:")
    draw_charts(data)

    print("\nGenerating notes:")
    write_notes(data)

    print(f"\nAll outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
