from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def run_router(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "scripts" / "global_router.py"),
            "--path",
            str(path),
            "--json",
            *args,
        ],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


class GlobalRouterTests(unittest.TestCase):
    def test_default_path_honors_codex_home_and_existing_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-router-home-") as raw:
            codex_home = Path(raw) / "custom-codex"
            codex_home.mkdir(parents=True)
            override = codex_home / "AGENTS.override.md"
            override.write_text("# Override\n", encoding="utf-8")
            environment = os.environ.copy()
            environment["CODEX_HOME"] = str(codex_home)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts" / "global_router.py"),
                    "--json",
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(Path(payload["path"]), override.resolve())
            self.assertEqual(override.read_text(encoding="utf-8"), "# Override\n")

    def test_preview_apply_is_idempotent_and_remove_preserves_other_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-router-") as raw:
            path = Path(raw) / ".codex" / "AGENTS.md"

            preview = run_router(path)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(json.loads(preview.stdout)["status"], "preview")
            self.assertFalse(path.exists())

            refused = run_router(path, "--apply")
            self.assertEqual(refused.returncode, 3)
            self.assertFalse(path.exists())

            path.parent.mkdir(parents=True)
            path.write_text("# My rules\n", encoding="utf-8")
            for _ in range(2):
                applied = run_router(path, "--apply", "--yes")
                self.assertEqual(applied.returncode, 0, applied.stderr)
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count("experience-loop:router:start"), 1)
            self.assertIn("# My rules", content)

            removed = run_router(path, "--remove", "--yes")
            self.assertEqual(removed.returncode, 0, removed.stderr)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("experience-loop:router:start", content)
            self.assertIn("# My rules", content)


if __name__ == "__main__":
    unittest.main()
