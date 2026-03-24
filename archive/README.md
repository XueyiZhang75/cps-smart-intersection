# Archive

This directory holds files from earlier development stages that are not part of the final project deliverable.

## Contents

### `scripts_legacy/`
Scripts superseded by the final pipeline:
- `run_batch_experiments.py` — early 4-scenario batch runner (superseded by `run_multiseed_proposal_matrix.py`)
- `run_multiseed_formal_experiments.py` — 4-scenario × 20 seed version (superseded)
- `analyze_formal_results.py` — analysis for 4-scenario results (superseded by `analyze_proposal_matrix.py`)
- `analyze_multiseed_results.py` — early multiseed analysis (superseded)
- `test_traci_connection.py` — minimal TraCI connectivity check from initial setup

### `controllers_dev/`
Standalone single-file controller scripts written during early development.
The authoritative controller implementations are embedded in `scripts/run_experiment.py`.
These files are kept for reference only.

### `results_legacy/`
Earlier experiment results superseded by the proposal-level matrix:
- `batch_results_formal.*` — 4-scenario single-run results
- `formal_multiseed_raw.*` / `formal_multiseed_summary.*` — 4-scenario × 20 seed results
- `analysis_formal/` / `analysis_formal_multiseed/` — charts from above
- Individual single-run JSON files from early integration tests

The final authoritative results are in `results/proposal_multiseed_*.csv/json`.

### `step_logs/`
Per-step simulation CSV logs from all 560 experimental runs (26 MB total).
These are regenerable by running `scripts/run_multiseed_proposal_matrix.py`.
They are archived here to keep the main repository lightweight.
