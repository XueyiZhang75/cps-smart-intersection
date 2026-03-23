# Case 3: False Pedestrian Button — Shield Suppresses Overreaction

## Proposal reference
Shield evidence example 3: "false/burst pedestrian button presses —
shield prevents every phantom trigger from becoming an actual phase switch"

## Configuration
- Controller: adaptive_shield
- Scenario: S5_false_ped_and_burst (bursty_ped base + runtime false ped injection)
- Seed: 0
- Duration: 120s
- Key window: t=1–42.0s

## What happened
The FalsePedInjector was active throughout the simulation (false_rate=0.2, Bernoulli
per step on crossings :J0_w0 and :J0_w2). Within the analysis window:

- **39 steps** had phantom_ped_count > 0 (false ped signal present)
- **4 phase switches** actually occurred
- **1 actual entries** into ped service phases (Ped_EW or Ped_NS)
- **4 shield overrides** (holds) occurred

The phantom signals inflated the ped demand score, causing the adaptive scheduler
to frequently propose switching to ped phases. However, the shield's min_hold
constraint and score margin filter prevented most of these from becoming actual
switches. The system did not react to every phantom trigger — instead, it maintained
stable phase durations and only switched when the combined real + phantom demand
was sustained enough to overcome the shield's thresholds.

## How the shield provides "debouncing"
The current implementation does not have a dedicated debounce filter. Instead,
the shield's existing constraints achieve a debounce effect:
1. **SHIELD_MIN_HOLD (18s)**: prevents switching within 18s of phase start,
   so transient phantom signals during this window are ignored
2. **SHIELD_SCORE_MARGIN (1.0)**: requires the candidate's score to exceed
   the current phase's score by at least 1.0, filtering out marginal phantom-
   boosted scores
3. **Starvation override (40s)**: ensures that if a ped phase is genuinely
   starved, it eventually gets served regardless — so the debouncing doesn't
   cause permanent ped starvation

This is honest: it's not classical signal debouncing, but constraint-based
filtering that achieves a similar practical effect.

## Evidence
- `false_ped_active=1` throughout window
- `phantom_ped_count > 0` on 39 steps
- Only 1 actual entries into ped service phases despite 39 phantom steps
- Shield overrides visible in key_events.csv

## Why this matters
Without the shield, the adaptive scheduler would chase every phantom ped signal,
causing frequent unnecessary phase switches that degrade both vehicle throughput
and real pedestrian service. The shield acts as a stability layer that absorbs
false input noise.
