# Data Sources, Preparation and Initial Analysis

## Data source and suitability

The project uses BESSTIE, a manually annotated benchmark for sentiment and sarcasm classification across Australian (`en-AU`), Indian (`en-IN`) and British (`en-UK`) English. The public release contains Google Places reviews and Reddit comments. These two domains support the proposed customer/social-insights workflow while also making domain and English-variety performance differences measurable.

Official dataset: <https://huggingface.co/datasets/unswnlporg/BESSTIE>  
Paper: Srirag et al. (2025), <https://aclanthology.org/2025.findings-acl.441/>

## Reproducible preparation

The pipeline downloads six official CSV files: train and validation files for each of the three varieties. Because the public release does not expose its test set, the official validation split is used once as the project's held-out test set. The official train split is divided into project train and validation subsets using seed `36118` and a `15%` validation target. Stratification uses the joint combination of variety, source, sentiment and sarcasm so that the small sarcasm class is represented across development splits.

Cleaning is intentionally minimal. Leading and trailing whitespace is removed and internal whitespace is collapsed, while case, spelling, punctuation, emoji, hashtags and regional expressions are retained. Exact/case-only duplicate text is detected after Unicode NFKC normalisation and case-folding. Conflicting-label duplicate groups are removed. For a duplicate appearing in both official train and validation, the validation example is retained and the train copy is removed, preventing text leakage into the project test set. No fuzzy deduplication is used because it could remove meaningful variety-specific wording.

## Dataset after quality control

| Project split | Rows | Share |
| --- | --- | --- |
| train | 7514 | 74.8% |
| validation | 1327 | 13.2% |
| test | 1211 | 12.0% |

| English variety | Rows | Share |
| --- | --- | --- |
| en-AU | 3077 | 30.6% |
| en-IN | 3779 | 37.6% |
| en-UK | 3196 | 31.8% |

The processed corpus contains **10,052 texts**. `en-IN` is the largest variety subset and `en-AU` is the smallest, so overall accuracy alone would allow the larger groups to dominate the result. The evaluation must therefore report macro-F1 and per-variety results. Google contributes **5,011** texts and Reddit contributes **5,041** texts, requiring per-source analysis rather than assuming one domain represents the other.

Positive sentiment accounts for **49.6%** of all retained texts. Sarcastic texts account for only **14.2%**, confirming material class imbalance for sarcasm. Model owners should use stratified training, macro-F1, per-class precision/recall and class weighting or threshold analysis rather than accuracy alone.

Quality control removed **22 rows**. The exact reasons and affected row IDs are recorded in `data/processed/audit/removed_rows.csv`; no manual or undocumented deletion is performed. The final validation report confirms unique IDs, valid labels, complete variety/source coverage and zero exact text overlap between train, validation and test.

## Key EDA findings and modelling consequences

| Variety | Source | Positive sentiment | Sarcastic | N |
| --- | --- | --- | --- | --- |
| en-AU | Google | 73.5% | 6.8% | 1076 |
| en-AU | Reddit | 31.9% | 42.0% | 2001 |
| en-IN | Google | 74.8% | 0.7% | 1870 |
| en-IN | Reddit | 25.4% | 13.5% | 1909 |
| en-UK | Google | 74.8% | 0.0% | 2065 |
| en-UK | Reddit | 11.4% | 21.8% | 1131 |

The strongest pattern is a **source-label interaction**. Google positive-sentiment rates are approximately 74% for all three varieties, whereas Reddit positive rates range from 11.4% to 31.9%. Sarcasm is extremely rare in Google reviews for en-IN and en-UK but substantially more common on Reddit, especially for en-AU. A model can therefore achieve deceptively strong aggregate results by learning domain cues rather than robust sentiment or sarcasm cues. Every model comparison should report both per-variety and per-source metrics, and the error analysis should examine source-specific failures.

Text length also varies by cell: the median ranges from **15 words** for `en-IN` `reddit` to **56 words** for `en-UK` `google`. Transformer truncation length and traditional-model features should therefore be documented and tested rather than chosen without evidence.

These are descriptive dataset findings, not claims about all speakers of the three English varieties. The observed differences may reflect platform, topic and collection choices as well as linguistic variation.

## Handoff to the team

- Sentiment modelling: `data/processed/by_task/sentiment/{train,validation,test}.csv`
- Sarcasm modelling: `data/processed/by_task/sarcasm/{train,validation,test}.csv`
- Variety and cross-variety work: `data/processed/by_task/variety/` and the full split files
- Common schema: `id,text,variety,source,sentiment,sarcasm,official_split,split,char_count,word_count`
- Test policy: the project test split must not be used for hyperparameter tuning, threshold selection or feature decisions

## Limitations and responsible use

Variety is assigned from collection context and annotation design; it is not a reliable indicator of a writer's identity or nationality. The corpus covers only three English varieties and two online domains, and it may contain topical, demographic and platform-specific biases. Results should be described as performance on BESSTIE subsets, not as universal performance for all Australian, Indian or British English speakers. User-provided text should not be stored or used for training without an explicit consent and privacy process.

## Data and EDA contribution

This work covers sourcing the official BESSTIE data, building the preparation pipeline, defining the shared dataset contract, creating leakage-safe project splits, recording cleaning and deduplication decisions, checking data quality, completing the initial analysis, and producing reusable task files and figures for the report and poster.
