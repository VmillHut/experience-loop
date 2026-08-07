# Conversational onboarding

Use this reference only when the host attached Experience Loop to the current context, or when an already host-attached user explicitly requests setup or teaching. A filesystem read of this file is source inspection, not activation. Check lightweight controls first: preserve existing state on upgrades and do not repeat onboarding or the tutorial unless requested. Use the user's language. Keep the flow conversational; do not send the user to README steps or present a settings screen.

## Non-negotiable behavior

- Profile answers are optional. The user may answer any subset or say “skip all.”
- Installation, a filesystem copy or read, a Skill listing, implicit matching, or selector-like text in an ordinary message is not current-turn activation. First install requires host attachment provenance plus a read-only `identity` comparison. Use only the exact invocation the current host actually returned and verified; package metadata may expose a candidate prompt, but neither a candidate nor matching text is host evidence. Match the installation fingerprint when one was supplied.
- Identity, Plugin registration, Skill availability, current-turn activation, and Hook observation are separate facts. Never let one stand in for another.
- A host-injected `experience-loop.host-hook/v1` marker proves only that the approved Hook ran in that session. It does not prove Skill availability or selection, and it never authorizes reading a repository `SKILL.md` as a fallback.
- Never create or accept a model-authored activation token or receipt as evidence. Current-turn host attachment is ephemeral; do not persist it or put it in a global prompt.
- Do not require a mode choice during initialization. The default is `auto`; honor a mode only when the user voluntarily asks to save `focus`, `deep`, or `off` as the default.
- Keep `default_mode` and `activation_scope` separate. The mode controls the learning intent after activation; the scope controls only when a host adapter may wake the Skill.
- Save only explicit answers. Do not infer missing profile fields during onboarding.
- Do not scan a project, ingest a document, edit `AGENTS.md`, install another tool, or enable a network service without separate authorization.
- If urgent or active work is waiting, defer onboarding and complete that work first.
- Ask once whether the user wants the experiential tutorial targeting roughly two minutes. A refusal or exit request ends onboarding cleanly.

## Minimal initialization flow

### Gate 0: verify this turn before onboarding

For a first install, do not ask profile questions in the installation turn. The next user request must use the host's real selection UI or attachment mechanism with the exact invocation the host actually verified and the install receipt recorded verbatim. The same characters appearing in plain user text are insufficient. Do not infer, normalize, or replace that selector with a package-name default. From the host-attached Skill's own root, run the read-only `identity --expected-fingerprint <receipt>` probe when an expected fingerprint exists; otherwise run `identity` and report only the observed copy.

Require both current-turn host attachment provenance and deterministic runtime identity before onboarding. Identity algorithm v2 binds the exact installed root and version to a versioned manifest digest covering the Skill instructions, runtime modules, references, lifecycle scripts, and vendor manifest; it never proves host activation. Plugin manifests and Hooks are distribution-layer evidence and remain separately validated. If an expected fingerprint mismatches, host attachment was not observed, or the instructions came from a filesystem/tool read, keep onboarding blocked and give one next action: select/refresh the exact Skill or repair the installation. Do not synthesize missing host evidence. If the runtime is already initialized, treat this as an upgrade and skip the beginner flow unless requested.

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
7. 希望 Experience Loop 以后怎样被路由？`explicit` 只在你通过宿主真实选择器附加时参与；`project` 保存仅面向软件项目会话的适配偏好；`global` 保存所有会话中的短路由偏好。不选择就保持 `explicit`。两种自动范围都需要在新任务中验证宿主适配能力。

这些画像信息都不是必填，也可以以后在真实任务中用一句话补充或修改。不需要写简历或提供公司名、项目名和敏感指标；项目规模与难度用大致描述即可，重点是你实际承担了什么。
```

Explain that `project/global` is a routing preference, not proof that the host adapter or Hook is active. Do not add more questions unless an answer is ambiguous enough to prevent a correct write.

### Turn 2: persist only answered fields

Map explicit answers to the runtime's `setup` fields, including `--activation-scope` only when chosen. Store approximate years or stage in `experience_level`, and a compact account of representative project scale, complexity, and actual ownership in `experience_context`; do not turn it into a resume. Keep presentation and interruption preferences separate as `explanation_style` and `guidance_preference`. Repeated responsibilities, domains, goals, and learning directions may be passed more than once. If the user skips everything, run default `setup`; this keeps `auto` plus `explicit`. Do not add a project path or content-access confirmation unless separately authorized. Reuse any explicit custom `--home` or `EXPERIENCE_LOOP_HOME`; receipt commands do not remember a one-off `--home`.

After saving `project/global`, report it as `preference_saved`, never `host_active`. The adapter remains `pending_new_session_verification` until a fresh/resumed/refreshed task contains the host-injected Hook marker. That marker still proves only `hook_observed`, not Skill availability or current-turn activation. If `setup/control` returns `adapter.requirement`, explain that a non-default one-off `--home` must be matched by a persistent `EXPERIENCE_LOOP_HOME` in later host sessions before routing can even be evaluated. If the Hook is unavailable, disabled, untrusted, or fails closed, use the host's real explicit selector. Never edit a global instruction file merely to make the preference appear active, and never read `SKILL.md` from disk as a substitute.

After a successful write, summarize only the saved fields and the external data location. Then ask exactly one decision:

```text
初始化完成。要不要现在体验一个目标约 2 分钟、深入浅出的对话式教学？你会先做一次小判断，再看证据如何验证；回复“要”或“跳过”即可。
```

If the user skips, finish by stating the saved mode and activation scope. Explain that `auto` decides from evidence rather than following a fixed lesson recipe, give the verified explicit invocation as the reliable control path, and mention that “跳过”“本次只交付” or a task-scoped `focus`/`deep` request remain available at any time.

## Optional experiential tutorial targeting roughly two minutes

Run this only after the user opts in. The point is to let the user feel the core loop, not merely read a control list. Target roughly two minutes rather than promising an exact duration, adapt the explanation to the answer, and stop immediately if the user says “跳过”, “本次只交付”, or gives a real urgent task. If the saved default is `off`, this explicit opt-in authorizes only the current tutorial and does not change that default.

### Stage 1: experience `auto` before explaining it

Present this compact engineering scenario and genuinely wait because the user opted into the tutorial:

```text
先体验一次 `auto`：

一个多租户缓存偶发返回其他租户的旧数据。现在有三个初步方向：
A. 缓存 key 没包含租户标识
B. TTL 太长
C. 数据库只读副本延迟

在看决定性证据前，你会先验证哪一个？说一个选项和一句理由即可；也可以说“跳过”立即结束教学。
```

If the user says “跳过”, confirm that the tutorial has ended and do not reveal the answer or enter later stages. Otherwise reveal the fixed decisive evidence: product IDs are unique only within a tenant; tenant A and tenant B both have product `42` with different content; both primary and replica database reads return the correct tenant-specific row; the cache key is `product:{id}`; and alternating A/B requests hit the same cache entry. Compare the user's reasoning fairly with that evidence. Explain briefly that A is the ownership-boundary defect; TTL or replica lag may cause stale data but cannot explain two tenant-scoped identities colliding in the same cache entry.

Then explain the experience in one short paragraph: `auto` found a valuable and safe judgment seam, let the user predict before the answer was visible, and corrected or reinforced the model from evidence. It would have continued immediately if the user had skipped or if delivery, safety, or incident recovery made waiting inappropriate.

### Stage 2: map the experience to the four modes

Use this compact mapping. It is a user contract, not a fixed curriculum or exhaustive list of future Agent behavior:

| Mode | Who controls learning intensity | What the user experiences |
| --- | --- | --- |
| `auto` | Agent detects opportunities and decides from changing evidence | May stay silent, explain inline, ask a skippable question, briefly wait for a judgment, or run a short practice loop; no fixed answer quota |
| `focus` | User names one capability goal | The real task centers one bounded practice goal with purposeful prediction, trade-off, review, and debrief |
| `deep` | User explicitly opens full useful depth | The Agent builds a model, explores alternatives and failure conditions, invites real review, and corrects the framework against evidence without a preset recipe or round count |
| `off` | User disables the learning layer | Normal implementation and verification continue without profile use, learning prompts, learning summaries, or ledger writes |

State that task quality, safety, verification, and useful Agent execution remain the floor in every mode. `auto` can become locally intensive when evidence justifies it, but it never silently saves a `focus` goal or opens an unbounded `deep` session.

### Stage 3: show only the smallest useful controls

Give these copyable examples without turning them into a checklist the user must memorize:

```text
跳过这个问题，直接继续。
这次只交付，使用 off。
这次使用 focus，我想练习根因定位。
这次使用 deep，完整推演这个架构决策。
```

Mention only that profiles, documents, structured data, persistent indexing, and project scans remain separate opt-in extensions that can be explained when requested; do not teach them in this short tutorial.

Honor every control literally. `off` is task-scoped unless the user explicitly asks to save it. If the user gives a real task at any point, begin it immediately.

Explain saved `project/global` routing preferences only on request; their host support still requires later-session verification and never substitutes for attachment.

Close only when a close is still useful:

```text
教学完成。现在直接给我一个真实任务即可；默认 `auto` 会根据证据、时间压力和你的目标决定是否介入以及介入多深。你随时可以说“跳过”或“本次只交付”，它不是一套固定流程。
```
