from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]


def run_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def run_python(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=script.parent,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def declared_skill_name(path: Path) -> Optional[str]:
    skill_file = path / "SKILL.md"
    if not skill_file.is_file():
        return None
    for line in skill_file.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if separator and key.strip() == "name":
            return value.strip().strip("\"'")
    return None


def discoverable_experience_loops(skills_root: Path) -> list[Path]:
    if not skills_root.is_dir():
        return []
    return [
        path
        for path in skills_root.iterdir()
        if path.is_dir() and declared_skill_name(path) == "experience-loop"
    ]


class InstallTests(unittest.TestCase):
    def test_install_update_and_uninstall_preserve_external_data(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-install-") as raw:
            root = Path(raw)
            skills_root = root / "skills"
            target = skills_root / "experience-loop"
            personal = root / ".experience-loop"
            personal.mkdir()
            sentinel = personal / "sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            unrelated = skills_root / "my-private-skill"
            unrelated.mkdir(parents=True)
            unrelated_sentinel = unrelated / "keep.txt"
            unrelated_sentinel.write_text("do not move", encoding="utf-8")

            first = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(first.returncode, 0, first.stderr)
            payload = json.loads(first.stdout)
            self.assertEqual(payload["status"], "installed")
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "agents" / "openai.yaml").is_file())
            self.assertTrue((target / "vendor" / "manifest.json").is_file())
            self.assertTrue((target / "LICENSE").is_file())

            # Simulate the sibling backup layout created by installer v1.
            legacy = target.with_name("experience-loop.backup-20250101T000000Z")
            shutil.copytree(target, legacy)
            self.assertEqual(len(discoverable_experience_loops(skills_root)), 2)

            # Give the current install a value that lets the rollback assertion prove
            # which copy was restored.
            (target / "VERSION").write_text("old-local-version\n", encoding="utf-8")

            second = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(second.returncode, 0, second.stderr)
            payload = json.loads(second.stdout)
            self.assertIsNotNone(payload["backup"])
            backup = Path(payload["backup"])
            expected_backup_root = root / "skill-backups" / "experience-loop"
            self.assertTrue(backup.is_dir())
            self.assertEqual(backup.parent, expected_backup_root)
            self.assertEqual(
                (backup / "VERSION").read_text(encoding="utf-8"),
                "old-local-version\n",
            )
            self.assertEqual(len(payload["migrated_legacy_backups"]), 1)
            migrated_legacy = Path(payload["migrated_legacy_backups"][0])
            self.assertEqual(migrated_legacy.parent, expected_backup_root)
            self.assertFalse(legacy.exists())
            self.assertEqual(discoverable_experience_loops(skills_root), [target])
            self.assertEqual(
                unrelated_sentinel.read_text(encoding="utf-8"), "do not move"
            )

            commands = payload["commands"]
            self.assertIn(str(target.resolve()), commands["status"])
            self.assertIn(str(target.resolve()), commands["uninstall"])
            self.assertIn(str(ROOT.resolve()), commands["upgrade_from_current_checkout"])
            self.assertIn(str(backup.resolve()), commands["rollback"])

            rollback = run_python(
                backup / "scripts" / "install.py",
                "--target",
                str(target),
                "--json",
            )
            self.assertEqual(rollback.returncode, 0, rollback.stderr)
            self.assertEqual(
                (target / "VERSION").read_text(encoding="utf-8"),
                "old-local-version\n",
            )
            self.assertEqual(discoverable_experience_loops(skills_root), [target])

            removed = run_script(
                "uninstall.py", "--target", str(target), "--yes", "--json"
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(target.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual(discoverable_experience_loops(skills_root), [])
            self.assertEqual(
                unrelated_sentinel.read_text(encoding="utf-8"), "do not move"
            )

    def test_installer_refuses_unrecognized_target_without_force(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-install-") as raw:
            target = Path(raw) / "experience-loop"
            target.mkdir()
            (target / "private.txt").write_text("mine", encoding="utf-8")

            result = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(result.returncode, 4)
            self.assertEqual(json.loads(result.stdout)["status"], "error")
            self.assertEqual((target / "private.txt").read_text(encoding="utf-8"), "mine")

    def test_uninstaller_rejects_forged_marker_and_dangerous_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-install-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            target.mkdir(parents=True)
            sentinel = target / "private.txt"
            sentinel.write_text("keep", encoding="utf-8")
            (target / ".experience-loop-install.json").write_text(
                json.dumps({"skill": "experience-loop"}), encoding="utf-8"
            )

            forged = run_script(
                "uninstall.py", "--target", str(target), "--yes", "--json"
            )
            self.assertEqual(forged.returncode, 3)
            self.assertEqual(json.loads(forged.stdout)["status"], "refused")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

            broad = root / "skills"
            broad_sentinel = broad / "root-sentinel.txt"
            broad_sentinel.write_text("keep root", encoding="utf-8")
            dangerous = run_script(
                "uninstall.py", "--target", str(broad), "--yes", "--json"
            )
            self.assertEqual(dangerous.returncode, 3)
            self.assertEqual(json.loads(dangerous.stdout)["status"], "refused")
            self.assertEqual(broad_sentinel.read_text(encoding="utf-8"), "keep root")

    def test_installed_commands_survive_source_checkout_deletion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-install-") as raw:
            root = Path(raw)
            source = root / "checkout" / "experience-loop"
            target = root / "user" / "skills" / "experience-loop"
            home = root / "experience-home"
            shutil.copytree(
                ROOT,
                source,
                ignore=shutil.ignore_patterns(
                    ".git", "__pycache__", "*.pyc", ".experience-loop-export.zip"
                ),
            )

            installed = run_python(
                source / "scripts" / "install.py",
                "--target",
                str(target),
                "--json",
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            commands = json.loads(installed.stdout)["commands"]
            self.assertIn(
                str((target / "scripts" / "experience_loop.py").resolve()),
                commands["status"],
            )
            self.assertIn(
                str((target / "scripts" / "uninstall.py").resolve()),
                commands["uninstall"],
            )

            shutil.rmtree(source.parent)
            status = run_python(
                target / "scripts" / "experience_loop.py",
                "--home",
                str(home),
                "--json",
                "status",
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertFalse(json.loads(status.stdout)["data"]["initialized"])

            removed = run_python(
                target / "scripts" / "uninstall.py", "--yes", "--json"
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(target.exists())
            self.assertEqual(discoverable_experience_loops(target.parent), [])


if __name__ == "__main__":
    unittest.main()
