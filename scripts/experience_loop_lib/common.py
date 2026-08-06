"""Shared constants and safe filesystem helpers."""

from __future__ import annotations

import contextlib
import datetime as _datetime
import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


APP_NAME = "experience-loop"
VERSION = "0.1.0"
SCHEMA_VERSION = 1

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARTIAL = 3
EXIT_OPERATION_FAILED = 4
EXIT_DEPENDENCY = 5
EXIT_CORRUPT = 6
EXIT_IO = 7
EXIT_UNEXPECTED = 10

MODES = ("auto", "focus", "off")
LEGACY_MODE_ALIASES = {
    "ship": "auto",
    "coach": "focus",
    "deep": "focus",
    "incident": "auto",
}
CAPABILITIES = (
    "problem-framing",
    "system-modeling",
    "verification",
    "reliability",
    "agent-leverage",
    "ownership",
)


class ExperienceLoopError(Exception):
    """Expected user-facing failure with a stable process exit code."""

    def __init__(self, message: str, code: int = EXIT_USAGE, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class DataCorruptionError(ExperienceLoopError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, EXIT_CORRUPT, details)


class DependencyError(ExperienceLoopError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, EXIT_DEPENDENCY, details)


def normalize_mode(value: str) -> str:
    """Return one of the three user-facing modes, accepting legacy aliases."""
    cleaned = str(value).strip().lower()
    normalized = LEGACY_MODE_ALIASES.get(cleaned, cleaned)
    if normalized not in MODES:
        raise ExperienceLoopError(
            "未知模式：%s。可用模式为 auto、focus、off。" % value
        )
    return normalized


def resolve_home(explicit: Optional[str] = None) -> Path:
    raw = explicit or os.environ.get("EXPERIENCE_LOOP_HOME")
    if raw:
        return Path(raw).expanduser().resolve()
    return (Path.home() / ".experience-loop").resolve()


def utc_now() -> str:
    """Return deterministic UTC time when EXPERIENCE_LOOP_NOW is set for tests."""
    overridden = os.environ.get("EXPERIENCE_LOOP_NOW")
    if overridden:
        candidate = overridden.strip()
        try:
            parsed = _datetime.datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ExperienceLoopError(
                "EXPERIENCE_LOOP_NOW 必须是 ISO-8601 时间，例如 2026-08-05T12:00:00Z。"
            ) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_datetime.timezone.utc)
        return parsed.astimezone(_datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return _datetime.datetime.now(_datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(prefix: str, value: str, length: int = 16) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()
    return "%s_%s" % (prefix, digest[:length])


def load_json(path: Path, *, missing: Any = None) -> Any:
    if not path.exists():
        return missing
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DataCorruptionError(
            "无法读取数据文件：%s" % path,
            {"path": str(path), "reason": str(exc)},
        ) from exc


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = -1
    temporary_name = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".%s." % path.name,
            suffix=".tmp",
            dir=str(path.parent),
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, str(path))
        temporary_name = None
    except OSError as exc:
        raise ExperienceLoopError(
            "写入失败：%s" % path,
            EXIT_IO,
            {"path": str(path), "reason": str(exc)},
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_name:
            with contextlib.suppress(OSError):
                os.unlink(temporary_name)


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


class FileLock:
    """Cross-process advisory lock released automatically on process exit.

    A persistent lock file is intentional. The operating system owns the
    actual lock, so a long-running import cannot be mistaken for a dead owner
    merely because a timestamp became old.
    """

    def __init__(self, path: Path, timeout: float = 5.0, stale_after: float = 120.0):
        self.path = path
        self.timeout = timeout
        self.stale_after = stale_after
        self._owned = False
        self._handle = None  # type: Any
        self._token = None  # type: Optional[str]

    @staticmethod
    def _try_lock(handle: Any) -> None:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock(handle: Any) -> None:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def __enter__(self) -> "FileLock":
        deadline = time.monotonic() + self.timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            handle = self.path.open("a+b")
            if os.name != "nt":
                with contextlib.suppress(OSError):
                    self.path.chmod(0o600)
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            self._handle = handle
        except OSError as exc:
            raise ExperienceLoopError(
                "无法打开数据目录锁。",
                EXIT_IO,
                {"lock": str(self.path), "reason": str(exc)},
            ) from exc
        while True:
            try:
                self._try_lock(self._handle)
                self._owned = True
                self._token = uuid.uuid4().hex
                metadata = json.dumps(
                    {
                        "pid": os.getpid(),
                        "owner_token": self._token,
                        "acquired_at": utc_now(),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode("utf-8")
                self._handle.seek(1)
                self._handle.truncate()
                self._handle.write(metadata)
                self._handle.flush()
                os.fsync(self._handle.fileno())
                return self
            except (OSError, BlockingIOError):
                if time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    raise ExperienceLoopError(
                        "数据目录正被另一个 Experience Loop 进程使用。",
                        EXIT_IO,
                        {"lock": str(self.path)},
                    )
                time.sleep(0.05)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        handle = self._handle
        self._handle = None
        try:
            if self._owned and handle is not None:
                with contextlib.suppress(OSError):
                    self._unlock(handle)
        finally:
            if handle is not None:
                handle.close()
            self._owned = False
            self._token = None


@contextlib.contextmanager
def null_lock() -> Iterator[None]:
    yield
