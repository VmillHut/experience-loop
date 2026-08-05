from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PythonCompatibilityTests(unittest.TestCase):
    def test_repository_python_sources_parse_as_python_39(self) -> None:
        paths = [
            path
            for path in ROOT.rglob("*.py")
            if "__pycache__" not in path.parts and ".git" not in path.parts
        ]
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                source = path.read_text(encoding="utf-8")
                ast.parse(source, filename=str(path), feature_version=(3, 9))


if __name__ == "__main__":
    unittest.main()
