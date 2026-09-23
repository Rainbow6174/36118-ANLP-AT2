# DistilBERT Under-Shift Results (Deployment Model)

Checkpoint: B_distilbert-base-uncased_plain_s42 (trained without cyclone_idai_2019)
DistilBERT's own T=1.1017, tau=0.8866

## Seen vs Unseen F1

| Class | Seen F1 | Unseen F1 | Drop |
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
| **Macro-F1** | **0.755** | **0.697** | **+0.058** |

## Calibration Under Shift

| Split | ECE (T=1) | ECE (T=1.1017) |
| --- | --- | --- |
| Seen test | 0.0461 | 0.0257 |
| Unseen held-out | 0.0473 | 0.0296 |

## Selective Prediction Under Shift

| Metric | Seen test | Unseen held |
| --- | --- | --- |
| Coverage | 47.3% | 58.4% |
| Risk (error rate) | 0.0511 | 0.0527 |
| Review rate | 52.7% | 41.6% |
