#!/usr/bin/env python3
"""Install Experience Loop into an Agent skill directory resolved at runtime.

The installer copies only runtime files. Personal data always lives outside the
skill directory and is therefore untouched by installs and upgrades. Dynamic host
metadata affects receipts and duplicate checks only; it cannot change Skill behavior.
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
CURRENT_RUNTIME_CONTRACT = 2
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
RUNTIME_CONTRACT_1_FILES = COMPATIBLE_INSTALL_FILES + (
    "references/onboarding.md",
)
CURRENT_SOURCE_REQUIRED_FILES = RUNTIME_CONTRACT_1_FILES + (
    "references/host-compatibility.md",
)
RUNTIME_CONTRACT_FILES = {
    1: RUNTIME_CONTRACT_1_FILES,
    CURRENT_RUNTIME_CONTRACT: CURRENT_SOURCE_REQUIRED_FILES,
}
BACKUP_DIRECTORY_NAME = "skill-backups"
HOST_SCOPES = ("user", "project", "custom")


def validated_contract_text(
    value: Optional[str], field: str, maximum: int, *, default: Optional[str] = None
) -> Optional[str]:
    if value is None:
        return default
    if not isinstance(value, str):
        raise RuntimeError(f"{field} must be text.")
    cleaned = value.strip()
    if not cleaned:
        return default
    if len(cleaned) > maximum:
        raise RuntimeError(f"{field} exceeds the {maximum}-character safety limit.")
    if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
        raise RuntimeError(f"{field} must be a single printable line.")
    return cleaned


def first_reparse_component(path: Path) -> Optional[Path]:
    normalized = normalized_target(path)
    current = Path(normalized.anchor)
    parts = normalized.parts[1:] if normalized.anchor else normalized.parts
    for part in parts:
        current = current / part
        if _is_reparse_point(current):
            return current
    return None


def validate_discovery_root(path: Path) -> Path:
    root = normalized_target(path)
    dangerous = (Path(root.anchor), normalized_target(Path.home()))
    if any(_same_path(root, candidate) for candidate in dangerous):
        raise RuntimeError(f"Refusing broad discovery root: {root}")
    reparse_component = first_reparse_component(root)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing discovery root with a symlink, junction, or reparse-point "
            f"component: {reparse_component}"
        )
    return root


def unique_discovery_roots(target: Path, supplied: list[Path]) -> list[Path]:
    roots = [validate_discovery_root(target.parent)]
    for candidate in supplied:
        root = validate_discovery_root(candidate)
        if not any(_same_path(root, existing) for existing in roots):
            roots.append(root)
    return roots


def build_host_contract(args: argparse.Namespace, target: Path) -> dict[str, object]:
    host = validated_contract_text(args.host, "--host", 80, default="current-agent")
    invocation = validated_contract_text(args.invocation, "--invocation", 160)
    reload_hint = validated_contract_text(args.reload_hint, "--reload-hint", 500)
    evidence = validated_contract_text(args.host_evidence, "--host-evidence", 500)
    affected_hosts: list[str] = []
    for raw_host in args.affected_host or []:
        label = validated_contract_text(raw_host, "--affected-host", 80)
        if label and label not in affected_hosts:
            affected_hosts.append(label)
    if not affected_hosts and host:
        affected_hosts.append(host)
    roots = unique_discovery_roots(target, args.discovery_root or [])
    return {
        "host": host,
        "scope": args.scope or "custom",
        "target": str(target),
        "invocation": invocation,
        "reload_hint": reload_hint,
        "host_evidence": evidence,
        "discovery_roots": [str(root) for root in roots],
        "affected_hosts": affected_hosts,
    }


def host_receipt(contract: dict[str, object]) -> dict[str, object]:
    reload_hint = contract.get("reload_hint")
    return {
        **contract,
        "host_contract_status": (
            "resolved-by-installing-agent"
            if contract.get("host_evidence")
            else "missing-host-evidence"
        ),
        "support_level": "dynamic-host-contract-requires-session-validation",
        "reload_hint": reload_hint
        or "Resolve and use the current host's documented reload procedure.",
        "host_verification_hint": (
            "Use the current host's independently verified discovery mechanism and "
            "prove that it loads this exact installed SKILL.md. Invocation metadata "
            "is reported separately and is never executed by the installer."
        ),
        "discovery_status": "requires-host-session-validation",
        "discovery_roots_coverage": "asserted-by-installing-agent",
        "discovery_roots_note": (
            "Duplicate protection covers only the discovery roots declared by the "
            "installation AI in this receipt."
        ),
        "global_router": "not-authorized-by-installation",
        "core_behavior_contract": "unchanged-across-hosts",
        "capabilities": {
            "guidance": "installed-core",
            "profile": "requires-runtime-validation",
            "ledger": "requires-runtime-validation",
            "knowledge_lens": "requires-runtime-validation",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install Experience Loop using host facts resolved by the calling AI; "
            "the Skill behavior and runtime remain identical across hosts."
        )
    )
    parser.add_argument(
        "--host",
        default=None,
        help=(
            "Informational current-host label resolved by the installation AI. "
            "It does not select a hard-coded adapter."
        ),
    )
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help="Current host Skill directory resolved and verified by the installation AI.",
    )
    parser.add_argument("--scope", choices=HOST_SCOPES, default=None)
    parser.add_argument(
        "--invocation",
        help="Current host invocation syntax or interaction, for the handoff receipt.",
    )
    parser.add_argument(
        "--reload-hint",
        help="Current host reload instruction, recorded as text and never executed.",
    )
    parser.add_argument(
        "--host-evidence",
        help="Short evidence explaining how the AI resolved the current host contract.",
    )
    parser.add_argument(
        "--discovery-root",
        action="append",
        type=Path,
        default=[],
        help="Additional current-host Skill scan root to check for duplicate installs.",
    )
    parser.add_argument(
        "--affected-host",
        action="append",
        default=[],
        help="Host label that may discover this target; repeat for shared directories.",
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
        "Experience Loop 完整核心已安装，且应先由当前宿主确认发现。请检查是否"
        "已经初始化；若尚未初始化，读取 "
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
    )
    if any(_same_path(target, candidate) for candidate in dangerous):
        raise RuntimeError(f"Refusing dangerous installation target: {target}")
    if target.name.casefold() != SKILL_NAME.casefold():
        raise RuntimeError(
            f"Installation target must end with '{SKILL_NAME}': {target}"
        )
    home = normalized_target(Path.home())
    if (
        target.parent == target
        or target.parent.parent == target.parent
        or _same_path(target.parent.parent, anchor)
        or _same_path(target.parent, home)
    ):
        raise RuntimeError(f"Installation target is too close to a filesystem root: {target}")
    reparse_component = first_reparse_component(target)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing installation target with a symlink, junction, or reparse-point "
            f"component: {reparse_component}"
        )
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


def stored_host_contract_validation_error(value: object) -> Optional[str]:
    if not isinstance(value, dict):
        return "Dynamic host contract must be an object."
    try:
        roots = value.get("discovery_roots")
        if not isinstance(roots, list) or not roots:
            return "Dynamic host safety context has no discovery roots."
        if not all(isinstance(root, str) and root.strip() for root in roots):
            return "Dynamic host safety context has an invalid discovery root."
        for root in roots:
            validate_discovery_root(Path(root))
    except RuntimeError as exc:
        return str(exc)
    return None


def explicit_host_contract_arguments(args: argparse.Namespace) -> bool:
    return any(
        (
            args.host is not None,
            args.scope is not None,
            bool(args.invocation),
            bool(args.reload_hint),
            bool(args.host_evidence),
            bool(args.discovery_root),
            bool(args.affected_host),
        )
    )


def normalized_stored_host_contract(
    value: dict[str, object], target: Path
) -> dict[str, object]:
    error = stored_host_contract_validation_error(value)
    if error is not None:
        raise RuntimeError("Stored dynamic host contract is invalid: " + error)
    roots = unique_discovery_roots(
        target, [Path(str(root)) for root in value["discovery_roots"]]
    )
    def optional_text(field: str, maximum: int, default: Optional[str] = None) -> Optional[str]:
        try:
            return validated_contract_text(value.get(field), field, maximum, default=default)
        except RuntimeError:
            return default

    host = optional_text("host", 80, "current-agent") or "current-agent"
    scope = value.get("scope") if value.get("scope") in HOST_SCOPES else "custom"
    affected_hosts: list[str] = []
    raw_affected = value.get("affected_hosts")
    if isinstance(raw_affected, list):
        for raw_host in raw_affected:
            try:
                label = validated_contract_text(str(raw_host), "affected host", 80)
            except RuntimeError:
                continue
            if label and label not in affected_hosts:
                affected_hosts.append(label)
    if host not in affected_hosts:
        affected_hosts.append(host)
    return {
        "host": host,
        "scope": scope,
        "target": str(target),
        "invocation": optional_text("invocation", 160),
        "reload_hint": optional_text("reload_hint", 500),
        "host_evidence": optional_text("host_evidence", 500),
        "discovery_roots": [str(root) for root in roots],
        "affected_hosts": affected_hosts,
    }


def effective_host_contract(
    args: argparse.Namespace, target: Path
) -> dict[str, object]:
    if not target.is_dir() or managed_install_validation_error(target) is not None:
        return build_host_contract(args, target)
    marker = read_marker(target)
    stored = marker.get("host_contract") if marker is not None else None
    installer_version = marker.get("installer_version") if marker is not None else None
    if not isinstance(stored, dict):
        if isinstance(installer_version, int) and installer_version >= 4:
            raise RuntimeError("Stored dynamic host safety context is missing.")
        return build_host_contract(args, target)

    base = normalized_stored_host_contract(stored, target)
    if not explicit_host_contract_arguments(args):
        return base

    host = validated_contract_text(
        args.host if args.host is not None else str(base["host"]),
        "--host",
        80,
        default="current-agent",
    )
    scope = args.scope or str(base["scope"])
    invocation = (
        validated_contract_text(args.invocation, "--invocation", 160)
        if args.invocation is not None
        else base.get("invocation")
    )
    reload_hint = (
        validated_contract_text(args.reload_hint, "--reload-hint", 500)
        if args.reload_hint is not None
        else base.get("reload_hint")
    )
    evidence = (
        validated_contract_text(args.host_evidence, "--host-evidence", 500)
        if args.host_evidence is not None
        else base.get("host_evidence")
    )
    roots = unique_discovery_roots(
        target,
        [Path(str(root)) for root in base["discovery_roots"]]
        + list(args.discovery_root or []),
    )
    affected_hosts = list(base["affected_hosts"])
    for raw_host in args.affected_host or []:
        label = validated_contract_text(raw_host, "--affected-host", 80)
        if label and label not in affected_hosts:
            affected_hosts.append(label)
    if host and host not in affected_hosts:
        affected_hosts.append(host)
    return {
        "host": host,
        "scope": scope,
        "target": str(target),
        "invocation": invocation,
        "reload_hint": reload_hint,
        "host_evidence": evidence,
        "discovery_roots": [str(root) for root in roots],
        "affected_hosts": affected_hosts,
    }


def required_files_for_marker(
    marker: dict[str, Any],
) -> tuple[Optional[tuple[str, ...]], Optional[str]]:
    contract = marker.get("runtime_contract")
    if contract is None:
        return COMPATIBLE_INSTALL_FILES, None
    if not isinstance(contract, int):
        return None, f"Install marker runtime_contract must be an integer: {contract!r}."
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
        pass
    else:
        raise RuntimeError(f"Backup directory must be outside the Skill scan root: {root}")
    reparse_component = first_reparse_component(root)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing backup root with a symlink, junction, or reparse-point "
            f"component: {reparse_component}"
        )
    return root


def _unique_backup_path(root: Path, label: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    safe_label = "".join(
        character if character.isalnum() or character in {"-", "."} else "-"
        for character in label
    ).strip("-.")
    return root / f"{safe_label or SKILL_NAME}-{timestamp}-{uuid4().hex[:8]}"


def _move_to_backup(path: Path, backup_root: Path, label: str) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    reparse_component = first_reparse_component(backup_root)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing backup write through a symlink, junction, or reparse point: "
            f"{reparse_component}"
        )
    destination = _unique_backup_path(backup_root, label)
    path.replace(destination)
    return destination


def planned_legacy_sibling_backups(target: Path) -> list[Path]:
    """Return recognized legacy sibling backups after validating every candidate."""

    candidates: list[Path] = []
    if not target.parent.is_dir():
        return candidates
    for candidate in sorted(target.parent.glob(f"{target.name}.backup-*")):
        if _is_reparse_point(candidate):
            raise RuntimeError(
                "Refusing unsafe legacy backup symlink/junction in Skill scan root: "
                f"{candidate}"
            )
        marker_claims_skill = read_marker(candidate) is not None
        if not marker_claims_skill and not is_discoverable_experience_loop(candidate):
            continue
        candidates.append(candidate)
    return candidates


def restore_legacy_sibling_backups(migrations: list[tuple[Path, Path]]) -> None:
    for original, destination in reversed(migrations):
        if not destination.exists():
            continue
        if original.exists():
            raise RuntimeError(
                "Could not restore a migrated legacy backup because its original "
                f"path is occupied: {original}"
            )
        destination.replace(original)


def migrate_legacy_sibling_backups(target: Path) -> list[tuple[Path, Path]]:
    """Move legacy sibling backups transactionally outside the Skill scan root."""

    backup_root = backup_root_for_target(target)
    migrations: list[tuple[Path, Path]] = []
    try:
        for candidate in planned_legacy_sibling_backups(target):
            destination = _move_to_backup(
                candidate, backup_root, f"legacy-{candidate.name}"
            )
            migrations.append((candidate, destination))
    except Exception:
        restore_legacy_sibling_backups(migrations)
        raise
    return migrations


def discoverable_installations(
    target: Path, discovery_roots: Optional[list[Path]] = None
) -> list[Path]:
    discovered: list[Path] = []
    roots = discovery_roots or [normalized_target(target).parent]
    for root in roots:
        if not root.is_dir():
            continue
        for candidate in root.iterdir():
            if _is_reparse_point(candidate):
                if candidate.name.casefold().startswith(SKILL_NAME.casefold()):
                    raise RuntimeError(
                        "Refusing a possible duplicate Experience Loop Skill through "
                        "a symlink, junction, or reparse point in a declared discovery "
                        f"root: {candidate}"
                    )
                continue
            if is_discoverable_experience_loop(candidate) and not any(
                _same_path(candidate, existing) for existing in discovered
            ):
                discovered.append(candidate)
    return discovered


def other_discoverable_installations(
    target: Path,
    discovery_roots: Optional[list[Path]] = None,
    ignored: Optional[list[Path]] = None,
) -> list[Path]:
    ignored_paths = ignored or []
    return [
        path
        for path in discoverable_installations(target, discovery_roots)
        if not _same_path(path, normalized_target(target))
        and not any(_same_path(path, candidate) for candidate in ignored_paths)
    ]


def ensure_no_other_discoverable_install(
    target: Path,
    discovery_roots: Optional[list[Path]] = None,
    ignored: Optional[list[Path]] = None,
) -> None:
    others = other_discoverable_installations(target, discovery_roots, ignored)
    if others:
        rendered = ", ".join(str(path) for path in others)
        raise RuntimeError(
            "Another discoverable experience-loop Skill remains in a scan root "
            f"declared by the installation AI: {rendered}. Move it outside that "
            "host's Skill discovery roots before continuing."
        )


def install_plan(
    target: Path, force: bool, host_contract: dict[str, object]
) -> dict[str, object]:
    target = validate_target_path(target)
    backup_root = backup_root_for_target(target)
    discovery_roots = [Path(str(root)) for root in host_contract["discovery_roots"]]
    legacy_candidates = planned_legacy_sibling_backups(target)
    duplicates = other_discoverable_installations(
        target, discovery_roots, legacy_candidates
    )
    if not target.exists():
        existing_target_class = "absent"
    elif is_managed_install(target):
        existing_target_class = "managed"
    elif is_legacy_install(target):
        existing_target_class = "legacy"
    else:
        existing_target_class = "unrecognized"
    requires_force = existing_target_class == "unrecognized"
    blockers: list[str] = []
    if requires_force and not force:
        blockers.append(
            f"Target already exists and is not a recognized {SKILL_NAME} install: "
            f"{target}. Re-run with --force only after reviewing that directory."
        )
    if duplicates:
        rendered = ", ".join(str(path) for path in duplicates)
        blockers.append(
            "Another discoverable experience-loop Skill remains in a scan root "
            f"declared by the installation AI: {rendered}. Move it outside that "
            "host's Skill discovery roots before continuing."
        )
    return {
        "existing_target_class": existing_target_class,
        "requires_force": requires_force,
        "backup_root": str(backup_root),
        "will_backup_existing_target": target.exists(),
        "legacy_migrations": [str(path) for path in legacy_candidates],
        "duplicates": [str(path) for path in duplicates],
        "blockers": blockers,
    }


def copy_runtime(
    source: Path, staging: Path, host_contract: dict[str, object]
) -> None:
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
        "installer_version": 4,
        "runtime_contract": CURRENT_RUNTIME_CONTRACT,
        "host_contract": host_contract,
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


def installer_accepts_dynamic_host_contract(path: Path) -> bool:
    marker = read_marker(path)
    if marker is None:
        return False
    version = marker.get("installer_version")
    return isinstance(version, int) and version >= 4


def contract_install_argv(
    contract: dict[str, object], target: Path
) -> list[str]:
    arguments = [
        "--host",
        str(contract["host"]),
        "--scope",
        str(contract["scope"]),
        "--target",
        str(target),
    ]
    optional_fields = (
        ("invocation", "--invocation"),
        ("reload_hint", "--reload-hint"),
        ("host_evidence", "--host-evidence"),
    )
    for field, flag in optional_fields:
        value = contract.get(field)
        if isinstance(value, str) and value:
            arguments.extend([flag, value])
    for raw_root in contract.get("discovery_roots", []):
        root = Path(str(raw_root))
        if not _same_path(root, target.parent):
            arguments.extend(["--discovery-root", str(root)])
    for affected in contract.get("affected_hosts", []):
        arguments.extend(["--affected-host", str(affected)])
    return arguments


def contract_uninstall_argv(
    contract: dict[str, object], target: Path
) -> list[str]:
    arguments = ["--host", str(contract["host"]), "--target", str(target)]
    for raw_root in contract.get("discovery_roots", []):
        root = Path(str(raw_root))
        if not _same_path(root, target.parent):
            arguments.extend(["--discovery-root", str(root)])
    for affected in contract.get("affected_hosts", []):
        arguments.extend(["--affected-host", str(affected)])
    return arguments


def lifecycle_argv(
    source: Path,
    target: Path,
    backup: Optional[Path],
    host_contract: dict[str, object],
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
            *contract_uninstall_argv(host_contract, target),
            "--yes",
        ],
        "upgrade_from_current_checkout": (
            None
            if _same_path(source, target)
            else [
                python,
                str(source / "scripts" / "install.py"),
                *contract_install_argv(host_contract, target),
            ]
        ),
        "rollback": None,
    }
    if backup is not None and rollback_source_error(backup) is None:
        rollback_command = [
            python,
            str(backup / "scripts" / "install.py"),
        ]
        if installer_accepts_dynamic_host_contract(backup):
            rollback_command.extend(contract_install_argv(host_contract, target))
        else:
            rollback_command.extend(["--target", str(target), "--force"])
        commands["rollback"] = rollback_command
    return commands


def lifecycle_commands(
    source: Path,
    target: Path,
    backup: Optional[Path],
    host_contract: dict[str, object],
) -> dict[str, Optional[str]]:
    return {
        name: _quoted_command(parts) if parts is not None else None
        for name, parts in lifecycle_argv(
            source, target, backup, host_contract
        ).items()
    }


def install(
    source: Path,
    target: Path,
    force: bool,
    host_contract: dict[str, object],
) -> dict[str, object]:
    source = source.resolve()
    target = validate_target_path(target)
    if _same_path(source, target):
        if not is_managed_install(target):
            raise RuntimeError(
                "The active Skill directory is incomplete or is missing a valid install marker."
            )
    plan = install_plan(target, force, host_contract)
    blockers = plan["blockers"]
    if isinstance(blockers, list) and blockers:
        raise RuntimeError(" ".join(str(blocker) for blocker in blockers))
    if _same_path(source, target):
        return {
            "status": "already-active",
            "version": read_version(source),
            "source": str(source),
            "source_provenance": source_provenance(source),
            "target": str(target),
            "backup": None,
            "migrated_legacy_backups": [],
            **host_receipt(host_contract),
            "commands": lifecycle_commands(source, target, None, host_contract),
            "command_argv": lifecycle_argv(source, target, None, host_contract),
            "command_shell": "powershell" if os.name == "nt" else "posix",
            "runtime": str((target / "scripts" / "experience_loop.py").resolve()),
            "onboarding_reference": str(
                (target / "references" / "onboarding.md").resolve()
            ),
            "onboarding_prompt": onboarding_prompt(target),
            "onboarding_state": "check_runtime_before_onboarding",
            "rollback_available": False,
            "rollback_note": None,
            "filesystem_status": "managed-install-validated",
            "runtime_validation_status": "required-from-installed-copy",
        }

    discovery_roots = [Path(str(root)) for root in host_contract["discovery_roots"]]
    target.parent.mkdir(parents=True, exist_ok=True)
    backup_root = Path(str(plan["backup_root"]))
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_root = backup_root_for_target(target)
    staging = Path(tempfile.mkdtemp(prefix=".install-", dir=str(backup_root)))
    backup: Optional[Path] = None
    migrated: list[tuple[Path, Path]] = []
    activated = False
    try:
        copy_runtime(source, staging, host_contract)
        if not is_managed_install(staging):
            raise RuntimeError("Staged Skill failed managed-install validation.")

        refreshed_plan = install_plan(target, force, host_contract)
        refreshed_blockers = refreshed_plan["blockers"]
        if isinstance(refreshed_blockers, list) and refreshed_blockers:
            raise RuntimeError(" ".join(str(blocker) for blocker in refreshed_blockers))
        migrated = migrate_legacy_sibling_backups(target)
        ensure_no_other_discoverable_install(target, discovery_roots)
        if target.exists():
            backup = _move_to_backup(target, backup_root, SKILL_NAME)
        staging.replace(target)
        activated = True
        discovered = discoverable_installations(target, discovery_roots)
        if len(discovered) != 1 or not _same_path(discovered[0], target):
            raise RuntimeError(
                "Installation did not leave exactly one discoverable Experience Loop Skill."
            )
    except Exception as exc:
        recovery_errors: list[str] = []
        try:
            if activated and target.exists() and is_managed_install(target):
                shutil.rmtree(target)
            if not target.exists() and backup is not None and backup.exists():
                backup.replace(target)
        except Exception as recovery_exc:
            recovery_errors.append(f"target restore failed: {recovery_exc}")
        try:
            restore_legacy_sibling_backups(migrated)
        except Exception as recovery_exc:
            recovery_errors.append(f"legacy-backup restore failed: {recovery_exc}")
        if recovery_errors:
            raise RuntimeError(
                f"Installation failed: {exc}. Recovery also failed: "
                + "; ".join(recovery_errors)
            ) from exc
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
        "migrated_legacy_backups": [
            str(destination) for _, destination in migrated
        ],
        **host_receipt(host_contract),
        "commands": lifecycle_commands(source, target, backup, host_contract),
        "command_argv": lifecycle_argv(source, target, backup, host_contract),
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
        "filesystem_status": "managed-install-validated",
        "runtime_validation_status": "required-from-installed-copy",
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
    exit_code = 0
    try:
        validate_source(source)
        target = validate_target_path(args.target)
        host_contract = effective_host_contract(args, target)
        if args.dry_run:
            plan = install_plan(target, args.force, host_contract)
            blocked = bool(plan["blockers"])
            result: dict[str, object] = {
                "status": "blocked" if blocked else "dry-run",
                "version": read_version(source),
                "source": str(source),
                "source_provenance": source_provenance(source),
                "target": str(target),
                "backup_root": str(plan["backup_root"]),
                "install_plan": plan,
                **host_receipt(host_contract),
                "filesystem_status": "preview-only",
                "runtime_validation_status": "not-run-during-dry-run",
            }
            if blocked:
                exit_code = 4
        else:
            result = install(source, target, args.force, host_contract)
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
        print(f"Agent host / 宿主: {result['host']}")
        print(f"Skill 目标目录 / Skill target directory: {result['target']}")
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
        if result["status"] == "blocked":
            print("预演被阻止 / Preview blocked:")
            for blocker in result["install_plan"]["blockers"]:
                print(f"  - {blocker}")
        elif result["status"] == "dry-run":
            print(
                "下一步 / Next: review the target above, then run the installer "
                "again without --dry-run."
            )
        else:
            print(f"宿主发现 / Host discovery: {result['discovery_status']}")
            print(f"验证提示 / Verify: {result['host_verification_hint']}")
            print(f"重载提示 / Reload: {result['reload_hint']}")
            print("下一步 / Next: after host discovery is verified, send:")
            print(f"  {result['onboarding_prompt']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
