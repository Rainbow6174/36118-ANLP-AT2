"""Build the executable EDA notebook from version-controlled cell sources."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "eda.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def build() -> None:
    notebook = nbf.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10+"},
        "title": "BESSTIE Data Preparation and EDA",
    }
    notebook["cells"] = [
        md(
            """
# BESSTIE Data Preparation and EDA

**Project:** VarietyLens - English-variety classification with variety-aware sentiment and sarcasm analysis  

This notebook checks the prepared BESSTIE data and explores the patterns that matter for the rest of the project. It creates tables and figures that the modelling, evaluation and application work can use directly.

The test labels appear only in coverage tables. They must not be used to choose features, models or thresholds.
"""
        ),
        md(
            """
## Set up the notebook

We start by loading the libraries, finding the shared dataset and creating the output folders. The two printed paths confirm that the notebook is reading and writing in the right place.
"""
        ),
        code(
            """
from pathlib import Path
import json
import re
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display, Markdown

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore", category=FutureWarning)
sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 180,
    "axes.titleweight": "bold",
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})

ROOT = Path.cwd().resolve()
if not (ROOT / "data" / "processed" / "dataset_v1.csv").exists():
    candidates = [Path.cwd().resolve().parent, Path.cwd().resolve().parents[1]]
    ROOT = next((candidate for candidate in candidates if (candidate / "data" / "processed" / "dataset_v1.csv").exists()), ROOT)

DATA_PATH = ROOT / "data" / "processed" / "dataset_v1.csv"
QUALITY_PATH = ROOT / "data" / "processed" / "quality_report.json"
VALIDATION_PATH = ROOT / "data" / "processed" / "validation_report.json"
OUTPUT_DIR = ROOT / "reports" / "eda" / "notebook_outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_COLUMNS = [
    "id", "text", "variety", "source", "sentiment", "sarcasm",
    "official_split", "split", "char_count", "word_count"
]
SPLIT_ORDER = ["train", "validation", "test"]
VARIETY_ORDER = ["en-AU", "en-IN", "en-UK"]
SOURCE_ORDER = ["google", "reddit"]

def save_figure(fig, name):
    fig.savefig(FIGURE_DIR / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIGURE_DIR / f"{name}.svg", bbox_inches="tight")

def with_percent_strings(frame, columns):
    formatted = frame.copy()
    for column in columns:
        formatted[column] = formatted[column].map(lambda value: f"{value:.2%}" if pd.notna(value) else "N/A")
    return formatted

print("The shared dataset is ready.")
print(f"Tables and figures will be saved in: {OUTPUT_DIR.relative_to(ROOT)}")
"""
        ),
        md(
            """
## 1. Load and check the shared data

Here we load the full dataset and its quality reports. The checks cover columns, IDs, labels and split mapping. The output is a short summary and three example rows; a failed check stops the run.

The public BESSTIE test set is not available, so the official validation split is used as our held-out project test set.
"""
        ),
        code(
            """
df = pd.read_csv(DATA_PATH)
quality = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
validation = json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))

assert list(df.columns) == EXPECTED_COLUMNS
assert df["id"].is_unique
assert set(df["variety"]) == set(VARIETY_ORDER)
assert set(df["source"]) == set(SOURCE_ORDER)
assert set(df["split"]) == set(SPLIT_ORDER)
assert set(df["sentiment"]) == {0, 1}
assert set(df["sarcasm"]) == {0, 1}
assert validation["passed"] is True
assert ((df["split"] == "test") == (df["official_split"] == "validation")).all()

overview = pd.DataFrame({
    "measure": ["Rows after QC", "Rows removed", "Duplicate-text removals", "Conflicting-label removals", "Validation checks passed"],
    "value": [
        len(df),
        quality["rows_removed"],
        quality["removal_reasons"].get("duplicate_text", 0),
        quality["removal_reasons"].get("conflicting_duplicate_labels", 0),
        sum(item["passed"] for item in validation["checks"]),
    ],
})
display(overview)
display(df.head(3))
"""
        ),
        md(
            """
## 2. Check label balance across the splits

The next tables compare sentiment and sarcasm rates across train, validation and test. We save both an overall view and a detailed `variety × source` view. Counts stay beside the rates because small groups can produce unstable percentages.
"""
        ),
        code(
            """
split_label_rows = []
for split in SPLIT_ORDER:
    part = df[df["split"] == split]
    split_label_rows.append({
        "split": split,
        "n": len(part),
        "sentiment_positive_n": int(part["sentiment"].sum()),
        "sentiment_positive_rate": part["sentiment"].mean(),
        "sarcastic_n": int(part["sarcasm"].sum()),
        "sarcastic_rate": part["sarcasm"].mean(),
    })

split_label_balance = pd.DataFrame(split_label_rows)
split_label_balance.to_csv(OUTPUT_DIR / "label_balance_by_split.csv", index=False)
display(with_percent_strings(split_label_balance, ["sentiment_positive_rate", "sarcastic_rate"]))

stratified_rows = []
for task in ["sentiment", "sarcasm"]:
    grouped = (
        df.groupby(["split", "variety", "source"], observed=True)[task]
          .agg(n="size", positive_n="sum", positive_rate="mean")
          .reset_index()
    )
    grouped.insert(0, "task", task)
    stratified_rows.append(grouped)
stratified_balance = pd.concat(stratified_rows, ignore_index=True)
stratified_balance.to_csv(OUTPUT_DIR / "label_balance_by_split_variety_source.csv", index=False)

pivot_rates = stratified_balance.pivot_table(
    index=["task", "variety", "source"], columns="split", values="positive_rate"
).reset_index()
pivot_rates["max_rate_gap"] = pivot_rates[SPLIT_ORDER].max(axis=1) - pivot_rates[SPLIT_ORDER].min(axis=1)
display(with_percent_strings(
    pivot_rates.sort_values("max_rate_gap", ascending=False),
    ["train", "validation", "test", "max_rate_gap"],
))
"""
        ),
        md(
            """
### Plot the split check

The bar chart makes any shift in label balance easy to spot. We save a PNG for quick use and an SVG for the report or poster.
"""
        ),
        code(
            """
fig, ax = plt.subplots(figsize=(8.5, 4.8))
x = np.arange(len(SPLIT_ORDER))
width = 0.34
ax.bar(x - width/2, split_label_balance["sentiment_positive_rate"] * 100, width, label="Positive sentiment", color="#2E74B5")
ax.bar(x + width/2, split_label_balance["sarcastic_rate"] * 100, width, label="Sarcastic", color="#E07A5F")
ax.set_xticks(x, SPLIT_ORDER)
ax.set_ylabel("Share of split (%)")
ax.set_title("Label proportions remain stable across project splits")
ax.legend(frameon=False)
for container in ax.containers:
    ax.bar_label(container, fmt="%.1f%%", padding=3, fontsize=9)
sns.despine(ax=ax)
save_figure(fig, "label_proportions_by_split")
plt.show()
"""
        ),
        md(
            """
## 3. See how sample sizes differ

These heatmaps count every variety and source combination: first across all data, then inside each split. They show which comparisons have enough support and which ones need cautious wording. The same counts are saved as CSV.
"""
        ),
        code(
            """
count_table = (
    df.groupby(["variety", "source"], observed=True)
      .size().unstack(fill_value=0)
      .reindex(index=VARIETY_ORDER, columns=SOURCE_ORDER)
)
count_table.to_csv(OUTPUT_DIR / "variety_source_sample_counts.csv")

fig, axes = plt.subplots(1, 4, figsize=(16, 4.2), constrained_layout=True)
sns.heatmap(count_table, annot=True, fmt=",d", cmap="Blues", cbar=False, ax=axes[0])
axes[0].set_title("All processed data")
for index, split in enumerate(SPLIT_ORDER, start=1):
    table = (
        df[df["split"] == split]
          .groupby(["variety", "source"], observed=True)
          .size().unstack(fill_value=0)
          .reindex(index=VARIETY_ORDER, columns=SOURCE_ORDER, fill_value=0)
    )
    sns.heatmap(table, annot=True, fmt=",d", cmap="Blues", cbar=False, ax=axes[index])
    axes[index].set_title(split.title())
    axes[index].set_ylabel("")
for ax in axes:
    ax.set_xlabel("Source")
save_figure(fig, "variety_source_sample_count_heatmaps")
plt.show()
"""
        ),
        md(
            """
## 4. Compare text lengths

A median alone would hide the long tail, so we calculate several length statistics and plot the full distribution. The boxplot stops at the 99th percentile only for readability; the data itself is unchanged. Later models can use this result to explain their truncation limit.
"""
        ),
        code(
            """
length_summary = (
    df.groupby(["variety", "source"], observed=True)["word_count"]
      .agg(n="size", mean="mean", median="median", std="std", min="min", max="max")
      .reset_index()
)
quantiles = (
    df.groupby(["variety", "source"], observed=True)["word_count"]
      .quantile([0.25, 0.75, 0.90, 0.95, 0.99])
      .unstack().reset_index()
      .rename(columns={0.25: "p25", 0.75: "p75", 0.90: "p90", 0.95: "p95", 0.99: "p99"})
)
length_summary = length_summary.merge(quantiles, on=["variety", "source"])
length_summary.to_csv(OUTPUT_DIR / "text_length_distribution_summary.csv", index=False)
display(length_summary.round(2))

plot_df = df.copy()
plot_df["segment"] = plot_df["variety"] + " / " + plot_df["source"].str.title()
segment_order = [f"{v} / {s.title()}" for v in VARIETY_ORDER for s in SOURCE_ORDER]
p99 = plot_df["word_count"].quantile(0.99)

fig, axes = plt.subplots(1, 2, figsize=(15, 5.2), constrained_layout=True)
sns.ecdfplot(
    data=plot_df, x="word_count", hue="source",
    log_scale=True, ax=axes[0], palette={"google": "#2E74B5", "reddit": "#E07A5F"}
)
axes[0].set_title("Cumulative word-count distribution by source")
axes[0].set_xlabel("Words per text (log scale)")
axes[0].set_ylabel("Cumulative share of texts")

sns.boxplot(
    data=plot_df[plot_df["word_count"] <= p99], x="word_count", y="segment",
    order=segment_order, hue="source", dodge=False, legend=False,
    palette={"google": "#2E74B5", "reddit": "#E07A5F"}, ax=axes[1]
)
axes[1].set_title(f"Group distributions up to the 99th percentile ({p99:.0f} words)")
axes[1].set_xlabel("Words per text")
axes[1].set_ylabel("")
save_figure(fig, "text_length_distributions")
plt.show()
"""
        ),
        md(
            """
## 5. Look at early keyword patterns

This quick TF-IDF comparison finds words and short phrases that stand out in each training group. The ranked table is useful for later error analysis. It is not proof of a variety feature, since place names, topics and platform habits can also appear near the top.
"""
        ),
        code(
            """
train_df = df[df["split"] == "train"].copy()
train_df["segment"] = train_df["variety"] + " / " + train_df["source"].str.title()

word_vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),
    min_df=5,
    max_df=0.95,
    max_features=18000,
    sublinear_tf=True,
)
word_matrix = word_vectorizer.fit_transform(train_df["text"])
word_names = np.asarray(word_vectorizer.get_feature_names_out())

keyword_rows = []
for segment in segment_order:
    mask = (train_df["segment"] == segment).to_numpy()
    group_mean = np.asarray(word_matrix[mask].mean(axis=0)).ravel()
    other_mean = np.asarray(word_matrix[~mask].mean(axis=0)).ravel()
    differential = group_mean - other_mean
    top_indices = differential.argsort()[-15:][::-1]
    for rank, feature_index in enumerate(top_indices, start=1):
        keyword_rows.append({
            "segment": segment,
            "rank": rank,
            "term": word_names[feature_index],
            "differential_tfidf": differential[feature_index],
        })

segment_keywords = pd.DataFrame(keyword_rows)
segment_keywords.to_csv(OUTPUT_DIR / "top_keywords_by_variety_source_train_only.csv", index=False)
keyword_display = segment_keywords.pivot(index="rank", columns="segment", values="term")
display(keyword_display)
"""
        ),
        md(
            """
### Character n-gram variety baseline and feature inspection

A small character 3-5 gram classifier gives us an early variety baseline. We fit it on train, check it on validation, and save its score report, confusion matrix and strongest character patterns. It is a diagnostic, not a final test result.
"""
        ),
        code(
            """
train = df[df["split"] == "train"]
valid = df[df["split"] == "validation"]

char_vectorizer = TfidfVectorizer(
    analyzer="char_wb",
    ngram_range=(3, 5),
    min_df=5,
    max_features=30000,
    sublinear_tf=True,
)
X_train_char = char_vectorizer.fit_transform(train["text"])
X_valid_char = char_vectorizer.transform(valid["text"])
char_model = LogisticRegression(max_iter=1500, class_weight="balanced", C=2.0)
char_model.fit(X_train_char, train["variety"])
valid_pred = char_model.predict(X_valid_char)

char_macro_f1 = f1_score(valid["variety"], valid_pred, average="macro")
char_report = pd.DataFrame(classification_report(
    valid["variety"], valid_pred, labels=VARIETY_ORDER, output_dict=True, zero_division=0
)).T
char_report.to_csv(OUTPUT_DIR / "char_ngram_variety_validation_report.csv")
print(f"Validation macro-F1: {char_macro_f1:.3f}")
display(char_report.round(3))

cm = confusion_matrix(valid["variety"], valid_pred, labels=VARIETY_ORDER)
fig, ax = plt.subplots(figsize=(5.6, 4.7))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=VARIETY_ORDER, yticklabels=VARIETY_ORDER, ax=ax)
ax.set_title("Character n-gram variety baseline - validation")
ax.set_xlabel("Predicted")
ax.set_ylabel("True")
save_figure(fig, "char_ngram_variety_validation_confusion")
plt.show()

char_names = np.asarray(char_vectorizer.get_feature_names_out())
char_rows = []
for class_index, variety in enumerate(char_model.classes_):
    top_indices = char_model.coef_[class_index].argsort()[-20:][::-1]
    for rank, feature_index in enumerate(top_indices, start=1):
        char_rows.append({
            "variety": variety,
            "rank": rank,
            "char_ngram": repr(char_names[feature_index]),
            "coefficient": char_model.coef_[class_index, feature_index],
        })
top_char_ngrams = pd.DataFrame(char_rows)
top_char_ngrams.to_csv(OUTPUT_DIR / "top_character_ngrams_by_variety_train_only.csv", index=False)
display(top_char_ngrams.pivot(index="rank", columns="variety", values="char_ngram").head(15))
"""
        ),
        md(
            """
### Source-shortcut diagnostic

We also test how easily the text reveals Google versus Reddit. The score report, confusion matrix and associated terms show how strong that shortcut is. A very high score warns us that later models may learn platform style instead of the task we care about.
"""
        ),
        code(
            """
source_pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=5, max_features=20000, sublinear_tf=True)),
    ("model", LogisticRegression(max_iter=1200, class_weight="balanced")),
])
source_pipeline.fit(train["text"], train["source"])
source_pred = source_pipeline.predict(valid["text"])
source_macro_f1 = f1_score(valid["source"], source_pred, average="macro")
source_report = pd.DataFrame(classification_report(
    valid["source"], source_pred, labels=SOURCE_ORDER, output_dict=True, zero_division=0
)).T
source_report.to_csv(OUTPUT_DIR / "source_diagnostic_validation_report.csv")
print(f"Source diagnostic validation macro-F1: {source_macro_f1:.3f}")
display(source_report.round(3))

source_cm = confusion_matrix(valid["source"], source_pred, labels=SOURCE_ORDER)
fig, ax = plt.subplots(figsize=(5.3, 4.5))
sns.heatmap(source_cm, annot=True, fmt="d", cmap="Oranges", xticklabels=SOURCE_ORDER, yticklabels=SOURCE_ORDER, ax=ax)
ax.set_title("Source shortcut diagnostic - validation")
ax.set_xlabel("Predicted source")
ax.set_ylabel("True source")
save_figure(fig, "source_diagnostic_validation_confusion")
plt.show()

src_vectorizer = source_pipeline.named_steps["tfidf"]
src_model = source_pipeline.named_steps["model"]
src_names = np.asarray(src_vectorizer.get_feature_names_out())
coef = src_model.coef_[0]
source_terms = pd.DataFrame({
    "google_associated": src_names[np.argsort(coef)[:15]],
    "reddit_associated": src_names[np.argsort(coef)[-15:][::-1]],
})
source_terms.to_csv(OUTPUT_DIR / "source_associated_terms_train_only.csv", index=False)
display(source_terms)

diagnostic_summary = {
    "char_ngram_variety_validation_macro_f1": float(char_macro_f1),
    "source_prediction_validation_macro_f1": float(source_macro_f1),
    "interpretation": "Source is much easier to predict than English variety, so the final evaluation needs source-aware and cross-source checks.",
}
(OUTPUT_DIR / "preliminary_diagnostic_summary.json").write_text(json.dumps(diagnostic_summary, indent=2), encoding="utf-8")
display(Markdown(
    f"**Diagnostic conclusion:** source prediction macro-F1 is **{source_macro_f1:.3f}**, "
    f"compared with **{char_macro_f1:.3f}** for the preliminary character n-gram variety baseline. "
    "The final project must test source/topic shortcuts rather than treating every variety score as linguistic evidence."
))
"""
        ),
        md(
            """
## 6. Count the sarcasm examples

Here we count sarcastic and non-sarcastic examples overall and for every useful grouping. All six tables are saved. Rates are always shown with counts, because a percentage can be misleading when only a few positive examples exist.
"""
        ),
        code(
            """
def binary_distribution(data, dimensions):
    grouped = (
        data.groupby(dimensions, observed=True)["sarcasm"]
            .agg(total="size", sarcastic="sum", rate="mean")
            .reset_index()
    )
    grouped["sarcastic"] = grouped["sarcastic"].astype(int)
    grouped["non_sarcastic"] = grouped["total"] - grouped["sarcastic"]
    return grouped[dimensions + ["total", "sarcastic", "non_sarcastic", "rate"]]

sarcasm_overall = pd.DataFrame([{
    "group": "overall",
    "total": len(df),
    "sarcastic": int(df["sarcasm"].sum()),
    "non_sarcastic": int((df["sarcasm"] == 0).sum()),
    "rate": df["sarcasm"].mean(),
}])
sarcasm_split = binary_distribution(df, ["split"])
sarcasm_variety = binary_distribution(df, ["variety"])
sarcasm_source = binary_distribution(df, ["source"])
sarcasm_cell = binary_distribution(df, ["variety", "source"])
sarcasm_full = binary_distribution(df, ["split", "variety", "source"])

tables = {
    "sarcasm_distribution_overall.csv": sarcasm_overall,
    "sarcasm_distribution_by_split.csv": sarcasm_split,
    "sarcasm_distribution_by_variety.csv": sarcasm_variety,
    "sarcasm_distribution_by_source.csv": sarcasm_source,
    "sarcasm_distribution_by_variety_source.csv": sarcasm_cell,
    "sarcasm_distribution_by_split_variety_source.csv": sarcasm_full,
}
for filename, table in tables.items():
    table.to_csv(OUTPUT_DIR / filename, index=False)

display(Markdown("### Overall"))
display(with_percent_strings(sarcasm_overall, ["rate"]))
display(Markdown("### By project split"))
display(with_percent_strings(sarcasm_split, ["rate"]))
display(Markdown("### By English variety"))
display(with_percent_strings(sarcasm_variety, ["rate"]))
display(Markdown("### By source"))
display(with_percent_strings(sarcasm_source, ["rate"]))
display(Markdown("### Complete variety × source distribution"))
display(with_percent_strings(sarcasm_cell, ["rate"]))
display(Markdown("### Full split × variety × source support"))
display(with_percent_strings(sarcasm_full, ["rate"]))
"""
        ),
        md(
            """
### Show the sarcasm imbalance

The heatmap puts the imbalance in one view. Each square shows both the rate and raw positive count, so the tiny Google-positive groups are not hidden behind percentages.
"""
        ),
        code(
            """
rate_matrix = sarcasm_cell.pivot(index="variety", columns="source", values="rate").reindex(index=VARIETY_ORDER, columns=SOURCE_ORDER)
positive_matrix = sarcasm_cell.pivot(index="variety", columns="source", values="sarcastic").reindex(index=VARIETY_ORDER, columns=SOURCE_ORDER)
total_matrix = sarcasm_cell.pivot(index="variety", columns="source", values="total").reindex(index=VARIETY_ORDER, columns=SOURCE_ORDER)
annotations = rate_matrix.copy().astype(object)
for variety in VARIETY_ORDER:
    for source in SOURCE_ORDER:
        annotations.loc[variety, source] = f"{rate_matrix.loc[variety, source]:.1%}\\n{positive_matrix.loc[variety, source]}/{total_matrix.loc[variety, source]}"

fig, ax = plt.subplots(figsize=(7.2, 4.8))
sns.heatmap(rate_matrix * 100, annot=annotations, fmt="", cmap="YlOrRd", vmin=0, vmax=45, cbar_kws={"label": "Sarcastic (%)"}, ax=ax)
ax.set_title("Sarcasm varies strongly by variety and source")
ax.set_xlabel("Source")
ax.set_ylabel("English variety")
save_figure(fig, "sarcasm_rate_by_variety_source")
plt.show()
"""
        ),
        md(
            """
## 7. Decide what the sarcasm data can support

The next table turns those counts into guidance for each segment. Sarcasm modelling, evaluation and the application can read it directly. These cut-offs are cautious rules for this project, not universal statistical laws:

- `test positives = 0`: positive-class recall/F1/PR-AUC are not estimable.
- `train positives < 20`: do not train a standalone segment model.
- `test positives < 5`: report support and descriptive behaviour only; avoid comparative claims.
- Every subgroup metric must display positive and total support.
"""
        ),
        code(
            """
support = sarcasm_full.pivot_table(
    index=["variety", "source"], columns="split", values=["sarcastic", "total"], aggfunc="first"
).reset_index()
support.columns = ["_".join([str(part) for part in col if str(part)]) if isinstance(col, tuple) else col for col in support.columns]

def support_recommendation(row):
    train_pos = row["sarcastic_train"]
    test_pos = row["sarcastic_test"]
    if train_pos < 20 and test_pos == 0:
        return "No standalone model; use shared global model, show limited-evidence warning, report false-positive behaviour only"
    if train_pos < 20:
        return "No standalone model; shared model only, descriptive subgroup metrics with support"
    if test_pos < 5:
        return "Shared model; subgroup comparison is unstable and descriptive only"
    return "Shared model is primary; subgroup metrics allowed with support and uncertainty"

support["recommendation"] = support.apply(support_recommendation, axis=1)
support.to_csv(OUTPUT_DIR / "sarcasm_segment_support_recommendations.csv", index=False)
display(support)

assert int(support.query("variety == 'en-UK' and source == 'google'")["sarcastic_train"].iloc[0]) == 1
assert int(support.query("variety == 'en-UK' and source == 'google'")["sarcastic_validation"].iloc[0]) == 0
assert int(support.query("variety == 'en-UK' and source == 'google'")["sarcastic_test"].iloc[0]) == 0
"""
        ),
        md(
            """
### What the sarcasm modelling work should do

The Google data needs special care: it has only 88 sarcastic examples in total. `en-UK Google` has one positive example in train and none in validation or test; `en-IN Google` is also very sparse.

1. Train one shared sarcasm model across all varieties and sources. Do not train separate Google models for en-UK or en-IN.
2. Compare a normal baseline with a class-weighted version. Calculate weights from the training split only.
3. Choose any probability or review threshold on validation only, then run the test set once.
4. Report macro-F1, sarcastic precision/recall/F1, PR-AUC, balanced accuracy and confusion matrices. Accuracy alone will hide the imbalance.
5. Show overall, per-variety and per-source results. Add `variety × source` results only with their positive and total counts.
6. For `en-UK Google` test, positive-class recall, F1 and PR-AUC are not measurable because there are no positive cases. Show them as `N/A`, not zero. Report false positives, false-positive rate, specificity and predicted-positive rate instead.
7. In the application, use the shared model for sparse Google segments and show a short `Limited segment evidence` warning. Send predicted-positive cases to human review rather than presenting them as certain.
"""
        ),
        md(
            """
## 8. What the EDA means for the system design

The results point to a review tool for customer and social-media text, not a nationality detector:

```text
Single text or batch CSV
        |
        v
Schema/privacy validation ---- known source and optional market context
        |
        v
English-variety classifier ---- calibrated probabilities
        |
        +---- low confidence ---> global fallback + human-review flag
        |
        v
Global sentiment/sarcasm models
        +---- compare with variety-aware or routed models
        |
        v
Source-aware dashboard
        +---- variety/source support shown
        +---- model disagreement shown
        +---- limited-evidence warnings
        +---- review queue and export
```

Why this architecture follows from the EDA:

- Unequal `variety × source` counts require support-aware dashboards and evaluation.
- Strong source-specific label rates require per-source metrics and shortcut diagnostics.
- Severe sarcasm imbalance requires macro/positive-class metrics, class weighting and threshold evaluation.
- Sparse segments require shared models, fallback behaviour and honest reliability warnings.
- Long-tailed text lengths require documented truncation/feature decisions and length-stratified error analysis.

The next steps and role-based work packages are in [`docs/EDA_TO_HD_IMPLEMENTATION_PLAN.md`](../docs/EDA_TO_HD_IMPLEMENTATION_PLAN.md).
"""
        ),
        md(
            """
## 9. Files created by this notebook

The final list is a quick check that everything was written. Later code can read the CSV tables directly, and every figure is available as both PNG and SVG under:

`reports/eda/notebook_outputs/`

The prepared task files live under `data/processed/by_task/`. Modelling can use them as they are; evaluation should join predictions by `id`; and the application should use the saved support table when it decides whether to show a limited-evidence warning.
"""
        ),
        code(
            """
generated = sorted(path.relative_to(ROOT).as_posix() for path in OUTPUT_DIR.rglob("*") if path.is_file())
print(f"Generated {len(generated)} reusable notebook artefacts:\\n")
print("\\n".join(f"- {path}" for path in generated))
"""
        ),
    ]

    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            assert index > 0 and notebook["cells"][index - 1]["cell_type"] == "markdown", (
                f"Code cell {index} needs a short explanation immediately before it."
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
