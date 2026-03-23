"""
Scenario Configuration Loader
Reads YAML scenario configs from configs/scenarios/ and provides
structured access to scenario metadata, base paths, and uncertainty settings.

Usage:
    from core.scenario_loader import load_scenario, load_all_scenarios, list_scenarios

    cfg = load_scenario("S1_balanced")
    print(cfg["status"])                # "implemented"
    print(cfg["base_sumocfg"])          # "sumo/cfg/intersection_balanced.sumocfg"
    print(cfg["is_runnable"])           # True  (proposal fully implemented)
    print(cfg["can_run_base_mapping"])  # True  (can execute via run_experiment.py)
    print(cfg["pending_features"])      # []
"""

import os
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS_DIR = os.path.join(PROJECT_ROOT, "configs", "scenarios")

# Status values and their semantics
RUNNABLE_STATUSES = {"implemented"}
PARTIAL_STATUSES = {"partial_mapping"}
PENDING_STATUSES = {"pending_injection", "placeholder"}

REQUIRED_FIELDS = [
    "scenario_id", "scenario_name", "status",
    "base_sumocfg", "base_route", "run_experiment_cfg",
    "description", "semantic_target", "demand_profile",
    "uncertainty", "runtime_notes",
]

UNCERTAINTY_TYPES = [
    "delay_detection", "false_ped_request", "burst_request", "detector_failure",
]


def _validate(cfg, filepath):
    """Basic field validation. Raises ValueError on missing required fields."""
    missing = [f for f in REQUIRED_FIELDS if f not in cfg]
    if missing:
        raise ValueError(f"{filepath}: missing required fields: {missing}")

    unc = cfg.get("uncertainty", {})
    for utype in UNCERTAINTY_TYPES:
        if utype not in unc:
            raise ValueError(f"{filepath}: uncertainty.{utype} missing")
        entry = unc[utype]
        if "enabled" not in entry:
            raise ValueError(f"{filepath}: uncertainty.{utype}.enabled missing")


def _enrich(cfg):
    """Add derived convenience fields."""
    status = cfg.get("status", "unknown")

    # is_runnable: proposal-level fully implemented (no caveats)
    cfg["is_runnable"] = status in RUNNABLE_STATUSES

    # is_partial: mapped to a real base scenario but not fully matching proposal
    cfg["is_partial"] = status in PARTIAL_STATUSES

    # can_run_base_mapping: can actually execute via run_experiment.py
    # True for implemented + partial_mapping (both have real base configs)
    # False for pending_injection + placeholder (running would be misleading)
    cfg["can_run_base_mapping"] = status in (RUNNABLE_STATUSES | PARTIAL_STATUSES)

    # List uncertainty features that are enabled but not yet implemented
    pending = []
    unc = cfg.get("uncertainty", {})
    for utype in UNCERTAINTY_TYPES:
        entry = unc.get(utype, {})
        if entry.get("enabled", False) and status not in RUNNABLE_STATUSES:
            # burst_request via route_based is only truly implemented when
            # the base_route actually contains burst patterns (partial_mapping).
            # For placeholder/pending scenarios, the base_route is a placeholder
            # and burst_request is NOT implemented even if mode=route_based.
            if (utype == "burst_request"
                    and entry.get("mode") == "route_based"
                    and status in PARTIAL_STATUSES):
                continue
            pending.append(utype)
    cfg["pending_features"] = pending

    # Full path to base sumocfg
    cfg["base_sumocfg_abs"] = os.path.join(PROJECT_ROOT, cfg["base_sumocfg"])

    return cfg


def load_scenario(scenario_name):
    """
    Load a single scenario config by name (e.g., "S1_balanced").

    Args:
        scenario_name: filename stem without .yaml extension

    Returns:
        dict with all YAML fields plus derived fields:
          is_runnable, is_partial, pending_features, base_sumocfg_abs
    """
    filepath = os.path.join(SCENARIOS_DIR, f"{scenario_name}.yaml")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Scenario config not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    _validate(cfg, filepath)
    _enrich(cfg)
    return cfg


def load_all_scenarios():
    """
    Load all .yaml files from configs/scenarios/.

    Returns:
        dict mapping scenario_name (stem) -> config dict
    """
    results = {}
    for fname in sorted(os.listdir(SCENARIOS_DIR)):
        if fname.endswith(".yaml"):
            name = fname[:-5]  # strip .yaml
            results[name] = load_scenario(name)
    return results


def list_scenarios():
    """Print a compact status table of all scenario configs."""
    all_cfgs = load_all_scenarios()
    print(f"{'ID':<4} {'Name':<26} {'Status':<20} {'CanRun':>6} {'Impl':>5}  Pending")
    print("-" * 95)
    for name, cfg in all_cfgs.items():
        sid = cfg.get("scenario_id", "?")
        sname = cfg.get("scenario_name", name)
        status = cfg.get("status", "unknown")
        can_run = "YES" if cfg["can_run_base_mapping"] else "no"
        impl = "YES" if cfg["is_runnable"] else "no"
        pending = ", ".join(cfg["pending_features"]) if cfg["pending_features"] else "-"
        print(f"{sid:<4} {sname:<26} {status:<20} {can_run:>6} {impl:>5}  {pending}")


if __name__ == "__main__":
    list_scenarios()
