from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

# Default taxonomy with the categories expected by tests
_DEFAULT_TAXONOMY: Dict[str, Dict[str, str]] = {
    "TECH_API_TIMEOUT": {
        "description": "API request timed out",
        "regex": r"(?i)api\s+(request\s+)?timed?\s*out|connection\s+timeout",
    },
    "TECH_API_AUTH": {
        "description": "API authentication failure",
        "regex": r"(?i)401\s+unauthorized|invalid\s+api\s+key|auth(?:entication)?\s+(fail|error|denied)",
    },
    "TECH_HOST_OOM": {
        "description": "Host out-of-memory",
        "regex": r"(?i)out\s+of\s+memory|oom|killed\s+by\s+.*oom",
    },
    "TECH_MCP_CRASH": {
        "description": "MCP server crash",
        "regex": r"(?i)mcp\s+(server\s+)?(process\s+)?(crash|died|segfault|sigsegv)",
    },
    "AGENT_TOOL_HALLUCINATION": {
        "description": "Agent called non-existent tool",
        "regex": r"(?i)(called|invoked|used)\s+(non.?existent|unknown|invalid)\s+tool",
    },
    "AGENT_BASH_RECOVERY_FAIL": {
        "description": "Agent failed to recover from bash failure",
        "regex": r"(?i)failed\s+to\s+recover.*bash|bash.*recovery\s+fail",
    },
    "AGENT_LOGIC_LOOP": {
        "description": "Agent entered infinite loop",
        "regex": r"(?i)(entered?\s+)?infinite\s+(logic\s+)?loop|repeated\s+same\s+action\s+\d+",
    },
    "AGENT_CONSTRAINT_VIOLATION": {
        "description": "Agent violated a system constraint",
        "regex": r"(?i)violated?\s+(system\s+)?constraint|outside\s+(workspace\s+)?boundary",
    },
    "AGENT_FINAL_INCORRECT": {
        "description": "Agent produced incorrect final output",
        "regex": r"(?i)(produced?\s+)?incorrect\s+final\s+output|expected\s+\d+\s+got\s+\d+",
    },
    "MEM_CURATION_LOSS": {
        "description": "Memory curation loss during consolidation",
        "regex": r"(?i)memory\s+curation\s+loss|consolidated?\s+facts?\s+diverged",
    },
    "MEM_RETRIEVAL_LOSS": {
        "description": "Memory retrieval returned irrelevant results",
        "regex": r"(?i)memory\s+retrieval\s+loss|memory_retrieve\s+returned\s+irrelevant",
    },
}


def load_taxonomy(config_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Load failure taxonomy from a JSON file, falling back to defaults."""
    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("categories", data)

    return dict(_DEFAULT_TAXONOMY)


# Compiled regex patterns
_TAXONOMY = load_taxonomy()
_COMPILED: Dict[str, re.Pattern[str]] = {}
for _cat, _info in _TAXONOMY.items():
    _pattern = _info.get("regex", "")
    if _pattern:
        _COMPILED[_cat] = re.compile(_pattern)


def classify_failure(error_text: str) -> str:
    """Classify an error message into a failure category.

    Returns the category string (e.g. 'TECH_API_TIMEOUT') or 'UNCLASSIFIED'.
    """
    if not error_text or not error_text.strip():
        return "UNCLASSIFIED"

    normalized = error_text.strip()

    # Check in priority order: TECH_*, AGENT_*, MEM_*
    priority_prefixes = ["TECH_", "AGENT_", "MEM_"]
    for prefix in priority_prefixes:
        for category, pattern in _COMPILED.items():
            if not category.startswith(prefix):
                continue
            if pattern.search(normalized):
                return category

    return "UNCLASSIFIED"


def is_retryable(category: str) -> bool:
    """Return True if the failure category is retryable (TECH_* only)."""
    return category.startswith("TECH_")
