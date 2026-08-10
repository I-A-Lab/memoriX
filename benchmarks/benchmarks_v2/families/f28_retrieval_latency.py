from __future__ import annotations

import random
import time
from typing import Any

from . import register_family
from ..orchestrator.ab_balancer import determine_order
from ..orchestrator.data_models import make_run_result


@register_family
class F28RetrievalLatency:
    """Retrieval Latency: benchmark family for the performance suite."""

    @property
    def family_id(self) -> str:
        return "f28"

    @property
    def family_name(self) -> str:
        return "Retrieval Latency"

    @property
    def suite(self) -> str:
        return "performance"

    def validate_config(self, config: dict) -> None:
        if "memory_count" not in config:
            raise ValueError("Config must include 'memory_count'")

    def run(self, pair_index: int, seed: int, mode: str, config: dict) -> dict:
        self.validate_config(config)
        start = time.monotonic()
        rng = random.Random(seed + pair_index * 28000)
        memory_count = config["memory_count"]
        base_precision = 0.88 + rng.gauss(0, 0.03)
        base_recall = 0.85 + rng.gauss(0, 0.03)

        precision = max(0.0, min(1.0, base_precision))
        recall = max(0.0, min(1.0, base_recall))
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        expected_latency = 30.0 + memory_count ** 0.6 + rng.gauss(15, 5)
        latency = max(10.0, expected_latency)
        prompt_tok = memory_count + rng.randint(20, 100)
        comp_tok = rng.randint(50, 200)

        status = "passed"
        failure_category = "PASS"
        if latency > 5000:
            status = "timeout"
            failure_category = "TECH_TIMEOUT"
        elif f1 < 0.70:
            status = "failed"
            failure_category = "MEM_RECALL_MISS"

        duration_ms = (time.monotonic() - start) * 1000
        return make_run_result(
            campaign_id=config.get("campaign_id", ""),
            family="f28",
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
            rss_bytes=8 * 1024 * 1024 + rng.randint(0, 2 * 1024 * 1024),
            cpu_percent=round(rng.uniform(8.0, 35.0), 1),
            duration_ms=round(duration_ms + latency, 2),
        )
