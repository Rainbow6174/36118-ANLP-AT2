# CrisisLens development plan and handoff record

This document records the work split and interface decisions used while CrisisLens was developed. All six work areas are now integrated. See `README.md` for the finished system, current repository layout and deployment instructions. The detailed contribution records are under `report/sections/`.

Start with README.md. Run notebooks/01_crisis_eda.ipynb. Then read the section for your role. This file explains the EDA results, each member's work, the files they should provide and how the app parts fit together.

## Current integration state

The six work areas now have code or results in the repository. The final application keeps the original handoff paths:

~~~
models/transformer/          deployed classifier
models/retrieval/index/      historical-message index
app/backend/main.py          FastAPI entry point
app/frontend/main.py         NiceGUI entry point
data/raw/humaid_events/      local event data
~~~

`app/backend/services.py` connects these parts without moving their internal files. The backend can use `mock`, `auto` or `real` runtime mode. `real` is the final deployment mode and stops with a clear message when a required model or index file is missing. See `README.md` for the preparation and run commands.

The remaining team work is to review the integrated flow, finish the user study, select final figures and combine the six report sections. Expensive model training does not need to be repeated when the selected artefacts and saved results are available.

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

Historical HumAID examples stay in the read-only retrieval index with
`source_type=humaid_history`. New messages are saved in SQLite with
`source_type=user`, and the public report-creation endpoint accepts user
messages only. Present predictions as sorting suggestions, not verified facts
or emergency priorities.

## Roles and boundaries

| Member | Main responsibility | Main results |
| --- | --- | --- |
| 1 | Data preparation, EDA and shared data rules | EDA results, labels, splits and data guidance |
| 2 | Transparent text baseline and model packaging | Majority, TF-IDF word/character models and baseline findings |
| 3 | Contextual text model, imbalance treatment and calibration | Compact Transformer, confidence scores and model findings |
| 4 | Backend, database, API and shared evaluation harness | Working service, database schema, integration tests and reusable evaluation code |
| 5 | Retrieval and search | Related-message index, search quality and retrieval findings |
| 6 | Frontend, UI/UX and user study | User flow, interface evidence and user-study findings |

Members 2 and 3 train and package the classification models. Member 4 owns the thin backend service and a reusable evaluator; Members 2 and 3 use that evaluator for their own event-held-out runs. Member 5 owns retrieval and search. Member 6 owns the frontend and user study. Every member supplies their own report section and evidence. Member 1 keeps the shared data rules stable and assembles the report structure, not all of the report text.

## Working evaluation agreement

Macro-F1 is the shared main classification metric. Each serious run reports precision, recall, F1 and support for every label, balanced accuracy, a confusion matrix, validation probabilities and run time.

The final app model also reports whether its confidence scores match its results. The current distribution-shift test holds out `cyclone_idai_2019` from the 13-event `events_set1_47K` subset. It reports macro-F1, calibration, review coverage and review risk, with support for every label. This is one held-out event, so the report treats it as a focused stress test rather than evidence of general robustness. Retrieval reports precision@k, pooled recall@k and search time. The user study reports task completion, time, board choice, confidence understanding and corrections.

### Dependency changes

The checked-in environment covers the EDA and shared project code. If a work area needs another package, install and test it locally first. After the local test works, update `pyproject.toml`, `requirements.txt` and `uv.lock` together, record the version and tell the team before changing the shared files. A planned package is not added to the repository until it has passed a local test.

## Member 1: data, EDA and shared data contract

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
7. Keep the report outline and shared evidence list up to date. Each member writes their own section.

### Why and purpose

The notebook shows uneven class support, event concentration, a small amount of duplicate leakage and the difference between HumAID and CrisisMMD. Keeping the data files fixed lets the other members work in parallel.

### Expected result and handoff

~~~
notebooks/01_crisis_eda.ipynb
outputs/eda/
report/sections/member1_data_and_eda.md
~~~

Member 1 does not train the final classifier or build a second copy of the application.

After the EDA outputs and shared interfaces are published, treat `outputs/eda/` and the ten-label list as read-only. Later changes need a team decision.

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
10. Wrap the selected model as `classify(text)` with the shared response format.
11. Run the common event-held-out evaluator supplied by Member 4 and save the baseline results.

### Purpose and expected result

This gives a clear lower bound. Member 4 can use the packaged model and its common evaluator. Member 6 can use the wrapper in the first app demo.

### Handoff

~~~
models/text_baseline/
models/text_baseline/metadata.json
outputs/predictions/baseline/
outputs/results/baseline/
outputs/results/cross_event/baseline/
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
8. Wrap it as the same `classify(text)` interface as Member 2.
9. Run the common event-held-out evaluator supplied by Member 4 and save the Transformer results.

### Purpose and expected result

This tests whether a Transformer understands the messages better than the simple baseline. It also shows the cost of uneven class sizes.

### Handoff

~~~
models/transformer/
models/transformer/metadata.json
outputs/predictions/transformer/
outputs/results/transformer/
outputs/results/cross_event/transformer/
report/sections/member3_contextual_model.md
~~~

## Member 4: backend, database, API and shared evaluation harness

### Start here

~~~
README.md
LATER_PLAN.md
outputs/eda/eda_summary.json
app/
evaluation/cross_event/
~~~

### Work

1. Build a small FastAPI service around the shared model and retrieval interfaces.
2. Create the SQLite schema and keep raw text, prediction, user correction, source, status and timestamps separate.
3. Implement the required REST endpoints in `README.md` and return the documented JSON fields.
4. Use mock model and retrieval responses while Members 2, 3 and 5 are still working.
5. Build a reusable event-held-out evaluator in `evaluation/cross_event/` that accepts any model with the shared `classify(text)` interface.
6. Let Members 2 and 3 run their own baseline and Transformer event tests with this evaluator. Member 4 maintains the script and combines the result tables.
7. Add integration tests for analyse -> save -> browse -> search and for category correction.
8. Record API response time, failures and the final end-to-end test results.
9. Document the local run command and sample requests.

### Purpose and expected result

This gives the team one stable service and one fair way to compare models on a disaster that was not in training. It keeps backend work separate from model experiments.

### Handoff

~~~
app/backend/
app/schema.sql
app/app_models.json
evaluation/cross_event/
outputs/results/cross_event/
outputs/results/system/
report/sections/member4_backend_and_evaluation.md
~~~

The backend, schema, model configuration and event-held-out evaluator are now present. The integration layer in `app/backend/services.py` loads Member 3's deployed Transformer and Member 5's retrieval index. Mock mode remains available for tests and frontend work; real mode is used for the final application.

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
4. Implement `retrieve(text, k, filters=None)` for related reports and `search(query, filters=None, k=20)` for keyword/filter search.
5. Return ID, similarity, text preview, board label and source type.
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

## Member 6: frontend, UI/UX and user study

### Start here

The frontend is now implemented and can still use mock responses for isolated interface work. For the final flow, set `CRISISLENS_API_URL` so it calls the real backend. The frontend continues to read only the documented API and does not load models or the database directly.

~~~
app/frontend/
outputs/eda/eda_summary.json
~~~

### Work

1. Build a single-message submission page.
2. Call the backend API and show the predicted board, confidence and review state.
3. Provide a board list and one page for every label.
4. Show the new message at the top of the selected board after submission.
5. Show historical and related messages returned by the API.
6. Add the agreed board search/filter controls and a low-confidence review view.
7. Allow category confirmation or correction without changing the original model prediction.
8. Add clear loading, empty, error and API response states.
9. Run a small user study with people from different English backgrounds.
10. Test submit, classify, save, redirect and find historical/related messages.
11. Record task completion, time, board choice, confidence understanding and corrections.
12. Make one visible interface revision from the study.
13. Provide frontend local-run steps and screenshots for the report and poster.

### Purpose and expected result

This turns model outputs into a complete board workflow. The final demo must show saving and board navigation, not only a prediction label. The backend and database remain Member 4's responsibility.

### Handoff

~~~
app/frontend/
report/user_study/
report/sections/member6_frontend_and_user_study.md
outputs/figures/application/
~~~

Do not store unnecessary personal information in the app database or user-study files.

Member 6 supplies screenshots and layout suggestions for the poster. All members supply their own poster text, figures and contribution evidence.

## Shared handoff formats

### Classification response

~~~
{
  "predicted_label": "requests_or_urgent_needs",
  "probabilities": {
    "caution_and_advice": 0.03,
    "displaced_people_and_evacuations": 0.02,
    "infrastructure_and_utility_damage": 0.03,
    "injured_or_dead_people": 0.01,
    "missing_or_found_people": 0.01,
    "not_humanitarian": 0.02,
    "other_relevant_information": 0.06,
    "requests_or_urgent_needs": 0.78,
    "rescue_volunteering_or_donation_effort": 0.02,
    "sympathy_and_support": 0.02
  },
  "confidence": 0.78,
  "model_version": "baseline-v1",
  "needs_review": false
}
~~~

`probabilities` should contain all ten labels in a fixed order. `predicted_label` is the model result. The model wrapper does not write to the database.

### Retrieval response

~~~
{
  "id": "history-123",
  "similarity": 0.74,
  "board_label": "requests_or_urgent_needs",
  "text_preview": "...",
  "source_type": "humaid_history"
}
~~~

The required Python-style interfaces are:

~~~
classify(text) -> classification response
retrieve(text, k, filters=None) -> ranked related reports
search(query, filters=None, k=20) -> ranked/filtered reports
~~~

### Stored message

~~~
message_id
text
predicted_label
board_label
source_type
confidence
model_version
needs_review
created_at
user_correction
status
~~~

`predicted_label` keeps the original model result. `board_label` is the board
shown by the application and defaults to `predicted_label`. A user correction
changes `board_label` but does not overwrite `predicted_label`. New user
records use `source_type=user` and `status=unverified`. Historical HumAID
results use `source_type=humaid_history`, come from the read-only retrieval
index and are not created through the user-report endpoint.

The MVP status values are `unverified`, `needs_review` and `resolved`. They describe the application's handling of a report, not the truth of its content.

All members use the same ten labels. A model may use its own label numbers, but its label order and loading steps must be recorded.

## What goes into Git

Commit notebooks, reusable code, approved EDA outputs, model settings, selected checkpoints when needed, validation and final predictions, result tables, reviewed errors, final figures, report sections, anonymous user-study results and poster sources. Each member commits to their own work path and does not replace another member's internal implementation.

Keep raw downloads, generated local datasets, virtual environments, temporary checkpoints, rejected experiments and personal study data local. Large model files may use Git LFS or shared storage, but the repository must contain the model version, location and loading steps.

## Parallel work sequence

1. Member 1 published the EDA outputs, ten-label list and shared interfaces.
2. Members 2 and 3 produced the baseline and contextual-model evidence. Member 3's DistilBERT package is the deployed classifier; Twitter-RoBERTa remains the analysis model.
3. Member 4 produced the API, database and evaluation harness. Member 5 produced semantic retrieval, keyword search and its evaluation. Member 6 produced the frontend flow.
4. The integration branch connects the selected classifier and retrieval implementation through `app/backend/services.py` while keeping the original frontend and backend entry points.
5. The team runs submit -> classify -> save -> redirect -> find the new message -> view historical/related messages in real mode and records the final system evidence.
6. The team runs the user study, locks final results, writes the report and prepares the poster together.
