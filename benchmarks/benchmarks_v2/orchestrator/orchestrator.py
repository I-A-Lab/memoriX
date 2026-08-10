from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .data_models import CampaignManifest, RunResult

try:
    from benchmarks.orchestrator.real_runner_adapter import (
        run_real_pair,
        list_available_families,
    )
    _HAS_REAL_RUNNER = True
except ImportError:
    _HAS_REAL_RUNNER = False

try:
    from benchmarks.orchestrator.direct_llm_runner import (
        run_direct_pair,
        list_available_families as list_direct_families,
    )
    _HAS_DIRECT_RUNNER = True
except ImportError:
    _HAS_DIRECT_RUNNER = False

try:
    from benchmarks.orchestrator.llm_backends import OllamaBackend, HuggingFaceBackend
    _HAS_LLM_BACKENDS = True
except ImportError:
    _HAS_LLM_BACKENDS = False


class BenchmarkOrchestrator:
    """Main orchestrator for running benchmarks."""

    def __init__(
        self,
        output_dir: Path,
        dry_run: bool = False,
        backend: Any = None,  # LLMBackend instance for direct execution
    ) -> None:
        self.output_dir = Path(output_dir)
        self._dry_run = dry_run
        self._backend = backend
        self._results: List[RunResult] = []

    # ------------------------------------------------------------------
    # Single family/seed pair execution
    # ------------------------------------------------------------------

    def run_single(
        self,
        family_id: str,
        seed: int,
        campaign_id: str,
        profile: Any = None,
    ) -> tuple[RunResult, RunResult]:
        """Execute one family/seed pair and return (no_memory_result, memorix_core_result).

        Dispatch logic:
        - dry_run=True  -> lightweight simulation, no side effects.
        - dry_run=False + real runner available -> real OpenCode execution.
        - dry_run=False + no real runner       -> RuntimeError.
        """
        # --- Simulation path (preserved) ---
        if self._dry_run:
            no_memory_result = RunResult(
                schema_version=1,
                run_id="dry-run",
                campaign_id=campaign_id,
                family=family_id,
                mode="A",
                seed=seed,
                pair_index=0,
                status="dry_run",
                failure_category="PASS",
                dry_run=True,
            )
            memorix_core_result = RunResult(
                schema_version=1,
                run_id="dry-run",
                campaign_id=campaign_id,
                family=family_id,
                mode="B",
                seed=seed,
                pair_index=1,
                status="dry_run",
                failure_category="PASS",
                dry_run=True,
            )
            return no_memory_result, memorix_core_result

        # --- Direct LLM execution path ---
        if self._backend is not None and _HAS_DIRECT_RUNNER:
            from benchmarks.orchestrator.direct_llm_runner import DirectRunRequest, run_direct

            no_memory_real = run_direct(DirectRunRequest(
                family_id=family_id,
                seed=seed,
                mode="no_memory",
                backend=self._backend,
            ))
            memorix_core_real = run_direct(DirectRunRequest(
                family_id=family_id,
                seed=seed,
                mode="memorix_core",
                backend=self._backend,
            ))

            no_memory_result = self._convert_direct_result(
                real=no_memory_real,
                campaign_id=campaign_id,
                mode="A",
                pair_index=0,
            )
            memorix_core_result = self._convert_direct_result(
                real=memorix_core_real,
                campaign_id=campaign_id,
                mode="B",
                pair_index=1,
            )
            return no_memory_result, memorix_core_result

        # --- Real execution path ---
        if not _HAS_REAL_RUNNER:
            raise RuntimeError(
                "Real runner adapter is not available. "
                "Ensure benchmarks.orchestrator.real_runner_adapter can be "
                "imported and all its dependencies are installed. "
                "Cannot execute real benchmarks in non-dry-run mode."
            )

        # Extract model from profile (attribute or dict)
        model: str | None = None
        if profile is not None:
            if hasattr(profile, "model"):
                model = profile.model
            elif isinstance(profile, dict):
                model = profile.get("model")

        repository_root = Path(__file__).resolve().parents[2]

        no_memory_real, memorix_core_real = run_real_pair(
            repository_root=repository_root,
            family_id=family_id,
            seed=seed,
            model=model,
        )

        no_memory_result = self._convert_real_result(
            real=no_memory_real,
            campaign_id=campaign_id,
            mode="A",
            pair_index=0,
        )
        memorix_core_result = self._convert_real_result(
            real=memorix_core_real,
            campaign_id=campaign_id,
            mode="B",
            pair_index=1,
        )

        return no_memory_result, memorix_core_result

    # ------------------------------------------------------------------
    # Conversion helper
    # ------------------------------------------------------------------

    def _convert_real_result(
        self,
        real: Any,
        campaign_id: str,
        mode: str,
        pair_index: int,
    ) -> RunResult:
        """Map a RealRunResult from the adapter into the orchestrator RunResult schema."""
        if real.passed:
            status = "passed"
            failure_category = "PASS"
        elif real.timed_out:
            status = "failed"
            failure_category = "TIMEOUT"
        elif real.error:
            status = "failed"
            failure_category = "ERROR"
        else:
            status = "failed"
            failure_category = "FAIL"

        case_count = max(real.case_count, 0)
        passed_case_count = max(real.passed_case_count, 0)
        precision = passed_case_count / max(case_count, 1)

        return RunResult(
            schema_version=1,
            run_id=f"real-{real.family_id}-seed{real.seed:08d}-{mode}",
            campaign_id=campaign_id,
            family=real.family_id,
            mode=mode,
            seed=real.seed,
            pair_index=pair_index,
            status=status,
            failure_category=failure_category,
            precision=precision,
            recall=precision,
            f1=precision,
            latency_ms=real.duration_ms,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            rss_bytes=0,
            cpu_percent=0.0,
            duration_ms=real.duration_ms,
            artifacts_path="",
            created_at_utc="",
            dry_run=False,
        )

    def _convert_direct_result(
        self,
        real: Any,
        campaign_id: str,
        mode: str,
        pair_index: int,
    ) -> RunResult:
        """Map a DirectRunResult into the orchestrator RunResult schema."""
        if real.passed:
            status = "passed"
            failure_category = "PASS"
        elif real.error:
            status = "failed"
            failure_category = "ERROR"
        else:
            status = "failed"
            failure_category = "FAIL"

        case_count = max(real.case_count, 0)
        passed_case_count = max(real.passed_case_count, 0)
        precision = passed_case_count / max(case_count, 1)

        return RunResult(
            schema_version=1,
            run_id=f"direct-{real.family_id}-seed{real.seed:08d}-{mode}",
            campaign_id=campaign_id,
            family=real.family_id,
            mode=mode,
            seed=real.seed,
            pair_index=pair_index,
            status=status,
            failure_category=failure_category,
            precision=precision,
            recall=precision,
            f1=precision,
            latency_ms=real.duration_ms,
            prompt_tokens=real.prompt_tokens,
            completion_tokens=real.completion_tokens,
            total_tokens=real.total_tokens,
            estimated_cost_usd=0.0,
            rss_bytes=0,
            cpu_percent=0.0,
            duration_ms=real.duration_ms,
            artifacts_path="",
            created_at_utc="",
            dry_run=False,
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(
        self,
        manifest: CampaignManifest,
        output_dir: Optional[Path] = None,
        families: Optional[List[str]] = None,
    ) -> List[RunResult]:
        """Run all family/seed pairs defined by the manifest.

        Parameters
        ----------
        manifest:
            Campaign manifest containing seeds and campaign metadata.
        output_dir:
            Override output directory. Falls back to self.output_dir.
        families:
            Explicit list of family IDs to run. When *None*, the real-runner
            ``list_available_families()`` is used if available, otherwise
            a single generic ``f01`` fallback is used for simulation-only
            runs.

        Returns
        -------
        List of RunResult objects (two per family/seed: no_memory + memorix_core).
        The raw results are also written to ``raw_results.json`` in the
        output directory.
        """
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        if families:
            family_list = families
        elif _HAS_REAL_RUNNER:
            family_list = list_available_families()
        elif _HAS_DIRECT_RUNNER:
            family_list = list_direct_families()
        else:
            family_list = ["f01"]

        results: List[RunResult] = []

        for family_id in family_list:
            for seed in manifest.seeds:
                no_memory_result, memorix_core_result = self.run_single(
                    family_id=family_id,
                    seed=seed,
                    campaign_id=manifest.campaign_id,
                )
                results.append(no_memory_result)
                results.append(memorix_core_result)

        self._results = results

        # Persist raw results
        raw_path = out_dir / "raw_results.json"
        raw_path.write_text(
            json.dumps([r.to_dict() for r in results], indent=2),
            encoding="utf-8",
        )

        return results

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_results(
        self, results: Optional[List[RunResult]] = None
    ) -> List[Dict[str, Any]]:
        """Aggregate results into summary statistics."""
        if results is None:
            results = self._results

        if not results:
            return []

        # Group by family
        family_groups: Dict[str, List[RunResult]] = {}
        for r in results:
            family_groups.setdefault(r.family, []).append(r)

        summaries = []
        for family_id, family_results in family_groups.items():
            total = len(family_results)
            passed = sum(1 for r in family_results if r.status == "passed")
            f1s = [r.f1 for r in family_results]
            latencies = [r.latency_ms for r in family_results]

            summaries.append({
                "family": family_id,
                "total_runs": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": passed / max(total, 1),
                "mean_f1": sum(f1s) / max(total, 1),
                "median_latency_ms": sorted(latencies)[total // 2] if total > 0 else 0.0,
            })

        return summaries
