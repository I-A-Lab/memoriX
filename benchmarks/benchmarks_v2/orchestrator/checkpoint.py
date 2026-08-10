from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def write_checkpoint(
    checkpoint_dir: Path,
    pair_index: int,
    seed: int,
    data: Dict[str, Any],
    allow_overwrite: bool = True,
) -> Path:
    """Write a checkpoint file for a given pair_index and seed.

    Raises FileExistsError if the file exists and allow_overwrite is False.
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    ckpt_file = checkpoint_dir / f"pair_{pair_index}_seed_{seed}.json"

    if ckpt_file.exists() and not allow_overwrite:
        raise FileExistsError(
            f"Checkpoint already exists: {ckpt_file}"
        )

    payload = {
        "pair_index": pair_index,
        "seed": seed,
        "data": data,
    }

    # Compute SHA-256 of the data payload
    data_str = json.dumps(data, sort_keys=True)
    sha256 = hashlib.sha256(data_str.encode("utf-8")).hexdigest()
    payload["sha256"] = sha256

    with open(ckpt_file, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    return ckpt_file


def load_checkpoint(
    checkpoint_dir: Path,
    pair_index: int,
    seed: int,
) -> Dict[str, Any]:
    """Load a checkpoint file for a given pair_index and seed.

    Raises FileNotFoundError if the checkpoint does not exist.
    """
    ckpt_file = checkpoint_dir / f"pair_{pair_index}_seed_{seed}.json"

    if not ckpt_file.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {ckpt_file}"
        )

    with open(ckpt_file, "r", encoding="utf-8") as fh:
        return json.load(fh)


def verify_checkpoint_integrity(
    checkpoint_dir: Path,
    pair_index: int,
    seed: int,
) -> bool:
    """Verify that a checkpoint file's SHA-256 matches its data.

    Returns True if integrity check passes, False otherwise.
    """
    ckpt_file = checkpoint_dir / f"pair_{pair_index}_seed_{seed}.json"

    if not ckpt_file.exists():
        return False

    with open(ckpt_file, "r", encoding="utf-8") as fh:
        content = json.load(fh)

    stored_hash = content.get("sha256")
    data = content.get("data")

    if stored_hash is None or data is None:
        return False

    data_str = json.dumps(data, sort_keys=True)
    computed_hash = hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    return stored_hash == computed_hash


def get_completed_pairs(checkpoint_dir: Path) -> Set[int]:
    """Return the set of pair indices that have checkpoint files."""
    if not checkpoint_dir.exists():
        return set()

    completed: Set[int] = set()
    for ckpt_file in checkpoint_dir.glob("pair_*_seed_*.json"):
        try:
            with open(ckpt_file, "r", encoding="utf-8") as fh:
                content = json.load(fh)
            pair_index = content.get("pair_index")
            if pair_index is not None:
                completed.add(pair_index)
        except (json.JSONDecodeError, KeyError):
            continue

    return completed


def cleanup_checkpoints(checkpoint_dir: Path) -> int:
    """Remove all checkpoint files in the directory.

    Returns the number of files removed.
    """
    if not checkpoint_dir.exists():
        return 0

    count = 0
    for ckpt_file in checkpoint_dir.glob("pair_*_seed_*.json"):
        ckpt_file.unlink()
        count += 1

    return count
