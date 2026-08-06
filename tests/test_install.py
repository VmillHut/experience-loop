from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Optional
from unittest import mock


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


def load_installer_module():
    spec = importlib.util.spec_from_file_location(
        "experience_loop_installer_under_test", ROOT / "scripts" / "install.py"
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load scripts/install.py for static validation tests.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            runtime = Path(payload["runtime"])
            onboarding_reference = Path(payload["onboarding_reference"])
            self.assertTrue(runtime.is_absolute())
            self.assertTrue(onboarding_reference.is_absolute())
            self.assertEqual(
                runtime, (target / "scripts" / "experience_loop.py").resolve()
            )
            self.assertEqual(
                onboarding_reference,
                (target / "references" / "onboarding.md").resolve(),
            )
            self.assertTrue(runtime.is_file())
            self.assertTrue(onboarding_reference.is_file())
            self.assertIn(str(onboarding_reference), payload["onboarding_prompt"])
            self.assertIn("$experience-loop", payload["onboarding_prompt"])
            self.assertIn("所有画像问题都可跳过", payload["onboarding_prompt"])

            first_commands = payload["commands"]
            first_argv = payload["command_argv"]
            self.assertEqual(
                set(first_commands),
                {
                    "version",
                    "mode",
                    "status",
                    "setup",
                    "doctor",
                    "uninstall",
                    "upgrade_from_current_checkout",
                    "rollback",
                },
            )
            self.assertEqual(set(first_argv), set(first_commands))
            self.assertIsNone(first_commands["rollback"])
            self.assertIsNone(first_argv["rollback"])
            self.assertFalse(payload["rollback_available"])
            self.assertIsNone(payload["rollback_note"])
            for name in ("version", "mode", "status", "setup", "doctor", "uninstall"):
                self.assertIn(str(target.resolve()), first_commands[name], name)
                self.assertIn(str(target.resolve()), " ".join(first_argv[name]), name)

            self.assertEqual(
                payload["command_shell"], "powershell" if os.name == "nt" else "posix"
            )
            provenance = payload["source_provenance"]
            self.assertEqual(Path(provenance["path"]), ROOT.resolve())
            self.assertIn("repository", provenance)
            self.assertIn("commit", provenance)
            self.assertIn("dirty", provenance)
            self.assertEqual(
                payload["onboarding_state"], "check_runtime_before_onboarding"
            )

            argv_version = subprocess.run(
                first_argv["version"],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(argv_version.returncode, 0, argv_version.stderr)
            self.assertIn("experience-loop", argv_version.stdout)

            if os.name == "nt":
                shell = shutil.which("powershell") or shutil.which("pwsh")
                self.assertIsNotNone(shell)
                copied = subprocess.run(
                    [shell, "-NoProfile", "-Command", first_commands["version"]],
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    check=False,
                )
            else:
                copied = subprocess.run(
                    first_commands["version"],
                    shell=True,
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    check=False,
                )
            self.assertEqual(copied.returncode, 0, copied.stderr)
            self.assertIn("experience-loop", copied.stdout)

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
            self.assertTrue(payload["rollback_available"])
            self.assertIsNone(payload["rollback_note"])

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

    def test_installer_reports_already_active_with_complete_absolute_handoff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-active-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)

            active = run_python(
                target / "scripts" / "install.py",
                "--target",
                str(target),
                "--json",
            )
            self.assertEqual(active.returncode, 0, active.stderr)
            data = json.loads(active.stdout)
            self.assertEqual(data["status"], "already-active")
            self.assertIsNone(data["backup"])
            self.assertEqual(data["migrated_legacy_backups"], [])

            runtime = Path(data["runtime"])
            onboarding_reference = Path(data["onboarding_reference"])
            self.assertTrue(runtime.is_absolute())
            self.assertTrue(onboarding_reference.is_absolute())
            self.assertEqual(
                runtime, (target / "scripts" / "experience_loop.py").resolve()
            )
            self.assertEqual(
                onboarding_reference,
                (target / "references" / "onboarding.md").resolve(),
            )
            self.assertIn(str(onboarding_reference), data["onboarding_prompt"])

            commands = data["commands"]
            command_argv = data["command_argv"]
            self.assertEqual(
                set(commands),
                {
                    "version",
                    "mode",
                    "status",
                    "setup",
                    "doctor",
                    "uninstall",
                    "upgrade_from_current_checkout",
                    "rollback",
                },
            )
            self.assertEqual(set(command_argv), set(commands))
            self.assertIsNone(commands["rollback"])
            self.assertIsNone(commands["upgrade_from_current_checkout"])
            self.assertIsNone(command_argv["rollback"])
            self.assertIsNone(command_argv["upgrade_from_current_checkout"])
            self.assertFalse(data["rollback_available"])
            self.assertIsNone(data["rollback_note"])
            for name in ("version", "mode", "status", "setup", "doctor", "uninstall"):
                self.assertIn(str(target.resolve()), commands[name], name)
                self.assertIn(str(target.resolve()), " ".join(command_argv[name]), name)

    def test_previous_runtime_contract_upgrades_without_force_and_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-previous-upgrade-") as raw:
            root = Path(raw)
            previous_source = root / "previous-source"
            target = root / "skills" / "experience-loop"
            shutil.copytree(
                ROOT,
                previous_source,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            (previous_source / "references" / "onboarding.md").unlink()
            previous_installer = previous_source / "scripts" / "install.py"
            source = previous_installer.read_text(encoding="utf-8")
            self.assertIn('    "references/onboarding.md",\n', source)
            self.assertIn(
                '        "runtime_contract": CURRENT_RUNTIME_CONTRACT,\n', source
            )
            source = source.replace('    "references/onboarding.md",\n', "", 1)
            source = source.replace(
                '        "runtime_contract": CURRENT_RUNTIME_CONTRACT,\n', "", 1
            )
            previous_installer.write_text(source, encoding="utf-8")

            previous = run_python(
                previous_installer, "--target", str(target), "--json"
            )
            self.assertEqual(previous.returncode, 0, previous.stderr)
            previous_marker = json.loads(
                (target / ".experience-loop-install.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("runtime_contract", previous_marker)
            self.assertFalse((target / "references" / "onboarding.md").exists())

            upgraded = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            data = json.loads(upgraded.stdout)
            self.assertTrue(data["rollback_available"])
            backup = Path(data["backup"])
            self.assertFalse((backup / "references" / "onboarding.md").exists())

            rollback = run_python(
                backup / "scripts" / "install.py",
                "--target",
                str(target),
                "--json",
            )
            self.assertEqual(rollback.returncode, 0, rollback.stderr)
            self.assertFalse((target / "references" / "onboarding.md").exists())
            version = run_python(
                target / "scripts" / "experience_loop.py", "--version"
            )
            self.assertEqual(version.returncode, 0, version.stderr)
            self.assertIn("experience-loop", version.stdout)

    def test_empty_profile_remains_readable_after_strict_legacy_rollback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-rollback-profile-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            home = root / "experience-home"

            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            setup = run_python(
                target / "scripts" / "experience_loop.py",
                "--home",
                str(home),
                "--json",
                "setup",
            )
            self.assertEqual(setup.returncode, 0, setup.stderr)
            self.assertIsNone(json.loads(setup.stdout)["data"]["profile"]["role"])
            stored_profile = json.loads(
                (home / "profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored_profile["role"], "software-developer")
            self.assertFalse(stored_profile["role_provided"])

            # Simulate the previous runtime's stricter on-disk role contract, then
            # let a normal upgrade preserve that runtime as the rollback source.
            profile_module = (
                target / "scripts" / "experience_loop_lib" / "profile.py"
            )
            source = profile_module.read_text(encoding="utf-8")
            marker = """def validate_profile(value: Any) -> Dict[str, Any]:\n    value = _validate_profile_container(value)\n"""
            replacement = """def validate_profile(value: Any) -> Dict[str, Any]:\n    value = _validate_profile_container(value)\n    legacy_role = value.get(\"role\")\n    if not isinstance(legacy_role, str) or not legacy_role.strip():\n        raise DataCorruptionError(\"profile.json 的 role 必须是非空文本。\")\n"""
            self.assertIn(marker, source)
            profile_module.write_text(
                source.replace(marker, replacement, 1), encoding="utf-8"
            )

            upgraded = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            upgrade_data = json.loads(upgraded.stdout)
            self.assertTrue(upgrade_data["rollback_available"])
            backup = Path(upgrade_data["backup"])

            rollback = run_python(
                backup / "scripts" / "install.py",
                "--target",
                str(target),
                "--json",
            )
            self.assertEqual(rollback.returncode, 0, rollback.stderr)
            status = run_python(
                target / "scripts" / "experience_loop.py",
                "--home",
                str(home),
                "--json",
                "status",
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertTrue(json.loads(status.stdout)["data"]["initialized"])

    def test_force_upgrade_without_complete_backup_installer_suppresses_rollback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-incomplete-backup-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)

            (target / ".experience-loop-install.json").unlink()
            (target / "scripts" / "install.py").unlink()
            upgraded = run_script(
                "install.py", "--target", str(target), "--force", "--json"
            )
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            data = json.loads(upgraded.stdout)
            backup = Path(data["backup"])

            self.assertTrue(backup.is_dir())
            self.assertFalse((backup / "scripts" / "install.py").exists())
            self.assertFalse(data["rollback_available"])
            self.assertIsNone(data["commands"]["rollback"])
            self.assertIsNone(data["command_argv"]["rollback"])
            self.assertIn("Backup was preserved", data["rollback_note"])
            self.assertIn("complete installer", data["rollback_note"])

    def test_force_upgrade_with_missing_runtime_module_suppresses_rollback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-incomplete-runtime-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)

            missing_module = target / "scripts" / "experience_loop_lib" / "cli.py"
            missing_module.unlink()
            upgraded = run_script(
                "install.py", "--target", str(target), "--force", "--json"
            )
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            data = json.loads(upgraded.stdout)
            backup = Path(data["backup"])

            self.assertTrue(backup.is_dir())
            self.assertFalse(
                (backup / "scripts" / "experience_loop_lib" / "cli.py").exists()
            )
            self.assertFalse(data["rollback_available"])
            self.assertIsNone(data["commands"]["rollback"])
            self.assertIsNone(data["command_argv"]["rollback"])
            self.assertIn("Backup was preserved", data["rollback_note"])
            self.assertIn("cli.py", data["rollback_note"])

    def test_intermediate_reparse_component_is_not_a_valid_rollback_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-reparse-runtime-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)

            installer = load_installer_module()
            scripts_directory = target / "scripts"
            real_is_reparse_point = installer._is_reparse_point

            def simulated_reparse_point(path: Path) -> bool:
                if Path(path) == scripts_directory:
                    return True
                return real_is_reparse_point(path)

            with mock.patch.object(
                installer,
                "_is_reparse_point",
                side_effect=simulated_reparse_point,
            ):
                validation_error = installer.managed_install_validation_error(target)
                rollback_error = installer.rollback_source_error(target)

            self.assertIn("reparse point", validation_error)
            self.assertIn("scripts/experience_loop.py", validation_error)
            self.assertEqual(rollback_error, validation_error)

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
