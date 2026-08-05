from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asset_service import AssetService, DownloadError, RetryPolicy


class AssetServiceTests(unittest.TestCase):
    def test_succeeds_on_third_attempt(self) -> None:
        attempts = 0

        def fetch(_: str) -> bytes:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise DownloadError("temporary")
            return b"ok"

        service = AssetService(fetch, RetryPolicy(max_attempts=3))
        self.assertEqual(service.download("asset"), b"ok")
        self.assertEqual(attempts, 3)

    def test_does_not_retry_non_transient_errors(self) -> None:
        def fetch(_: str) -> bytes:
            raise ValueError("bad key")

        with self.assertRaises(ValueError):
            AssetService(fetch).download("bad")


if __name__ == "__main__":
    unittest.main()
