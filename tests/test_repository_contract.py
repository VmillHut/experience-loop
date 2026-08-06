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
        self.assertLessEqual(len(skill.splitlines()), 500)
        self.assertIn("| `auto` |", skill)
        self.assertIn("| `focus` |", skill)
        self.assertIn("| `off` |", skill)
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
