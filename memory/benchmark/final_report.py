from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REPORT_VERSION = "40.1"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def _canonical_json_bytes(
    value: Any,
) -> bytes:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return (payload + "\n").encode("utf-8")


def _write_json(
    path: Path,
    value: Any,
) -> None:
    path.write_bytes(
        _canonical_json_bytes(value)
    )


def _ensure_empty(
    path: Path,
) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(
            "Refusing to overwrite non-empty final report directory: "
            f"{path}"
        )

    path.mkdir(
        parents=True,
        exist_ok=True,
    )


def _flatten_aggregates(
    multiseed_report: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    aggregates = multiseed_report["aggregates"]

    for mode in multiseed_report["modes"]:
        mode_metrics = aggregates[mode]

        for metric_name, summary in mode_metrics.items():
            rows.append(
                {
                    "mode": mode,
                    "metric": metric_name,
                    "count": int(summary["count"]),
                    "mean": float(summary["mean"]),
                    "median": float(summary["median"]),
                    "stdev": float(summary["stdev"]),
                    "min": float(summary["min"]),
                    "max": float(summary["max"]),
                    "ci95_low": float(
                        summary["ci95_low"]
                    ),
                    "ci95_high": float(
                        summary["ci95_high"]
                    ),
                }
            )

    return rows


def _comparison_rows(
    multiseed_report: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for comparison_name, metrics in (
        multiseed_report.get(
            "comparisons",
            {},
        ).items()
    ):
        for metric_name, delta in metrics.items():
            rows.append(
                {
                    "comparison": comparison_name,
                    "metric": metric_name,
                    "delta": float(delta),
                }
            )

    return rows


def _write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _build_markdown(
    multiseed_report: dict[str, Any],
    aggregate_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
) -> str:
    lines: list[str] = [
        "# memoriX Benchmark Report",
        "",
        f"- Report version: {REPORT_VERSION}",
        f"- Suite: {multiseed_report['suite']}",
        f"- Seeds: {', '.join(str(seed) for seed in multiseed_report['seeds'])}",
        f"- Modes: {', '.join(multiseed_report['modes'])}",
        f"- Runs: {multiseed_report['run_count']}",
        "",
        "## Aggregate metrics",
        "",
        "| Mode | Metric | Mean | Median | Std. dev. | 95% CI |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for row in aggregate_rows:
        lines.append(
            "| "
            + str(row["mode"])
            + " | "
            + str(row["metric"])
            + " | "
            + f"{row['mean']:.6f}"
            + " | "
            + f"{row['median']:.6f}"
            + " | "
            + f"{row['stdev']:.6f}"
            + " | ["
            + f"{row['ci95_low']:.6f}"
            + ", "
            + f"{row['ci95_high']:.6f}"
            + "] |"
        )

    lines.extend(
        [
            "",
            "## Comparisons",
            "",
            "| Comparison | Metric | Delta |",
            "|---|---:|---:|",
        ]
    )

    for row in comparison_rows:
        lines.append(
            "| "
            + str(row["comparison"])
            + " | "
            + str(row["metric"])
            + " | "
            + f"{row['delta']:.6f}"
            + " |"
        )

    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- Deterministic control runs validate the protocol.",
            "- They are not final scientific evidence.",
            "- Final conclusions require real multi-seed runs.",
            "- All generated artifacts must stay outside the repository.",
            "",
        ]
    )

    return "\n".join(lines)


def generate_final_report(
    *,
    multiseed_report_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    _ensure_empty(output_root)

    multiseed_report = _read_json(
        multiseed_report_path
    )

    if (
        multiseed_report.get(
            "orchestrator_version"
        )
        != "39.1"
    ):
        raise ValueError(
            "Unsupported multiseed report version"
        )

    aggregate_rows = _flatten_aggregates(
        multiseed_report
    )
    comparison_rows = _comparison_rows(
        multiseed_report
    )

    aggregate_csv = (
        output_root
        / "aggregate_metrics.csv"
    )
    comparison_csv = (
        output_root
        / "comparisons.csv"
    )
    chart_data_json = (
        output_root
        / "chart_data.json"
    )
    markdown_report = (
        output_root
        / "benchmark_report.md"
    )
    summary_json = (
        output_root
        / "final_report.json"
    )

    _write_csv(
        aggregate_csv,
        aggregate_rows,
        [
            "mode",
            "metric",
            "count",
            "mean",
            "median",
            "stdev",
            "min",
            "max",
            "ci95_low",
            "ci95_high",
        ],
    )

    _write_csv(
        comparison_csv,
        comparison_rows,
        [
            "comparison",
            "metric",
            "delta",
        ],
    )

    chart_data = {
        "schema_version": SCHEMA_VERSION,
        "report_version": REPORT_VERSION,
        "suite": multiseed_report["suite"],
        "series": aggregate_rows,
        "comparisons": comparison_rows,
    }

    _write_json(
        chart_data_json,
        chart_data,
    )

    markdown_report.write_text(
        _build_markdown(
            multiseed_report,
            aggregate_rows,
            comparison_rows,
        ),
        encoding="utf-8",
        newline="\n",
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "report_version": REPORT_VERSION,
        "benchmark_id": "memorix_vs_no_memory",
        "suite": multiseed_report["suite"],
        "source_orchestrator_version": (
            multiseed_report[
                "orchestrator_version"
            ]
        ),
        "run_count": int(
            multiseed_report["run_count"]
        ),
        "seed_count": len(
            multiseed_report["seeds"]
        ),
        "mode_count": len(
            multiseed_report["modes"]
        ),
        "aggregate_row_count": len(
            aggregate_rows
        ),
        "comparison_row_count": len(
            comparison_rows
        ),
        "artifacts": {
            "aggregate_metrics_csv": (
                aggregate_csv.name
            ),
            "comparisons_csv": (
                comparison_csv.name
            ),
            "chart_data_json": (
                chart_data_json.name
            ),
            "benchmark_report_markdown": (
                markdown_report.name
            ),
        },
    }

    _write_json(
        summary_json,
        summary,
    )

    return summary


def validate_final_report(
    path: Path,
) -> dict[str, Any]:
    report = _read_json(path)

    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            "Invalid schema_version"
        )

    if report.get("report_version") != REPORT_VERSION:
        raise ValueError(
            "Invalid report_version"
        )

    if report.get("benchmark_id") != "memorix_vs_no_memory":
        raise ValueError(
            "Invalid benchmark_id"
        )

    if int(report.get("run_count", 0)) < 1:
        raise ValueError(
            "Invalid run_count"
        )

    if int(
        report.get(
            "aggregate_row_count",
            0,
        )
    ) < 1:
        raise ValueError(
            "Invalid aggregate_row_count"
        )

    artifacts = report.get("artifacts")

    if not isinstance(artifacts, dict):
        raise ValueError(
            "Invalid artifacts"
        )

    required_artifacts = (
        "aggregate_metrics_csv",
        "comparisons_csv",
        "chart_data_json",
        "benchmark_report_markdown",
    )

    for artifact_name in required_artifacts:
        if artifact_name not in artifacts:
            raise ValueError(
                f"Missing artifact: {artifact_name}"
            )

    return report
