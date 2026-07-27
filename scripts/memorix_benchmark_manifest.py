#!/usr/bin/env python3
"""Create and validate global benchmark run manifests."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory.benchmark.global_contracts import BenchmarkMode, BenchmarkSize, BenchmarkSuite
from memory.benchmark.run_manifest import (
    RunRequest,
    build_manifest,
    capture_environment,
    load_manifest,
    write_manifest_atomic,
)


def _load_request(path: Path) -> RunRequest:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.pop("schema_version")) != 1:
        raise ValueError("Unsupported request schema_version.")
    if payload.pop("benchmark_id") != "memorix_vs_no_memory":
        raise ValueError("Unexpected benchmark_id.")
    payload["mode"] = BenchmarkMode(payload["mode"])
    payload["suite"] = BenchmarkSuite(payload["suite"])
    payload["size"] = BenchmarkSize(payload["size"])
    return RunRequest(**payload)


def _default_runtime_root(mode: BenchmarkMode, run_hint: str) -> Path | None:
    if mode is BenchmarkMode.NO_MEMORY:
        return None
    return Path(tempfile.gettempdir()) / "memorix-benchmark-runtimes" / run_hint


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture")
    capture.add_argument("--request", type=Path, required=True)
    capture.add_argument("--output", type=Path, required=True)
    capture.add_argument("--repository-root", type=Path, default=Path.cwd())
    capture.add_argument("--runtime-root", type=Path)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--compact", action="store_true")

    args = parser.parse_args()

    if args.command == "capture":
        request = _load_request(args.request)
        environment = capture_environment(args.repository_root)
        runtime_root = args.runtime_root
        if runtime_root is None:
            runtime_root = _default_runtime_root(
                request.mode,
                f"{request.paired_run_group_id}-{request.mode.value}-s{request.seed}",
            )
        manifest = build_manifest(
            request,
            environment,
            runtime_root=runtime_root,
        )
        write_manifest_atomic(args.output, manifest)
        print("MEMORIX_BENCHMARK_MANIFEST_CAPTURED")
        print(args.output)
        print(manifest.run_id)
        return 0

    manifest = load_manifest(args.manifest)
    payload = manifest.to_dict()
    if args.compact:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
