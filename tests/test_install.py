from __future__ import annotations

import contextlib
import importlib.util
import hashlib
import io
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


def run_script(
    script: str, *args: str, env: Optional[dict[str, str]] = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(ROOT / "scripts" / script), *args],
        cwd=ROOT,
        env=env,
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


def load_uninstaller_module():
    scripts_directory = str(ROOT / "scripts")
    spec = importlib.util.spec_from_file_location(
        "experience_loop_uninstaller_under_test", ROOT / "scripts" / "uninstall.py"
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load scripts/uninstall.py for recovery tests.")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, scripts_directory)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(scripts_directory)
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

            first = run_script(
                "install.py",
                "--host",
                "codex",
                "--scope",
                "user",
                "--invocation",
                "$experience-loop",
                "--reload-hint",
                "Use the current host's verified refresh flow.",
                "--host-evidence",
                "Resolved by the installation AI from the live host session.",
                "--target",
                str(target),
                "--json",
            )
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
            self.assertIn("完整核心已安装", payload["onboarding_prompt"])
            self.assertIn("所有画像问题都可跳过", payload["onboarding_prompt"])
            self.assertEqual(payload["host"], "codex")
            self.assertEqual(payload["invocation"], "$experience-loop")
            self.assertEqual(
                payload["core_behavior_contract"], "unchanged-across-hosts"
            )
            self.assertEqual(
                payload["support_level"],
                "dynamic-host-contract-requires-session-validation",
            )
            self.assertEqual(
                payload["host_contract_status"], "resolved-by-installing-agent"
            )
            self.assertEqual(
                payload["discovery_roots_coverage"], "asserted-by-installing-agent"
            )
            self.assertEqual(payload["capabilities"]["guidance"], "installed-core")
            self.assertEqual(
                payload["capabilities"]["knowledge_lens"],
                "requires-runtime-validation",
            )

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

            inherited = run_script(
                "install.py",
                "--target",
                str(target),
                "--dry-run",
                "--json",
            )
            self.assertEqual(inherited.returncode, 0, inherited.stderr)
            inherited_payload = json.loads(inherited.stdout)
            self.assertEqual(inherited_payload["host"], "codex")
            self.assertEqual(inherited_payload["scope"], "user")
            self.assertEqual(inherited_payload["invocation"], "$experience-loop")
            self.assertEqual(
                inherited_payload["host_evidence"],
                "Resolved by the installation AI from the live host session.",
            )

            partial = run_script(
                "install.py",
                "--target",
                str(target),
                "--reload-hint",
                "Updated verified refresh flow.",
                "--dry-run",
                "--json",
            )
            self.assertEqual(partial.returncode, 0, partial.stderr)
            partial_payload = json.loads(partial.stdout)
            self.assertEqual(partial_payload["host"], "codex")
            self.assertEqual(partial_payload["scope"], "user")
            self.assertEqual(partial_payload["invocation"], "$experience-loop")
            self.assertEqual(
                partial_payload["reload_hint"], "Updated verified refresh flow."
            )
            self.assertEqual(
                partial_payload["host_evidence"],
                "Resolved by the installation AI from the live host session.",
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

            second = run_script(
                "install.py",
                "--host",
                "codex",
                "--scope",
                "user",
                "--invocation",
                "$experience-loop",
                "--reload-hint",
                "Use the current host's verified refresh flow.",
                "--host-evidence",
                "Resolved by the installation AI from the live host session.",
                "--target",
                str(target),
                "--json",
            )
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
            self.assertIn("--host", payload["command_argv"]["upgrade_from_current_checkout"])
            self.assertIn("codex", payload["command_argv"]["upgrade_from_current_checkout"])
            self.assertIn(str(backup.resolve()), commands["rollback"])
            self.assertTrue(payload["rollback_available"])
            self.assertIsNone(payload["rollback_note"])

            rollback = subprocess.run(
                payload["command_argv"]["rollback"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
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

            secondary_root = Path(raw) / "secondary-skills"
            duplicate = secondary_root / "experience-loop"
            shutil.copytree(target, duplicate)
            blocked = run_python(
                target / "scripts" / "install.py",
                "--target",
                str(target),
                "--discovery-root",
                str(secondary_root),
                "--json",
            )
            self.assertEqual(blocked.returncode, 4)
            self.assertIn("Another discoverable", json.loads(blocked.stdout)["error"])

    def test_verify_only_accepts_complete_host_managed_copy_without_marker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-host-managed-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            shutil.copytree(
                ROOT,
                target,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            marker = target / ".experience-loop-install.json"
            self.assertFalse(marker.exists())

            verified = run_python(
                target / "scripts" / "install.py",
                "--target",
                str(target),
                "--verify-only",
                "--json",
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            data = json.loads(verified.stdout)
            self.assertEqual(data["status"], "host-managed-copy-validated")
            self.assertEqual(data["install_manager"], "host-native")
            self.assertEqual(
                data["filesystem_status"], "complete-host-managed-copy-validated"
            )
            self.assertEqual(
                data["lifecycle_owner"], "current-host-native-install-manager"
            )
            self.assertFalse(marker.exists())

            duplicate = target.with_name("experience-loop-copy")
            shutil.copytree(target, duplicate)
            blocked = run_python(
                target / "scripts" / "install.py",
                "--target",
                str(target),
                "--verify-only",
                "--json",
            )
            self.assertEqual(blocked.returncode, 4)
            self.assertIn("Another discoverable", json.loads(blocked.stdout)["error"])

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
            source = source.replace('        "installer_version": 4,\n', '        "installer_version": 3,\n', 1)
            current_contract_map = """RUNTIME_CONTRACT_FILES = {
    1: RUNTIME_CONTRACT_1_FILES,
    CURRENT_RUNTIME_CONTRACT: CURRENT_SOURCE_REQUIRED_FILES,
}
"""
            self.assertIn(current_contract_map, source)
            source = source.replace(
                current_contract_map,
                "RUNTIME_CONTRACT_FILES = {1: RUNTIME_CONTRACT_1_FILES}\n",
                1,
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
            rollback_argv = data["command_argv"]["rollback"]
            self.assertIsNotNone(rollback_argv)
            self.assertIn("--restore-from", rollback_argv)
            self.assertNotEqual(Path(rollback_argv[1]).parent, backup / "scripts")

            rollback = subprocess.run(
                rollback_argv,
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
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

            rollback = subprocess.run(
                upgrade_data["command_argv"]["rollback"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
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
                installer.park_skill_manifest(target)
                try:
                    validation_error = installer.managed_install_validation_error(
                        target, installer.DORMANT_SKILL_MANIFEST
                    )
                    rollback_error = installer.rollback_source_error(target)
                finally:
                    installer.activate_parked_skill_manifest(target)

            self.assertIn("reparse point", validation_error)
            self.assertIn("scripts/experience_loop.py", validation_error)
            self.assertEqual(rollback_error, validation_error)

    def test_restricted_parent_uses_dormant_transaction_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-restricted-parent-") as raw:
            root = Path(raw)
            skills_root = root / "skills"
            skills_root.mkdir()
            target = skills_root / "experience-loop"
            preferred_blocker = root / "skill-backups"
            preferred_blocker.write_text("host-owned\n", encoding="utf-8")
            fallback = (
                skills_root / ".experience-loop-transactions" / "experience-loop"
            )

            preview = run_script(
                "install.py", "--target", str(target), "--dry-run", "--json"
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            preview_data = json.loads(preview.stdout)
            self.assertEqual(preview_data["status"], "dry-run")
            self.assertEqual(
                Path(preview_data["transaction_root"]), fallback.resolve()
            )
            self.assertEqual(
                preview_data["install_plan"]["transaction_capability"], "verified"
            )
            self.assertFalse(fallback.exists())
            self.assertFalse(target.exists())
            self.assertEqual(
                preferred_blocker.read_text(encoding="utf-8"), "host-owned\n"
            )

            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            installed_data = json.loads(installed.stdout)
            self.assertEqual(Path(installed_data["transaction_root"]), fallback.resolve())
            self.assertIsNone(installed_data["backup"])
            self.assertFalse(installed_data["rollback_available"])
            self.assertEqual(discoverable_experience_loops(skills_root), [target])
            self.assertFalse(fallback.exists())
            self.assertEqual(
                preferred_blocker.read_text(encoding="utf-8"), "host-owned\n"
            )

    def test_restricted_parent_upgrade_and_rollback_use_new_manager(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-restricted-upgrade-") as raw:
            root = Path(raw)
            skills_root = root / "skills"
            skills_root.mkdir()
            target = skills_root / "experience-loop"
            preferred_blocker = root / "skill-backups"
            preferred_blocker.write_text("host-owned\n", encoding="utf-8")
            fallback = (
                skills_root / ".experience-loop-transactions" / "experience-loop"
            )

            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            (target / "VERSION").write_text("restricted-old-version\n", encoding="utf-8")
            (target / "scripts" / "install.py").write_text(
                "raise SystemExit(97)\n", encoding="utf-8"
            )

            upgraded = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            data = json.loads(upgraded.stdout)
            backup = Path(data["backup"])
            self.assertEqual(backup.parent, fallback.resolve())
            self.assertFalse((backup / "SKILL.md").exists())
            self.assertTrue((backup / ".experience-loop-SKILL.md").is_file())
            self.assertTrue(data["rollback_available"])
            rollback_argv = data["command_argv"]["rollback"]
            self.assertIsNotNone(rollback_argv)
            self.assertNotEqual(Path(rollback_argv[1]), backup / "scripts" / "install.py")

            rollback = subprocess.run(
                rollback_argv,
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(rollback.returncode, 0, rollback.stderr)
            self.assertEqual(
                (target / "VERSION").read_text(encoding="utf-8"),
                "restricted-old-version\n",
            )
            self.assertEqual(discoverable_experience_loops(skills_root), [target])
            self.assertEqual(
                preferred_blocker.read_text(encoding="utf-8"), "host-owned\n"
            )

    def test_rollback_move_failure_reactivates_current_target(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="experience-loop-rollback-recovery-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            upgraded = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            data = json.loads(upgraded.stdout)
            backup = Path(data["backup"])
            transaction_root = Path(data["transaction_root"])
            marker = json.loads(
                (target / ".experience-loop-install.json").read_text(encoding="utf-8")
            )
            contract = marker["host_contract"]
            current_version = (target / "VERSION").read_text(encoding="utf-8")

            with mock.patch.object(
                installer,
                "_move_to_backup",
                side_effect=OSError("simulated rollback move failure"),
            ):
                with self.assertRaisesRegex(OSError, "simulated rollback move failure"):
                    installer.restore_backup(
                        target, backup, contract, transaction_root
                    )

            self.assertEqual(
                (target / "VERSION").read_text(encoding="utf-8"), current_version
            )
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertFalse((target / ".experience-loop-SKILL.md").exists())
            self.assertTrue((backup / ".experience-loop-SKILL.md").is_file())
            self.assertEqual(discoverable_experience_loops(target.parent), [target])

    def test_committed_first_install_reports_lifecycle_cleanup_as_warning(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="experience-loop-cleanup-warning-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            transaction_root = root / "skill-backups" / "experience-loop"
            manager_installer = transaction_root / "install.py"
            contract = {
                "host": "Test Agent",
                "scope": "custom",
                "target": str(target.resolve()),
                "invocation": None,
                "reload_hint": None,
                "host_evidence": "Test contract.",
                "discovery_roots": [str(target.parent.resolve())],
                "affected_hosts": ["Test Agent"],
            }
            real_unlink = Path.unlink

            def fail_manager_cleanup(path: Path, *args, **kwargs):
                if installer._same_path(path, manager_installer):
                    raise PermissionError("simulated lifecycle cleanup failure")
                return real_unlink(path, *args, **kwargs)

            with mock.patch.object(Path, "unlink", new=fail_manager_cleanup):
                result = installer.install(ROOT, target, False, contract)

            self.assertEqual(result["status"], "installed")
            self.assertTrue(result["warnings"])
            self.assertIn("lifecycle cleanup failed", result["warnings"][0])
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertEqual(discoverable_experience_loops(target.parent), [target])

    def test_dry_run_blocks_when_all_transaction_roots_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-no-transaction-") as raw:
            root = Path(raw)
            skills_root = root / "skills"
            skills_root.mkdir()
            target = skills_root / "experience-loop"
            preferred_blocker = root / "skill-backups"
            fallback_blocker = skills_root / ".experience-loop-transactions"
            preferred_blocker.write_text("host-owned\n", encoding="utf-8")
            fallback_blocker.write_text("host-owned\n", encoding="utf-8")

            preview = run_script(
                "install.py", "--target", str(target), "--dry-run", "--json"
            )
            self.assertEqual(preview.returncode, 4, preview.stderr)
            preview_data = json.loads(preview.stdout)
            self.assertEqual(preview_data["status"], "blocked")
            self.assertIsNone(preview_data["transaction_root"])
            self.assertEqual(
                preview_data["install_plan"]["transaction_capability"], "blocked"
            )
            self.assertTrue(preview_data["install_plan"]["blockers"])

            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 4, installed.stderr)
            self.assertFalse(target.exists())
            self.assertEqual(
                preferred_blocker.read_text(encoding="utf-8"), "host-owned\n"
            )
            self.assertEqual(
                fallback_blocker.read_text(encoding="utf-8"), "host-owned\n"
            )

    def test_rejected_outer_transaction_path_still_uses_dormant_fallback(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="experience-loop-reparse-fallback-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            preferred = root / "skill-backups" / "experience-loop"
            fallback = target.parent / ".experience-loop-transactions" / "experience-loop"
            contract = {
                "host": "Test Agent",
                "scope": "custom",
                "target": str(target.resolve()),
                "invocation": None,
                "reload_hint": None,
                "host_evidence": "Test contract.",
                "discovery_roots": [str(target.parent.resolve())],
                "affected_hosts": ["Test Agent"],
            }
            real_first_reparse = installer.first_reparse_component

            def reject_preferred(path: Path) -> Optional[Path]:
                if installer._same_path(path, preferred):
                    return preferred
                return real_first_reparse(path)

            with mock.patch.object(
                installer,
                "first_reparse_component",
                side_effect=reject_preferred,
            ):
                plan = installer.install_plan(target, False, contract)

            self.assertEqual(plan["transaction_capability"], "verified")
            self.assertEqual(Path(plan["transaction_root"]), fallback.resolve())
            self.assertEqual(plan["transaction_attempts"][0]["status"], "unavailable")
            self.assertEqual(plan["transaction_attempts"][1]["status"], "ready")

    def test_activation_failure_restores_previous_target_without_discoverable_residue(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="experience-loop-activation-failure-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            first = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(first.returncode, 0, first.stderr)
            (target / "VERSION").write_text("before-failure\n", encoding="utf-8")
            contract = {
                "host": "Test Agent",
                "scope": "custom",
                "target": str(target.resolve()),
                "invocation": None,
                "reload_hint": None,
                "host_evidence": "Test contract.",
                "discovery_roots": [str(target.parent.resolve())],
                "affected_hosts": ["Test Agent"],
            }
            real_activate = installer.activate_parked_skill_manifest
            failed = False

            def fail_first_activation(path: Path) -> bool:
                nonlocal failed
                if not failed and Path(path) == target:
                    failed = True
                    raise OSError("simulated activation failure")
                return real_activate(path)

            with mock.patch.object(
                installer,
                "activate_parked_skill_manifest",
                side_effect=fail_first_activation,
            ):
                with self.assertRaisesRegex(OSError, "simulated activation failure"):
                    installer.install(ROOT, target, False, contract)

            self.assertEqual(
                (target / "VERSION").read_text(encoding="utf-8"),
                "before-failure\n",
            )
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertFalse((target / ".experience-loop-SKILL.md").exists())
            self.assertEqual(discoverable_experience_loops(target.parent), [target])
            transaction_root = root / "skill-backups" / "experience-loop"
            if transaction_root.exists():
                self.assertFalse(
                    any(
                        path.name.startswith(".install-")
                        for path in transaction_root.iterdir()
                    )
                )
                self.assertEqual(list(transaction_root.rglob("SKILL.md")), [])

    def test_installer_refuses_unrecognized_target_without_force(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-install-") as raw:
            target = Path(raw) / "experience-loop"
            target.mkdir()
            (target / "private.txt").write_text("mine", encoding="utf-8")

            preview = run_script(
                "install.py", "--target", str(target), "--dry-run", "--json"
            )
            self.assertEqual(preview.returncode, 4)
            preview_data = json.loads(preview.stdout)
            self.assertEqual(preview_data["status"], "blocked")
            self.assertTrue(preview_data["install_plan"]["requires_force"])
            self.assertTrue(preview_data["install_plan"]["blockers"])

            forced_preview = run_script(
                "install.py",
                "--target",
                str(target),
                "--force",
                "--dry-run",
                "--json",
            )
            self.assertEqual(forced_preview.returncode, 0, forced_preview.stderr)
            self.assertEqual(json.loads(forced_preview.stdout)["status"], "dry-run")

            result = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(result.returncode, 4)
            self.assertEqual(json.loads(result.stdout)["status"], "error")
            self.assertEqual((target / "private.txt").read_text(encoding="utf-8"), "mine")

    def test_partial_uninstall_never_restores_a_damaged_quarantine(self) -> None:
        uninstaller = load_uninstaller_module()
        with tempfile.TemporaryDirectory(prefix="experience-loop-partial-uninstall-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            real_rmtree = uninstaller.shutil.rmtree
            failed = False

            def partial_rmtree(path, *args, **kwargs):
                nonlocal failed
                candidate = Path(path)
                if not failed and candidate.name.startswith("uninstall-pending-"):
                    failed = True
                    (candidate / ".experience-loop-SKILL.md").unlink()
                    (candidate / "VERSION").unlink()
                    raise OSError("simulated partial quarantine deletion")
                return real_rmtree(path, *args, **kwargs)

            stdout = io.StringIO()
            stderr = io.StringIO()
            argv = [
                "uninstall.py",
                "--target",
                str(target),
                "--yes",
                "--json",
            ]
            with mock.patch.object(uninstaller.shutil, "rmtree", side_effect=partial_rmtree):
                with mock.patch.object(sys, "argv", argv):
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        exit_code = uninstaller.main()

            self.assertEqual(exit_code, 3)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["status"], "refused")
            self.assertIn("partially deleted uninstall quarantine", data["error"])
            self.assertFalse(target.exists())
            self.assertEqual(discoverable_experience_loops(target.parent), [])
            transaction_root = root / "skill-backups" / "experience-loop"
            quarantines = [
                path
                for path in transaction_root.iterdir()
                if path.name.startswith("uninstall-pending-")
            ]
            self.assertEqual(len(quarantines), 1)
            self.assertFalse((quarantines[0] / "SKILL.md").exists())

    def test_uninstaller_rejects_forged_marker_and_dangerous_target(self) -> None:
        installer = load_installer_module()
        anchor = Path(Path.cwd().anchor)
        with self.assertRaisesRegex(RuntimeError, "too close"):
            installer.validate_target_path(anchor / "temporary" / "experience-loop")
        with self.assertRaisesRegex(RuntimeError, "too close"):
            installer.validate_target_path(Path.home() / "experience-loop")
        with tempfile.TemporaryDirectory(prefix="experience-loop-backup-root-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            unsafe = Path(raw) / "skill-backups"
            with mock.patch.object(
                installer, "first_reparse_component", return_value=unsafe
            ):
                with self.assertRaisesRegex(RuntimeError, "backup root"):
                    installer.backup_root_for_target(target)
        with tempfile.TemporaryDirectory(prefix="experience-loop-reparse-scan-") as raw:
            root = Path(raw) / "skills"
            candidate = root / "experience-loop"
            candidate.mkdir(parents=True)
            with mock.patch.object(
                installer,
                "_is_reparse_point",
                side_effect=lambda path: installer._same_path(path, candidate),
            ):
                with self.assertRaisesRegex(RuntimeError, "possible duplicate"):
                    installer.discoverable_installations(candidate, [root])

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

    def test_dynamic_host_contracts_install_identical_core_with_distinct_handoffs(self) -> None:
        digests: dict[str, str] = {}
        expected = {
            "Desktop Agent": "invoke experience-loop from the palette",
            "Terminal Agent": "/experience-loop",
            "Future Agent": "ask the host to use experience-loop",
        }
        with tempfile.TemporaryDirectory(prefix="experience-loop-hosts-") as raw:
            root = Path(raw)
            for index, (host, invocation) in enumerate(expected.items()):
                target = root / f"host-{index}" / "skills" / "experience-loop"

                preview = run_script(
                    "install.py",
                    "--host",
                    host,
                    "--scope",
                    "user",
                    "--target",
                    str(target),
                    "--invocation",
                    invocation,
                    "--reload-hint",
                    f"Use {host}'s current verified refresh flow.",
                    "--host-evidence",
                    f"Resolved from the live {host} session and current help.",
                    "--dry-run",
                    "--json",
                )
                self.assertEqual(preview.returncode, 0, preview.stderr)
                preview_data = json.loads(preview.stdout)
                target = target.resolve()
                self.assertEqual(Path(preview_data["target"]), target.resolve())
                self.assertEqual(preview_data["invocation"], invocation)
                self.assertEqual(
                    preview_data["host_contract_status"],
                    "resolved-by-installing-agent",
                )
                self.assertEqual(
                    preview_data["discovery_status"],
                    "requires-host-session-validation",
                )

                installed = run_script(
                    "install.py",
                    "--host",
                    host,
                    "--scope",
                    "user",
                    "--target",
                    str(target),
                    "--invocation",
                    invocation,
                    "--reload-hint",
                    f"Use {host}'s current verified refresh flow.",
                    "--host-evidence",
                    f"Resolved from the live {host} session and current help.",
                    "--json",
                )
                self.assertEqual(installed.returncode, 0, installed.stderr)
                data = json.loads(installed.stdout)
                self.assertEqual(data["host"], host)
                self.assertEqual(data["invocation"], invocation)
                self.assertNotIn(invocation, data["onboarding_prompt"])
                self.assertIn("完整核心已安装", data["onboarding_prompt"])
                digests[host] = hashlib.sha256(
                    (target / "SKILL.md").read_bytes()
                ).hexdigest()

            self.assertEqual(len(set(digests.values())), 1, digests)

    def test_dynamic_contract_requires_target_and_never_claims_host_discovery(self) -> None:
        missing_target = run_script("install.py", "--dry-run", "--json")
        self.assertEqual(missing_target.returncode, 2)
        self.assertIn("--target", missing_target.stderr)

        with tempfile.TemporaryDirectory(prefix="experience-loop-contract-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            unresolved = run_script(
                "install.py",
                "--target",
                str(target),
                "--dry-run",
                "--json",
            )
            self.assertEqual(unresolved.returncode, 0, unresolved.stderr)
            data = json.loads(unresolved.stdout)
            self.assertEqual(data["host"], "current-agent")
            self.assertIsNone(data["invocation"])
            self.assertEqual(data["host_contract_status"], "missing-host-evidence")
            self.assertEqual(
                data["discovery_status"], "requires-host-session-validation"
            )

            bad_contract = run_script(
                "install.py",
                "--target",
                str(target),
                "--host",
                "bad\nhost",
                "--dry-run",
                "--json",
            )
            self.assertEqual(bad_contract.returncode, 4)
            self.assertIn("single printable line", json.loads(bad_contract.stdout)["error"])

    def test_ai_declared_discovery_roots_block_duplicates_and_report_sharing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-shared-host-") as raw:
            root = Path(raw)
            secondary_root = root / "secondary-skills"
            secondary_target = secondary_root / "experience-loop"
            first = run_script(
                "install.py",
                "--host",
                "CLI Agent",
                "--target",
                str(secondary_target),
                "--host-evidence",
                "Resolved by the live CLI Agent.",
                "--json",
            )
            self.assertEqual(first.returncode, 0, first.stderr)

            primary_target = root / "primary-skills" / "experience-loop"
            second = run_script(
                "install.py",
                "--host",
                "Desktop Agent",
                "--target",
                str(primary_target),
                "--discovery-root",
                str(secondary_root),
                "--host-evidence",
                "Resolved by the live Desktop Agent.",
                "--json",
            )
            self.assertEqual(second.returncode, 4)
            self.assertIn("Another discoverable", json.loads(second.stdout)["error"])

            preview = run_script(
                "install.py",
                "--host",
                "Desktop Agent",
                "--target",
                str(primary_target),
                "--discovery-root",
                str(secondary_root),
                "--affected-host",
                "Desktop Agent",
                "--affected-host",
                "CLI Agent",
                "--host-evidence",
                "The installation AI verified a shared discovery directory.",
                "--dry-run",
                "--json",
            )
            self.assertEqual(preview.returncode, 4, preview.stderr)
            preview_data = json.loads(preview.stdout)
            self.assertEqual(preview_data["status"], "blocked")
            self.assertEqual(
                preview_data["affected_hosts"], ["Desktop Agent", "CLI Agent"]
            )
            self.assertEqual(
                preview_data["install_plan"]["duplicates"],
                [str(secondary_target.resolve())],
            )

    def test_upgrade_can_replace_stale_discovery_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-replace-roots-") as raw:
            root = Path(raw)
            target = root / "skills" / "experience-loop"
            stale_root = root / "stale-skills"
            current_root = root / "current-skills"
            installed = run_script(
                "install.py",
                "--target",
                str(target),
                "--discovery-root",
                str(stale_root),
                "--json",
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            stale_root.write_text("obsolete host path\n", encoding="utf-8")
            current_root.mkdir()

            missing_evidence = run_script(
                "install.py",
                "--target",
                str(target),
                "--replace-discovery-roots",
                "--discovery-root",
                str(current_root),
                "--dry-run",
                "--json",
            )
            self.assertEqual(missing_evidence.returncode, 4)
            self.assertIn(
                "requires fresh --host-evidence",
                json.loads(missing_evidence.stdout)["error"],
            )

            upgraded = run_script(
                "install.py",
                "--target",
                str(target),
                "--replace-discovery-roots",
                "--discovery-root",
                str(current_root),
                "--host-evidence",
                "The installation AI verified the current discovery roots.",
                "--json",
            )
            self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
            data = json.loads(upgraded.stdout)
            roots = data["discovery_roots"]
            self.assertIn(str(target.parent.resolve()), roots)
            self.assertIn(str(current_root.resolve()), roots)
            self.assertNotIn(str(stale_root.resolve()), roots)
            marker = json.loads(
                (target / ".experience-loop-install.json").read_text(encoding="utf-8")
            )
            self.assertEqual(marker["host_contract"]["discovery_roots"], roots)

            rollback = subprocess.run(
                data["command_argv"]["rollback"],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(rollback.returncode, 0, rollback.stderr)
            restored_marker = json.loads(
                (target / ".experience-loop-install.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                restored_marker["host_contract"]["discovery_roots"], roots
            )
            self.assertEqual(
                restored_marker["host_contract"]["host_evidence"],
                "The installation AI verified the current discovery roots.",
            )

    def test_uninstaller_reuses_persisted_dynamic_discovery_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-uninstall-contract-") as raw:
            root = Path(raw)
            primary_root = root / "primary-skills"
            secondary_root = root / "secondary-skills"
            target = primary_root / "experience-loop"
            duplicate = secondary_root / "experience-loop"
            installed = run_script(
                "install.py",
                "--host",
                "Current Agent",
                "--target",
                str(target),
                "--discovery-root",
                str(secondary_root),
                "--affected-host",
                "Current Agent",
                "--affected-host",
                "Second Surface",
                "--host-evidence",
                "The installation AI verified both live discovery roots.",
                "--json",
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)
            marker = json.loads(
                (target / ".experience-loop-install.json").read_text(encoding="utf-8")
            )
            self.assertEqual(marker["host_contract"]["host"], "Current Agent")
            self.assertIn(
                str(secondary_root.resolve()),
                marker["host_contract"]["discovery_roots"],
            )

            merged = run_script(
                "install.py",
                "--target",
                str(target),
                "--host",
                "Renamed Agent",
                "--reload-hint",
                "Use the newly verified refresh flow.",
                "--dry-run",
                "--json",
            )
            self.assertEqual(merged.returncode, 0, merged.stderr)
            merged_data = json.loads(merged.stdout)
            self.assertEqual(merged_data["host"], "Renamed Agent")
            self.assertIn(
                str(secondary_root.resolve()), merged_data["discovery_roots"]
            )
            self.assertEqual(
                merged_data["affected_hosts"],
                ["Current Agent", "Second Surface", "Renamed Agent"],
            )
            self.assertEqual(
                merged_data["host_evidence"],
                "The installation AI verified both live discovery roots.",
            )

            shutil.copytree(target, duplicate)
            third_root = root / "third-skills"
            refused = run_python(
                target / "scripts" / "uninstall.py",
                "--discovery-root",
                str(third_root),
                "--yes",
                "--json",
            )
            self.assertEqual(refused.returncode, 3)
            refused_data = json.loads(refused.stdout)
            self.assertIn("Another discoverable", refused_data["error"])
            self.assertTrue(target.is_dir())
            self.assertTrue(duplicate.is_dir())

            shutil.rmtree(duplicate)
            removed = run_python(
                target / "scripts" / "uninstall.py", "--yes", "--json"
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse(target.exists())
            removed_data = json.loads(removed.stdout)
            self.assertTrue(removed_data["personal_data_preserved"])
            self.assertIn(
                removed_data["personal_data_location_basis"],
                {"EXPERIENCE_LOOP_HOME", "default-only"},
            )

    def test_informational_host_metadata_does_not_invalidate_runtime(self) -> None:
        installer = load_installer_module()
        with tempfile.TemporaryDirectory(prefix="experience-loop-host-info-") as raw:
            target = Path(raw) / "skills" / "experience-loop"
            installed = run_script("install.py", "--target", str(target), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            marker_path = target / ".experience-loop-install.json"
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            marker["host_contract"]["invocation"] = "bad\nmetadata"
            marker["host_contract"]["reload_hint"] = "x" * 1000
            marker_path.write_text(
                json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            self.assertIsNone(installer.managed_install_validation_error(target))
            preview = run_script(
                "install.py", "--target", str(target), "--dry-run", "--json"
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            preview_data = json.loads(preview.stdout)
            self.assertIsNone(preview_data["invocation"])
            self.assertEqual(
                preview_data["reload_hint"],
                "Resolve and use the current host's documented reload procedure.",
            )
            self.assertNotIn("x" * 20, preview_data["reload_hint"])


if __name__ == "__main__":
    unittest.main()
