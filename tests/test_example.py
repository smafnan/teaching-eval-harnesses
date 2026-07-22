"""Minimal, stdlib-only tests for example.py: run_eval + the compare() gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from example import CASES, compare, run_eval, system_v1, system_v2

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_run_eval_v1_is_perfect():
    scores, mean = run_eval(system_v1)
    assert scores == {cid: 1.0 for cid in (c["id"] for c in CASES)}
    assert mean == 1.0


def test_run_eval_v2_has_seeded_japan_bug():
    scores, mean = run_eval(system_v2)
    assert scores["japan"] == 0.0
    assert scores["france"] == 1.0
    assert scores["italy"] == 1.0
    assert mean < 1.0


def test_compare_detects_regression():
    base_scores, _ = run_eval(system_v1)
    cand_scores, _ = run_eval(system_v2)
    diff = compare(base_scores, cand_scores)
    assert diff["regressed"] == ["japan"]
    assert diff["missing"] == []
    assert diff["extra"] == []


def test_compare_no_regression_when_scores_equal():
    scores, _ = run_eval(system_v1)
    diff = compare(scores, dict(scores))
    assert diff == {"regressed": [], "missing": [], "extra": []}


def test_compare_handles_mismatched_case_ids_without_keyerror():
    baseline = {"a": 1.0, "b": 1.0, "c": 0.5}
    candidate = {"b": 0.0, "c": 0.5, "d": 1.0}

    diff = compare(baseline, candidate)

    # "a" only exists in baseline, "d" only exists in candidate: neither can
    # be diffed for regression, but both must be surfaced, not raise KeyError.
    assert diff["missing"] == ["a"]
    assert diff["extra"] == ["d"]
    # Only the shared case that actually got worse ("b") is a regression.
    assert diff["regressed"] == ["b"]


def test_example_script_exits_1_and_reports_regression():
    result = subprocess.run(
        [sys.executable, "example.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "REGRESSION DETECTED in: japan" in result.stdout
