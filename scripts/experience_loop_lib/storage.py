"""External state layout and schema validation."""

from __future__ import annotations

import os
from pathlib import Path
import re
import stat
from typing import Any, Dict, Optional
import uuid

from .common import (
    APP_NAME,
    EXIT_OPERATION_FAILED,
    SCHEMA_VERSION,
    DataCorruptionError,
    ExperienceLoopError,
    FileLock,
    atomic_write_json,
    load_json,
    resolve_home,
    utc_now,
)


class Store:
    MANAGED_TOP_LEVEL = {
        "state.json",
        "controls.json",
        "profile.json",
        "projects",
        "ledger",
        "knowledge",
        "archives",
    }
    HOME_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

    def __init__(self, home: Optional[str] = None):
        self.home = resolve_home(home)
        self.state_path = self.home / "state.json"
        self.controls_path = self.home / "controls.json"
        self.profile_path = self.home / "profile.json"
        self.projects_dir = self.home / "projects"
        self.projects_index_path = self.projects_dir / "index.json"
        self.ledger_dir = self.home / "ledger"
        self.ledger_path = self.ledger_dir / "events.jsonl"
        self.knowledge_dir = self.home / "knowledge"
        self.archives_dir = self.home / "archives"
        # Keep the operating-system lock outside the directory that import may
        # transactionally replace.
        self.lock_path = self.home.parent / (self.home.name + ".lock")

    def lock(self) -> FileLock:
        return FileLock(self.lock_path)

    def is_initialized(self) -> bool:
        return self.state_path.is_file()

    def _is_protected_target(self) -> bool:
        resolved = self.home.resolve(strict=False)
        anchor = Path(resolved.anchor).resolve(strict=False)
        user_home = Path.home().resolve(strict=False)
        return resolved == anchor or resolved == user_home

    def _assert_safe_new_home(self) -> None:
        if self._is_protected_target():
            raise ExperienceLoopError(
                "拒绝把文件系统根目录或用户主目录作为 Experience Loop HOME；请使用专用子目录。",
                code=EXIT_OPERATION_FAILED,
                details={"home": str(self.home)},
            )
        if not self.home.exists():
            return
        if not self.home.is_dir():
            raise ExperienceLoopError(
                "Experience Loop HOME 不是目录：%s" % self.home,
                code=EXIT_OPERATION_FAILED,
            )
        try:
            entries = sorted(path.name for path in self.home.iterdir())
        except OSError as exc:
            raise ExperienceLoopError(
                "无法检查 Experience Loop HOME：%s" % exc,
                code=EXIT_OPERATION_FAILED,
                details={"home": str(self.home)},
            ) from exc
        if entries:
            raise ExperienceLoopError(
                "目标目录已有非 Experience Loop 内容；为防止覆盖，请选择新的专用子目录。",
                code=EXIT_OPERATION_FAILED,
                details={"home": str(self.home), "entries": entries[:20]},
            )

    @staticmethod
    def _make_private(path: Path, mode: int) -> None:
        if os.name == "nt" or not path.exists() or path.is_symlink():
            return
        try:
            path.chmod(mode)
        except OSError:
            pass

    def ensure_layout(self) -> None:
        for path in (
            self.home,
            self.projects_dir,
            self.ledger_dir,
            self.knowledge_dir,
            self.archives_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
            self._make_private(path, 0o700)

    def harden_known_permissions(self, *, deep: bool = False) -> None:
        """Best-effort POSIX privacy for known state and knowledge paths."""

        if os.name == "nt":
            return
        for directory in (
            self.home,
            self.projects_dir,
            self.ledger_dir,
            self.knowledge_dir,
            self.archives_dir,
            self.knowledge_dir / "objects",
            self.knowledge_dir / "objects" / "sha256",
        ):
            self._make_private(directory, 0o700)
        for path in (
            self.state_path,
            self.controls_path,
            self.profile_path,
            self.projects_index_path,
            self.ledger_path,
            self.knowledge_dir / "library.sqlite",
        ):
            self._make_private(path, 0o600)
        if deep and self.knowledge_dir.is_dir():
            for path in self.knowledge_dir.rglob("*"):
                self._make_private(path, 0o700 if path.is_dir() else 0o600)

    def permission_issues(self, *, deep: bool = False) -> list:
        if os.name == "nt":
            return []
        paths = [
            self.home,
            self.projects_dir,
            self.ledger_dir,
            self.knowledge_dir,
            self.archives_dir,
            self.state_path,
            self.controls_path,
            self.profile_path,
            self.projects_index_path,
            self.ledger_path,
            self.knowledge_dir / "library.sqlite",
        ]
        if deep and self.home.is_dir():
            paths.extend(self.home.rglob("*"))
        issues = []
        seen = set()
        for path in paths:
            if path in seen or not path.exists() or path.is_symlink():
                continue
            seen.add(path)
            try:
                mode = stat.S_IMODE(path.stat().st_mode)
            except OSError:
                continue
            if mode & 0o077:
                issues.append({"path": str(path), "mode": oct(mode)})
        return issues

    def assert_managed_home(self) -> Dict[str, Any]:
        """Require a dedicated, valid HOME before destructive replacement."""

        state = self.require_initialized()
        if self._is_protected_target():
            raise ExperienceLoopError(
                "拒绝替换文件系统根目录或用户主目录。",
                code=EXIT_OPERATION_FAILED,
                details={"home": str(self.home)},
            )
        try:
            unknown = sorted(
                path.name
                for path in self.home.iterdir()
                if path.name not in self.MANAGED_TOP_LEVEL
            )
        except OSError as exc:
            raise ExperienceLoopError(
                "无法核验目标数据目录：%s" % exc,
                code=EXIT_OPERATION_FAILED,
                details={"home": str(self.home)},
            ) from exc
        if unknown:
            raise ExperienceLoopError(
                "目标目录含非受管顶层内容，拒绝整体替换。请先移出这些文件。",
                code=EXIT_OPERATION_FAILED,
                details={"home": str(self.home), "unknown_entries": unknown[:20]},
            )
        return state

    def initialize(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            # Reject dangerous/non-dedicated targets before even creating the
            # sibling lock file.
            self._assert_safe_new_home()
        self.home.parent.mkdir(parents=True, exist_ok=True)
        with self.lock():
            existing = load_json(self.state_path, missing=None)
            if existing is None:
                self._assert_safe_new_home()
                self.ensure_layout()
                now = utc_now()
                state = {
                    "application": APP_NAME,
                    "schema_version": SCHEMA_VERSION,
                    "managed_home": True,
                    "home_id": uuid.uuid4().hex,
                    "created_at": now,
                    "updated_at": now,
                }
                atomic_write_json(self.state_path, state)
            else:
                state = self.validate_state(existing)
                self.ensure_layout()
            if not self.projects_index_path.exists():
                atomic_write_json(
                    self.projects_index_path,
                    {"schema_version": SCHEMA_VERSION, "projects": {}},
                )
            if not self.ledger_path.exists():
                self.ledger_path.touch()
            self.harden_known_permissions()
        return state

    def require_initialized(self) -> Dict[str, Any]:
        if not self.is_initialized():
            raise ExperienceLoopError(
                "Experience Loop 尚未初始化。请先运行 setup。",
                details={"home": str(self.home), "next_command": "setup"},
            )
        state = load_json(self.state_path)
        return self.validate_state(state)

    def validate_state(self, state: Any) -> Dict[str, Any]:
        if not isinstance(state, dict):
            raise DataCorruptionError("state.json 必须是 JSON 对象。")
        if state.get("application") != APP_NAME:
            raise DataCorruptionError("数据目录不是有效的 Experience Loop 状态目录。")
        if state.get("managed_home") is not True:
            raise DataCorruptionError("state.json 缺少受管数据目录标记。")
        home_id = state.get("home_id")
        if not isinstance(home_id, str) or not self.HOME_ID_PATTERN.match(home_id):
            raise DataCorruptionError("state.json 的 home_id 无效。")
        version = state.get("schema_version")
        if version != SCHEMA_VERSION:
            raise DataCorruptionError(
                "不支持的数据版本：%r（当前支持 %s）。" % (version, SCHEMA_VERSION),
                {"found": version, "supported": SCHEMA_VERSION},
            )
        return state

    def touch_state(self) -> None:
        with self.lock():
            self.touch_state_locked()

    def touch_state_locked(self) -> None:
        """Update the state timestamp while the caller holds the store lock."""
        state = self.require_initialized()
        state["updated_at"] = utc_now()
        atomic_write_json(self.state_path, state)

    def load_projects_index(self) -> Dict[str, Any]:
        self.require_initialized()
        value = load_json(self.projects_index_path, missing=None)
        if value is None:
            raise DataCorruptionError("项目索引缺失。请运行 doctor --repair。")
        if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
            raise DataCorruptionError("项目索引格式或版本无效。")
        projects = value.get("projects")
        if not isinstance(projects, dict):
            raise DataCorruptionError("项目索引中的 projects 必须是对象。")
        return value

    def save_projects_index(self, value: Dict[str, Any]) -> None:
        value["schema_version"] = SCHEMA_VERSION
        atomic_write_json(self.projects_index_path, value)

    def project_path(self, project_id: str) -> Path:
        return self.projects_dir / (project_id + ".json")
