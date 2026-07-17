"""Public gateway for the memoriX memory system."""

from memory.gateway.capacity_control import (
    CapacityAdmissionDecision,
    CapacityAdmissionError,
    SoftPruningApplicationError,
    SoftPruningApplicationReport,
    apply_soft_pruning_plan,
    evaluate_capacity_admission,
    require_capacity_admission,
)
from memory.gateway.event_service import (
    DuplicateEventError,
    MemoryEventConsistencyError,
    MemoryEventService,
    RecordedMemoryEvent,
)
from memory.gateway.public_api import (
    MemoriXGateway,
    get_default_gateway,
    record_memory_event,
    reset_default_gateway,
    retrieve_memory,
    search_cold_site_history,
)
from memory.gateway.validation_service import (
    CandidateValidationError,
    MemoryValidationService,
)

__all__ = [
    "require_capacity_admission",
    "evaluate_capacity_admission",
    "apply_soft_pruning_plan",
    "SoftPruningApplicationReport",
    "SoftPruningApplicationError",
    "CapacityAdmissionError",
    "CapacityAdmissionDecision",
    "CandidateValidationError",
    "DuplicateEventError",
    "MemoriXGateway",
    "MemoryEventConsistencyError",
    "MemoryEventService",
    "MemoryValidationService",
    "RecordedMemoryEvent",
    "get_default_gateway",
    "record_memory_event",
    "reset_default_gateway",
    "retrieve_memory",
    "search_cold_site_history",
]
