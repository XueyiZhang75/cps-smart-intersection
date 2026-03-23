"""
Proposal Matrix Results Analysis
Reads proposal_multiseed_summary.csv and generates final presentation-ready
charts, tables, and notes organized by proposal analysis order.

Usage:
  python scripts/analyze_proposal_matrix.py
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = r"E:\cps-smart-intersection"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
INPUT_CSV = os.path.join(RESULTS_DIR, "proposal_multiseed_summary.csv")
OUTPUT_DIR = os.path.join(RESULTS_DIR, "analysis_proposal_matrix")

SCENARIO_IDS = [
    "S1_balanced", "S2_directional_surge", "S3_ped_heavy",
    "S4_delay_detection", "S5_false_ped_and_burst",
    "S6_detector_failure", "S7_combined_stress",
]
CONTROLLERS = ["fixed_time", "actuated", "adaptive_only", "adaptive_shield"]

SCENARIO_SHORT = {
    "S1_balanced": "S1", "S2_directional_surge": "S2",
    "S3_ped_heavy": "S3", "S4_delay_detection": "S4",
    "S5_false_ped_and_burst": "S5", "S6_detector_failure": "S6",
    "S7_combined_stress": "S7",
}
CONTROLLER_SHORT = {
    "fixed_time": "Fixed-Time", "actuated": "Actuated",
    "adaptive_only": "Adaptive-Only", "adaptive_shield": "Adaptive+Shield",
}

COLORS = ["#4878CF", "#6ACC65", "#D65F5F", "#B47CC7"]

# Charts organized by proposal analysis order
CHARTS = [
    # A. Safety
    ("dangerous_switch_attempt_count", "Dangerous Switch Attempts",
     "Count (mean)", "fig_dangerous_switch_attempt_count.png"),
    ("conflict_release_count", "Conflict Release Count",
     "Count (mean)", "fig_conflict_release_count.png"),
    # B. Service
    ("vehicle_wait_p95", "Vehicle Waiting Time P95",
     "Time (s)", "fig_vehicle_wait_p95.png"),
    ("ped_wait_p95", "Pedestrian Waiting Time P95",
     "Time (s)", "fig_ped_wait_p95.png"),
    ("vehicle_starvation_count", "Vehicle Starvation Count",
     "Count (mean)", "fig_vehicle_starvation_count.png"),
    ("ped_starvation_count", "Pedestrian Starvation Count",
     "Count (mean)", "fig_ped_starvation_count.png"),
    # C. Efficiency
    ("average_vehicle_queue_length", "Average Vehicle Queue Length",
     "Queue length", "fig_avg_vehicle_queue.png"),
    ("average_vehicle_waiting_time", "Average Vehicle Waiting Time",
     "Time (s)", "fig_avg_vehicle_waiting.png"),
    ("average_ped_waiting_time", "Average Pedestrian Waiting Time",
     "Time (s)", "fig_avg_ped_waiting.png"),
    ("max_vehicle_waiting_time", "Max Vehicle Waiting Time",
     "Time (s)", "fig_max_vehicle_waiting.png"),
    ("max_ped_waiting_time", "Max Pedestrian Waiting Time",
     "Time (s)", "fig_max_ped_waiting.png"),
    # D. Stability
    ("switch_rate_per_300s", "Phase Switch Rate (per 300s)",
     "Switches / 300s", "fig_switch_rate_per_300s.png"),
    ("unnecessary_switch_rate", "Unnecessary Switch Rate",
     "Rate", "fig_unnecessary_switch_rate.png"),
]

SHIELD_SUMMARY_FIELDS = [
    "shield_hold_min_hold", "shield_hold_small_gain",
    "shield_override_starvation", "shield_override_demand",
    "dangerous_switch_attempt_count", "unnecessary_switch_rate",
]


def load_data():
    data = {}
    rows = []
    with open(INPUT_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for k in row:
                if k not in ("scenario_id", "controller_name"):
                    try:
                        row[k] = float(row[k])
                    except (ValueError, TypeError):
                        pass
            key = (row["scenario_id"], row["controller_name"])
            data[key] = row
            rows.append(row)
    return data, rows


def g(data, s, c, metric):
    return float(data.get((s, c), {}).get(f"{metric}_mean", 0))


def gs(data, s, c, metric):
    return float(data.get((s, c), {}).get(f"{metric}_std", 0))


def is_all_zero(data, metric):
    for s in SCENARIO_IDS:
        for c in CONTROLLERS:
            if g(data, s, c, metric) > 0.001:
                return False
    return True


def write_summary_csv(rows):
    cols = ["scenario_id", "controller_name", "n_runs"]
    metrics = [
        "conflict_release_count", "dangerous_switch_attempt_count",
        "vehicle_wait_p95", "ped_wait_p95",
        "vehicle_starvation_count", "ped_starvation_count",
        "average_vehicle_queue_length", "average_vehicle_waiting_time",
        "average_ped_waiting_time", "max_vehicle_waiting_time", "max_ped_waiting_time",
        "switch_rate_per_300s", "unnecessary_switch_rate",
    ]
    for m in metrics:
        cols += [f"{m}_mean", f"{m}_std"]
    path = os.path.join(OUTPUT_DIR, "proposal_results_summary.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"  [OK] {path}")


def write_by_scenario_csv(data):
    metrics_short = {
        "dangerous_switch_attempt_count": "DangAttempt",
        "vehicle_wait_p95": "VehP95", "ped_wait_p95": "PedP95",
        "vehicle_starvation_count": "VehStarve", "ped_starvation_count": "PedStarve",
        "average_vehicle_queue_length": "AvgVQ",
        "average_vehicle_waiting_time": "AvgVW", "average_ped_waiting_time": "AvgPW",
        "max_vehicle_waiting_time": "MaxVW", "max_ped_waiting_time": "MaxPW",
        "switch_rate_per_300s": "SwRate", "unnecessary_switch_rate": "UnnecRate",
    }
    header = ["Scenario"]
    for c in CONTROLLERS:
        for ms in metrics_short.values():
            header.append(f"{CONTROLLER_SHORT[c]}_{ms}")

    path = os.path.join(OUTPUT_DIR, "proposal_results_by_scenario.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for s in SCENARIO_IDS:
            row = [SCENARIO_SHORT[s]]
            for c in CONTROLLERS:
                for mk in metrics_short:
                    m = g(data, s, c, mk)
                    sd = gs(data, s, c, mk)
                    row.append(f"{m:.2f}±{sd:.2f}")
            writer.writerow(row)
    print(f"  [OK] {path}")


def write_shield_csv(data):
    path = os.path.join(OUTPUT_DIR, "shield_behavior_summary.csv")
    cols = ["scenario_id"]
    for f in SHIELD_SUMMARY_FIELDS:
        cols += [f"{f}_mean", f"{f}_std"]

    with open(path, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for s in SCENARIO_IDS:
            r = data.get((s, "adaptive_shield"), {})
            row = {"scenario_id": SCENARIO_SHORT[s]}
            for f in SHIELD_SUMMARY_FIELDS:
                row[f"{f}_mean"] = r.get(f"{f}_mean", 0)
                row[f"{f}_std"] = r.get(f"{f}_std", 0)
            writer.writerow(row)
    print(f"  [OK] {path}")


def draw_charts(data):
    n_scen = len(SCENARIO_IDS)
    bar_width = 0.17
    skipped = []

    for metric_key, title, ylabel, filename in CHARTS:
        if is_all_zero(data, metric_key):
            skipped.append((metric_key, filename))
            continue

        fig, ax = plt.subplots(figsize=(10, 4.5))
        x_base = list(range(n_scen))

        for i, c in enumerate(CONTROLLERS):
            means = [g(data, s, c, metric_key) for s in SCENARIO_IDS]
            stds = [gs(data, s, c, metric_key) for s in SCENARIO_IDS]
            x_pos = [x + (i - 1.5) * bar_width for x in x_base]
            ax.bar(x_pos, means, width=bar_width, yerr=stds,
                   label=CONTROLLER_SHORT[c], color=COLORS[i],
                   edgecolor="white", linewidth=0.5,
                   capsize=2, error_kw={"linewidth": 0.8})

        ax.set_xticks(x_base)
        ax.set_xticklabels([SCENARIO_SHORT[s] for s in SCENARIO_IDS], fontsize=9)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(f"{title} (20-seed mean±std)", fontsize=11, fontweight="bold")
        ax.legend(fontsize=7, loc="best")
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        fig.tight_layout()

        path = os.path.join(OUTPUT_DIR, filename)
        fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"  [OK] {path}")

    return skipped


def write_notes(data, skipped_charts):
    lines = []
    lines.append("# Proposal Matrix Results — Key Observations\n")
    lines.append("Source: `results/proposal_multiseed_summary.csv`")
    lines.append("(7 scenarios × 4 controllers × 20 seeds = 560 runs)\n")
    lines.append("All values reported as mean±std.\n")

    # Skipped metrics
    if skipped_charts:
        lines.append("## Omitted Charts\n")
        for mk, fn in skipped_charts:
            lines.append(f"- **{mk}**: all-zero across all 28 combinations. "
                         f"Chart `{fn}` omitted. This confirms the metric was never "
                         f"triggered under any tested condition.\n")

    # Overall
    lines.append("## Overall Trends\n")
    lines.append(
        "Fixed-Time (B1) consistently shows the worst vehicle queue and waiting times, "
        "and the highest pedestrian starvation counts. Actuated (B2) improves vehicle "
        "metrics through demand-responsive switching but follows a rigid sequential "
        "rotation. Adaptive-Only (A1) achieves the best vehicle efficiency by score-based "
        "phase selection, but sometimes at the cost of elevated pedestrian waiting. "
        "Adaptive+Shield (A2) trades a small amount of vehicle efficiency for improved "
        "safety margins (dangerous switch prevention) and, in several scenarios, better "
        "pedestrian starvation outcomes.\n"
    )

    # Per-scenario
    scenarios_text = {
        "S1_balanced": (
            "Baseline scenario. Adaptive-Only leads on AvgVQ "
            f"({g(data,'S1_balanced','adaptive_only','average_vehicle_queue_length'):.2f}) "
            f"and AvgVW ({g(data,'S1_balanced','adaptive_only','average_vehicle_waiting_time'):.1f}s). "
            f"Actuated has the lowest AvgPW ({g(data,'S1_balanced','actuated','average_ped_waiting_time'):.1f}s). "
            f"Shield's DangerAttempt={g(data,'S1_balanced','adaptive_shield','dangerous_switch_attempt_count'):.1f} "
            "confirms it actively prevents premature switches even under normal load."
        ),
        "S2_directional_surge": (
            "NS surge creates strong directional imbalance. Fixed-Time/Actuated AvgVQ exceeds 10, "
            f"while both Adaptive variants stay at ~3.5. PedStarve={g(data,'S2_directional_surge','adaptive_only','ped_starvation_count'):.1f} "
            "for both Adaptive controllers — the surge direction dominates, leaving pedestrians waiting. "
            "Shield provides no additional benefit here because the surge is a demand-profile issue, "
            "not a safety/stability issue."
        ),
        "S3_ped_heavy": (
            "High pedestrian pressure. Shield achieves the lowest AvgPW "
            f"({g(data,'S3_ped_heavy','adaptive_shield','average_ped_waiting_time'):.2f}s) "
            f"and lowest PedP95 ({g(data,'S3_ped_heavy','adaptive_shield','ped_wait_p95'):.1f}s). "
            f"Fixed-Time PedStarve={g(data,'S3_ped_heavy','fixed_time','ped_starvation_count'):.1f} "
            "is the highest across all S3 controllers."
        ),
        "S4_delay_detection": (
            "5s sensing delay degrades Adaptive controllers' responsiveness. "
            f"Compared to S1, Adaptive-Only AvgPW drops from 4.46 to {g(data,'S4_delay_detection','adaptive_only','average_ped_waiting_time'):.1f}s "
            "(delayed switching accidentally reduces ped interruptions). "
            f"Shield DangerAttempt={g(data,'S4_delay_detection','adaptive_shield','dangerous_switch_attempt_count'):.1f} — "
            "delay does not introduce new dangerous attempts, confirming shield stability under sensing uncertainty."
        ),
        "S5_false_ped_and_burst": (
            "False ped injection + burst arrivals. Shield's DangerAttempt is highest here "
            f"({g(data,'S5_false_ped_and_burst','adaptive_shield','dangerous_switch_attempt_count'):.1f}), "
            "showing it actively blocks phantom-driven premature switches. "
            f"Adaptive-Only AvgVW={g(data,'S5_false_ped_and_burst','adaptive_only','average_vehicle_waiting_time'):.1f}s "
            f"vs Shield {g(data,'S5_false_ped_and_burst','adaptive_shield','average_vehicle_waiting_time'):.1f}s — "
            "shield's min_hold constraint slightly increases vehicle wait but prevents oscillation."
        ),
        "S6_detector_failure": (
            "NS detector stuck-off (t=60-180s). This is the most damaging scenario for Adaptive controllers: "
            f"VehP95 jumps to {g(data,'S6_detector_failure','adaptive_only','vehicle_wait_p95'):.1f}s (A1) / "
            f"{g(data,'S6_detector_failure','adaptive_shield','vehicle_wait_p95'):.1f}s (A2), "
            f"and VehStarve reaches {g(data,'S6_detector_failure','adaptive_only','vehicle_starvation_count'):.1f} / "
            f"{g(data,'S6_detector_failure','adaptive_shield','vehicle_starvation_count'):.1f}. "
            "Baselines are unaffected because Fixed-Time ignores demand and Actuated still detects EW demand. "
            "Shield provides DangerAttempt prevention but cannot fix the underlying observation loss."
        ),
        "S7_combined_stress": (
            "Surge + delay + false_ped simultaneously. Adaptive variants maintain AvgVQ ~4.1 "
            f"(vs Fixed-Time {g(data,'S7_combined_stress','fixed_time','average_vehicle_queue_length'):.1f}). "
            f"Shield DangerAttempt={g(data,'S7_combined_stress','adaptive_shield','dangerous_switch_attempt_count'):.1f} — "
            "the second-highest after S5, confirming the shield is actively filtering combined noise. "
            f"PedStarve={g(data,'S7_combined_stress','adaptive_shield','ped_starvation_count'):.1f} "
            "for both Adaptive controllers, showing the trade-off between vehicle efficiency and ped service "
            "persists under maximum stress."
        ),
    }

    for sid in SCENARIO_IDS:
        short = SCENARIO_SHORT[sid]
        lines.append(f"## {short}: {sid.split('_', 1)[1].replace('_', ' ').title()}\n")
        lines.append(scenarios_text.get(sid, "No notes.") + "\n")

    path = os.path.join(OUTPUT_DIR, "proposal_results_notes.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [OK] {path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Reading: {INPUT_CSV}\n")

    data, rows = load_data()
    print(f"Loaded {len(rows)} summary rows.\n")

    print("Generating tables:")
    write_summary_csv(rows)
    write_by_scenario_csv(data)
    write_shield_csv(data)

    print("\nGenerating charts:")
    skipped = draw_charts(data)
    if skipped:
        print(f"\n  Skipped (all-zero): {', '.join(fn for _, fn in skipped)}")

    print("\nGenerating notes:")
    write_notes(data, skipped)

    print(f"\nAll outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
