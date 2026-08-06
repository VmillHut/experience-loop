# 让 AI 安装 Experience Loop

这是一份给安装 Agent 阅读的执行协议。用户不需要照着手工敲命令；只要把仓库地址交给能访问终端和文件系统的 AI，并要求它遵守本文件。

仓库地址：`https://github.com/VmillHut/experience-loop`

## 用户只需发送一句话

```text
请按照 https://github.com/VmillHut/experience-loop 仓库中的 `docs/AI_INSTALL.md`，安装并初始化 `experience-loop` Skill。
```

## 安装 Agent 的完成标准

只有以下条件全部满足，才能向用户报告安装完成：

1. 使用的是仓库自带安装器，而不是手工拼接或零散复制文件。
2. 已确认 Python 3.9 或更高版本可用，并在预演、安装和验证中使用同一个解释器。项目持续测试 Python 3.9–3.14。
3. 已先运行 `scripts/install.py --dry-run`，检查解析后的个人 Skill 目标目录和备份目录。
4. 正式安装成功，并且目标目录中至少存在 `SKILL.md`、`agents/openai.yaml`、`scripts/experience_loop.py` 和卸载脚本。
5. 从已安装目录运行轻量 `mode --json` 成功，返回 `auto` 或用户已有的合法持久模式。
6. 已向用户准确报告安装位置、是否产生升级备份，以及当前会话是否需要重开才能发现 Skill。
7. 已调起下方的安装后初始化；如果当前会话无法调用新 Skill，已给出一条可直接复制到新会话的初始化提示词。

不要把“已克隆仓库”“已复制部分文件”或“命令看起来应该能运行”当作安装成功。

## 允许的操作边界

安装默认只授权以下变更：

- 将仓库临时克隆或下载到隔离目录；
- 运行仓库自带安装器；
- 写入安装器解析出的当前用户 Skill 目录；
- 让安装器为被识别的旧版创建托管备份；
- 在用户回答初始化问题后，通过运行时 `setup` 写入 Experience Loop 自己的外部数据目录。

安装本身不授权以下操作：

- 修改项目或全局 `AGENTS.md`、系统提示词、编辑器设置或其他 Skill；
- 扫描用户项目、读取文章或数据、建立 Knowledge Lens 索引；
- 上传代码、画像或资料，启用外部服务，安装无关依赖；
- 删除个人数据、旧备份、仓库或未知目录；
- 对无法识别的现有目标目录直接使用 `--force`。
- 执行 `curl | shell`、远程脚本管道或其他无法先审阅的安装方式。

如果确实遇到未识别的目标目录，先停止，展示其绝对路径、冲突原因和安装器计划保留的备份位置，再取得用户明确同意后才可使用 `--force`。不要绕过安装器的路径检查。

## 推荐执行流程

安装 Agent 应按当前操作系统使用等价命令；下列 `python` 在 Windows 上可在必要时换成 `py -3`。

1. 获取仓库源码到临时或用户同意的目录，确认远端地址和当前 commit，并阅读本文件、`SECURITY.md` 和安装器帮助。若源码来源或结构不符合预期，停止而不是继续猜测。

   ```text
   git remote get-url origin
   git rev-parse HEAD
   python scripts/install.py --help
   ```

2. 使用同一个 Python 解释器检查源码发布契约、版本和安装预演：

   ```text
   python --version
   python -B scripts/verify_release.py --skip-tests --json
   python -B scripts/install.py --dry-run --json
   ```

3. 审阅预演输出。若目标安全且不存在需要额外同意的冲突，正式安装：

   ```text
   python -B scripts/install.py --json
   ```

4. 优先使用安装 JSON 的结构化 `command_argv` 调用验证命令；`commands` 是为返回的 `command_shell` 生成的可复制形式（Windows 为 PowerShell，已包含 `&`）。从个人 Skill 目录执行验证，不要依赖临时源码目录：

   ```text
   python -B <已安装目录>/scripts/experience_loop.py --version
   python -B <已安装目录>/scripts/experience_loop.py --json mode
   python -B <已安装目录>/scripts/experience_loop.py --json status
   ```

5. 根据 `mode`/`status` 结果决定交接：未初始化时进入固定问答；已初始化时视为升级，保留现有画像且不重复新手问卷或教学，除非用户明确要求。
6. 初始化完成后，从已安装目录运行 `doctor --json` 和 `status --json`；必须验证退出码和 JSON 中的 `ok`/`initialized`，不能只看有输出。
7. 若当前 Codex 会话尚未发现新 Skill，要求用户先新开一个任务；新任务仍未发现时再重启 Codex。不要声称已经调用了当前会话无法发现的 Skill。

安装器会输出当前平台可复制的 `commands`、适合 Agent 直接逐项执行的 `command_argv`、源码远端/commit/dirty 状态，以及状态、卸载、升级和回滚信息。只有备份仍是可验证的、带完整安装器的 Experience Loop 安装源时，`rollback_available` 才为真并提供回滚命令；否则必须保留并报告 `backup` 与 `rollback_note`，不要自行拼接或执行备份中的脚本。原有个人画像、项目画像、经验记录和知识库位于 Skill 目录之外，正常安装或升级不会删除它们。

## 安装后的固定交接

首次成功安装且 `persisted`/`initialized` 为假时，立即对当前或新会话发送安装器返回的 `onboarding_prompt`。其含义等同于：

```text
$experience-loop 已安装。请按 references/onboarding.md 开始初始化；所有画像问题都可跳过，最后询问我是否需要约 2 分钟的使用教学。
```

接下来的 Agent 必须遵守 Skill 的 onboarding 流程：

1. 一次性询问具体但全部可选的角色、经验、责任、领域、目标、学习方向、解释风格、指导互动偏好和交付环境；允许用户回答任意部分或“全部跳过”。
2. 只保存用户实际回答的字段；全部跳过时使用默认 `auto` 初始化，不编造画像。
3. 初始化阶段不扫描项目、不读取资料、不强迫用户选择模式；默认 `auto`，但应保存用户主动提出的默认模式。
4. 初始化完成后只问一次是否需要约 2 分钟的对话式教学。
5. 用户同意后运行固定互动示例，并完整介绍 `auto`、`focus`、`deep`、`off`；用户跳过则直接结束，不追加设置步骤。

将解释呈现偏好写入 `--explanation-style`，将“少打断/愿意先判断”等介入偏好写入 `--guidance-preference`，不要混为一个字段。用户提供的每个值都应作为独立命令参数传递，不要把原始回答拼成可执行 shell 文本。

初始化写入后，从已安装目录运行 `doctor --json` 和 `status --json` 做运行时健康检查。如果检查失败，报告真实错误和下一步，不要用静默降级伪造成功。

## 最终回执格式

安装 Agent 应用简短、可核验的格式结束，而不是只说“装好了”：

```text
Experience Loop 安装结果
- source: <仓库地址、commit 与 dirty 状态>
- python: <解释器绝对路径与版本>
- version: <Skill 版本>
- target: <个人 Skill 绝对路径>
- backup: <无，或备份绝对路径>
- rollback: <可用，或不可用及安装器返回的原因>
- validation: mode/status/doctor 的实际结果
- discovery: 当前任务可用，或需要新开任务/重启
- onboarding: 已开始、用户跳过，或等待在新任务中粘贴交接提示
```

如果 AI 没有本机终端或文件权限，应明确说“未执行安装”，然后给出手工兜底；不能把说明文档当作执行结果。

## 手工安装兜底

只有用户明确希望自己操作，或当前 AI 没有终端/文件权限时，才把以下最短流程交给用户：

```text
git clone https://github.com/VmillHut/experience-loop.git
cd experience-loop
python -B scripts/install.py --dry-run
python -B scripts/install.py
```

安装后重开 Codex 会话，并粘贴“安装后的固定交接”提示词。不要让用户阅读整份 README 才能开始使用。
