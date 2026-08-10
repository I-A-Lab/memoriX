from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.orchestrator.checkpoint import (
    cleanup_checkpoints,
    get_completed_pairs,
    load_checkpoint,
    verify_checkpoint_integrity,
    write_checkpoint,
)


class TestWriteCheckpointCreatesFile:
    def test_write_checkpoint_creates_file(self, tmp_path):
        """Checkpoint file is created."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        pair_index = 0
        seed = 42
        data = {"status": "completed", "result": {"score": 0.95}}

        write_checkpoint(checkpoint_dir, pair_index, seed, data)

        expected_file = checkpoint_dir / f"pair_{pair_index}_seed_{seed}.json"
        assert expected_file.exists()

        saved = json.loads(expected_file.read_text(encoding="utf-8"))
        assert saved["pair_index"] == pair_index
        assert saved["seed"] == seed
        assert saved["data"] == data
        assert "sha256" in saved


class TestLoadCheckpointReturnsData:
    def test_load_checkpoint_returns_data(self, tmp_path):
        """Loaded checkpoint matches written data."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        pair_index = 3
        seed = 7
        data = {"metrics": {"latency_ms": 120.5, "accuracy": 0.88}}

        write_checkpoint(checkpoint_dir, pair_index, seed, data)
        loaded = load_checkpoint(checkpoint_dir, pair_index, seed)

        assert loaded["pair_index"] == pair_index
        assert loaded["seed"] == seed
        assert loaded["data"] == data


class TestVerifyCheckpointIntegrityValid:
    def test_verify_checkpoint_integrity_valid(self, tmp_path):
        """SHA-256 verification passes for unmodified checkpoint."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        data = {"status": "ok"}

        write_checkpoint(checkpoint_dir, 0, 1, data)
        assert verify_checkpoint_integrity(checkpoint_dir, 0, 1) is True


class TestVerifyCheckpointIntegrityTampered:
    def test_verify_checkpoint_integrity_tampered(self, tmp_path):
        """SHA-256 verification fails for tampered checkpoint."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()
        data = {"status": "ok"}

        write_checkpoint(checkpoint_dir, 0, 1, data)

        # Tamper with the checkpoint file
        ckpt_file = checkpoint_dir / "pair_0_seed_1.json"
        content = json.loads(ckpt_file.read_text(encoding="utf-8"))
        content["data"]["status"] = "tampered"
        ckpt_file.write_text(json.dumps(content), encoding="utf-8")

        assert verify_checkpoint_integrity(checkpoint_dir, 0, 1) is False


class TestGetCompletedPairs:
    def test_get_completed_pairs(self, tmp_path):
        """Returns correct set of completed pair indices."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()

        for pi in [0, 2, 5]:
            write_checkpoint(checkpoint_dir, pi, 42, {"done": True})

        completed = get_completed_pairs(checkpoint_dir)
        assert completed == {0, 2, 5}

    def test_get_completed_pairs_empty(self, tmp_path):
        """Empty checkpoint directory returns empty set."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()

        completed = get_completed_pairs(checkpoint_dir)
        assert completed == set()


class TestNoOverwriteExistingCheckpoint:
    def test_no_overwrite_existing_checkpoint(self, tmp_path):
        """Raises error when overwriting an existing checkpoint."""
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir()

        write_checkpoint(checkpoint_dir, 0, 1, {"first": True})

        with pytest.raises(Exception):
            write_checkpoint(checkpoint_dir, 0, 1, {"second": True}, allow_overwrite=False)
