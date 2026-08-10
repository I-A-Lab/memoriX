#!/usr/bin/env python3
"""Consolidate the 5 BFCL campaign reports into bfcl_summary.json."""
from __future__ import annotations
import json
from pathlib import Path

RUN_ROOT = Path(r"C:\GitHub\memoriX\.benchmarks_v2\bfcl_run")
CAMPAIGNS = ("canary", "pilot5", "pilot25", "blind", "robustness")

def load_campaign(name: str) -> dict:
    path = RUN_ROOT / name / f"{name}_report.json"
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> None:
    campaigns = {}
    for name in CAMPAIGNS:
        data = load_campaign(name)
        campaigns[name] = data["summary"]
    summary = {
        "schema_version": 1,
        "scale": 5,
        "model": "qwen2.5:3b",
        "consolidated": True,
        "campaigns": campaigns,
    }
    out = RUN_ROOT / "bfcl_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("=" * 60)
    print("BFCL CONSOLIDATED SUMMARY (scale x5)")
    print("=" * 60)
    c = campaigns["canary"]
    print(f"Canary:      baseline {c['baseline_correct']}/{c['total_pairs']} memoriX {c['memorix_correct']}/{c['total_pairs']} ({c['rate_memorix']:.1%})")
    p5 = campaigns["pilot5"]
    print(f"Pilot 5:     baseline {p5['baseline_correct']}/{p5['total_pairs']} memoriX {p5['memorix_correct']}/{p5['total_pairs']} ({p5['rate_memorix']:.1%})")
    p25 = campaigns["pilot25"]
    print(f"Pilot 25:    baseline {p25['baseline_correct']}/{p25['total_pairs']} memoriX {p25['memorix_correct']}/{p25['total_pairs']} ({p25['rate_memorix']:.1%})")
    b = campaigns["blind"]
    print(f"Blind:       corpus {b['corpus_contains_reference']}/{b['total_questions']} retrieval {b['retrieval_contains_reference']}/{b['total_questions']} answers {b['correct_answer']}/{b['total_questions']}")
    r = campaigns["robustness"]
    print(f"Robustness:  corpus {r['corpus_contains_reference']}/{r['total_runs']} retrieval {r['retrieval_contains_reference']}/{r['total_runs']} answers {r['correct_answer']}/{r['total_runs']} (3/3: {r['cases_successful_3of3']}, >=2/3: {r['cases_successful_at_least_2of3']})")
    print(f"Summary:     {out}")
    print("=" * 60)

if __name__ == "__main__":
    main()
