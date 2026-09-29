# Member 2: Traditional Text Baseline

## Purpose

The traditional text baseline provides CrisisLens with a transparent, computationally inexpensive reference model for the ten-class HumAID humanitarian classification task. Its purpose is not only to establish a lower bound for the contextual Transformer models, but also to provide an interpretable and reproducible classifier with native probabilities, confidence-based human review, and a shared `classify(text)` interface for application integration.

All model selection decisions were made using the official training and validation splits. The official test split was kept untouched until the model configuration, probability handling, and human-review threshold had been frozen.

## Data and preprocessing

The baseline uses the official HumAID text-only classification split:

| Split | Rows |
| --- | ---: |
| Train | 53,531 |
| Validation | 7,793 |
| Test | 15,160 |

The ten-class label order is shared with the rest of CrisisLens and is preserved in model probabilities, reports, confusion matrices, metadata, and the deployment wrapper.

To align the baseline with the contextual model, the same lightweight modelling normalisation is applied to every message:

- URLs are removed;
- mentions are replaced with `@user`;
- the `#` marker is removed while retaining hashtag text;
- repeated whitespace is collapsed.

This intentionally preserves most lexical content instead of aggressively cleaning short social-media messages. The EDA showed that words, hashtags, morphology, spelling variation and character patterns can all provide useful humanitarian-category signals.

## Baseline representations and model selection

The experiments compared word TF-IDF, character TF-IDF, and a combined word-plus-character representation with linear classifiers. Macro-F1 was the primary selection metric because HumAID is strongly imbalanced and accuracy alone can be dominated by the larger categories.

As a reference point, always predicting the majority class, `rescue_volunteering_or_donation_effort`, produced validation accuracy of 0.2782 but macro-F1 of only 0.0435 and balanced accuracy of 0.1000. This demonstrates why class-sensitive metrics are required.

The strongest validation results from the main representation screening were:

| Representation / classifier | Key setting | Validation macro-F1 |
| --- | --- | ---: |
| Word TF-IDF + LinearSVC | `C=0.25`, no class weights | 0.7145 |
| Character TF-IDF + LinearSVC | `C=0.25`, balanced weights | 0.7190 |
| Word + character TF-IDF + LinearSVC | `C=0.1`, no class weights | 0.7250 |
| Word + character TF-IDF + Logistic Regression | `C=1.0`, no class weights | **0.7258** |

Character features improved on the word-only SVM, and combining both representations improved further. This is consistent with the short and noisy nature of social-media crisis text: word n-grams capture explicit humanitarian terms and phrases, while character n-grams capture spelling variation, morphology and fragments of hashtags or named entities.

The final representation uses a `FeatureUnion` containing:

- word TF-IDF with 1–2 grams, `min_df=5`, `max_features=12,000`, and sublinear term frequency;
- character TF-IDF with 3–5 grams, `min_df=10`, `max_features=16,000`, and sublinear term frequency.

The selected classifier is Logistic Regression with `C=1.0`, `class_weight=None`, `solver=lbfgs`, `max_iter=1000`, and `random_state=42`.

Its validation results were:

| Metric | Validation result |
| --- | ---: |
| Accuracy | 0.7514 |
| Macro-F1 | 0.7258 |
| Balanced accuracy | 0.7008 |

The advantage over the strongest combined LinearSVC configuration was small, so it should not be interpreted as a large accuracy improvement. Logistic Regression was preferred because it slightly improved validation macro-F1 while also providing native `predict_proba()` probabilities, which support confidence estimation and human-review routing without adding a separate probability-conversion layer.

## Class imbalance

Class weighting was explicitly evaluated rather than omitted. Balanced weights generally improved balanced accuracy but reduced macro-F1, the primary model-selection metric.

For example:

| Model | Weighting | Macro-F1 | Balanced accuracy |
| --- | --- | ---: | ---: |
| Word SVC, `C=0.25` | None | 0.7145 | 0.6920 |
| Word SVC, `C=0.25` | Balanced | 0.7086 | 0.7231 |
| Combined SVC, `C=0.25` | None | 0.7234 | 0.7017 |
| Combined SVC, `C=0.25` | Balanced | 0.7167 | 0.7218 |
| Logistic Regression, `C=1` | None | 0.7258 | 0.7008 |
| Logistic Regression, `C=1` | Balanced | 0.7153 | 0.7376 |

The final `class_weight=None` setting is therefore a validation-driven decision. The experiments show a real trade-off: balanced weighting raised average recall across classes but reduced the F1 balance between precision and recall.

## Probability quality and calibration assessment

The final Logistic Regression model provides native class probabilities through `predict_proba()`. These probabilities were assessed explicitly rather than assumed to be calibrated.

On validation:

- log loss = 0.7074;
- expected calibration error (ECE) = 0.0232.

ECE was calculated using 15 equal-width confidence bins. Confidence is the maximum predicted class probability, and each bin compares average confidence with empirical accuracy.

Because validation ECE was already low, no additional temperature scaling or other post-hoc calibration was added. The final probability method is therefore native Logistic Regression `predict_proba()`, with `additional_calibration_applied=false`.

This differs from the contextual Transformer pipeline, which applies temperature scaling. The baseline should not be described as temperature-scaled.

## Selective prediction and human review

CrisisLens uses confidence to decide whether a prediction can be auto-accepted or should be routed to human review.

The baseline defines:

`confidence = max(predict_proba)`

The review threshold was selected on validation before official test evaluation. Following the shared project criterion, the threshold search used 200 candidate values and selected the point with maximum validation coverage while keeping accepted-sample risk at or below 5%.

The frozen threshold is:

`tau = 0.8894472361809045`

The decision rule is:

- `confidence >= tau`: auto-accepted;
- `confidence < tau`: `needs_review=true`.

At the selected validation operating point:

| Quantity | Validation result |
| --- | ---: |
| Coverage | 36.05% |
| Accepted-sample risk | 4.73% |
| Review rate | 63.95% |
| Auto-accepted messages | 2,809 |
| Messages requiring review | 4,984 |

The threshold was frozen before the official test was accessed.

## Final official test performance

After model selection, probability assessment, and threshold selection were complete, the frozen model was evaluated once on the official HumAID test split.

The final model is:

**Word + Character TF-IDF + Logistic Regression**

Its official test results are:

| Metric | Test result |
| --- | ---: |
| Accuracy | 0.7557 |
| Macro-F1 | **0.7262** |
| Balanced accuracy | 0.7050 |
| Log loss | 0.6941 |
| ECE | 0.0214 |

The validation macro-F1 of 0.7258 and test macro-F1 of 0.7262 are very close, indicating that the main held-out test result is consistent with the validation estimate rather than showing a large selection-to-test drop.

The frozen validation threshold also transferred closely to the test set:

| Selective-prediction quantity | Test result |
| --- | ---: |
| Coverage | 36.48% |
| Accepted-sample risk | 4.76% |
| Review rate | 63.52% |
| Auto-accepted | 5,530 |
| Needs review | 9,630 |

The accepted-sample error remained below the 5% target, although this safety-oriented operating point sends a majority of messages to human review.

## Per-label test performance

The final per-class results show substantial variation across humanitarian categories.

| Label | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `caution_and_advice` | 0.7169 | 0.5963 | 0.6510 | 1,070 |
| `displaced_people_and_evacuations` | 0.8847 | 0.8646 | 0.8745 | 790 |
| `infrastructure_and_utility_damage` | 0.7998 | 0.8126 | 0.8061 | 1,617 |
| `injured_or_dead_people` | 0.9010 | 0.9060 | 0.9035 | 1,447 |
| `missing_or_found_people` | 0.8148 | 0.6111 | 0.6984 | 72 |
| `not_humanitarian` | 0.6112 | 0.5277 | 0.5664 | 1,245 |
| `other_relevant_information` | 0.5481 | 0.6111 | 0.5779 | 2,407 |
| `requests_or_urgent_needs` | 0.6090 | 0.4664 | 0.5283 | 521 |
| `rescue_volunteering_or_donation_effort` | 0.8132 | 0.8843 | 0.8473 | 4,219 |
| `sympathy_and_support` | 0.8525 | 0.7698 | 0.8090 | 1,772 |

The strongest categories are `injured_or_dead_people`, `displaced_people_and_evacuations`, and `rescue_volunteering_or_donation_effort`.

The weakest are `requests_or_urgent_needs`, `not_humanitarian`, and `other_relevant_information`. These classes contain substantial lexical and semantic overlap with neighbouring categories.

`missing_or_found_people` has only 72 test examples, so its apparent performance should not be overinterpreted.

## Confusion and qualitative error analysis

The largest off-diagonal test confusions were:

| True label | Predicted label | Count |
| --- | --- | ---: |
| `not_humanitarian` | `other_relevant_information` | 361 |
| `other_relevant_information` | `rescue_volunteering_or_donation_effort` | 299 |
| `caution_and_advice` | `other_relevant_information` | 279 |
| `rescue_volunteering_or_donation_effort` | `other_relevant_information` | 246 |
| `other_relevant_information` | `not_humanitarian` | 243 |
| `requests_or_urgent_needs` | `rescue_volunteering_or_donation_effort` | 179 |
| `sympathy_and_support` | `rescue_volunteering_or_donation_effort` | 177 |
| `infrastructure_and_utility_damage` | `other_relevant_information` | 164 |

The main failure mode is lexical overlap across semantically related humanitarian intents. Terms such as `help`, `donate`, `relief`, `fund`, and `supplies` can occur both in messages describing urgent needs and in messages describing donation or volunteering activity. As a result, the TF-IDF model can classify an urgent request as `rescue_volunteering_or_donation_effort` when donation-related lexical features dominate.

A second difficult boundary is `caution_and_advice` versus `other_relevant_information`. Situational reports, forecasts and warnings can contain similar vocabulary, while the distinction may depend on whether the text explicitly advises an action.

The `not_humanitarian` versus `other_relevant_information` boundary is also difficult. These errors are best described as semantic or annotation-category boundary ambiguity rather than evidence that the dataset labels are incorrect.

These patterns illustrate a core limitation of a sparse lexical model: it represents discriminative tokens and token combinations effectively, but it does not model sentence-level context as directly as a contextual encoder.

## Human-review effectiveness

The selective-prediction system does more than reduce accepted-set risk: it concentrates errors in the human-review queue.

Across the 15,160-message official test set:

- total classification errors = 3,704;
- errors routed to review = 3,441;
- errors auto-accepted = 263;
- fraction of all errors captured by review = **92.90%**.

The review queue itself has an error rate of approximately 35.73%, compared with substantially lower error among auto-accepted examples. This shows that confidence is useful for concentrating difficult cases rather than rejecting messages uniformly.

The effect varies by class. Review rates are particularly high for the difficult `not_humanitarian` and `other_relevant_information` categories, at approximately 96% each. `requests_or_urgent_needs` has a review rate of approximately 81.8% and an error-capture rate of approximately 84.5%.

The main limitation is workload: 63.52% of all test messages are routed to human review. The operating point therefore prioritises safety and error capture over automation coverage. This trade-off should be stated explicitly rather than presenting the threshold as a cost-free reliability improvement.

## Computational efficiency

The sparse linear pipeline is inexpensive to train and run relative to neural contextual models.

For the final official evaluation:

- fitting the complete word-plus-character TF-IDF Logistic Regression pipeline on 53,531 training messages took approximately 39.96 seconds;
- inference over all 15,160 test messages took approximately 10.35 seconds;
- evaluation-metric computation took approximately 0.31 seconds.

These measurements depend on the execution environment, but they demonstrate one practical advantage of the traditional baseline: it can be trained and evaluated locally without specialised accelerator hardware.

The packaged `model.joblib` artifact is approximately 3.26 MB, which also makes the baseline suitable for lightweight deployment and reproducible local testing.

## Comparison with the contextual models

Member 3 reports seen-test macro-F1 of approximately 0.755 for DistilBERT and 0.762 for Twitter-RoBERTa. The baseline's test macro-F1 of 0.7262 is lower, providing evidence that contextual modelling improves overall classification performance.

However, the baseline remains useful for several reasons. It is much cheaper to train, has a small packaged artifact, exposes native probabilities, and provides a transparent point of comparison for determining how much value is gained by the Transformer models.

The comparison also helps interpret the source of model improvements. The baseline performs strongly when categories have distinctive lexical patterns, while its largest errors occur where similar words express different intents. This is precisely the type of distinction where contextual representations are expected to help.

## Cross-event generalisation

The project requires a common leave-one-event-out evaluation in which the model is trained on 18 disaster events, tested on the remaining unseen event, and the procedure is repeated across all 19 events.

Member 2's cross-event result is currently **pending the shared Member 4 evaluation harness**.

No cross-event score is reported here yet. In particular, Member 3's earlier experiment using a 13-event subset with `cyclone_idai_2019` held out is a different protocol and is not treated as directly comparable to the planned shared Member 2 evaluation.

When the common harness is available, the packaged baseline will be evaluated with the shared 18-train / 1-held-out protocol and the resulting cross-event metrics will be added to this section.

## Limitations

Several limitations should be considered when interpreting the baseline.

First, TF-IDF is fundamentally lexical. It can represent discriminative words, phrases and character patterns, but it cannot directly model context, compositional meaning or event semantics in the same way as a Transformer.

Second, the EDA identified a small number of duplicate messages, including normalised duplicate groups crossing official split boundaries. This creates a limited potential source of leakage and should be acknowledged when interpreting official-split results.

Third, event-specific words, hashtags, locations and named entities may become shortcuts for a lexical model. Strong performance on the official random-style split therefore does not establish robustness to unseen disasters; this is why the project also requires common cross-event evaluation.

Fourth, the human-review threshold is deliberately conservative. It captures most test errors but requires review of more than sixty percent of messages, which may be operationally expensive at scale.

Finally, performance estimates for very small classes are uncertain. `missing_or_found_people`, for example, has only 72 official test examples.

## Reproducibility and deployment handoff

The final baseline configuration is frozen and recorded in `models/text_baseline/metadata.json`.

The packaged model is:

`models/text_baseline/model.joblib`

It is trained on the official 53,531-row training split only so that the packaged model corresponds to the evaluated frozen baseline. It is not retrained on train plus validation after observing the test result.

The deployment interface is implemented in:

`models/text_baseline/inference.py`

Its `classify(text)` function returns:

- `predicted_label`;
- probabilities for all ten labels in canonical order;
- maximum probability as `confidence`;
- `model_version="baseline-v1"`;
- `needs_review` based on the frozen threshold.

The wrapper only performs prediction and does not write to the application database.

The main result artifacts are:

- `outputs/results/baseline/selected_validation.json`;
- `outputs/results/baseline/final_test.json`;
- `outputs/predictions/baseline/test_predictions.csv`;
- `outputs/results/baseline/test_selective_by_class.csv`.

The final official HumAID test result for the Member 2 baseline is:

**Word + Character TF-IDF + Logistic Regression — macro-F1 = 0.7262.**
