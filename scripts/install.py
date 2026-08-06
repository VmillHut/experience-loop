#!/usr/bin/env python3
"""Install Experience Loop into the current user's Codex skill directory.

The installer copies only runtime files. Personal data always lives outside the
skill directory and is therefore untouched by installs and upgrades.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Optional
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
CURRENT_RUNTIME_CONTRACT = 1
COMPATIBLE_INSTALL_FILES = (
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "assets/icon-large.svg",
    "assets/icon-small.svg",
    "references/capability-compass.md",
    "references/experience-model.md",
    "references/knowledge-lens.md",
    "references/safety-and-privacy.md",
    "references/setup-and-profiles.md",
    "references/workflow.md",
    "scripts/experience_loop.py",
    "scripts/experience_loop_lib/__init__.py",
    "scripts/experience_loop_lib/archive.py",
    "scripts/experience_loop_lib/cli.py",
    "scripts/experience_loop_lib/common.py",
    "scripts/experience_loop_lib/extractors.py",
    "scripts/experience_loop_lib/knowledge.py",
    "scripts/experience_loop_lib/ledger.py",
    "scripts/experience_loop_lib/path_policy.py",
    "scripts/experience_loop_lib/profile.py",
    "scripts/experience_loop_lib/project.py",
    "scripts/experience_loop_lib/storage.py",
    "scripts/install.py",
    "scripts/uninstall.py",
    "vendor/manifest.json",
)
CURRENT_SOURCE_REQUIRED_FILES = COMPATIBLE_INSTALL_FILES + (
    "references/onboarding.md",
)
RUNTIME_CONTRACT_FILES = {
    CURRENT_RUNTIME_CONTRACT: CURRENT_SOURCE_REQUIRED_FILES,
}
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


def read_version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def onboarding_prompt(target: Path) -> str:
    reference = (target / "references" / "onboarding.md").resolve()
    return (
        "$experience-loop 已安装。请先检查是否已经初始化；若尚未初始化，读取 "
        f'"{reference}" 并开始对话式初始化。所有画像问题都可跳过，最后询问我'
        "是否需要约 2 分钟的使用教学；若已经初始化，请保留现有画像且不要重复"
        "新手教学，除非我明确要求。"
    )


def source_provenance(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(root.resolve()),
        "repository": None,
        "commit": None,
        "dirty": None,
        "git_note": None,
    }
    try:
        top_level = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        result["git_note"] = f"Git metadata unavailable: {exc}"
        return result
    if top_level.returncode != 0 or not top_level.stdout.strip():
        result["git_note"] = (
            top_level.stderr.strip() or "Source is not a standalone Git checkout"
        )
        return result
    discovered_root = Path(top_level.stdout.strip()).resolve()
    if not _same_path(discovered_root, root.resolve()):
        result["git_note"] = (
            f"Source is inside a different Git worktree: {discovered_root}"
        )
        return result

    commands = {
        "repository": [
            "git",
            "-C",
            str(root),
            "config",
            "--get",
            "remote.origin.url",
        ],
        "commit": ["git", "-C", str(root), "rev-parse", "HEAD"],
    }
    failures = []
    for field, command in commands.items():
        try:
            completed = subprocess.run(
                command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            failures.append(f"{field}: {exc}")
            continue
        if completed.returncode == 0 and completed.stdout.strip():
            result[field] = completed.stdout.strip()
        else:
            detail = completed.stderr.strip() or "Git metadata unavailable"
            failures.append(f"{field}: {detail}")
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        failures.append(f"dirty: {exc}")
    else:
        if completed.returncode == 0:
            result["dirty"] = bool(completed.stdout.strip())
        else:
            detail = completed.stderr.strip() or "Git worktree status unavailable"
            failures.append(f"dirty: {detail}")
    if failures:
        result["git_note"] = "; ".join(failures)
    return result


def validate_source(root: Path) -> None:
    problems = [
        problem
        for relative in CURRENT_SOURCE_REQUIRED_FILES
        if (problem := required_file_validation_error(root, relative)) is not None
    ]
    if problems:
        raise RuntimeError("Skill source is incomplete or unsafe: " + "; ".join(problems))
    if read_skill_name(root) != SKILL_NAME:
        raise RuntimeError(f"Skill source does not declare name: {SKILL_NAME}")
    vendor_error = vendor_bundle_validation_error(root)
    if vendor_error is not None:
        raise RuntimeError(vendor_error)


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


def required_file_validation_error(root: Path, relative: str) -> Optional[str]:
    """Reject missing files and reparse points in every path component."""

    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return f"Unsafe required path: {relative}"
    current = root
    for part in relative_path.parts:
        current = current / part
        if _is_reparse_point(current):
            return f"Required path contains a symlink, junction, or reparse point: {relative}"
    if not current.is_file():
        return f"Required file is missing: {relative}"
    return None


def vendor_bundle_validation_error(root: Path) -> Optional[str]:
    """Statically validate bundled wheels and licenses without importing backup code."""

    manifest_problem = required_file_validation_error(root, "vendor/manifest.json")
    if manifest_problem is not None:
        return manifest_problem
    manifest_path = root / "vendor" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"vendor/manifest.json is invalid: {exc}"
    packages = manifest.get("packages") if isinstance(manifest, dict) else None
    if not isinstance(packages, list):
        return "vendor/manifest.json packages must be a list."
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            return f"Vendor package entry {index} is not an object."
        relative_file = package.get("file")
        relative_license = package.get("license_file")
        expected_hash = package.get("sha256")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (relative_file, relative_license, expected_hash)
        ):
            return f"Vendor package entry {index} has incomplete file metadata."
        wheel_manifest_path = PurePosixPath(relative_file)
        license_manifest_path = PurePosixPath(relative_license)
        if (
            wheel_manifest_path.is_absolute()
            or ".." in wheel_manifest_path.parts
            or not wheel_manifest_path.parts
            or wheel_manifest_path.parts[0] != "wheels"
            or wheel_manifest_path.suffix.lower() != ".whl"
        ):
            return f"Vendored artifact path is unsafe: {relative_file}"
        if (
            license_manifest_path.is_absolute()
            or len(license_manifest_path.parts) < 3
            or license_manifest_path.parts[:2] != ("..", "licenses")
            or ".." in license_manifest_path.parts[2:]
        ):
            return f"Vendor license path is unsafe: {relative_license}"
        wheel_relative = Path("vendor", *wheel_manifest_path.parts)
        license_relative = Path("licenses", *license_manifest_path.parts[2:])
        for relative in (wheel_relative, license_relative):
            problem = required_file_validation_error(root, str(relative))
            if problem is not None:
                return problem
        wheel = root / wheel_relative
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if digest != expected_hash.lower():
            return f"Bundled wheel hash mismatch: {relative_file}"
    return None


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


def required_files_for_marker(
    marker: dict[str, Any],
) -> tuple[Optional[tuple[str, ...]], Optional[str]]:
    contract = marker.get("runtime_contract")
    if contract is None:
        return COMPATIBLE_INSTALL_FILES, None
    files = RUNTIME_CONTRACT_FILES.get(contract)
    if files is None:
        return None, f"Unsupported runtime contract in install marker: {contract!r}."
    return files, None


def has_required_runtime(path: Path) -> bool:
    for relative in COMPATIBLE_INSTALL_FILES:
        if required_file_validation_error(path, relative) is not None:
            return False
    return (
        read_skill_name(path) == SKILL_NAME
        and vendor_bundle_validation_error(path) is None
    )


def managed_install_validation_error(path: Path) -> Optional[str]:
    if not path.is_dir():
        return "The target is not a directory."
    if _is_reparse_point(path):
        return "The target is a symlink, junction, or reparse point."
    marker = read_marker(path)
    if marker is None:
        return (
            f"{MARKER_NAME} is missing, invalid JSON, or does not declare "
            f"skill == {SKILL_NAME}."
        )
    required_files, contract_error = required_files_for_marker(marker)
    if contract_error is not None or required_files is None:
        return contract_error
    if read_skill_name(path) != SKILL_NAME:
        return f"SKILL.md does not declare name: {SKILL_NAME}."
    problems = [
        problem
        for relative in required_files
        if (problem := required_file_validation_error(path, relative)) is not None
    ]
    if problems:
        return "Required installed files are missing or unsafe: " + "; ".join(problems)
    vendor_error = vendor_bundle_validation_error(path)
    if vendor_error is not None:
        return vendor_error
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
        "runtime_contract": CURRENT_RUNTIME_CONTRACT,
    }
    (staging / MARKER_NAME).write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _quoted_command(parts: list[str]) -> str:
    if os.name == "nt":
        quoted = ["'" + part.replace("'", "''") + "'" for part in parts]
        return "& " + " ".join(quoted)
    return shlex.join(parts)


def rollback_source_error(backup: Optional[Path]) -> Optional[str]:
    if backup is None:
        return None
    if (backup / MARKER_NAME).exists():
        return managed_install_validation_error(backup)
    if not is_legacy_install(backup):
        return (
            "The backup is not a recognized managed or legacy Experience Loop "
            "install with a complete installer."
        )
    return None


def rollback_note(backup: Optional[Path]) -> Optional[str]:
    error = rollback_source_error(backup)
    if error is None:
        return None
    return (
        f"Backup was preserved at {backup}, but no executable rollback command was "
        f"issued because the backup is not a self-contained install source: {error}"
    )


def lifecycle_argv(
    source: Path, target: Path, backup: Optional[Path]
) -> dict[str, Optional[list[str]]]:
    python = str(Path(sys.executable).resolve())
    source = source.resolve()
    target = target.resolve()
    if backup is not None:
        backup = backup.resolve()
    commands: dict[str, Optional[list[str]]] = {
        "version": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--version",
        ],
        "mode": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "mode",
        ],
        "status": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "status",
        ],
        "setup": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "setup",
        ],
        "doctor": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "doctor",
        ],
        "uninstall": [
            python,
            str(target / "scripts" / "uninstall.py"),
            "--target",
            str(target),
            "--yes",
        ],
        "upgrade_from_current_checkout": (
            None
            if _same_path(source, target)
            else [
                python,
                str(source / "scripts" / "install.py"),
                "--target",
                str(target),
            ]
        ),
        "rollback": None,
    }
    if backup is not None and rollback_source_error(backup) is None:
        commands["rollback"] = [
            python,
            str(backup / "scripts" / "install.py"),
            "--target",
            str(target),
        ]
    return commands


def lifecycle_commands(
    source: Path, target: Path, backup: Optional[Path]
) -> dict[str, Optional[str]]:
    return {
        name: _quoted_command(parts) if parts is not None else None
        for name, parts in lifecycle_argv(source, target, backup).items()
    }


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
            "version": read_version(source),
            "source": str(source),
            "source_provenance": source_provenance(source),
            "target": str(target),
            "backup": None,
            "migrated_legacy_backups": [],
            "commands": lifecycle_commands(source, target, None),
            "command_argv": lifecycle_argv(source, target, None),
            "command_shell": "powershell" if os.name == "nt" else "posix",
            "runtime": str((target / "scripts" / "experience_loop.py").resolve()),
            "onboarding_reference": str(
                (target / "references" / "onboarding.md").resolve()
            ),
            "onboarding_prompt": onboarding_prompt(target),
            "onboarding_state": "check_runtime_before_onboarding",
            "rollback_available": False,
            "rollback_note": None,
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
        "version": read_version(source),
        "source": str(source),
        "source_provenance": source_provenance(source),
        "target": str(target),
        "backup": str(backup) if backup else None,
        "migrated_legacy_backups": [str(path) for path in migrated],
        "commands": lifecycle_commands(source, target, backup),
        "command_argv": lifecycle_argv(source, target, backup),
        "command_shell": "powershell" if os.name == "nt" else "posix",
        "runtime": str((target / "scripts" / "experience_loop.py").resolve()),
        "onboarding_reference": str(
            (target / "references" / "onboarding.md").resolve()
        ),
        "onboarding_prompt": onboarding_prompt(target),
        "onboarding_state": "check_runtime_before_onboarding",
        "rollback_available": rollback_source_error(backup) is None
        and backup is not None,
        "rollback_note": rollback_note(backup),
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
                "version": read_version(source),
                "source": str(source),
                "source_provenance": source_provenance(source),
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
            print(f"  version: {commands['version']}")
            print(f"  mode: {commands['mode']}")
            print(f"  status: {commands['status']}")
            print(f"  setup: {commands['setup']}")
            print(f"  doctor: {commands['doctor']}")
            print(f"  uninstall: {commands['uninstall']}")
            if commands.get("upgrade_from_current_checkout"):
                print(
                    "  upgrade (this checkout must still exist; otherwise re-download it): "
                    f"{commands['upgrade_from_current_checkout']}"
                )
            else:
                print("  upgrade: re-download the repository and run its installer")
            if commands.get("rollback"):
                print(f"  rollback: {commands['rollback']}")
            elif result.get("rollback_note"):
                print(f"  rollback unavailable: {result['rollback_note']}")
        if result["status"] == "dry-run":
            print(
                "下一步 / Next: review the target above, then run the installer "
                "again without --dry-run."
            )
        else:
            print("下一步 / Next: restart Codex or open a new session if needed, then say:")
            print(f"  {result['onboarding_prompt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
