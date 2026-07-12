"""Minimal UTF-8 JSONL persistence helpers for memoriX."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Mapping, Any

from memory.data.contracts import JSONValue


class JsonlStorageError(RuntimeError):
    """Raised when a JSONL storage operation cannot be completed."""


class JsonlDecodeError(JsonlStorageError):
    """Raised when one stored JSONL line is invalid."""


def append_json_line(
    path: str | Path,
    payload: Mapping[str, JSONValue],
) -> None:
    """Append one JSON object as one durable UTF-8 JSONL line."""

    target = Path(path)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(
            dict(payload),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

        with target.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, TypeError, ValueError) as error:
        raise JsonlStorageError(
            f"Unable to append JSONL data to {target}."
        ) from error


def read_json_lines(
    path: str | Path,
) -> list[dict[str, Any]]:
    """Read every JSON object from a JSONL file.

    A missing file represents an empty store. Invalid or non-object lines are
    rejected explicitly instead of being ignored silently.
    """

    source = Path(path)

    if not source.exists():
        return []

    records: list[dict[str, Any]] = []

    try:
        with source.open("r", encoding="utf-8") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                stripped = raw_line.strip()

                if not stripped:
                    continue

                try:
                    decoded = json.loads(stripped)
                except json.JSONDecodeError as error:
                    raise JsonlDecodeError(
                        f"Invalid JSON at {source}:{line_number}."
                    ) from error

                if not isinstance(decoded, dict):
                    raise JsonlDecodeError(
                        f"Expected a JSON object at "
                        f"{source}:{line_number}."
                    )

                records.append(decoded)
    except JsonlDecodeError:
        raise
    except OSError as error:
        raise JsonlStorageError(
            f"Unable to read JSONL data from {source}."
        ) from error

    return records


def rewrite_json_lines(
    path: str | Path,
    payloads: Iterable[Mapping[str, JSONValue]],
) -> None:
    """Atomically replace a JSONL file with the supplied records."""

    target = Path(path)
    temporary = target.with_name(f"{target.name}.tmp")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)

        with temporary.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            for payload in payloads:
                stream.write(
                    json.dumps(
                        dict(payload),
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                )
                stream.write("\n")

            stream.flush()
            os.fsync(stream.fileno())

        os.replace(temporary, target)
    except (OSError, TypeError, ValueError) as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass

        raise JsonlStorageError(
            f"Unable to rewrite JSONL data at {target}."
        ) from error
