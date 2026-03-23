# Case 1: Min-Green Hold

## Proposal reference
Shield evidence example 1: "minimum green not satisfied — shield blocks premature switch"

## Configuration
- Controller: adaptive_shield
- Scenario: intersection_balanced
- Seed: 0
- Duration: 120s
- Key window: t=6.0–31.0s

## What happened
At t=16.0s, the adaptive scheduler selected **V_EW** as the
best candidate (current phase: **V_NS**, time_in_phase=15s).

The safety shield blocked this switch because SHIELD_MIN_HOLD=18s had not been reached
(override_reason: `hold:min_hold (16s < 18s)`). The controller continued serving
the current phase until the min_hold constraint was satisfied.

This event is also flagged as `dangerous_switch_attempt_flag=1`, confirming that
without the shield, the controller would have switched prematurely.

## Evidence
- `override_flag=1` at t=16.0s
- `override_reason=hold:min_hold (16s < 18s)`
- `final_action=hold_by_shield`
- `dangerous_switch_attempt_flag=1`

## Why this matters
The shield prevents phase oscillation and ensures each service phase receives
adequate green time before being interrupted, even when the adaptive scorer
detects higher-priority demand elsewhere.
