# Case 2: Ped Request During Vehicle Phase — Safe Clearance Transition

## Proposal reference
Shield evidence example 2: "pedestrian request arrives during conflicting vehicle phase —
system does not jump directly to ped phase but transitions safely through clearance"

## Configuration
- Controller: adaptive_shield
- Scenario: intersection_ped_heavy
- Seed: 0
- Duration: 120s
- Key window: t=25.0–61.0s

## Verified evidence sequence
The following strict sequence was verified in the step log:

1. **t=28s**: Ped demand detected during vehicle phase (ped_demand_ew_obs=1 or ped_demand_ns_obs=1)
2. **t=47s**: Adaptive scheduler selected a ped phase as candidate (candidate_phase_name = Ped_*)
3. **t=47s**: System entered clearance phase (entered_clearance=1) — did NOT jump directly to ped
4. **t=51s**: Ped service phase actually started (current_phase_name = Ped_*)

Throughout this entire sequence, `conflict_flag=0` — no illegal state was ever applied.

## Phase transitions in this window
- t=30s: V_NS → Cl_NS
- t=33s: Cl_NS → V_EW
- t=48s: V_EW → Cl_EW
- t=51s: Cl_EW → P_EW
- t=61s: P_EW → Cl_PEW

## Evidence
- Ped demand visible during vehicle phase at t=28s
- Ped candidate selected at t=47s (visible as dashed line in timeline plot)
- Clearance entered at t=47s before ped service
- Ped service started at t=51s
- No `conflict_flag=1` events in the entire window
- The shield's clearance enforcement is structural: any service-to-service
  transition must go through the corresponding clearance phase

## Why this matters
Even when the adaptive scheduler urgently wants to serve waiting pedestrians,
the system never skips clearance. This guarantees that conflicting vehicle and
pedestrian movements are never simultaneously active.
