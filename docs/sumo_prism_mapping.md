# SUMO → PRISM Semantic Mapping

This document describes how the SUMO simulation model is abstracted into the PRISM formal model (`prism/intersection_base.pm`).

## Overview

The PRISM model is a **Discrete-Time Markov Chain (DTMC)** that abstracts the SUMO intersection into a finite-state probabilistic model. It preserves the phase structure and safety invariants while discarding continuous vehicle/pedestrian dynamics.

## Phase Mapping

| PRISM `phase` | SUMO Phase Name | Type | SUMO Index |
|---------------|----------------|------|------------|
| 0 | Vehicle_NS | service | 0 |
| 1 | Clearance_after_NS | clearance | 1 |
| 2 | Vehicle_EW | service | 2 |
| 3 | Clearance_after_EW | clearance | 3 |
| 4 | Ped_EW | service | 4 |
| 5 | Clearance_after_Ped_EW | clearance | 5 |
| 6 | Ped_NS | service | 6 |
| 7 | Clearance_after_Ped_NS | clearance | 7 |

The phase encoding is identical between SUMO and PRISM. The 8-phase cycle structure is preserved exactly.

## Time-in-Phase Abstraction

| PRISM `tip_bucket` | SUMO Semantics | Range (Vehicle) | Range (Ped) |
|--------------------|----------------|-----------------|-------------|
| 0 | before_min_green | tip < 15s | tip < 10s |
| 1 | eligible (between min and max green) | 15s ≤ tip < 30s | 10s ≤ tip < 15s |
| 2 | expired (at or after max green) | tip ≥ 30s | tip ≥ 15s |

In SUMO, `time_in_phase` is a continuous integer counter (1s steps). In PRISM, it is abstracted to 3 discrete buckets. The transition probabilities between buckets approximate the average dwell time in each bucket:

- `0 → 0` with probability 0.7 (vehicle) or 0.6 (ped): stays in before_min
- `0 → 1` with probability 0.3 (vehicle) or 0.4 (ped): reaches min_green
- `1 → 1` with probability 0.4-0.8: stays eligible
- `1 → 2` with probability 0.2: expires

These probabilities are calibrated to roughly match the average phase durations observed in SUMO experiments.

## Demand Abstraction

| PRISM Variable | SUMO Source | Abstraction |
|----------------|------------|-------------|
| `req_veh_ns` | `getLastStepHaltingNumber("N2C_1") + ... "S2C_1"` | Binary: 0 = no halting vehicles, 1 = at least one |
| `req_veh_ew` | `getLastStepHaltingNumber("E2C_1") + ... "W2C_1"` | Binary: 0/1 |
| `req_ped_ew` | persons waiting on `:J0_w0` or `:J0_w2` | Binary: 0/1 |
| `req_ped_ns` | persons waiting on `:J0_w1` or `:J0_w3` | Binary: 0/1 |

In SUMO, demand is a continuous count (0, 1, 2, ...). In the PRISM base model, it is abstracted to binary presence (0 or 1). This is sufficient for safety property verification because the safety invariants (no conflict, clearance enforcement) do not depend on exact demand quantities.

Demand transitions are modeled as independent Bernoulli processes:
- Arrival probability: 0.3 (vehicle), 0.15 (pedestrian) per step
- Departure probability: 0.15 (vehicle), 0.10 (pedestrian) per step

## Clearance Enforcement

| PRISM | SUMO |
|-------|------|
| `cl_count` increments from 0 to `CLEARANCE_DUR=3` | `time_in_phase` counts 1..3 during clearance |
| Phase can only advance to next service phase when `cl_count = CLEARANCE_DUR` | Phase advances when `time_in_phase >= duration` |
| Service phase entered with `cl_count=0` guaranteed | `time_in_phase` reset to 0 on phase entry |

The clearance counter ensures that every service-to-service transition passes through exactly `CLEARANCE_DUR` steps of clearance. This directly models the SUMO shield's `ENTER_CLEARANCE` enforcement.

## Safety Labels

| PRISM Label | Definition | SUMO Correspondence |
|-------------|-----------|---------------------|
| `conflict` | Service phase active AND cl_count > 0 | `conflict_flag` in step log |
| `veh_conflict_during_ped` | Ped phase AND vehicle phase simultaneously | Structurally impossible (single phase variable) |
| `clearance` | Phase 1, 3, 5, or 7 active | `entered_clearance` in step log |
| `veh_green` | Phase 0 or 2 | Vehicle service active |
| `ped_green` | Phase 4 or 6 | Pedestrian service active |

## What This Model Deliberately Omits

1. **Individual vehicle/pedestrian trajectories**: No vehicle positions, speeds, or lane-level queuing
2. **Exact timing**: Continuous seconds abstracted to 3 time buckets
3. **Adaptive scoring**: The score function (W_Q, W_W, W_C) is not modeled; switching decisions are probabilistic
4. **Uncertainty injection**: delay_detection, false_ped_request, detector_failure not in base model (planned for Stage G)
5. **Multi-lane dynamics**: Single demand bit per direction, no turning movements
6. **Shield's three-layer logic**: Abstracted into structural transition rules rather than explicit shield module

## Why This Abstraction Is Sufficient for Basic Safety

The two core safety properties are:
1. **No conflict release**: No two service phases are ever simultaneously active
2. **Clearance enforcement**: Every service-to-service transition goes through clearance

Both properties depend only on the **phase transition structure**, not on exact demand values, queue lengths, or vehicle trajectories. The PRISM model preserves this structure exactly: transitions between service phases are only possible through clearance phases, and the single `phase` variable guarantees mutual exclusion.

The demand and timing abstractions affect **when** transitions happen (efficiency), not **whether** transitions are safe (safety). Therefore, the base model is sufficient to formally verify these safety invariants.

---

# Extended Model Mapping (Stage G)

The extended model (`prism/intersection_uncertain.pm`) adds service guarantee, extreme wait risk, and delay uncertainty to the base model.

## Wait-Risk Buckets

| PRISM Variable | Range | SUMO Correspondence |
|----------------|-------|---------------------|
| `wr_veh_ns` | 0-2 | Vehicle NS starvation risk |
| `wr_ped_ew` | 0-2 | Ped EW starvation risk |

| Bucket | PRISM Semantics | SUMO Equivalent |
|--------|----------------|-----------------|
| 0 (ok) | No demand, or demand being served | vehicle_starvation_flag=0 |
| 1 (moderate) | Demand present, not served, within normal range | waiting but below threshold |
| 2 (extreme) | Demand present, not served, prolonged | vehicle waiting > VEHICLE_STARVATION_THRESHOLD (90s) |

Escalation probability `p_escalate=0.04` per step means on average ~25 steps to reach extreme from moderate. This roughly corresponds to SUMO's observation that vehicles start approaching the 90s starvation threshold after sustained unserved demand.

## Service Labels

| PRISM Label | Definition | SUMO Correspondence |
|-------------|-----------|---------------------|
| `serve_veh_ns` | phase=0 & req_veh_ns=1 | Vehicle NS phase active with NS demand present |
| `serve_ped_ew` | phase=4 & req_ped_ew=1 | Ped EW phase active with EW ped demand present |

These track "demand is actively being served" — the service phase is green AND there is demand for it. The bounded reachability property `P=? [F<=T serve_*]` asks: starting from a waiting state, how likely is service within T steps?

## Delay Mode Mapping

| PRISM | SUMO (Stage C) |
|-------|---------------|
| `delay_mode=0` | No uncertainty injection |
| `delay_mode=1` | `delay_detection.enabled=true` with `delay_seconds=5` |
| Effect: `p_switch` drops from 0.6 to 0.35 | Controller sees stale demand, switches less responsively |

The reduced `p_switch` under delay models the fact that delayed detection makes the adaptive scheduler slower to respond to new demand. In SUMO, this manifests as higher queue lengths and waiting times (confirmed in S4 experiments).

## Reward Structures

| PRISM Reward | SUMO Metric |
|-------------|-------------|
| `wait_veh_ns`: 1 per step when req=1 & phase≠0 | `average_vehicle_waiting_time` (conceptual) |
| `wait_ped_ew`: 1 per step when req=1 & phase≠4 | `average_ped_waiting_time` (conceptual) |

## What the Extended Model Still Omits

1. **Wait risk for all 4 directions**: Only veh_ns and ped_ew tracked (2 of 4)
2. **false_ped_request and detector_failure**: Not modeled (only delay_mode)
3. **Adaptive score function / shield three-layer logic**: Abstracted as probabilistic switching
4. **Exact queue lengths**: Binary demand only
5. **Demand correlation**: All 4 demand bits are independent

## Key Results and SUMO-PRISM Alignment

| Property | Normal (delay=0) | Delayed (delay=1) | Direction |
|----------|-----------------|-------------------|-----------|
| Extreme wait risk (veh_ns) | 11.6% | 11.7% | Slightly worse with delay |
| Extreme wait risk (ped_ew) | 12.7% | 12.8% | Slightly worse with delay |
| Cumulative wait (veh_ns, 100 steps) | 39.5 | 35.4 | Counter-intuitively lower with delay — because delayed switching also delays leaving the current veh phase, so veh_ns gets more service time |
| Cumulative wait (ped_ew, 100 steps) | 41.9 | 42.6 | Higher with delay — ped phases receive less responsive service |

This asymmetry (vehicle wait decreasing but ped wait increasing under delay) matches the SUMO observation that delay_detection primarily degrades pedestrian service while partially benefiting the currently-serving vehicle direction.
