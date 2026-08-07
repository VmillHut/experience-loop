<div align="center">
  <img src="assets/icon-large.svg" alt="Experience Loop" width="620">

  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme-intro.zh.dark.svg">
    <img src="assets/readme-intro.zh.light.svg" alt="代码可以交给 Agent，判断力不能一起外包。它提升的不是 Agent 的能力，而是你的判断力。任务照常由 Agent 高质量完成；只在关键节点，把工程判断留给你，并用真实证据让它越练越准。" width="860">
  </picture>

  <p>
    <a href="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml"><strong>CI</strong></a> ·
    <strong>Python 3.9+</strong> ·
    <strong>Tested 3.9–3.14</strong> ·
    <strong>v0.2.1</strong> ·
    <a href="LICENSE"><strong>MIT</strong></a>
  </p>

  <p>
    <a href="#install"><strong>让 AI 安装</strong></a> ·
    <a href="#overview">核心概念</a> ·
    <a href="#auto">核心机制</a> ·
    <a href="#modes">四种模式</a> ·
    <a href="#scenarios">真实场景</a> ·
    <a href="#principles">承诺与底线</a> ·
    <a href="#boundaries">边界与文档</a> ·
    <a href="README.en.md">English</a>
  </p>
</div>

<a name="overview"></a>

## 01 · 30 秒看懂它

<blockquote>
  <p><sub><strong>Experience Loop 为 Agent 工作流加入判断训练：实现、测试与交付仍由 Agent 负责；你在高价值节点做预测、取舍与复盘，让经验可验证、可迁移。</strong></sub></p>
</blockquote>

- <strong>Agent 继续负责：</strong>分析、实现、测试、验证与交付。
- <strong>你保留并增长：</strong>定义正确问题、理解系统边界、审查证据、做工程取舍、承担真实结果。

　　它不把真实任务改造成课程，也不要求你手写本可由 Agent 完成的工作。它只在原生流程上增加三件事：

1. **交付优先** · `DELIVERY FIRST` — 学习层只做加法：安全、正确性、验证范围和交付效率不能降级。
2. **证据决策** · `DECIDE FROM EVIDENCE` — `auto` 随任务证据判断是否值得介入，以及应该安静、解释、提问还是运行短循环。
3. **判断迁移** · `COMPOUND JUDGMENT` — 只有预测、纠正、真实结果和后续复用才算增长；聊天变长、代码生成成功都不算。

<div align="center">
  <img src="assets/readme-loop.zh.svg" alt="上方展示只完成任务的线性流程；下方展示 Experience Loop 在交付中保留判断、验收、复盘和可迁移经验" width="100%" loading="lazy" decoding="async">
</div>

　　**最终得到的不是更多教学步骤，而是一次次经过证据检验、以后还能复用的工程判断。**

<a name="install"></a>

## 02 · 安装：Skill 核心 + 可选 OpenAI Plugin

> [!TIP]
> 最省事的安装方式，是把下面这句话交给当前 AI。它会优先调用宿主原生安装管理器；某个命令、目录或方式失败时，会在现有权限内自动继续安全路线，并把首次激活交接到新会话。

```text
请根据 https://github.com/VmillHut/experience-loop 安装 `experience-loop`：优先使用当前宿主原生 Skill、Plugin 或 Marketplace 管理器；OpenAI 宿主支持 Plugin 生命周期时可使用其分发层，否则安装完整可移植 Skill 核心。若某个命令、目录或方式受限，请在现有权限内按 `docs/AI_INSTALL.md` 自动继续下一条安全路线，完成文件、运行时和宿主发现验收，并把首次显式激活交接到新会话；不要在安装轮假定 Skill 已激活或开始初始化。
```

1. **选择包装与管理器** — 可移植 Skill 是唯一行为核心；仓库还可构建包含同一核心的本地 OpenAI Plugin / Marketplace 包，并附带受限的相关性提示 Hook。构建不等于已注册、已启用、已信任或已激活。
2. **持续推进并分项验收** — 文件与运行时先验收；身份、Plugin 注册、Skill 可用性、当前轮宿主附加和 Hook observed 是五项独立生命周期事实，任何一项都不能替代另一项。
3. **新会话显式激活** — 首次安装后新开或刷新会话，只使用宿主实际返回并验证过的精确 selector，再核对安装回执中的 `identity` v2 指纹。生成包可能提供候选提示，但 invocation 不能从包名猜测或硬编码；身份只证明精确安装副本，不证明宿主激活。
4. **可选初始化** — 只有真实宿主 attachment 与指纹同时匹配后，才提供一次可全部跳过的简短问答，以及目标约 2 分钟、先体验后理解的对话式教学。

安装结束时不会伪装成“已经在当前轮生效”，而是只留下一个明确动作：

```text
安装副本已就绪，但安装不等于宿主发现，发现也不等于当前轮激活。请在新会话中显式选择 Experience Loop，并核对回执身份指纹；匹配后再开始初始化。
```

　　通过激活闸门后，画像问题仍可全部跳过；最后只询问是否体验一个目标约 2 分钟的对话式教学。选择「要」，你会在一个微型工程故障中先做判断，再看决定性证据，并把这次体验映射到 `auto / focus / deep / off`；选择「跳过」则立即结束初始化。教学可随时中止，不会阻塞真实任务；升级后默认不重复，除非你主动要求。跳过设置时保留默认 `auto / explicit / normal`。

<details>

<summary><strong>平台兼容、安全边界与升级行为</strong></summary>

　　安装契约不会把今天的宿主路径或调用语法写死。安装 AI 会重新解析当前宿主和安装管理器，让宿主返回精确 selector，并把实际验证过的 invocation 原样写入回执；随后分别报告身份、Plugin 注册、Skill 可用性、当前轮 attachment 与 Hook observed。宿主能力不足会被如实报告，不会通过删掉画像、经验账本或 Knowledge Lens 来伪装成功。当前轮激活只认宿主上下文中的 attachment provenance；模型或安装器生成的“激活回执”不能替代它，也不承诺以后自动调起。identity v2 绑定安装根、版本和运行时契约摘要；Plugin manifest 与 Hook 仍是独立验证层。

　　初始化问答只涉及你愿意提供的岗位、经验、常做领域、成长方向、解释风格与介入偏好；不需要简历、项目名或敏感指标，也不会顺手扫描项目或读取资料。

　　安装目标不是“跑通某一条命令”。单一路径失败不等于安装失败；只有全部适用安全路线都有失败证据，或继续确实需要新增权限时才停止。升级通常沿用原安装管理器，宿主规则变化时则做受控迁移。当前仓库提供的是可验证的本地 Plugin / Marketplace 构建能力；构建器不会注册 Marketplace、启用 Plugin、信任 Hook、启动新任务或直接改宿主 cache。Hook 通过信任审查并在新任务被观察到后，只能声称相关性提示已运行；当前 `allow_implicit_invocation: false`，所以显式宿主选择仍是可靠路径。仓库安装器会真实探测写入和双向 rename 能力；常规备份位置不可写时，自动使用休眠事务容器，且由新版生命周期管理器回滚，不执行旧备份里的安装脚本。完整契约见 [AI 安装协议](docs/AI_INSTALL.md) 与 [动态宿主契约](references/host-compatibility.md)。

</details>

<a name="auto"></a>

## 03 · 核心机制：何时值得介入

　　默认模式 `auto` 的核心机制不是「少打扰」，也不是「多提问」。它像一枚跟随任务证据变化的小雷达，持续判断：**这里有没有值得留给人的工程判断，现在是不是合适的介入时机。**

<div align="center">
  <img src="assets/readme-auto.zh.svg" alt="Experience Loop 根据真实任务证据、判断价值和介入时机选择静默执行、解释、检查点或短训练循环" width="100%" loading="lazy" decoding="async">
</div>

### 介入成立的三个条件

- <strong>有价值</strong>：问的是工程判断，而不是工具可查的事实；对现实责任或以后复用有明显价值。
- <strong>可验证</strong>：你的选择能被后续日志、代码、测试或真实结果检验；先公布答案会损失预测价值。
- <strong>适合现在发生</strong>：等待不会降低安全、正确性与交付质量；当前不是故障恢复或紧急发布。

　　三项同时成立时，`auto` 才可能真的等待你的判断。你仍然拥有控制权：随时说「跳过」「直接做」「只交付」或切到 `off`，Agent 必须立即继续，不惩罚、不重复追问。

　　这些响应只是示例，不是封闭菜单。`auto` 没有固定问题数、检查点数或解释强度，也不会擅自把任务升级成 `focus` 或 `deep`。

> **静默不是默认，提问也不是默认；预期净收益最高的介入方式才是默认。**

### 六个能力方向，只选择当前最值得练习的一条主线

　　`auto` 会从**问题定义、系统建模、验证、可靠性、Agent 协作杠杆、工程所有权**六个方向观察可迁移的判断机会。它们是当前稳定但非穷举的记录与校准坐标，不限制 Agent 发现其他有价值的判断维度。一次交互只突出最有价值的学习主线，是为了保护注意力；实现、风险分析和验证仍覆盖任务真正需要的全部工程范围，不会因为练习焦点而被缩窄。详见 [能力罗盘](references/capability-compass.md)。

<a name="modes"></a>

## 04 · 四种模式

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme-modes.zh.dark.svg">
  <img src="assets/readme-modes.zh.light.svg" alt="auto 默认智能，focus 定向练习，deep 完整推演，off 只交付" width="100%" loading="lazy" decoding="async">
</picture>

| 模&#8288;式 | 谁决定强度 | 你会实际感受到什么 |
| :---: | --- | --- |
| <strong><code>auto</code><br>默&#8288;认&#8288;智&#8288;能</strong> | Agent 根据当前证据持续决定 | 可能全程安静，也可能解释、可选提问、等待一次关键判断，或运行一个短训练循环。 |
| <strong><code>focus</code><br>定&#8288;向&#8288;练&#8288;习</strong> | 你明确锁定一个能力目标 | 围绕同一目标安排有边界的预测、取舍、审查与复盘；实现和验证仍由 Agent 负责。 |
| <strong><code>deep</code><br>完&#8288;整&#8288;推&#8288;演</strong> | 你显式授权全深度 | 在真实任务中建立模型、比较方案、预测失效、审查设计，再用证据纠正与迁移。 |
| <strong><code>off</code><br>只&#8288;交&#8288;付</strong> | 你关闭学习层 | 学习行为退化为普通只交付流程：不读内容型画像、不提问、不追加学习总结、不记录学习事件；实现与验证照常完成。 |

模式随时用自然语言切换，不需要重新初始化：

```text
这次使用 focus，我想练习根因定位。
使用 deep，完整推演这个架构决策。
这次只交付，使用 off。
以后默认使用 focus。
```

> *只有明确说「以后默认」或「保存为默认」时，这个设置才会持久化。*

　　一次性切换只影响当前任务。`focus` 和 `deep` 永远不会因为任务复杂就被 Agent 擅自开启。模式表达学习意图，不是固定流程、问题数量、检查清单或能力上限；未来宿主 Agent 更强时，应让它用更好的推理、工具与验证方式实现同一意图。

### 模式不等于激活范围

`controls.json` 是 `default_mode`、`activation_scope` 和 `privacy` 的唯一权威。模式只在 Skill 已激活后决定学习层意图；激活范围只决定获准的宿主适配器何时可以路由，两者互不替代。

| 激&#8288;活&#8288;范&#8288;围 | 行为 | 选择建议 |
| :---: | --- | --- |
| <strong><code>explicit</code></strong> | 不注入自动路由；仅在你显式选择 Skill 时参与。 | 默认，注意力成本最低。 |
| <strong><code>project</code></strong> | 只在识别到软件项目的会话中允许一条极短相关性提示。 | 可选开启；目前不代表 Skill 自动参与。 |
| <strong><code>global</code></strong> | 每个会话都可能带一条极短相关性提示，再判断是否为实质性软件任务。 | 范围更广，需明确接受持续注意力成本；仍不等于激活。 |

　　在兼容 OpenAI Plugin 中，SessionStart Hook 只读取这份非内容控制文件，不读画像，也不会预载完整 Skill；缺失/损坏控制、`off`、`explicit` 或不符合 `project` 的会话都不注入。当前包保持 `allow_implicit_invocation: false`，所以该 Hook 只是相关性提示，不能替宿主 attachment 激活 Skill；在宿主提供可验证的自动 attachment 能力前，`project/global` 只保存适配偏好，显式选择仍是可靠路径。静态 global router 仅是经单独同意后的兼容提示，同样不得读磁盘回退或冒充激活。

> 若个人数据目录只通过一次性 `--home` 指定，后续 Hook 不会自动记住它。依赖 `project/global` 前，宿主会话必须持续获得匹配的 `EXPERIENCE_LOOP_HOME`；显式选择不受这个限制。

<a name="scenarios"></a>

## 05 · 真实场景：你会实际感受到什么

| 场&#8288;景 | 你可以直接说 | Experience Loop 如何响应 |
| :---: | --- | --- |
| <strong>日&#8288;常<br>修&#8288;改</strong> | `实现这个缓存失效需求，本周要提测。` | 验收明确时直接完成；只有边界判断值得保留时，才补充证据或安排一个最小检查点。 |
| <strong>高&#8288;价&#8288;值<br>判&#8288;断</strong> | `线上偶发重复扣款，帮我定位并修复。` | 当前证据能区分关键根因且恢复不紧急时，先让你做一次可验证预测，然后真的等待。 |
| <strong><code>focus</code><br>定&#8288;向&#8288;练&#8288;习</strong> | `使用 focus，我想练习测试设计。` | 围绕同一能力目标组织短而有边界的预测、审查与复盘。 |
| <strong><code>deep</code><br>架&#8288;构&#8288;推&#8288;演</strong> | `使用 deep 分析这次状态同步设计，先不要改代码。` | 先建模、比较方案与二阶影响、预测失效条件，再审查实现与证据。 |
| <strong>故&#8288;障&#8288;与<br>赶&#8288;工</strong> | `先恢复发布，确认健康后再复盘。` | 安全、恢复、截止期和交付优先；`off` 或「只交付」时不追加学习尾巴。 |

<details>

<summary><strong>展开：一次真的会等你的高价值判断</strong></summary>

　　当证据恰好能区分「幂等键失效」和「消息重复消费」时，Agent 可能在打开决定性日志前问：

```text
在打开决定性日志前，你认为哪条证据最能区分这两个根因？
请先给一个选择和理由；如果现在只想推进，可以说"跳过"。
```

　　它会等你的回答，再用日志、代码和测试对照你的判断，而不是把问题当作解释性点缀。

</details>

<details>

<summary><strong>展开：`deep` 到底深入什么</strong></summary>

　　`deep` 不是更长的说明，也不是固定教学清单。它会让你定义约束、不变量与责任边界，比较方案和二阶影响，预测失效与可证伪证据，审查 Agent 的设计、代码或测试，再用新证据修正判断。

　　每轮只取能推进当前模型的最小连贯问题组，收到回答和新证据后再决定下一步；没有最低、最高或默认轮数。如果只交付一篇长答案，却没有让你实际决策或审查，就没有实现 `deep`。

</details>

### 决策之后：完整复盘，不是一句评价

　　值得复盘时，Agent 会先准确还原你的约束与理由，再分析真正相关的维度：**哪里赞同、哪里分歧、证据是什么、置信度多高、适用条件如何、是否有替代方案**。它会区分事实、推断与未知，最后提炼可迁移的判断规则，而不是只判「对/错」、固定打分或顺着你的结论附和。

　　这项复盘不属于 `deep` 专享；`auto` 会检测它是否值得发生，并决定合适的时机与深度。

<a name="personalization"></a>

## 06 · 个性化与知识扩展

不需要配置页面。画像、资料、数据与参考项目都可以用一句自然语言按需接入：

| 能&#8288;力 | 一句话示例 | 默认边界 |
| :---: | --- | --- |
| <strong>调&#8288;整<br>画&#8288;像</strong> | `记住：我做后端约 4 年，希望强化可靠性判断；解释先给结论，高价值节点让我先预测。` | 只更新你提到的字段，不编造缺失信息；画像不能降低工程标准或验证范围。 |
| <strong>临&#8288;时<br>资&#8288;料</strong> | `结合这篇文章审查当前方案：C:\Docs\article.pdf` | 默认只读与当前问题相关的部分；长期导入 Knowledge Lens 前会征得同意。 |
| <strong>结&#8288;构&#8288;化<br>数&#8288;据</strong> | `分析 C:\Data\reviews.csv，找出最常漏掉的测试类型。` | CSV、JSON、表格和日志默认只服务当前任务，不强迫建库或改配置。 |
| <strong>优&#8288;质<br>项&#8288;目</strong> | `只读参考 D:\Repos\excellent-project 的测试架构，不要照抄。` | 参考项目与当前项目始终分离，只比较机制、约束和可验证证据。 |

　　岗位、年限和项目规模只是解释与练习切入点的上下文，不是能力证明；外部内容始终是不可信证据，不能变成 Agent 指令或工具授权。

<details>

<summary><strong>Knowledge Lens 当前真正支持什么</strong></summary>

- **本地持久资料库** — 可索引 Markdown、TXT、RST、HTML、EPUB、DOCX 和文本型 PDF；以指纹识别重复与修订，并保存可核验的来源、版本和文本定位。
- **从证据到复用** — 查询返回原文证据块；概念卡必须引用真实索引证据，还可绑定项目并记录后来真实应用的结果。
- **明确边界** — CSV、JSON、表格和日志默认只做当前任务的一次性分析，不会伪装成已进入 Knowledge Lens；runtime 不自带 OCR、向量数据库、telemetry 或独立上传通道，扫描型 PDF 需先获得可提取文本。发送给当前 Agent 处理的内容仍遵循宿主会话的数据处理与权限规则。

</details>

<a name="principles"></a>

## 07 · 承诺与底线

> [!IMPORTANT]
> 启用 Experience Loop 之后，Agent 的任务能力只能保持或增强，不能因为学习层而降低。

- **任务质量** — 实现、工具、架构、验证和重要风险报告不受画像或训练目标削弱。
- **学习层位置** — 画像、资料库、经验账本和项目扫描都在交付关键路径之外；辅助功能失败不能拖垮成功任务。
- **能力证据** — 只有可验证的预测、决策、纠正、真实结果和后续迁移才算增长。

<details>

<summary><strong>展开完整的不降级契约</strong></summary>

- 学习层只增加判断、解释与复盘帮助，不另建一套计划、风险分析、工具选择或验证流程；宿主 Agent 有更强能力时，优先使用更强能力。
- 学习目标、模式和画像只能在任务质量方案确定后影响学习层的选择与表达，不能改变实现、工具、架构、验证或重要风险报告。
- 不为了练习强迫手写、制造困难，或减少 Agent 能完成的有用工作。
- 永不隐藏安全关键、交付关键或故障恢复所需的证据。
- 画像、资料库、经验账本和项目扫描位于交付关键路径之外，辅助失败不能让成功任务变成失败任务。
- 风险类别、验证方法和介入形式都是非穷举示例，不是限制未来 Agent 的固定清单。
- `auto` 没有固定问题数、学习节点数或解释强度；它可以全程安静，也可以在高价值节点局部开足马力。
- 机械任务、紧急恢复、明确「只交付」和 `off` 只绕过学习层，不改变 Agent 原生的质量底线。
- 新证据始终可以让 `auto` 重新决策；一次反馈不会被固化成永久规则。

</details>

### 它不是什么

- 不是「自动变强」的游戏化外挂；
- 不是用提问拖延任务的教学机器人；
- 不是测试、代码审查、导师或生产验证的替代品；
- 不是通过削弱 Agent 能力来逼你学习；
- 不是看到文章或项目路径就自动扫描、导入、持久化的知识收集器。

　　它做的事更朴素，也更难：**在真实交付不降级的前提下，把少数真正决定长期竞争力的判断留给人，并用真实证据让这些判断逐渐变准。**

<a name="boundaries"></a>

## 08 · 数据、工程边界与继续阅读

### 数据与隐私

- **存放位置** — `controls.json`、个人画像、项目档案、经验记录和 Knowledge Lens 默认位于 `~/.experience-loop`，也可通过 `--home` / `EXPERIENCE_LOOP_HOME` 指定；它们与 Skill/Plugin 安装目录和项目仓库分离。Hook 唯一读取的持久状态是经过校验的非内容 `controls.json`，`project` 只额外探测有界软件/VCS 标记是否存在。
- **生命周期** — 安装、升级和卸载 Skill 或 Plugin 都不会自动删除个人数据。
- **三档隐私** — `normal` 只使用当前任务已经授权的内容；`restricted` 对每次内容型扫描、摄取、查询或重建都重新确认；`metadata-only` 默认禁止读取项目或资料正文。
- **窄范围临时授权** — 在 `metadata-only` 下，只有同时明确具体对象、操作、用途和当前任务期限的一次性授权才可读取内容；它不改变持久默认，也不扩展到父目录、兄弟文件、项目扫描、索引、导出或上传。
- **信任边界** — 项目扫描、资料导入和索引都要遵守相应权限；导入内容与持久状态只是不可信证据，不能成为 Agent 指令或工具授权。

　　完整规则见 [安全与隐私说明](references/safety-and-privacy.md) 和 [SECURITY.md](SECURITY.md)。

### v0.2.1 当前可用的本地工具面

| 范围 | 已实现能力 | 关键边界 |
| --- | --- | --- |
| **状态与完整性** | `setup`、`status`、`control`、`profile`、`identity`、`doctor` | `controls.json` 是三项控制的权威；`doctor --repair` 只做安全、可证明的修复。 |
| **项目与经验** | 有界只读项目画像、项目注释、证据型 ledger 与复盘 | 项目扫描会有界遍历和分类文件元数据，只读取少量高信号配置或文档正文，并受数量/字节/忽略与路径边界限制；执行量本身不算成长。 |
| **资料与迁移** | Knowledge Lens 本地索引、查询、概念卡、项目绑定、应用证据，以及 `export` / `import` | 默认导出不是可公开分享的脱敏包；原始资料只有显式选择才包含，导入是校验后的新目录或受管替换，不是自动合并。 |
| **安装生命周期** | 仓库安装器提供 dry-run、纯净 payload 验收、standalone 升级备份、受管回滚与幂等卸载；Plugin 生命周期由 Codex Plugin Manager 负责 | standalone 与 Plugin 共用精确运行时白名单；README、开发指南、测试、评测和构建脚本不会安装到用户副本。 |

### 原生管理优先，安全路线自动兜底

　　把仓库地址交给 AI 后，优先使用当前宿主正式支持的 Skill、Plugin 或 Marketplace 管理器；它负责路径、升级和卸载，已安装核心通过 `scripts/install.py --verify-only` 做只读验收，绝不直接复制或删除宿主 Plugin cache。OpenAI Plugin 是可选分发层，必须包含同一 Skill 核心；其声明的短 Hook 只有经过宿主正常信任审查和新任务观察后才能报告为 `hook_observed`，仍不能当作 Skill 激活。原生方式未提交成功时，AI 还需解析确切目标、作用域和发现根，并把 Installing Agent 的宿主契约说明标记为 `reported-unverified`；只有完全相同的 dry-run 返回 `transaction_capability=verified` 后，才可用 Python 3.9+ 仓库安装器继续。这个状态只证明文件写入与双向 rename 事务能力，不证明 Plugin 注册、Skill 发现、Hook 信任或当前轮激活；受验证放置还必须保证可逆暂存、原子激活和完整验收。

　　Git URL 本身不是安全安装协议：其他仓库可能包含不同目录布局、脚本、hooks、MCP 或外部依赖。安装 AI 必须先确认安装管理器和权限边界；一次未提交的失败尝试不锁定管理器，已经提交的升级所有权则不得静默更换，也不要对未知目标目录擅自使用 `--force`。安装后仍需把首次显式激活与身份核对交给新会话，不能把文件存在或 Plugin 已列出当成当前轮已启用。

　　贡献者直接从源码 checkout 运行时，首次 `setup` 默认拒绝，避免把仓库读取冒充成已激活 Skill；只有明确的本地开发测试才可设置 `EXPERIENCE_LOOP_DEVELOPER_SOURCE=1`，且该变量绝不是宿主激活证据。

### 进一步阅读

- **安装与宿主** — [AI 安装协议](docs/AI_INSTALL.md) · [动态宿主契约](references/host-compatibility.md)
- **Agent 实际行为** — [Skill 核心指令](SKILL.md) · [自适应工作流](references/workflow.md)
- **初始化与成长模型** — [对话式初始化](references/onboarding.md) · [能力罗盘](references/capability-compass.md)
- **资料与隐私** — [Knowledge Lens](references/knowledge-lens.md) · [安全与隐私说明](references/safety-and-privacy.md)
- **项目维护** — [版本变化](CHANGELOG.md) · [参与贡献](CONTRIBUTING.md) · [安全报告](SECURITY.md)

---

<div align="center">
  <p><strong>先自动检测，再智能决策；增强人的判断力，不限制 Agent 的智能。</strong></p>
</div>
