"""The interface colours meet the WCAG 2.2 AA 4.5:1 target claimed in the report."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_contrast.py"


def test_all_text_colour_pairs_reach_aa_contrast():
    spec = importlib.util.spec_from_file_location("check_contrast", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.collect_pairs()
    assert len(rows) >= 20
    failing = [(r["usage"], r["ratio"]) for r in rows if r["ratio"] < 4.5]
    assert not failing, failing
