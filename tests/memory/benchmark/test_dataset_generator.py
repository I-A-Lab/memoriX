from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.dataset_generator import (
    FAMILIES,
    generate_dataset,
    load_dataset_request,
    validate_dataset_directory,
    write_dataset,
)


ROOT = Path(__file__).resolve().parents[3]
CONFIGS = ROOT / "benchmarks" / "memorix_vs_no_memory" / "configs"
DEFAULT_REQUEST = CONFIGS / "default_dataset.json"


class DatasetGeneratorTests(unittest.TestCase):
    def test_same_seed_is_byte_deterministic(self) -> None:
        request = load_dataset_request(DEFAULT_REQUEST)
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_artifact = write_dataset(request, configs_dir=CONFIGS, output_dir=Path(first))
            second_artifact = write_dataset(request, configs_dir=CONFIGS, output_dir=Path(second))
            self.assertEqual(first_artifact.records_sha256, second_artifact.records_sha256)
            self.assertEqual(first_artifact.queries_sha256, second_artifact.queries_sha256)
            self.assertEqual(
                (Path(first) / "records.jsonl").read_bytes(),
                (Path(second) / "records.jsonl").read_bytes(),
            )

    def test_all_required_families_are_generated(self) -> None:
        request = load_dataset_request(DEFAULT_REQUEST)
        records, _ = generate_dataset(request, configs_dir=CONFIGS)
        self.assertEqual({record["family"] for record in records}, set(FAMILIES))

    def test_forget_records_are_forbidden_retrieval_targets(self) -> None:
        request = load_dataset_request(DEFAULT_REQUEST)
        records, queries = generate_dataset(request, configs_dir=CONFIGS)
        forgotten = {record["record_id"] for record in records if record["family"] == "forget"}
        self.assertTrue(forgotten)
        for query in queries:
            if query["family"] == "forget":
                self.assertEqual(query["expected_record_ids"], [])
                self.assertEqual(set(query["forbidden_record_ids"]), forgotten.intersection(query["forbidden_record_ids"]))

    def test_updates_and_contradictions_reference_previous_ids(self) -> None:
        request = load_dataset_request(DEFAULT_REQUEST)
        records, _ = generate_dataset(request, configs_dir=CONFIGS)
        affected = [
            record for record in records if record["family"] in {"update", "contradiction"}
        ]
        self.assertTrue(affected)
        self.assertTrue(all(record["supersedes"] for record in affected))

    def test_non_empty_output_is_not_overwritten(self) -> None:
        request = load_dataset_request(DEFAULT_REQUEST)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_dataset(request, configs_dir=CONFIGS, output_dir=output)
            with self.assertRaises(FileExistsError):
                write_dataset(request, configs_dir=CONFIGS, output_dir=output)

    def test_manifest_detects_tampered_records(self) -> None:
        request = load_dataset_request(DEFAULT_REQUEST)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_dataset(request, configs_dir=CONFIGS, output_dir=output)
            with (output / "records.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"tampered": True}) + "\n")
            with self.assertRaisesRegex(ValueError, "records_sha256 mismatch"):
                validate_dataset_directory(output)

    def test_generated_directory_validates(self) -> None:
        request = load_dataset_request(DEFAULT_REQUEST)
        with tempfile.TemporaryDirectory() as directory:
            artifact = write_dataset(request, configs_dir=CONFIGS, output_dir=Path(directory))
            validated = validate_dataset_directory(Path(directory))
            self.assertEqual(validated.records_sha256, artifact.records_sha256)
            self.assertEqual(validated.query_count, artifact.query_count)


if __name__ == "__main__":
    unittest.main()
