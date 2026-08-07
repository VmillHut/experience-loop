from __future__ import annotations

import hashlib
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

from experience_loop_lib.identity import (  # noqa: E402
    FINGERPRINT_ALGORITHM,
    RUNTIME_IDENTITY_FILES,
    RUNTIME_MANIFEST_SCHEMA,
    installed_identity,
    runtime_contract_manifest,
)


class IdentityTests(unittest.TestCase):
    def test_fingerprint_is_canonical_and_bound_to_the_exact_copy(self) -> None:
        identity = installed_identity(ROOT)
        manifest = runtime_contract_manifest(ROOT)
        canonical = json.dumps(
            {
                "name": "experience-loop",
                "root": os.path.normcase(str(ROOT.resolve())),
                "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
                "runtime_manifest_schema": RUNTIME_MANIFEST_SCHEMA,
                "runtime_manifest_digest": manifest["digest"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            identity["fingerprint"],
            "sha256:" + hashlib.sha256(canonical).hexdigest(),
        )
        self.assertEqual(identity["fingerprint_algorithm"], FINGERPRINT_ALGORITHM)
        self.assertEqual(
            identity["runtime_contract_manifest"],
            {
                "schema": RUNTIME_MANIFEST_SCHEMA,
                "digest_algorithm": "sha256",
                "digest": manifest["digest"],
                "file_count": len(RUNTIME_IDENTITY_FILES),
            },
        )

    def test_runtime_manifest_covers_core_contract_and_excludes_plugin_adapters(self) -> None:
        required = {
            "SKILL.md",
            "references/onboarding.md",
            "references/safety-and-privacy.md",
            "scripts/experience_loop.py",
            "scripts/global_router.py",
            "scripts/experience_loop_lib/controls.py",
            "scripts/experience_loop_lib/identity.py",
            "scripts/experience_loop_lib/project.py",
            "scripts/install.py",
            "scripts/uninstall.py",
            "vendor/manifest.json",
        }
        self.assertEqual(required - set(RUNTIME_IDENTITY_FILES), set())
        self.assertFalse(
            any(
                path.startswith((".codex-plugin/", "hooks/", "packaging/"))
                for path in RUNTIME_IDENTITY_FILES
            )
        )

    def test_manifest_detects_reference_and_runtime_module_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-identity-manifest-") as raw:
            copied = Path(raw) / "experience-loop"
            for relative in RUNTIME_IDENTITY_FILES:
                source = ROOT.joinpath(*relative.split("/"))
                target = copied.joinpath(*relative.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            baseline = installed_identity(copied)
            workflow = copied / "references" / "workflow.md"
            workflow.write_text(
                workflow.read_text(encoding="utf-8") + "\nmanifest probe\n",
                encoding="utf-8",
            )
            changed_reference = installed_identity(copied)
            self.assertNotEqual(
                changed_reference["runtime_manifest_digest"],
                baseline["runtime_manifest_digest"],
            )
            self.assertNotEqual(changed_reference["fingerprint"], baseline["fingerprint"])

            project_module = copied / "scripts" / "experience_loop_lib" / "project.py"
            project_module.write_text(
                project_module.read_text(encoding="utf-8") + "\n# manifest probe\n",
                encoding="utf-8",
            )
            changed_module = installed_identity(copied)
            self.assertNotEqual(
                changed_module["runtime_manifest_digest"],
                changed_reference["runtime_manifest_digest"],
            )

    def test_cli_probe_is_read_only_and_blocks_a_mismatched_handoff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-identity-") as raw:
            home = Path(raw) / "data"
            expected = installed_identity(ROOT)["fingerprint"]

            verified = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts" / "experience_loop.py"),
                    "--home",
                    str(home),
                    "--json",
                    "identity",
                    "--expected-fingerprint",
                    expected,
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            data = json.loads(verified.stdout)["data"]
            self.assertEqual(data["status"], "matched")
            self.assertTrue(data["match"])
            self.assertEqual(data["comparison"]["status"], "matched")
            self.assertEqual(data["host_activation"]["status"], "not_evaluated")
            self.assertNotIn("onboarding_identity_gate", data)
            self.assertFalse(data["runtime"]["initialized"])
            self.assertFalse(home.exists())

            mismatch = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts" / "experience_loop.py"),
                    "--home",
                    str(home),
                    "--json",
                    "identity",
                    "--expected-fingerprint",
                    "sha256:" + "0" * 64,
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(mismatch.returncode, 0, mismatch.stderr)
            envelope = json.loads(mismatch.stdout)
            self.assertFalse(envelope["ok"])
            data = envelope["data"]
            self.assertFalse(data["ok"])
            self.assertEqual(data["status"], "mismatch")
            self.assertFalse(data["match"])
            self.assertEqual(data["comparison"]["status"], "mismatch")
            self.assertEqual(data["host_activation"]["status"], "not_evaluated")
            self.assertFalse(home.exists())

    def test_identity_proof_remains_available_when_controls_are_corrupt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-identity-corrupt-") as raw:
            home = Path(raw) / "data"
            environment = os.environ.copy()
            environment["EXPERIENCE_LOOP_DEVELOPER_SOURCE"] = "1"
            setup = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts" / "experience_loop.py"),
                    "--home",
                    str(home),
                    "--json",
                    "setup",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
                env=environment,
            )
            self.assertEqual(setup.returncode, 0, setup.stderr)
            (home / "controls.json").write_text("{broken", encoding="utf-8")

            probe = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts" / "experience_loop.py"),
                    "--home",
                    str(home),
                    "--json",
                    "identity",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            data = json.loads(probe.stdout)["data"]
            self.assertEqual(data["status"], "observed")
            self.assertIsNone(data["match"])
            self.assertEqual(data["comparison"]["status"], "not-requested")
            self.assertEqual(data["host_activation"]["status"], "not_evaluated")
            self.assertNotIn("onboarding_identity_gate", data)
            self.assertEqual(data["runtime"]["controls_status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
