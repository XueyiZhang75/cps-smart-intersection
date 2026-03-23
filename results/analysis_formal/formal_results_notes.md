# Formal Experiment Results — Key Observations

Source: `results/batch_results_formal.csv` (4 scenarios x 4 controllers)

## balanced
- Adaptive-only achieves the lowest avg vehicle queue (2.13) and avg vehicle wait (2.4s),
  but at the cost of higher avg ped wait (4.6s) compared to Actuated (2.2s).
- Adaptive+Shield reduces max ped wait from 63s to 58s vs Adaptive-only,
  while keeping vehicle metrics competitive (avg queue 2.48).
- Fixed-time has the worst performance across all metrics.

## ped_heavy
- With 2.5x pedestrian load, Adaptive+Shield achieves the lowest avg ped wait (2.4s)
  and lowest max ped wait (49s), outperforming Adaptive-only on pedestrian metrics.
- Adaptive-only and Actuated tie on avg ped wait (2.7s), but Adaptive-only
  has better vehicle queue (2.91 vs 3.10).
- Fixed-time max ped wait reaches 86s — the highest across all scenarios.

## vehicle_heavy
- Under 2.5x vehicle load, Adaptive variants dramatically outperform baselines:
  avg queue 4.6-4.8 vs 12.4-13.7 for Fixed-time/Actuated.
- The vehicle-pedestrian trade-off is starkest here: Adaptive-only max ped wait
  reaches 100s, while Adaptive+Shield limits it to 98s — shield provides marginal
  pedestrian protection at no vehicle cost (avg vehicle wait identical at 1.8s).
- Actuated performs worse than Fixed-time on avg queue (13.71 vs 12.37),
  suggesting its sequential rotation is suboptimal under heavy directional load.

## bursty_ped
- Burst pedestrian arrivals create the clearest Adaptive vs Adaptive+Shield separation:
  max ped wait 72s vs 57s (15s gap), the largest shield benefit across all scenarios.
- Adaptive+Shield also achieves the best avg vehicle queue (2.71) in this scenario,
  indicating that shield stability benefits both vehicle and pedestrian metrics.
- Fixed-time max ped wait (83s) confirms its inability to respond to demand bursts.
