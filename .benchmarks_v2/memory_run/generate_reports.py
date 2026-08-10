"""Generate reports for the memory benchmark results."""
import sys
sys.path.insert(0, r"C:\GitHub\memoriX")

import json
from pathlib import Path
from collections import defaultdict

from benchmarks_v2.orchestrator.data_models import AggregateReport
from benchmarks_v2.reporting.report_generator import ReportGenerator
from benchmarks_v2.reporting.figures import FigureGenerator

raw_path = Path(r"C:\GitHub\memoriX\.benchmarks_v2\memory_run\memory-benchmark-results\raw_results.json")
raw_data = json.loads(raw_path.read_text(encoding="utf-8"))

family_groups = defaultdict(list)
for r in raw_data:
    family_groups[r["family"]].append(r)

aggregate_reports = []
for fam, runs in sorted(family_groups.items()):
    precisions = [r.get("passed_case_count", 0) / max(r.get("case_count", 1), 1) for r in runs]
    latencies = [r.get("llm_ms", 0) for r in runs]
    passed = sum(1 for r in runs if r.get("passed"))
    total = len(runs)
    aggregate_reports.append(AggregateReport(
        schema_version=1,
        campaign_id="memory-benchmark",
        family=fam,
        suite="standard",
        precision=sum(precisions) / max(len(precisions), 1),
        recall=sum(precisions) / max(len(precisions), 1),
        f1=sum(precisions) / max(len(precisions), 1),
        pass_rate=passed / max(total, 1),
        total_runs=total,
        failed_runs=total - passed,
        median_latency=sorted(latencies)[len(latencies) // 2] if latencies else 0,
        p95_latency=sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
    ))

families = sorted(set(r["family"] for r in raw_data))
output_dir = Path(r"C:\GitHub\memoriX\.benchmarks_v2\memory_run")

gen = ReportGenerator(output_dir)
md = gen.generate("memory-benchmark", "standard", families, aggregate_reports, raw_data)
print(f"MD: {md}")

try:
    docx = gen.generate_docx("memory-benchmark", "standard", families, aggregate_reports)
    print(f"DOCX: {docx}")
except Exception as e:
    print(f"DOCX error: {e}")

try:
    fig_dir = output_dir / "memory-benchmark"
    fig_dir.mkdir(parents=True, exist_ok=True)
    figs = FigureGenerator(fig_dir)
    figs.generate_all("memory-benchmark", aggregate_reports, raw_data)
    print(f"PNG: {fig_dir / 'figures'}")
except Exception as e:
    print(f"PNG error: {e}")

print("Done.")
