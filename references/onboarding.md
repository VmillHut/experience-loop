# Conversational onboarding

Use this reference after a first-install handoff or when the user explicitly asks to initialize, set up, or learn Experience Loop. Check lightweight mode/status first: when an upgrade already has persisted state, preserve it and do not repeat onboarding or the tutorial unless requested. Use the user's language. Keep the flow conversational; do not send the user to README steps or present a settings screen.

## Non-negotiable behavior

- Profile answers are optional. The user may answer any subset or say “skip all.”
- Do not require a mode choice during initialization. The default is `auto`; honor a mode only when the user voluntarily asks to save `focus`, `deep`, or `off` as the default.
- Save only explicit answers. Do not infer missing profile fields during onboarding.
- Do not scan a project, ingest a document, edit `AGENTS.md`, install another tool, or enable a network service without separate authorization.
- If urgent or active work is waiting, defer onboarding and complete that work first.
- Ask once whether the user wants the short tutorial. A refusal ends onboarding cleanly.

## Fixed initialization flow

### Turn 1: optional profile

After confirming installation, ask all profile questions in one compact message. Use wording equivalent to:

```text
Experience Loop 已安装。下面信息都可选，回答你愿意回答的部分即可，也可以直接回复“全部跳过”：

1. 你目前的岗位或角色，以及大致从业年限或经验阶段？
2. 目前主要负责什么、常做哪些领域或项目类型？如果愿意，可补充一两个代表性项目的大致规模或复杂度，以及你实际负责的部分。
3. 未来 3–12 个月最想提升什么，或希望承担什么更高层次的责任？
4. 希望我怎样解释，例如先结论、偏原理还是偏示例？
5. 希望我怎样介入，例如尽量少打断，还是高价值时可以让我先判断并短暂等我回答？
6. 常见交付环境是什么，例如发布节奏、截止期、兼容性或可靠性要求？

这些画像信息都不是必填，也可以以后在真实任务中用一句话补充或修改。不需要写简历或提供公司名、项目名和敏感指标；项目规模与难度用大致描述即可，重点是你实际承担了什么。
```

Do not add more questions unless an answer is ambiguous enough to prevent a correct profile write.

### Turn 2: persist only answered fields

Map explicit answers to the runtime's `setup` fields. Store approximate years or stage in `experience_level`, and a compact account of representative project scale, complexity, and actual ownership in `experience_context`; do not turn it into a resume. Store presentation preferences in `explanation_style` and interruption/participation preferences in `guidance_preference`; do not merge them. Repeated responsibilities, domains, goals, and learning directions may be passed more than once. If the user skips everything, run default `setup` with no optional profile arguments. Do not add a project path or content-access confirmation unless separately authorized. If the user explicitly supplied a custom runtime home, reuse that same `--home` (or the same `EXPERIENCE_LOOP_HOME`) for `setup`, follow-up `status`, and `doctor`; receipt commands do not remember a one-off `--home` value.

After a successful write, summarize only the saved fields and the external data location. Then ask exactly one decision:

```text
初始化完成。要不要现在看一个约 2 分钟的对话式使用教学？回复“要”或“跳过”即可。
```

If the user skips, finish with: “以后直接给我真实任务即可；默认 `auto` 会自动检测任务风险和能力机会，再智能决定是否介入、何时解释或请你先做判断。你随时可以说 `focus`、`deep`、`off` 或‘跳过，直接做’。”

## Fixed short tutorial

The tutorial is interactive, not a documentation dump. Run these stages in order.

### Stage 1: let the user experience `auto`

Present this small scenario and wait for the answer because the user opted into teaching:

```text
先体验一次 `auto`：

一个多租户缓存偶发返回其他租户的旧数据。现在有三个初步方向：
A. 缓存 key 没包含租户标识
B. TTL 太长
C. 数据库只读副本延迟

在看决定性证据前，你会先验证哪一个？说一个选项和一句理由即可；也可以说“跳过”。
```

After the answer, compare it with this fixed evidence: the cache key is `product:{id}` and contains no tenant identifier, while direct database reads are correct. Explain briefly that A is the ownership-boundary defect; TTL or replica delay may cause stale data but do not explain cross-tenant identity leakage. If the user skipped, state the Agent's prediction and continue.

Then explain the effect in one paragraph: `auto` did not merely explain after the fact; it detected a valuable, safe judgment seam, briefly waited for a prediction, compared it with evidence, and would have continued immediately if the user had said “skip” or if the situation were urgent.

### Stage 2: explain all four modes

Use this compact mapping. The four modes are the user contract; the listed `auto` responses are examples, not a closed capability menu:

| Mode | Who controls learning intensity | What the user experiences |
| --- | --- | --- |
| `auto` | Agent detects automatically and decides intelligently as evidence changes | May stay silent, explain inline, ask an optional checkpoint, briefly use a required judgment checkpoint, or run a short guided practice loop; no fixed answer quota |
| `focus` | User names one capability goal | The task centers one bounded practice goal with purposeful prediction, trade-off, or review points |
| `deep` | User explicitly opens full learning depth | Proactively exercises real task decisions and Agent-output review, objectively debriefs the user's reasoning, corrects a framework against evidence, and adapts current-host methods and rounds to that outcome rather than a fixed recipe |
| `off` | User disables the learning layer | Normal task execution and verification with no learning prompts, profile use, learning tail, or event recording |

State that task quality, verification, safety, and useful Agent execution remain the floor in every mode. `auto` can be locally intensive, but it does not silently create a persistent `focus` goal or an open-ended `deep` session.

### Stage 3: show control and extensions

Give only these copyable examples:

```text
跳过这个问题，直接继续。
这次只交付，使用 off。
这次使用 focus，我想练习根因定位。
这次使用 deep，完整推演这个架构决策。
记住：我主要负责支付链路，希望更重视可靠性判断。
结合这篇文章帮助我做当前任务：<文件路径或链接>
用这份 CSV 分析我的测试薄弱点：<文件路径>
参考这个优质项目的测试架构，只读比较相关部分：<项目路径>
```

Clarify in one sentence that profile updates need only natural language, documents and data are used once by default, and persistent indexing or project scanning happens only when reuse justifies it and the user authorizes it.

### Stage 4: close

End without another setup choice:

```text
教学完成。现在直接给我一个真实任务即可；默认 `auto` 会自动检测任务风险和能力机会，再根据证据、时间压力和你的画像智能决定是否介入以及介入多深。
```
