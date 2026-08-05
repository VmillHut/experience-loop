from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class VendorTests(unittest.TestCase):
    def test_bundled_artifacts_match_manifest(self) -> None:
        manifest = json.loads(
            (ROOT / "vendor" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["schema_version"], 1)
        for package in manifest["packages"]:
            path = ROOT / "vendor" / package["file"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, package["sha256"])
            self.assertTrue((ROOT / "vendor" / package["license_file"]).resolve().is_file())


if __name__ == "__main__":
    unittest.main()
