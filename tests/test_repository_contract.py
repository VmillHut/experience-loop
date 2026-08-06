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
        self.assertLessEqual(len(skill), 15000)
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
        self.assertIn("silence, embedded guidance", mode_rows["auto"])
        self.assertIn("required judgment checkpoint", mode_rows["auto"])
        self.assertIn("short guided practice loop", mode_rows["auto"])
        self.assertIn("No fixed answer quota", mode_rows["auto"])
        self.assertIn("never creates a standing `focus` or `deep`", mode_rows["auto"])
        self.assertIn("no content-bearing profile use", mode_rows["off"])
        self.assertIn("learning references, checkpoints", mode_rows["off"])
        self.assertIn("learning summaries, or ledger writes", mode_rows["off"])
        self.assertIn("minimal mode/privacy control read", mode_rows["off"])
        self.assertIn("honor a previously saved `off`", mode_rows["off"])
        self.assertIn("`auto` is not a synonym for low intervention", skill)
        self.assertIn("Choose the highest expected net user value", skill)
        self.assertNotIn("requires 0 mandatory learning answers", skill.lower())
        self.assertNotIn("at most two skippable checkpoints", skill.lower())
        self.assertNotIn("at most 2 skippable checkpoints", skill.lower())
        self.assertIn(
            "Let one selected capability limit only learning intervention and ledger labeling.",
            skill,
        )
        self.assertIn(
            "It must never limit the engineering concerns inspected.", skill
        )
        self.assertIn("## Resolve only state that changes the task", skill)
        self.assertIn("Do not run `status` or `doctor` routinely", skill)
        self.assertIn(
            "Load a saved profile only when it is customized and can change", skill
        )
        self.assertIn(
            "Never consume content-bearing profile fields on the fast path or in `off`.",
            skill,
        )
        self.assertIn("Ordinary `auto` work should not need it.", skill)
        self.assertIn("references/capability-compass.md", skill)
        self.assertTrue((ROOT / "references" / "capability-compass.md").is_file())
        self.assertIn("references/host-compatibility.md", skill)
        compatibility = (ROOT / "references" / "host-compatibility.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("must not remove or rewrite", compatibility)
        self.assertIn("File installation alone is not host support", compatibility)
        self.assertIn("must not freeze today's directory", compatibility)
        self.assertNotIn("~/.claude/skills", compatibility)
        self.assertNotIn("~/.agents/skills", compatibility)

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
        self.assertIn("`auto` 不是弱模式", readme)
        self.assertIn("必答判断检查点", readme)
        self.assertIn("短训练循环", readme)
        self.assertIn("没有“0 个必答学习问题”的预设", readme)
        self.assertIn("没有“最多 N 个可跳过检查点”的固定上限", readme)
        for mode in ("auto", "focus", "deep", "off"):
            self.assertIn(f"| `{mode}` |", readme)
            self.assertIn(f"| `{mode}` |", readme_en)

        self.assertIn("## Installation", readme_en)
        self.assertIn("docs/AI_INSTALL.en.md", readme_en)
        self.assertIn("Platform compatibility boundary", readme_en)
        self.assertIn("does not freeze today's host paths", readme_en)
        self.assertIn("three separate pieces of evidence", readme_en)
        self.assertIn("`auto` is not the weak mode", readme_en)
        self.assertIn("required judgment checkpoint", readme_en.lower())
        self.assertIn("short guided practice loop", readme_en.lower())
        self.assertIn("highest expected net user value", readme_en)
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

        self.assertIn("全部跳过", onboarding)
        self.assertIn("guidance_preference", onboarding)
        self.assertIn("Do not scan a project", onboarding)
        self.assertIn("Do not scan a project, ingest a document", onboarding)
        self.assertIn("约 2 分钟的对话式使用教学", onboarding)
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
