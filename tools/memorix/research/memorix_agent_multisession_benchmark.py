#!/usr/bin/env python3
"""Run or validate the deterministic multi-session agent benchmark."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

REPOSITORY_ROOT = find_repository_root(Path(__file__))
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory.benchmark.agent_multisession import (  # noqa: E402
    build_agent,
    run_agent_multisession_benchmark,
    validate_agent_report,
    write_agent_results,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--dataset", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--mode", choices=("no_memory", "memorix_core"), required=True)
    run.add_argument("--backend", choices=("lexical", "memorix"), default="lexical")
    run.add_argument("--runtime-root")
    run.add_argument("--top-k", type=int, default=5)
    validate = commands.add_parser("validate")
    validate.add_argument("--report", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "validate":
        payload = validate_agent_report(Path(args.report))
        print("MEMORIX_AGENT_REPORT_VALID")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    runtime_root = None if args.runtime_root is None else Path(args.runtime_root)
    agent = build_agent(mode=args.mode, backend=args.backend, runtime_root=runtime_root)
    metrics, rows = run_agent_multisession_benchmark(
        Path(args.dataset), agent, top_k=args.top_k
    )
    manifest = json.loads(
        (Path(args.dataset) / "dataset_manifest.json").read_text(encoding="utf-8-sig")
    )
    report = write_agent_results(
        Path(args.output), metrics, rows,
        mode=args.mode, backend=args.backend, dataset_id=str(manifest["dataset_id"]),
    )
    print("MEMORIX_AGENT_MULTISESSION_BENCHMARK_OK")
    print(report)
    print(json.dumps(metrics.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
