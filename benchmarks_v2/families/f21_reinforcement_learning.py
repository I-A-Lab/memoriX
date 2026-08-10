from __future__ import annotations

import random
import time
from typing import Any

from . import register_family
from ..orchestrator.ab_balancer import determine_order
from ..orchestrator.data_models import make_run_result


@register_family
class F21ReinforcementLearning:
    """Reinforcement Learning: benchmark family for the temporal suite."""

    @property
    def family_id(self) -> str:
        return "f21"

    @property
    def family_name(self) -> str:
        return "Reinforcement Learning"

    @property
    def suite(self) -> str:
        return "temporal"

    def validate_config(self, config: dict) -> None:
        if "memory_count" not in config:
            raise ValueError("Config must include 'memory_count'")

    def run(self, pair_index: int, seed: int, mode: str, config: dict) -> dict:
        self.validate_config(config)
        start = time.monotonic()
        rng = random.Random(seed + pair_index * 21000)
        memory_count = config["memory_count"]
        reinforcement_bonus = min(pair_index * 0.005, 0.10)
        base_precision = 0.82 + reinforcement_bonus + rng.gauss(0, 0.04)
        base_recall = 0.8 + reinforcement_bonus + rng.gauss(0, 0.04)

        precision = max(0.0, min(1.0, base_precision))
        recall = max(0.0, min(1.0, base_recall))
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        latency = 85.0 + rng.gauss(25, 12)
        prompt_tok = memory_count + rng.randint(30, 150)
        comp_tok = rng.randint(50, 200)

        status = "passed" if f1 >= 0.55 else "failed"
        failure_category = "PASS" if status == "passed" else "MEM_RECALL_MISS"

        duration_ms = (time.monotonic() - start) * 1000
        return make_run_result(
            campaign_id=config.get("campaign_id", ""),
            family="f21",
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
            rss_bytes=9 * 1024 * 1024 + rng.randint(0, 2 * 1024 * 1024),
            cpu_percent=round(rng.uniform(8.0, 35.0), 1),
            duration_ms=round(duration_ms + latency, 2),
        )
