from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_plugin  # noqa: E402
import install  # noqa: E402


class PluginPackageTests(unittest.TestCase):
    def output_path(self, parent: Path) -> Path:
        return parent / build_plugin.PLUGIN_NAME

    def test_payload_covers_the_installer_runtime_contract(self) -> None:
        payload = set(build_plugin.SKILL_PAYLOAD_FILES)
        self.assertEqual(len(payload), len(build_plugin.SKILL_PAYLOAD_FILES))
        self.assertEqual(
            build_plugin.SKILL_PAYLOAD_FILES,
            install.PORTABLE_SKILL_PAYLOAD_FILES,
        )
        self.assertEqual(set(install.CURRENT_SOURCE_REQUIRED_FILES) - payload, set())
        for source_only in (
            "AGENTS.md",
            "CONTRIBUTING.md",
            "docs/DEVELOPMENT_COMPASS.md",
            "scripts/build_plugin.py",
            "scripts/verify_release.py",
            "assets/readme-auto.zh.svg",
        ):
            self.assertNotIn(source_only, payload)

    def test_version_pattern_is_strict_semver(self) -> None:
        for version in ("0.1.0", "1.2.3-alpha.1+build.5", "10.20.30-rc.0"):
            with self.subTest(version=version):
                self.assertIsNotNone(build_plugin.SEMVER_PATTERN.fullmatch(version))
        for version in (
            "01.2.3",
            "1.02.3",
            "1.2.03",
            "1.2.3-01",
            "1.2.3-.alpha",
            "1.2.3-alpha..1",
            "1.2.3+build..1",
        ):
            with self.subTest(version=version):
                self.assertIsNone(build_plugin.SEMVER_PATTERN.fullmatch(version))

    def test_local_marketplace_build_uses_cachebuster_and_formal_host_handoff(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="experience-loop-local-marketplace-"
        ) as raw:
            marketplace_root = Path(raw) / "marketplace"
            marketplace_root.mkdir()
            (marketplace_root / "marketplace.json").write_text(
                json.dumps(
                    {
                        "name": "experience-loop-local",
                        "interface": {"displayName": "Existing Local"},
                        "plugins": [
                            {
                                "name": "keep-me",
                                "source": {
                                    "source": "local",
                                    "path": "./plugins/keep-me",
                                },
                                "policy": {
                                    "installation": "AVAILABLE",
                                    "authentication": "ON_INSTALL",
                                },
                                "category": "Productivity",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = build_plugin.build_marketplace(
                source_root=ROOT,
                packaging_root=ROOT / "packaging" / "openai",
                marketplace_root=marketplace_root,
                cachebuster="local-20260807-120000",
            )

            base_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
            expected_version = (
                base_version.split("+", 1)[0]
                + "+codex.local-20260807-120000"
            )
            self.assertEqual(result["status"], "marketplace-built")
            self.assertEqual(result["version"], expected_version)
            self.assertEqual(
                result["cache_policy"],
                "never-copy-or-delete-host-plugin-cache-directly",
            )
            self.assertTrue(
                all(value == "unknown" for value in result["host_state"].values())
            )

            marketplace = json.loads(
                (marketplace_root / "marketplace.json").read_text(encoding="utf-8")
            )
            self.assertEqual(marketplace["name"], "experience-loop-local")
            self.assertEqual(
                marketplace["interface"]["displayName"], "Existing Local"
            )
            self.assertEqual(
                [entry["name"] for entry in marketplace["plugins"]],
                ["keep-me", "experience-loop"],
            )
            experience_entry = marketplace["plugins"][1]
            self.assertEqual(
                experience_entry["source"],
                {"source": "local", "path": "./plugins/experience-loop"},
            )
            self.assertEqual(
                experience_entry["policy"],
                {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            )

            plugin_root = marketplace_root / "plugins" / "experience-loop"
            manifest = json.loads(
                (plugin_root / ".codex-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["version"], expected_version)
            self.assertFalse(
                (plugin_root / build_plugin.OWNERSHIP_MARKER_NAME).exists()
            )
            self.assertTrue(
                build_plugin._ownership_marker_path(plugin_root).is_file()
            )

            actions = {action["kind"]: action for action in result["next_actions"]}
            self.assertEqual(
                actions["install-or-update-plugin"]["command_argv"],
                [
                    "codex",
                    "plugin",
                    "add",
                    "experience-loop@experience-loop-local",
                    "--json",
                ],
            )
            self.assertEqual(
                actions["verify-host-registration"]["command_argv"],
                ["codex", "plugin", "list", "--json"],
            )
            self.assertIn("start-fresh-task", actions)

    def test_local_marketplace_rejects_invalid_cachebuster_and_name(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="experience-loop-invalid-marketplace-"
        ) as raw:
            root = Path(raw)
            with self.assertRaisesRegex(
                build_plugin.PluginBuildError, "Cachebuster"
            ):
                build_plugin.build_marketplace(
                    source_root=ROOT,
                    packaging_root=ROOT / "packaging" / "openai",
                    marketplace_root=root / "bad-cachebuster",
                    cachebuster="bad token",
                )
            with self.assertRaisesRegex(
                build_plugin.PluginBuildError, "Marketplace name"
            ):
                build_plugin.build_marketplace(
                    source_root=ROOT,
                    packaging_root=ROOT / "packaging" / "openai",
                    marketplace_root=root / "bad-name",
                    marketplace_name="Bad Name",
                    cachebuster="local-test",
                )

    def test_default_hook_manifest_uses_the_session_start_contract(self) -> None:
        payload = json.loads(
            (ROOT / "packaging" / "openai" / "hooks" / "hooks.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(set(payload), {"description", "hooks"})
        session_start = payload["hooks"]["SessionStart"]
        self.assertEqual(len(session_start), 1)
        self.assertEqual(
            session_start[0]["matcher"], "^(startup|resume|clear|compact)$"
        )
        handlers = session_start[0]["hooks"]
        self.assertEqual(len(handlers), 1)
        handler = handlers[0]
        self.assertEqual(handler["type"], "command")
        self.assertEqual(handler["timeout"], 3)
        self.assertEqual(handler["additionalContextLimit"], 448)
        self.assertIn("${PLUGIN_ROOT}/hooks/session_start.py", handler["command"])
        self.assertIn("os.environ['PLUGIN_ROOT']", handler["commandWindows"])
        self.assertNotIn("${PLUGIN_ROOT}", handler["commandWindows"])

    def test_build_uses_the_explicit_payload_and_replaces_stale_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-plugin-build-") as raw:
            parent = Path(raw)
            output = self.output_path(parent)
            canonical_metadata_path = ROOT / "agents" / "openai.yaml"
            canonical_metadata_before = canonical_metadata_path.read_bytes()
            build_plugin.build_plugin(
                source_root=ROOT,
                packaging_root=ROOT / "packaging" / "openai",
                output=output,
            )
            (output / "stale.txt").write_text("old\n", encoding="utf-8")

            result = build_plugin.build_plugin(
                source_root=ROOT,
                packaging_root=ROOT / "packaging" / "openai",
                output=output,
            )

            self.assertEqual(result["status"], "built")
            self.assertEqual(
                result["version"],
                (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
            )
            self.assertFalse((output / "stale.txt").exists())
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    ".codex-plugin",
                    "hooks",
                    "skills",
                },
            )
            ownership = json.loads(
                build_plugin._ownership_marker_path(output).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(ownership["plugin_name"], build_plugin.PLUGIN_NAME)
            self.assertEqual(ownership["version"], result["version"])
            self.assertEqual(
                result["hook_files"], ["hooks.json", "session_start.py"]
            )
            self.assertTrue((output / "hooks" / "hooks.json").is_file())
            self.assertTrue((output / "hooks" / "session_start.py").is_file())

            skill_root = output / "skills" / build_plugin.PLUGIN_NAME
            actual_payload = {
                path.relative_to(skill_root).as_posix()
                for path in skill_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual_payload, set(build_plugin.SKILL_PAYLOAD_FILES))
            self.assertEqual(
                (skill_root / "SKILL.md").read_bytes(),
                (ROOT / "SKILL.md").read_bytes(),
            )
            self.assertEqual(canonical_metadata_path.read_bytes(), canonical_metadata_before)
            canonical_metadata = canonical_metadata_path.read_text(encoding="utf-8")
            plugin_metadata = (skill_root / "agents" / "openai.yaml").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                build_plugin.STANDALONE_SKILL_SELECTOR,
                canonical_metadata,
            )
            self.assertNotIn(
                build_plugin.OPENAI_PLUGIN_SKILL_SELECTOR,
                canonical_metadata,
            )
            self.assertIn(
                build_plugin.OPENAI_PLUGIN_SKILL_SELECTOR,
                plugin_metadata,
            )
            self.assertIn("allow_implicit_invocation: false", plugin_metadata)
            self.assertEqual(
                plugin_metadata.replace(
                    build_plugin.OPENAI_PLUGIN_SKILL_SELECTOR,
                    build_plugin.STANDALONE_SKILL_SELECTOR,
                ),
                canonical_metadata,
            )
            self.assertNotIn("README.md", actual_payload)
            self.assertNotIn("scripts/build_plugin.py", actual_payload)
            self.assertNotIn("scripts/verify_release.py", actual_payload)
            self.assertNotIn("assets/readme-auto.en.svg", actual_payload)
            self.assertFalse((output / build_plugin.OWNERSHIP_MARKER_NAME).exists())
            self.assertFalse(any("__pycache__" in path.parts for path in output.rglob("*")))
            self.assertFalse(any(path.suffix == ".pyc" for path in output.rglob("*")))

            manifest = json.loads(
                (output / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["name"], build_plugin.PLUGIN_NAME)
            self.assertEqual(manifest["version"], result["version"])
            self.assertEqual(manifest["skills"], "./skills/")
            self.assertTrue(
                all(
                    build_plugin.OPENAI_PLUGIN_SKILL_SELECTOR in prompt
                    for prompt in manifest["interface"]["defaultPrompt"]
                )
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(skill_root / "scripts" / "experience_loop.py"),
                    "--version",
                ],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(result["version"], completed.stdout)
            self.assertFalse(any("__pycache__" in path.parts for path in output.rglob("*")))

    def test_unowned_existing_output_is_preserved_without_force(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-plugin-unowned-") as raw:
            output = self.output_path(Path(raw))
            output.mkdir()
            user_file = output / "user-data.txt"
            user_file.write_text("preserve me\n", encoding="utf-8")

            with self.assertRaisesRegex(
                build_plugin.PluginBuildError, "Refusing to replace unowned"
            ):
                build_plugin.build_plugin(
                    source_root=ROOT,
                    packaging_root=ROOT / "packaging" / "openai",
                    output=output,
                )

            self.assertEqual(user_file.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse((output / ".codex-plugin").exists())

    def test_plugin_copy_defers_install_and_uninstall_to_the_host_manager(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-plugin-lifecycle-") as raw:
            root = Path(raw)
            output = self.output_path(root / "artifact")
            build_plugin.build_plugin(
                source_root=ROOT,
                packaging_root=ROOT / "packaging" / "openai",
                output=output,
            )
            skill_root = output / "skills" / build_plugin.PLUGIN_NAME
            installer = skill_root / "scripts" / "install.py"
            uninstaller = skill_root / "scripts" / "uninstall.py"
            before = {
                path.relative_to(output).as_posix(): path.read_bytes()
                for path in output.rglob("*")
                if path.is_file()
            }

            managed_target = root / "standalone" / "experience-loop"
            refused_install = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(installer),
                    "--target",
                    str(managed_target),
                    "--json",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(refused_install.returncode, 3, refused_install.stderr)
            install_receipt = json.loads(refused_install.stdout)
            self.assertEqual(install_receipt["status"], "host-manager-required")
            self.assertEqual(
                install_receipt["lifecycle_owner"], "codex-plugin-manager"
            )
            self.assertEqual(install_receipt["registration_status"], "unknown")
            self.assertFalse(managed_target.exists())

            verified = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(installer),
                    "--target",
                    str(skill_root),
                    "--verify-only",
                    "--json",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            verify_receipt = json.loads(verified.stdout)
            self.assertEqual(
                verify_receipt["lifecycle_owner"], "codex-plugin-manager"
            )
            self.assertEqual(
                verify_receipt["plugin_lifecycle"]["hook_trust_status"],
                "unknown",
            )
            self.assertEqual(
                verify_receipt["plugin_lifecycle"]["current_turn_activation_status"],
                "unknown",
            )

            refused_uninstall = subprocess.run(
                [sys.executable, "-B", str(uninstaller), "--yes", "--json"],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                refused_uninstall.returncode, 3, refused_uninstall.stderr
            )
            uninstall_receipt = json.loads(refused_uninstall.stdout)
            self.assertEqual(uninstall_receipt["status"], "host-manager-required")
            self.assertTrue(uninstall_receipt["personal_data_preserved"])
            after = {
                path.relative_to(output).as_posix(): path.read_bytes()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_force_replaces_unowned_output_only_after_successful_staging(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-plugin-force-") as raw:
            output = self.output_path(Path(raw))
            output.mkdir()
            user_file = output / "reviewed-old-output.txt"
            user_file.write_text("replace me\n", encoding="utf-8")

            result = build_plugin.build_plugin(
                source_root=ROOT,
                packaging_root=ROOT / "packaging" / "openai",
                output=output,
                force=True,
            )

            self.assertEqual(result["status"], "built")
            self.assertFalse(user_file.exists())
            self.assertTrue(build_plugin._ownership_marker_path(output).is_file())
            self.assertFalse((output / build_plugin.OWNERSHIP_MARKER_NAME).exists())

    @unittest.skipUnless(os.name == "nt", "commandWindows integration requires Windows")
    def test_command_windows_runs_the_built_hook_with_a_spaced_plugin_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience loop plugin windows ") as raw:
            root = Path(raw)
            output = self.output_path(root / "plugin bundle")
            build_plugin.build_plugin(
                source_root=ROOT,
                packaging_root=ROOT / "packaging" / "openai",
                output=output,
            )
            hook_manifest = json.loads(
                (output / "hooks" / "hooks.json").read_text(encoding="utf-8")
            )
            command = hook_manifest["hooks"]["SessionStart"][0]["hooks"][0][
                "commandWindows"
            ]

            home = root / "controls home"
            home.mkdir()
            (home / "controls.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "default_mode": "auto",
                        "activation_scope": "global",
                        "privacy": "normal",
                        "profile_customized": False,
                        "revision": 1,
                        "created_at": "2026-08-07T00:00:00Z",
                        "updated_at": "2026-08-07T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            cwd = root / "working directory"
            cwd.mkdir()
            environment = os.environ.copy()
            environment["PLUGIN_ROOT"] = str(output)
            environment["EXPERIENCE_LOOP_HOME"] = str(home)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            event = json.dumps(
                {
                    "hook_event_name": "SessionStart",
                    "source": "startup",
                    "session_id": "plugin-package-windows-command-test",
                    "cwd": str(cwd),
                }
            )

            shells = []
            command_prompt = os.environ.get("COMSPEC") or shutil.which("cmd")
            if command_prompt:
                shells.append(("cmd", command, True, command_prompt))
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell:
                shells.append(
                    (
                        "powershell",
                        [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                        False,
                        None,
                    )
                )
            self.assertTrue(shells, "No Windows command shell is available for validation.")

            for label, argv, use_shell, executable in shells:
                with self.subTest(shell=label):
                    completed = subprocess.run(
                        argv,
                        input=event,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        capture_output=True,
                        check=False,
                        cwd=cwd,
                        env=environment,
                        shell=use_shell,
                        executable=executable,
                    )
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    output_payload = json.loads(completed.stdout)
                    self.assertEqual(
                        output_payload["hookSpecificOutput"]["hookEventName"],
                        "SessionStart",
                    )
            self.assertFalse(any("__pycache__" in path.parts for path in output.rglob("*")))
            self.assertFalse(any(path.suffix == ".pyc" for path in output.rglob("*")))

    def test_declared_hooks_copy_without_packaging_metadata_or_cache_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-plugin-hooks-") as raw:
            root = Path(raw)
            packaging_root = root / "packaging"
            hooks_root = packaging_root / "hooks"
            hooks_root.mkdir(parents=True)
            shutil.copy2(ROOT / "packaging" / "openai" / "plugin.json", packaging_root)
            (hooks_root / "session-start.json").write_text("{}\n", encoding="utf-8")
            (hooks_root / "helpers").mkdir()
            (hooks_root / "helpers" / "route.py").write_text(
                "print('route')\n", encoding="utf-8"
            )
            (hooks_root / "unlisted.env").write_text("SECRET=no\n", encoding="utf-8")
            cache = hooks_root / "__pycache__"
            cache.mkdir()
            (cache / "route.pyc").write_bytes(b"cache")
            (hooks_root / "files.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "files": ["session-start.json", "helpers/route.py"],
                    }
                ),
                encoding="utf-8",
            )
            output = self.output_path(root / "artifact")

            result = build_plugin.build_plugin(
                source_root=ROOT,
                packaging_root=packaging_root,
                output=output,
            )

            self.assertEqual(
                result["hook_files"], ["session-start.json", "helpers/route.py"]
            )
            self.assertTrue((output / "hooks" / "session-start.json").is_file())
            self.assertTrue((output / "hooks" / "helpers" / "route.py").is_file())
            self.assertFalse((output / "hooks" / "files.json").exists())
            self.assertFalse((output / "hooks" / "unlisted.env").exists())
            self.assertFalse((output / "hooks" / "__pycache__").exists())

    def test_hook_manifest_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-plugin-hook-path-") as raw:
            root = Path(raw)
            packaging_root = root / "packaging"
            hooks_root = packaging_root / "hooks"
            hooks_root.mkdir(parents=True)
            shutil.copy2(ROOT / "packaging" / "openai" / "plugin.json", packaging_root)
            (packaging_root / "secret.json").write_text("{}\n", encoding="utf-8")
            (hooks_root / "files.json").write_text(
                json.dumps({"schema_version": 1, "files": ["../secret.json"]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(build_plugin.PluginBuildError, "stay inside"):
                build_plugin.build_plugin(
                    source_root=ROOT,
                    packaging_root=packaging_root,
                    output=self.output_path(root / "artifact"),
                )

    def test_failed_validator_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-plugin-validator-") as raw:
            root = Path(raw)
            output = self.output_path(root / "artifact")
            output.mkdir(parents=True)
            marker = output / "previous.txt"
            marker.write_text("preserve me\n", encoding="utf-8")
            validator = root / "reject_plugin.py"
            validator.write_text(
                "import sys\nprint('intentional rejection')\nraise SystemExit(9)\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                build_plugin.PluginBuildError, "intentional rejection"
            ):
                build_plugin.build_plugin(
                    source_root=ROOT,
                    packaging_root=ROOT / "packaging" / "openai",
                    output=output,
                    validator=validator,
                    force=True,
                )

            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse((output / ".codex-plugin").exists())
            leftovers = [
                path.name
                for path in output.parent.iterdir()
                if path.name.startswith(f".{build_plugin.PLUGIN_NAME}.build-")
                or path.name.startswith(f".{build_plugin.PLUGIN_NAME}.backup-")
            ]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
