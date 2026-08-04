"""Read-only final release-readiness inspection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_PROJECT_PATHS = (
    "memory/gateway/public_api.py",
    "memory/integrations/mcp/server.py",
    "memory/integrations/mcp/tools.py",
    "packages/opencode/src/memorix/service.ts",
    "packages/opencode/src/tool/registry.ts",
    ".opencode/plugins/memorix.ts",
    "tools/memorix/runtime/start_opencode_with_memorix.ps1",
    "tools/memorix/validation/verify_memorix.ps1",
)


@dataclass(frozen=True, slots=True)
class ReleaseCheck:
    """One deterministic readiness check."""

    name: str
    passed: bool
    details: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class ReleaseReadinessReport:
    """Final read-only readiness report."""

    project_root: str
    runtime_root: str
    status: str
    checks: tuple[ReleaseCheck, ...]
    dry_run: bool = True
    runtime_modified: bool = False
    repository_modified: bool = False
    neural_model_loaded: bool = False

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "runtime_root": self.runtime_root,
            "status": self.status,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "dry_run": self.dry_run,
            "runtime_modified": self.runtime_modified,
            "repository_modified": self.repository_modified,
            "neural_model_loaded": self.neural_model_loaded,
        }


def inspect_release_readiness(
    project_root: str | Path,
    runtime_root: str | Path,
) -> ReleaseReadinessReport:
    """Inspect the final integration without writing or loading Titan."""

    project = Path(project_root).expanduser().resolve()
    runtime = Path(runtime_root).expanduser().resolve()
    forbidden_runtime = (project / "memory" / "runtime").resolve()

    required_missing = tuple(
        relative
        for relative in REQUIRED_PROJECT_PATHS
        if not (project / relative).is_file()
    )
    runtime_outside_repository = not _is_within(runtime, project)
    repository_runtime_absent = not forbidden_runtime.exists()
    plugin_source = _read_optional(project / ".opencode/plugins/memorix.ts")
    launcher_source = _read_optional(project / "tools/memorix/runtime/start_opencode_with_memorix.ps1")

    checks = (
        ReleaseCheck(
            name="project_root",
            passed=project.is_dir(),
            details=str(project),
        ),
        ReleaseCheck(
            name="required_files",
            passed=not required_missing,
            details=(
                "all required files present"
                if not required_missing
                else "missing: " + ", ".join(required_missing)
            ),
        ),
        ReleaseCheck(
            name="runtime_outside_repository",
            passed=runtime_outside_repository,
            details=str(runtime),
        ),
        ReleaseCheck(
            name="repository_runtime_absent",
            passed=repository_runtime_absent,
            details=str(forbidden_runtime),
        ),
        ReleaseCheck(
            name="opencode_hooks",
            passed=(
                '"chat.message"' in plugin_source
                and '"tool.execute.after"' in plugin_source
                and "recordUserMessageHook" in plugin_source
                and "recordToolResultHook" in plugin_source
            ),
            details="message and tool-result hooks are declared",
        ),
        ReleaseCheck(
            name="launcher_memory_activation",
            passed=(
                'MEMORIX_ENABLED = "true"' in launcher_source
                and "MEMORIX_RUNTIME_ROOT" in launcher_source
                and "memorix_mcp_server.py" in launcher_source
            ),
            details="launcher configures memoriX and MCP stdio",
        ),
    )

    passed = all(check.passed for check in checks)
    return ReleaseReadinessReport(
        project_root=str(project),
        runtime_root=str(runtime),
        status="ready" if passed else "blocked",
        checks=checks,
    )


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _read_optional(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8-sig")
