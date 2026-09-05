# From EDA to the Final System

This guide explains what the EDA found and what each project role should deliver next. Run all cells in `eda.ipynb` first. The roles are separate on purpose, so people can work in parallel without editing the same files.

## The short version

The data is large enough for a solid English-variety classifier and useful sentiment and sarcasm experiments. The main difficulty is not the total number of rows. It is the link between source and label:

- Google and Reddit are easy to tell apart from the text.
- Sarcasm is much more common on Reddit.
- Google has only 88 sarcastic examples in total.
- `en-UK Google` has one sarcastic example in train and none in validation or test.
- Text length and sample size also differ across variety and source groups.

A strong project should therefore do more than report one accuracy score. It should compare simple and stronger models, show results by variety and source, explain where the evidence is weak, and turn those limits into useful behaviour in the application.

## What the notebook creates

After `eda.ipynb` finishes, the shared files are under `outputs/processed/` and the EDA evidence is under `outputs/eda/`.

| Need | File or folder |
| --- | --- |
| Full dataset with both labels | `outputs/processed/dataset_v1.csv` |
| Fixed train, validation and test splits | `outputs/processed/train.csv`, `validation.csv`, `test.csv` |
| Sentiment-ready files | `outputs/processed/by_task/sentiment/` |
| Sarcasm-ready files | `outputs/processed/by_task/sarcasm/` |
| Variety-ready files | `outputs/processed/by_task/variety/` |
| Removed-row record | `outputs/processed/audit/removed_rows.csv` |
| Data quality checks | `outputs/processed/validation_report.json` |
| EDA support tables and figures | `outputs/eda/` |

Each task file has the same five columns:

```text
id,text,variety,source,label
```

These files are ready for modelling. A model may add its own tokenizer or feature extraction, but it should not rewrite the shared files. Predictions should keep `id`, because evaluation will use it to join predictions back to the correct examples.

The test split is only for the final run. Use train for fitting and validation for model choices, thresholds and early stopping.

## What the EDA tells us to build

### A useful product

The clearest user is a communications or customer-insights analyst who needs to review English feedback from different markets and platforms. The system should help that person sort and check text; it should not claim to identify a writer's nationality.

A practical flow is:

```text
Paste one text or upload a CSV
        |
        v
Check the input and optional source
        |
        v
Predict English variety with confidence
        |
        +---- low confidence ----> use the global route and ask for review
        |
        v
Predict sentiment and sarcasm
        |
        v
Show probabilities, group support, warnings and a review queue
        |
        v
Let the user correct, filter and export results
```

The useful contribution is not just three predictions. It is the combination of:

- one place to review variety, sentiment and sarcasm;
- visible confidence and model disagreement;
- source-aware results, because Google and Reddit behave differently;
- a clear warning when a subgroup has too little evidence;
- a review queue for uncertain or high-risk cases;
- an export that preserves both model output and human corrections.

### Model comparisons that are worth showing

For each task, start with a simple baseline. This makes the final improvement credible.

- Variety: word TF-IDF baseline, character n-gram baseline, then the chosen stronger model.
- Sentiment: majority baseline, TF-IDF logistic regression, then a stronger model if time allows.
- Sarcasm: majority baseline, unweighted TF-IDF model, class-weighted model, then a stronger model if it brings a clear gain.

For sentiment and sarcasm, compare at least these routes:

1. one global model;
2. a model given the true variety as an oracle experiment;
3. the same route using predicted variety;
4. a confidence-gated route that falls back to the global model when variety confidence is low.

This separates a scientific question from a product claim: does variety information help, and does it still help when the variety label comes from the real classifier?

## Six independent work packages

The team can assign one person to each role. Folder ownership keeps the work separate. People can discuss results without editing each other's model code.

### Data and report coordination

Owns:

- `eda.ipynb`
- the shared data rules and output description in `README.md`
- the data and EDA sections of the final report
- final report assembly

Delivers:

- reproducible data download and preparation;
- fixed train, validation and test files;
- quality and removed-row reports;
- the EDA tables and figures already produced;
- a short data section for the report;
- final assembly after every role supplies verified text and results.

Why it matters: this gives every model the same data and prevents split leakage or inconsistent row handling. It also supports the report's data, reproducibility, limitations and contribution sections.

Done when: every cell in `eda.ipynb` runs from a clean start, `outputs/processed/validation_report.json` says that all checks passed, and each task folder can be loaded without extra shared cleaning.

### Sentiment modelling

Owns:

- `src/models/sentiment/`
- `reports/sentiment/`

Delivers:

- a majority or constant baseline;
- a TF-IDF logistic-regression baseline;
- the strongest justified sentiment model;
- validation-only model selection;
- prediction CSV files for validation and test;
- global, per-variety and per-source results;
- a small error sample with likely causes;
- a short report section explaining what improved and what did not.

Why it matters: this proves that the final sentiment component is better than a simple baseline and shows whether performance holds across markets and platforms.

Prediction files should use:

```text
id,pred_label,prob_0,prob_1,model_name
```

### Sarcasm modelling

Owns:

- `src/models/sarcasm/`
- `reports/sarcasm/`

The Google imbalance needs to be handled here, not left for evaluation to discover later. There are 88 sarcastic Google examples in the whole prepared dataset. `en-UK Google` has only one in train and zero in validation and test. `en-IN Google` is also very sparse.

Required approach:

1. Train one shared model across all varieties and sources. Do not build a separate `en-UK Google` or `en-IN Google` sarcasm model.
2. Keep a normal TF-IDF baseline and compare it with a class-weighted version. Calculate the weights from train only.
3. If a probability threshold is changed, choose it on validation only. Record both the default and chosen threshold.
4. Do not oversample validation or test. If training-only oversampling is tried, keep it inside the training fold and compare it with class weighting.
5. Report macro-F1, sarcastic precision, recall and F1, PR-AUC, balanced accuracy and the confusion matrix. Accuracy is secondary.
6. Break results down by variety and by source. Show a `variety × source` result only beside its positive and total support.
7. For `en-UK Google` test, positive-class recall, F1 and PR-AUC are not measurable. Write `N/A`, not zero. Report false positives, false-positive rate, specificity and predicted-positive rate.
8. Export a segment-support file or reuse `outputs/eda/sarcasm_segment_support_recommendations.csv` so the application knows when to show a warning.

The application behaviour for sparse Google segments should also be agreed here: use the shared model, display `Limited segment evidence`, and send predicted sarcastic cases to human review.

Delivers:

- the majority, unweighted and class-weighted baselines;
- the strongest justified model;
- validation and test predictions with probabilities;
- the chosen threshold and how it was selected;
- source-aware and support-aware metrics;
- a short error analysis, including Google false positives;
- a clear limitations paragraph.

Why it matters: honest handling of rare positives is more convincing than a high accuracy number that mostly predicts “not sarcastic.” It directly supports model quality, evaluation quality and trustworthy user interaction.

### Variety modelling and variety-aware experiments

Owns:

- `src/models/variety/`
- `src/models/routing/`
- `reports/variety/`

Delivers:

- word and character n-gram baselines;
- the final variety classifier and calibrated probabilities;
- per-class precision, recall and F1;
- a confusion matrix and source-sliced results;
- a cross-source check, such as training on one source and testing on the other;
- the global/oracle/predicted/gated comparison for sentiment and sarcasm;
- a short explanation of whether variety information really helped.

Why it matters: the current EDA gets about 0.71 validation macro-F1 from a simple character model, but source can be predicted at about 0.97. This role must show that the system learned more than Google-versus-Reddit style.

The inference wrapper should return probabilities, not only a label, so low-confidence routing can be tested.

### Common evaluation

Owns:

- `evaluation/`
- `reports/evaluation/`
- the locked final metric tables and figures

Delivers:

- one evaluator that reads prediction CSV files by `id`;
- the same metrics and label order for every model;
- overall, per-variety, per-source and support-aware segment results;
- confidence intervals for the main differences, using paired bootstrap resampling if practical;
- length-based and source-based error analysis;
- a simple significance or uncertainty statement for claimed improvements;
- final figures and a results table that the report, poster and application all reuse.

Why it matters: central evaluation stops each model from choosing the metric that makes it look best. It also turns subgroup limitations into visible evidence.

The evaluator should never import private training classes. It should work from gold files and prediction files only.

### Application, user testing and poster

Owns:

- `app/`
- `src/inference/`
- `reports/user_study/`
- `poster/`

Delivers:

- single-text input and CSV upload;
- optional source and market context;
- variety, sentiment and sarcasm predictions with confidence;
- low-confidence and limited-evidence warnings;
- a review queue and downloadable results;
- a short privacy note and a clear statement that variety is not nationality;
- a structured user test and a record of what changed afterwards;
- the final poster using only locked results.

Why it matters: Part B asks for user-focused interaction, not only a model demo. Users should be able to understand uncertainty, correct outputs and finish a realistic review task.

A small but useful test can use six to twelve participants from, or familiar with, different English-speaking regions. Ask each person to:

1. enter one natural message or short review in their usual English;
2. enter one clearly positive or negative example;
3. enter a sarcastic example only if it feels natural to them;
4. inspect the model's confidence and warning;
5. correct a wrong result;
6. complete a short batch-review task;
7. explain what they think the warning means.

Record task completion, time, incorrect interpretations, correction use and short ratings for clarity and trust. Do not treat these user-written examples as a new test set or add them to training without consent. Use the observations to make at least one visible interface change and report the before-and-after reason.

## Shared agreements

### Prediction contract

All modelling roles should export the same basic fields:

```text
id,pred_label,prob_0,prob_1,model_name
```

Extra probability columns are fine for the three-class variety task. Keep class order in a small metadata JSON file.

### Inference contract

The application should be able to call one function and receive a structure like:

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

The application can start with a mock response. Final model files should replace the mock without changing the interface.

### Language for claims

Use “English variety in the BESSTIE dataset,” not “the user's nationality.” Say that a model “performed better on this test split,” not that it “understands British, Indian or Australian people.” Always show subgroup sample counts near subgroup scores.

## A simple order of work

1. Data files and schemas are fixed.
2. The three modelling roles work in parallel.
3. Evaluation is built early against small mock prediction files.
4. The application is built early against a mock inference response.
5. Model roles export validation predictions and agree on final settings.
6. Each final model runs once on test and sends predictions to evaluation.
7. Evaluation publishes the locked result package.
8. User testing uses the integrated application and leads to at least one recorded change.
9. Each role supplies its finished report text and contribution statement.
10. The report and poster are assembled from the same verified numbers.

## Final quality check

Before submission, the team should be able to answer yes to all of these:

- Can someone reproduce the prepared data with one command?
- Are train, validation and test used for the right purposes?
- Does every task have a simple baseline and a justified final model?
- Are macro and per-class results shown, not only accuracy?
- Are variety and source results shown with sample counts?
- Is the Google sarcasm limitation handled in training, evaluation and the interface?
- Is there evidence that source shortcuts were tested?
- Can a user correct results and understand uncertainty?
- Did user testing lead to a documented change?
- Do the report, poster and application use the same final numbers?
- Are limitations and contributions stated plainly?

## Starting point

Install `requirements.txt`, open `eda.ipynb` from the repository root and run all cells. The notebook downloads any missing BESSTIE source files, prepares and checks the shared data, and writes every handoff file to the paths listed in `README.md`.
