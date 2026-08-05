from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
import sys

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from experience_loop_lib.common import ExperienceLoopError, FileLock


class FileLockTests(unittest.TestCase):
    def test_old_mtime_never_allows_a_live_owner_to_be_stolen(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-lock-") as raw:
            lock_path = Path(raw) / "state.lock"
            first = FileLock(lock_path, timeout=0.2, stale_after=0.01)
            first.__enter__()
            try:
                old = time.time() - 3600
                os.utime(lock_path, (old, old))
                with self.assertRaises(ExperienceLoopError):
                    with FileLock(lock_path, timeout=0.1, stale_after=0.01):
                        self.fail("a live operating-system lock must not be stolen")
            finally:
                first.__exit__(None, None, None)

            with FileLock(lock_path, timeout=0.2, stale_after=0.01):
                self.assertTrue(lock_path.is_file())


if __name__ == "__main__":
    unittest.main()
