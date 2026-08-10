from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..orchestrator.data_models import RunResult


class BenchmarkFamily(abc.ABC):
    """Abstract base class for all benchmark families."""

    @property
    @abc.abstractmethod
    def family_id(self) -> str:
        """Unique identifier like 'f01'."""

    @property
    @abc.abstractmethod
    def family_name(self) -> str:
        """Human-readable name like 'Exact Key Recall'."""

    @property
    @abc.abstractmethod
    def suite(self) -> str:
        """Suite grouping like 'core_recall', 'temporal', 'noise', etc."""

    @abc.abstractmethod
    def run(
        self,
        pair_index: int,
        seed: int,
        mode: str,
        config: Dict[str, Any],
    ) -> RunResult:
        """Execute a single benchmark run and return the result."""

    @abc.abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the configuration for this family."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.family_id} name={self.family_name}>"


# Global registry
FAMILY_REGISTRY: Dict[str, Type[BenchmarkFamily]] = {}


def register_family(cls: Type[BenchmarkFamily]) -> Type[BenchmarkFamily]:
    """Decorator to register a benchmark family class."""
    instance = cls.__new__(cls)
    FAMILY_REGISTRY[instance.family_id] = cls
    return cls


def get_family(family_id: str) -> BenchmarkFamily:
    """Instantiate and return a family by its ID."""
    cls = FAMILY_REGISTRY.get(family_id)
    if cls is None:
        available = ", ".join(sorted(FAMILY_REGISTRY.keys()))
        raise ValueError(f"Unknown family '{family_id}'. Available: {available}")
    return cls()


def list_families() -> List[str]:
    """Return all registered family IDs."""
    return sorted(FAMILY_REGISTRY.keys())


def get_all_families() -> Dict[str, BenchmarkFamily]:
    """Instantiate and return all registered families."""
    return {fid: get_family(fid) for fid in FAMILY_REGISTRY}


# Import all family modules to trigger registration
# These are imported at module level so the registry is populated on first access
from . import (  # noqa: E402, F401
    f01_exact_key_recall,
    f02_semantic_retrieval,
    f03_temporal_ordering,
    f04_noise_resistance,
    f05_partial_match,
    f06_multi_hop_chain,
    f07_contradiction_detection,
    f08_entity_resolution,
    f09_context_window_stress,
    f10_aggregation_accuracy,
    f11_summarization_fidelity,
    f12_translation_alignment,
    f13_code_memory_recall,
    f14_numerical_reasoning,
    f15_causal_inference,
    f16_negation_handling,
    f17_ambiguity_resolution,
    f18_scale_invariance,
    f19_duplicate_merge,
    f20_forgetting_curve,
    f21_reinforcement_learning,
    f22_cross_session_drift,
    f23_hierarchical_memory,
    f24_temporal_decay,
    f25_noise_injection_robustness,
    f26_concurrent_access,
    f27_memory_fragmentation,
    f28_retrieval_latency,
    f29_cost_efficiency,
    f30_safety_compliance,
    f31_edge_case_handling,
    f32_end_to_end_pipeline,
)
