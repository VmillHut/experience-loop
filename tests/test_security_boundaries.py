from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from helpers import assert_ok, payload, run_cli, tree_fingerprint


class SecurityBoundaryTests(unittest.TestCase):
    def test_project_command_extraction_rejects_shell_chains(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-command-safety-") as raw:
            root = Path(raw)
            home = root / "home"
            project = root / "project"
            project.mkdir()
            (project / "README.md").write_text(
                "# Commands\n\n```powershell\n"
                "python -m unittest discover -s tests\n"
                "python -m pytest && echo stolen\n"
                "python -m pytest; echo stolen\n"
                "python -m pytest | tee result.txt\n"
                "python -m pytest > result.txt\n"
                "python -m pytest $(echo stolen)\n"
                "```\n",
                encoding="utf-8",
            )
            before = tree_fingerprint(project)
            assert_ok(self, run_cli(home, "setup"))
            scan = assert_ok(self, run_cli(home, "project", "scan", str(project)))
            commands = scan["scan"]["suggested_commands"]
            self.assertEqual([item["command"] for item in commands], [
                "python -m unittest discover -s tests"
            ])
            self.assertTrue(commands[0]["untrusted_content"])
            self.assertFalse(commands[0]["execution_authorized"])
            self.assertTrue(commands[0]["requires_verification"])
            self.assertEqual(tree_fingerprint(project), before)

    def test_metadata_only_blocks_source_content_but_keeps_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-metadata-only-") as raw:
            root = Path(raw)
            home = root / "home"
            material = root / "notes.md"
            material.write_text("# Secret notes\n\nUnique evidence phrase.\n", encoding="utf-8")
            assert_ok(self, run_cli(home, "setup", "--privacy", "normal"))
            added = assert_ok(self, run_cli(home, "knowledge", "add", str(material)))
            source_id = added["added"][0]["source_id"]
            assert_ok(self, run_cli(home, "setup", "--privacy", "metadata-only"))

            listing = assert_ok(self, run_cli(home, "knowledge", "list"))
            self.assertEqual(listing["count"], 1)
            metadata = assert_ok(
                self, run_cli(home, "knowledge", "inspect", source_id)
            )
            self.assertEqual(metadata["chunks"], [])

            for args in (
                ("knowledge", "query", "Unique evidence"),
                ("knowledge", "inspect", source_id, "--include-chunks"),
                ("knowledge", "reindex", source_id),
                ("knowledge", "add", str(material)),
            ):
                result = run_cli(home, *args)
                self.assertEqual(result.returncode, 4, (args, result.stdout, result.stderr))
                self.assertFalse(payload(result)["ok"])


if __name__ == "__main__":
    unittest.main()
