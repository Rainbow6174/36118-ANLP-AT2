# CrisisLens — Member 3 canonical results (seed-42, as-run 2026-09-23)

All numbers are seed 42. Analysis model = Twitter-RoBERTa (A4); deployment model = DistilBERT (A1). Dataset = HumAID events_set1_47K (13 events). Held-out event = cyclone_idai_2019 (n=779). macro-F1 is the primary metric; accuracy is never reported alone.

## Table 1 — Seen HumAID test (Regime A, macro-F1)

| Model | macro-F1 | note |
| --- | --- | --- |
| Word + character TF-IDF + Logistic Regression (M2 baseline) | 0.7262 | transparent traditional reference |
| DistilBERT plain (deploy) | 0.755 | ~2x cheaper than RoBERTa |
| Twitter-RoBERTa plain (analysis) | 0.762 | seed 123 = 0.766; 2-seed mean 0.764, range 0.004 |

Imbalance ablation: class-weighted and focal were tested on both encoders. Both LOWERED macro-F1 and did NOT raise the smallest-3 class F1, so the pre-registered go/no-go REJECTS them; final = plain. Honest trade-off to report: they do raise minority-class recall (e.g. requests_or_urgent_needs recall 0.54 -> 0.71/0.77) at a precision cost.

## Table 2 — Calibration + selective prediction

| Metric | RoBERTa A4 (analysis) | DistilBERT A1 (deploy) |
| --- | --- | --- |
| Seen test macro-F1 | 0.762 | 0.755 |
| Fitted temperature T | 1.351 | 1.102 |
| Seen ECE (pre -> post, 15 bins) | 0.093 -> 0.035 | 0.046 -> 0.026 |
| Review threshold tau (5% target risk, on val) | 0.894 | 0.887 |
| Seen auto-accept coverage / risk at tau | 45.3% / 0.045 | 47.3% / 0.051 |

## Table 3 — Cross-event: seen vs unseen (RoBERTa seed 42, per-class F1)

| Class | Seen | Unseen (cyclone_idai) | Drop |
| --- | --- | --- | --- |
| caution_and_advice | 0.713 | 0.690 | +0.023 |
| displaced_people_and_evacuations | 0.891 | 0.750 | +0.141 |
| infrastructure_and_utility_damage | 0.818 | 0.847 | -0.029 |
| injured_or_dead_people | 0.930 | 0.950 | -0.020 |
| missing_or_found_people | 0.783 | 0.667 | +0.116 |
| not_humanitarian | 0.621 | 0.438 | +0.183 |
| other_relevant_information | 0.545 | 0.573 | -0.028 |
| requests_or_urgent_needs | 0.607 | 0.509 | +0.098 |
| rescue_volunteering_or_donation_effort | 0.877 | 0.905 | -0.028 |
| sympathy_and_support | 0.837 | 0.854 | -0.017 |
| **Macro-F1** | 0.762 | 0.718 | +0.044 |

Note: positive Drop = performance fell on the unseen event; a few classes improve, which is expected noise at low support on a single event.

## Table 4 — Cross-event: seen vs unseen (DistilBERT seed 42, per-class F1)

| Class | Seen | Unseen (cyclone_idai) | Drop |
| --- | --- | --- | --- |
| caution_and_advice | 0.688 | 0.765 | -0.077 |
| displaced_people_and_evacuations | 0.898 | 0.609 | +0.289 |
| infrastructure_and_utility_damage | 0.816 | 0.832 | -0.016 |
| injured_or_dead_people | 0.929 | 0.943 | -0.014 |
| missing_or_found_people | 0.803 | 0.667 | +0.136 |
| not_humanitarian | 0.575 | 0.333 | +0.242 |
| other_relevant_information | 0.532 | 0.532 | +0.000 |
| requests_or_urgent_needs | 0.597 | 0.566 | +0.031 |
| rescue_volunteering_or_donation_effort | 0.873 | 0.894 | -0.021 |
| sympathy_and_support | 0.837 | 0.829 | +0.008 |
| **Macro-F1** | 0.755 | 0.697 | +0.058 |

## Calibration and selective prediction UNDER SHIFT (the key finding)

### RoBERTa (analysis model)
- Unseen-event ECE: 0.041 (T=1) -> 0.061 (frozen T=1.351). Temperature scaling fitted on seen data OVER-corrects on the unseen event; it was not overconfident there to begin with. Calibration does NOT transfer under shift.
- Selective prediction under shift: at the frozen tau=0.894, unseen auto-accept coverage 36.8% / risk 0.011 (review rate 63.2%). The frozen review threshold keeps the auto-accepted set's error under target by routing more cases to human review. This is the safety net that survives shift even though calibration transfer fails.

### DistilBERT (deployment model)
- Unseen-event ECE: 0.047 (T=1) -> 0.030 (frozen T=1.102). Unlike RoBERTa, DistilBERT's milder temperature DOES reduce ECE on the unseen event. Its lower T means less aggressive rescaling, so over-correction is avoided.
- Selective prediction under shift: at the frozen tau=0.887, unseen auto-accept coverage 58.4% / risk 0.053 (review rate 41.6%). Risk is just above the 5% target (0.053 vs 0.050), coverage is higher than RoBERTa's 36.8%. The threshold still provides meaningful human-review routing.

### Comparative summary (under shift)

| Metric | RoBERTa | DistilBERT |
| --- | --- | --- |
| Unseen macro-F1 | 0.718 | 0.697 |
| F1 drop (seen - unseen) | 0.044 | 0.058 |
| Unseen ECE (T=1) | 0.041 | 0.047 |
| Unseen ECE (frozen T) | 0.061 | 0.030 |
| Calibration transfer? | NO (ECE worsens) | YES (ECE improves) |
| Unseen coverage at frozen tau | 36.8% | 58.4% |
| Unseen risk at frozen tau | 0.011 | 0.053 |
| Review rate | 63.2% | 41.6% |

## Limitations to state explicitly
- Distribution-shift evidence is from ONE held-out event (cyclone_idai_2019); the ~0.04-0.06 macro-F1 drop is modest. Do not claim strong general robustness.
- Dataset is the 13-event events_set1_47K subset, not the full 19-event HumAID.
- kerala_floods_2018 (in the original plan) is not present in this subset and is not used.
