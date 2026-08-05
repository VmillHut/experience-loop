from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from helpers import assert_ok, payload, run_cli
from experience_loop_lib import knowledge


class KnowledgePurgeSafetyTests(unittest.TestCase):
    def test_cli_requires_preview_before_source_and_concept_purge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-purge-cli-") as raw:
            root = Path(raw)
            home = root / "home"
            source = root / "review.md"
            source.write_text(
                "# Review\n\nInspect failure paths before approval.\n",
                encoding="utf-8",
            )
            assert_ok(self, run_cli(home, "setup"))
            source_id = assert_ok(
                self, run_cli(home, "knowledge", "add", str(source))
            )["added"][0]["source_id"]
            citation_id = assert_ok(
                self,
                run_cli(home, "knowledge", "query", "failure paths approval"),
            )["matches"][0]["citation_id"]
            concept_id = assert_ok(
                self,
                run_cli(
                    home,
                    "knowledge",
                    "concept",
                    "upsert",
                    "--title",
                    "Review failure paths",
                    "--thesis",
                    "Inspect failures before accepting an abstraction.",
                    "--citation",
                    citation_id,
                ),
            )["card"]["concept_id"]

            concept_preview = assert_ok(
                self,
                run_cli(
                    home,
                    "knowledge",
                    "concept",
                    "remove",
                    concept_id,
                    "--purge",
                ),
            )
            self.assertTrue(concept_preview["requires_confirmation"])
            self.assertFalse(concept_preview["purged"])
            assert_ok(
                self,
                run_cli(home, "knowledge", "concept", "inspect", concept_id),
            )
            concept_purge = assert_ok(
                self,
                run_cli(
                    home,
                    "knowledge",
                    "concept",
                    "remove",
                    concept_id,
                    "--purge",
                    "--yes",
                ),
            )
            self.assertEqual(concept_purge["action"], "purged")

            source_preview = assert_ok(
                self,
                run_cli(home, "knowledge", "remove", source_id, "--purge"),
            )
            self.assertTrue(source_preview["requires_confirmation"])
            self.assertFalse(source_preview["purged"])
            assert_ok(self, run_cli(home, "knowledge", "inspect", source_id))
            source_purge = assert_ok(
                self,
                run_cli(
                    home,
                    "knowledge",
                    "remove",
                    source_id,
                    "--purge",
                    "--yes",
                ),
            )
            self.assertTrue(source_purge["purged"])

    def _seed_revisioned_source(self, root: Path) -> tuple[Path, str, list[str]]:
        home = root / "home"
        source = root / "guide.md"
        source.write_text(
            "# Retry\n\nUse a finite retry budget and inspect terminal failures.\n",
            encoding="utf-8",
        )
        first = knowledge.add_sources(source, data_dir=home)
        self.assertTrue(first["ok"], first)
        source_id = first["added"][0]["source_id"]

        source.write_text(
            "# Retry\n\nUse exponential backoff, jitter, and a finite retry budget.\n",
            encoding="utf-8",
        )
        second = knowledge.add_sources(source, data_dir=home)
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["revised"][0]["source_id"], source_id)

        inspected = knowledge.inspect_source(source_id, data_dir=home)
        hashes = [revision["sha256"] for revision in inspected["revisions"]]
        self.assertEqual(len(hashes), 2)
        return home, source_id, hashes

    def _object_path(self, home: Path, object_hash: str) -> Path:
        return home / "knowledge" / "objects" / "sha256" / object_hash[:2] / object_hash

    def _assert_source_and_objects_intact(
        self, home: Path, source_id: str, hashes: list[str]
    ) -> None:
        inspected = knowledge.inspect_source(source_id, data_dir=home)
        self.assertEqual(
            {revision["sha256"] for revision in inspected["revisions"]}, set(hashes)
        )
        for object_hash in hashes:
            object_path = self._object_path(home, object_hash)
            self.assertTrue(object_path.is_file(), object_path)
            self.assertEqual(knowledge.sha256_file(object_path), object_hash)
        quarantine = home / "knowledge" / "quarantine" / source_id
        self.assertFalse(quarantine.exists(), quarantine)

    def test_move_failure_restores_staged_objects_and_keeps_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-purge-move-") as raw:
            home, source_id, hashes = self._seed_revisioned_source(Path(raw))
            real_move = knowledge._move_object_to_quarantine
            calls = 0

            def fail_second_move(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise knowledge.KnowledgeError("injected move failure")
                real_move(source, destination)

            with mock.patch.object(
                knowledge,
                "_move_object_to_quarantine",
                side_effect=fail_second_move,
            ):
                with self.assertRaisesRegex(
                    knowledge.KnowledgeError, "数据库未改变"
                ):
                    knowledge.remove_source(source_id, data_dir=home, purge=True)

            self.assertEqual(calls, 2)
            self._assert_source_and_objects_intact(home, source_id, hashes)

    def test_database_failure_rolls_back_rows_and_restores_objects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-purge-db-") as raw:
            home, source_id, hashes = self._seed_revisioned_source(Path(raw))

            with mock.patch.object(
                knowledge,
                "_sync_derived_snapshots",
                side_effect=knowledge.KnowledgeError("injected snapshot failure"),
            ):
                with self.assertRaisesRegex(
                    knowledge.KnowledgeError, "数据库未改变"
                ):
                    knowledge.remove_source(source_id, data_dir=home, purge=True)

            self._assert_source_and_objects_intact(home, source_id, hashes)
            integrity = knowledge.integrity_check(data_dir=home, deep=True)
            self.assertTrue(integrity["ok"], integrity)

    def test_cleanup_failure_leaves_retryable_quarantine(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-purge-cleanup-") as raw:
            root = Path(raw)
            home = root / "home"
            source = root / "guide.md"
            source.write_text(
                "# Review\n\nReview failure paths before accepting generated code.\n",
                encoding="utf-8",
            )
            assert_ok(self, run_cli(home, "setup"))
            added = knowledge.add_sources(source, data_dir=home)["added"][0]
            source_id = added["source_id"]
            object_hash = added["sha256"]
            object_path = self._object_path(home, object_hash)
            quarantine_path = (
                home / "knowledge" / "quarantine" / source_id / object_hash
            )

            with mock.patch.object(
                knowledge,
                "_delete_quarantine_file",
                return_value="injected cleanup failure",
            ):
                result = knowledge.remove_source(source_id, data_dir=home, purge=True)

            self.assertFalse(result["ok"], result)
            self.assertTrue(result["purged"])
            self.assertTrue(result["cleanup_pending"])
            self.assertEqual(result["retry"]["source_id"], source_id)
            self.assertEqual(result["retryable_residuals"][0]["sha256"], object_hash)
            self.assertFalse(object_path.exists())
            self.assertTrue(quarantine_path.is_file())
            with self.assertRaises(knowledge.SourceNotFoundError):
                knowledge.inspect_source(source_id, data_dir=home)

            integrity = knowledge.integrity_check(data_dir=home, deep=True)
            self.assertFalse(integrity["ok"], integrity)
            self.assertTrue(
                any(
                    error["kind"] == "purge_cleanup_pending"
                    for error in integrity["errors"]
                )
            )
            doctor = run_cli(home, "doctor", "--deep")
            self.assertEqual(doctor.returncode, 4, doctor.stderr or doctor.stdout)
            doctor_data = payload(doctor)["data"]
            knowledge_check = next(
                check
                for check in doctor_data["checks"]
                if check["name"] == "knowledge"
            )
            self.assertEqual(knowledge_check["status"], "fail")

            retry = knowledge.remove_source(source_id, data_dir=home, purge=True)
            self.assertTrue(retry["ok"], retry)
            self.assertEqual(retry["action"], "purge-cleanup-retried")
            self.assertTrue(retry["cleanup_retried"])
            self.assertFalse(retry["cleanup_pending"])
            self.assertFalse(quarantine_path.exists())
            self.assertFalse(quarantine_path.parent.exists())
            integrity = knowledge.integrity_check(data_dir=home, deep=True)
            self.assertTrue(integrity["ok"], integrity)

    def test_retry_resumes_an_interrupted_precommit_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-purge-resume-") as raw:
            root = Path(raw)
            home = root / "home"
            source = root / "guide.md"
            source.write_text(
                "# Recovery\n\nA purge should be recoverable across process interruption.\n",
                encoding="utf-8",
            )
            added = knowledge.add_sources(source, data_dir=home)["added"][0]
            source_id = added["source_id"]
            object_hash = added["sha256"]
            object_path = self._object_path(home, object_hash)
            quarantine_path = knowledge._quarantine_object_path(
                home, source_id, object_hash
            )

            knowledge._move_object_to_quarantine(object_path, quarantine_path)
            self.assertFalse(object_path.exists())
            self.assertTrue(quarantine_path.is_file())
            self.assertEqual(
                knowledge.inspect_source(source_id, data_dir=home)["source"]["source_id"],
                source_id,
            )

            result = knowledge.remove_source(source_id, data_dir=home, purge=True)

            self.assertTrue(result["ok"], result)
            self.assertTrue(result["purged"])
            self.assertFalse(quarantine_path.exists())
            with self.assertRaises(knowledge.SourceNotFoundError):
                knowledge.inspect_source(source_id, data_dir=home)

    def test_shared_object_is_not_quarantined_or_deleted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-purge-shared-") as raw:
            root = Path(raw)
            home = root / "home"
            markdown = root / "same.md"
            text = root / "same.txt"
            content = "The same immutable evidence bytes are shared.\n"
            markdown.write_text(content, encoding="utf-8")
            text.write_text(content, encoding="utf-8")
            first = knowledge.add_sources(markdown, data_dir=home)["added"][0]
            second = knowledge.add_sources(text, data_dir=home)["added"][0]
            self.assertNotEqual(first["source_id"], second["source_id"])
            self.assertEqual(first["sha256"], second["sha256"])

            result = knowledge.remove_source(
                first["source_id"], data_dir=home, purge=True
            )

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["objects_quarantined"], 0)
            self.assertEqual(result["objects_preserved_for_other_sources"], 1)
            object_path = self._object_path(home, first["sha256"])
            self.assertTrue(object_path.is_file())
            inspected = knowledge.inspect_source(second["source_id"], data_dir=home)
            self.assertEqual(inspected["source"]["sha256"], second["sha256"])


if __name__ == "__main__":
    unittest.main()
