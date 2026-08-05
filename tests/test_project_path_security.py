from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from helpers import assert_ok, payload, run_cli
from experience_loop_lib.common import ExperienceLoopError
from experience_loop_lib.project import annotate_project, get_project, remove_project
from experience_loop_lib.storage import Store


def _language_evidence(scan: dict, language: str) -> list[str]:
    for item in scan["scan"]["languages"]:
        if item["name"] == language:
            return item["evidence"]
    return []


def _write_git_config(project: Path, remote: str) -> None:
    git = project / ".git"
    git.mkdir(parents=True)
    (git / "config").write_text(
        '[core]\n\trepositoryformatversion = 0\n'
        '[remote "origin"]\n\turl = {0}\n'.format(remote),
        encoding="utf-8",
    )


class ProjectPathSecurityTests(unittest.TestCase):
    def test_root_and_nested_gitignore_apply_in_metadata_only_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-ignore-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            nested = project / "nested"
            deeper = nested / "deeper"
            blocked = project / "blocked"
            deeper.mkdir(parents=True)
            blocked.mkdir()
            (project / ".gitignore").write_text(
                "root-hidden.py\n*.rs\nblocked/\n!blocked/escape.ts\n",
                encoding="utf-8",
            )
            (nested / ".gitignore").write_text(
                "!keep.rs\n/anchored.go\n*.secret.cs\n",
                encoding="utf-8",
            )
            (project / "root-hidden.py").write_text("hidden", encoding="utf-8")
            (nested / "hidden.rs").write_text("hidden", encoding="utf-8")
            (nested / "keep.rs").write_text("visible", encoding="utf-8")
            (nested / "anchored.go").write_text("hidden", encoding="utf-8")
            (deeper / "anchored.go").write_text("visible", encoding="utf-8")
            (nested / "value.secret.cs").write_text("hidden", encoding="utf-8")
            (nested / "value.cs").write_text("visible", encoding="utf-8")
            (blocked / "escape.ts").write_text("hidden", encoding="utf-8")

            assert_ok(self, run_cli(home, "setup", "--privacy", "metadata-only"))
            scan = assert_ok(self, run_cli(home, "project", "scan", str(project)))

            self.assertFalse(scan["scan"]["content_read"])
            self.assertEqual(scan["scan"]["stats"]["files_analyzed"], 0)
            self.assertEqual(scan["scan"]["stats"]["bytes_read"], 0)
            self.assertEqual(_language_evidence(scan, "Python"), [])
            self.assertEqual(_language_evidence(scan, "TypeScript"), [])
            self.assertEqual(_language_evidence(scan, "Rust"), ["nested/keep.rs"])
            self.assertEqual(_language_evidence(scan, "Go"), ["nested/deeper/anchored.go"])
            self.assertEqual(_language_evidence(scan, "C#"), ["nested/value.cs"])
            self.assertGreaterEqual(scan["scan"]["stats"]["skipped"].get("gitignored", 0), 4)

    def test_priority_unity_manifest_survives_breadth_limit_but_not_gitignore(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-unity-priority-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            (project / "ProjectSettings").mkdir(parents=True)
            (project / "Packages").mkdir()
            assets = project / "Assets"
            assets.mkdir()
            (project / "ProjectSettings" / "ProjectVersion.txt").write_text(
                "m_EditorVersion: 2022.3.1f1\n", encoding="utf-8"
            )
            (project / "Packages" / "manifest.json").write_text("{}\n", encoding="utf-8")
            for index in range(100):
                (assets / ("file-{0:03d}.cs".format(index))).write_text("class C {}", encoding="utf-8")

            assert_ok(self, run_cli(home, "setup"))
            scan = assert_ok(
                self,
                run_cli(home, "project", "scan", str(project), "--max-files", "1"),
            )
            self.assertIn("Unity/Tuanjie", [item["name"] for item in scan["scan"]["frameworks"]])
            self.assertTrue(scan["scan"]["stats"]["truncated"])

            (project / ".gitignore").write_text(
                "ProjectSettings/ProjectVersion.txt\nPackages/manifest.json\n",
                encoding="utf-8",
            )
            ignored = assert_ok(
                self,
                run_cli(home, "project", "scan", str(project), "--max-files", "1"),
            )
            self.assertNotIn("Unity/Tuanjie", [item["name"] for item in ignored["scan"]["frameworks"]])

    def test_symlink_escape_is_never_scanned_and_symlink_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-symlink-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            outside = root / "outside"
            project.mkdir()
            outside.mkdir()
            (outside / "escape.py").write_text("print('outside')", encoding="utf-8")
            link = project / "linked"
            try:
                os.symlink(str(outside), str(link), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlink creation is unavailable: {0}".format(exc))

            assert_ok(self, run_cli(home, "setup"))
            scan = assert_ok(self, run_cli(home, "project", "scan", str(project)))
            self.assertEqual(_language_evidence(scan, "Python"), [])
            self.assertGreaterEqual(scan["scan"]["stats"]["skipped"].get("reparse_point", 0), 1)

            rejected = run_cli(home, "project", "scan", str(link))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(payload(rejected)["ok"])

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_windows_directory_junction_escape_is_never_scanned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-junction-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            outside = root / "outside"
            project.mkdir()
            outside.mkdir()
            (outside / "escape.py").write_text("print('outside')", encoding="utf-8")
            junction = project / "junction"
            created = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                text=True,
                capture_output=True,
                check=False,
            )
            if created.returncode != 0:
                self.skipTest("junction creation is unavailable: {0}".format(created.stderr))
            try:
                assert_ok(self, run_cli(home, "setup"))
                scan = assert_ok(self, run_cli(home, "project", "scan", str(project)))
                self.assertEqual(_language_evidence(scan, "Python"), [])
                self.assertGreaterEqual(scan["scan"]["stats"]["skipped"].get("reparse_point", 0), 1)
            finally:
                if junction.exists():
                    os.rmdir(str(junction))

    def test_git_remote_hash_reuses_clone_without_storing_remote(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-identity-remote-") as raw:
            root = Path(raw)
            home = root / "home"
            first = root / "first-clone"
            second = root / "renamed-clone"
            first.mkdir()
            second.mkdir()
            _write_git_config(first, "https://secret-token@github.com/Example/Experience.git")
            _write_git_config(second, "git@github.com:example/experience.git")

            assert_ok(self, run_cli(home, "setup"))
            original = assert_ok(self, run_cli(home, "project", "scan", str(first)))
            relocated = assert_ok(self, run_cli(home, "project", "scan", str(second)))

            self.assertEqual(original["id"], relocated["id"])
            self.assertEqual(relocated["identity_resolution"]["status"], "matched-portable-identity")
            self.assertEqual(relocated["identity"]["kind"], "git-remote")
            serialized = json.dumps(relocated, ensure_ascii=False).lower()
            self.assertNotIn("github.com", serialized)
            self.assertNotIn("secret-token", serialized)

    def test_manifest_fingerprint_is_portable_but_distinct_remotes_win(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-identity-manifest-") as raw:
            root = Path(raw)
            home = root / "home"
            first = root / "one"
            second = root / "two"
            fork = root / "fork"
            for project in (first, second, fork):
                project.mkdir()
                (project / "package.json").write_text(
                    '{"name":"portable-app","scripts":{"test":"node test.js"}}\n',
                    encoding="utf-8",
                )
            _write_git_config(fork, "https://gitlab.com/other/fork.git")

            assert_ok(self, run_cli(home, "setup"))
            original = assert_ok(self, run_cli(home, "project", "scan", str(first)))
            relocated = assert_ok(self, run_cli(home, "project", "scan", str(second)))
            distinct_fork = assert_ok(self, run_cli(home, "project", "scan", str(fork)))

            self.assertEqual(original["identity"]["kind"], "manifest-fingerprint")
            self.assertEqual(original["id"], relocated["id"])
            self.assertNotEqual(original["id"], distinct_fork["id"])

    def test_same_basename_and_legacy_placeholder_require_safe_resolution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-identity-name-") as raw:
            root = Path(raw)
            home = root / "home"
            first = root / "a" / "shared"
            second = root / "b" / "shared"
            third = root / "c" / "placeholder-project"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            third.mkdir(parents=True)

            assert_ok(self, run_cli(home, "setup"))
            first_scan = assert_ok(self, run_cli(home, "project", "scan", str(first)))
            second_scan = assert_ok(self, run_cli(home, "project", "scan", str(second)))
            self.assertNotEqual(first_scan["id"], second_scan["id"])

            index_path = home / "projects" / "index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["projects"]["prj_legacy_placeholder"] = {
                "id": "prj_legacy_placeholder",
                "name": "placeholder-project",
                "path": None,
            }
            index_path.write_text(json.dumps(index), encoding="utf-8")

            scanned = assert_ok(self, run_cli(home, "project", "scan", str(third)))
            self.assertNotEqual(scanned["id"], "prj_legacy_placeholder")
            resolution = scanned["identity_resolution"]
            self.assertTrue(resolution["needs_confirmation"])
            self.assertEqual(resolution["candidates"][0]["id"], "prj_legacy_placeholder")
            persisted = json.loads((home / "projects" / (scanned["id"] + ".json")).read_text(encoding="utf-8"))
            self.assertTrue(persisted["identity_resolution"]["needs_confirmation"])

    def test_restricted_scan_requires_explicit_content_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-restricted-project-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            (project / "README.md").write_text(
                "# Verify\n\n```text\npython -m unittest discover -s tests\n```\n",
                encoding="utf-8",
            )
            assert_ok(self, run_cli(home, "setup", "--privacy", "restricted"))

            denied = assert_ok(self, run_cli(home, "project", "scan", str(project)))
            self.assertFalse(denied["scan"]["content_read"])
            self.assertFalse(denied["scan"]["content_access_confirmed"])
            self.assertEqual(denied["scan"]["suggested_commands"], [])
            self.assertEqual(denied["scan"]["stats"]["bytes_read"], 0)

            allowed = assert_ok(
                self,
                run_cli(home, "project", "scan", str(project), "--confirm-content-access"),
            )
            self.assertTrue(allowed["scan"]["content_read"])
            self.assertTrue(allowed["scan"]["content_access_confirmed"])
            self.assertEqual(
                [item["command"] for item in allowed["scan"]["suggested_commands"]],
                ["python -m unittest discover -s tests"],
            )

    def test_annotations_persist_as_untrusted_context_and_remove_keeps_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-project-lifecycle-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            (project / "package.json").write_text('{"name":"lifecycle"}\n', encoding="utf-8")
            assert_ok(self, run_cli(home, "setup"))
            scanned = assert_ok(self, run_cli(home, "project", "scan", str(project)))
            project_id = scanned["id"]
            store = Store(str(home))

            annotated = annotate_project(
                store,
                project_id,
                architecture_notes=["推测：API 层不能直接依赖存储实现。"],
                learning_opportunities=["练习依赖方向审查。"],
            )
            annotations = annotated["annotations"]
            self.assertEqual(annotations["authority"], "non-authoritative-user-context")
            self.assertTrue(annotations["untrusted_content"])
            self.assertTrue(annotations["requires_verification"])

            annotate_project(
                store,
                project_id,
                architecture_notes=["推测：API 层不能直接依赖存储实现。"],
                verification_notes=["待用依赖测试核验。"],
            )
            rescanned = assert_ok(self, run_cli(home, "project", "scan", str(project)))
            self.assertEqual(
                rescanned["annotations"]["architecture_notes"],
                ["推测：API 层不能直接依赖存储实现。"],
            )
            self.assertEqual(rescanned["annotations"]["verification_notes"], ["待用依赖测试核验。"])

            cleared = annotate_project(store, project_id, architecture_notes=[], replace=True)
            self.assertEqual(cleared["annotations"]["architecture_notes"], [])
            self.assertEqual(cleared["annotations"]["learning_opportunities"], ["练习依赖方向审查。"])

            assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "decision",
                    "--summary",
                    "保留历史记录",
                    "--project",
                    project_id,
                    "--evidence",
                    "test:lifecycle",
                ),
            )
            removed = remove_project(store, project_id)
            self.assertTrue(removed["removed"])
            self.assertTrue(removed["retained_history"])
            self.assertTrue(removed["retained_knowledge"])
            self.assertFalse((home / "projects" / (project_id + ".json")).exists())
            index = json.loads((home / "projects" / "index.json").read_text(encoding="utf-8"))
            self.assertNotIn(project_id, index["projects"])
            self.assertIn(project_id, (home / "ledger" / "events.jsonl").read_text(encoding="utf-8"))

            with self.assertRaises(ExperienceLoopError):
                get_project(store, "../profile")
            self.assertTrue((home / "profile.json").is_file())


if __name__ == "__main__":
    unittest.main()
