# Proposal Matrix Results — Key Observations

Source: `results/proposal_multiseed_summary.csv`
(7 scenarios × 4 controllers × 20 seeds = 560 runs)

All values reported as mean±std.

## Omitted Charts

- **conflict_release_count**: all-zero across all 28 combinations. Chart `fig_conflict_release_count.png` omitted. This confirms the metric was never triggered under any tested condition.

## Overall Trends

Fixed-Time (B1) consistently shows the worst vehicle queue and waiting times, and the highest pedestrian starvation counts. Actuated (B2) improves vehicle metrics through demand-responsive switching but follows a rigid sequential rotation. Adaptive-Only (A1) achieves the best vehicle efficiency by score-based phase selection, but sometimes at the cost of elevated pedestrian waiting. Adaptive+Shield (A2) trades a small amount of vehicle efficiency for improved safety margins (dangerous switch prevention) and, in several scenarios, better pedestrian starvation outcomes.

## S1: Balanced

Baseline scenario. Adaptive-Only leads on AvgVQ (2.21) and AvgVW (2.5s). Actuated has the lowest AvgPW (2.2s). Shield's DangerAttempt=1.1 confirms it actively prevents premature switches even under normal load.

## S2: Directional Surge

NS surge creates strong directional imbalance. Fixed-Time/Actuated AvgVQ exceeds 10, while both Adaptive variants stay at ~3.5. PedStarve=5.0 for both Adaptive controllers — the surge direction dominates, leaving pedestrians waiting. Shield provides no additional benefit here because the surge is a demand-profile issue, not a safety/stability issue.

## S3: Ped Heavy

High pedestrian pressure. Shield achieves the lowest AvgPW (2.52s) and lowest PedP95 (20.8s). Fixed-Time PedStarve=10.8 is the highest across all S3 controllers.

## S4: Delay Detection

5s sensing delay degrades Adaptive controllers' responsiveness. Compared to S1, Adaptive-Only AvgPW drops from 4.46 to 3.5s (delayed switching accidentally reduces ped interruptions). Shield DangerAttempt=0.0 — delay does not introduce new dangerous attempts, confirming shield stability under sensing uncertainty.

## S5: False Ped And Burst

False ped injection + burst arrivals. Shield's DangerAttempt is highest here (4.0), showing it actively blocks phantom-driven premature switches. Adaptive-Only AvgVW=4.5s vs Shield 4.8s — shield's min_hold constraint slightly increases vehicle wait but prevents oscillation.

## S6: Detector Failure

NS detector stuck-off (t=60-180s). This is the most damaging scenario for Adaptive controllers: VehP95 jumps to 65.7s (A1) / 67.5s (A2), and VehStarve reaches 3.1 / 3.8. Baselines are unaffected because Fixed-Time ignores demand and Actuated still detects EW demand. Shield provides DangerAttempt prevention but cannot fix the underlying observation loss.

## S7: Combined Stress

Surge + delay + false_ped simultaneously. Adaptive variants maintain AvgVQ ~4.1 (vs Fixed-Time 10.0). Shield DangerAttempt=3.7 — the second-highest after S5, confirming the shield is actively filtering combined noise. PedStarve=2.4 for both Adaptive controllers, showing the trade-off between vehicle efficiency and ped service persists under maximum stress.
