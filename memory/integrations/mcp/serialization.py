"""JSON-compatible serialization helpers for the memoriX MCP boundary."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


def to_json_value(value: Any) -> Any:
    """Recursively convert a Python value to JSON-compatible data."""

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value):
        return to_json_value(asdict(value))

    if hasattr(value, "to_dict"):
        return to_json_value(value.to_dict())

    if isinstance(value, Mapping):
        return {
            str(key): to_json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            to_json_value(item)
            for item in value
        ]

    raise TypeError(
        f"Unsupported MCP serialization type: "
        f"{type(value).__name__}"
    )
