from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.reference_campaign import (
    CampaignRequest,
    _summary,
    validate_reference_campaign,
)


class ReferenceCampaignTests(unittest.TestCase):
    def test_default_request_is_valid(self):
        CampaignRequest().validate()

    def test_medium_request_is_valid(self):
        CampaignRequest(
            size="medium",
            seeds=(10, 20, 30),
        ).validate()

    def test_tiny_is_rejected(self):
        with self.assertRaises(ValueError):
            CampaignRequest(
                size="tiny"
            ).validate()

    def test_duplicate_seeds_are_rejected(self):
        with self.assertRaises(ValueError):
            CampaignRequest(
                seeds=(1, 1)
            ).validate()

    def test_summary_uses_real_variance(self):
        result = _summary(
            [0.2, 0.5, 0.8]
        )
        self.assertEqual(
            result["count"],
            3,
        )
        self.assertGreater(
            result["stdev"],
            0,
        )
        self.assertLess(
            result["ci95_low"],
            result["ci95_high"],
        )

    def test_report_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "campaign_version": (
                            "40.5.1"
                        ),
                        "campaign_type": (
                            "real_memorix_reference"
                        ),
                        "request": {
                            "size": "small",
                            "seeds": [
                                101,
                                202,
                                303,
                            ],
                        },
                        "run_count": 12,
                        "real_memorix_run_count": 6,
                        "aggregates": {
                            "memory_pure": {},
                            "agent_multisession": {},
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = (
                validate_reference_campaign(
                    path
                )
            )
            self.assertEqual(
                result["run_count"],
                12,
            )

    def test_tampered_run_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "campaign_version": (
                            "40.5.1"
                        ),
                        "campaign_type": (
                            "real_memorix_reference"
                        ),
                        "request": {
                            "size": "small",
                            "seeds": [101],
                        },
                        "run_count": 99,
                        "real_memorix_run_count": 2,
                        "aggregates": {
                            "memory_pure": {},
                            "agent_multisession": {},
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(
                ValueError
            ):
                validate_reference_campaign(
                    path
                )


if __name__ == "__main__":
    unittest.main()
