from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from helpers import assert_ok, run_cli


class ProjectScanEfficiencyTests(unittest.TestCase):
    def test_backup_tree_cannot_consume_the_live_source_scan_budget(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-scan-backup-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "unity-project"
            live = project / "Assets" / "Live"
            backup = project / "_Backup_SDK"
            live.mkdir(parents=True)
            backup.mkdir(parents=True)
            (live / "CurrentFeature.cs").write_text(
                "public sealed class CurrentFeature {}\n", encoding="utf-8"
            )
            for index in range(20):
                (backup / ("Legacy%02d.cs" % index)).write_text(
                    "public sealed class Legacy%02d {}\n" % index,
                    encoding="utf-8",
                )
            assert_ok(self, run_cli(home, "setup"))

            scanned = assert_ok(
                self,
                run_cli(
                    home,
                    "project",
                    "scan",
                    str(project),
                    "--max-files",
                    "3",
                ),
            )["scan"]

            csharp = next(item for item in scanned["languages"] if item["name"] == "C#")
            self.assertEqual(csharp["files"], 1)
            self.assertEqual(csharp["evidence"], ["Assets/Live/CurrentFeature.cs"])
            self.assertGreaterEqual(scanned["stats"]["skipped"]["excluded_directory"], 1)

    def test_conventional_source_directory_precedes_large_vendor_like_tree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-scan-priority-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "unity-project"
            live = project / "Assets" / "Code"
            vendor_like = project / "Assets" / "AmplifyHuge"
            project_version = project / "ProjectSettings" / "ProjectVersion.txt"
            live.mkdir(parents=True)
            vendor_like.mkdir(parents=True)
            project_version.parent.mkdir(parents=True)
            project_version.write_text("m_EditorVersion: 2022.3\n", encoding="utf-8")
            (live / "CurrentFeature.cs").write_text(
                "public sealed class CurrentFeature {}\n", encoding="utf-8"
            )
            for index in range(20):
                (vendor_like / ("Legacy%02d.cs" % index)).write_text(
                    "public sealed class Legacy%02d {}\n" % index,
                    encoding="utf-8",
                )
            assert_ok(self, run_cli(home, "setup"))

            scanned = assert_ok(
                self,
                run_cli(
                    home,
                    "project",
                    "scan",
                    str(project),
                    "--max-files",
                    "4",
                ),
            )["scan"]

            csharp = next(item for item in scanned["languages"] if item["name"] == "C#")
            self.assertEqual(csharp["evidence"][0], "Assets/Code/CurrentFeature.cs")
            self.assertTrue(scanned["stats"]["truncated"])

    def test_source_files_are_classified_without_reading_their_bodies(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-scan-efficiency-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "large-project"
            source = project / "src"
            source.mkdir(parents=True)
            for index in range(200):
                (source / ("module_%03d.py" % index)).write_text(
                    "# body that a project inventory does not need\n" + "x = 1\n" * 200,
                    encoding="utf-8",
                )
            (project / "AGENTS.md").write_text(
                "先运行 `tools/unicli.cmd status` 确认编辑器状态。\n",
                encoding="utf-8",
            )
            assert_ok(self, run_cli(home, "setup"))

            scanned = assert_ok(
                self, run_cli(home, "project", "scan", str(project))
            )["scan"]
            languages = {item["name"]: item for item in scanned["languages"]}
            self.assertEqual(languages["Python"]["files"], 200)
            self.assertGreaterEqual(scanned["stats"]["files_classified"], 201)
            self.assertLessEqual(scanned["stats"]["files_analyzed"], 2)
            self.assertLess(scanned["stats"]["bytes_read"], 4096)
            self.assertIn(
                "tools/unicli.cmd status",
                [item["command"] for item in scanned["suggested_commands"]],
            )

    def test_metadata_only_does_not_read_git_remote_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-metadata-only-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            (project / ".git").mkdir(parents=True)
            (project / ".git" / "config").write_text(
                '[remote "origin"]\nurl = https://token@example.invalid/private.git\n',
                encoding="utf-8",
            )
            (project / ".gitignore").write_text("private.py\n", encoding="utf-8")
            (project / "private.py").write_text("SECRET = 'never read'\n", encoding="utf-8")
            assert_ok(self, run_cli(home, "setup", "--privacy", "metadata-only"))

            scanned = assert_ok(
                self, run_cli(home, "project", "scan", str(project))
            )
            self.assertFalse(scanned["scan"]["content_read"])
            self.assertEqual(scanned["scan"]["stats"]["bytes_read"], 0)
            self.assertEqual(scanned["identity"]["kind"], "path-only")
            self.assertIsNone(scanned["identity"]["git_remote_hash"])


if __name__ == "__main__":
    unittest.main()
