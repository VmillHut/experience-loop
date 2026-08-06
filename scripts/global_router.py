#!/usr/bin/env python3
"""Preview or manage an optional host instruction-file router.

The router is intentionally tiny. Experience Loop remains usable through
explicit invocation and skill discovery without this file. The installation AI
must resolve and verify the current host's instruction file before passing --path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import os
import tempfile


START = "<!-- experience-loop:router:start -->"
END = "<!-- experience-loop:router:end -->"
ROUTER_BODY = """For substantive software-development work, apply the locally
installed `experience-loop` Skill when a
reusable human judgment may justify the interaction cost. Resolve an explicitly
saved mode; otherwise implicit use starts in `auto` and intelligently chooses
silence, embedded guidance, an optional checkpoint, a required judgment
checkpoint, or a short guided practice loop from consequence, uncertainty,
transfer value, user profile, time pressure, and interaction cost. A required
checkpoint may briefly wait only when participation is valuable and safe; honor
"skip", "just do it", urgent recovery, explicit "delivery only", and `off`
immediately. Never infer a standing `focus` or `deep` contract from complexity.
One learning seam must not narrow engineering or verification coverage.
"""


def router_text() -> str:
    return f"{START}\n{ROUTER_BODY.rstrip()}\n{END}\n"


def content_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_markers(current: str) -> None:
    start_count = current.count(START)
    end_count = current.count(END)
    if start_count > 1 or end_count > 1:
        raise RuntimeError("Multiple Experience Loop router blocks were found.")
    if start_count != end_count:
        raise RuntimeError("Existing Experience Loop router markers are malformed.")
    if start_count == 1 and current.find(END) < current.find(START):
        raise RuntimeError("Existing Experience Loop router markers are malformed.")


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
        description=(
            "Manage an optional Experience Loop block in a host instruction file "
            "whose current path was verified by the calling AI."
        )
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--remove", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm a write operation.")
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Current host instruction file resolved and verified by the calling AI.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown",),
        required=True,
        help="Verified instruction-file format. Only Markdown is supported.",
    )
    parser.add_argument("--host", default="current-agent")
    parser.add_argument(
        "--expected-sha256",
        help="Exact current-file hash returned by preview; required for writes.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.path.expanduser().resolve()
    try:
        current_bytes = path.read_bytes() if path.exists() else b""
        current = current_bytes.decode("utf-8")
        current_hash = content_sha256(current_bytes)
        router = router_text()
        validate_markers(current)

        if not args.apply and not args.remove:
            result = {
                "status": "preview",
                "host": args.host,
                "format": args.format,
                "path": str(path),
                "current_sha256": current_hash,
                "already_present": START in current and END in current,
                "router": router,
            }
            code = 0
        elif not args.yes or not args.expected_sha256:
            result = {
                "status": "confirmation-required",
                "path": str(path),
                "current_sha256": current_hash,
                "hint": (
                    "Review the preview, then re-run with --yes and its exact "
                    "--expected-sha256 value."
                ),
            }
            code = 3
        elif args.expected_sha256.casefold() != current_hash:
            result = {
                "status": "stale-preview",
                "path": str(path),
                "expected_sha256": args.expected_sha256,
                "current_sha256": current_hash,
                "error": "The instruction file changed after preview; preview it again.",
            }
            code = 4
        elif args.apply:
            updated = replace_block(current, router)
            atomic_write(path, updated)
            result = {
                "status": "applied",
                "path": str(path),
                "sha256": content_sha256(updated.encode("utf-8")),
            }
            code = 0
        else:
            updated, changed = remove_block(current)
            if changed:
                atomic_write(path, updated)
            result = {
                "status": "removed" if changed else "not-present",
                "path": str(path),
                "sha256": content_sha256(updated.encode("utf-8")),
            }
            code = 0
    except Exception as exc:
        result = {"status": "refused", "path": str(path), "error": str(exc)}
        code = 4

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["status"] == "preview":
        print(f"Optional instruction router target: {path}\n")
        print(router)
        print("No file was changed. Apply only after the user explicitly agrees.")
    else:
        print(result["status"])
        if result.get("hint"):
            print(result["hint"])
        if result.get("error"):
            print(result["error"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
