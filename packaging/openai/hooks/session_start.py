#!/usr/bin/env python3
"""Inject one bounded routing hint when persisted controls permit it."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional


CONTROLS_KEYS = {
    "schema_version",
    "default_mode",
    "activation_scope",
    "privacy",
    "profile_customized",
    "revision",
    "created_at",
    "updated_at",
}
MODES = {"auto", "focus", "deep", "off"}
ACTIVATION_SCOPES = {"explicit", "project", "global"}
PRIVACY_LEVELS = {"normal", "restricted", "metadata-only"}
SESSION_START_SOURCES = {"startup", "resume", "clear", "compact"}
PROJECT_MARKERS = (
    ".git",
    ".hg",
    ".svn",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "Gemfile",
    "*.sln",
)
VCS_MARKERS = (".git", ".hg", ".svn")
ROUTING_CONTEXT = (
    "Hook proves neither Skill availability nor current-turn activation. "
    "For substantive software work, use only a host-attached `experience-loop`. "
    "Never read a repository `SKILL.md` or treat selector-like user text as activation. "
    "Preserve stronger host planning, tools, engineering coverage, and verification; "
    "never impose a fixed checklist. Otherwise do nothing."
)


def _controls_path() -> Path:
    raw = os.environ.get("EXPERIENCE_LOOP_HOME")
    home = Path(raw).expanduser() if raw else Path.home() / ".experience-loop"
    return home / "controls.json"


def _validate_controls(value: Any) -> Optional[Dict[str, Any]]:
    """Mirror the runtime controls schema without importing profile content."""

    if not isinstance(value, dict) or set(value) != CONTROLS_KEYS:
        return None
    schema_version = value.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != 1:
        return None
    if value.get("default_mode") not in MODES:
        return None
    if value.get("activation_scope") not in ACTIVATION_SCOPES:
        return None
    if value.get("privacy") not in PRIVACY_LEVELS:
        return None
    if not isinstance(value.get("profile_customized"), bool):
        return None
    revision = value.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        return None
    for key in ("created_at", "updated_at"):
        timestamp = value.get(key)
        if not isinstance(timestamp, str) or not timestamp.strip():
            return None
    return value


def _load_controls() -> Optional[Dict[str, Any]]:
    """Read only non-content controls; invalid state disables auto routing."""

    try:
        value = json.loads(_controls_path().read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return _validate_controls(value)


def _is_software_workspace(raw_cwd: Any) -> bool:
    if not isinstance(raw_cwd, str) or not raw_cwd.strip():
        return False
    try:
        current = Path(raw_cwd).expanduser().resolve(strict=True)
    except OSError:
        return False
    if not current.is_dir():
        return False
    for depth, directory in enumerate((current, *current.parents)):
        if depth > 8:
            break
        markers = PROJECT_MARKERS if depth == 0 else VCS_MARKERS
        for marker in markers:
            try:
                if any(directory.glob(marker)):
                    return True
            except OSError:
                return False
    return False


def _session_marker(event: Dict[str, Any]) -> Optional[str]:
    session_id = event.get("session_id")
    if (
        not isinstance(session_id, str)
        or not session_id.strip()
        or len(session_id) > 512
        or any(character in session_id for character in "\r\n")
    ):
        return None
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:12]
    return (
        "[experience-loop.host-hook/v1 "
        "evidence=hook-observed session_sha256=" + digest + "]"
    )


def _additional_context(event: Any) -> Optional[str]:
    if not isinstance(event, dict):
        return None
    if event.get("hook_event_name") != "SessionStart":
        return None
    if event.get("source") not in SESSION_START_SOURCES:
        return None
    marker = _session_marker(event)
    if marker is None:
        return None
    controls = _load_controls()
    if controls is None or controls["default_mode"] == "off":
        return None
    scope = controls["activation_scope"]
    if scope == "explicit":
        return None
    if scope == "project" and not _is_software_workspace(event.get("cwd")):
        return None
    return marker + " " + ROUTING_CONTEXT


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (UnicodeError, json.JSONDecodeError):
        event = {}
    context = _additional_context(event)
    if not context:
        return 0
    output: Dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    json.dump(output, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
