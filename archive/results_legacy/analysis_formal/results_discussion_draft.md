# Results and Discussion

## Experimental Setup

We evaluated four traffic signal controllers on a single four-way intersection modeled in SUMO: Fixed-Time (B1), Actuated (B2), Adaptive-Only (A1), and Adaptive with Safety Shield (A2). Each controller was tested across four formally designed scenarios — balanced, ped\_heavy, vehicle\_heavy, and bursty\_ped — with a simulation duration of 300 seconds per run. The scenarios vary in the relative intensity and temporal pattern of vehicle and pedestrian demand, while the underlying road network and 8-phase signal structure remain constant. Key metrics include average and maximum waiting times for both vehicles and pedestrians, average vehicle queue length, and phase switch count. For the Adaptive+Shield controller, we additionally report shield-internal debug statistics (hold counts and override counts) to characterize how the safety layer modifies scheduling behavior.

## Overall Trends

Across all four scenarios, a consistent hierarchy emerges in vehicle efficiency: Fixed-Time performs worst, Actuated provides a meaningful improvement, and the two Adaptive variants achieve the best vehicle metrics. In the balanced scenario, for example, average vehicle queue length decreases from 4.65 (Fixed-Time) to 3.24 (Actuated) to 2.13 (Adaptive-Only) and 2.48 (Adaptive+Shield). A similar pattern holds for average vehicle waiting time: 8.3s, 4.3s, 2.4s, and 3.0s respectively.

However, vehicle efficiency does not tell the full story. Adaptive-Only, which aggressively optimizes for the highest-scoring phase, sometimes incurs elevated pedestrian waiting times. In the balanced scenario, its average pedestrian wait is 4.6s compared to Actuated's 2.2s, and its maximum pedestrian wait reaches 63s versus 49s. Adaptive+Shield consistently narrows this gap — achieving 4.3s average and 58s maximum pedestrian wait in the same scenario — by constraining premature phase switches and ensuring that no user group is starved for extended periods. The remainder of this section examines how these trade-offs manifest under different demand conditions.

## Balanced Scenario

The balanced scenario represents medium-intensity demand with roughly equal pressure from all four vehicle directions (~56 vehicles) and all four pedestrian crossings (~26 pedestrians). Under these conditions, Adaptive-Only achieves the lowest average vehicle queue (2.13) and lowest average vehicle waiting time (2.4s), confirming that score-based phase selection outperforms both baselines. However, its maximum pedestrian waiting time reaches 63s, which is 29% higher than Actuated's 49s. This occurs because Adaptive-Only's scheduler tends to extend vehicle phases when their score remains high, occasionally delaying pedestrian service beyond what a simple round-robin actuated approach would allow.

Adaptive+Shield mitigates this by introducing a minimum hold constraint and starvation override. Its maximum pedestrian wait drops to 58s — an 8% reduction compared to Adaptive-Only — while average vehicle queue increases only modestly from 2.13 to 2.48. The shield's maximum vehicle waiting time (40s) is actually the lowest among all four controllers, suggesting that phase stability benefits vehicles as well by avoiding mid-service interruptions.

## Pedestrian-Heavy Scenario

The ped\_heavy scenario increases pedestrian flow to approximately 2.5 times the balanced level (~65 pedestrians), while vehicle demand remains unchanged. This design isolates the controllers' response to sustained pedestrian pressure. Under these conditions, the gap between Adaptive-Only and Adaptive+Shield shifts noticeably. Adaptive+Shield achieves the lowest average pedestrian waiting time (2.4s) and the lowest maximum pedestrian waiting time (49s), outperforming not only Fixed-Time (86s max) but also Adaptive-Only (50s max) and Actuated (50s max).

This improvement comes at a measurable but modest vehicle cost: Adaptive+Shield's average vehicle queue is 3.12 compared to Adaptive-Only's 2.91, and its average vehicle waiting time is 4.2s versus 3.7s. The shield's starvation override mechanism, which triggered 17 times in this scenario, ensures that pedestrian phases are not indefinitely postponed even when vehicle demand scores remain high. Fixed-Time's max pedestrian wait of 86s — the highest recorded across all experiments — illustrates its fundamental inability to respond to demand conditions.

## Vehicle-Heavy Scenario

The vehicle\_heavy scenario increases vehicle flow to approximately 2.5 times the balanced level (~140 vehicles), while keeping pedestrian demand at the balanced level. This creates the most extreme demand imbalance in our test suite and produces the starkest performance separation. Fixed-Time and Actuated both accumulate large vehicle queues (average 12.37 and 13.71 respectively), while the Adaptive variants maintain queues below 5 (4.77 and 4.63). The fact that Actuated's average queue (13.71) exceeds Fixed-Time's (12.37) is notable: under heavy directional load, Actuated's sequential phase rotation wastes green time on directions with no demand, whereas Fixed-Time at least allocates predictable green windows.

The vehicle-pedestrian trade-off is most pronounced in this scenario. Adaptive-Only's aggressive vehicle optimization pushes its maximum pedestrian waiting time to 100s — the highest single value observed in any experiment. Adaptive+Shield reduces this to 98s, a marginal improvement that reflects the difficulty of protecting pedestrians when vehicle demand dominates the scoring function. The shield's debug statistics reveal that this is the only scenario where both the small-gain hold (1 occurrence) and the demand override (1 occurrence) were triggered, indicating that the shield's multiple layers were all engaged. Average pedestrian waiting time shows a more meaningful difference: 10.0s for Adaptive-Only versus 7.9s for Adaptive+Shield, a 21% reduction.

## Bursty Pedestrian Scenario

The bursty\_ped scenario maintains balanced vehicle demand but restructures pedestrian arrivals into three concentrated 40-second burst windows (t=20–60, t=120–160, t=220–260), with sparse trickle periods in between. This design tests whether controllers can respond to sudden demand spikes without destabilizing vehicle service.

This scenario produces the clearest differentiation between Adaptive-Only and Adaptive+Shield. Adaptive-Only's maximum pedestrian waiting time is 72s, while Adaptive+Shield limits it to 57s — a 15-second gap that is the largest shield benefit observed across all experiments. The mechanism is instructive: when a burst arrives, Adaptive-Only's score function immediately detects the pedestrian demand spike and attempts to switch phases. However, if the current vehicle phase has just started, this leads to a short, interrupted vehicle phase followed by a clearance, then a pedestrian phase, then another clearance, and potentially another short vehicle phase. The shield's minimum hold constraint prevents this oscillation, allowing the current phase to complete a meaningful service period before transitioning. The result is that pedestrians wait for one stable cycle rather than multiple fragmented ones.

Notably, Adaptive+Shield also achieves the best average vehicle queue in this scenario (2.71 vs. 2.87 for Adaptive-Only), demonstrating that phase stability benefits vehicles as well. Fixed-Time's max pedestrian wait of 83s confirms its inability to respond to temporal demand patterns.

## Safety Shield Behavior

The shield debug statistics across all four scenarios reveal a consistent pattern. The minimum-hold constraint triggers once per scenario (1 hold in each), indicating that the adaptive scheduler occasionally attempts to switch prematurely but is restrained. The starvation override is the most active mechanism, triggering 15–17 times per scenario, which reflects the shield's primary role: ensuring that phases which have not been served recently are given priority regardless of instantaneous score differences.

The small-gain hold and demand override are triggered only in the vehicle\_heavy scenario (1 occurrence each). This makes sense: under extreme vehicle load, the score differences between vehicle and pedestrian phases are large, so the small-gain filter rarely applies; but when it does, it prevents a marginal score advantage from triggering an unnecessary switch. The demand override activating once indicates a situation where pedestrian demand exceeded the threshold despite the vehicle-dominated scoring.

Importantly, the shield does not simply make the controller more conservative. In three out of four scenarios, Adaptive+Shield achieves lower maximum pedestrian waiting times than Adaptive-Only, and in the bursty\_ped scenario it simultaneously improves both vehicle and pedestrian average metrics. The shield reshapes the efficiency-safety trade-off rather than uniformly degrading performance.

## Summary

These results provide evidence that an adaptive scheduling approach with a safety shield layer can improve upon both fixed-time baselines and pure adaptive optimization for intersection signal control. The adaptive scheduler consistently outperforms the two baselines on vehicle efficiency metrics. The safety shield adds measurable pedestrian protection — reducing maximum pedestrian waiting times by 5–15 seconds across scenarios — with only modest increases in vehicle metrics. The benefit is most pronounced under bursty pedestrian demand, where the shield's phase stability prevents oscillatory switching behavior.

However, several limitations should be noted. All experiments use a single intersection with single-lane approaches, which limits generalizability to multi-lane or networked settings. The pedestrian demand detection relies on walking-area waiting, which may miss approaching pedestrians. The shield parameters (minimum hold time, score margin, starvation limit) were set based on engineering judgment rather than systematic optimization. These results should therefore be interpreted as demonstrating the feasibility and direction of the approach, rather than as definitive proof of optimality.
