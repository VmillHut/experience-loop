#!/usr/bin/env python3
"""Prepare an isolated copy of the blind-evaluation fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination directory; defaults to a new system temporary directory.",
    )
    args = parser.parse_args()

    output = (
        args.output.expanduser().resolve()
        if args.output
        else Path(tempfile.mkdtemp(prefix="experience-loop-blind-trial-"))
    )
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Output directory must be empty: {0}".format(output))
    output.mkdir(parents=True, exist_ok=True)
    project = output / "project"
    knowledge = output / "knowledge"
    home = output / "home"
    shutil.copytree(ROOT / "fixtures" / "sample_project", project)
    shutil.copytree(ROOT / "fixtures" / "knowledge", knowledge)
    home.mkdir()
    (project / ".env").write_text(
        "SAMPLE_TOKEN=blind-evaluation-do-not-read\n", encoding="utf-8"
    )
    result = {
        "root": str(output),
        "project": str(project),
        "knowledge": str(knowledge),
        "experience_loop_home": str(home),
        "cleanup": "Delete the root directory after the evaluation.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
