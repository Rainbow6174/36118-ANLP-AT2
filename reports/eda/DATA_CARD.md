# BESSTIE Project Data Card

## Summary

- **Dataset:** BESSTIE
- **Project rows after QC:** 10,052
- **Varieties:** en-AU, en-IN, en-UK
- **Sources:** Google Places reviews and Reddit comments
- **Labels:** sentiment (0 negative, 1 positive); sarcasm (0 non-sarcastic, 1 sarcastic)
- **Official repository:** <https://huggingface.co/datasets/unswnlporg/BESSTIE>
- **License shown by the official repository at retrieval:** CC BY 4.0
- **Project split seed:** 36118

## Split construction

The public official validation split becomes the project test split. A stratified 15% sample of the official train split becomes the project validation split; the remainder becomes project train. The held-out project test set is not for tuning.

## Fields

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable readable row identifier; not a hash |
| `text` | string | Minimally cleaned input text |
| `variety` | category | en-AU, en-IN or en-UK |
| `source` | category | google or reddit |
| `sentiment` | integer | 0 negative, 1 positive |
| `sarcasm` | integer | 0 non-sarcastic, 1 sarcastic |
| `official_split` | category | train or validation in the public release |
| `split` | category | train, validation or test for this project |
| `char_count` | integer | Number of characters after whitespace cleaning |
| `word_count` | integer | Whitespace-token count |

## Processing and quality controls

Only whitespace is normalised. Linguistic signals such as spelling, case, punctuation and emoji are retained. Empty/invalid rows, label validity, exact duplicates, conflicting duplicate labels and cross-split overlap are checked. Removed rows are listed in the audit CSV. The pipeline deliberately does not use local file hashes or SHA256 freezing.

## Appropriate use

Sentiment and sarcasm modelling, per-variety evaluation, cross-variety generalisation analysis and a decision-support prototype for aggregate customer/social-insight workflows.

## Inappropriate use

Do not use predictions to infer nationality, ethnicity or identity, to make high-impact decisions about individuals, or to claim representation of all speakers of a country or English variety.

## Citation

Srirag, D., Joshi, A., Painter, J., & Kanojia, D. (2025). BESSTIE: A Benchmark for Sentiment and Sarcasm Classification for Varieties of English. Findings of ACL 2025, 8413-8429. <https://doi.org/10.18653/v1/2025.findings-acl.441>
