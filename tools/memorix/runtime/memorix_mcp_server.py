"""Launch the memoriX MCP stdio server from the repository root."""

from __future__ import annotations

from pathlib import Path
import sys


MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.integrations.mcp.server import main


if __name__ == "__main__":
    raise SystemExit(main())
