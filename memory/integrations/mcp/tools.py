"""MCP tool declarations and dispatch for memoriX."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from memory.data import CandidateStatus
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.serialization import (
    to_json_value,
)


class McpToolError(RuntimeError):
    """Base error returned by an MCP tool."""


class McpUnknownToolError(McpToolError):
    """Raised when a requested tool does not exist."""


class McpInvalidArgumentsError(McpToolError):
    """Raised when MCP tool arguments are invalid."""


@dataclass(frozen=True, slots=True)
class McpToolDefinition:
    """One MCP tool declaration."""

    name: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the MCP declaration."""

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def _object_schema(
    properties: Mapping[str, Any],
    *,
    required: tuple[str, ...] = (),
    additional_properties: bool = False,
) -> dict[str, Any]:
    """Build a JSON Schema object."""

    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": additional_properties,
    }


STRING = {"type": "string"}
NUMBER_0_1 = {
    "type": "number",
    "minimum": 0.0,
    "maximum": 1.0,
}
POSITIVE_INTEGER = {
    "type": "integer",
    "minimum": 1,
}
METADATA_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
}


TOOL_DEFINITIONS: tuple[McpToolDefinition, ...] = (
    McpToolDefinition(
        name="memorix_record_event",
        description=(
            "Record one event in short-term memory and archive it "
            "directly in the durable cold site."
        ),
        input_schema=_object_schema(
            {
                "content": STRING,
                "event_type": STRING,
                "source": STRING,
                "project_id": {
                    "type": ["string", "null"]
                },
                "session_id": {
                    "type": ["string", "null"]
                },
                "importance": NUMBER_0_1,
                "confidence": NUMBER_0_1,
                "surprise": NUMBER_0_1,
                "metadata": METADATA_SCHEMA,
            },
            required=(
                "content",
                "event_type",
                "source",
            ),
        ),
    ),
    McpToolDefinition(
        name="memorix_context",
        description=(
            "Retrieve active validated memory from the Titan hot "
            "site only. There is no cold-site fallback."
        ),
        input_schema=_object_schema(
            {
                "query": STRING,
                "role": {
                    "type": ["string", "null"]
                },
                "top_k": POSITIVE_INTEGER,
            },
            required=("query",),
        ),
    ),
    McpToolDefinition(
        name="memorix_search_cold_history",
        description=(
            "Explicitly search durable cold-site history for audit "
            "purposes. Results are never rehydrated automatically."
        ),
        input_schema=_object_schema(
            {
                "query": STRING,
                "limit": POSITIVE_INTEGER,
            },
            required=("query",),
        ),
    ),
    McpToolDefinition(
        name="memorix_propose_candidate",
        description=(
            "Create a pending memory candidate. This does not write "
            "to the Titan hot site."
        ),
        input_schema=_object_schema(
            {
                "content": STRING,
                "reason": STRING,
                "source_event_ids": {
                    "type": "array",
                    "items": STRING,
                    "minItems": 1,
                },
                "importance": NUMBER_0_1,
                "confidence": NUMBER_0_1,
                "surprise": NUMBER_0_1,
                "target_memory_id": {
                    "type": ["string", "null"]
                },
                "metadata": METADATA_SCHEMA,
            },
            required=(
                "content",
                "reason",
                "source_event_ids",
            ),
        ),
    ),
    McpToolDefinition(
        name="memorix_list_candidates",
        description=(
            "List memory candidates, optionally filtered by pending, "
            "validated, or rejected status."
        ),
        input_schema=_object_schema(
            {
                "status": {
                    "type": ["string", "null"],
                    "enum": [
                        "pending",
                        "validated",
                        "rejected",
                        None,
                    ],
                },
            },
        ),
    ),
    McpToolDefinition(
        name="memorix_validate_candidate",
        description=(
            "Human-validate a pending candidate and store the "
            "validated memory in the Titan hot site only."
        ),
        input_schema=_object_schema(
            {
                "candidate_id": STRING,
                "validated_by": STRING,
                "validation_reason": STRING,
                "final_content": {
                    "type": ["string", "null"]
                },
            },
            required=(
                "candidate_id",
                "validated_by",
                "validation_reason",
            ),
        ),
    ),
    McpToolDefinition(
        name="memorix_reject_candidate",
        description=(
            "Reject a pending candidate without writing anything "
            "to the Titan hot site."
        ),
        input_schema=_object_schema(
            {
                "candidate_id": STRING,
                "rejected_by": STRING,
                "rejection_reason": STRING,
            },
            required=(
                "candidate_id",
                "rejected_by",
                "rejection_reason",
            ),
        ),
    ),
    McpToolDefinition(
        name="memorix_forget_memory",
        description=(
            "Soft-forget one validated memory in the Titan hot site "
            "only. The cold archive is never modified."
        ),
        input_schema=_object_schema(
            {
                "memory_id": STRING,
                "validated_by": STRING,
                "reason": STRING,
            },
            required=(
                "memory_id",
                "validated_by",
                "reason",
            ),
        ),
    ),
    McpToolDefinition(
        name="memorix_run_consolidation",
        description=(
            "Run Titan V2 consolidation over short-term memory and "
            "create pending candidates without automatic validation."
        ),
        input_schema=_object_schema(
            {
                "mode": STRING,
            },
        ),
    ),
    McpToolDefinition(
        name="memorix_run_nightly",
        description=(
            "Run protected nightly consolidation and replay active "
            "hot-site memories while verifying cold-site integrity."
        ),
        input_schema=_object_schema(
            {
                "clear_short_term_after_success": {
                    "type": "boolean"
                },
            },
        ),
    ),
    McpToolDefinition(
        name="memorix_status",
        description=(
            "Return memoriX architecture, storage, candidate, and "
            "Titan status."
        ),
        input_schema=_object_schema({}),
    ),
)


def _require_mapping(
    arguments: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Normalize MCP tool arguments."""

    if arguments is None:
        return {}

    if not isinstance(arguments, Mapping):
        raise McpInvalidArgumentsError(
            "Tool arguments must be a JSON object."
        )

    return dict(arguments)


def _require_text(
    arguments: Mapping[str, Any],
    name: str,
) -> str:
    """Read one required non-empty text argument."""

    value = arguments.get(name)

    if not isinstance(value, str) or not value.strip():
        raise McpInvalidArgumentsError(
            f"{name} must be a non-empty string."
        )

    return value.strip()


def _optional_text(
    arguments: Mapping[str, Any],
    name: str,
) -> str | None:
    """Read one optional text argument."""

    value = arguments.get(name)

    if value is None:
        return None

    if not isinstance(value, str) or not value.strip():
        raise McpInvalidArgumentsError(
            f"{name} must be null or a non-empty string."
        )

    return value.strip()


class MemoriXMcpTools:
    """Dispatch MCP tool calls through MemoriXGateway."""

    def __init__(
        self,
        gateway: MemoriXGateway,
    ) -> None:
        self._gateway = gateway

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all available MCP tools."""

        return [
            definition.to_dict()
            for definition in TOOL_DEFINITIONS
        ]

    def call(
        self,
        name: str,
        arguments: Mapping[str, Any] | None,
    ) -> Any:
        """Execute one named tool."""

        normalized_name = name.strip()

        handlers: dict[
            str,
            Callable[[dict[str, Any]], Any],
        ] = {
            "memorix_record_event": self._record_event,
            "memorix_context": self._context,
            "memorix_search_cold_history": (
                self._search_cold_history
            ),
            "memorix_propose_candidate": (
                self._propose_candidate
            ),
            "memorix_list_candidates": (
                self._list_candidates
            ),
            "memorix_validate_candidate": (
                self._validate_candidate
            ),
            "memorix_reject_candidate": (
                self._reject_candidate
            ),
            "memorix_forget_memory": self._forget_memory,
            "memorix_run_consolidation": (
                self._run_consolidation
            ),
            "memorix_run_nightly": self._run_nightly,
            "memorix_status": self._status,
        }

        handler = handlers.get(normalized_name)

        if handler is None:
            raise McpUnknownToolError(
                f"Unknown MCP tool: {normalized_name}"
            )

        return handler(_require_mapping(arguments))

    def _record_event(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return self._gateway.record_memory_event(
            content=_require_text(arguments, "content"),
            event_type=_require_text(
                arguments,
                "event_type",
            ),
            source=_require_text(arguments, "source"),
            project_id=_optional_text(
                arguments,
                "project_id",
            ),
            session_id=_optional_text(
                arguments,
                "session_id",
            ),
            importance=float(
                arguments.get("importance", 0.5)
            ),
            confidence=float(
                arguments.get("confidence", 1.0)
            ),
            surprise=float(
                arguments.get("surprise", 0.0)
            ),
            metadata=dict(
                arguments.get("metadata") or {}
            ),
        )

    def _context(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        top_k = arguments.get("top_k")

        return self._gateway.retrieve_memory(
            _require_text(arguments, "query"),
            role=_optional_text(arguments, "role"),
            top_k=(
                int(top_k)
                if top_k is not None
                else None
            ),
        )

    def _search_cold_history(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return self._gateway.search_cold_site_history(
            _require_text(arguments, "query"),
            limit=int(arguments.get("limit", 10)),
        )

    def _propose_candidate(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        source_event_ids = arguments.get(
            "source_event_ids"
        )

        if (
            not isinstance(source_event_ids, list)
            or not source_event_ids
            or not all(
                isinstance(item, str)
                and item.strip()
                for item in source_event_ids
            )
        ):
            raise McpInvalidArgumentsError(
                "source_event_ids must be a non-empty "
                "array of strings."
            )

        return self._gateway.propose_memory_candidate(
            content=_require_text(arguments, "content"),
            reason=_require_text(arguments, "reason"),
            source_event_ids=tuple(
                item.strip()
                for item in source_event_ids
            ),
            importance=float(
                arguments.get("importance", 0.5)
            ),
            confidence=float(
                arguments.get("confidence", 0.5)
            ),
            surprise=float(
                arguments.get("surprise", 0.0)
            ),
            target_memory_id=_optional_text(
                arguments,
                "target_memory_id",
            ),
            metadata=dict(
                arguments.get("metadata") or {}
            ),
        )

    def _list_candidates(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        raw_status = arguments.get("status")

        status = (
            CandidateStatus(raw_status)
            if raw_status is not None
            else None
        )

        return self._gateway.list_memory_candidates(
            status=status
        )

    def _validate_candidate(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return self._gateway.validate_memory_candidate(
            _require_text(arguments, "candidate_id"),
            validated_by=_require_text(
                arguments,
                "validated_by",
            ),
            validation_reason=_require_text(
                arguments,
                "validation_reason",
            ),
            final_content=_optional_text(
                arguments,
                "final_content",
            ),
        )

    def _reject_candidate(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return self._gateway.reject_memory_candidate(
            _require_text(arguments, "candidate_id"),
            rejected_by=_require_text(
                arguments,
                "rejected_by",
            ),
            rejection_reason=_require_text(
                arguments,
                "rejection_reason",
            ),
        )

    def _forget_memory(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return self._gateway.forget_memory(
            _require_text(arguments, "memory_id"),
            validated_by=_require_text(
                arguments,
                "validated_by",
            ),
            reason=_require_text(arguments, "reason"),
        )

    def _run_consolidation(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        mode = arguments.get("mode", "manual")

        if not isinstance(mode, str):
            raise McpInvalidArgumentsError(
                "mode must be a string."
            )

        return self._gateway.run_consolidation(
            mode=mode
        )

    def _run_nightly(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        clear = arguments.get(
            "clear_short_term_after_success",
            True,
        )

        if not isinstance(clear, bool):
            raise McpInvalidArgumentsError(
                "clear_short_term_after_success "
                "must be a boolean."
            )

        return (
            self._gateway.run_nightly_consolidation(
                clear_short_term_after_success=clear
            )
        )

    def _status(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        if arguments:
            raise McpInvalidArgumentsError(
                "memorix_status does not accept arguments."
            )

        return self._gateway.memory_status()


def tool_result_payload(value: Any) -> dict[str, Any]:
    """Build a standard MCP tools/call result.

    MCP structuredContent must be a JSON object. Object-shaped values are
    returned directly. Arrays and primitive values are wrapped under "value".
    """

    serialized = to_json_value(value)

    structured_content = (
        serialized
        if isinstance(serialized, dict)
        else {"value": serialized}
    )

    return {
        "content": [
            {
                "type": "text",
                "text": __import__("json").dumps(
                    serialized,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        ],
        "structuredContent": structured_content,
        "isError": False,
    }
