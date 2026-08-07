from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Optional
import unittest


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from helpers import CLI, assert_ok, payload, run_cli, tree_fingerprint


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

            mode_help = run_cli(home, "mode", "--help")
            self.assertEqual(mode_help.returncode, 0, mode_help.stderr)
            self.assertIn("auto", mode_help.stdout)
            self.assertIn("focus", mode_help.stdout)
            self.assertIn("deep", mode_help.stdout)
            self.assertIn("off", mode_help.stdout)
            self.assertNotIn("ship", mode_help.stdout)
            self.assertNotIn("coach", mode_help.stdout)
            self.assertNotIn("incident", mode_help.stdout)

            setup_help = run_cli(home, "setup", "--help")
            self.assertEqual(setup_help.returncode, 0, setup_help.stderr)
            self.assertIn("--guidance-preference", setup_help.stdout)
            self.assertIn("--experience-context", setup_help.stdout)

            profile_help = run_cli(home, "profile", "update", "--help")
            self.assertEqual(profile_help.returncode, 0, profile_help.stderr)
            self.assertIn("--guidance-preference", profile_help.stdout)
            self.assertIn("--clear-guidance-preference", profile_help.stdout)
            self.assertIn("--experience-context", profile_help.stdout)
            self.assertIn("--clear-experience-context", profile_help.stdout)

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
                "--experience-context",
                "参与中等规模跨服务支付改造，负责方案设计、上线与故障复盘",
                "--responsibility",
                "支付链路, 发布质量",
                "--responsibility",
                "支付链路",
                "--domain",
                "支付；Unity 客户端",
                "--goal",
                "架构决策, 代码审查",
                "--goal",
                "架构决策",
                "--learning-focus",
                "测试设计；故障诊断",
                "--explanation-style",
                "先结论，再解释机制",
                "--guidance-preference",
                "高价值判断时可以短暂等待；赶工时少打断",
                "--delivery-context",
                "双周发布且兼容旧客户端",
                "--mode",
                "coach",
                "--privacy",
                "restricted",
            )
            first_data = assert_ok(self, first)
            self.assertFalse(first_data["already_initialized"])
            self.assertEqual(first_data["host_activation"], "not_evaluated")
            self.assertIn("本地状态已初始化", first_data["message"])
            self.assertNotIn("已可用", first_data["message"])
            profile = first_data["profile"]
            self.assertEqual(profile["name"], "小林")
            self.assertEqual(profile["role"], "backend-engineer")
            self.assertEqual(profile["experience_level"], "1-3 years")
            self.assertEqual(
                profile["experience_context"],
                "参与中等规模跨服务支付改造，负责方案设计、上线与故障复盘",
            )
            self.assertEqual(profile["responsibilities"], ["支付链路", "发布质量"])
            self.assertEqual(profile["domains"], ["支付", "Unity 客户端"])
            self.assertEqual(profile["goals"], ["架构决策", "代码审查"])
            self.assertEqual(profile["learning_focus"], ["测试设计", "故障诊断"])
            self.assertEqual(profile["explanation_style"], "先结论，再解释机制")
            self.assertEqual(
                profile["guidance_preference"],
                "高价值判断时可以短暂等待；赶工时少打断",
            )
            self.assertEqual(profile["delivery_context"], "双周发布且兼容旧客户端")
            self.assertEqual(profile["mode"], "focus")
            self.assertEqual(profile["privacy"], "restricted")
            self.assertTrue(profile["customized"])
            self.assertTrue((home / "state.json").is_file())
            self.assertTrue((home / "profile.json").is_file())
            self.assertTrue((home / "ledger" / "events.jsonl").is_file())
            stored_profile = json.loads(
                (home / "profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored_profile["role"], "backend-engineer")
            self.assertTrue(stored_profile["role_provided"])
            self.assertEqual(first_data["next_actions"], ["offer_short_tutorial"])
            self.assertNotIn("project", first_data)
            next_actions = " ".join(first_data["next_actions"]).lower()
            self.assertNotIn("scan", next_actions)
            self.assertNotIn("import", next_actions)
            self.assertNotIn("ingest", next_actions)

            second_data = assert_ok(self, run_cli(home, "setup"))
            self.assertTrue(second_data["already_initialized"])
            self.assertEqual(second_data["host_activation"], "not_evaluated")
            self.assertEqual(second_data["next_actions"], [])
            self.assertIn("不重复新手教学", second_data["message"])
            second_profile = second_data["profile"]
            for field in (
                "name",
                "role",
                "experience_level",
                "experience_context",
                "responsibilities",
                "domains",
                "goals",
                "learning_focus",
                "explanation_style",
                "guidance_preference",
                "delivery_context",
                "mode",
                "privacy",
                "customized",
                "created_at",
            ):
                self.assertEqual(second_profile[field], profile[field], field)

    def test_source_checkout_first_setup_requires_explicit_developer_opt_in(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-source-guard-") as raw:
            home = Path(raw) / "data"

            refused = run_cli(home, "setup", developer_source=False)
            self.assertEqual(refused.returncode, 4, refused.stdout or refused.stderr)
            envelope = payload(refused)
            self.assertFalse(envelope["ok"])
            error = envelope["error"]
            self.assertIn("仓库文件不是宿主激活", error["message"])
            self.assertEqual(
                error["details"]["developer_override"],
                "EXPERIENCE_LOOP_DEVELOPER_SOURCE=1",
            )
            self.assertEqual(
                error["details"]["host_activation"], "not_evaluated"
            )
            self.assertFalse(home.exists())

            allowed = assert_ok(self, run_cli(home, "setup"))
            self.assertEqual(allowed["host_activation"], "not_evaluated")
            self.assertTrue((home / "state.json").is_file())

    def test_four_modes_and_legacy_profiles_normalize_without_user_migration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-mode-migration-") as raw:
            home = Path(raw) / "data"
            setup = assert_ok(self, run_cli(home, "setup"))
            self.assertEqual(setup["profile"]["mode"], "auto")
            self.assertIsNone(setup["profile"]["role"])
            self.assertFalse(setup["profile"]["customized"])
            stored_profile = json.loads(
                (home / "profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored_profile["role"], "software-developer")
            self.assertFalse(stored_profile["role_provided"])

            shown = assert_ok(self, run_cli(home, "profile", "show"))["profile"]
            self.assertIsNone(shown["role"])
            self.assertNotIn("role_provided", shown)

            for mode in ("auto", "focus", "deep", "off"):
                switched = assert_ok(self, run_cli(home, "mode", mode))
                self.assertEqual(switched["mode"], mode)
                self.assertTrue(switched["persisted"])
                self.assertEqual(
                    switched["records_learning_events"], mode != "off"
                )
                self.assertEqual(
                    assert_ok(self, run_cli(home, "status"))["mode"], mode
                )

            for legacy_mode, expected in (
                ("ship", "auto"),
                ("incident", "auto"),
                ("coach", "focus"),
            ):
                switched = assert_ok(self, run_cli(home, "mode", legacy_mode))
                self.assertEqual(switched["mode"], expected)

            profile_path = home / "profile.json"
            # A genuine legacy install has no controls.json. Once controls exist,
            # profile.mode is only a compatibility mirror and cannot override it.
            (home / "controls.json").unlink()
            persisted = json.loads(profile_path.read_text(encoding="utf-8"))
            for legacy_mode, expected in (
                ("ship", "auto"),
                ("incident", "auto"),
                ("coach", "focus"),
                ("deep", "deep"),
            ):
                persisted["mode"] = legacy_mode
                profile_path.write_text(
                    json.dumps(persisted, ensure_ascii=False), encoding="utf-8"
                )
                status = assert_ok(self, run_cli(home, "status"))
                self.assertEqual(status["mode"], expected)

    def test_mode_query_is_lightweight_and_reports_persisted_controls(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-mode-query-") as raw:
            home = Path(raw) / "data"

            uninitialized = assert_ok(self, run_cli(home, "mode"))
            self.assertEqual(uninitialized["mode"], "auto")
            self.assertFalse(uninitialized["persisted"])
            self.assertFalse(uninitialized["profile_customized"])
            self.assertEqual(uninitialized["privacy"], "normal")
            self.assertFalse(home.exists())

            refused = run_cli(home, "mode", "off")
            self.assertEqual(refused.returncode, 2, refused.stdout or refused.stderr)
            self.assertFalse(home.exists())

            privacy_only = assert_ok(
                self, run_cli(home, "setup", "--privacy", "restricted")
            )
            self.assertFalse(privacy_only["profile"]["customized"])

            saved_off = assert_ok(self, run_cli(home, "mode", "off"))
            self.assertEqual(saved_off["mode"], "off")
            self.assertTrue(saved_off["persisted"])
            self.assertFalse(saved_off["records_learning_events"])
            self.assertTrue(home.exists())

            privacy_controls = assert_ok(self, run_cli(home, "mode"))
            self.assertFalse(privacy_controls["profile_customized"])
            self.assertEqual(privacy_controls["privacy"], "restricted")

            assert_ok(
                self,
                run_cli(
                    home,
                    "setup",
                    "--responsibility",
                    "支付链路",
                    "--mode",
                    "deep",
                    "--privacy",
                    "restricted",
                ),
            )
            persisted = assert_ok(self, run_cli(home, "mode"))
            self.assertEqual(persisted["mode"], "deep")
            self.assertTrue(persisted["persisted"])
            self.assertTrue(persisted["profile_customized"])
            self.assertEqual(persisted["privacy"], "restricted")
            self.assertTrue(persisted["records_learning_events"])

    def test_control_command_separates_default_mode_from_activation_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-control-cli-") as raw:
            home = Path(raw) / "data"

            defaults = assert_ok(self, run_cli(home, "control", "show"))
            self.assertEqual(defaults["default_mode"], "auto")
            self.assertEqual(defaults["activation_scope"], "explicit")
            self.assertFalse(defaults["persisted"])
            self.assertFalse(home.exists())

            refused = run_cli(
                home,
                "control",
                "set",
                "--default-mode",
                "focus",
                "--activation-scope",
                "project",
                "--privacy",
                "restricted",
            )
            self.assertEqual(refused.returncode, 2, refused.stdout or refused.stderr)
            self.assertFalse(home.exists())

            assert_ok(self, run_cli(home, "setup"))
            saved = assert_ok(
                self,
                run_cli(
                    home,
                    "control",
                    "set",
                    "--default-mode",
                    "focus",
                    "--activation-scope",
                    "project",
                    "--privacy",
                    "restricted",
                ),
            )
            self.assertEqual(saved["default_mode"], "focus")
            self.assertEqual(saved["activation_scope"], "project")
            self.assertEqual(saved["privacy"], "restricted")
            self.assertTrue(saved["preference_saved"])
            self.assertEqual(saved["host_activation"], "not_evaluated")
            self.assertEqual(
                saved["adapter"]["status"], "pending_new_session_verification"
            )
            self.assertTrue((home / "profile.json").is_file())
            self.assertTrue((home / "controls.json").is_file())

            status = assert_ok(self, run_cli(home, "status"))
            self.assertEqual(status["mode"], "focus")
            self.assertEqual(status["activation_scope"], "project")
            self.assertEqual(status["privacy"], "restricted")

            changed = assert_ok(
                self,
                run_cli(
                    home,
                    "control",
                    "set",
                    "--activation-scope",
                    "global",
                ),
            )
            self.assertEqual(changed["default_mode"], "focus")
            self.assertEqual(changed["activation_scope"], "global")

            empty_home = Path(raw) / "empty-control-data"
            rejected = run_cli(empty_home, "control", "set")
            self.assertEqual(rejected.returncode, 2, rejected.stdout)
            self.assertFalse(payload(rejected)["ok"])
            self.assertFalse(empty_home.exists())

    def test_custom_home_automatic_scope_reports_persistent_adapter_requirement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-adapter-home-") as raw:
            root = Path(raw)
            user_home = root / "user"
            custom_home = root / "custom-data"
            user_home.mkdir()

            def invoke(
                *args: str, environment_home: Optional[Path] = None
            ) -> dict[str, object]:
                env = os.environ.copy()
                env.update(
                    {
                        "HOME": str(user_home),
                        "USERPROFILE": str(user_home),
                        "HOMEDRIVE": user_home.drive,
                        "HOMEPATH": str(user_home)[len(user_home.drive) :],
                        "PYTHONUTF8": "1",
                        "EXPERIENCE_LOOP_DEVELOPER_SOURCE": "1",
                    }
                )
                if environment_home is None:
                    env.pop("EXPERIENCE_LOOP_HOME", None)
                else:
                    env["EXPERIENCE_LOOP_HOME"] = str(environment_home)
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(CLI),
                        *args,
                        "--home",
                        str(custom_home),
                        "--json",
                    ],
                    cwd=TESTS_DIR.parent,
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    check=False,
                )
                return assert_ok(self, completed)

            setup = invoke("setup", "--activation-scope", "project")
            adapter = setup["adapter"]
            self.assertIsInstance(adapter, dict)
            assert isinstance(adapter, dict)
            self.assertEqual(adapter["status"], "configuration_required")
            self.assertEqual(
                adapter["warning"]["code"],
                "automatic_routing_custom_home_not_persistent",
            )
            self.assertEqual(
                adapter["requirement"],
                {
                    "kind": "persist_environment_variable",
                    "name": "EXPERIENCE_LOOP_HOME",
                    "must_match_runtime_home": True,
                    "applies_to": ["project", "global"],
                },
            )
            self.assertFalse(adapter["explicit_invocation_affected"])
            self.assertNotIn(str(custom_home), json.dumps(adapter, ensure_ascii=False))

            shown = invoke("control", "show")
            self.assertIn("adapter", shown)
            changed = invoke(
                "control",
                "set",
                "--activation-scope",
                "global",
                environment_home=root / "different-data",
            )
            self.assertIn("adapter", changed)

            matched = invoke("control", "show", environment_home=custom_home)
            self.assertEqual(
                matched["adapter"]["status"],
                "pending_new_session_verification",
            )
            self.assertTrue(matched["adapter"]["preference_saved"])
            self.assertEqual(matched["adapter"]["hook_observed"], "unknown")
            self.assertEqual(
                matched["adapter"]["host_activation"], "not_evaluated"
            )
            explicit = invoke(
                "control", "set", "--activation-scope", "explicit"
            )
            self.assertNotIn("adapter", explicit)

    def test_stale_role_marker_is_reconciled_from_the_role_sentinel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-role-roundtrip-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup"))
            profile_path = home / "profile.json"
            stored = json.loads(profile_path.read_text(encoding="utf-8"))

            # An older runtime can change role without understanding role_provided.
            stored["role"] = "backend-engineer"
            stored["role_provided"] = False
            stored["customized"] = False
            profile_path.write_text(
                json.dumps(stored, ensure_ascii=False), encoding="utf-8"
            )
            controls = assert_ok(self, run_cli(home, "mode"))
            self.assertFalse(controls["profile_customized"])
            shown = assert_ok(self, run_cli(home, "profile", "show"))["profile"]
            self.assertEqual(shown["role"], "backend-engineer")
            self.assertTrue(shown["customized"])
            assert_ok(self, run_cli(home, "profile", "update"))
            self.assertTrue(
                assert_ok(self, run_cli(home, "mode"))["profile_customized"]
            )

            # Sentinel priority also reconciles an older reset that leaves true.
            stored["role"] = "software-developer"
            stored["role_provided"] = True
            stored["customized"] = True
            profile_path.write_text(
                json.dumps(stored, ensure_ascii=False), encoding="utf-8"
            )
            controls = assert_ok(self, run_cli(home, "mode"))
            self.assertTrue(controls["profile_customized"])
            shown = assert_ok(self, run_cli(home, "profile", "show"))["profile"]
            self.assertIsNone(shown["role"])
            self.assertFalse(shown["customized"])
            assert_ok(self, run_cli(home, "profile", "update"))
            self.assertFalse(
                assert_ok(self, run_cli(home, "mode"))["profile_customized"]
            )

    def test_mode_off_ignores_unrelated_profile_content_corruption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-mode-corrupt-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup"))
            profile_path = home / "profile.json"
            damaged = json.loads(profile_path.read_text(encoding="utf-8"))
            damaged["responsibilities"] = [{"unexpected": "object"}]
            damaged["customized"] = False
            profile_path.write_text(
                json.dumps(damaged, ensure_ascii=False), encoding="utf-8"
            )

            switched = assert_ok(self, run_cli(home, "mode", "off"))
            self.assertEqual(switched["mode"], "off")
            self.assertTrue(switched["profile_customized"])
            queried = assert_ok(self, run_cli(home, "mode"))
            self.assertEqual(queried["mode"], "off")
            self.assertTrue(queried["profile_customized"])

            invalid_profile = run_cli(home, "profile", "show")
            self.assertEqual(invalid_profile.returncode, 6)
            self.assertEqual(payload(invalid_profile)["error"]["code"], 6)

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

    def test_ledger_uses_task_resolved_mode_before_the_persisted_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-ledger-mode-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup", "--mode", "off"))

            recorded = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "decision",
                    "--summary",
                    "task-scoped deep decision",
                    "--resolved-mode",
                    "deep",
                ),
            )
            self.assertTrue(recorded["recorded"])
            self.assertEqual(recorded["event"]["mode"], "deep")

            ledger = home / "ledger" / "events.jsonl"
            before = ledger.read_bytes()
            skipped = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "decision",
                    "--summary",
                    "task-scoped delivery only",
                    "--resolved-mode",
                    "off",
                ),
            )
            self.assertFalse(skipped["recorded"])
            self.assertEqual(skipped["reason"], "mode_off")
            self.assertEqual(ledger.read_bytes(), before)

    def test_off_short_circuits_transfer_validation_and_prior_ledger_reads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-ledger-off-transfer-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup", "--mode", "off"))
            ledger = home / "ledger" / "events.jsonl"
            ledger.write_text("{broken-ledger\n", encoding="utf-8")
            before = ledger.read_bytes()

            saved_off = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "transfer",
                    "--summary",
                    "must be ignored before transfer validation",
                ),
            )
            self.assertFalse(saved_off["recorded"])
            self.assertEqual(saved_off["reason"], "mode_off")

            saved_off_without_history_read = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "transfer",
                    "--summary",
                    "saved off must not read prior ledger",
                    "--prior-event",
                    "evt_missing",
                    "--context-difference",
                    "new context",
                    "--concept",
                    "retry-budget",
                    "--evidence",
                    "test:test_retry",
                    "--outcome",
                    "verified",
                ),
            )
            self.assertFalse(saved_off_without_history_read["recorded"])
            self.assertEqual(saved_off_without_history_read["reason"], "mode_off")

            assert_ok(self, run_cli(home, "mode", "auto"))
            task_off = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "transfer",
                    "--summary",
                    "must not read prior ledger",
                    "--prior-event",
                    "evt_missing",
                    "--context-difference",
                    "new context",
                    "--concept",
                    "retry-budget",
                    "--evidence",
                    "test:test_retry",
                    "--outcome",
                    "verified",
                    "--resolved-mode",
                    "off",
                ),
            )
            self.assertFalse(task_off["recorded"])
            self.assertEqual(task_off["reason"], "mode_off")
            self.assertEqual(ledger.read_bytes(), before)

    def test_ledger_groups_evidence_by_capability_without_scoring_gaps(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-capability-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup"))
            assert_ok(self, run_cli(home, "mode", "deep"))
            recorded = assert_ok(
                self,
                run_cli(
                    home,
                    "ledger",
                    "record",
                    "--kind",
                    "verification",
                    "--summary",
                    "确认重试边界由失败路径测试覆盖",
                    "--capability",
                    "verification",
                    "--independence",
                    "independent",
                    "--evidence",
                    "python -m unittest tests.test_retry",
                ),
            )
            self.assertEqual(recorded["event"]["mode"], "deep")

            review = assert_ok(self, run_cli(home, "ledger", "review"))
            self.assertEqual(review["events"][0]["mode"], "deep")
            self.assertEqual(
                review["capability_evidence"],
                [
                    {
                        "capability": "verification",
                        "events": 1,
                        "evidence_events": 1,
                        "independent_events": 1,
                        "correction_events": 0,
                        "transfer_events": 0,
                        "latest_timestamp": review["events"][0]["timestamp"],
                    }
                ],
            )
            self.assertNotIn("weakest", review)

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
                    "--responsibility",
                    "旧责任",
                    "--domain",
                    "旧领域",
                    "--goal",
                    "旧目标, 保留目标",
                    "--learning-focus",
                    "旧方向",
                    "--explanation-style",
                    "旧解释偏好",
                    "--guidance-preference",
                    "旧指导偏好",
                    "--delivery-context",
                    "旧交付场景",
                ),
            )

            updated = assert_ok(
                self,
                run_cli(
                    home,
                    "profile",
                    "update",
                    "--clear-name",
                    "--responsibility",
                    "支付链路, 发布质量",
                    "--replace-responsibilities",
                    "--domain",
                    "支付, 游戏客户端",
                    "--replace-domains",
                    "--goal",
                    "架构决策",
                    "--replace-goals",
                    "--learning-focus",
                    "代码审查, 故障诊断",
                    "--replace-learning-focus",
                    "--experience-level",
                    "2 years",
                    "--experience-context",
                    "做过高可靠性订单链路改造，承担边界设计和灰度验收",
                    "--explanation-style",
                    "先给结论，再解释失效条件",
                    "--guidance-preference",
                    "关键判断可以先等我回答",
                    "--delivery-context",
                    "每周发布，必须兼容旧客户端",
                ),
            )
            profile = updated["profile"]
            self.assertIsNone(profile["name"])
            self.assertEqual(profile["responsibilities"], ["支付链路", "发布质量"])
            self.assertEqual(profile["domains"], ["支付", "游戏客户端"])
            self.assertEqual(profile["goals"], ["架构决策"])
            self.assertEqual(profile["learning_focus"], ["代码审查", "故障诊断"])
            self.assertEqual(profile["experience_level"], "2 years")
            self.assertEqual(
                profile["experience_context"],
                "做过高可靠性订单链路改造，承担边界设计和灰度验收",
            )
            self.assertEqual(
                profile["explanation_style"], "先给结论，再解释失效条件"
            )
            self.assertEqual(
                profile["guidance_preference"], "关键判断可以先等我回答"
            )
            self.assertEqual(
                profile["delivery_context"], "每周发布，必须兼容旧客户端"
            )

            cleared = assert_ok(
                self,
                run_cli(
                    home,
                    "profile",
                    "update",
                    "--clear-responsibilities",
                    "--clear-domains",
                    "--clear-goals",
                    "--clear-learning-focus",
                    "--clear-experience-level",
                    "--clear-experience-context",
                    "--clear-explanation-style",
                    "--clear-guidance-preference",
                    "--clear-delivery-context",
                ),
            )
            self.assertEqual(cleared["profile"]["responsibilities"], [])
            self.assertEqual(cleared["profile"]["domains"], [])
            self.assertEqual(cleared["profile"]["goals"], [])
            self.assertEqual(cleared["profile"]["learning_focus"], [])
            self.assertIsNone(cleared["profile"]["experience_level"])
            self.assertIsNone(cleared["profile"]["experience_context"])
            self.assertIsNone(cleared["profile"]["explanation_style"])
            self.assertIsNone(cleared["profile"]["guidance_preference"])
            self.assertIsNone(cleared["profile"]["delivery_context"])
            shown = assert_ok(self, run_cli(home, "profile", "show"))
            self.assertEqual(shown["profile"], cleared["profile"])

    def test_profile_rejects_clear_plus_new_values_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-profile-conflict-") as raw:
            home = Path(raw) / "data"
            initial = assert_ok(
                self,
                run_cli(
                    home,
                    "setup",
                    "--responsibility",
                    "旧责任",
                    "--domain",
                    "旧领域",
                    "--goal",
                    "旧目标",
                    "--learning-focus",
                    "旧方向",
                ),
            )["profile"]

            conflicts = (
                ("--clear-responsibilities", "--responsibility", "新责任"),
                ("--clear-domains", "--domain", "新领域"),
                ("--clear-goals", "--goal", "新目标"),
                ("--clear-learning-focus", "--learning-focus", "新方向"),
                (
                    "--clear-experience-context",
                    "--experience-context",
                    "新的代表性项目经验",
                ),
                (
                    "--clear-guidance-preference",
                    "--guidance-preference",
                    "关键节点先让我判断",
                ),
            )
            for clear_flag, value_flag, value in conflicts:
                failed = run_cli(
                    home, "profile", "update", clear_flag, value_flag, value
                )
                self.assertEqual(failed.returncode, 2, failed.stderr)
                self.assertEqual(payload(failed)["error"]["code"], 2)

            shown = assert_ok(self, run_cli(home, "profile", "show"))["profile"]
            for field in (
                "responsibilities",
                "domains",
                "goals",
                "learning_focus",
                "experience_context",
                "customized",
                "updated_at",
            ):
                self.assertEqual(shown[field], initial[field], field)

    def test_legacy_profile_backfills_optional_personalization_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-profile-backfill-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup"))
            profile_path = home / "profile.json"
            legacy = json.loads(profile_path.read_text(encoding="utf-8"))
            added_fields = (
                "responsibilities",
                "domains",
                "experience_context",
                "explanation_style",
                "guidance_preference",
                "delivery_context",
            )
            for field in added_fields:
                legacy.pop(field, None)
            profile_path.write_text(
                json.dumps(legacy, ensure_ascii=False), encoding="utf-8"
            )

            shown = assert_ok(self, run_cli(home, "profile", "show"))["profile"]
            self.assertEqual(shown["responsibilities"], [])
            self.assertEqual(shown["domains"], [])
            self.assertIsNone(shown["experience_context"])
            self.assertIsNone(shown["explanation_style"])
            self.assertIsNone(shown["guidance_preference"])
            self.assertIsNone(shown["delivery_context"])

            setup = assert_ok(self, run_cli(home, "setup"))
            self.assertTrue(setup["already_initialized"])
            materialized = json.loads(profile_path.read_text(encoding="utf-8"))
            for field in added_fields:
                self.assertIn(field, materialized)

    def test_profile_validates_array_elements_and_recomputes_customized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-profile-types-") as raw:
            home = Path(raw) / "data"
            assert_ok(self, run_cli(home, "setup", "--privacy", "restricted"))
            profile_path = home / "profile.json"
            persisted = json.loads(profile_path.read_text(encoding="utf-8"))
            persisted["responsibilities"] = ["支付链路"]
            persisted["customized"] = False
            profile_path.write_text(
                json.dumps(persisted, ensure_ascii=False), encoding="utf-8"
            )

            shown = assert_ok(self, run_cli(home, "profile", "show"))["profile"]
            self.assertTrue(shown["customized"])
            controls = assert_ok(self, run_cli(home, "mode"))
            self.assertFalse(controls["profile_customized"])
            assert_ok(self, run_cli(home, "profile", "update"))
            controls = assert_ok(self, run_cli(home, "mode"))
            self.assertTrue(controls["profile_customized"])

            persisted["guidance_preference"] = ["unexpected"]
            profile_path.write_text(
                json.dumps(persisted, ensure_ascii=False), encoding="utf-8"
            )
            invalid_guidance = run_cli(home, "profile", "show")
            self.assertEqual(invalid_guidance.returncode, 6)
            self.assertEqual(payload(invalid_guidance)["error"]["code"], 6)

            persisted["guidance_preference"] = None
            persisted["responsibilities"] = ["支付链路", 7]
            profile_path.write_text(
                json.dumps(persisted, ensure_ascii=False), encoding="utf-8"
            )
            invalid = run_cli(home, "profile", "show")
            self.assertEqual(invalid.returncode, 6)
            self.assertEqual(payload(invalid)["error"]["code"], 6)

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
