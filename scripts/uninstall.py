#!/usr/bin/env python3
"""Remove the installed Skill without deleting personal Experience Loop data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from install import (
    SKILL_NAME,
    backup_root_for_target,
    discoverable_siblings,
    ensure_no_other_discoverable_install,
    managed_install_validation_error,
    migrate_legacy_sibling_backups,
    validate_target_path,
)


def default_target() -> Path:
    installed_root = Path(__file__).resolve().parent.parent
    if managed_install_validation_error(installed_root) is None:
        return installed_root
    return Path.home() / ".agents" / "skills" / SKILL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uninstall the Experience Loop Skill.")
    parser.add_argument("--target", type=Path, default=default_target())
    parser.add_argument("--yes", action="store_true", help="Confirm removal.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        target = validate_target_path(args.target)
        if not target.exists():
            discoverable = discoverable_siblings(target)
            if discoverable and not args.yes:
                result = {
                    "status": "confirmation-required",
                    "target": str(target),
                    "hint": (
                        "The active target is absent, but discoverable legacy copies remain. "
                        "Re-run with --yes to migrate recognized legacy backups outside the "
                        "Skill scan root."
                    ),
                }
            else:
                migrated = migrate_legacy_sibling_backups(target) if args.yes else []
                ensure_no_other_discoverable_install(target)
                result = {
                    "status": "not-installed",
                    "target": str(target),
                    "migrated_legacy_backups": [str(path) for path in migrated],
                }
        else:
            validation_error = managed_install_validation_error(target)
            if validation_error is not None:
                result = {
                    "status": "refused",
                    "target": str(target),
                    "error": (
                        "The directory is not a strongly validated Experience Loop install: "
                        + validation_error
                    ),
                }
            elif not args.yes:
                result = {
                    "status": "confirmation-required",
                    "target": str(target),
                    "hint": (
                        "Re-run with --yes. Personal data under ~/.experience-loop is not "
                        "removed."
                    ),
                }
            else:
                migrated = migrate_legacy_sibling_backups(target)
                ensure_no_other_discoverable_install(target)
                current_directory = Path.cwd().resolve()
                if _is_within(current_directory, target.resolve()):
                    os.chdir(str(target.parent))
                shutil.rmtree(target)
                remaining = discoverable_siblings(target)
                if remaining:
                    rendered = ", ".join(str(path) for path in remaining)
                    raise RuntimeError(
                        "Uninstall left a discoverable Experience Loop Skill in the scan "
                        f"root: {rendered}"
                    )
                result = {
                    "status": "uninstalled",
                    "target": str(target),
                    "backup_root": str(backup_root_for_target(target)),
                    "migrated_legacy_backups": [str(path) for path in migrated],
                    "personal_data_preserved": str(Path.home() / ".experience-loop"),
                }
    except Exception as exc:  # User-facing destructive-operation boundary.
        result = {
            "status": "refused",
            "target": str(args.target.expanduser()),
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
