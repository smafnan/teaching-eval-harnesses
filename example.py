"""A minimal, dependency-free LLM evaluation harness — the article in ~60 lines.

It shows all four pieces: a labelled set, a scorer (here an LLM-as-judge stubbed
so it runs offline), aggregation, and a regression gate that catches a v1->v2
regression. Run it:  python example.py
"""

from __future__ import annotations

# 1) LABELLED TEST SET ------------------------------------------------------ #
CASES = [
    {"id": "france", "input": "Capital of France?", "reference": "Paris"},
    {"id": "japan", "input": "Capital of Japan?", "reference": "Tokyo"},
    {"id": "italy", "input": "Capital of Italy?", "reference": "Rome"},
]

# Two versions of the "system under test". v2 has a bug (wrong on Japan).
KB = {"Capital of France?": "Paris", "Capital of Japan?": "Tokyo",
      "Capital of Italy?": "Rome"}


def system_v1(q: str) -> str:
    return f"The answer is {KB.get(q, 'unknown')}."


def system_v2(q: str) -> str:                       # a 'refactor' broke Japan
    ans = "Kyoto" if "Japan" in q else KB.get(q, "unknown")
    return f"The answer is {ans}."


# 2) SCORER: an LLM-as-judge (stubbed deterministically for the demo). A real
#    one would call a model with a rubric and parse a JSON {"score": ...}.
def judge(output: str, reference: str) -> float:
    return 1.0 if reference.lower() in output.lower() else 0.0


# 3) AGGREGATE: run every case, score it, return {case_id: score} + the mean.
def run_eval(system) -> tuple[dict[str, float], float]:
    scores = {c["id"]: judge(system(c["input"]), c["reference"]) for c in CASES}
    mean = sum(scores.values()) / len(scores)
    return scores, mean


# 4) REGRESSION GATE: diff two runs case-by-case. Tolerates mismatched case
#    IDs (e.g. a case renamed or dropped between runs) instead of raising
#    KeyError — missing/extra cases are reported, not silently skipped.
def compare(baseline: dict[str, float], candidate: dict[str, float]) -> dict[str, list[str]]:
    shared = baseline.keys() & candidate.keys()
    return {
        "regressed": [cid for cid in shared if candidate[cid] < baseline[cid]],
        "missing": sorted(baseline.keys() - candidate.keys()),
        "extra": sorted(candidate.keys() - baseline.keys()),
    }


if __name__ == "__main__":
    base_scores, base_mean = run_eval(system_v1)
    cand_scores, cand_mean = run_eval(system_v2)

    print(f"v1 mean score: {base_mean:.3f}")
    print(f"v2 mean score: {cand_mean:.3f}")

    diff = compare(base_scores, cand_scores)
    if diff["missing"]:
        print(f"\nWARNING: missing from candidate: {', '.join(diff['missing'])}")
    if diff["extra"]:
        print(f"\nWARNING: extra in candidate (no baseline): {', '.join(diff['extra'])}")

    regressed = diff["regressed"]
    if regressed:
        print(f"\nREGRESSION DETECTED in: {', '.join(regressed)}")
        for cid in regressed:
            print(f"  {cid}: {base_scores[cid]:.2f} -> {cand_scores[cid]:.2f}")
        print("\n(A CI gate would fail the build here.)")
        raise SystemExit(1)
    print("\nNo regressions — safe to ship.")
