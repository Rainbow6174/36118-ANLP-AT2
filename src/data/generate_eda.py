"""Generate the shared EDA tables, figures and report text."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from .data_contract import SOURCES, SPLITS, VARIETIES
    from .data_utils import load_records
except ImportError:
    from data_contract import SOURCES, SPLITS, VARIETIES
    from data_utils import load_records


COLORS = ["#2E74B5", "#E07A5F", "#2E6B57", "#7A5195"]


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def percentile(values: list[int], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def svg_bar_chart(
    path: Path,
    title: str,
    categories: list[str],
    series: list[tuple[str, list[float]]],
    y_label: str,
    percentage: bool = False,
) -> None:
    width, height = 1200, 680
    left, right, top, bottom = 105, 55, 95, 120
    chart_w, chart_h = width - left - right, height - top - bottom
    max_value = max((value for _, values in series for value in values), default=1)
    ceiling = 1.0 if percentage else max(1.0, max_value * 1.12)
    group_width = chart_w / max(1, len(categories))
    bar_width = min(64, group_width * 0.72 / max(1, len(series)))

    items = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<text x="{left}" y="42" font-family="Calibri,Arial,sans-serif" font-size="28" font-weight="700" fill="#0B2545">{escape(title)}</text>',
        f'<text x="24" y="{top + chart_h / 2}" transform="rotate(-90 24 {top + chart_h / 2})" font-family="Calibri,Arial,sans-serif" font-size="16" fill="#5D6875">{escape(y_label)}</text>',
    ]
    for tick in range(6):
        value = ceiling * tick / 5
        y = top + chart_h - chart_h * value / ceiling
        label = f"{value * 100:.0f}%" if percentage else f"{value:.0f}"
        items.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="#DCE3EA" stroke-width="1"/>')
        items.append(f'<text x="{left - 12}" y="{y + 5:.1f}" text-anchor="end" font-family="Calibri,Arial,sans-serif" font-size="14" fill="#5D6875">{label}</text>')

    for cat_index, category in enumerate(categories):
        group_center = left + (cat_index + 0.5) * group_width
        total_series_width = bar_width * len(series)
        start_x = group_center - total_series_width / 2
        for series_index, (_, values) in enumerate(series):
            value = values[cat_index]
            bar_h = chart_h * value / ceiling
            x = start_x + series_index * bar_width
            y = top + chart_h - bar_h
            items.append(f'<rect x="{x + 3:.1f}" y="{y:.1f}" width="{bar_width - 6:.1f}" height="{bar_h:.1f}" rx="4" fill="{COLORS[series_index % len(COLORS)]}"/>')
            value_label = f"{value * 100:.1f}%" if percentage else f"{value:.0f}"
            items.append(f'<text x="{x + bar_width / 2:.1f}" y="{max(top + 14, y - 7):.1f}" text-anchor="middle" font-family="Calibri,Arial,sans-serif" font-size="13" fill="#263442">{value_label}</text>')
        items.append(f'<text x="{group_center:.1f}" y="{top + chart_h + 30}" text-anchor="middle" font-family="Calibri,Arial,sans-serif" font-size="15" fill="#263442">{escape(category)}</text>')

    legend_x = left
    legend_y = height - 38
    for index, (name, _) in enumerate(series):
        x = legend_x + index * 220
        items.append(f'<rect x="{x}" y="{legend_y - 13}" width="16" height="16" rx="2" fill="{COLORS[index % len(COLORS)]}"/>')
        items.append(f'<text x="{x + 24}" y="{legend_y}" font-family="Calibri,Arial,sans-serif" font-size="15" fill="#263442">{escape(name)}</text>')
    items.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(items), encoding="utf-8")


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    output.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def generate(project_root: Path) -> dict:
    rows = load_records(root=project_root)
    eda_dir = project_root / "reports" / "eda" / "summary"
    figure_dir = eda_dir / "figures"
    eda_dir.mkdir(parents=True, exist_ok=True)

    count_rows = []
    for split in SPLITS:
        for variety in VARIETIES:
            for source in SOURCES:
                count_rows.append(
                    {
                        "split": split,
                        "variety": variety,
                        "source": source,
                        "count": sum(1 for row in rows if row["split"] == split and row["variety"] == variety and row["source"] == source),
                    }
                )
    write_csv(eda_dir / "counts_by_split_variety_source.csv", count_rows, ["split", "variety", "source", "count"])

    label_rows = []
    for split in ("all",) + SPLITS:
        selected = rows if split == "all" else [row for row in rows if row["split"] == split]
        for variety in VARIETIES:
            for source in SOURCES:
                subset = [row for row in selected if row["variety"] == variety and row["source"] == source]
                for task in ("sentiment", "sarcasm"):
                    positive = sum(row[task] == 1 for row in subset)
                    label_rows.append(
                        {
                            "split": split,
                            "variety": variety,
                            "source": source,
                            "task": task,
                            "n": len(subset),
                            "negative_or_non_sarcastic": len(subset) - positive,
                            "positive_or_sarcastic": positive,
                            "positive_rate": round(positive / len(subset), 6) if subset else 0,
                        }
                    )
    write_csv(
        eda_dir / "label_distribution.csv",
        label_rows,
        ["split", "variety", "source", "task", "n", "negative_or_non_sarcastic", "positive_or_sarcastic", "positive_rate"],
    )

    length_rows = []
    for variety in VARIETIES:
        for source in SOURCES:
            subset = [row for row in rows if row["variety"] == variety and row["source"] == source]
            for field in ("word_count", "char_count"):
                values = [row[field] for row in subset]
                length_rows.append(
                    {
                        "variety": variety,
                        "source": source,
                        "measure": field,
                        "n": len(values),
                        "mean": round(statistics.fmean(values), 2),
                        "median": round(statistics.median(values), 2),
                        "p95": round(percentile(values, 0.95), 2),
                        "max": max(values),
                    }
                )
    write_csv(eda_dir / "text_length_summary.csv", length_rows, ["variety", "source", "measure", "n", "mean", "median", "p95", "max"])

    missing_rows = []
    for field in ("id", "text", "variety", "source", "sentiment", "sarcasm", "split"):
        missing = sum(row.get(field) in (None, "") for row in rows)
        missing_rows.append({"field": field, "missing": missing, "missing_rate": round(missing / len(rows), 6)})
    write_csv(eda_dir / "missingness.csv", missing_rows, ["field", "missing", "missing_rate"])

    split_counts = Counter(row["split"] for row in rows)
    variety_counts = Counter(row["variety"] for row in rows)
    source_counts = Counter(row["source"] for row in rows)
    cell_counts = Counter((row["variety"], row["source"]) for row in rows)
    categories = list(VARIETIES)
    svg_bar_chart(
        figure_dir / "dataset_size_by_variety_source.svg",
        "BESSTIE sample size after quality control",
        categories,
        [("Google", [cell_counts[(v, "google")] for v in categories]), ("Reddit", [cell_counts[(v, "reddit")] for v in categories])],
        "Number of texts",
    )

    label_lookup = {(item["variety"], item["source"], item["task"]): item["positive_rate"] for item in label_rows if item["split"] == "all"}
    rate_categories = [f"{v}-{s.title()}" for v in VARIETIES for s in SOURCES]
    svg_bar_chart(
        figure_dir / "positive_label_rates.svg",
        "Positive sentiment and sarcasm rates by variety and source",
        rate_categories,
        [
            ("Positive sentiment", [label_lookup[(v, s, "sentiment")] for v in VARIETIES for s in SOURCES]),
            ("Sarcastic", [label_lookup[(v, s, "sarcasm")] for v in VARIETIES for s in SOURCES]),
        ],
        "Share of texts",
        percentage=True,
    )

    quality_report_path = project_root / "data" / "processed" / "quality_report.json"
    quality_report = json.loads(quality_report_path.read_text(encoding="utf-8"))
    total = len(rows)
    overall_sentiment_rate = sum(row["sentiment"] for row in rows) / total
    overall_sarcasm_rate = sum(row["sarcasm"] for row in rows) / total
    largest_variety = max(VARIETIES, key=lambda value: variety_counts[value])
    smallest_variety = min(VARIETIES, key=lambda value: variety_counts[value])

    summary = {
        "total_rows": total,
        "split_counts": dict(split_counts),
        "variety_counts": dict(variety_counts),
        "source_counts": dict(source_counts),
        "overall_positive_sentiment_rate": round(overall_sentiment_rate, 6),
        "overall_sarcasm_rate": round(overall_sarcasm_rate, 6),
        "largest_variety": largest_variety,
        "smallest_variety": smallest_variety,
        "rows_removed": quality_report["rows_removed"],
        "removal_reasons": quality_report["removal_reasons"],
    }
    (eda_dir / "eda_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    count_table = [
        [split, split_counts[split], f"{split_counts[split] / total:.1%}"] for split in SPLITS
    ]
    variety_table = [
        [variety, variety_counts[variety], f"{variety_counts[variety] / total:.1%}"] for variety in VARIETIES
    ]
    rate_table = [
        [
            variety,
            source.title(),
            f"{label_lookup[(variety, source, 'sentiment')]:.1%}",
            f"{label_lookup[(variety, source, 'sarcasm')]:.1%}",
            int(cell_counts[(variety, source)]),
        ]
        for variety in VARIETIES
        for source in SOURCES
    ]
    word_median = {
        (item["variety"], item["source"]): item["median"]
        for item in length_rows
        if item["measure"] == "word_count"
    }
    longest_cell = max(word_median, key=word_median.get)
    shortest_cell = min(word_median, key=word_median.get)

    report = f"""# Data Sources, Preparation and Initial Analysis

## Data source and suitability

The project uses BESSTIE, a manually annotated benchmark for sentiment and sarcasm classification across Australian (`en-AU`), Indian (`en-IN`) and British (`en-UK`) English. The public release contains Google Places reviews and Reddit comments. These two domains support the proposed customer/social-insights workflow while also making domain and English-variety performance differences measurable.

Official dataset: <https://huggingface.co/datasets/unswnlporg/BESSTIE>  
Paper: Srirag et al. (2025), <https://aclanthology.org/2025.findings-acl.441/>

## Reproducible preparation

The pipeline downloads six official CSV files: train and validation files for each of the three varieties. Because the public release does not expose its test set, the official validation split is used once as the project's held-out test set. The official train split is divided into project train and validation subsets using seed `{quality_report['configuration']['random_seed']}` and a `{quality_report['configuration']['validation_fraction_from_official_train']:.0%}` validation target. Stratification uses the joint combination of variety, source, sentiment and sarcasm so that the small sarcasm class is represented across development splits.

Cleaning is intentionally minimal. Leading and trailing whitespace is removed and internal whitespace is collapsed, while case, spelling, punctuation, emoji, hashtags and regional expressions are retained. Exact/case-only duplicate text is detected after Unicode NFKC normalisation and case-folding. Conflicting-label duplicate groups are removed. For a duplicate appearing in both official train and validation, the validation example is retained and the train copy is removed, preventing text leakage into the project test set. No fuzzy deduplication is used because it could remove meaningful variety-specific wording.

## Dataset after quality control

{markdown_table(['Project split', 'Rows', 'Share'], count_table)}

{markdown_table(['English variety', 'Rows', 'Share'], variety_table)}

The processed corpus contains **{total:,} texts**. `{largest_variety}` is the largest variety subset and `{smallest_variety}` is the smallest, so overall accuracy alone would allow the larger groups to dominate the result. The evaluation must therefore report macro-F1 and per-variety results. Google contributes **{source_counts['google']:,}** texts and Reddit contributes **{source_counts['reddit']:,}** texts, requiring per-source analysis rather than assuming one domain represents the other.

Positive sentiment accounts for **{overall_sentiment_rate:.1%}** of all retained texts. Sarcastic texts account for only **{overall_sarcasm_rate:.1%}**, confirming material class imbalance for sarcasm. Model owners should use stratified training, macro-F1, per-class precision/recall and class weighting or threshold analysis rather than accuracy alone.

Quality control removed **{quality_report['rows_removed']:,} rows**. The exact reasons and affected row IDs are recorded in `data/processed/audit/removed_rows.csv`; no manual or undocumented deletion is performed. The final validation report confirms unique IDs, valid labels, complete variety/source coverage and zero exact text overlap between train, validation and test.

## Key EDA findings and modelling consequences

{markdown_table(['Variety', 'Source', 'Positive sentiment', 'Sarcastic', 'N'], rate_table)}

The strongest pattern is a **source-label interaction**. Google positive-sentiment rates are approximately 74% for all three varieties, whereas Reddit positive rates range from {min(label_lookup[(v, 'reddit', 'sentiment')] for v in VARIETIES):.1%} to {max(label_lookup[(v, 'reddit', 'sentiment')] for v in VARIETIES):.1%}. Sarcasm is extremely rare in Google reviews for en-IN and en-UK but substantially more common on Reddit, especially for en-AU. A model can therefore achieve deceptively strong aggregate results by learning domain cues rather than robust sentiment or sarcasm cues. Every model comparison should report both per-variety and per-source metrics, and the error analysis should examine source-specific failures.

Text length also varies by cell: the median ranges from **{word_median[shortest_cell]:.0f} words** for `{shortest_cell[0]}` `{shortest_cell[1]}` to **{word_median[longest_cell]:.0f} words** for `{longest_cell[0]}` `{longest_cell[1]}`. Transformer truncation length and traditional-model features should therefore be documented and tested rather than chosen without evidence.

These are descriptive dataset findings, not claims about all speakers of the three English varieties. The observed differences may reflect platform, topic and collection choices as well as linguistic variation.

## Handoff to the team

- Sentiment modelling: `data/processed/by_task/sentiment/{{train,validation,test}}.csv`
- Sarcasm modelling: `data/processed/by_task/sarcasm/{{train,validation,test}}.csv`
- Variety and cross-variety work: `data/processed/by_task/variety/` and the full split files
- Common schema: `id,text,variety,source,sentiment,sarcasm,official_split,split,char_count,word_count`
- Test policy: the project test split must not be used for hyperparameter tuning, threshold selection or feature decisions

## Limitations and responsible use

Variety is assigned from collection context and annotation design; it is not a reliable indicator of a writer's identity or nationality. The corpus covers only three English varieties and two online domains, and it may contain topical, demographic and platform-specific biases. Results should be described as performance on BESSTIE subsets, not as universal performance for all Australian, Indian or British English speakers. User-provided text should not be stored or used for training without an explicit consent and privacy process.

## Data and EDA contribution

This work covers sourcing the official BESSTIE data, building the preparation pipeline, defining the shared dataset contract, creating leakage-safe project splits, recording cleaning and deduplication decisions, checking data quality, completing the initial analysis, and producing reusable task files and figures for the report and poster.
"""
    report_dir = project_root / "reports" / "eda"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "data_section.md").write_text(report, encoding="utf-8")

    card = f"""# BESSTIE Project Data Card

## Summary

- **Dataset:** BESSTIE
- **Project rows after QC:** {total:,}
- **Varieties:** en-AU, en-IN, en-UK
- **Sources:** Google Places reviews and Reddit comments
- **Labels:** sentiment (0 negative, 1 positive); sarcasm (0 non-sarcastic, 1 sarcastic)
- **Official repository:** <https://huggingface.co/datasets/unswnlporg/BESSTIE>
- **License shown by the official repository at retrieval:** CC BY 4.0
- **Project split seed:** {quality_report['configuration']['random_seed']}

## Split construction

The public official validation split becomes the project test split. A stratified {quality_report['configuration']['validation_fraction_from_official_train']:.0%} sample of the official train split becomes the project validation split; the remainder becomes project train. The held-out project test set is not for tuning.

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
"""
    (report_dir / "DATA_CARD.md").write_text(card, encoding="utf-8")

    handoff = """# Using the Prepared Dataset

Use the task views under `data/processed/by_task/`. Every task file has exactly five columns:

`id,text,variety,source,label`

- Sentiment modelling uses `by_task/sentiment/`.
- Sarcasm modelling uses `by_task/sarcasm/`.
- Variety modelling uses `by_task/variety/`; the full split files are available for cross-task experiments.
- Evaluation joins predictions to the gold data using `id`, never row order.
- The application reads model artefacts and can use `variety` and `source` for filters and warnings.

Do not tune on `test.csv`. If a model needs different text cleaning or tokenisation, keep it inside that model's code and document it. Do not overwrite the shared text or split files.
"""
    (report_dir / "DATA_HANDOFF.md").write_text(handoff, encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[2])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(generate(args.project_root.resolve()), indent=2))


if __name__ == "__main__":
    main()
