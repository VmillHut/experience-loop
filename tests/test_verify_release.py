from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import verify_release  # noqa: E402


def write_version_files(
    root: Path,
    file_version: str,
    runtime_version: str,
    changelog_version: str,
) -> None:
    (root / "scripts" / "experience_loop_lib").mkdir(parents=True)
    (root / "VERSION").write_text(file_version + "\n", encoding="utf-8")
    (root / "scripts" / "experience_loop_lib" / "common.py").write_text(
        'VERSION = "{0}"\n'.format(runtime_version), encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [{0}] - 2026-08-05\n".format(changelog_version),
        encoding="utf-8",
    )


class VerifyReleaseTests(unittest.TestCase):
    def test_current_release_metadata_is_consistent(self) -> None:
        self.assertEqual(verify_release.check_skill(ROOT), [])
        self.assertEqual(verify_release.check_openai_metadata(ROOT), [])
        self.assertEqual(verify_release.check_version_consistency(ROOT), [])
        self.assertEqual(verify_release.check_tag_consistency("v0.1.0", ROOT), [])
        self.assertEqual(verify_release.check_publish_placeholders(ROOT), [])
        self.assertEqual(verify_release.check_vendor(ROOT), [])

    def test_skill_and_tag_checks_reject_invalid_release_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-release-skill-") as raw:
            root = Path(raw)
            (root / "agents").mkdir(parents=True)
            (root / "assets").mkdir()
            (root / "SKILL.md").write_text(
                "---\nname: Experience_Loop\ndescription:\nextra: value\n---\n",
                encoding="utf-8",
            )
            (root / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Experience Loop"\n', encoding="utf-8"
            )
            (root / "VERSION").write_text("0.1.0\n", encoding="utf-8")
            skill_errors = "\n".join(verify_release.check_skill(root))
            metadata_errors = "\n".join(verify_release.check_openai_metadata(root))
            tag_errors = "\n".join(
                verify_release.check_tag_consistency("refs/tags/v0.1.1", root)
            )
            self.assertIn("unsupported field", skill_errors)
            self.assertIn("name must be experience-loop", skill_errors)
            self.assertIn("non-empty description", skill_errors)
            self.assertIn("non-empty instruction body", skill_errors)
            self.assertIn("short_description must be non-empty", metadata_errors)
            self.assertIn("icon_small must be a non-empty relative path", metadata_errors)
            self.assertIn("Release tag mismatch", tag_errors)

    def test_metadata_checks_reject_malformed_yaml_and_comment_decoys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-release-yaml-") as raw:
            root = Path(raw)
            (root / "agents").mkdir(parents=True)
            (root / "assets").mkdir()
            (root / "assets" / "icon-small.svg").write_text("<svg/>\n", encoding="utf-8")
            (root / "assets" / "icon-large.svg").write_text("<svg/>\n", encoding="utf-8")
            (root / "SKILL.md").write_text(
                '---\nname: experience-loop\ndescription: "unterminated\n---\nBody\n',
                encoding="utf-8",
            )
            skill_errors = "\n".join(verify_release.check_skill(root))
            self.assertIn("invalid double-quoted scalar", skill_errors)

            (root / "agents" / "openai.yaml").write_text(
                "interface: [\n# $experience-loop\n",
                encoding="utf-8",
            )
            malformed_errors = "\n".join(verify_release.check_openai_metadata(root))
            self.assertIn("unsupported YAML scalar syntax", malformed_errors)

            (root / "agents" / "openai.yaml").write_text(
                "interface:\n"
                '  display_name: "Experience Loop"\n'
                '  short_description: ""\n'
                '  icon_small: "./assets/icon-small.svg"\n'
                '  icon_large: "./assets/icon-large.svg"\n'
                '  default_prompt: ""\n'
                "# $experience-loop\n"
                "policy:\n"
                "  allow_implicit_invocation: false\n",
                encoding="utf-8",
            )
            decoy_errors = "\n".join(verify_release.check_openai_metadata(root))
            self.assertIn("short_description must be non-empty", decoy_errors)
            self.assertIn("default_prompt must be non-empty", decoy_errors)
            self.assertIn("allow_implicit_invocation must be true", decoy_errors)

    def test_version_check_rejects_runtime_and_changelog_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-release-version-") as raw:
            root = Path(raw)
            write_version_files(root, "0.1.0", "0.1.1", "0.1.2")
            errors = verify_release.check_version_consistency(root)
            rendered = "\n".join(errors)
            self.assertIn("runtime VERSION='0.1.1'", rendered)
            self.assertIn("CHANGELOG='0.1.2'", rendered)

    def test_placeholder_check_rejects_unpublished_github_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-release-placeholder-") as raw:
            root = Path(raw)
            (root / "README.md").write_text(
                "git clone https://github.com/<owner>/experience-loop.git\n",
                encoding="utf-8",
            )
            (root / "README.en.md").write_text(
                "git clone https://github.com/your-org/experience-loop.git\n",
                encoding="utf-8",
            )
            errors = verify_release.check_publish_placeholders(root)
            self.assertTrue(errors)
            rendered = "\n".join(errors)
            self.assertIn("<owner>", rendered)
            self.assertIn("your-org", rendered)

    def test_artifact_check_rejects_bytecode_and_personal_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-release-artifact-") as raw:
            root = Path(raw)
            cache = root / "scripts" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "runtime.cpython-312.pyc").write_bytes(b"not-bytecode")
            personal = root / ".experience-loop"
            personal.mkdir()
            (personal / "profile.json").write_text("{}\n", encoding="utf-8")
            (root / "profile.json").write_text("{}\n", encoding="utf-8")
            errors = verify_release.check_release_artifacts(root)
            rendered = "\n".join(errors)
            self.assertIn("__pycache__", rendered)
            self.assertIn(".experience-loop", rendered)
            self.assertIn("profile.json", rendered)

    def test_vendor_check_rejects_unmanifested_wheel_and_missing_license(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-release-vendor-") as raw:
            root = Path(raw)
            wheels = root / "vendor" / "wheels"
            wheels.mkdir(parents=True)
            (root / "licenses").mkdir()
            declared = wheels / "declared-1.0-py3-none-any.whl"
            declared.write_bytes(b"declared")
            (wheels / "orphan-1.0-py3-none-any.whl").write_bytes(b"orphan")
            manifest = {
                "schema_version": 1,
                "packages": [
                    {
                        "name": "declared",
                        "version": "1.0",
                        "file": "wheels/declared-1.0-py3-none-any.whl",
                        "sha256": hashlib.sha256(declared.read_bytes()).hexdigest(),
                        "license": "MIT",
                        "license_file": "../licenses/declared-LICENSE",
                    }
                ],
            }
            (root / "vendor" / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            errors = verify_release.check_vendor(root)
            rendered = "\n".join(errors)
            self.assertIn("Missing vendor license file", rendered)
            self.assertIn("Unmanifested vendored wheel", rendered)


if __name__ == "__main__":
    unittest.main()
