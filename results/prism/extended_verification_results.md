# PRISM Extended Verification Results

## Model
- File: `E:\cps-smart-intersection\prism\intersection_uncertain.pm`
- Properties: `E:\cps-smart-intersection\prism\properties_extended.pctl`

## Configuration: normal (delay_mode=0)

| # | Property | Result |
|---|----------|--------|
| P1 | `P>=1 [ G !"conflict" ]` | Result: true |
| P2 | `P=? [ F<=50 "veh_ns_green" ]` | Result: 1.0 (exact floating point) |
| P3 | `P=? [ F<=50 "ped_ew_green" ]` | Result: 0.002086997613740022 (exact floating point) |
| P4 | `P=? [ F<=30 "veh_ns_green" ]` | Result: 1.0 (exact floating point) |
| P5 | `P=? [ F<=30 "ped_ew_green" ]` | Result: 5.981542297533224E-6 (exact floating point) |
| P6 | `P>=1 [ F "veh_ns_green" ]` | Result: true |
| P7 | `P>=1 [ F "ped_ew_green" ]` | Result: true |
| P8 | `S=? [ "veh_ns_green" ]` | Result: 0.14726567821346875 |
| P9 | `S=? [ "ped_ew_green" ]` | Result: 0.12256100056450403 |
| P10 | `S=? [ "extreme_wait_veh_ns" ]` | Result: 0.11636446789155572 |
| P11 | `S=? [ "extreme_wait_ped_ew" ]` | Result: 0.1272161408675081 |
| P12 | `S=? [ "any_extreme_wait" ]` | Result: 0.23030140996677798 |
| P13 | `R{"wait_veh_ns"}=? [ C<=100 ]` | Result: 39.486530125955106 (exact floating point) |
| P14 | `R{"wait_ped_ew"}=? [ C<=100 ]` | Result: 41.93487214903649 (exact floating point) |

## Configuration: delayed (delay_mode=1)

| # | Property | Result |
|---|----------|--------|
| P1 | `P>=1 [ G !"conflict" ]` | Result: true |
| P2 | `P=? [ F<=50 "veh_ns_green" ]` | Result: 1.0 (exact floating point) |
| P3 | `P=? [ F<=50 "ped_ew_green" ]` | Result: 9.873121377411442E-4 (exact floating point) |
| P4 | `P=? [ F<=30 "veh_ns_green" ]` | Result: 1.0 (exact floating point) |
| P5 | `P=? [ F<=30 "ped_ew_green" ]` | Result: 2.5239340028087106E-6 (exact floating point) |
| P6 | `P>=1 [ F "veh_ns_green" ]` | Result: true |
| P7 | `P>=1 [ F "ped_ew_green" ]` | Result: true |
| P8 | `S=? [ "veh_ns_green" ]` | Result: 0.15959323563707387 |
| P9 | `S=? [ "ped_ew_green" ]` | Result: 0.1379472244465445 |
| P10 | `S=? [ "extreme_wait_veh_ns" ]` | Result: 0.11707373439079598 |
| P11 | `S=? [ "extreme_wait_ped_ew" ]` | Result: 0.12761999724597972 |
| P12 | `S=? [ "any_extreme_wait" ]` | Result: 0.23149440268402022 |
| P13 | `R{"wait_veh_ns"}=? [ C<=100 ]` | Result: 35.35586532746312 (exact floating point) |
| P14 | `R{"wait_ped_ew"}=? [ C<=100 ]` | Result: 42.5617002284146 (exact floating point) |

## Interpretation

### Safety (P1)
No-conflict invariant holds under both normal and delayed modes.

### Service Reachability (P2-P5)
P2/P4: Vehicle_NS green is reached with probability 1.0 even within
30 steps, because the model starts in phase=0 (Vehicle_NS).
P3/P5: Ped_EW green requires traversing phases 0→1→2→3→4, which
takes many probabilistic steps. The low bounded probability reflects
the model's stochastic dwell times, not a design flaw. Under delay,
P3/P5 decrease further because reduced p_switch slows phase progression.

### Eventual Service (P6-P7)
Both directions are guaranteed to eventually receive green (P=1.0),
confirming no starvation deadlock exists in the model.

### Steady-State Service Fraction (P8-P9)
Vehicle_NS gets ~14.7% of total time (normal) vs ~16.0% (delayed).
Ped_EW gets ~12.3% vs ~13.8%. Under delay, each phase runs longer
before switching, so both fractions increase slightly.

### Extreme Wait Risk (P10-P12)
~11.6-12.7% steady-state probability of extreme wait per direction.
Under delay, these increase marginally (~0.1%). The any_extreme_wait
probability ~23% means roughly 1 in 4 time steps has at least one
direction in extreme wait — this corresponds to SUMO's starvation events.

### Cumulative Wait (P13-P14)
Over 100 steps, veh_ns accumulates ~39.5 unserved-demand steps (normal)
vs ~35.4 (delayed). The reduction under delay occurs because veh_ns
phase runs longer (slower switching), giving it more service time.
Ped_ew wait increases from 41.9 to 42.6, confirming delay hurts ped service.
