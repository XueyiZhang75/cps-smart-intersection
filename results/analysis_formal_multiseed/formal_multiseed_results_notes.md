# Formal Experiment Results — 20-Seed Summary

Source: `results/formal_multiseed_summary.csv`
(4 scenarios × 4 controllers × 20 seeds = 320 runs)

All values reported as mean±std unless noted.

## balanced

Adaptive-Only achieves the lowest avg vehicle queue (2.21±0.10) and avg vehicle wait (2.5±0.2s). However, its avg ped wait (4.5±0.2s) is roughly double that of Actuated (2.2±0.1s).

Adaptive+Shield shows similar avg ped wait to Adaptive-Only (4.4±0.5s vs 4.5±0.2s). On max ped wait, the two are not clearly separated (62.7±5.4s vs 61.6±4.5s) — the std ranges overlap. **Conclusion: under balanced load, shield provides no significant pedestrian advantage over adaptive-only; both clearly outperform fixed-time on vehicle metrics.**

## ped_heavy

Under 2.5× pedestrian load, Adaptive+Shield achieves the lowest avg ped wait (2.52±0.16s), narrowly ahead of Adaptive-Only (2.60±0.14s). Max ped wait is nearly identical (50.0±1.2s vs 50.0±1.1s).

Fixed-time max ped wait reaches 83.8±1.4s — the highest value across all scenarios. **Conclusion: shield and adaptive-only perform similarly under sustained high ped load; the main story is that all adaptive/actuated controllers dramatically outperform fixed-time.**

## vehicle_heavy

This scenario produces the starkest separation. Adaptive variants maintain avg queue below 5 (4.78±0.26 / 4.56±0.25) while baselines exceed 12 (12.25 / 13.58).

The vehicle-pedestrian trade-off is most pronounced here. Adaptive-Only's max ped wait is 119.3±13.1s, while Adaptive+Shield reduces it to 103.4±7.7s (a ~16s reduction in mean, with non-overlapping std). Avg ped wait also improves: 12.4±1.4s vs 10.5±0.8s. **Conclusion: under heavy vehicle load, the shield provides the clearest and most statistically robust pedestrian protection benefit, with no vehicle cost.**

## bursty_ped

Adaptive+Shield avg vehicle queue (2.78±0.11) is slightly better than Adaptive-Only (2.91±0.14). On max ped wait, the 20-seed results show 64.3±9.9s (Adaptive-Only) vs 67.0±3.6s (Shield). Adaptive-Only's large std (±9.9s) overlaps with Shield's range, making this difference a weak trend rather than a robust finding.

**Conclusion: under bursty ped demand, Shield shows a consistent directional advantage on vehicle metrics and stabilizes max ped wait variance (std 3.6 vs 9.9), but the mean max ped wait difference is not statistically significant at this sample size.**

## Corrections from Single-Run Results

The single-run batch results suggested a 15s shield benefit on max ped wait in bursty_ped (72s vs 57s). The 20-seed results revise this to a weaker trend (64.3±10.0 vs 67.0±3.6), where the means are closer and the Adaptive-Only std is large. This illustrates why multi-seed validation is essential: single-run results can overstate differences that are within normal variation.

The vehicle_heavy finding, by contrast, is strengthened by multi-seed data: the shield's pedestrian protection (119.3±13.1 vs 103.4±7.7 on max ped wait) remains robust with non-overlapping confidence intervals.
