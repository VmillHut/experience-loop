from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_skill_has_complete_frontmatter_and_stays_progressive(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("TODO", skill)
        self.assertTrue(skill.startswith("---\n"))
        match = re.search(r"^description:\s*(.+)$", skill, flags=re.MULTILINE)
        self.assertIsNotNone(match)
        description = match.group(1).strip()
        self.assertGreater(len(description), 60)
        self.assertIn("when", description.lower())
        self.assertLessEqual(len(skill.splitlines()), 160)
        self.assertLessEqual(len(skill), 15000)
        self.assertIn("| `auto` |", skill)
        self.assertIn("| `focus` |", skill)
        self.assertIn("| `deep` |", skill)
        self.assertIn("| `off` |", skill)
        mode_rows = {
            mode: next(
                line
                for line in skill.splitlines()
                if line.startswith("| `{0}` |".format(mode))
            )
            for mode in ("auto", "focus", "deep", "off")
        }
        self.assertIn("silence, embedded guidance", mode_rows["auto"])
        self.assertIn("Intensity rises", mode_rows["auto"])
        self.assertIn("never silently becomes `deep`", mode_rows["auto"])
        self.assertIn("no content-bearing profile use", mode_rows["off"])
        self.assertIn("learning references, checkpoints", mode_rows["off"])
        self.assertIn("learning summaries, or ledger writes", mode_rows["off"])
        self.assertIn("minimal mode/privacy control read", mode_rows["off"])
        self.assertIn("honor a previously saved `off`", mode_rows["off"])
        self.assertIn("`auto` is not a synonym for low intervention", skill)
        self.assertIn(
            "Let one selected capability limit only learning intervention and ledger labeling.",
            skill,
        )
        self.assertIn(
            "It must never limit the engineering concerns inspected.", skill
        )
        self.assertIn("## Resolve only state that changes the task", skill)
        self.assertIn("Do not run `status` or `doctor` routinely", skill)
        self.assertIn(
            "Load a saved profile only when it is customized and can change", skill
        )
        self.assertIn(
            "Never consume content-bearing profile fields on the fast path or in `off`.",
            skill,
        )
        self.assertIn("Ordinary `auto` work should not need it.", skill)
        self.assertIn("references/capability-compass.md", skill)
        self.assertTrue((ROOT / "references" / "capability-compass.md").is_file())

    def test_openai_metadata_is_utf8_and_invokes_the_skill(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertNotIn("�", metadata)
        self.assertIn('display_name: "Experience Loop"', metadata)
        self.assertIn("$experience-loop", metadata)
        self.assertIn("allow_implicit_invocation: true", metadata)

    def test_bundled_pdf_parser_imports_without_installation(self) -> None:
        script = (
            "import json, sys; "
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r}); "
            "sys.version_info = (3, 9, 19, 'final', 0); "
            "from experience_loop_lib import extractors; "
            "pypdf = extractors._load_pypdf(); "
            "info = extractors.pdf_parser_info(); "
            "assert pypdf.__version__ == '6.14.2', info; "
            "assert info['source'] == 'bundled-verified-wheel', info; "
            "assert info['verified'] is True, info; "
            "assert info['dependencies'][0]['name'] == 'typing_extensions', info; "
            "assert info['dependencies'][0]['verified'] is True, info; "
            "print(json.dumps(info, sort_keys=True))"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-I", "-S", "-c", script],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"source": "bundled-verified-wheel"', result.stdout)
        self.assertIn('"name": "typing_extensions"', result.stdout)


if __name__ == "__main__":
    unittest.main()
