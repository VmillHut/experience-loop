from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_development_compass_guides_source_work_and_stays_source_only(self) -> None:
        compass_path = ROOT / "docs" / "DEVELOPMENT_COMPASS.md"
        agents_path = ROOT / "AGENTS.md"
        self.assertTrue(compass_path.is_file())
        self.assertTrue(agents_path.is_file())

        compass = compass_path.read_text(encoding="utf-8")
        agents = agents_path.read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        self.assertIn("experience-loop-source-only: true", compass)
        for heading in (
            "## 2. 核心目标",
            "## 3. 产品判断",
            "## 4. 能力单调性与未来 AI",
            "## 5. 设计边界",
            "## 6. 宿主生命周期与激活真实性",
            "## 8. 模拟测试与证据",
            "## 9. 当前开发方向",
            "## 10. 长期目标",
            "## 12. 源码与用户安装边界",
        ):
            self.assertIn(heading, compass)

        self.assertIn("docs/DEVELOPMENT_COMPASS.md", agents)
        self.assertIn("completely once for the current task", agents)
        self.assertIn("not as a fixed implementation checklist", agents)
        self.assertIn("docs/DEVELOPMENT_COMPASS.md", contributing)

        installer_path = ROOT / "scripts" / "install.py"
        installer = installer_path.read_text(encoding="utf-8")
        tree = ast.parse(installer, filename=str(installer_path))
        assignments = {
            target.id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
            and target.id
            in {"PORTABLE_SKILL_PAYLOAD_FILES", "SOURCE_ONLY_CONTAMINATION"}
        }
        payload = assignments["PORTABLE_SKILL_PAYLOAD_FILES"]
        source_only = assignments["SOURCE_ONLY_CONTAMINATION"]
        for excluded in (
            "AGENTS.md",
            "CONTRIBUTING.md",
            "docs",
            "evals",
        ):
            self.assertNotIn(excluded, payload)
            self.assertIn(excluded, source_only)

        plugin_builder = (ROOT / "scripts" / "build_plugin.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "SKILL_PAYLOAD_FILES = install.PORTABLE_SKILL_PAYLOAD_FILES",
            plugin_builder,
        )

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

    def test_metadata_only_task_grants_are_object_scoped_and_ephemeral(self) -> None:
        safety = (ROOT / "references" / "safety-and-privacy.md").read_text(
            encoding="utf-8"
        )

        for required in (
            "Task-scoped content grants under `metadata-only`",
            "exact canonical resource or source object",
            "allowed content operation and its stated purpose",
            "expires when that operation completes or the current task ends",
            "Treat the grant as ephemeral",
            "Do not write the grant or raw source content",
            "does not authorize its parent directory, sibling files, a project scan",
            "persistent index, export, network upload, or reuse in a later task",
            "remain `metadata-only` and do not read content",
        ):
            self.assertIn(required, safety)

        self.assertIn(
            "weaker software manifests count only in the current working directory",
            safety,
        )
        self.assertIn("`AGENTS.md` alone is never a project signal", safety)

    def test_readmes_define_ai_first_installation_and_all_four_modes(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_en = (ROOT / "README.en.md").read_text(encoding="utf-8")
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

        self.assertIn(f"v{version}", readme)
        self.assertIn(f"v{version}", readme_en)

        self.assertIn("安装：Skill 核心 + 可选 OpenAI Plugin", readme)
        self.assertIn("docs/AI_INSTALL.md", readme)
        self.assertEqual(
            readme.count(
                "请根据 https://github.com/VmillHut/experience-loop 安装 `experience-loop`："
            ),
            1,
        )
        self.assertIn("不要在安装轮假定 Skill 已激活或开始初始化", readme)
        self.assertIn("宿主原生安装管理器", readme)
        self.assertIn("scripts/install.py --verify-only", readme)
        self.assertIn("单一路径失败不等于安装失败", readme)
        self.assertIn("一次未提交的失败尝试不锁定管理器", readme)
        self.assertIn("Git URL 本身不是安全安装协议", readme)
        self.assertNotIn('<img src="http', readme)
        self.assertNotIn("img.shields.io", readme)
        self.assertGreaterEqual(readme.count('loading="lazy"'), 3)
        self.assertIn("references/onboarding.md", readme)
        self.assertIn("平台兼容、安全边界与升级行为", readme)
        self.assertIn("不会把今天的宿主路径或调用语法写死", readme)
        self.assertIn("身份、Plugin 注册、Skill 可用性、当前轮宿主附加和 Hook observed", readme)
        self.assertIn("identity v2", readme)
        self.assertIn("构建不等于已注册、已启用、已信任或已激活", readme)
        self.assertIn("只保存适配偏好，显式选择仍是可靠路径", readme)
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
        self.assertIn("问题定义、系统建模、验证、可靠性、Agent 协作杠杆、工程所有权", readme)
        self.assertIn("当前稳定但非穷举的记录与校准坐标", readme)
        self.assertIn("目标约 2 分钟、先体验后理解的对话式教学", readme)
        self.assertIn("具体对象、操作、用途和当前任务期限", readme)
        self.assertIn("runtime 不自带 OCR、向量数据库、telemetry 或独立上传通道", readme)
        self.assertIn("发送给当前 Agent 处理的内容仍遵循宿主会话", readme)
        self.assertIn("EXPERIENCE_LOOP_DEVELOPER_SOURCE=1", readme)
        self.assertIn("transaction_capability=verified", readme)
        self.assertIn("reported-unverified", readme)
        self.assertIn("只证明文件写入与双向 rename 事务能力", readme)
        self.assertIn("Plugin 生命周期由 Codex Plugin Manager 负责", readme)
        self.assertIn("README、开发指南、测试、评测和构建脚本不会安装到用户副本", readme)
        for mode in ("auto", "focus", "deep", "off"):
            self.assertIn(f"<code>{mode}</code>", readme)
            self.assertIn(f"<code>{mode}</code>", readme_en)

        self.assertIn("Installation: Skill core + optional OpenAI Plugin", readme_en)
        self.assertIn("docs/AI_INSTALL.en.md", readme_en)
        self.assertIn("Host compatibility, safety boundaries, and upgrades", readme_en)
        self.assertIn("never freezes today's host paths", readme_en)
        self.assertIn("Identity, Plugin registration, Skill availability", readme_en)
        self.assertIn("five independent lifecycle facts", readme_en)
        self.assertIn("A build is not registration, enablement, trust, or activation", readme_en)
        self.assertIn("host-native install manager", readme_en)
        self.assertIn("scripts/install.py --verify-only", readme_en)
        self.assertIn("One failed route is not an installation failure", readme_en)
        self.assertIn(
            "An uncommitted failed attempt does not lock the manager",
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
        self.assertIn("problem framing, system modeling, verification, reliability", readme_en)
        self.assertIn("conversation targeting roughly two minutes", readme_en)
        self.assertIn("exact object, operation, purpose, and current-task lifetime", readme_en)
        self.assertIn("no built-in OCR, vector database, telemetry, or independent upload channel", readme_en)
        self.assertIn("EXPERIENCE_LOOP_DEVELOPER_SOURCE=1", readme_en)
        self.assertIn("transaction_capability=verified", readme_en)
        self.assertIn("reported-unverified", readme_en)
        self.assertIn("proves file-write and two-way-rename transaction capability only", readme_en)
        self.assertIn("Codex Plugin Manager owns Plugin lifecycle", readme_en)
        self.assertNotIn("requires zero mandatory learning answers", readme_en.lower())
        self.assertNotIn("at most two skippable checkpoints", readme_en.lower())

    def test_ai_install_and_onboarding_protocols_keep_installation_low_cost(self) -> None:
        install_zh_path = ROOT / "docs" / "AI_INSTALL.md"
        install_en_path = ROOT / "docs" / "AI_INSTALL.en.md"
        onboarding_path = ROOT / "references" / "onboarding.md"
        setup_profiles_path = ROOT / "references" / "setup-and-profiles.md"
        self.assertTrue(install_zh_path.is_file())
        self.assertTrue(install_en_path.is_file())
        self.assertTrue(onboarding_path.is_file())
        self.assertTrue(setup_profiles_path.is_file())

        install_zh = install_zh_path.read_text(encoding="utf-8")
        install_en = install_en_path.read_text(encoding="utf-8")
        onboarding = onboarding_path.read_text(encoding="utf-8")
        setup_profiles = setup_profiles_path.read_text(encoding="utf-8")

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
        self.assertIn("所有画像字段都可选", install_zh)
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
        self.assertIn("$experience-loop:experience-loop", install_zh)
        self.assertIn("standalone 的常见候选是 `$experience-loop`", install_zh)
        self.assertIn("只有在当前宿主实际返回并验证后才可使用", install_zh)
        self.assertIn("原样记录宿主实际验证过的 invocation", install_zh)
        self.assertIn("目标约 2 分钟的对话式教学", install_zh)
        self.assertIn("先判断、再看证据、再纠正或迁移", install_zh)
        self.assertIn("安装验收与五项生命周期事实不能互相代替", install_zh)
        self.assertIn("`reported-unverified` 说明", install_zh)
        self.assertIn("只证明目标上的文件写入与双向 rename 事务能力", install_zh)
        self.assertIn("every profile field is optional", install_en)
        self.assertIn("does not authorize global instructions or a Hook", install_en)
        self.assertIn("rollback_note", install_en)
        self.assertIn("real Skill/Plugin list, selector, or new-session mechanism", install_en)
        self.assertIn("never authorizes deleting existing or unknown content", install_en)
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
        self.assertIn("$experience-loop:experience-loop", install_en)
        self.assertIn("`$experience-loop` is the common standalone candidate", install_en)
        self.assertIn("only after the current host actually returns and verifies one", install_en)
        self.assertIn("record the invocation actually verified by the host verbatim", install_en)
        self.assertIn("conversational tutorial targeting roughly two minutes", install_en)
        self.assertIn("Installation acceptance and five lifecycle facts remain independent", install_en)
        self.assertIn("only a `reported-unverified` note", install_en)
        self.assertIn("proves only file-write and two-way-rename transaction capability", install_en)

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
        self.assertIn("stronger planning, reasoning, tools", router)
        self.assertIn("decide adaptively from current evidence", router)
        self.assertIn("Never impose a fixed checklist", router)
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
        self.assertIn("exact invocation the current host actually returned and verified", onboarding)
        self.assertIn("目标约 2 分钟、深入浅出的对话式教学", onboarding)
        self.assertIn("先体验一次 `auto`", onboarding)
        self.assertIn("一个多租户缓存偶发返回其他租户的旧数据", onboarding)
        self.assertIn("the cache key is `product:{id}`", onboarding)
        self.assertIn("tenant A and tenant B both have product `42`", onboarding)
        self.assertIn("alternating A/B requests hit the same cache entry", onboarding)
        self.assertIn("ownership-boundary defect", onboarding)
        self.assertIn("do not reveal the answer or enter later stages", onboarding)
        self.assertIn("map the experience to the four modes", onboarding)
        self.assertIn("not merely read a control list", onboarding)
        self.assertIn("跳过", onboarding)
        self.assertIn("本次只交付", onboarding)
        self.assertIn("大致从业年限或经验阶段", onboarding)
        self.assertIn("experience_context", onboarding)
        self.assertIn("不需要写简历", onboarding)
        self.assertIn("重点是你实际承担了什么", onboarding)
        self.assertIn("receipt commands do not remember a one-off `--home`", onboarding)
        self.assertIn("task-scoped `focus`/`deep` request", onboarding)
        self.assertIn("stop immediately", onboarding)
        self.assertIn("experiential tutorial targeting roughly two minutes", setup_profiles)
        self.assertIn("predict in a tiny engineering scenario", setup_profiles)
        self.assertIn("rather than a fixed course", setup_profiles)

    def test_openai_metadata_is_utf8_and_invokes_the_skill(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertNotIn("�", metadata)
        self.assertIn('display_name: "Experience Loop"', metadata)
        self.assertIn("$experience-loop", metadata)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertNotIn("$experience-loop:experience-loop", metadata)
        self.assertIn("stronger planning, reasoning, tools", metadata)
        self.assertIn("without turning it into a fixed workflow", metadata)
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
