"""Measure WCAG 2.2 contrast ratios for the CrisisLens interface colours.

Reads the design tokens in app/frontend/styles/tokens.css and the category
colours in app/frontend/constants/labels.py, computes the contrast ratio of
every text/background pair the interface uses, and writes the results to
outputs/results/system/contrast_check.csv.

Run from the repository root:

    python scripts/check_contrast.py

The exit code is 1 when any pair is below the 4.5:1 AA target for normal text.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "app" / "frontend" / "styles" / "tokens.css"
OUTPUT = ROOT / "outputs" / "results" / "system" / "contrast_check.csv"
AA_NORMAL_TEXT = 4.5

# (text token, background token, where the pair appears)
TOKEN_PAIRS = [
    ("--color-text-main", "--color-background", "Body text on the page"),
    ("--color-text-main", "--color-surface", "Body text on cards"),
    ("--color-text-secondary", "--color-background", "Secondary text on the page"),
    ("--color-text-secondary", "--color-surface", "Secondary text on cards"),
    ("--color-text-secondary", "--color-notice-soft", "Safety line under the header"),
    ("--color-text-main", "--color-header-background", "Navigation text"),
    ("--color-primary", "--color-surface", "Links and outline buttons"),
    ("--color-primary", "--color-primary-soft", "Primary soft chips"),
    ("#FFFFFF", "--color-primary", "Text on primary buttons"),
    ("--color-review", "--color-review-soft", "Category needs review badge and alerts"),
    ("--color-error", "--color-error-soft", "Error messages"),
    ("--color-success", "--color-success-soft", "Category reviewed badge"),
    ("--color-urgent", "--color-surface", "Urgent Needs accent"),
]


def read_tokens(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    root_block = text[text.index(":root") : text.index("}", text.index(":root"))]
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})", root_block))


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def collect_pairs() -> list[dict]:
    tokens = read_tokens(TOKENS)

    def resolve(name: str) -> str:
        return name if name.startswith("#") else tokens[name]

    rows = []
    for fg, bg, usage in TOKEN_PAIRS:
        rows.append({"usage": usage, "text": fg, "background": bg,
                     "text_hex": resolve(fg), "background_hex": resolve(bg)})

    sys.path.insert(0, str(ROOT / "app" / "frontend"))
    from constants.labels import LABEL_COLORS

    for label, (bg_hex, fg_hex) in LABEL_COLORS.items():
        rows.append({"usage": f"Category badge: {label}", "text": "label text",
                     "background": "label background",
                     "text_hex": fg_hex, "background_hex": bg_hex})
    for row in rows:
        row["ratio"] = round(contrast(row["text_hex"], row["background_hex"]), 2)
        row["passes_aa_normal_text"] = row["ratio"] >= AA_NORMAL_TEXT
    return rows


def main() -> int:
    rows = collect_pairs()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    failures = [r for r in rows if not r["passes_aa_normal_text"]]
    lowest = min(rows, key=lambda r: r["ratio"])
    print(f"{len(rows)} colour pairs checked; lowest ratio {lowest['ratio']}:1 "
          f"({lowest['usage']}).")
    for row in failures:
        print(f"Below 4.5:1: {row['usage']} {row['text_hex']} on "
              f"{row['background_hex']} = {row['ratio']}:1")
    print(f"Results written to {OUTPUT.relative_to(ROOT)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
