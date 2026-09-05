from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.data_contract import REQUIRED_COLUMNS, clean_text, duplicate_key
from src.data.prepare_besstie import assign_project_splits, deduplicate
from src.data.validate_besstie import validate


class DataContractTests(unittest.TestCase):
    def test_clean_text_preserves_linguistic_signals(self):
        value = "  Yeah!!!\n  Great job 🙃  "
        self.assertEqual(clean_text(value), "Yeah!!! Great job 🙃")

    def test_duplicate_key_is_case_and_whitespace_insensitive(self):
        self.assertEqual(duplicate_key(" Good   DAY "), duplicate_key("good day"))


class SplitTests(unittest.TestCase):
    @staticmethod
    def row(identifier: str, official_split: str, text: str, sentiment: int = 1, sarcasm: int = 0) -> dict:
        return {
            "id": identifier,
            "text": text,
            "variety": "en-AU",
            "source": "google",
            "sentiment": sentiment,
            "sarcasm": sarcasm,
            "official_split": official_split,
            "_duplicate_key": duplicate_key(text),
            "_raw_row": int(identifier.rsplit("-", 1)[-1]),
        }

    def test_deduplication_prefers_official_validation(self):
        removed = []
        rows = [
            self.row("row-1", "train", "Same text"),
            self.row("row-2", "validation", "same   text"),
        ]
        kept = deduplicate(rows, removed)
        self.assertEqual([item["id"] for item in kept], ["row-2"])
        self.assertEqual(removed[0]["duplicate_of"], "row-2")

    def test_conflicting_duplicate_group_is_removed(self):
        removed = []
        rows = [
            self.row("row-1", "train", "Same text", sentiment=1),
            self.row("row-2", "train", "same text", sentiment=0),
        ]
        self.assertEqual(deduplicate(rows, removed), [])
        self.assertEqual({item["reason"] for item in removed}, {"conflicting_duplicate_labels"})

    def test_split_is_deterministic_and_official_validation_becomes_test(self):
        rows = [self.row(f"row-{index}", "train", f"text {index}") for index in range(1, 21)]
        rows.append(self.row("row-21", "validation", "held out"))
        first = assign_project_splits([dict(item) for item in rows], 0.15, 36118)
        second = assign_project_splits([dict(item) for item in rows], 0.15, 36118)
        self.assertEqual([(item["id"], item["split"]) for item in first], [(item["id"], item["split"]) for item in second])
        self.assertEqual(next(item for item in first if item["id"] == "row-21")["split"], "test")


class GeneratedDatasetTests(unittest.TestCase):
    @unittest.skipUnless((PROJECT_ROOT / "data" / "processed" / "dataset_v1.csv").exists(), "run pipeline first")
    def test_generated_dataset_passes_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            report = validate(
                PROJECT_ROOT / "data" / "processed" / "dataset_v1.csv",
                Path(directory) / "validation.json",
            )
            self.assertTrue(report["passed"])

    @unittest.skipUnless((PROJECT_ROOT / "data" / "processed" / "dataset_v1.csv").exists(), "run pipeline first")
    def test_task_files_match_split_sizes(self):
        dataset_path = PROJECT_ROOT / "data" / "processed" / "dataset_v1.csv"
        with dataset_path.open("r", encoding="utf-8", newline="") as stream:
            main_rows = list(csv.DictReader(stream))
        for task in ("sentiment", "sarcasm", "variety"):
            for split in ("train", "validation", "test"):
                task_path = PROJECT_ROOT / "data" / "processed" / "by_task" / task / f"{split}.csv"
                with task_path.open("r", encoding="utf-8", newline="") as stream:
                    task_rows = list(csv.DictReader(stream))
                expected = sum(row["split"] == split for row in main_rows)
                self.assertEqual(len(task_rows), expected, f"{task}/{split}")

    @unittest.skipUnless((PROJECT_ROOT / "reports" / "eda" / "summary" / "figures").exists(), "run pipeline first")
    def test_generated_svg_figures_are_valid_xml(self):
        figure_dir = PROJECT_ROOT / "reports" / "eda" / "summary" / "figures"
        figures = sorted(figure_dir.glob("*.svg"))
        self.assertGreaterEqual(len(figures), 2)
        for figure in figures:
            root = ET.parse(figure).getroot()
            self.assertTrue(root.tag.endswith("svg"), figure.name)


if __name__ == "__main__":
    unittest.main()
