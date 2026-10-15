# Data and exploratory analysis

## Purpose

This section defines the data used by CrisisLens and records the main findings from the exploratory data analysis (EDA). The aim is to give the modelling, retrieval, backend and interface work one clear starting point.

## Data sources

The main task uses the text-only [HumAID-all dataset](https://huggingface.co/datasets/QCRI/HumAID-all). It contains short messages written during disasters and assigns each message one humanitarian information label. The EDA notebook also downloads the event-wise HumAID release so that later experiments can test an unseen disaster event.

CrisisMMD is kept as a separate supporting benchmark. Its label files contain image-text rows and support informative, humanitarian and damage-severity tasks. The current MVP does not download or use the large image archive. CrisisMMD labels are not merged with the HumAID labels because the two datasets answer different questions and use different label definitions.

All downloads and preparation steps are in `notebooks/01_crisis_eda.ipynb`. Raw downloads are written to the local `data/raw/` folder. The approved tables and figures are written to `outputs/eda/`.

## HumAID data contract

The downloaded HumAID files contain 76,484 rows from 19 disaster events. The official split is:

| Split | Rows | Share |
| --- | ---: | ---: |
| Train | 53,531 | 69.99% |
| Validation | 7,793 | 10.19% |
| Test | 15,160 | 19.82% |

The ten labels found in the downloaded files are:

`caution_and_advice`, `displaced_people_and_evacuations`, `infrastructure_and_utility_damage`, `injured_or_dead_people`, `missing_or_found_people`, `not_humanitarian`, `other_relevant_information`, `requests_or_urgent_needs`, `rescue_volunteering_or_donation_effort`, and `sympathy_and_support`.

The dataset card mentions an older eleven-label list, but the downloaded files do not contain a separate `dont_know_cant_judge` class. The project therefore uses the ten labels above. They should be treated as the shared label contract for the app and all model comparisons.

Each prepared record keeps the message text, its label, the official split and the event information when it is available. Historical HumAID results use `source_type=humaid_history` in the read-only retrieval index. New messages saved by the application use `source_type=user`.

## Main EDA findings

### Class balance

The official split keeps almost the same class proportions across train, validation and test. The largest class is `rescue_volunteering_or_donation_effort` (about 27.8% of each split). `other_relevant_information` is the next large class (about 15.9%). `missing_or_found_people` is the smallest class (about 0.5%). This makes accuracy alone misleading. Model work should report macro-F1, per-label recall and per-label support, with special attention to the smallest classes.

The full counts are in `outputs/eda/humaid_label_distribution.csv`. The split-level check is in `outputs/eda/humaid_split_summary.csv`.

### Events and disaster types

The 19 events cover five event types: earthquake, flood, hurricane, wildfire and other. The event sizes are uneven. Several hurricane events provide much more training data than the smaller earthquake, flood and wildfire events. A random split can therefore look strong while still relying on event-specific wording or hashtags.

For this reason, the project has two evaluation views:

1. the official HumAID train/validation/test split for the main model comparison;
2. a focused unseen-event stress test on the 13-event `events_set1_47K`
   subset, where `cyclone_idai_2019` is removed from training and validation,
   the model trains on the other 12 events, and evaluation uses the held-out
   event's 779 test messages.

The full 19-event download is still used for the EDA and retrieval index. The
event sizes and label support are listed in
`outputs/eda/humaid_event_holdout_plan.csv`. Small held-out events can have
labels with very low support or no test examples. These cases should be
reported clearly rather than hidden in an overall score. Because the final
stress test uses one held-out event, it is evidence about that distribution
shift rather than a claim of general cross-disaster robustness.

### Text shape and social-media markers

Messages are short, but length changes with the disaster type and label. The EDA records median, mean, 90th-percentile word count and median character count for each split/event/label group. It also records URL, mention, hashtag and retweet rates. These fields show why the models should preserve useful social-media signals during the baseline stage instead of removing every symbol.

The detailed table is `outputs/eda/humaid_text_statistics.csv`. The length and split figure is `outputs/eda/figures/humaid_text_length_and_split_proportions.png`.

### Duplicates and leakage

The check found 12 exact duplicate rows and 12 duplicates after simple text normalisation. Four normalised duplicate groups cross an official split boundary. This is a small amount of leakage, but it can make a short-text classifier look better than it is. All model runs should use the same text normalisation and mention this limitation when interpreting scores. The duplicate summary is in `outputs/eda/humaid_duplicate_summary.csv`.

### Early word and character signals

The notebook produces label-level word features and character n-grams in `outputs/eda/humaid_label_top_word_features.csv` and `outputs/eda/humaid_label_top_char_ngrams.csv`. These are an initial diagnostic, not a claim that a word alone defines a class. They can guide the TF-IDF baseline, help explain model errors and show whether character features are useful for hashtags, spelling variation and short social-media text.

## Consequences for the rest of the project

- Member 2 should build a transparent majority and TF-IDF word/character baseline on the ten-label HumAID contract. The baseline should provide per-label scores and an error table.
- Member 3 should compare a compact Transformer with the baseline and test class weighting, sampling or threshold calibration for the rare labels. The event-held-out plan should be reused.
- Member 4 should use the same labels and fields in the API, database schema and shared evaluation harness. A prediction is a sorting suggestion, not a verified emergency fact.
- Member 5 should build retrieval over historical HumAID messages and preserve the event, label and source fields as filters.
- Member 6 should use the ten labels as the board categories, show the predicted label and confidence, and test whether users understand that the prediction can be wrong.

The main user-facing flow is: a user submits a message, the classifier returns a label and confidence, and the user can correct the label before saving. The app then opens the selected board and shows similar reports already saved for the current event. Historical messages remain available through a separate search mode. Low-confidence predictions stay visible for review.

## Reproducibility and handoff

The complete preparation is inside `notebooks/01_crisis_eda.ipynb`; no prepared local dataset is required before running it. Other members should read the README first, run the notebook when they need to rebuild local data, and use the approved files in `outputs/eda/` for shared numbers.

The Member 1 handoff is:

```text
notebooks/01_crisis_eda.ipynb
outputs/eda/
report/sections/member1_data_and_eda.md
```

Raw downloads, generated local datasets and personal experiment files stay local. Reusable code, approved EDA tables and figures, model metadata, validation results, reviewed errors and final report material should be shared when another member would otherwise have to recreate them.
