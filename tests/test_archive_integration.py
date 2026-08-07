from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys
import tempfile
from typing import Any, Dict
import unittest
import zipfile


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from helpers import assert_ok, payload, run_cli
from experience_loop_lib.common import APP_NAME, SCHEMA_VERSION


class ArchiveIntegrationTests(unittest.TestCase):
    def _seed_home(self, root: Path) -> Dict[str, Any]:
        home = root / "source-home"
        project = root / "service"
        project.mkdir()
        (project / "README.md").write_text(
            "# Retry service\n\n```bash\npython -m unittest discover -s tests\n```\n",
            encoding="utf-8",
        )
        (project / "AGENTS.md").write_text(
            "# Private project rules\n\n- Internal codename: blue-orchid.\n",
            encoding="utf-8",
        )
        material = root / "reliability.md"
        material.write_text(
            "# Reliability\n\n"
            "熔断器必须用真实失败率驱动，并保留恢复窗口的验证证据。\n",
            encoding="utf-8",
        )
        assert_ok(
            self,
            run_cli(
                home,
                "setup",
                "--name",
                "Archive User",
                "--goal",
                "架构与验证",
                "--learning-focus",
                "可靠性决策",
            ),
        )
        project_data = assert_ok(
            self, run_cli(home, "project", "scan", str(project))
        )
        project_id = project_data["id"]
        source_data = assert_ok(
            self,
            run_cli(
                home,
                "knowledge",
                "add",
                str(material),
                "--project",
                project_id,
            ),
        )
        source_id = source_data["added"][0]["source_id"]
        query = assert_ok(
            self,
            run_cli(home, "knowledge", "query", "真实失败率 恢复窗口"),
        )
        citation_id = query["matches"][0]["citation_id"]
        concept_data = assert_ok(
            self,
            run_cli(
                home,
                "knowledge",
                "concept",
                "upsert",
                "--title",
                "用证据驱动熔断",
                "--thesis",
                "熔断阈值必须来自可观测失败证据，而不是主观常量。",
                "--citation",
                citation_id,
                "--project",
                project_id,
                "--status",
                "reviewed",
                "--applies-when",
                "依赖服务出现级联失败",
                "--decision-trigger",
                "需要选择熔断阈值",
                "--engineering-question",
                "失败率证据来自哪里？",
                "--tag",
                "reliability",
            ),
        )
        concept_id = concept_data["card"]["concept_id"]
        application_data = assert_ok(
            self,
            run_cli(
                home,
                "knowledge",
                "application",
                "record",
                concept_id,
                "--situation",
                "下游接口间歇失败",
                "--decision",
                "按失败率打开熔断并设置半开窗口",
                "--outcome",
                "级联超时下降且恢复过程可验证",
                "--project",
                project_id,
                "--evidence",
                "integration-test:test_circuit_breaker",
                "--independence",
                "independent",
            ),
        )
        prior_event = assert_ok(
            self,
            run_cli(
                home,
                "ledger",
                "record",
                "--kind",
                "decision",
                "--summary",
                "先在入口服务采用证据驱动熔断",
                "--project",
                project_id,
                "--concept",
                concept_id,
                "--evidence",
                "integration-test:test_gateway_circuit_breaker",
                "--outcome",
                "入口服务恢复窗口得到验证",
                "--independence",
                "independent",
            ),
        )["event"]
        assert_ok(
            self,
            run_cli(
                home,
                "ledger",
                "record",
                "--kind",
                "transfer",
                "--summary",
                "把熔断原则迁移到当前服务",
                "--prior-event",
                prior_event["id"],
                "--context-difference",
                "从同步入口流量迁移到异步下游任务",
                "--project",
                project_id,
                "--concept",
                concept_id,
                "--evidence",
                "integration-test:test_circuit_breaker",
                "--outcome",
                "级联超时下降且半开恢复得到验证",
                "--independence",
                "independent",
            ),
        )
        return {
            "home": home,
            "project_id": project_id,
            "source_id": source_id,
            "concept_id": concept_id,
            "application_id": application_data["application"]["application_id"],
            "query_term": "真实失败率",
        }

    def test_default_export_omits_raw_index_and_restores_derived_knowledge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-archive-") as raw:
            root = Path(raw)
            seeded = self._seed_home(root)
            archive_path = root / "portable-default.zip"

            exported = assert_ok(
                self,
                run_cli(seeded["home"], "export", str(archive_path)),
            )
            self.assertFalse(exported["includes_raw_sources"])
            self.assertIn("不是可公开分享的脱敏包", exported["privacy_note"])
            self.assertIn("绑定备注", exported["privacy_note"])
            self.assertIn("概念卡", exported["privacy_note"])
            self.assertIn("应用证据", exported["privacy_note"])
            self.assertTrue(archive_path.is_file())
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive_names = archive.namelist()
                names = set(archive_names)
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                project_payload = json.loads(
                    archive.read(
                        "projects/{0}.json".format(seeded["project_id"])
                    ).decode("utf-8")
                )
            self.assertFalse(manifest["includes_raw_sources"])
            self.assertEqual(manifest["archive_schema_version"], 2)
            self.assertEqual(exported["files"], len(archive_names))
            self.assertEqual(exported["payload_files"], len(manifest["entries"]))
            self.assertEqual(exported["files"], exported["payload_files"] + 1)
            self.assertNotIn("knowledge/library.sqlite", names)
            self.assertIn("controls.json", names)
            self.assertFalse(any(name.startswith("knowledge/objects/") for name in names))
            self.assertIn("knowledge/portable-catalog.json", names)
            self.assertIn("knowledge/derived/source_bindings.json", names)
            self.assertIn("knowledge/derived/concept_cards.json", names)
            self.assertIn("knowledge/derived/application_evidence.json", names)
            self.assertIsNone(project_payload["path"])
            for rule in project_payload["scan"]["project_rules"]:
                self.assertNotIn("text", rule)
                self.assertTrue(rule["redacted_from_export"])
                self.assertIn("text_sha256", rule)
            for command in project_payload["scan"]["suggested_commands"]:
                self.assertNotIn("command", command)
                self.assertTrue(command["redacted_from_export"])
                self.assertIn("command_sha256", command)

            restored_home = root / "restored-default"
            imported = assert_ok(
                self,
                run_cli(restored_home, "import", str(archive_path)),
            )
            self.assertFalse(imported["includes_raw_sources"])
            self.assertEqual(imported["files"], len(archive_names))
            self.assertEqual(imported["payload_files"], len(manifest["entries"]))
            self.assertEqual(imported["restored_knowledge_sources"], 1)
            restored_status = assert_ok(self, run_cli(restored_home, "status"))
            self.assertEqual(restored_status["knowledge_sources"], 1)
            self.assertEqual(restored_status["knowledge_materialized_sources"], 0)
            self.assertEqual(restored_status["knowledge_placeholder_sources"], 1)

            concepts = assert_ok(
                self,
                run_cli(
                    restored_home,
                    "knowledge",
                    "concept",
                    "list",
                    "--project",
                    seeded["project_id"],
                ),
            )
            self.assertEqual(concepts["count"], 1)
            self.assertEqual(concepts["cards"][0]["concept_id"], seeded["concept_id"])
            applications = assert_ok(
                self,
                run_cli(
                    restored_home,
                    "knowledge",
                    "application",
                    "list",
                    "--concept",
                    seeded["concept_id"],
                ),
            )
            self.assertEqual(applications["count"], 1)
            self.assertEqual(
                applications["applications"][0]["application_id"],
                seeded["application_id"],
            )
            bound_sources = assert_ok(
                self,
                run_cli(
                    restored_home,
                    "knowledge",
                    "list",
                    "--project",
                    seeded["project_id"],
                ),
            )
            self.assertEqual(bound_sources["count"], 1)
            self.assertEqual(bound_sources["sources"][0]["source_id"], seeded["source_id"])
            self.assertEqual(bound_sources["sources"][0]["chunk_count"], 0)
            no_raw_text = assert_ok(
                self,
                run_cli(restored_home, "knowledge", "query", seeded["query_term"]),
            )
            self.assertEqual(no_raw_text["count"], 0)

            projects = assert_ok(self, run_cli(restored_home, "project", "list"))
            self.assertEqual(projects["count"], 1)
            self.assertIsNone(projects["projects"][0]["path"])
            review = assert_ok(self, run_cli(restored_home, "ledger", "review"))
            self.assertEqual(review["total_events"], 2)

    def test_v1_archive_materializes_controls_from_the_legacy_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-archive-v1-") as raw:
            root = Path(raw)
            source_home = root / "source"
            archive_path = root / "legacy-v1.zip"
            target_home = root / "target"
            assert_ok(
                self,
                run_cli(
                    source_home,
                    "setup",
                    "--mode",
                    "focus",
                    "--privacy",
                    "restricted",
                ),
            )
            (source_home / "controls.json").unlink()
            relative_paths = (
                "state.json",
                "profile.json",
                "projects/index.json",
                "ledger/events.jsonl",
            )
            entries = []
            payloads = {}
            for relative in relative_paths:
                payload = (source_home / Path(relative)).read_bytes()
                payloads[relative] = payload
                entries.append(
                    {
                        "path": relative,
                        "size": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                )
            manifest = {
                "application": APP_NAME,
                "archive_schema_version": 1,
                "created_at": "2026-08-07T00:00:00Z",
                "includes_raw_sources": False,
                "entries": entries,
            }
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                for relative, payload in payloads.items():
                    archive.writestr(relative, payload)

            imported = assert_ok(
                self, run_cli(target_home, "import", str(archive_path))
            )
            self.assertTrue(imported["imported"])
            self.assertTrue((target_home / "controls.json").is_file())
            status = assert_ok(self, run_cli(target_home, "status"))
            self.assertEqual(status["default_mode"], "focus")
            self.assertEqual(status["activation_scope"], "explicit")
            self.assertEqual(status["privacy"], "restricted")

    def test_include_sources_export_restores_searchable_raw_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-archive-raw-") as raw:
            root = Path(raw)
            seeded = self._seed_home(root)
            archive_path = root / "portable-with-sources.zip"

            exported = assert_ok(
                self,
                run_cli(
                    seeded["home"],
                    "export",
                    str(archive_path),
                    "--include-sources",
                ),
            )
            self.assertTrue(exported["includes_raw_sources"])
            self.assertIn("不是公开脱敏包", exported["privacy_note"])
            self.assertIn("知识库原始资料", exported["privacy_note"])
            with zipfile.ZipFile(archive_path, "r") as archive:
                names = set(archive.namelist())
                manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            self.assertTrue(manifest["includes_raw_sources"])
            self.assertIn("knowledge/library.sqlite", names)
            self.assertNotIn("knowledge/library.sqlite-wal", names)
            self.assertNotIn("knowledge/library.sqlite-shm", names)
            self.assertTrue(any(name.startswith("knowledge/objects/sha256/") for name in names))

            restored_home = root / "restored-with-sources"
            imported = assert_ok(
                self,
                run_cli(restored_home, "import", str(archive_path)),
            )
            self.assertTrue(imported["includes_raw_sources"])
            query = assert_ok(
                self,
                run_cli(restored_home, "knowledge", "query", seeded["query_term"]),
            )
            self.assertGreaterEqual(query["count"], 1)
            self.assertEqual(query["matches"][0]["source_id"], seeded["source_id"])
            concepts = assert_ok(
                self,
                run_cli(
                    restored_home,
                    "knowledge",
                    "concept",
                    "list",
                    "--source",
                    seeded["source_id"],
                ),
            )
            self.assertEqual(concepts["count"], 1)
            self.assertEqual(concepts["cards"][0]["evidence_status"], "verified")

    def test_export_refuses_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-export-overwrite-") as raw:
            root = Path(raw)
            home = root / "home"
            archive_path = root / "backup.zip"
            assert_ok(self, run_cli(home, "setup"))
            assert_ok(self, run_cli(home, "export", str(archive_path)))
            before = archive_path.read_bytes()

            refused = run_cli(home, "export", str(archive_path))
            self.assertEqual(refused.returncode, 4)
            self.assertEqual(archive_path.read_bytes(), before)
            assert_ok(self, run_cli(home, "export", str(archive_path), "--force"))

    def test_import_rejects_structurally_incomplete_archive_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-bad-archive-") as raw:
            root = Path(raw)
            archive_path = root / "incomplete.zip"
            target_home = root / "target-home"
            state = json.dumps(
                {
                    "application": APP_NAME,
                    "schema_version": SCHEMA_VERSION,
                    "created_at": "2026-08-05T00:00:00Z",
                    "updated_at": "2026-08-05T00:00:00Z",
                },
                ensure_ascii=False,
            ).encode("utf-8")
            manifest = {
                "application": APP_NAME,
                "archive_schema_version": SCHEMA_VERSION,
                "created_at": "2026-08-05T00:00:00Z",
                "includes_raw_sources": False,
                "entries": [
                    {
                        "path": "state.json",
                        "size": len(state),
                        "sha256": hashlib.sha256(state).hexdigest(),
                    }
                ],
            }
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.writestr("state.json", state)

            imported = run_cli(target_home, "import", str(archive_path))
            self.assertEqual(imported.returncode, 6)
            self.assertFalse(target_home.exists())

    def test_import_rejects_boolean_and_float_archive_schema_versions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-archive-version-type-") as raw:
            root = Path(raw)
            for index, version in enumerate((True, 1.0), start=1):
                with self.subTest(version=version):
                    archive_path = root / ("bad-version-%s.zip" % index)
                    target_home = root / ("target-%s" % index)
                    manifest = {
                        "application": APP_NAME,
                        "archive_schema_version": version,
                        "created_at": "2026-08-07T00:00:00Z",
                        "includes_raw_sources": False,
                        "entries": [],
                    }
                    with zipfile.ZipFile(archive_path, "w") as archive:
                        archive.writestr("manifest.json", json.dumps(manifest))

                    imported = run_cli(target_home, "import", str(archive_path))
                    self.assertEqual(imported.returncode, 6)
                    self.assertIn("不支持的归档版本", payload(imported)["error"]["message"])
                    self.assertFalse(target_home.exists())

    def test_import_rejects_boolean_and_float_entry_sizes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-archive-size-type-") as raw:
            root = Path(raw)
            content = b"x"
            for index, size in enumerate((True, 1.0), start=1):
                with self.subTest(size=size):
                    archive_path = root / ("bad-size-%s.zip" % index)
                    target_home = root / ("target-%s" % index)
                    manifest = {
                        "application": APP_NAME,
                        "archive_schema_version": 1,
                        "created_at": "2026-08-07T00:00:00Z",
                        "includes_raw_sources": False,
                        "entries": [
                            {
                                "path": "state.json",
                                "size": size,
                                "sha256": hashlib.sha256(content).hexdigest(),
                            }
                        ],
                    }
                    with zipfile.ZipFile(archive_path, "w") as archive:
                        archive.writestr("manifest.json", json.dumps(manifest))
                        archive.writestr("state.json", content)

                    imported = run_cli(target_home, "import", str(archive_path))
                    self.assertEqual(imported.returncode, 6)
                    self.assertIn("归档条目元数据无效", payload(imported)["error"]["message"])
                    self.assertFalse(target_home.exists())

    def test_import_rejects_archive_stored_inside_replaced_home(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-inner-archive-") as raw:
            home = Path(raw) / "home"
            assert_ok(self, run_cli(home, "setup"))
            archive_path = home / "backup.zip"
            assert_ok(self, run_cli(home, "export", str(archive_path)))

            imported = run_cli(home, "import", str(archive_path), "--replace")
            self.assertEqual(imported.returncode, 4)
            self.assertTrue(archive_path.is_file())
            self.assertTrue((home / "profile.json").is_file())

    def test_import_replace_refuses_unmanaged_nonempty_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-import-safety-") as raw:
            root = Path(raw)
            source_home = root / "source-home"
            archive_path = root / "backup.zip"
            assert_ok(self, run_cli(source_home, "setup"))
            assert_ok(self, run_cli(source_home, "export", str(archive_path)))

            target = root / "unrelated-project"
            (target / "src").mkdir(parents=True)
            valuable = target / "valuable.txt"
            valuable.write_text("preserve me", encoding="utf-8")
            before = {
                path.relative_to(target).as_posix(): path.read_bytes()
                for path in target.rglob("*")
                if path.is_file()
            }

            imported = run_cli(target, "import", str(archive_path), "--replace")
            self.assertNotEqual(imported.returncode, 0)
            after = {
                path.relative_to(target).as_posix(): path.read_bytes()
                for path in target.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_import_rejects_windows_style_archive_traversal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-archive-traversal-") as raw:
            root = Path(raw)
            archive_path = root / "malicious.zip"
            target_home = root / "target"
            malicious_name = "projects/foo\\..\\..\\outside.txt"
            content = b"owned"
            manifest = {
                "application": APP_NAME,
                "archive_schema_version": SCHEMA_VERSION,
                "created_at": "2026-08-05T00:00:00Z",
                "includes_raw_sources": False,
                "entries": [
                    {
                        "path": malicious_name,
                        "size": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                ],
            }
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.writestr(malicious_name, content)

            imported = run_cli(target_home, "import", str(archive_path))
            self.assertEqual(imported.returncode, 6)
            self.assertFalse((root / "outside.txt").exists())
            self.assertFalse(target_home.exists())


if __name__ == "__main__":
    unittest.main()
