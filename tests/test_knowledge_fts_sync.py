from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from experience_loop_lib import knowledge


class _NoFtsConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        object.__setattr__(self, "_connection", connection)

    def __getattr__(self, name: str):
        return getattr(self._connection, name)

    def __setattr__(self, name: str, value) -> None:
        setattr(self._connection, name, value)

    def execute(self, sql: str, parameters=()):
        if "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts" in sql:
            raise sqlite3.OperationalError("no such module: fts5")
        return self._connection.execute(sql, parameters)


class KnowledgeFtsSyncTests(unittest.TestCase):
    def _create_library(
        self,
        root: Path,
        token: str,
        *,
        sections: int = 1,
    ) -> tuple[Path, Path, int]:
        home = root / "home"
        source = root / "source.md"
        blocks = []
        for index in range(sections):
            blocks.append(
                "# Section {0}\n\n{1} indexed evidence {2}.\n".format(
                    index + 1,
                    token,
                    "supports architecture review " * 180,
                )
            )
        source.write_text("\n".join(blocks), encoding="utf-8")
        result = knowledge.add_sources(source, data_dir=home)
        self.assertTrue(result["ok"], result)
        chunk_count = result["added"][0]["chunk_count"]
        database = home / "knowledge" / "library.sqlite"
        with closing(sqlite3.connect(str(database))) as connection:
            available = connection.execute(
                "SELECT value FROM library_meta WHERE key = 'fts5_available'"
            ).fetchone()
        if not available or available[0] != "1":
            self.skipTest("SQLite FTS5 is unavailable in this Python runtime")
        return home, database, chunk_count

    def test_healthy_database_does_not_take_backfill_write_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-fts-steady-") as raw:
            home, _, _ = self._create_library(Path(raw), "STEADY_STATE_TOKEN")

            with mock.patch.object(
                knowledge,
                "_transaction",
                side_effect=AssertionError("healthy FTS must not take a repair lock"),
            ):
                result = knowledge.query_sources(
                    "STEADY_STATE_TOKEN", data_dir=home
                )

            self.assertGreaterEqual(result["count"], 1)

    def test_partial_fts_corruption_is_repaired_before_query(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-fts-repair-") as raw:
            home, database, _ = self._create_library(Path(raw), "FTS_REPAIR_TOKEN")
            with closing(sqlite3.connect(str(database))) as connection:
                chunk_id = connection.execute("SELECT chunk_id FROM chunks").fetchone()[0]
                connection.execute(
                    "DELETE FROM chunk_fts WHERE chunk_id = ?", (chunk_id,)
                )
                connection.commit()

            result = knowledge.query_sources("FTS_REPAIR_TOKEN", data_dir=home)

            self.assertGreaterEqual(result["count"], 1)
            self.assertEqual(result["retrieval_method"], "sqlite-fts5+cjk-ngram")
            with closing(sqlite3.connect(str(database))) as connection:
                restored = connection.execute(
                    "SELECT COUNT(*) FROM chunk_fts WHERE chunk_id = ?", (chunk_id,)
                ).fetchone()[0]
            self.assertEqual(restored, 1)

    def test_dropped_fts_table_is_recreated_and_backfilled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-fts-recreate-") as raw:
            home, database, chunk_count = self._create_library(
                Path(raw), "RECREATE_FTS_TOKEN"
            )
            with closing(sqlite3.connect(str(database))) as connection:
                connection.execute("DROP TABLE chunk_fts")
                connection.commit()

            result = knowledge.query_sources("RECREATE_FTS_TOKEN", data_dir=home)

            self.assertGreaterEqual(result["count"], 1)
            with closing(sqlite3.connect(str(database))) as connection:
                row_count = connection.execute(
                    "SELECT COUNT(*) FROM chunk_fts"
                ).fetchone()[0]
            self.assertEqual(row_count, chunk_count)

    def test_backfill_difference_is_null_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-fts-null-") as raw:
            home, database, _ = self._create_library(Path(raw), "NULL_SAFE_TOKEN")
            with closing(sqlite3.connect(str(database))) as connection:
                chunk_id = connection.execute("SELECT chunk_id FROM chunks").fetchone()[0]
                connection.execute(
                    "DELETE FROM chunk_fts WHERE chunk_id = ?", (chunk_id,)
                )
                connection.execute(
                    "INSERT INTO chunk_fts(chunk_id, source_id, revision_id, text, ngrams) "
                    "VALUES (NULL, NULL, NULL, 'orphan', 'orphan')"
                )
                connection.commit()

            result = knowledge.query_sources("NULL_SAFE_TOKEN", data_dir=home)

            self.assertGreaterEqual(result["count"], 1)
            with closing(sqlite3.connect(str(database))) as connection:
                restored = connection.execute(
                    "SELECT COUNT(*) FROM chunk_fts WHERE chunk_id = ?", (chunk_id,)
                ).fetchone()[0]
            self.assertEqual(restored, 1)

    def test_failed_backfill_rolls_back_partial_writes_and_retries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-fts-retry-") as raw:
            home, database, chunk_count = self._create_library(
                Path(raw), "FTS_RETRY_TOKEN", sections=3
            )
            self.assertGreaterEqual(chunk_count, 2)
            with closing(sqlite3.connect(str(database))) as connection:
                connection.execute("DELETE FROM chunk_fts")
                connection.commit()

            original_ngram_text = knowledge._ngram_text
            calls = 0

            def fail_second_row(text: str) -> str:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise sqlite3.OperationalError("injected backfill failure")
                return original_ngram_text(text)

            with mock.patch.object(
                knowledge, "_ngram_text", side_effect=fail_second_row
            ):
                with self.assertRaisesRegex(
                    knowledge.KnowledgeError, "injected backfill failure"
                ):
                    knowledge.query_sources("FTS_RETRY_TOKEN", data_dir=home)

            self.assertEqual(calls, 2)
            with closing(sqlite3.connect(str(database))) as connection:
                rows_after_failure = connection.execute(
                    "SELECT COUNT(*) FROM chunk_fts"
                ).fetchone()[0]
            self.assertEqual(rows_after_failure, 0)

            recovered = knowledge.query_sources("FTS_RETRY_TOKEN", data_dir=home)
            self.assertGreaterEqual(recovered["count"], 1)
            with closing(sqlite3.connect(str(database))) as connection:
                row_count = connection.execute(
                    "SELECT COUNT(*) FROM chunk_fts"
                ).fetchone()[0]
                distinct_count = connection.execute(
                    "SELECT COUNT(DISTINCT chunk_id) FROM chunk_fts"
                ).fetchone()[0]
            self.assertEqual(row_count, chunk_count)
            self.assertEqual(distinct_count, chunk_count)

    def test_concurrent_backfill_rechecks_after_write_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-fts-concurrent-") as raw:
            home, database, chunk_count = self._create_library(
                Path(raw), "FTS_CONCURRENT_TOKEN", sections=2
            )
            with closing(sqlite3.connect(str(database))) as connection:
                connection.execute("DELETE FROM chunk_fts")
                connection.commit()

            barrier = threading.Barrier(2)
            seen_threads = set()
            seen_lock = threading.Lock()
            original_missing_rows = knowledge._missing_fts_rows

            def synchronize_first_check(connection: sqlite3.Connection):
                rows = original_missing_rows(connection)
                thread_id = threading.get_ident()
                with seen_lock:
                    first_check = thread_id not in seen_threads
                    seen_threads.add(thread_id)
                if first_check:
                    barrier.wait(timeout=10.0)
                return rows

            def run_query() -> int:
                return knowledge.query_sources(
                    "FTS_CONCURRENT_TOKEN", data_dir=home
                )["count"]

            with mock.patch.object(
                knowledge, "_missing_fts_rows", side_effect=synchronize_first_check
            ):
                with ThreadPoolExecutor(max_workers=2) as executor:
                    counts = [future.result() for future in [
                        executor.submit(run_query),
                        executor.submit(run_query),
                    ]]

            self.assertTrue(all(count >= 1 for count in counts), counts)
            with closing(sqlite3.connect(str(database))) as connection:
                fts_count = connection.execute(
                    "SELECT COUNT(*) FROM chunk_fts"
                ).fetchone()[0]
                distinct_fts_count = connection.execute(
                    "SELECT COUNT(DISTINCT chunk_id) FROM chunk_fts"
                ).fetchone()[0]
            self.assertEqual(fts_count, chunk_count)
            self.assertEqual(distinct_fts_count, chunk_count)

    def test_fts_unavailable_uses_fallback_then_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-fts-unavailable-") as raw:
            root = Path(raw)
            home = root / "home"
            source = root / "source.md"
            source.write_text(
                "# Fallback\n\nNO_FTS_TOKEN remains searchable without FTS5.\n",
                encoding="utf-8",
            )
            real_connect = sqlite3.connect

            def connect_without_fts(*args, **kwargs):
                return _NoFtsConnection(real_connect(*args, **kwargs))

            with mock.patch.object(
                knowledge.sqlite3, "connect", side_effect=connect_without_fts
            ):
                added = knowledge.add_sources(source, data_dir=home)
                fallback = knowledge.query_sources("NO_FTS_TOKEN", data_dir=home)

            self.assertTrue(added["ok"], added)
            self.assertGreaterEqual(fallback["count"], 1)
            self.assertEqual(
                fallback["retrieval_method"], "lexical-cjk-ngram-fallback"
            )
            database = home / "knowledge" / "library.sqlite"
            with closing(real_connect(str(database))) as connection:
                available = connection.execute(
                    "SELECT value FROM library_meta WHERE key = 'fts5_available'"
                ).fetchone()
                fts_table = connection.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type = 'table' AND name = 'chunk_fts'"
                ).fetchone()
            self.assertEqual(available, ("0",))
            self.assertIsNone(fts_table)

            recovered = knowledge.query_sources("NO_FTS_TOKEN", data_dir=home)
            self.assertGreaterEqual(recovered["count"], 1)
            self.assertEqual(recovered["retrieval_method"], "sqlite-fts5+cjk-ngram")
            with closing(real_connect(str(database))) as connection:
                chunk_count = connection.execute(
                    "SELECT COUNT(*) FROM chunks"
                ).fetchone()[0]
                fts_count = connection.execute(
                    "SELECT COUNT(*) FROM chunk_fts"
                ).fetchone()[0]
            self.assertEqual(fts_count, chunk_count)


if __name__ == "__main__":
    unittest.main()
