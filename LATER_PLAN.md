# Work Plan After the EDA

## What the EDA has completed

Running every cell in `eda.ipynb` completes the shared data work:

1. Find the six BESSTIE source files and download any missing file.
2. Check columns, English-variety values, source values and labels.
3. Clean whitespace while preserving spelling, case, punctuation, emoji, hashtags and regional wording.
4. Remove exact and case-only duplicate text and record each removal.
5. Use the official validation data as the held-out project test set.
6. Create a fixed project validation split from official train with seed `36118`.
7. Write shared and task-specific data under `outputs/processed/`.
8. Write EDA tables and figures under `outputs/eda/`.

The prepared dataset contains 10,052 texts:

| Split | Rows |
| --- | ---: |
| Train | 7,514 |
| Validation | 1,327 |
| Test | 1,211 |

Quality control removes 20 duplicate copies and two rows from a conflicting-label duplicate group. The generated validation report confirms unique IDs, valid labels and clean split separation.

## What the EDA has found

### Stable project splits

Positive sentiment stays close to 49.6% in train, validation and test. Sarcasm stays close to 14.2%. The modelling roles can use validation for model choices and reserve test for the final run.

Relevant outputs:

- `outputs/eda/label_balance_by_split.csv`
- `outputs/eda/label_balance_by_split_variety_source.csv`

### Unequal variety and source groups

Every `variety × source` group appears in all three splits. Their sample sizes differ, so the final results need overall, per-variety and per-source views with sample counts.

Relevant outputs:

- `outputs/eda/variety_source_sample_counts.csv`
- `outputs/eda/figures/variety_source_sample_count_heatmaps.png`

### Different text-length distributions

Median length ranges from about 15 words for `en-IN Reddit` to about 56 words for `en-UK Google`, with long tails in several groups. These results support the token-length and feature-limit choices in later models.

Relevant outputs:

- `outputs/eda/text_length_distribution_summary.csv`
- `outputs/eda/figures/text_length_distributions.png`

### Learnable English-variety patterns

The initial character 3–5 gram classifier reaches about 0.710 validation macro-F1. Character patterns may provide a useful baseline for the variety work.

Relevant outputs:

- `outputs/eda/char_ngram_variety_validation_report.csv`
- `outputs/eda/top_character_ngrams_by_variety_train_only.csv`
- `outputs/eda/figures/char_ngram_variety_validation_confusion.png`

### Strong source signal

A word/bigram classifier predicts Google versus Reddit with about 0.972 validation macro-F1. 

Source-sliced results and cross-source experiments will show how well the final models transfer across platform style and topic.

Relevant outputs:

- `outputs/eda/source_diagnostic_validation_report.csv`
- `outputs/eda/source_associated_terms_train_only.csv`
- `outputs/eda/figures/source_diagnostic_validation_confusion.png`

### Sarcasm concentrated on Reddit

The prepared data contains 1,432 sarcastic and 8,620 non-sarcastic texts.

| Source | Sarcastic | Total | Rate |
| --- | ---: | ---: | ---: |
| Google | 88 | 5,011 | 1.76% |
| Reddit | 1,344 | 5,041 | 26.66% |

The Google segments have the following positive support:

| Segment | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| en-AU Google | 56 | 10 | 7 |
| en-IN Google | 10 | 2 | 2 |
| en-UK Google | 1 | 0 | 0 |

Relevant outputs:

- `outputs/eda/sarcasm_distribution_by_source.csv`
- `outputs/eda/sarcasm_distribution_by_split_variety_source.csv`
- `outputs/eda/sarcasm_segment_support_recommendations.csv`
- `outputs/eda/figures/sarcasm_rate_by_variety_source.png`

## How the findings shape the project

The original project structure remains suitable:

- Member 1 provides stable data, EDA, shared file formats and final report assembly.
- Member 2 develops the complete sentiment stream.
- Member 3 develops the complete sarcasm stream.
- Member 4 develops the English-variety and variety-aware research contribution.
- Member 5 evaluates all modelling streams with one common method.
- Member 6 builds the application, completes user testing and assembles the poster.

The EDA adds four useful decisions to this structure:

1. Every model reports performance by English variety and source.
2. Text-length analysis supports token and feature limits.
3. Variety experiments include a source-transfer check.
4. Sarcasm modelling uses one shared model and support-aware evaluation for sparse Google groups.

## Workload and handoff balance

Each role owns one main build and one report section:

| Member | Main build | Main evidence |
| --- | --- | --- |
| 1 | Data preparation and EDA | Data quality, EDA and final report assembly |
| 2 | Sentiment models | Baselines, Transformer, ablation and sentiment findings |
| 3 | Sarcasm models | Imbalance experiments, threshold and sarcasm findings |
| 4 | Variety model and variety-aware experiment | Cross-variety, source-transfer and routing findings |
| 5 | Common evaluator | Locked metrics, uncertainty, errors and figures |
| 6 | Web application | User study, interface revision, deployment and poster |

Model training stays with Member 2–4. Metric production and final figures stay with Member 5. Application integration and usability evidence stay with Member 6. Member 1 maintains the data interface and assembles the team-authored report sections.

## Member 1 Data EDA coordination and report assembly

The early work is complete in `eda.ipynb`. The remaining work keeps the shared foundation clear through the rest of the project.

## Member 2 Sentiment modelling

### Starting data

```text
outputs/processed/by_task/sentiment/train.csv
outputs/processed/by_task/sentiment/validation.csv
outputs/processed/by_task/sentiment/test.csv
```

### Main work

1. Calculate a majority-class reference result.
2. Train word and character TF-IDF baselines with Logistic Regression or SVM.
3. Fine-tune one suitable Transformer sentiment classifier.
4. Run one focused ablation covering a feature, preprocessing choice or model setting.
5. Choose the final configuration from validation results.
6. Record macro-F1, per-class results, per-variety results and per-source results.
7. Review representative errors across varieties, sources and text lengths.
8. Export validation and final test predictions through the shared prediction format.

### EDA connection

Sentiment is balanced overall, which supports direct model comparison. The source and text-length differences guide subgroup results and the error sample.

### Purpose

This work compares traditional and Transformer sentiment modelling and shows how reliably sentiment transfers across varieties and sources.

### Expected result

- reproducible majority, TF-IDF and Transformer results;
- one clear ablation result;
- a selected sentiment model;
- validation and test predictions with probabilities;
- overall, variety and source metric tables;
- sentiment methods, findings and limitations text.

### Upload(Save and Upload your notebook(code) and final trained model)

```text
src/models/sentiment/
artifacts/sentiment/
predictions/sentiment/validation.csv
predictions/sentiment/test.csv
results/sentiment/
reports/sections/sentiment.md
```

The selected artefact includes its tokenizer or vectorizer, class order, configuration, seed and loading instructions.

## Member 3 Sarcasm modelling

### Starting data

```text
outputs/processed/by_task/sarcasm/train.csv
outputs/processed/by_task/sarcasm/validation.csv
outputs/processed/by_task/sarcasm/test.csv
outputs/eda/sarcasm_segment_support_recommendations.csv
```

### Main work

1. Calculate a majority-class reference result.
2. Train an ordinary TF-IDF sarcasm baseline.
3. Train a class-weighted TF-IDF baseline using weights from train.
4. Fine-tune one suitable Transformer sarcasm classifier.
5. Compare two imbalance responses, using class weighting and validation threshold selection as the core comparison. Training-only sampling or focal loss can provide an additional experiment when time allows.
6. Select the operating threshold from validation probabilities.
7. Record macro-F1, sarcastic precision, recall and F1, PR-AUC, balanced accuracy and confusion matrices.
8. Add per-variety and per-source results with positive and total support.
9. Analyse Google false positives and low-confidence sarcastic cases.
10. Export validation and final test predictions through the shared prediction format.
11. Supply a small support configuration for the application's `Limited segment evidence` message.

### EDA connection

Google contains 88 sarcastic examples, while Reddit contains 1,344. The shared model learns from the full training set. The per-source results show how its behaviour changes between Google and Reddit.

`en-UK Google` test contains zero sarcastic examples. Its positive-class recall, F1 and PR-AUC fields use `N/A`. False positives, false-positive rate, specificity and predicted-positive rate describe this segment.

### Purpose

This work measures the ability to find the rare sarcastic class and turns the Google support limitation into useful evaluation and application information.

### Expected result

- ordinary and class-weighted traditional baselines;
- one Transformer result;
- a comparison of imbalance responses;
- a selected shared sarcasm model and validation threshold;
- validation and test predictions with probabilities;
- source-aware and support-aware metrics;
- a focused error analysis;
- sarcasm methods, findings and limitations text.

### Upload(Save and Upload your notebook(code) and final trained model)

```text
src/models/sarcasm/
artifacts/sarcasm/
predictions/sarcasm/validation.csv
predictions/sarcasm/test.csv
results/sarcasm/
config/sarcasm_support.json
reports/sections/sarcasm.md
```

The selected artefact includes its tokenizer or vectorizer, class order, threshold, configuration, seed and loading instructions.

## Member 4 Variety aware innovation and cross variety analysis

### Starting data

```text
outputs/processed/by_task/variety/train.csv
outputs/processed/by_task/variety/validation.csv
outputs/processed/by_task/variety/test.csv
outputs/eda/top_character_ngrams_by_variety_train_only.csv
outputs/eda/source_diagnostic_validation_report.csv
```

Member 2 and Member 3 provide standard prediction files and inference artefacts for the variety-aware comparison.

### Main work

1. Reproduce the character n-gram variety baseline from the EDA.
2. Add a word-feature variety baseline.
3. Train one stronger English-variety classifier and save class probabilities.
4. Assess confidence on validation and define a low-confidence routing point.
5. Record per-variety and per-source performance.
6. Run one source-transfer experiment to measure the effect identified by the EDA.
7. Produce a cross-variety generalisation view.
8. Compare the original variety-agnostic control with three variety-aware conditions:
   - known variety as the oracle condition;
   - predicted variety from the classifier;
   - confidence-gated routing with a global fallback.
9. Keep the comparison controlled so the intended variety information is the main experimental change.
10. Export variety probabilities and the selected routing configuration.

### EDA connection

The character baseline shows learnable variety signal. The stronger source result shows why source-transfer evidence belongs beside the main variety score.

### Purpose

This work provides the project's distinctive variety component and measures whether variety information improves sentiment or sarcasm in realistic inference.

### Workload boundary

Member 4 trains the variety model and runs one shared routing experiment. Member 2 and Member 3 supply their trained models or standard predictions. Member 4 uses those handoffs without repeating their training experiments.

### Expected result

- word and character variety baselines;
- one selected variety classifier with probabilities;
- per-variety, per-source and source-transfer results;
- a cross-variety generalisation view;
- a variety-agnostic versus oracle, predicted and gated comparison;
- a routing rule for application integration;
- variety and innovation findings text.

### Upload(Save and Upload your notebook(code) and final trained model)

```text
src/models/variety/
src/models/routing/
artifacts/variety/
predictions/variety/validation.csv
predictions/variety/test.csv
results/variety/
results/routing/
config/routing.json
reports/sections/variety_and_routing.md
```

## Member 5 Evaluation error analysis and figures

### Starting material

Use the gold task files under `outputs/processed/` and the standard prediction files from Member 2–4.

### Main work

1. Build one evaluator that joins gold labels and predictions by `id`.
2. Apply the same metric definitions and label order across comparable models.
3. Produce overall, per-class, per-variety and per-source tables.
4. Add support beside each detailed sarcasm result.
5. Measure confidence or calibration for the selected models.
6. Estimate uncertainty for the main comparisons with repeated runs or paired bootstrap resampling.
7. Compare errors across text-length and source groups.
8. Organise approximately 40–60 representative errors across the three modelling streams.
9. Produce one locked results package for the report, application and poster.
10. Create the final result figures with consistent labels and colours.

### EDA connection

The sample-size, source, text-length and sarcasm-support tables define the main evaluation slices. They also provide the support counts used beside detailed results.

### Purpose

This work gives the team one consistent source of final numbers and connects model performance with clear findings and limitations.

### Expected result

- a reusable evaluator;
- one main model-comparison table;
- per-variety and per-source results;
- calibration or confidence evidence;
- uncertainty estimates for the main comparisons;
- a structured error-analysis file;
- locked tables and figures for every final deliverable;
- evaluation, findings, discussion and recommendations text.

### Upload(Save and Upload your notebook(code) and necessary file with clear explaination document)

```text
evaluation/
results/final/
figures/final/
reports/sections/evaluation_and_results.md
```

Machine-readable CSV or JSON results accompany the report-ready tables and figures.

## Member 6 Web application deployment user study and poster

### Starting material

Member 2–4 provide selected inference artefacts and metadata. Member 5 provides locked result tables and figures. The EDA supplies segment support and text-length evidence.

### Main work

1. Build the application early with a mock inference response.
2. Support single-text input and CSV batch upload.
3. Include known market or variety context in the input workflow.
4. Show variety, sentiment and sarcasm predictions with confidence.
5. Show the global and variety-aware comparison where it helps the analyst understand a result.
6. Use the routing configuration from Member 4 and support configuration from Member 3.
7. Provide filtering, text-level review, correction and export.
8. Add a review queue for low-confidence, model-disagreement and sparse-segment cases.
9. Integrate the final model artefacts through one inference wrapper.
10. Provide deployed and local demonstration instructions.
11. Run a usability study with approximately 6–12 users familiar with the three English varieties.
12. Use common tasks covering clear sentiment, sarcasm, ambiguous text, batch review, filtering and export.
13. Record task completion, difficulty, assistance, clarity ratings and open feedback.
14. Implement one visible interface revision from the observations.
15. Assemble the poster from team-supplied text, Member 5's figures and final application screenshots.

### EDA connection

The source and sarcasm-support findings become plain-language confidence and evidence messages in the interface. The variety classifier supports comparison and routing. The user study checks whether people understand these outputs during a realistic review task.

### Purpose

This work turns the research results into a usable analyst workflow and supplies the user-interaction evidence for the project.

### Workload boundary

Member 6 builds and tests the application. Member 2–4 supply loadable models and metadata. Member 5 supplies final numbers and figures. Every member supplies finished poster text for their own work.

### Expected result

- a working single-text and batch interface;
- stable inference integration;
- confidence, comparison and review features;
- filters, corrections and export;
- deployment and local-run instructions;
- an anonymous user-study summary;
- one documented interface revision;
- an editable final poster.

### Upload

```text
app/
src/inference/
config/app_models.json
reports/user_study/
poster/
```

## Shared handoff formats

### Prediction files

Binary prediction files use:

```text
id,pred_label,prob_0,prob_1,model_name,model_version
```

The variety prediction files add one probability column per variety and record the class order in metadata.

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

### GitHub updates

The `data/` and `outputs/` folders stay local because `eda.ipynb` recreates them. Later work adds the files that save other members time:

- training, evaluation, inference and application code;
- final configurations and seeds;
- selected fitted model artefacts;
- validation and final test predictions;
- metric tables and final figures;
- thresholds, class order and loading metadata;
- report sections, user-study findings and poster files.

Large selected artefacts can use Git LFS or the team's shared model storage(DONT UPLOAD original data/unnecessary data). A small metadata file in Git records the artefact name, version, location and loading command.

## Parallel work sequence

1. Member 1 publishes the EDA handoff and stable task files.
2. Member 2–4 build their modelling streams in parallel.
3. Member 5 builds the evaluator against small mock prediction files.
4. Member 6 builds the application against a mock inference response.
5. Member 2–4 upload selected artefacts, metadata and validation predictions.
6. Final model settings are agreed from validation evidence.
7. Member 2–4 produce one final test prediction file for each selected model.
8. Member 5 publishes the results package.
9. Member 6 integrates final artefacts, runs the user study and records the interface revision.
10. Each member supplies their report and poster content; Member 1 assembles the report and Member 6 assembles the poster.
