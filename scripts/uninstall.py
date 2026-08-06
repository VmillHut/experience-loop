#!/usr/bin/env python3
"""Remove the installed Skill without deleting personal Experience Loop data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Optional

from install import (
    _move_to_backup,
    _same_path,
    backup_root_for_target,
    ensure_no_other_discoverable_install,
    managed_install_validation_error,
    migrate_legacy_sibling_backups,
    normalized_stored_host_contract,
    other_discoverable_installations,
    planned_legacy_sibling_backups,
    read_marker,
    restore_legacy_sibling_backups,
    validate_discovery_root,
    validate_target_path,
    validated_contract_text,
)


def default_target() -> Optional[Path]:
    installed_root = Path(__file__).resolve().parent.parent
    if managed_install_validation_error(installed_root) is None:
        return installed_root
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uninstall the Experience Loop Skill.")
    parser.add_argument(
        "--host",
        default=None,
        help=(
            "Informational host label. Normally recovered from the managed-install "
            "marker or supplied by the install receipt."
        ),
    )
    parser.add_argument("--target", type=Path, default=default_target())
    parser.add_argument("--discovery-root", action="append", type=Path, default=[])
    parser.add_argument("--affected-host", action="append", default=[])
    parser.add_argument("--yes", action="store_true", help="Confirm removal.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_uninstall_contract(
    target: Path,
    requested_host: Optional[str],
    requested_roots: list[Path],
    requested_affected: list[str],
) -> dict[str, object]:
    marker = read_marker(target)
    stored = marker.get("host_contract") if marker is not None else None
    installer_version = marker.get("installer_version") if marker is not None else None
    if isinstance(stored, dict):
        stored_contract = normalized_stored_host_contract(stored, target)
    elif isinstance(installer_version, int) and installer_version >= 4:
        raise RuntimeError("Stored dynamic host safety context is missing.")
    else:
        stored_contract = {
            "host": "current-agent",
            "discovery_roots": [str(validate_discovery_root(target.parent))],
            "affected_hosts": [],
        }
    legacy_host = marker.get("host_adapter") if marker is not None else None
    host = validated_contract_text(
        requested_host
        or (stored_contract.get("host") if isinstance(stored_contract.get("host"), str) else None)
        or (legacy_host if isinstance(legacy_host, str) else None),
        "--host",
        80,
        default="current-agent",
    )
    stored_roots = stored_contract.get("discovery_roots")
    raw_roots: list[Path] = (
        [Path(str(root)) for root in stored_roots]
        if isinstance(stored_roots, list)
        else []
    )
    raw_roots.extend(requested_roots)
    roots: list[Path] = [validate_discovery_root(target.parent)]
    for raw_root in raw_roots:
        root = validate_discovery_root(raw_root)
        if not any(_same_path(root, existing) for existing in roots):
            roots.append(root)
    affected_hosts: list[str] = []
    raw_affected = (
        stored_contract.get("affected_hosts")
        if isinstance(stored_contract.get("affected_hosts"), list)
        else []
    )
    raw_affected = list(raw_affected) + list(requested_affected)
    for raw_host in raw_affected:
        label = validated_contract_text(str(raw_host), "--affected-host", 80)
        if label and label not in affected_hosts:
            affected_hosts.append(label)
    if not affected_hosts and host:
        affected_hosts.append(host)
    return {
        "host": host,
        "discovery_roots": roots,
        "affected_hosts": affected_hosts,
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        if args.target is None:
            raise RuntimeError(
                "--target is required when uninstall.py is not running from an "
                "installed Experience Loop directory."
            )
        target = validate_target_path(args.target)
        validation_error = (
            managed_install_validation_error(target) if target.exists() else None
        )
        if validation_error is not None:
            host = validated_contract_text(
                args.host, "--host", 80, default="current-agent"
            )
            result = {
                "status": "refused",
                "host": host,
                "target": str(target),
                "error": (
                    "The directory is not a strongly validated Experience Loop install: "
                    + validation_error
                ),
            }
        else:
            contract = resolve_uninstall_contract(
                target, args.host, args.discovery_root, args.affected_host
            )
            host = str(contract["host"])
            discovery_roots = contract["discovery_roots"]
            legacy_candidates = planned_legacy_sibling_backups(target)
            conflicts = other_discoverable_installations(
                target, discovery_roots, legacy_candidates
            )
            if conflicts:
                rendered = ", ".join(str(path) for path in conflicts)
                raise RuntimeError(
                    "Another discoverable experience-loop Skill remains in a scan root "
                    f"declared by the installation AI: {rendered}. Move it outside that "
                    "host's Skill discovery roots before continuing."
                )
        if validation_error is None and not target.exists():
            if legacy_candidates and not args.yes:
                result = {
                    "status": "confirmation-required",
                    "host": host,
                    "target": str(target),
                    "hint": (
                        "The active target is absent, but discoverable legacy copies remain. "
                        "Re-run with --yes to migrate recognized legacy backups outside the "
                        "Skill scan root."
                    ),
                }
            else:
                migrated: list[tuple[Path, Path]] = []
                try:
                    if args.yes:
                        migrated = migrate_legacy_sibling_backups(target)
                    ensure_no_other_discoverable_install(target, discovery_roots)
                except Exception:
                    restore_legacy_sibling_backups(migrated)
                    raise
                result = {
                    "status": "not-installed",
                    "host": host,
                    "target": str(target),
                    "migrated_legacy_backups": [
                        str(destination) for _, destination in migrated
                    ],
                }
        elif validation_error is None:
            if not args.yes:
                result = {
                    "status": "confirmation-required",
                    "host": host,
                    "target": str(target),
                    "hint": (
                        "Re-run with --yes. Personal Experience Loop data is not removed."
                    ),
                }
            else:
                migrated: list[tuple[Path, Path]] = []
                quarantine: Optional[Path] = None
                backup_root = backup_root_for_target(target)
                backup_root.mkdir(parents=True, exist_ok=True)
                backup_root = backup_root_for_target(target)
                try:
                    migrated = migrate_legacy_sibling_backups(target)
                    ensure_no_other_discoverable_install(target, discovery_roots)
                    current_directory = Path.cwd().resolve()
                    if _is_within(current_directory, target.resolve()):
                        os.chdir(str(target.parent))
                    quarantine = _move_to_backup(
                        target, backup_root, "uninstall-pending"
                    )
                    ensure_no_other_discoverable_install(target, discovery_roots)
                    shutil.rmtree(quarantine)
                    quarantine = None
                except Exception as exc:
                    recovery_errors: list[str] = []
                    try:
                        if (
                            quarantine is not None
                            and quarantine.exists()
                            and not target.exists()
                        ):
                            quarantine.replace(target)
                    except Exception as recovery_exc:
                        recovery_errors.append(f"target restore failed: {recovery_exc}")
                    try:
                        restore_legacy_sibling_backups(migrated)
                    except Exception as recovery_exc:
                        recovery_errors.append(
                            f"legacy-backup restore failed: {recovery_exc}"
                        )
                    if recovery_errors:
                        raise RuntimeError(
                            f"Uninstall failed: {exc}. Recovery also failed: "
                            + "; ".join(recovery_errors)
                        ) from exc
                    raise
                configured_home = os.environ.get("EXPERIENCE_LOOP_HOME")
                data_location = (
                    str(Path(configured_home).expanduser().resolve())
                    if configured_home
                    else str((Path.home() / ".experience-loop").resolve())
                )
                result = {
                    "status": "uninstalled",
                    "host": host,
                    "target": str(target),
                    "backup_root": str(backup_root),
                    "migrated_legacy_backups": [
                        str(destination) for _, destination in migrated
                    ],
                    "personal_data_preserved": True,
                    "personal_data_location_hint": data_location,
                    "personal_data_location_basis": (
                        "EXPERIENCE_LOOP_HOME" if configured_home else "default-only"
                    ),
                    "personal_data_note": (
                        "The uninstaller did not inspect or delete personal data. An "
                        "explicit runtime --home may point elsewhere."
                    ),
                }
    except Exception as exc:  # User-facing destructive-operation boundary.
        rendered_target = (
            str(args.target.expanduser()) if args.target is not None else "<unspecified>"
        )
        result = {
            "status": "refused",
            "target": rendered_target,
            "error": str(exc),
        }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["status"])
        if result.get("hint"):
            print(result["hint"])
        if result.get("error"):
            print(result["error"], file=sys.stderr)
    return 0 if result["status"] in {"not-installed", "uninstalled"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
