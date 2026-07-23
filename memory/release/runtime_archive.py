"""Portable, verified backup and restore for a memoriX runtime."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from memory.release.path_safety import validate_destructive_runtime_path


MANIFEST_NAME = "memorix-runtime-manifest.json"
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class RuntimeArchiveManifest:
    """Manifest stored alongside runtime files in a backup archive."""

    schema_version: int
    created_at: str
    file_count: int
    total_bytes: int
    files: tuple[tuple[str, int, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "files": [
                {
                    "path": path,
                    "size": size,
                    "sha256": digest,
                }
                for path, size, digest in self.files
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeArchiveManifest":
        files = tuple(
            (
                str(item["path"]),
                int(item["size"]),
                str(item["sha256"]),
            )
            for item in payload.get("files", ())
        )
        return cls(
            schema_version=int(payload["schema_version"]),
            created_at=str(payload["created_at"]),
            file_count=int(payload["file_count"]),
            total_bytes=int(payload["total_bytes"]),
            files=files,
        )


def create_runtime_backup(
    runtime_root: str | Path,
    destination: str | Path,
) -> RuntimeArchiveManifest:
    """Create a deterministic ZIP backup with per-file SHA-256 hashes."""

    runtime = Path(runtime_root).expanduser().resolve()
    target = Path(destination).expanduser().resolve()
    if not runtime.is_dir():
        raise FileNotFoundError(f"Runtime directory not found: {runtime}")
    if _is_within(target, runtime):
        raise ValueError("Backup destination must remain outside the runtime.")

    entries = tuple(
        path
        for path in sorted(runtime.rglob("*"))
        if path.is_file()
    )
    files = tuple(
        (
            path.relative_to(runtime).as_posix(),
            path.stat().st_size,
            _sha256_file(path),
        )
        for path in entries
    )
    manifest = RuntimeArchiveManifest(
        schema_version=SCHEMA_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(),
        file_count=len(files),
        total_bytes=sum(size for _, size, _ in files),
        files=files,
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(
            temporary,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in entries:
                archive.write(path, path.relative_to(runtime).as_posix())
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(
                    manifest.to_dict(),
                    indent=2,
                    sort_keys=True,
                ),
            )
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def inspect_runtime_backup(
    archive_path: str | Path,
) -> RuntimeArchiveManifest:
    """Validate archive structure, manifest, sizes, and hashes."""

    archive_file = Path(archive_path).expanduser().resolve()
    with zipfile.ZipFile(archive_file, mode="r") as archive:
        names = tuple(info.filename for info in archive.infolist())
        if MANIFEST_NAME not in names:
            raise ValueError("Runtime backup manifest is missing.")
        for name in names:
            _validate_archive_name(name)
        payload = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        manifest = RuntimeArchiveManifest.from_dict(payload)
        if manifest.schema_version != SCHEMA_VERSION:
            raise ValueError("Unsupported runtime backup schema version.")
        expected_names = {path for path, _, _ in manifest.files}
        actual_names = {name for name in names if name != MANIFEST_NAME}
        if actual_names != expected_names:
            raise ValueError("Runtime backup entries do not match the manifest.")
        for path, size, digest in manifest.files:
            content = archive.read(path)
            if len(content) != size:
                raise ValueError(f"Runtime backup size mismatch: {path}")
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"Runtime backup hash mismatch: {path}")
        if manifest.file_count != len(manifest.files):
            raise ValueError("Runtime backup file count is inconsistent.")
        if manifest.total_bytes != sum(size for _, size, _ in manifest.files):
            raise ValueError("Runtime backup byte count is inconsistent.")
        return manifest


def restore_runtime_backup(
    archive_path: str | Path,
    runtime_root: str | Path,
    *,
    overwrite: bool = False,
) -> RuntimeArchiveManifest:
    """Restore a verified archive through a temporary directory."""

    archive_file = Path(archive_path).expanduser().resolve()
    destination = validate_destructive_runtime_path(runtime_root, project_root=Path(__file__).resolve().parents[2])
    manifest = inspect_runtime_backup(archive_file)
    if destination.exists() and any(destination.iterdir()) and not overwrite:
        raise FileExistsError(
            "Runtime destination is not empty; pass overwrite=True explicitly."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix="memorix-restore-",
            dir=destination.parent,
        )
    )
    try:
        with zipfile.ZipFile(archive_file, mode="r") as archive:
            for path, _, _ in manifest.files:
                target = temporary / PurePosixPath(path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(path))
        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest


def _validate_archive_name(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe runtime backup entry: {name}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
