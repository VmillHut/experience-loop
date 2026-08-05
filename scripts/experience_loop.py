#!/usr/bin/env python3
"""Portable entry point for Experience Loop."""

from __future__ import annotations

import sys
from pathlib import Path


for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from experience_loop_lib.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
