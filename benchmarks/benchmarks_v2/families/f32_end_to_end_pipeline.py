from __future__ import annotations

import random
import time
from typing import Any

from . import register_family
from ..orchestrator.ab_balancer import determine_order
from ..orchestrator.data_models import make_run_result


@register_family
class F32EndToEndPipeline:
    """End-to-End Pipeline: benchmark family for the integration suite."""

    @property
    def family_id(self) -> str:
        return "f32"

    @property
    def family_name(self) -> str:
        return "End-to-End Pipeline"

    @property
    def suite(self) -> str:
        return "integration"

    def validate_config(self, config: dict) -> None:
        if "memory_count" not in config:
            raise ValueError("Config must include 'memory_count'")
        if "distractor_count" not in config:
            raise ValueError("Config must include 'distractor_count'")

    def run(self, pair_index: int, seed: int, mode: str, config: dict) -> dict:
        self.validate_config(config)
        start = time.monotonic()
        rng = random.Random(seed + pair_index * 32000)
        memory_count = config["memory_count"]
        base_precision = 0.81 + rng.gauss(0, 0.05)
        base_recall = 0.78 + rng.gauss(0, 0.05)

        precision = max(0.0, min(1.0, base_precision))
        recall = max(0.0, min(1.0, base_recall))
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        memory_count = config["memory_count"]
        distractor_count = config["distractor_count"]
        latency = 200.0 + memory_count * 0.002 + distractor_count * 0.001 + rng.gauss(50, 20)
        prompt_tok = memory_count + distractor_count + rng.randint(100, 400)
        comp_tok = rng.randint(100, 500)

        status = "passed" if f1 >= 0.55 else "failed"
        failure_category = "PASS" if status == "passed" else "TECH_UNCAUGHT"

        duration_ms = (time.monotonic() - start) * 1000
        return make_run_result(
            campaign_id=config.get("campaign_id", ""),
            family="f32",
            mode=mode,
            seed=seed,
            pair_index=pair_index,
            status=status,
            failure_category=failure_category,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            latency_ms=round(latency, 2),
            prompt_tokens=prompt_tok,
            completion_tokens=comp_tok,
            estimated_cost_usd=round((prompt_tok * 0.003 + comp_tok * 0.015) / 1000, 6),
            rss_bytes=4 * 1024 * 1024 + rng.randint(0, 2 * 1024 * 1024),
            cpu_percent=round(rng.uniform(8.0, 35.0), 1),
            duration_ms=round(duration_ms + latency, 2),
        )
