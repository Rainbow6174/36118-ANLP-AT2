# Work Plan After the EDA

This file explains what the EDA has produced, what each member owns and where each handoff belongs. Start with `README.md`, run `notebooks/01_data_eda.ipynb`, and then use the section for your role.

## Shared starting point

The EDA notebook completes the shared data work:

1. download any missing BESSTIE files to `data/raw/besstie/`;
2. check columns, varieties, sources and labels;
3. clean whitespace while keeping spelling, case, punctuation and emoji;
4. remove duplicate text and record each removal;
5. use the official validation files as the held-out project test set;
6. create a fixed validation split from official train with seed `36118`;
7. write shared and task-specific data to `data/processed/`;
8. write EDA tables and figures to `outputs/eda/`.

The prepared dataset contains 10,052 texts:

| Split | Rows |
| --- | ---: |
| Train | 7,514 |
| Validation | 1,327 |
| Test | 1,211 |

The quality checks remove 20 duplicate copies and two rows from one conflicting-label duplicate group. The generated validation report checks unique IDs, valid labels and clean split separation.

The `data/` folder is local. Every member creates the same files by running the EDA notebook. The approved EDA results in `outputs/eda/` are shared through Git.

## What the EDA tells us

### The project splits are stable

Positive sentiment stays close to 49.6% in train, validation and test. Sarcasm stays close to 14.2%. Use validation for model and threshold choices. Use test after the final settings are agreed.

Useful files:

- `outputs/eda/label_balance_by_split.csv`
- `outputs/eda/label_balance_by_split_variety_source.csv`

### Variety and source groups have different sizes

Every `variety × source` group appears in all three splits, but the sample sizes differ. Final results therefore need overall, per-variety and per-source views with support counts.

Useful files:

- `outputs/eda/variety_source_sample_counts.csv`
- `outputs/eda/figures/variety_source_sample_count_heatmaps.png`

### Text lengths differ

Median length ranges from about 15 words for `en-IN Reddit` to about 56 words for `en-UK Google`, with long tails in several groups. These results can guide token limits, TF-IDF feature limits and error analysis.

Useful files:

- `outputs/eda/text_length_distribution_summary.csv`
- `outputs/eda/figures/text_length_distributions.png`

### English variety is learnable

The initial character 3–5 gram classifier reaches about 0.712 validation macro-F1. This is a useful baseline for the variety work.

Useful files:

- `outputs/eda/char_ngram_variety_validation_report.csv`
- `outputs/eda/top_character_ngrams_by_variety_train_only.csv`
- `outputs/eda/figures/char_ngram_variety_validation_confusion.png`

### Source is a strong signal

A word/bigram classifier predicts Google versus Reddit with about 0.972 validation macro-F1. Variety and downstream models therefore need source-sliced results. The variety work also includes a cross-source check.

Useful files:

- `outputs/eda/source_diagnostic_validation_report.csv`
- `outputs/eda/source_associated_terms_train_only.csv`
- `outputs/eda/figures/source_diagnostic_validation_confusion.png`

### Sarcasm is concentrated on Reddit

The prepared data contains 1,432 sarcastic and 8,620 non-sarcastic texts.

| Source | Sarcastic | Total | Rate |
| --- | ---: | ---: | ---: |
| Google | 88 | 5,011 | 1.76% |
| Reddit | 1,344 | 5,041 | 26.66% |

Google has very little positive support in some segments:

| Segment | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| en-AU Google | 56 | 10 | 7 |
| en-IN Google | 10 | 2 | 2 |
| en-UK Google | 1 | 0 | 0 |

Useful files:

- `outputs/eda/sarcasm_distribution_by_source.csv`
- `outputs/eda/sarcasm_distribution_by_split_variety_source.csv`
- `outputs/eda/sarcasm_segment_support_recommendations.csv`
- `outputs/eda/figures/sarcasm_rate_by_variety_source.png`

## How the EDA shapes the project

The original six-person structure still fits the evidence. The EDA adds four decisions that connect the roles:

1. Every selected model reports results by English variety and source, with support counts.
2. Text-length results guide token limits, feature limits and error analysis.
3. The variety experiments include a source-transfer check.
4. Sarcasm uses one shared model and support-aware evaluation for sparse Google groups.

## Roles and boundaries

| Member | Main responsibility | Main evidence |
| --- | --- | --- |
| 1 | Data preparation, EDA and report assembly | Data quality, EDA findings and assembled report |
| 2 | Sentiment modelling | Baselines, Transformer, ablation and sentiment findings |
| 3 | Sarcasm modelling | Imbalance experiments, threshold analysis and sarcasm findings |
| 4 | English-variety modelling and one variety-aware experiment | Variety, source-transfer and routing findings |
| 5 | Shared evaluation | Agreed metrics, uncertainty, errors and final figures |
| 6 | Application, user study and poster | Working interface, user evidence and poster |

Members 2–4 own model training. Member 5 owns the shared evaluation protocol and final metric production. Member 6 owns application integration and user testing. Member 1 maintains the shared data interface and assembles the team-written report sections.

## Working evaluation agreement

Validation macro-F1 is the working primary metric for sentiment, sarcasm and variety classification. This gives every modelling role one comparable result to save from the beginning.

Member 5 will review the project needs and propose the final evaluation protocol. The team will agree on it before final model selection. That protocol will define:

- secondary metrics for each task;
- the objective used to choose the sarcasm threshold;
- confidence or calibration analysis;
- the uncertainty method for the main model comparisons;
- the exact final table and figure formats.

The current recommendations are:

- sentiment: macro-F1, accuracy and per-class precision, recall and F1;
- sarcasm: macro-F1, sarcastic-class precision, recall and F1, PR-AUC, balanced accuracy and a confusion matrix;
- variety: macro-F1, accuracy, per-class results and a confusion matrix;
- selected models: per-variety and per-source results with support counts;
- main comparisons: paired bootstrap 95% confidence intervals when practical.

For early sarcasm experiments, maximise validation macro-F1 when a threshold is required. Save validation probabilities so Member 5 can apply the agreed threshold rule later without retraining.

The held-out test set is used after the protocol, model settings and thresholds are fixed. Member 5 calculates the final metrics from saved test predictions.

## Member 1: data, EDA, coordination and report assembly

### Work

The main data and EDA work is complete in `notebooks/01_data_eda.ipynb`.

Member 1 will:

1. keep the notebook paths and task-file columns stable;
2. answer data-interface questions from Members 2–5;
3. update approved EDA outputs when the notebook changes;
4. write the data and EDA report section;
5. assemble the report sections supplied by all members.

### Why this follows from the EDA

The notebook has created a stable data interface, documented data quality and identified the main comparison groups. Keeping that interface stable lets the modelling and evaluation work proceed in parallel.

### Expected result

- a reproducible data and EDA notebook;
- stable shared task files and approved EDA outputs;
- a clear data and EDA report section;
- one assembled report using the sections supplied by the team.

### Handoff

```text
notebooks/01_data_eda.ipynb
outputs/eda/
report/sections/member1_data_and_eda.md
```

## Member 2: sentiment modelling

### Start here

```text
data/processed/by_task/sentiment/train.csv
data/processed/by_task/sentiment/validation.csv
data/processed/by_task/sentiment/test.csv
```

### Work

1. Calculate a majority-class reference result.
2. Train word and character TF-IDF baselines with Logistic Regression or SVM.
3. Fine-tune one suitable Transformer sentiment classifier.
4. Run one focused ablation on a feature, preprocessing choice or model setting.
5. Choose the final configuration from validation results.
6. Record validation macro-F1, per-class results, per-variety results and per-source results.
7. Save validation probabilities for every serious candidate.
8. Review representative errors across varieties, sources and text lengths.
9. Produce one final test prediction file after the configuration is fixed.

### Why this follows from the EDA

Sentiment is balanced overall, which supports direct model comparison. The source and text-length differences guide subgroup results and the error sample.

### Purpose

This work compares traditional and Transformer sentiment models and shows how reliably sentiment transfers across varieties and sources.

### Expected result

- reproducible majority, TF-IDF and Transformer results;
- one clear ablation result;
- a selected sentiment model;
- validation and test predictions with probabilities;
- overall, variety and source metric tables;
- sentiment methods, findings and limitations text.

### Handoff

```text
notebooks/02_sentiment_modelling.ipynb
models/sentiment/
models/sentiment/metadata.json
outputs/predictions/sentiment/validation.csv
outputs/predictions/sentiment/test.csv
outputs/results/sentiment/
report/sections/member2_sentiment.md
```

The model folder contains the selected model or its storage location, tokenizer or vectorizer, class order, configuration, seed and loading instructions.

## Member 3: sarcasm modelling

### Start here

```text
data/processed/by_task/sarcasm/train.csv
data/processed/by_task/sarcasm/validation.csv
data/processed/by_task/sarcasm/test.csv
outputs/eda/sarcasm_segment_support_recommendations.csv
```

### Work

1. Calculate a majority-class reference result.
2. Train an ordinary TF-IDF baseline.
3. Train a class-weighted TF-IDF baseline using training data only.
4. Fine-tune one suitable Transformer sarcasm classifier.
5. Compare class weighting with validation threshold selection. Training-only sampling or focal loss can be an extra experiment if time allows.
6. Save validation probabilities for every serious candidate.
7. Record validation macro-F1 and the agreed sarcasm metrics.
8. Report positive and total support beside per-variety and per-source results.
9. Analyse Google false positives and low-confidence sarcastic examples.
10. Produce one final test prediction file after the model and threshold are fixed.
11. Provide a small support configuration for the application's limited-evidence message.

### Sparse Google rule

Use one shared sarcasm model across all varieties and sources. `en-UK Google` test has no sarcastic examples, so its positive-class recall, F1 and PR-AUC are `N/A`. Report false positives, false-positive rate, specificity and predicted-positive rate for that segment.

### Why this follows from the EDA

Google contains 88 sarcastic examples, while Reddit contains 1,344. `en-IN Google` has little positive support, and `en-UK Google` has one positive training example and none in validation or test. A shared model uses all available training evidence, while support-aware results make the source difference clear.

### Purpose

This work tests how well the system finds the rare sarcastic class and turns sparse-segment evidence into useful evaluation and application guidance.

### Expected result

- ordinary and class-weighted traditional baselines;
- one Transformer result;
- a comparison of imbalance responses;
- a selected shared sarcasm model and validation threshold;
- validation and test predictions with probabilities;
- source-aware and support-aware metrics;
- a focused error analysis;
- sarcasm methods, findings and limitations text.

### Handoff

```text
notebooks/03_sarcasm_modelling.ipynb
models/sarcasm/
models/sarcasm/metadata.json
models/sarcasm/support_config.json
outputs/predictions/sarcasm/validation.csv
outputs/predictions/sarcasm/test.csv
outputs/results/sarcasm/
report/sections/member3_sarcasm.md
```

The metadata records the class order, final threshold, configuration, seed and loading instructions.

## Member 4: English variety and the variety-aware contribution

Member 4 keeps the branch's original research idea: build an English-variety classifier, test source transfer and use variety information in one controlled downstream experiment. The implementation below makes that experiment independent and practical.

### Start here

```text
data/processed/by_task/variety/train.csv
data/processed/by_task/variety/validation.csv
data/processed/by_task/variety/test.csv
data/processed/by_task/sentiment/train.csv
data/processed/by_task/sentiment/validation.csv
data/processed/by_task/sentiment/test.csv
outputs/eda/top_character_ngrams_by_variety_train_only.csv
outputs/eda/source_diagnostic_validation_report.csv
```

### Part A: English-variety classification

1. Reproduce the character n-gram baseline from the EDA.
2. Add a word-feature baseline.
3. Train one stronger variety classifier and save `en-AU`, `en-IN` and `en-UK` probabilities.
4. Report macro-F1, accuracy, per-class results and the confusion matrix.
5. Report results separately for Google and Reddit.
6. Run a source-transfer check: train on one source's training rows and evaluate on the other source's validation rows, in both directions.
7. Choose a low-confidence point on validation for later routing.

### Part B: controlled variety-aware sentiment experiment

The core question is:

> Can predicted English variety improve a sentiment baseline compared with the same global baseline?

Sentiment is used for this experiment because its labels are balanced across the project splits. Member 4 uses one lightweight TF-IDF and Logistic Regression recipe throughout, so the variety information is the main experimental change.

Train:

- one global sentiment model using all training rows;
- one en-AU sentiment model;
- one en-IN sentiment model;
- one en-UK sentiment model.

Compare four conditions on validation:

1. **Global control:** always use the global sentiment model.
2. **Oracle variety:** route with the gold variety label. This measures the upper bound of the routing idea.
3. **Predicted variety:** route with the variety classifier from Part A.
4. **Confidence gate:** use the predicted-variety model when variety confidence is high enough and use the global model otherwise.

Use the same text features, classifier family and training rules in all four conditions. Choose the confidence gate on validation. Run the final comparison on test after the design is fixed.

If routing does not improve validation performance, keep the result as evidence and give the application the global fallback. The experiment still answers the research question.

### Part C: cross-variety view

Use the same lightweight sentiment recipe for a small leave-one-variety-out check:

- train on en-IN and en-UK, then evaluate en-AU;
- train on en-AU and en-UK, then evaluate en-IN;
- train on en-AU and en-IN, then evaluate en-UK.

For each run, train on the training rows from two varieties and evaluate first on the validation rows from the held-out variety. After the design is fixed, produce the corresponding final test table. This measures downstream cross-variety transfer and is separate from the three-class variety-classification score.

### Work boundary

Member 4 owns these lightweight controlled models and can start without waiting for Members 2 or 3. Members 2 and 3 retain their Transformer searches, and their final results can be added later as reference points in the shared evaluation table.

### Why this follows from the EDA

The character baseline shows that English variety is learnable. The stronger source classifier shows a possible platform shortcut, so source-sliced and source-transfer evidence belongs beside the main variety score. Balanced sentiment labels make the downstream comparison practical and controlled.

### Purpose

This work provides the project's English-variety model and directly tests whether variety information adds value to a downstream NLP task.

### Expected result

- word and character variety baselines;
- one selected variety classifier with probabilities;
- per-variety, per-source and source-transfer results;
- a leave-one-variety-out sentiment result;
- a global, oracle, predicted and confidence-gated routing comparison;
- a routing configuration for application integration;
- variety and routing methods, findings and limitations text.

### Handoff

```text
notebooks/04_variety_modelling.ipynb
models/variety/
models/variety/metadata.json
models/variety/routing_config.json
outputs/predictions/variety/validation.csv
outputs/predictions/variety/test.csv
outputs/predictions/routing/validation.csv
outputs/predictions/routing/test.csv
outputs/results/variety/
outputs/results/routing/
report/sections/member4_variety_and_routing.md
```

## Member 5: shared evaluation, error analysis and figures

### Start here

Use the gold files under `data/processed/by_task/` and predictions from `outputs/predictions/`.

### Work

1. Propose the final evaluation protocol and discuss it with the team before final model selection.
2. Build one evaluator that joins gold labels and predictions by `id`.
3. Use the same label order and metric definitions across comparable models.
4. Produce overall, per-class, per-variety and per-source tables.
5. Include positive and total support in detailed sarcasm results.
6. Select a practical confidence or calibration analysis for the final models.
7. Select an uncertainty method for the main comparisons; paired bootstrap is the recommended starting point.
8. Compare errors across task, variety, source and text length.
9. Organise about 40–60 representative errors across the three modelling streams.
10. Publish one locked set of tables and figures for the report, application and poster.

### Why this follows from the EDA

The sample-size, source, text-length and sarcasm-support tables define the main evaluation slices. They also provide the support counts needed to interpret detailed results.

### Purpose

This work gives the team one source of final numbers and prevents small differences in metric code from changing the conclusions.

### Expected result

- an agreed evaluation protocol and reusable evaluator;
- one main model-comparison table;
- per-variety and per-source results with support;
- confidence or calibration evidence;
- uncertainty estimates for the main comparisons;
- a structured error-analysis file;
- locked tables and figures for the final deliverables;
- evaluation, findings and discussion text.

### Handoff

```text
notebooks/05_model_evaluation.ipynb
outputs/results/evaluation_protocol.md
outputs/results/final/
outputs/error_analysis/final_error_sample.csv
outputs/figures/final/
report/sections/member5_evaluation_and_results.md
```

Machine-readable CSV or JSON results accompany report-ready tables and figures.

## Member 6: application, user study and poster

### Start here

Members 2–4 provide selected models and metadata. Member 5 provides final tables and figures. Member 6 can build the interface early with a mock inference response.

### Work

1. Support single-text input and CSV batch upload.
2. Ask for the known source with a Google/Reddit selector. Batch input includes `text` and `source`; `variety` is optional.
3. Show variety, sentiment and sarcasm predictions with confidence.
4. Use the routing configuration only when Member 4's validation evidence supports it; otherwise use the global fallback.
5. Show the limited-evidence message from Member 3 for sparse sarcasm segments.
6. Provide filtering, text-level review, correction and export.
7. Add a review queue for low confidence, model disagreement and sparse evidence.
8. Integrate the selected models through one inference wrapper.
9. Provide local and deployed demonstration instructions.
10. Run a usability study with about 6–12 users whose backgrounds collectively cover the three English varieties.
11. Use common tasks covering clear sentiment, sarcasm, ambiguous text, batch review, filtering and export.
12. Record task completion, difficulty, assistance, output clarity and open feedback.
13. Make one visible interface revision based on the study.
14. Assemble the poster from team text, final figures and application screenshots.

### Why this follows from the EDA

The source and sarcasm-support findings become clear confidence and evidence messages in the interface. The variety classifier supports comparison and routing. The user study checks whether people understand these outputs during a realistic review task.

### Purpose

This work turns the modelling results into a realistic review workflow and provides evidence that users can understand and act on the outputs.

### Expected result

- a working single-text and batch interface;
- stable inference integration;
- confidence, evidence and review features;
- filters, corrections and export;
- deployment and local-run instructions;
- an anonymous user-study summary;
- one documented interface revision;
- an editable final poster.

### Handoff

```text
app/
app/app_models.json
report/user_study/
report/sections/member6_application_and_user_study.md
poster/
```

User-study files contain anonymous results and a short description of the interface change.

## Shared handoff formats

### Binary prediction files

Sentiment and sarcasm prediction files use:

```text
id,pred_label,prob_0,prob_1,model_name,model_version
```

### Variety prediction files

Variety prediction files use:

```text
id,pred_label,prob_en_AU,prob_en_IN,prob_en_UK,model_name,model_version
```

Each prediction file has one row per input ID. Probabilities are numeric values from 0 to 1. The model metadata records the class order and the code used to create the file.

### Inference response

The application consumes one response structure:

```json
{
  "variety": {"label": "en-AU", "confidence": 0.72},
  "sentiment": {"label": 1, "confidence": 0.83},
  "sarcasm": {"label": 0, "confidence": 0.61},
  "source": "google",
  "warnings": ["Limited segment evidence"],
  "needs_review": true
}
```

## What goes into Git

Share:

- notebooks and reusable code;
- approved EDA outputs;
- selected model artefacts or model-location metadata;
- validation and final test predictions;
- agreed results, reviewed errors and final figures;
- thresholds, class order and routing metadata;
- report sections, anonymous user-study results and poster files.

Keep local:

- `data/raw/` and `data/processed/`;
- virtual environments and package caches;
- temporary checkpoints and rejected experimental artefacts;
- exploratory logs and draft figures.

## Work sequence

1. Every member runs `notebooks/01_data_eda.ipynb` to create the local task files.
2. Members 2–4 begin their modelling work in parallel.
3. Member 5 drafts the evaluation protocol and builds the evaluator with mock predictions.
4. Member 6 builds the application with the shared mock response.
5. The team agrees on the evaluation protocol.
6. Members 2–4 upload selected models, metadata and validation predictions.
7. Final model settings and thresholds are fixed from validation evidence.
8. Members 2–4 create one final test prediction file for each selected model.
9. Member 5 publishes the locked result package and figures.
10. Member 6 integrates the selected models, runs the user study and records the interface revision.
11. Every member supplies their report and poster content. Member 1 assembles the report, and Member 6 assembles the poster.
