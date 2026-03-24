# Safe and Robust Smart Intersection Control under Sensing Uncertainty and Abnormal Requests

A CPS course project implementing and evaluating adaptive traffic signal control with a runtime safety shield, tested under uncertainty and stress conditions using SUMO simulation and PRISM formal verification.

## Project Overview

This project investigates whether a **safety shield layer** on top of an adaptive signal controller can preserve basic safety properties and improve robustness under sensing uncertainty, without unacceptable efficiency degradation. We compare four controllers across seven scenarios (including demand-only and uncertainty-injected conditions), using both simulation-based evaluation (7 × 4 × 20 = 560 runs) and probabilistic model checking.

The intersection is a **single four-way junction** with 8 signal phases (4 service + 4 clearance), supporting both vehicles and pedestrians.

### Controllers

| ID | Controller | Description |
|----|-----------|-------------|
| B1 | **Fixed-Time** | Static 8-phase cycle (102s period) with fixed durations |
| B2 | **Actuated** | Demand-responsive: switches after min green when competing demand exists |
| A1 | **Adaptive-Only** | Score-based phase selection weighing queue size, starvation, and switch cost |
| A2 | **Adaptive+Shield** | A1 + three-layer safety filter (min-hold guard, score-margin filter, starvation override) |

### Scenarios (S1–S7)

| ID | Scenario | Base Demand | Runtime Uncertainty |
|----|---------|-------------|---------------------|
| S1 | Balanced | Medium symmetric | None |
| S2 | Directional Surge | NS heavy (~75 veh), EW low (~20 veh) | None |
| S3 | Ped Heavy | Medium vehicles, ~2.5× pedestrians | None |
| S4 | Delay Detection | Balanced base | 5s fixed sensing delay on all lanes |
| S5 | False Ped + Burst | Bursty peds base | Phantom ped requests (20% false rate) |
| S6 | Detector Failure | Balanced base | NS vehicle detectors stuck-off (t=60–180s) |
| S7 | Combined Stress | NS surge base | Delay (5s) + false ped (20%) simultaneously |

S1–S3 test demand-profile stress without uncertainty. S4–S6 each inject one type of sensing anomaly. S7 combines directional surge with two uncertainty sources. All scenarios use the same network and 8-phase structure.

## Experiment Protocol

- **Formal matrix:** 7 scenarios × 4 controllers × 20 seeds = **560 runs**
- **Duration:** 300 simulated seconds per run
- **Seed mechanism:** passed to SUMO via `--seed`; affects vehicle/pedestrian departure jitter
- **Uncertainty injection:** S4–S7 must be run via `--scenario_id` (not `--cfg` alone), which loads the scenario YAML and activates the corresponding runtime injection layer
- **S1–S3** can be run via either `--cfg` or `--scenario_id`; both produce the same results since no runtime uncertainty is enabled

## Tech Stack

- **SUMO 1.26** — microscopic traffic simulation
- **Python 3 + TraCI** — controller logic, experiment orchestration, analysis
- **PRISM 4.10** — probabilistic model checking (requires `E:\prism-4.10\lib` on system PATH)
- **matplotlib** — result visualization

## Project Structure

```
cps-smart-intersection/
├── README.md
├── requirements.txt
├── .gitignore
├── core/                      # Shared runtime modules
│   ├── uncertainty.py             # Uncertainty injection (delay, false ped, detector failure)
│   ├── scenario_loader.py         # YAML scenario config loader + validator
│   └── experiment_logger.py       # Per-step CSV logger
├── configs/scenarios/         # Scenario YAML configs (S1–S7)
│   ├── S1_balanced.yaml
│   ├── S2_directional_surge.yaml
│   ├── S3_ped_heavy.yaml
│   ├── S4_delay_detection.yaml
│   ├── S5_false_ped_and_burst.yaml
│   ├── S6_detector_failure.yaml
│   └── S7_combined_stress.yaml
├── sumo/                      # SUMO network, routes, configs
│   ├── net/                       # Network files (nod, edg, net, tll, con)
│   ├── routes/                    # Route/flow files per scenario
│   └── cfg/                       # .sumocfg entry points
├── scripts/                   # Experiment & analysis scripts
│   ├── run_experiment.py              # Single-run entry point (all controllers)
│   ├── run_multiseed_proposal_matrix.py  # Full S1–S7 × 4 ctrl × 20 seed (560 runs)
│   ├── analyze_proposal_matrix.py     # Chart & table generation
│   ├── build_case_studies.py          # Shield evidence case extraction
│   ├── run_prism_base.py              # PRISM base safety verification
│   └── run_prism_extended.py          # PRISM service/risk + delay comparison
├── prism/                     # PRISM formal models
│   ├── intersection_base.pm           # Base DTMC: 8 phases + demand bits
│   ├── intersection_uncertain.pm      # Extended: + wait-risk buckets + delay mode
│   ├── properties_base.pctl           # 3 base safety properties
│   └── properties_extended.pctl       # 14 extended properties
├── cases/                     # Shield evidence case studies
│   ├── case1_min_green_hold/
│   ├── case2_ped_conflict_clearance/
│   └── case3_false_button_debounce/
├── results/                   # Experiment outputs
│   ├── proposal_multiseed_raw.csv     # 560 raw results
│   ├── proposal_multiseed_summary.csv # 28-row mean±std aggregation
│   ├── proposal_matrix_main_table.csv # Human-readable summary table
│   ├── analysis_proposal_matrix/      # 12 PNG charts + summary CSVs + notes
│   └── prism/                         # PRISM verification outputs
├── docs/                      # Documentation
│   ├── project_contract_v1.md
│   ├── sumo_prism_mapping.md
│   └── scenario_config_schema.md
└── archive/                   # Earlier development artefacts (not part of submission)
    ├── controllers_dev/           # Standalone controller scripts (early dev)
    ├── scripts_legacy/            # Superseded batch/analysis scripts
    ├── results_legacy/            # Superseded 4-scenario result sets
    └── step_logs/                 # Per-step CSV logs, 26 MB (regenerable)
```

## Quick Start

### Prerequisites

- Python 3.10+
- SUMO 1.26+ (with `sumo`, `sumo-gui`, `netconvert` on PATH; TraCI bundled)
- PRISM 4.10 (optional; requires `E:\prism-4.10\lib` added to system PATH for DLL resolution)

Install Python dependencies:
```bash
pip install pyyaml matplotlib
```

TraCI ships with SUMO. Add SUMO's tools directory to `PYTHONPATH`:
```bash
export PYTHONPATH="$SUMO_HOME/tools:$PYTHONPATH"
```

### Run a Single Experiment

```bash
# Basic: controller + base config (no uncertainty injection)
python scripts/run_experiment.py --controller adaptive_shield --cfg intersection_balanced --duration 300

# With scenario YAML (required for S4–S7 to enable uncertainty injection)
python scripts/run_experiment.py --controller adaptive_shield --scenario_id S4_delay_detection --duration 300 --seed 0

# With GUI for visual observation
python scripts/run_experiment.py --controller adaptive_shield --cfg intersection_balanced --duration 300 --gui
```

### Run Full Proposal Matrix (560 experiments)

```bash
python scripts/run_multiseed_proposal_matrix.py
```

Outputs:
- `results/proposal_multiseed_raw.csv` — 560 rows, one per (scenario, controller, seed)
- `results/proposal_multiseed_summary.csv` — 28 rows, mean±std per (scenario, controller)
- `results/proposal_matrix_main_table.csv` — formatted for direct reading

### Generate Final Charts

```bash
python scripts/analyze_proposal_matrix.py
```

Outputs 12 grouped bar charts (with error bars) and summary tables to `results/analysis_proposal_matrix/`.

### Run PRISM Formal Verification

```bash
# Base: 3 safety properties (no-conflict, no ped-vehicle overlap, clearance completion)
python scripts/run_prism_base.py

# Extended: 14 properties across normal and delayed configurations
python scripts/run_prism_extended.py
```

### Build Shield Evidence Cases

```bash
python scripts/build_case_studies.py
```

Generates 3 case study packages in `cases/`, each with step log, key events CSV, timeline PNG, and explanatory README.

## Full Pipeline: Understanding and Reproducing the Project

This section walks through the complete project from first principles to final results. It is intended for anyone picking up this repository for the first time.

### Conceptual Flow

```
SUMO Network (sumo/net/)
    │  4-way junction, 8 signal phases, vehicle lanes + pedestrian crossings
    ▼
Scenario Configs (configs/scenarios/S1–S7.yaml)
    │  Each scenario = demand profile + optional uncertainty injection settings
    ▼
Experiment Runner (scripts/run_experiment.py)
    │  Loads scenario → starts SUMO via TraCI → runs one controller for 300s
    │  Controller types: Fixed-Time | Actuated | Adaptive-Only | Adaptive+Shield
    │  Uncertainty injection activates at runtime (observation-layer only)
    │  Outputs: per-run JSON summary + per-step CSV log
    ▼
Multi-seed Matrix (scripts/run_multiseed_proposal_matrix.py)
    │  Repeats single-run logic for all 7 × 4 × 20 = 560 combinations
    │  Outputs: raw CSV (560 rows) + summary CSV (28 rows mean±std)
    ▼
Analysis & Charts (scripts/analyze_proposal_matrix.py)
    │  Reads summary CSV → generates 12 grouped bar charts + result tables
    ▼
Shield Case Studies (scripts/build_case_studies.py)       ← parallel, optional
    │  Extracts step-log evidence for 3 concrete shield intervention events
    ▼
PRISM Verification (scripts/run_prism_base.py / run_prism_extended.py)   ← parallel, optional
    │  Checks safety/liveness properties on the formal DTMC abstraction
    ▼
Results (results/)
    ├── proposal_multiseed_raw.csv / summary.csv / main_table.csv
    ├── analysis_proposal_matrix/  (12 PNG charts)
    ├── prism/  (verification outputs)
    └── cases/  (3 shield evidence packages)
```

### Step 0 — Environment Setup

**Required for all simulation steps:**

```bash
# 1. Install Python dependencies
pip install pyyaml matplotlib

# 2. Add SUMO's TraCI library to Python path (adjust to your SUMO install location)
export PYTHONPATH="$SUMO_HOME/tools:$PYTHONPATH"
# Windows example: set PYTHONPATH=C:\Program Files (x86)\Eclipse\Sumo\tools;%PYTHONPATH%

# 3. Verify SUMO is accessible
sumo --version
```

**Required only for PRISM formal verification (Step 5):**

```bash
# Add PRISM native libraries to PATH so Windows can resolve DLL dependencies
export PATH="/e/prism-4.10/lib:$PATH"
# Windows: add E:\prism-4.10\lib to System PATH in Environment Variables
```

### Step 1 — Understand the Network and Scenarios

The SUMO network is a single 4-way junction with 8 signal phases:
- Phases 0, 2, 4, 6: **service phases** (one direction gets green)
- Phases 1, 3, 5, 7: **clearance/yellow phases** (transition buffers)

Signal phases and their phases are defined in `sumo/net/intersection_ped.tll.xml`. The network file itself is `sumo/net/intersection_ped.net.xml`.

Scenarios are declared in `configs/scenarios/`. Each YAML file specifies:
- Which SUMO `.sumocfg` and route file to use
- What uncertainty to inject at runtime (or none for S1–S3)

To inspect a scenario config:
```bash
cat configs/scenarios/S4_delay_detection.yaml
```

### Step 2 — Run a Single Experiment

The entry point for any single run is `scripts/run_experiment.py`. Use `--scenario_id` for S4–S7 (required to activate uncertainty injection); `--cfg` alone works for S1–S3.

```bash
# S1 (no uncertainty) with Adaptive+Shield, visual GUI
python scripts/run_experiment.py \
    --controller adaptive_shield \
    --scenario_id S1_balanced \
    --duration 300 --seed 0 --gui

# S4 (5s sensing delay) with Adaptive-Only, headless
python scripts/run_experiment.py \
    --controller adaptive_only \
    --scenario_id S4_delay_detection \
    --duration 300 --seed 0

# Compare all 4 controllers on S7 (combined stress), one at a time
for ctrl in fixed_time actuated adaptive_only adaptive_shield; do
    python scripts/run_experiment.py \
        --controller $ctrl --scenario_id S7_combined_stress \
        --duration 300 --seed 0
done
```

**Controller names:** `fixed_time`, `actuated`, `adaptive_only`, `adaptive_shield`

**Output:** JSON summary written to `results/`, step-level CSV written to `archive/step_logs/`.

### Step 3 — Run the Full 560-Run Experiment Matrix

This is the authoritative data-generation step. It runs all 7 scenarios × 4 controllers × 20 seeds = 560 experiments sequentially (no SUMO GUI; headless mode). Expect roughly 30–60 minutes depending on hardware.

```bash
python scripts/run_multiseed_proposal_matrix.py
```

Outputs written to `results/`:
| File | Contents |
|------|----------|
| `proposal_multiseed_raw.csv` | 560 rows, one per (scenario, controller, seed) |
| `proposal_multiseed_summary.csv` | 28 rows, mean ± std per (scenario × controller) |
| `proposal_matrix_main_table.csv` | Human-readable formatted table |

**Note:** Pre-computed results are already present in `results/`. Re-running will overwrite them. The step logs (26 MB) are stored in `archive/step_logs/` and are regenerated by this script.

### Step 4 — Generate Analysis Charts

Reads `results/proposal_multiseed_summary.csv` and produces 12 grouped bar charts with error bars plus CSV summaries.

```bash
python scripts/analyze_proposal_matrix.py
```

Outputs to `results/analysis_proposal_matrix/`:
- 12 PNG charts: one per metric (average queue, wait times, switch rates, starvation counts, etc.)
- `proposal_results_summary.csv`, `proposal_results_by_scenario.csv`
- `shield_behavior_summary.csv` — shield intervention counts per scenario
- `proposal_results_notes.md` — auto-generated interpretation notes

### Step 5 — Build Shield Evidence Case Studies

Extracts concrete evidence from step logs for 3 shield intervention scenarios. Requires that step logs exist in `archive/step_logs/` (generated by Step 3, or by running individual experiments).

```bash
python scripts/build_case_studies.py
```

Outputs to `cases/` (3 subdirectories):
| Case | What it demonstrates |
|------|----------------------|
| `case1_min_green_hold/` | Shield blocks premature phase switch before 18s min-hold |
| `case2_ped_conflict_clearance/` | Shield routes ped service through mandatory clearance phase |
| `case3_false_button_debounce/` | Shield rejects spurious ped demand from false injection |

Each case directory contains: `step_log.csv`, `key_events.csv`, `timeline.png`, `README.md`, `trigger_config.json`.

### Step 6 — Run PRISM Formal Verification (Optional)

Requires PRISM 4.10 installed and `E:\prism-4.10\lib` on system PATH (see Step 0). These steps verify safety/liveness properties on the DTMC abstraction of the intersection — independent of SUMO simulation.

```bash
# Base model: 3 safety properties (always verified true by design)
python scripts/run_prism_base.py

# Extended model: 14 properties (service guarantees, risk levels, delay comparison)
python scripts/run_prism_extended.py
```

Outputs written to `results/prism/`:
- `base_verification_results.md` / `prism_raw_output.txt`
- `extended_verification_results.md` / `extended_prism_raw_output.txt`

Pre-computed results are already present. Re-running requires PRISM to be installed.

### Recommended Reproduction Order

For a full reproduction from scratch:

```
Step 0  →  Step 3  →  Step 4  →  Step 5  →  Step 6
(setup)    (560 runs)  (charts)  (cases)   (PRISM, optional)
```

To just verify the analysis pipeline on existing data (no re-simulation needed):

```
Step 4  →  Step 5  →  Step 6
```

To visually observe the controllers in action before running the full matrix:

```
Step 0  →  Step 2 (with --gui)  →  Step 3  →  Step 4
```

---

## Key Results

### Formal Verification (PRISM)

**Base model** (DTMC, 448 states, 8-phase + demand abstraction):

| Property | Result |
|----------|--------|
| No conflict release: `P>=1 [G !"conflict"]` | **true** |
| No vehicle-pedestrian overlap: `P>=1 [G !"veh_conflict_during_ped"]` | **true** |
| Clearance always completes: `"clearance" => F cl_count=3` | **true** |

**Extended model** (adds wait-risk buckets + delay mode, 14 properties):

| Property | Normal | Delayed |
|----------|--------|---------|
| No-conflict invariant | true | true |
| Eventual service (Vehicle_NS) | P=1.0 | P=1.0 |
| Eventual service (Ped_EW) | P=1.0 | P=1.0 |
| Steady-state Vehicle_NS green fraction | 14.7% | 16.0% |
| Steady-state Ped_EW green fraction | 12.3% | 13.8% |
| Steady-state extreme wait (any direction) | 23.0% | 23.1% |

The extended model covers representative service/risk properties for one vehicle direction (NS) and one pedestrian direction (EW) under normal vs. delayed observation. It abstracts delay_detection as a binary mode; false_ped and detector_failure are evaluated in SUMO but not yet abstracted into separate PRISM modes.

### Simulation Results (20-seed mean, 300s)

Selected highlights from the full 7 × 4 matrix (see `results/proposal_multiseed_summary.csv` for complete data):

**S1 Balanced:** Adaptive-Only achieves the lowest vehicle queue (2.21±0.10) and vehicle wait (2.51±0.18s). Actuated achieves the lowest ped wait (2.17±0.15s). Shield records 1.15±0.37 dangerous switch attempts per run, all successfully intercepted.

**S2 Directional Surge:** Adaptive variants maintain avg queue ~3.5 vs Fixed-Time/Actuated >10, demonstrating score-based selection handles asymmetric demand well. Ped starvation reaches 5.0±1.4 for both adaptive controllers, reflecting the inherent trade-off under directional imbalance.

**S6 Detector Failure:** The most disruptive scenario for demand-dependent controllers. Adaptive-Only vehicle P95 wait jumps to 65.7±2.5s with vehicle starvation 3.1±0.4, compared to Actuated's 25.3±0.8s. This demonstrates vulnerability when demand observations become unreliable.

**S7 Combined Stress:** Under simultaneous NS surge + delay + false ped, Shield logs the highest dangerous_switch_attempt_count (3.7±1.4), confirming active safety filtering. Adaptive variants still outperform baselines on vehicle queue (~4.1 vs ~10.0).

**Overall pattern:** Adaptive+Shield does not uniformly dominate on raw efficiency metrics. Its value lies in maintaining safety invariants, reducing dangerous switch attempts, and providing more stable behavior under uncertainty — with moderate efficiency trade-off relative to Adaptive-Only.

## Metrics

The experiment framework tracks four categories of metrics, aligned with the proposal analysis structure:

**Safety Compliance:**
- `conflict_release_count` — conflicting phases simultaneously green (always 0 in current experiments, as expected by design)
- `dangerous_switch_attempt_count` — switch attempts violating min-green or safety constraints

**Service Guarantee:**
- `vehicle_wait_p95` / `ped_wait_p95` — 95th percentile waiting time
- `vehicle_starvation_count` / `ped_starvation_count` — events where vehicle wait >90s or ped wait >60s

**Efficiency:**
- `average_vehicle_queue_length` / `max_vehicle_queue_length`
- `average_vehicle_waiting_time` / `max_vehicle_waiting_time`
- `average_ped_waiting_time` / `max_ped_waiting_time`

**Stability:**
- `switch_rate_per_300s` — service phase transitions normalized to 300s
- `unnecessary_switch_rate` — switches where target phase had near-zero demand

Per-step CSV logs (36+ columns) are generated during each run and record candidate phase, final action, shield override events, observed vs. true demand, and uncertainty state. These are used by `build_case_studies.py` and are stored in `archive/step_logs/` (regenerable by re-running the experiment scripts).

## Architecture

### Uncertainty Injection Layer (`core/uncertainty.py`)

Runtime wrappers that modify what controllers observe, without changing real SUMO world state:
- **DelayBuffer**: returns demand observations from N steps ago (fixed delay)
- **FalsePedInjector**: injects phantom pedestrian demand via per-step Bernoulli trigger (seed-controlled)
- **DetectorFailure**: spoofs lane demand during configurable failure windows (modes: stuck-off, stuck-on, intermittent)

### Safety Shield (in `scripts/run_experiment.py`, `step_adaptive_shield`)

Three-layer filter between the adaptive scheduler's candidate and the executed action:
1. **Min-hold guard**: blocks switching before `SHIELD_MIN_HOLD` (18s) elapsed in current phase
2. **Score-margin filter**: rejects switches where candidate score leads by less than `SHIELD_SCORE_MARGIN` (1.0)
3. **Starvation override**: forces service for phases unserved for >`SHIELD_STARVATION_LIMIT` (40s), or with demand >= `SHIELD_DEMAND_OVERRIDE` (3)

When the shield blocks a switch, the controller holds the current phase. Clearance enforcement is handled structurally (service-to-service transitions always pass through clearance).

### Scenario Configuration (`configs/scenarios/*.yaml`)

Declarative YAML files specifying each scenario's demand profile, base SUMO config, and uncertainty parameters. The `scenario_loader` validates required fields, computes `can_run_base_mapping` and `pending_features`, and passes uncertainty settings to the runtime injection layer.

## Documentation

- [Project Contract](docs/project_contract_v1.md) — scope, timing parameters, controller specs
- [SUMO–PRISM Mapping](docs/sumo_prism_mapping.md) — how simulation state maps to formal model variables
- [Scenario Config Schema](docs/scenario_config_schema.md) — YAML field reference and validation rules

## Current Scope and Limitations

1. **Single intersection only.** The network is one four-way junction; multi-intersection coordination is out of scope.
2. **Adaptive+Shield is not universally best on efficiency.** In several scenarios (e.g., S1, S6), Actuated or Adaptive-Only achieve lower average wait or queue. The shield's value is in safety preservation and robustness under uncertainty, not raw throughput optimization.
3. **PRISM model is a representative abstraction.** The extended model covers one vehicle direction (NS) and one pedestrian direction (EW), with delay as the modeled uncertainty mode. False pedestrian requests and detector failure are evaluated in SUMO simulation but are not yet abstracted into separate PRISM configurations.
4. **Demand is flow-based, not origin-destination.** Routes use SUMO `<flow>` and `<personFlow>` elements; there is no turning-movement or OD matrix model.
5. **Seed affects departure jitter only.** The route files define deterministic flow rates; SUMO's `--seed` controls per-vehicle/pedestrian departure time jitter within those flows. Across 20 seeds, standard deviations are generally small.
6. **Case studies are evidence packages, not statistical tests.** The 3 shield cases demonstrate specific shield behaviors via step-log evidence. They complement but do not replace the 560-run statistical comparison.
7. **`conflict_release_count` is zero in all experiments.** The 8-phase design structurally prevents conflicting green states. This metric is included for completeness and formal alignment, not because violations were expected.

## License

Course project — academic use only.
