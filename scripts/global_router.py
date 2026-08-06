#!/usr/bin/env python3
"""Preview or manage the optional user-level AGENTS.md router.

The router is intentionally tiny. Experience Loop remains usable through
explicit invocation and skill discovery without this file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import tempfile


START = "<!-- experience-loop:router:start -->"
END = "<!-- experience-loop:router:end -->"
ROUTER = f"""{START}
For substantive software-development work, apply `$experience-loop` when a
reusable human judgment may justify the interaction cost. Resolve an explicitly
saved mode; otherwise implicit use starts in `auto` and chooses silence,
embedded guidance, one checkpoint, or at most two short checkpoints from
consequence, uncertainty, transfer value, user profile, time pressure, and
interaction cost. Do not invoke it for mechanical or simple factual work, an
explicit "delivery only" request, or `off`. During urgent recovery, use the
normal delivery fast path without learning interruptions. Never infer `focus`
or `deep` from complexity. One learning seam must not narrow engineering or
verification coverage.
{END}
"""


def default_agents_file() -> Path:
    configured_home = os.environ.get("CODEX_HOME")
    codex_home = (
        Path(configured_home).expanduser()
        if configured_home
        else Path.home() / ".codex"
    )
    override = codex_home / "AGENTS.override.md"
    return override if override.exists() else codex_home / "AGENTS.md"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def replace_block(current: str, replacement: str) -> str:
    start = current.find(START)
    end = current.find(END)
    if start == -1 and end == -1:
        prefix = current.rstrip()
        return ((prefix + "\n\n") if prefix else "") + replacement.rstrip() + "\n"
    if start == -1 or end == -1 or end < start:
        raise RuntimeError("Existing Experience Loop router markers are malformed.")
    end += len(END)
    before = current[:start].rstrip()
    after = current[end:].lstrip("\r\n")
    pieces = [part for part in (before, replacement.rstrip(), after.rstrip()) if part]
    return "\n\n".join(pieces) + ("\n" if pieces else "")


def remove_block(current: str) -> tuple[str, bool]:
    if START not in current and END not in current:
        return current, False
    return replace_block(current, ""), True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage the optional Experience Loop global AGENTS.md router."
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--remove", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm a write operation.")
    parser.add_argument("--path", type=Path, default=default_agents_file())
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.path.expanduser().resolve()
    current = path.read_text(encoding="utf-8") if path.exists() else ""

    if not args.apply and not args.remove:
        result = {
            "status": "preview",
            "path": str(path),
            "already_present": START in current and END in current,
            "router": ROUTER,
        }
        code = 0
    elif not args.yes:
        result = {
            "status": "confirmation-required",
            "path": str(path),
            "hint": "Review the preview, then re-run with --apply --yes or --remove --yes.",
        }
        code = 3
    elif args.apply:
        atomic_write(path, replace_block(current, ROUTER))
        result = {"status": "applied", "path": str(path)}
        code = 0
    else:
        updated, changed = remove_block(current)
        if changed:
            atomic_write(path, updated)
        result = {
            "status": "removed" if changed else "not-present",
            "path": str(path),
        }
        code = 0

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["status"] == "preview":
        print(f"Optional global router target: {path}\n")
        print(ROUTER)
        print("No file was changed. Apply only after the user explicitly agrees.")
    else:
        print(result["status"])
        if result.get("hint"):
            print(result["hint"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
