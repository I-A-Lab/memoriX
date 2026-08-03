#!/usr/bin/env python3
"""Generate or validate deterministic memoriX benchmark datasets."""

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

from memory.benchmark.dataset_generator import (  # noqa: E402
    load_dataset_request,
    validate_dataset_directory,
    write_dataset,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--request", required=True)
    generate.add_argument("--output", required=True)
    generate.add_argument(
        "--configs-dir",
        default=str(REPOSITORY_ROOT / "benchmarks" / "memorix_vs_no_memory" / "configs"),
    )

    validate = subparsers.add_parser("validate")
    validate.add_argument("--dataset", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "generate":
        request = load_dataset_request(Path(args.request))
        artifact = write_dataset(
            request,
            configs_dir=Path(args.configs_dir),
            output_dir=Path(args.output),
        )
        print("MEMORIX_DATASET_GENERATED")
        print(json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False))
        return 0

    artifact = validate_dataset_directory(Path(args.dataset))
    print("MEMORIX_DATASET_VALID")
    print(json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
