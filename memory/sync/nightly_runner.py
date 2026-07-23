"""Operational wrapper for protected memoriX nightly consolidation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import tempfile
import time
from typing import Any
from uuid import uuid4

from memory.data.jsonl_store import append_json_line
from memory.data.paths import MEMORY_PACKAGE_ROOT, MemoryStoragePaths
from memory.gateway.public_api import MemoriXGateway

EXIT_COMPLETED = 0
EXIT_VALIDATION = 2
EXIT_ALREADY_RUNNING = 3
EXIT_LOCK_ERROR = 4
EXIT_FAILED = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repository_root() -> Path:
    return MEMORY_PACKAGE_ROOT.parent.resolve()


def validate_runtime_root(runtime_root: str | Path) -> Path:
    root = Path(runtime_root).expanduser().resolve()
    repo = _repository_root()
    try:
        root.relative_to(repo)
    except ValueError:
        pass
    else:
        raise ValueError("The memoriX runtime root must remain outside the repository.")
    return root


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@dataclass(slots=True)
class NightlyRunResult:
    exit_code: int
    payload: dict[str, Any]


class NightlyAlreadyRunningError(RuntimeError):
    pass


class NightlyLockError(RuntimeError):
    pass


class NightlyLock:
    def __init__(self, path: Path, *, timeout_hours: float, runtime_root: Path) -> None:
        self.path = path
        self.timeout_seconds = timeout_hours * 3600
        self.runtime_root = runtime_root
        self.run_id = str(uuid4())
        self.recovered_stale_lock = False

    def acquire(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'run_id': self.run_id,
            'pid': os.getpid(),
            'hostname': socket.gethostname(),
            'started_at': _utc_now(),
            'runtime_root': str(self.runtime_root),
        }
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except FileExistsError:
            self._recover_or_raise()
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        return payload

    def _recover_or_raise(self) -> None:
        try:
            existing = json.loads(self.path.read_text(encoding='utf-8'))
            stat = self.path.stat()
        except Exception as exc:
            raise NightlyLockError('The existing nightly lock is unreadable.') from exc
        age = max(0.0, time.time() - stat.st_mtime)
        same_host = existing.get('hostname') == socket.gethostname()
        pid = int(existing.get('pid', -1))
        if age <= self.timeout_seconds or not same_host or _pid_alive(pid):
            raise NightlyAlreadyRunningError('A nightly consolidation is already running.')
        self.path.unlink()
        self.recovered_stale_lock = True

    def release(self) -> None:
        try:
            existing = json.loads(self.path.read_text(encoding='utf-8'))
        except FileNotFoundError:
            return
        except Exception:
            return
        if existing.get('run_id') == self.run_id:
            self.path.unlink(missing_ok=True)


class NightlyRunner:
    def __init__(self, runtime_root: str | Path, *, lock_timeout_hours: float = 6) -> None:
        self.runtime_root = validate_runtime_root(runtime_root)
        self.paths = MemoryStoragePaths.from_runtime_root(self.runtime_root)
        if lock_timeout_hours <= 0:
            raise ValueError('lock_timeout_hours must be positive.')
        self.lock_timeout_hours = float(lock_timeout_hours)

    def latest_status(self) -> dict[str, Any] | None:
        if not self.paths.nightly_latest.exists():
            return None
        return json.loads(self.paths.nightly_latest.read_text(encoding='utf-8'))

    def run(self, *, clear_short_term_after_success: bool = True, trigger: str = 'manual') -> NightlyRunResult:
        if not isinstance(clear_short_term_after_success, bool):
            raise TypeError('clear_short_term_after_success must be a boolean.')
        trigger = trigger.strip()
        if trigger not in {'manual', 'task_scheduler', 'opencode'}:
            raise ValueError('trigger must be manual, task_scheduler, or opencode.')
        lock = NightlyLock(self.paths.nightly_lock, timeout_hours=self.lock_timeout_hours, runtime_root=self.runtime_root)
        started_at = _utc_now()
        started_monotonic = time.monotonic()
        try:
            lock.acquire()
        except NightlyAlreadyRunningError as exc:
            payload = {'run_id': lock.run_id, 'status': 'already_running', 'started_at': started_at, 'completed_at': _utc_now(), 'trigger': trigger, 'runtime_root': str(self.runtime_root), 'message': str(exc)}
            append_json_line(self.paths.nightly_runs, payload)
            _atomic_write_json(self.paths.nightly_latest, payload)
            return NightlyRunResult(EXIT_ALREADY_RUNNING, payload)
        except NightlyLockError as exc:
            payload = {'run_id': lock.run_id, 'status': 'validation_failed', 'started_at': started_at, 'completed_at': _utc_now(), 'trigger': trigger, 'runtime_root': str(self.runtime_root), 'message': str(exc)}
            append_json_line(self.paths.nightly_runs, payload)
            _atomic_write_json(self.paths.nightly_latest, payload)
            return NightlyRunResult(EXIT_LOCK_ERROR, payload)

        started = {'run_id': lock.run_id, 'status': 'started', 'started_at': started_at, 'trigger': trigger, 'runtime_root': str(self.runtime_root), 'clear_short_term_after_success': clear_short_term_after_success, 'recovered_stale_lock': lock.recovered_stale_lock}
        append_json_line(self.paths.nightly_runs, started)
        try:
            report = MemoriXGateway(storage_paths=self.paths).run_nightly_consolidation(clear_short_term_after_success=clear_short_term_after_success)
            report_dict = report.to_dict()
            consolidation = report_dict.get('consolidation', {})
            payload = {
                **started,
                'status': 'completed',
                'completed_at': _utc_now(),
                'duration_seconds': round(time.monotonic() - started_monotonic, 6),
                'candidates_created': consolidation.get('candidates_created', 0),
                'active_memories_replayed': report.active_memories_replayed,
                'short_term_events_cleared': report.short_term_events_cleared,
                'cold_site_modified': report.cold_site_modified,
                'automatic_candidate_validation': report.automatic_candidate_validation,
            }
            append_json_line(self.paths.nightly_runs, payload)
            _atomic_write_json(self.paths.nightly_latest, payload)
            return NightlyRunResult(EXIT_COMPLETED, payload)
        except Exception as exc:
            payload = {**started, 'status': 'failed', 'completed_at': _utc_now(), 'duration_seconds': round(time.monotonic() - started_monotonic, 6), 'error_type': type(exc).__name__, 'message': str(exc)}
            append_json_line(self.paths.nightly_runs, payload)
            _atomic_write_json(self.paths.nightly_latest, payload)
            return NightlyRunResult(EXIT_FAILED, payload)
        finally:
            lock.release()
