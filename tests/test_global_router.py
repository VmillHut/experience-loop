from __future__ import annotations

import json
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
            "--format",
            "markdown",
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
    def test_instruction_path_is_required_and_never_inferred_from_host_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-router-home-") as raw:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts" / "global_router.py"),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("--path", completed.stderr)
            self.assertEqual(list(Path(raw).iterdir()), [])

    def test_preview_apply_is_idempotent_and_remove_preserves_other_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-router-") as raw:
            path = Path(raw) / "current-host" / "instructions.md"

            preview = run_router(path)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            preview_data = json.loads(preview.stdout)
            self.assertEqual(preview_data["status"], "preview")
            self.assertEqual(preview_data["host"], "current-agent")
            self.assertNotIn("$experience-loop", preview_data["router"])
            self.assertFalse(path.exists())
            self.assertEqual(len(preview_data["current_sha256"]), 64)

            refused = run_router(path, "--apply")
            self.assertEqual(refused.returncode, 3)
            self.assertFalse(path.exists())

            path.parent.mkdir(parents=True)
            path.write_text("# My rules\n", encoding="utf-8")
            for _ in range(2):
                current = json.loads(run_router(path).stdout)
                applied = run_router(
                    path,
                    "--apply",
                    "--yes",
                    "--expected-sha256",
                    current["current_sha256"],
                )
                self.assertEqual(applied.returncode, 0, applied.stderr)
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count("experience-loop:router:start"), 1)
            self.assertIn("# My rules", content)

            remove_preview = json.loads(run_router(path).stdout)
            removed = run_router(
                path,
                "--remove",
                "--yes",
                "--expected-sha256",
                remove_preview["current_sha256"],
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("experience-loop:router:start", content)
            self.assertIn("# My rules", content)

    def test_write_rejects_stale_preview_and_duplicate_markers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-router-race-") as raw:
            path = Path(raw) / "instructions.md"
            path.write_text("# Initial\n", encoding="utf-8")
            preview = json.loads(run_router(path).stdout)
            path.write_text("# Changed\n", encoding="utf-8")

            stale = run_router(
                path,
                "--apply",
                "--yes",
                "--expected-sha256",
                preview["current_sha256"],
            )
            self.assertEqual(stale.returncode, 4)
            self.assertEqual(json.loads(stale.stdout)["status"], "stale-preview")
            self.assertEqual(path.read_text(encoding="utf-8"), "# Changed\n")

            path.write_text(
                "<!-- experience-loop:router:start -->\n"
                "<!-- experience-loop:router:end -->\n"
                "<!-- experience-loop:router:start -->\n"
                "<!-- experience-loop:router:end -->\n",
                encoding="utf-8",
            )
            duplicate = run_router(path)
            self.assertEqual(duplicate.returncode, 4)
            self.assertIn("Multiple", json.loads(duplicate.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
