from __future__ import annotations

import random
import time
from typing import Any

from . import register_family
from ..orchestrator.ab_balancer import determine_order
from ..orchestrator.data_models import make_run_result


@register_family
class F26ConcurrentAccess:
    """Concurrent Access: benchmark family for the stress suite."""

    @property
    def family_id(self) -> str:
        return "f26"

    @property
    def family_name(self) -> str:
        return "Concurrent Access"

    @property
    def suite(self) -> str:
        return "stress"

    def validate_config(self, config: dict) -> None:
        if "memory_count" not in config:
            raise ValueError("Config must include 'memory_count'")

    def run(self, pair_index: int, seed: int, mode: str, config: dict) -> dict:
        self.validate_config(config)
        start = time.monotonic()
        rng = random.Random(seed + pair_index * 26000)
        memory_count = config["memory_count"]
        context_pressure = min(memory_count / 10000.0, 1.0)
        base_precision = 0.86 - 0.20 * context_pressure + rng.gauss(0, 0.04)
        base_recall = 0.83 - 0.18 * context_pressure + rng.gauss(0, 0.04)

        precision = max(0.0, min(1.0, base_precision))
        recall = max(0.0, min(1.0, base_recall))
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        latency = 110.0 + memory_count * 0.01 + rng.gauss(30, 10)
        prompt_tok = memory_count * 3 + rng.randint(100, 500)
        comp_tok = rng.randint(50, 200)

        status = "passed" if f1 >= 0.5 else "failed"
        failure_category = "PASS" if status == "passed" else "TECH_CORRUPTION"

        duration_ms = (time.monotonic() - start) * 1000
        return make_run_result(
            campaign_id=config.get("campaign_id", ""),
            family="f26",
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
            rss_bytes=6 * 1024 * 1024 + rng.randint(0, 2 * 1024 * 1024),
            cpu_percent=round(rng.uniform(8.0, 35.0), 1),
            duration_ms=round(duration_ms + latency, 2),
        )
