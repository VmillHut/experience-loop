from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from helpers import assert_ok, payload, run_cli, tree_fingerprint


class RuntimeCliTests(unittest.TestCase):
    def test_cli_help_explains_confidence_range_and_partial_knowledge_add(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-help-") as raw:
            home = Path(raw) / "data"

            ledger_help = run_cli(home, "ledger", "record", "--help")
            self.assertEqual(ledger_help.returncode, 0, ledger_help.stderr)
            self.assertIn("0.0–1.0", ledger_help.stdout)
            self.assertIn("浮点数", ledger_help.stdout)

            knowledge_help = run_cli(home, "knowledge", "add", "--help")
            self.assertEqual(knowledge_help.returncode, 0, knowledge_help.stderr)
            self.assertIn("退出码 3", knowledge_help.stdout)
            self.assertIn("成功项会保留", knowledge_help.stdout)

    def test_setup_is_idempotent_and_preserves_custom_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-runtime-") as raw:
            root = Path(raw)
            home = root / "data"

            first = run_cli(
                home,
                "setup",
                "--name",
                "小林",
                "--role",
                "backend-engineer",
                "--experience-level",
                "1-3 years",
                "--goal",
                "架构决策, 代码审查",
                "--goal",
                "架构决策",
                "--learning-focus",
                "测试设计；故障诊断",
                "--mode",
                "coach",
                "--privacy",
                "restricted",
            )
            first_data = assert_ok(self, first)
            self.assertFalse(first_data["already_initialized"])
            profile = first_data["profile"]
            self.assertEqual(profile["name"], "小林")
            self.assertEqual(profile["role"], "backend-engineer")
            self.assertEqual(profile["experience_level"], "1-3 years")
            self.assertEqual(profile["goals"], ["架构决策", "代码审查"])
            self.assertEqual(profile["learning_focus"], ["测试设计", "故障诊断"])
            self.assertEqual(profile["mode"], "coach")
            self.assertEqual(profile["privacy"], "restricted")
            self.assertTrue(profile["customized"])
            self.assertTrue((home / "state.json").is_file())
            self.assertTrue((home / "profile.json").is_file())
            self.assertTrue((home / "ledger" / "events.jsonl").is_file())

            second_data = assert_ok(self, run_cli(home, "setup"))
            self.assertTrue(second_data["already_initialized"])
            second_profile = second_data["profile"]
            for field in (
                "name",
                "role",
                "experience_level",
                "goals",
                "learning_focus",
                "mode",
                "privacy",
                "customized",
                "created_at",
            ):
                self.assertEqual(second_profile[field], profile[field], field)

    def test_status_distinguishes_sources_placeholders_and_storage_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-status-") as raw:
            root = Path(raw)
            home = root / "data"
            source = root / "architecture.md"
            source.write_text(
                "# Boundary\n\nKeep policy decisions separate from transport mechanics.\n",
                encoding="utf-8",
            )
            assert_ok(self, run_cli(home, "setup"))

            empty_status = assert_ok(self, run_cli(home, "status"))
            self.assertNotIn("knowledge_files", empty_status)
            self.assertEqual(empty_status["knowledge_status"], "ok")
            self.assertEqual(empty_status["knowledge_sources"], 0)
            self.assertEqual(empty_status["knowledge_materialized_sources"], 0)
            self.assertEqual(empty_status["knowledge_placeholder_sources"], 0)
            self.assertGreaterEqual(empty_status["knowledge_storage_files"], 1)

            assert_ok(self, run_cli(home, "knowledge", "add", str(source)))
            populated_status = assert_ok(self, run_cli(home, "status"))
            self.assertEqual(populated_status["knowledge_sources"], 1)
            self.assertEqual(populated_status["knowledge_materialized_sources"], 1)
            self.assertEqual(populated_status["knowledge_placeholder_sources"], 0)
            self.assertGreaterEqual(populated_status["knowledge_storage_files"], 2)

    def test_status_reports_unavailable_knowledge_counts_instead_of_zero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-status-corrupt-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup"))
            database = home / "knowledge" / "library.sqlite"
            database.parent.mkdir(parents=True, exist_ok=True)
            database.write_bytes(b"this is not a sqlite database")

            status = assert_ok(self, run_cli(home, "status"))
            self.assertEqual(status["knowledge_status"], "unavailable")
            self.assertIsNone(status["knowledge_sources"])
            self.assertIsNone(status["knowledge_materialized_sources"])
            self.assertIsNone(status["knowledge_placeholder_sources"])
            self.assertEqual(status["knowledge_storage_files"], 1)
            self.assertEqual(status["knowledge_errors"][0]["area"], "sources")

    def test_partial_knowledge_add_keeps_successes_and_returns_exit_code_three(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-partial-add-") as raw:
            root = Path(raw)
            home = root / "data"
            good = root / "good.md"
            bad = root / "empty.pdf"
            good.write_text("# Retry budget\n\nBound retries by an explicit budget.\n", encoding="utf-8")
            bad.write_bytes(b"")
            assert_ok(self, run_cli(home, "setup"))

            added = run_cli(home, "knowledge", "add", str(good), str(bad))
            self.assertEqual(added.returncode, 3, added.stderr or added.stdout)
            added_payload = payload(added)
            self.assertFalse(added_payload["ok"])
            self.assertEqual(len(added_payload["data"]["added"]), 1)
            self.assertEqual(len(added_payload["data"]["errors"]), 1)
            listing = assert_ok(self, run_cli(home, "knowledge", "list"))
            self.assertEqual(listing["count"], 1)

    def test_mode_off_never_appends_a_learning_event(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-runtime-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup"))
            assert_ok(self, run_cli(home, "mode", "off"))
            ledger = home / "ledger" / "events.jsonl"
            before = ledger.read_bytes()

            record = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "verification",
                    "--summary",
                    "验证了失败路径",
                    "--evidence",
                    "python -m unittest",
                ),
            )
            self.assertFalse(record["recorded"])
            self.assertEqual(record["reason"], "mode_off")
            self.assertEqual(ledger.read_bytes(), before)
            review = assert_ok(self, run_cli(home, "ledger", "review"))
            self.assertEqual(review["total_events"], 0)
            self.assertEqual(review["xp_total"], 0)

    def test_profile_can_replace_and_clear_stale_learning_targets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-profile-") as raw:
            home = Path(raw) / "data"
            assert_ok(
                self,
                run_cli(
                    home,
                    "setup",
                    "--name",
                    "旧名字",
                    "--goal",
                    "旧目标, 保留目标",
                    "--learning-focus",
                    "旧方向",
                ),
            )

            updated = assert_ok(
                self,
                run_cli(
                    home,
                    "profile",
                    "update",
                    "--clear-name",
                    "--goal",
                    "架构决策",
                    "--replace-goals",
                    "--learning-focus",
                    "代码审查, 故障诊断",
                    "--replace-learning-focus",
                    "--experience-level",
                    "2 years",
                ),
            )
            profile = updated["profile"]
            self.assertIsNone(profile["name"])
            self.assertEqual(profile["goals"], ["架构决策"])
            self.assertEqual(profile["learning_focus"], ["代码审查", "故障诊断"])
            self.assertEqual(profile["experience_level"], "2 years")

            cleared = assert_ok(
                self,
                run_cli(
                    home,
                    "profile",
                    "update",
                    "--clear-goals",
                    "--clear-learning-focus",
                    "--clear-experience-level",
                ),
            )
            self.assertEqual(cleared["profile"]["goals"], [])
            self.assertEqual(cleared["profile"]["learning_focus"], [])
            self.assertIsNone(cleared["profile"]["experience_level"])
            shown = assert_ok(self, run_cli(home, "profile", "show"))
            self.assertEqual(shown["profile"], cleared["profile"])

    def test_transfer_requires_prior_context_and_shared_concept(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-transfer-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup"))

            unsupported = run_cli(
                home,
                "ledger",
                "record",
                "--kind",
                "transfer",
                "--summary",
                "声称完成迁移",
                "--concept",
                "retry-budget",
                "--evidence",
                "test:test_retry",
                "--outcome",
                "测试通过",
                "--context-difference",
                "从同步调用迁移到异步队列",
            )
            self.assertEqual(unsupported.returncode, 2)
            self.assertEqual(
                assert_ok(self, run_cli(home, "ledger", "review"))["total_events"],
                0,
            )

            prior = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "decision",
                    "--summary",
                    "为同步依赖设置重试预算",
                    "--concept",
                    "retry-budget",
                    "--evidence",
                    "test:test_sync_retry",
                    "--outcome",
                    "超时边界已验证",
                    "--independence",
                    "independent",
                ),
            )["event"]
            transferred = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "transfer",
                    "--summary",
                    "把重试预算迁移到异步消费者",
                    "--prior-event",
                    prior["id"],
                    "--context-difference",
                    "异步队列没有调用方超时作为天然截止点",
                    "--concept",
                    "retry-budget",
                    "--evidence",
                    "test:test_async_retry_budget",
                    "--outcome",
                    "毒消息不再无限重试",
                    "--independence",
                    "independent",
                ),
            )["event"]
            self.assertEqual(transferred["prior_event_id"], prior["id"])
            self.assertIn("demonstrated-transfer", transferred["xp"]["reasons"])
            self.assertGreater(transferred["xp"]["value"], prior["xp"]["value"])

    def test_documented_exit_codes_are_observable_through_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-runtime-") as raw:
            root = Path(raw)

            usage_home = root / "usage"
            usage = run_cli(usage_home, "mode", "definitely-not-a-mode")
            self.assertEqual(usage.returncode, 2)
            self.assertEqual(payload(usage)["error"]["code"], 2)

            operation_home = root / "operation"
            operation = run_cli(operation_home, "doctor")
            self.assertEqual(operation.returncode, 4)
            operation_payload = payload(operation)
            self.assertFalse(operation_payload["ok"])
            self.assertFalse(operation_payload["data"]["ok"])

            corrupt_home = root / "corrupt"
            assert_ok(self, run_cli(corrupt_home, "setup"))
            (corrupt_home / "profile.json").write_text(
                json.dumps({"schema_version": 999}), encoding="utf-8"
            )
            corrupt = run_cli(corrupt_home, "status")
            self.assertEqual(corrupt.returncode, 6)
            self.assertEqual(payload(corrupt)["error"]["code"], 6)

    def test_setup_refuses_a_nonempty_unmanaged_home(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-unmanaged-home-") as raw:
            home = Path(raw) / "existing-project"
            home.mkdir()
            valuable = home / "valuable.txt"
            valuable.write_text("must survive", encoding="utf-8")

            setup = run_cli(home, "setup")
            self.assertEqual(setup.returncode, 4)
            self.assertEqual(valuable.read_text(encoding="utf-8"), "must survive")
            self.assertFalse((home / "state.json").exists())

    def test_project_scan_is_read_only_skips_env_and_extracts_unittest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-project-") as raw:
            root = Path(raw)
            home = root / "data"
            project = root / "sample-project"
            (project / "src").mkdir(parents=True)
            (project / "tests").mkdir()
            (project / ".gitignore").write_text(".env\n", encoding="utf-8")
            (project / ".env").write_text("API_TOKEN=never-read\n", encoding="utf-8")
            (project / "README.md").write_text(
                "# Sample\n\n验证命令：\n\n```powershell\n"
                "python -m unittest discover -s tests\n```\n",
                encoding="utf-8",
            )
            (project / "src" / "app.py").write_text(
                "def answer():\n    return 42\n", encoding="utf-8"
            )
            (project / "tests" / "test_app.py").write_text(
                "import unittest\n", encoding="utf-8"
            )
            before = tree_fingerprint(project)
            assert_ok(self, run_cli(home, "setup"))

            scan = assert_ok(self, run_cli(home, "project", "scan", str(project)))
            self.assertTrue(scan["scan"]["read_only"])
            self.assertTrue(scan["scan"]["content_read"])
            self.assertGreaterEqual(scan["scan"]["stats"]["skipped"].get("secret", 0), 1)
            commands = [
                item["command"] for item in scan["scan"]["suggested_commands"]
            ]
            self.assertIn("python -m unittest discover -s tests", commands)
            self.assertEqual(tree_fingerprint(project), before)
            self.assertFalse((project / ".experience-loop").exists())

    def test_project_annotations_are_inspectable_and_removal_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-project-cli-") as raw:
            root = Path(raw)
            home = root / "data"
            project = root / "sample-project"
            project.mkdir()
            (project / "README.md").write_text("# Service\n", encoding="utf-8")
            assert_ok(self, run_cli(home, "setup"))
            project_id = assert_ok(
                self, run_cli(home, "project", "scan", str(project))
            )["id"]

            annotated = assert_ok(
                self,
                run_cli(
                    home,
                    "project",
                    "annotate",
                    project_id,
                    "--architecture-note",
                    "写路径拥有缓存失效责任，仍需用集成测试核验。",
                    "--learning-opportunity",
                    "练习审查跨进程一致性假设。",
                ),
            )
            self.assertTrue(annotated["annotations"]["requires_verification"])
            inspected = assert_ok(
                self, run_cli(home, "project", "inspect", project_id)
            )
            self.assertEqual(
                inspected["annotations"]["architecture_notes"],
                ["写路径拥有缓存失效责任，仍需用集成测试核验。"],
            )

            preview = assert_ok(
                self, run_cli(home, "project", "remove", project_id)
            )
            self.assertFalse(preview["removed"])
            self.assertTrue(preview["requires_confirmation"])
            self.assertEqual(
                assert_ok(self, run_cli(home, "project", "list"))["count"], 1
            )
            removed = assert_ok(
                self, run_cli(home, "project", "remove", project_id, "--yes")
            )
            self.assertTrue(removed["removed"])
            self.assertEqual(
                assert_ok(self, run_cli(home, "project", "list"))["count"], 0
            )


if __name__ == "__main__":
    unittest.main()
