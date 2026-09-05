# Using the Prepared Dataset

Use the task views under `data/processed/by_task/`. Every task file has exactly five columns:

`id,text,variety,source,label`

- Sentiment modelling uses `by_task/sentiment/`.
- Sarcasm modelling uses `by_task/sarcasm/`.
- Variety modelling uses `by_task/variety/`; the full split files are available for cross-task experiments.
- Evaluation joins predictions to the gold data using `id`, never row order.
- The application reads model artefacts and can use `variety` and `source` for filters and warnings.

Do not tune on `test.csv`. If a model needs different text cleaning or tokenisation, keep it inside that model's code and document it. Do not overwrite the shared text or split files.
