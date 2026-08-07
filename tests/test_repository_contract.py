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
        self.assertLessEqual(len(skill.splitlines()), 160)
        self.assertLessEqual(len(skill), 13500)
        self.assertIn("| `auto` |", skill)
        self.assertIn("| `focus` |", skill)
        self.assertIn("| `deep` |", skill)
        self.assertIn("| `off` |", skill)
        mode_rows = {
            mode: next(
                line
                for line in skill.splitlines()
                if line.startswith("| `{0}` |".format(mode))
            )
            for mode in ("auto", "focus", "deep", "off")
        }
        self.assertIn("Automatically detects task risks", mode_rows["auto"])
        self.assertIn("intelligently chooses", mode_rows["auto"])
        self.assertIn("full local intensity", mode_rows["auto"])
        self.assertIn("no fixed answer quota", mode_rows["auto"])
        self.assertIn("without content-bearing profile use", mode_rows["off"])
        self.assertIn("learning references, checkpoints", mode_rows["off"])
        self.assertIn("learning summaries, or ledger writes", mode_rows["off"])
        self.assertIn("Proactively uses meaningful task seams", mode_rows["deep"])
        self.assertIn("make the user frame, predict, decide, and audit", mode_rows["deep"])
        self.assertIn("Methods and rounds adapt to value", mode_rows["deep"])
        self.assertIn(
            "Preserve capability monotonicity",
            skill,
        )
        self.assertIn("never replace or narrow the host's planning", skill)
        self.assertIn("Use stronger current host capabilities", skill)
        self.assertIn("Detect first, decide intelligently", skill)
        self.assertIn("no learning addition", skill)
        self.assertIn("never as the starting assumption", skill)
        self.assertIn("Common non-exhaustive examples", skill)
        self.assertIn("use a stronger current-host interaction", skill)
        self.assertIn("There is no default strength and no fixed answer quota", skill)
        self.assertNotIn("requires 0 mandatory learning answers", skill.lower())
        self.assertNotIn("at most two skippable checkpoints", skill.lower())
        self.assertNotIn("at most 2 skippable checkpoints", skill.lower())
        for forbidden_quota in (
            "at most one high-value",
            "select at most one",
            "at most one reusable insight",
            "one or two purposeful checkpoints",
            "two to four purposeful checkpoints",
            "one acceptance gate",
        ):
            self.assertNotIn(forbidden_quota, skill.lower())
        self.assertIn("not a global per-task quota", skill)
        self.assertIn("do not impose a universal question count", skill)
        self.assertIn("Inspect only what the change makes relevant", skill)
        self.assertIn("Surface every material finding needed for task quality", skill)
        self.assertIn("## Resolve only state that can improve the task", skill)
        self.assertIn("Do not run `status` or `doctor` routinely", skill)
        self.assertIn(
            "If the lightweight result says a profile is customized", skill
        )
        self.assertIn("from task evidence alone", skill)
        self.assertIn("may affect only the learning-layer choice", skill)
        self.assertIn("only after the task-quality plan is intact", skill)
        self.assertIn("It must not change implementation, tool selection", skill)
        self.assertIn("Ordinary `auto` runs the detector and controller above", skill)
        self.assertIn("references/capability-compass.md", skill)
        self.assertTrue((ROOT / "references" / "capability-compass.md").is_file())
        self.assertIn("references/host-compatibility.md", skill)
        workflow = (ROOT / "references" / "workflow.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("boundary-condition behavior", workflow)
        self.assertIn("interleaving or race-focused tests", workflow)
        self.assertIn("load, spike, soak, or saturation tests", workflow)
        self.assertIn("non-exhaustive examples", workflow)
        self.assertIn("not an alternative task workflow", workflow)
        self.assertIn("use stronger current tools when available", workflow)
        self.assertIn("do not impose a fixed count", workflow)
        self.assertNotIn("ask one blocking question", workflow)
        self.assertNotIn("shared acceptance gate", workflow)
        self.assertIn("explicit acceptance responsibilities", workflow)
        self.assertIn("adaptive dialogic practice contract", workflow)
        self.assertIn("no preset minimum, maximum, or default round count", workflow)
        self.assertIn("Completing a teaching sequence is not an outcome", workflow)
        self.assertIn("Choose, merge, reorder, repeat, or skip", workflow)
        self.assertIn("task-scoped authorization for strong capability practice", workflow)
        self.assertIn("Proactivity applies only to the learning overlay", workflow)
        self.assertIn("real review pass over the Agent's proposal", workflow)
        self.assertIn("Use progressive scaffolding", workflow)
        self.assertIn("smallest coherent question set", workflow)
        self.assertIn("does not mean exposing every possible seam at once", workflow)
        self.assertIn("Do not announce a fixed syllabus", workflow)
        self.assertIn("not a round count, verbosity, or completed recipe", workflow)
        self.assertIn("misses the purpose of `deep`", workflow)
        self.assertIn("strongest current or future host interactions", workflow)
        self.assertIn("Decision debrief and internalization", workflow)
        self.assertIn("Reconstruct the user's reasoning", workflow)
        self.assertIn("Separate decision quality from eventual outcome", workflow)
        self.assertIn("Distinguish facts, inferences, and unknowns", workflow)
        self.assertIn("Agent's independent recommendation", workflow)
        self.assertIn("not an exhaustive scorecard", workflow)
        self.assertIn("available in both `auto` and `deep`", workflow)
        self.assertIn("intelligently chooses its timing and depth", workflow)
        self.assertIn("proactively looks for and pursues high-value debrief seams", workflow)
        compatibility = (ROOT / "references" / "host-compatibility.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("must not remove or rewrite", compatibility)
        self.assertIn("File installation alone is not host support", compatibility)
        self.assertIn("must not freeze today's directory", compatibility)
        self.assertNotIn("~/.claude/skills", compatibility)
        self.assertNotIn("~/.agents/skills", compatibility)
        profiles = (ROOT / "references" / "setup-and-profiles.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("representative project scale, complexity, and actual ownership", profiles)
        self.assertIn("calibration context, not capability evidence", profiles)
        self.assertIn("Prefer what the user actually owned", profiles)

    def test_readmes_define_ai_first_installation_and_all_four_modes(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_en = (ROOT / "README.en.md").read_text(encoding="utf-8")

        self.assertIn("安装：把仓库交给 AI", readme)
        self.assertIn("docs/AI_INSTALL.md", readme)
        install_prompt = (
            "请根据 https://github.com/VmillHut/experience-loop 完成安装并初始化 "
            "`experience-loop` Skill：优先使用当前宿主原生安装管理器；若某个命令、"
            "目录或方式受限，请在现有权限内按 `docs/AI_INSTALL.md` 自动继续下一条安全路线，"
            "直到完成文件、运行时和宿主发现验收，或确认所有可行路线都不可用。"
        )
        self.assertEqual(readme.count(install_prompt), 1)
        self.assertIn("宿主原生安装管理器", readme)
        self.assertIn("scripts/install.py --verify-only", readme)
        self.assertIn("单一路径失败不等于安装失败", readme)
        self.assertIn("未提交且未改动目标的失败尝试不产生安装所有权", readme)
        self.assertIn("Git URL 本身不是安全安装协议", readme)
        self.assertNotIn('<img src="http', readme)
        self.assertNotIn("img.shields.io", readme)
        self.assertGreaterEqual(readme.count('loading="lazy"'), 3)
        self.assertIn("references/onboarding.md", readme)
        self.assertIn("平台兼容、安全边界与升级行为", readme)
        self.assertIn("不会把今天的宿主路径或调用语法写死", readme)
        self.assertIn("文件、运行时、宿主发现三段独立证据", readme)
        self.assertNotIn("~/.claude/skills", readme)
        self.assertIn("先自动检测，再智能决策", readme)
        self.assertIn("Agent 根据当前证据持续决定", readme)
        self.assertIn("任务能力只能保持或增强", readme)
        self.assertIn("宿主 Agent 有更强能力时，优先使用更强能力", readme)
        self.assertIn("不是限制未来 Agent 的固定清单", readme)
        self.assertIn("没有固定问题数、检查点数或解释强度", readme)
        self.assertIn("短训练循环", readme)
        self.assertIn("而不是只判「对/错」、固定打分或顺着你的结论附和", readme)
        self.assertIn("提炼可迁移的判断规则", readme)
        self.assertIn("这项复盘不属于 `deep` 专享", readme)
        self.assertIn("岗位、年限和项目规模", readme)
        self.assertIn("不是能力证明", readme)
        for mode in ("auto", "focus", "deep", "off"):
            self.assertIn(f"<code>{mode}</code>", readme)
            self.assertIn(f"<code>{mode}</code>", readme_en)

        self.assertIn("Installation: hand the repository to AI", readme_en)
        self.assertIn("docs/AI_INSTALL.en.md", readme_en)
        self.assertIn("Host compatibility, safety boundaries, and upgrades", readme_en)
        self.assertIn("never freezes today's host paths", readme_en)
        self.assertIn("filesystem, runtime, and actual host discovery", readme_en)
        self.assertIn("host-native install manager", readme_en)
        self.assertIn("scripts/install.py --verify-only", readme_en)
        self.assertIn("One failed route is not an installation failure", readme_en)
        self.assertIn(
            "uncommitted failed attempt that left the target unchanged acquires no ownership",
            readme_en,
        )
        self.assertIn("A Git URL is not itself a safe installation protocol", readme_en)
        self.assertNotIn('<img src="http', readme_en)
        self.assertNotIn("img.shields.io", readme_en)
        self.assertGreaterEqual(readme_en.count('loading="lazy"'), 3)
        self.assertIn("Detect automatically, decide intelligently", readme_en)
        self.assertIn("The Agent continuously decides from current evidence", readme_en)
        self.assertIn("task capability can only stay the same or improve", readme_en)
        self.assertIn("Stronger host capabilities always take precedence", readme_en)
        self.assertIn("not a fixed ceiling on future Agents", readme_en)
        self.assertIn("no fixed question count, checkpoint count", readme_en.lower())
        self.assertIn("short practice loop", readme_en.lower())
        self.assertIn("highest expected net value", readme_en)
        self.assertIn("instead of merely marking the decision right or wrong", readme_en)
        self.assertIn("distills a transferable judgment rule", readme_en)
        self.assertIn("This debrief is not exclusive to `deep`", readme_en)
        self.assertIn("Title, years, and project scale", readme_en)
        self.assertIn("not proof of capability", readme_en)
        self.assertNotIn("requires zero mandatory learning answers", readme_en.lower())
        self.assertNotIn("at most two skippable checkpoints", readme_en.lower())

    def test_ai_install_and_onboarding_protocols_keep_installation_low_cost(self) -> None:
        install_zh_path = ROOT / "docs" / "AI_INSTALL.md"
        install_en_path = ROOT / "docs" / "AI_INSTALL.en.md"
        onboarding_path = ROOT / "references" / "onboarding.md"
        self.assertTrue(install_zh_path.is_file())
        self.assertTrue(install_en_path.is_file())
        self.assertTrue(onboarding_path.is_file())

        install_zh = install_zh_path.read_text(encoding="utf-8")
        install_en = install_en_path.read_text(encoding="utf-8")
        onboarding = onboarding_path.read_text(encoding="utf-8")

        for protocol in (install_zh, install_en):
            self.assertIn("--force", protocol)
            self.assertIn("scripts/install.py --help", protocol)
            self.assertIn("doctor", protocol)
            self.assertIn("status", protocol)
            self.assertIn("onboarding", protocol.lower())
            self.assertNotIn("~/.agents/skills", protocol)
            self.assertNotIn("~/.claude/skills", protocol)
            self.assertNotIn("copilot-cli", protocol.lower())

        self.assertLessEqual(len(install_zh.splitlines()), 75)
        self.assertLessEqual(len(install_en.splitlines()), 75)

        self.assertIn("不扫描项目、不读取资料", install_zh)
        self.assertIn("所有字段都可选", install_zh)
        self.assertIn("不要把宿主目录、安装参数或刷新方式转交给用户选择", install_zh)
        self.assertIn("最终只给一个当前必要的 `next_action`", install_zh)
        self.assertIn("宿主原生管理优先", install_zh)
        self.assertIn("单一路径失败不等于安装失败", install_zh)
        self.assertIn("未提交且未改动目标的失败尝试不产生所有权", install_zh)
        self.assertIn("只清理能证明由本次尝试创建的临时产物", install_zh)
        self.assertIn("安全路线全部不适用", install_zh)
        self.assertIn("--verify-only --json", install_zh)
        self.assertIn("一个目标只有一个所有者", install_zh)
        self.assertIn("transaction_capability", install_zh)
        self.assertIn("--replace-discovery-roots", install_zh)
        self.assertIn("新的 `--host-evidence`", install_zh)
        self.assertIn("--dry-run --json", install_zh)
        self.assertIn("完全相同的目标", install_zh)
        self.assertIn("不要用静默降级伪造成功", install_zh)
        self.assertIn("rollback_available", install_zh)
        self.assertIn("rollback_note", install_zh)
        self.assertIn("Every field is optional", install_en)
        self.assertIn("does not also authorize", install_en.lower())
        self.assertIn("rollback_note", install_en)
        self.assertIn("real list, invocation, or new-session mechanism", install_en)
        self.assertIn("Never remove profiles", install_en)
        self.assertIn("Do not hand host-directory", install_en)
        self.assertIn("exactly one currently necessary `next_action`", install_en)
        self.assertIn("Prefer the host-native manager", install_en)
        self.assertIn("One failed route is not an installation failure", install_en)
        self.assertIn(
            "An uncommitted attempt that left the target unchanged owns nothing",
            install_en,
        )
        self.assertIn("temporary artifacts proven to belong to this attempt", install_en)
        self.assertIn("all safe routes are inapplicable", install_en)
        self.assertIn("--verify-only --json", install_en)
        self.assertIn("One target has one owner", install_en)
        self.assertIn("identical target", install_en)
        self.assertIn("--replace-discovery-roots", install_en)
        self.assertIn("fresh `--host-evidence`", install_en)

        installer = (ROOT / "scripts" / "install.py").read_text(encoding="utf-8")
        for stale_host_fact in (
            "CODEX_HOME",
            "~/.agents/skills",
            "~/.claude/skills",
            "copilot-cli",
        ):
            self.assertNotIn(stale_host_fact, installer)
        self.assertIn("--host-evidence", installer)
        self.assertIn("--discovery-root", installer)
        self.assertIn("discovery_roots_coverage", installer)

        router = (ROOT / "scripts" / "global_router.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('choices=("markdown",)', router)
        self.assertIn("--expected-sha256", router)
        self.assertIn("Multiple Experience Loop router blocks", router)
        self.assertIn("native planning, tools, engineering coverage", router)
        self.assertIn("detect and decide instead of duplicating", router)
        for duplicated_controller_detail in (
            "optional checkpoint",
            "required judgment checkpoint",
            "short guided practice loop",
            "consequence, uncertainty",
        ):
            self.assertNotIn(duplicated_controller_detail, router)

        self.assertIn("全部跳过", onboarding)
        self.assertIn("guidance_preference", onboarding)
        self.assertIn("Do not scan a project", onboarding)
        self.assertIn("Do not scan a project, ingest a document", onboarding)
        self.assertIn("约 2 分钟的对话式使用教学", onboarding)
        self.assertIn("自动检测任务风险和能力机会", onboarding)
        self.assertIn("大致从业年限或经验阶段", onboarding)
        self.assertIn("experience_context", onboarding)
        self.assertIn("不需要写简历", onboarding)
        self.assertIn("重点是你实际承担了什么", onboarding)
        self.assertIn("receipt commands do not remember a one-off `--home`", onboarding)
        self.assertIn("required judgment", onboarding)
        self.assertIn("short guided", onboarding)
        for mode in ("auto", "focus", "deep", "off"):
            self.assertIn(f"| `{mode}` |", onboarding)

    def test_openai_metadata_is_utf8_and_invokes_the_skill(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertNotIn("�", metadata)
        self.assertIn('display_name: "Experience Loop"', metadata)
        self.assertIn("$experience-loop", metadata)
        self.assertIn("allow_implicit_invocation: true", metadata)
        self.assertIn("native planning, tools, engineering coverage", metadata)
        self.assertIn("detect and decide instead of duplicating", metadata)
        for duplicated_controller_detail in (
            "optional checkpoint",
            "required judgment checkpoint",
            "short guided practice loop",
            "consequence, uncertainty",
        ):
            self.assertNotIn(duplicated_controller_detail, metadata)

    def test_deep_evaluation_includes_a_narrow_compactness_probe(self) -> None:
        evaluation = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
        report_path = (
            ROOT / "evals" / "2026-08-06-deep-mode-experience-report.md"
        )
        self.assertTrue(report_path.is_file())
        report = report_path.read_text(encoding="utf-8")

        self.assertIn("## Deep compactness probe", evaluation)
        self.assertIn("at least one narrow task", evaluation)
        self.assertIn("Do not tell the evaluator to be concise", evaluation)
        self.assertIn("smallest useful sequence of dependent exchanges", evaluation)
        self.assertIn("long explanation", evaluation)
        self.assertIn("continues asking after another exchange", evaluation)
        self.assertIn("strict narrow compactness probe", report)
        self.assertIn("one 30-second checkpoint", report)
        self.assertIn("It asked no further questions", report)

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
