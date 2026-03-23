# Scenario Configuration Schema

This document describes the YAML schema used for scenario configuration files in `configs/scenarios/`.

## Overview

Each scenario is defined by a single YAML file that captures:
- What base SUMO network and route files to use
- What the scenario represents in the proposal (S1–S7)
- What uncertainty/abnormality injections are configured
- Whether the scenario is currently runnable or pending implementation

## File Location

All scenario configs are stored in:
```
configs/scenarios/S{N}_{name}.yaml
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `scenario_id` | string | Proposal ID: S1, S2, ..., S7 |
| `scenario_name` | string | Short name: balanced, ped_heavy, etc. |
| `status` | string | Implementation status (see below) |
| `base_sumocfg` | string | Relative path to .sumocfg from project root |
| `base_route` | string | Relative path to .rou.xml from project root |
| `description` | string | What this scenario does |
| `semantic_target` | string | What this scenario means in the proposal |
| `demand_profile` | object | Vehicle/ped demand characteristics |
| `uncertainty` | object | Uncertainty injection settings |

## Status Values

| Status | Meaning |
|--------|---------|
| `implemented` | Fully implemented, validated, can be run directly |
| `partial_mapping` | Mapped to an existing scenario that partially matches; some aspects differ from proposal |
| `pending_injection` | Config skeleton ready, but uncertainty injection logic not yet implemented |
| `placeholder` | Config skeleton only; requires new route files and/or injection logic |

## Demand Profile

```yaml
demand_profile:
  vehicle_level: low | medium | high
  pedestrian_level: low | medium | medium_bursty | high
  directional_bias: none | symmetric_high | single_direction
  burst_pattern: none | "description of burst windows"
```

## Uncertainty Block

Each scenario has an `uncertainty` block with four sub-entries:

```yaml
uncertainty:
  delay_detection:
    enabled: true/false
    mode: null | fixed_delay | variable_delay
    params: {}
  false_ped_request:
    enabled: true/false
    mode: null | random_phantom | periodic_phantom
    params: {}
  burst_request:
    enabled: true/false
    mode: null | route_based | runtime_injection
    params: {}
  detector_failure:
    enabled: true/false
    mode: null | stuck_off | stuck_on | intermittent
    params: {}
```

### Important: `enabled: true` does NOT mean implemented

A field like `delay_detection.enabled: true` means "this scenario is designed to include delay detection." If the scenario's `status` is `pending_injection`, the enabled flag represents the **design intent**, not a currently active feature. The `scenario_loader.py` reports these as `pending_features`.

## Loader API

```python
from core.scenario_loader import load_scenario, load_all_scenarios, list_scenarios

cfg = load_scenario("S1_balanced")
cfg["is_runnable"]       # True if status == "implemented"
cfg["is_partial"]        # True if status == "partial_mapping"
cfg["pending_features"]  # List of uncertainty types enabled but not yet implemented
cfg["base_sumocfg_abs"]  # Absolute path to the base .sumocfg file
```

## Current Status (as of Stage B)

| ID | Name | Status | Runnable | Pending |
|----|------|--------|----------|---------|
| S1 | balanced | implemented | YES | - |
| S2 | directional_surge | partial_mapping | no | - |
| S3 | ped_heavy | implemented | YES | - |
| S4 | delay_detection | pending_injection | no | delay_detection |
| S5 | false_ped_and_burst | partial_mapping | no | false_ped_request |
| S6 | detector_failure | pending_injection | no | detector_failure |
| S7 | combined_stress | placeholder | no | delay_detection, false_ped_request |
