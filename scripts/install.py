#!/usr/bin/env python3
"""Install Experience Loop into the current user's Codex skill directory.

The installer copies only runtime files. Personal data always lives outside the
skill directory and is therefore untouched by installs and upgrades.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Optional, Union
from uuid import uuid4


SKILL_NAME = "experience-loop"
RUNTIME_ENTRIES = (
    "SKILL.md",
    "LICENSE",
    "VERSION",
    "agents",
    "assets",
    "references",
    "scripts",
    "vendor",
    "licenses",
    "THIRD_PARTY_NOTICES.md",
)
MARKER_NAME = ".experience-loop-install.json"
REQUIRED_INSTALL_FILES = (
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "scripts/experience_loop.py",
    "scripts/uninstall.py",
)
BACKUP_DIRECTORY_NAME = "skill-backups"


def default_target() -> Path:
    return Path.home() / ".agents" / "skills" / SKILL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install Experience Loop as a user-level Codex skill."
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=default_target(),
        help="Installation directory (default: ~/.agents/skills/experience-loop).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate and show the target only."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an unrecognized existing directory after preserving a backup.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_source(root: Path) -> None:
    required = tuple(root / relative for relative in REQUIRED_INSTALL_FILES)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Skill source is incomplete: " + ", ".join(missing))
    if read_skill_name(root) != SKILL_NAME:
        raise RuntimeError(f"Skill source does not declare name: {SKILL_NAME}")


def normalized_target(path: Path) -> Path:
    """Return an absolute lexical path without following the final entry."""

    expanded = os.path.expanduser(str(path))
    return Path(os.path.abspath(expanded))


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _is_reparse_point(path: Path) -> bool:
    try:
        value = os.lstat(str(path))
    except OSError:
        return False
    if stat.S_ISLNK(value.st_mode):
        return True
    attributes = getattr(value, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def validate_target_path(path: Path) -> Path:
    """Reject paths whose removal or replacement could affect a broad directory."""

    target = normalized_target(path)
    anchor = Path(target.anchor)
    dangerous = (
        anchor,
        normalized_target(Path.home()),
        normalized_target(Path.home() / ".agents"),
        normalized_target(Path.home() / ".agents" / "skills"),
    )
    if any(_same_path(target, candidate) for candidate in dangerous):
        raise RuntimeError(f"Refusing dangerous installation target: {target}")
    if target.name.casefold() != SKILL_NAME.casefold():
        raise RuntimeError(
            f"Installation target must end with '{SKILL_NAME}': {target}"
        )
    if target.parent == target or target.parent.parent == target.parent:
        raise RuntimeError(f"Installation target is too close to a filesystem root: {target}")
    if target.exists() and _is_reparse_point(target):
        raise RuntimeError(f"Refusing symlink, junction, or reparse-point target: {target}")
    return target


def read_skill_name(path: Path) -> Optional[str]:
    skill_file = path / "SKILL.md"
    if not skill_file.is_file() or _is_reparse_point(skill_file):
        return None
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    declared_name: Optional[str] = None
    for line in lines[1:]:
        if line.strip() == "---":
            return declared_name
        key, separator, value = line.partition(":")
        if separator and key.strip() == "name":
            declared_name = value.strip().strip("\"'")
    return None


def read_marker(path: Path) -> Optional[dict[str, Any]]:
    marker = path / MARKER_NAME
    if not marker.is_file() or _is_reparse_point(marker):
        return None
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("skill") != SKILL_NAME:
        return None
    return value


def has_required_runtime(path: Path) -> bool:
    for relative in REQUIRED_INSTALL_FILES:
        item = path / relative
        if not item.is_file() or _is_reparse_point(item):
            return False
    return read_skill_name(path) == SKILL_NAME


def managed_install_validation_error(path: Path) -> Optional[str]:
    if not path.is_dir():
        return "The target is not a directory."
    if _is_reparse_point(path):
        return "The target is a symlink, junction, or reparse point."
    if read_marker(path) is None:
        return (
            f"{MARKER_NAME} is missing, invalid JSON, or does not declare "
            f"skill == {SKILL_NAME}."
        )
    if read_skill_name(path) != SKILL_NAME:
        return f"SKILL.md does not declare name: {SKILL_NAME}."
    missing = [
        relative
        for relative in REQUIRED_INSTALL_FILES
        if not (path / relative).is_file() or _is_reparse_point(path / relative)
    ]
    if missing:
        return "Required installed files are missing or unsafe: " + ", ".join(missing)
    return None


def is_managed_install(path: Path) -> bool:
    return managed_install_validation_error(path) is None


def is_legacy_install(path: Path) -> bool:
    """Recognize a pre-marker install without weakening uninstall validation."""

    return (
        path.is_dir()
        and not (path / MARKER_NAME).exists()
        and has_required_runtime(path)
    )


def is_discoverable_experience_loop(path: Path) -> bool:
    return path.is_dir() and read_skill_name(path) == SKILL_NAME


def backup_root_for_target(target: Path) -> Path:
    root = target.parent.parent / BACKUP_DIRECTORY_NAME / SKILL_NAME
    if _same_path(root, target) or _same_path(root.parent, target.parent):
        raise RuntimeError(f"Could not choose a backup directory outside: {target.parent}")
    try:
        root.relative_to(target.parent)
    except ValueError:
        return root
    raise RuntimeError(f"Backup directory must be outside the Skill scan root: {root}")


def _unique_backup_path(root: Path, label: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    safe_label = "".join(
        character if character.isalnum() or character in {"-", "."} else "-"
        for character in label
    ).strip("-.")
    return root / f"{safe_label or SKILL_NAME}-{timestamp}-{uuid4().hex[:8]}"


def _move_to_backup(path: Path, backup_root: Path, label: str) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    destination = _unique_backup_path(backup_root, label)
    path.replace(destination)
    return destination


def migrate_legacy_sibling_backups(target: Path) -> list[Path]:
    """Move old discoverable ``experience-loop.backup-*`` folders out of Skills."""

    backup_root = backup_root_for_target(target)
    migrated: list[Path] = []
    for candidate in sorted(target.parent.glob(f"{target.name}.backup-*")):
        if _is_reparse_point(candidate):
            raise RuntimeError(
                "Refusing unsafe legacy backup symlink/junction in Skill scan root: "
                f"{candidate}"
            )
        marker_claims_skill = read_marker(candidate) is not None
        if not marker_claims_skill and not is_discoverable_experience_loop(candidate):
            continue
        migrated.append(
            _move_to_backup(candidate, backup_root, f"legacy-{candidate.name}")
        )
    return migrated


def discoverable_siblings(target: Path, include_target: bool = True) -> list[Path]:
    discovered: list[Path] = []
    if not target.parent.is_dir():
        return discovered
    for candidate in target.parent.iterdir():
        if not include_target and _same_path(candidate, target):
            continue
        if _is_reparse_point(candidate):
            continue
        if is_discoverable_experience_loop(candidate):
            discovered.append(candidate)
    return discovered


def ensure_no_other_discoverable_install(target: Path) -> None:
    others = discoverable_siblings(target, include_target=False)
    if others:
        rendered = ", ".join(str(path) for path in others)
        raise RuntimeError(
            "Another discoverable experience-loop Skill remains in the scan root: "
            f"{rendered}. Move it outside the Skills directory before continuing."
        )


def copy_runtime(source: Path, staging: Path) -> None:
    for name in RUNTIME_ENTRIES:
        item = source / name
        if not item.exists():
            continue
        destination = staging / name
        if item.is_dir():
            shutil.copytree(
                item,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
            )
        else:
            shutil.copy2(item, destination)

    marker = {
        "skill": SKILL_NAME,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "installer_version": 2,
    }
    (staging / MARKER_NAME).write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _quoted_command(parts: list[Union[Path, str]]) -> str:
    return " ".join(f'"{str(part)}"' for part in parts)


def lifecycle_commands(
    source: Path, target: Path, backup: Optional[Path]
) -> dict[str, Optional[str]]:
    python = Path(sys.executable).resolve()
    # These paths exist when commands are rendered, so expand Windows 8.3 aliases.
    source = source.resolve()
    target = target.resolve()
    if backup is not None:
        backup = backup.resolve()
    commands: dict[str, Optional[str]] = {
        "status": _quoted_command(
            [python, target / "scripts" / "experience_loop.py", "status"]
        ),
        "uninstall": _quoted_command(
            [
                python,
                target / "scripts" / "uninstall.py",
                "--target",
                target,
                "--yes",
            ]
        ),
        "upgrade_from_current_checkout": _quoted_command(
            [python, source / "scripts" / "install.py", "--target", target]
        ),
        "rollback": None,
    }
    if backup is not None:
        commands["rollback"] = _quoted_command(
            [python, backup / "scripts" / "install.py", "--target", target]
        )
    return commands


def install(source: Path, target: Path, force: bool) -> dict[str, object]:
    source = source.resolve()
    target = validate_target_path(target)
    if _same_path(source, target):
        if not is_managed_install(target):
            raise RuntimeError(
                "The active Skill directory is incomplete or is missing a valid install marker."
            )
        return {
            "status": "already-active",
            "target": str(target),
            "backup": None,
            "migrated_legacy_backups": [],
            "commands": lifecycle_commands(source, target, None),
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not (
        is_managed_install(target) or is_legacy_install(target)
    ) and not force:
        raise RuntimeError(
            f"Target already exists and is not a recognized {SKILL_NAME} install: {target}. "
            "Re-run with --force only after reviewing that directory."
        )

    backup_root = backup_root_for_target(target)
    migrated = migrate_legacy_sibling_backups(target)
    ensure_no_other_discoverable_install(target)
    backup_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".install-", dir=str(backup_root)))
    backup: Optional[Path] = None
    activated = False
    try:
        copy_runtime(source, staging)
        validate_source(staging)
        if not is_managed_install(staging):
            raise RuntimeError("Staged Skill failed managed-install validation.")

        if target.exists():
            backup = _move_to_backup(target, backup_root, SKILL_NAME)
        staging.replace(target)
        activated = True
        discovered = discoverable_siblings(target)
        if len(discovered) != 1 or not _same_path(discovered[0], target):
            raise RuntimeError(
                "Installation did not leave exactly one discoverable Experience Loop Skill."
            )
    except Exception:
        if activated and target.exists() and is_managed_install(target):
            shutil.rmtree(target)
        if not target.exists() and backup is not None and backup.exists():
            backup.replace(target)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    return {
        "status": "installed",
        "target": str(target),
        "backup": str(backup) if backup else None,
        "migrated_legacy_backups": [str(path) for path in migrated],
        "commands": lifecycle_commands(source, target, backup),
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    args = parse_args()
    if sys.version_info < (3, 9):
        message = "Experience Loop requires Python 3.9 or newer."
        if args.json:
            print(json.dumps({"status": "error", "error": message}, ensure_ascii=False))
        else:
            print("安装失败 / Installation failed: " + message, file=sys.stderr)
        return 4
    source = repo_root()
    target = args.target
    try:
        validate_source(source)
        if args.dry_run:
            checked_target = validate_target_path(target)
            result: dict[str, object] = {
                "status": "dry-run",
                "source": str(source),
                "target": str(checked_target),
                "backup_root": str(backup_root_for_target(checked_target)),
            }
        else:
            result = install(source, target, args.force)
    except Exception as exc:  # User-facing CLI boundary.
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"安装失败 / Installation failed: {exc}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Experience Loop: {result['status']}")
        print(f"个人 Skill 目录 / User skill directory: {result['target']}")
        if result.get("backup"):
            print(f"上一版本备份 / Previous version backup: {result['backup']}")
        commands = result.get("commands")
        if isinstance(commands, dict):
            print("已安装命令 / Installed commands:")
            print(f"  status: {commands['status']}")
            print(f"  uninstall: {commands['uninstall']}")
            print(
                "  upgrade (keep or re-download this checkout): "
                f"{commands['upgrade_from_current_checkout']}"
            )
            if commands.get("rollback"):
                print(f"  rollback: {commands['rollback']}")
        print("下一步 / Next: restart Codex if needed, then run `$experience-loop setup`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
