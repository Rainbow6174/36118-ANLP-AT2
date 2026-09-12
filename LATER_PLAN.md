# CrisisLens work plan after the EDA

Start with README.md. Run notebooks/01_crisis_eda.ipynb. Then read the section for your role. This file explains the EDA results, each member's work, the files they should provide and how the app parts fit together.

## Shared starting point

The EDA notebook downloads missing public files, checks them and writes shared results to outputs/eda/. It uses:

1. HumAID-all train, validation and test Parquet files;
2. the event-wise HumAID release for the 19 disaster events;
3. the small CrisisMMD label archive.

Raw and generated data stay in data/, which is rebuilt locally and is not committed.

The downloaded HumAID files contain 76,484 rows:

| Split | Rows | Share |
| --- | ---: | ---: |
| Train | 53,531 | 69.99% |
| Validation | 7,793 | 10.19% |
| Test | 15,160 | 19.82% |

The current files contain ten labels:

~~~
caution_and_advice
displaced_people_and_evacuations
infrastructure_and_utility_damage
injured_or_dead_people
missing_or_found_people
not_humanitarian
other_relevant_information
requests_or_urgent_needs
rescue_volunteering_or_donation_effort
sympathy_and_support
~~~

The dataset card lists an older eleven-label set, but the downloaded files do not contain a separate dont_know_cant_judge class. Use the ten labels above. Do not add or remove a class without a team decision.

## What the EDA tells us

### The official splits are usable

Use the official train, validation and test split for the main benchmark. Use validation to choose models and thresholds. Use the test split only after the settings are fixed.

### Class support is uneven

rescue_volunteering_or_donation_effort is the largest class with 21,278 rows. missing_or_found_people has 358 rows. Report macro-F1, precision, recall, F1 and support for each label. Accuracy alone would hide failures in small classes.

### Events are uneven

Hurricanes account for 41,320 rows. Floods, wildfires and earthquakes have 11,166, 11,133 and 8,932 rows. Some small events have only a few test examples for particular labels, so event-held-out results must show support.

### Duplicate leakage is small but non-zero

The EDA found 12 exact duplicate rows and four simple duplicate groups crossing official splits. Keep model text cleaning consistent and mention these groups in the final discussion.

### CrisisMMD is separate

CrisisMMD has informative, humanitarian and damage-severity tasks. Its files contain image-text rows, so one tweet may occur with several images. Split or remove duplicates by tweet_id, not by raw row. Do not merge its labels with HumAID without a separate research question.

## Product goal and system boundary

The product question is:

> When a user submits a new English disaster message, can CrisisLens classify it, save it in a useful humanitarian information board, take the user to that board and show comparable historical messages while making uncertainty visible?

The model is only one part. The app also needs:

1. Classification: predict a board label, probabilities, confidence and a review flag.
2. Saving: store the message, prediction, model version, source type and time.
3. Boards: list all boards, show each board's published messages and redirect after submission.
4. Context and review: show related messages, support search and filters, and show low-confidence or corrected records.

The complete flow is:

~~~
submit message
  -> classify message
  -> save message with predicted board and confidence
  -> redirect to /boards/<predicted_label>
  -> show the new message and related historical messages
  -> browse/search boards or correct/confirm the label
  -> keep uncertain items in a review queue
~~~

Historical HumAID examples are read-only records with source_type=humaid_history. New messages use source_type=user. Present predictions as sorting suggestions, not verified facts or emergency priorities.

## Roles and boundaries

| Member | Main responsibility | Main results |
| --- | --- | --- |
| 1 | Data preparation, EDA and shared data rules | EDA results, labels, splits and data guidance |
| 2 | Transparent text baselines | Majority, TF-IDF word/character models and baseline findings |
| 3 | Contextual text model and imbalance treatment | Compact Transformer, probabilities and model findings |
| 4 | New-event performance | Leave-one-event-out tests and error analysis |
| 5 | Retrieval and related-message results | Search quality, duplicate grouping and search time |
| 6 | Application, user study and poster | Storage, boards, full flow, user results and poster |

Members 2 and 3 train models. Member 4 tests new-event performance. Member 5 builds retrieval. Member 6 builds the app and runs the user study. Member 1 keeps the data files stable and assembles the report.

## Working evaluation agreement

Macro-F1 is the shared main classification metric. Each serious run reports precision, recall, F1 and support for every label, balanced accuracy, a confusion matrix, validation probabilities and run time.

The final app model also reports whether its confidence scores match its results. New-event results report the mean and range across events and flag labels with very little support. Retrieval reports precision@k or recall@k and search time. The user study reports task completion, time, board choice, confidence understanding and corrections.

## Member 1: data, EDA, coordination and report assembly

### Start here

~~~
notebooks/01_crisis_eda.ipynb
outputs/eda/
README.md
~~~

### Work

1. Keep notebook paths and the ten-label contract stable.
2. Keep download and local-output instructions clear.
3. Update approved EDA outputs if the notebook changes.
4. Answer data-interface questions from Members 2–6.
5. Maintain the event-held-out support table and record-source convention.
6. Write the data and EDA report section.
7. Assemble report sections supplied by the team.

### Why and purpose

The notebook shows uneven class support, event concentration, a small amount of duplicate leakage and the difference between HumAID and CrisisMMD. Keeping the data files fixed lets the other members work in parallel.

### Expected result and handoff

~~~
notebooks/01_crisis_eda.ipynb
outputs/eda/
report/sections/member1_data_and_eda.md
~~~

Member 1 does not train the final classifier or build a second copy of the application.

## Member 2: transparent text baselines

### Start here

~~~
outputs/eda/eda_summary.json
data/raw/humaid/
data/raw/humaid_events/
~~~

### Work

1. Calculate a majority-class reference result.
2. Train word TF-IDF with Logistic Regression or linear SVM.
3. Train a character n-gram TF-IDF baseline.
4. Document class weights or another way to handle uneven classes.
5. Select settings from validation.
6. Save probabilities for each serious model.
7. Report macro-F1, per-label results, confusion matrix and run time.
8. Review errors for large and small classes.
9. Produce one final test prediction after settings are fixed.
10. Wrap the selected model as predict(text) with the shared response format.

### Purpose and expected result

This gives a clear lower bound. Member 4 can use it for the first new-event test. Member 6 can use it for the first app demo.

### Handoff

~~~
models/text_baseline/
models/text_baseline/metadata.json
outputs/predictions/baseline/
outputs/results/baseline/
report/sections/member2_text_baseline.md
~~~

## Member 3: Transformer model and uneven-class treatment

### Start here

~~~
data/raw/humaid/
outputs/eda/humaid_label_distribution.csv
outputs/eda/humaid_text_statistics.csv
~~~

### Work

1. Fine-tune one small Transformer, such as DistilBERT or RoBERTa.
2. Keep the official split and ten labels.
3. Compare normal training with class weights or one other clear method.
4. Record the tokenizer, seed, text length limit and training settings.
5. Save validation probabilities and per-label results.
6. Review errors between other_relevant_information, rescue_volunteering_or_donation_effort and the small classes.
7. Select one model from validation and produce final test predictions after the test plan is fixed.
8. Wrap it as the same predict(text) interface as Member 2.

### Purpose and expected result

This tests whether a Transformer understands the messages better than the simple baseline. It also shows the cost of uneven class sizes.

### Handoff

~~~
models/transformer/
models/transformer/metadata.json
outputs/predictions/transformer/
outputs/results/transformer/
report/sections/member3_contextual_model.md
~~~

## Member 4: performance on new events

### Start here

~~~
data/raw/humaid_events/
outputs/eda/humaid_event_holdout_plan.csv
models/text_baseline/
~~~

### Work

1. Build an evaluator that accepts any model with the shared interface.
2. Start with Member 2's baseline while Member 3 is training.
3. For each event, train on official training rows from the other 18 events.
4. Use held-out validation rows for design choices and held-out test rows for the final event result.
5. Report macro-F1 for each event, per-label scores, support and confusion summaries.
6. Group results by disaster type where support allows.
7. Repeat with the selected Transformer if it is chosen for the app.
8. Explain errors caused by new-event language, rare labels or missing support.

### Purpose and expected result

This answers whether CrisisLens can sort messages from a disaster that was not in training.

### Handoff

~~~
evaluation/cross_event/
outputs/results/cross_event/
report/sections/member4_cross_event.md
~~~

Member 4 can start before the final model is chosen.

## Member 5: related messages and duplicate grouping

### Start here

~~~
data/raw/humaid_events/
outputs/eda/humaid_duplicate_summary.csv
outputs/eda/humaid_label_top_word_features.csv
~~~

### Work

1. Build a historical-message index.
2. Start with TF-IDF cosine similarity.
3. Test sentence embeddings only if they give better results.
4. Implement search(query, board_label, k).
5. Return ID, similarity, text preview and source type.
6. Create a small query set and check it by hand.
7. Report precision@k or recall@k, duplicate behaviour and search time.
8. Keep similarity separate from classification and fact checking.

### Purpose and expected result

This gives each board useful context instead of showing only one label.

### Handoff

~~~
models/retrieval/
outputs/results/retrieval/
report/sections/member5_retrieval.md
~~~

## Member 6: application, storage, user study and poster

### Start here

Member 6 can use mock model and retrieval responses. The app does not need to wait for model training.

~~~
app/
outputs/eda/eda_summary.json
~~~

### Work

1. Build a single-message submission page.
2. Call the model wrapper and show label, confidence and review state.
3. Save each message to SQLite or another simple documented store.
4. Keep historical records and user submissions distinguishable.
5. Provide a board list and one page for every label.
6. Redirect to /boards/<predicted_label> after submission.
7. Show the new message at the top of the board.
8. Query historical messages from the same board.
9. Add related messages from Member 5.
10. Add board search/filtering and a low-confidence review queue.
11. Allow confirmation or correction without changing the original prediction.
12. Provide local-run and deployment steps.
13. Run a user study with people from different English backgrounds.
14. Test submit, classify, save, redirect and find historical/related messages.
15. Record task completion, time, board choice, confidence understanding and corrections.
16. Make one visible interface revision from the study.
17. Assemble the poster from the final story, figures and screenshots.

### Purpose and expected result

This turns model outputs into a complete board workflow. The final demo must show saving and board navigation, not only a prediction label.

### Handoff

~~~
app/
app/app_models.json
app/schema.sql
report/user_study/
report/sections/member6_application_and_user_study.md
poster/
~~~

Do not store unnecessary personal information in the app database or user-study files.

## Shared handoff formats

### Classification response

~~~
{
  "predicted_label": "requests_or_urgent_needs",
  "probabilities": {"requests_or_urgent_needs": 0.82},
  "confidence": 0.82,
  "model_version": "baseline-v1",
  "needs_review": false
}
~~~

### Retrieval response

~~~
{
  "id": "history-123",
  "similarity": 0.74,
  "text_preview": "...",
  "source_type": "humaid_history"
}
~~~

### Stored message

~~~
message_id
text
board_label
source_type
confidence
model_version
needs_review
created_at
user_correction
~~~

All members use the same ten labels. A model may use its own label numbers, but its label order and loading steps must be recorded.

## What goes into Git

Commit notebooks, reusable code, approved EDA outputs, model settings, selected checkpoints when needed, validation and final predictions, result tables, reviewed errors, final figures, report sections, anonymous user-study results and poster sources.

Keep raw downloads, generated local datasets, virtual environments, temporary checkpoints, rejected experiments and personal study data local. Large model files may use Git LFS or shared storage, but the repository must contain the model version, location and loading steps.

## Parallel work sequence

1. Member 1 publishes the EDA outputs and shared label/interface rules.
2. Members 2–5 start in parallel. Member 4 starts with the baseline; Member 5 starts with TF-IDF retrieval.
3. Member 6 builds the complete app flow with mock responses.
4. Member 4 finishes the new-event evaluator and Member 5 finishes the retrieval checks.
5. The team selects the app model using validation and new-event results.
6. Member 6 replaces mocks with the selected model and retrieval index.
7. The team runs submit -> classify -> save -> redirect -> find the new message -> view historical/related messages.
8. The team runs the user study, locks final results, writes the report and prepares the poster.
