from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from helpers import assert_ok, run_cli


class ProjectAdoptionTests(unittest.TestCase):
    def test_imported_path_only_project_can_adopt_history_after_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-project-adopt-") as raw:
            root = Path(raw)
            first_home = root / "first-home"
            second_home = root / "second-home"
            first_project = root / "machine-a" / "scratch"
            second_project = root / "machine-b" / "scratch"
            first_project.mkdir(parents=True)
            second_project.mkdir(parents=True)
            for project in (first_project, second_project):
                (project / "notes.txt").write_text("same small project\n", encoding="utf-8")
            material = root / "review.md"
            material.write_text("# Review\n\nVerify failure paths before approval.\n", encoding="utf-8")

            assert_ok(self, run_cli(first_home, "setup"))
            original_id = assert_ok(
                self, run_cli(first_home, "project", "scan", str(first_project))
            )["id"]
            assert_ok(
                self,
                run_cli(
                    first_home,
                    "knowledge",
                    "add",
                    str(material),
                    "--project",
                    original_id,
                ),
            )
            archive = root / "portable.zip"
            assert_ok(self, run_cli(first_home, "export", str(archive)))
            assert_ok(self, run_cli(second_home, "import", str(archive)))

            ambiguous = assert_ok(
                self, run_cli(second_home, "project", "scan", str(second_project))
            )
            provisional_id = ambiguous["id"]
            self.assertNotEqual(provisional_id, original_id)
            self.assertTrue(ambiguous["identity_resolution"]["needs_confirmation"])
            self.assertIn(
                original_id,
                [item["id"] for item in ambiguous["identity_resolution"]["candidates"]],
            )
            self.assertEqual(
                assert_ok(
                    self,
                    run_cli(
                        second_home,
                        "knowledge",
                        "list",
                        "--project",
                        provisional_id,
                    ),
                )["count"],
                0,
            )

            adopted = assert_ok(
                self,
                run_cli(
                    second_home,
                    "project",
                    "scan",
                    str(second_project),
                    "--adopt-project",
                    original_id,
                ),
            )
            self.assertEqual(adopted["id"], original_id)
            self.assertEqual(
                adopted["identity_resolution"]["status"],
                "adopted-by-user-confirmation",
            )
            self.assertEqual(
                adopted["identity_resolution"]["replaced_provisional_project_id"],
                provisional_id,
            )
            projects = assert_ok(self, run_cli(second_home, "project", "list"))
            self.assertEqual(projects["count"], 1)
            self.assertEqual(projects["projects"][0]["id"], original_id)
            restored_sources = assert_ok(
                self,
                run_cli(
                    second_home,
                    "knowledge",
                    "list",
                    "--project",
                    original_id,
                ),
            )
            self.assertEqual(restored_sources["count"], 1)


if __name__ == "__main__":
    unittest.main()
