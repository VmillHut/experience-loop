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

        self.assertIn("## 安装方式", readme)
        self.assertIn("docs/AI_INSTALL.md", readme)
        install_prompt = (
            "请根据 https://github.com/VmillHut/experience-loop 安装并初始化 "
            "`experience-loop` Skill；仓库特有的安全与验收要求见 "
            "`docs/AI_INSTALL.md`。"
        )
        self.assertEqual(readme.count(install_prompt), 1)
        self.assertIn("references/onboarding.md", readme)
        self.assertIn("平台兼容边界", readme)
        self.assertIn("不把今天的宿主路径或调用语法写死", readme)
        self.assertIn("三段证据", readme)
        self.assertNotIn("~/.claude/skills", readme)
        self.assertIn("自动检测 + 智能决策", readme)
        self.assertIn("Agent 自动检测并基于当前证据智能决策", readme)
        self.assertIn("能力单调", readme)
        self.assertIn("宿主 Agent 更新后出现更强能力时，优先使用更强能力", readme)
        self.assertIn("不是限制未来 Agent 的固定清单", readme)
        self.assertIn("必答判断检查点", readme)
        self.assertIn("短训练循环", readme)
        self.assertIn("没有“0 个必答学习问题”的预设", readme)
        self.assertIn("没有“最多 N 个可跳过检查点”的固定上限", readme)
        self.assertIn("不会只判“对/错”或顺着你的结论说", readme)
        self.assertIn("提炼可迁移的判断规则", readme)
        self.assertIn("决策后复盘并不是 `deep` 独占", readme)
        self.assertIn("大致从业年限或经验阶段", readme)
        self.assertIn("代表性项目的大致规模、复杂度和本人实际承担部分", readme)
        self.assertIn("不是能力证明", readme)
        for mode in ("auto", "focus", "deep", "off"):
            self.assertIn(f"| `{mode}` |", readme)
            self.assertIn(f"| `{mode}` |", readme_en)

        self.assertIn("## Installation", readme_en)
        self.assertIn("docs/AI_INSTALL.en.md", readme_en)
        self.assertIn("Platform compatibility boundary", readme_en)
        self.assertIn("does not freeze today's host paths", readme_en)
        self.assertIn("three separate pieces of evidence", readme_en)
        self.assertIn("automatic detection + intelligent decisions", readme_en)
        self.assertIn("detects automatically and decides intelligently", readme_en)
        self.assertIn("capability monotonicity", readme_en)
        self.assertIn("stronger capabilities from future host updates take precedence", readme_en)
        self.assertIn("rather than a fixed ceiling on future Agents", readme_en)
        self.assertIn("required judgment checkpoint", readme_en.lower())
        self.assertIn("short guided practice loop", readme_en.lower())
        self.assertIn("highest expected net user value", readme_en)
        self.assertIn("does not merely mark it right or wrong", readme_en)
        self.assertIn("extracts a transferable decision rule", readme_en)
        self.assertIn("Decision debriefs are not exclusive to `deep`", readme_en)
        self.assertIn("approximate years or experience stage", readme_en)
        self.assertIn("representative projects and what you actually owned", readme_en)
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
        self.assertIn("所有写入必须使用仓库安装器", install_zh)
        self.assertIn("--dry-run --json", install_zh)
        self.assertIn("完全相同的契约", install_zh)
        self.assertIn("不要用静默降级伪造成功", install_zh)
        self.assertIn("rollback_available", install_zh)
        self.assertIn("rollback_note", install_zh)
        self.assertIn("Every field is optional", install_en)
        self.assertIn("does not also authorize", install_en.lower())
        self.assertIn("rollback_note", install_en)
        self.assertIn("actual discovery or invocation", install_en)
        self.assertIn("Never remove profiles", install_en)
        self.assertIn("Do not hand host-directory", install_en)
        self.assertIn("exactly one currently necessary `next_action`", install_en)
        self.assertIn("every write must use the bundled installer", install_en)
        self.assertIn("identical contract", install_en)

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
