"""Read-only inspection helpers for memoriX runtime files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory.diagnostics.contracts import (
    RuntimeFileObservation,
)


def _count_non_empty_lines(path: Path) -> int:
    count = 0

    with path.open(
        "r",
        encoding="utf-8",
        errors="strict",
    ) as handle:
        for raw_line in handle:
            if raw_line.strip():
                count += 1

    return count


def _inspect_json(path: Path) -> tuple[
    bool,
    int | None,
]:
    value: Any = json.loads(
        path.read_text(encoding="utf-8")
    )

    if isinstance(value, list):
        return True, len(value)

    if isinstance(value, dict):
        for key in (
            "items",
            "records",
            "memories",
            "candidates",
            "events",
            "blocks",
        ):
            nested = value.get(key)

            if isinstance(nested, list):
                return True, len(nested)

        return True, 1

    return True, 1


def _inspect_jsonl(path: Path) -> tuple[
    bool,
    int,
]:
    record_count = 0

    with path.open(
        "r",
        encoding="utf-8",
        errors="strict",
    ) as handle:
        for line_number, raw_line in enumerate(
            handle,
            start=1,
        ):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at line {line_number}."
                ) from exc

            if not isinstance(value, dict):
                raise ValueError(
                    "JSONL records must be JSON objects."
                )

            record_count += 1

    return True, record_count


def inspect_runtime_path(
    logical_name: str,
    path: Path,
) -> RuntimeFileObservation:
    """Inspect one path without creating or modifying it."""

    path = Path(path)

    if not path.exists():
        return RuntimeFileObservation(
            logical_name=logical_name,
            path=str(path),
            exists=False,
            is_file=False,
            is_directory=False,
            size_bytes=None,
            line_count=None,
            record_count=None,
            valid_json=None,
            valid_jsonl=None,
        )

    if path.is_dir():
        try:
            child_count = sum(
                1
                for _ in path.iterdir()
            )
        except OSError as exc:
            return RuntimeFileObservation(
                logical_name=logical_name,
                path=str(path),
                exists=True,
                is_file=False,
                is_directory=True,
                size_bytes=None,
                line_count=None,
                record_count=None,
                valid_json=None,
                valid_jsonl=None,
                error=str(exc),
            )

        return RuntimeFileObservation(
            logical_name=logical_name,
            path=str(path),
            exists=True,
            is_file=False,
            is_directory=True,
            size_bytes=None,
            line_count=None,
            record_count=child_count,
            valid_json=None,
            valid_jsonl=None,
        )

    size_bytes = path.stat().st_size
    suffix = path.suffix.lower()

    line_count: int | None = None
    record_count: int | None = None
    valid_json: bool | None = None
    valid_jsonl: bool | None = None
    error: str | None = None

    try:
        if suffix in {
            ".json",
            ".jsonl",
            ".txt",
            ".log",
        }:
            line_count = _count_non_empty_lines(
                path
            )

        if suffix == ".json":
            valid_json, record_count = (
                _inspect_json(path)
            )

        if suffix == ".jsonl":
            valid_jsonl, record_count = (
                _inspect_jsonl(path)
            )
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        error = str(exc)

        if suffix == ".json":
            valid_json = False

        if suffix == ".jsonl":
            valid_jsonl = False

    return RuntimeFileObservation(
        logical_name=logical_name,
        path=str(path),
        exists=True,
        is_file=True,
        is_directory=False,
        size_bytes=size_bytes,
        line_count=line_count,
        record_count=record_count,
        valid_json=valid_json,
        valid_jsonl=valid_jsonl,
        error=error,
    )
