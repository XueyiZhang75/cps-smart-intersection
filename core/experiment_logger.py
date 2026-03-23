"""
Step-Level Experiment Logger
Writes a per-step CSV log during simulation for post-hoc analysis.
"""

import csv
import os

STEP_LOG_COLUMNS = [
    # Basic info
    "sim_time", "controller_name", "scenario_name", "scenario_id", "seed",
    # Phase & switching
    "current_phase_idx", "current_phase_name", "time_in_phase",
    "candidate_phase_idx", "candidate_phase_name",
    "final_action", "switch_event", "entered_clearance",
    "override_flag", "override_reason",
    # Observed demand (post-uncertainty)
    "veh_queue_ns_obs", "veh_queue_ew_obs",
    "ped_wait_ew_obs", "ped_wait_ns_obs",
    "veh_demand_ns_obs", "veh_demand_ew_obs",
    "ped_demand_ew_obs", "ped_demand_ns_obs",
    # True demand (raw TraCI, pre-uncertainty)
    "veh_queue_ns_true", "veh_queue_ew_true",
    "ped_wait_ew_true", "ped_wait_ns_true",
    # Uncertainty state
    "delay_active", "false_ped_active", "detector_failure_active",
    "failure_mode", "phantom_ped_count",
    # Risk & stats flags
    "dangerous_switch_attempt_flag", "conflict_flag",
    "vehicle_starvation_flag", "ped_starvation_flag",
    "unnecessary_switch_flag",
]

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "logs", "step_logs")


class StepLogger:
    """Writes step-level CSV log during a simulation run."""

    def __init__(self, controller_name, scenario_label, seed=None):
        os.makedirs(LOG_DIR, exist_ok=True)
        seed_str = f"_seed{seed}" if seed is not None else ""
        filename = f"{controller_name}_{scenario_label}{seed_str}.csv"
        self.filepath = os.path.join(LOG_DIR, filename)
        self._file = open(self.filepath, "w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=STEP_LOG_COLUMNS,
                                       extrasaction="ignore")
        self._writer.writeheader()

    def log(self, row):
        """Append one row (dict). Missing keys become empty strings."""
        self._writer.writerow(row)

    def close(self):
        if self._file:
            self._file.close()
            self._file = None
