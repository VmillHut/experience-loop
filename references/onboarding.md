# Conversational onboarding

Use this reference only when the host attached Experience Loop to the current context, or when an already host-attached user explicitly requests setup or teaching. A filesystem read of this file is source inspection, not activation. Check lightweight controls first: preserve existing state on upgrades and do not repeat onboarding or the tutorial unless requested. Use the user's language. Keep the flow conversational; do not send the user to README steps or present a settings screen.

## Non-negotiable behavior

- Profile answers are optional. The user may answer any subset or say “skip all.”
- Installation, a filesystem copy or read, a Skill listing, implicit matching, or selector-like text in an ordinary message is not current-turn activation. First install requires host attachment provenance plus a read-only `identity` comparison; current OpenAI Plugin invocations use `$experience-loop:experience-loop` or a host-inserted `plugin://` selector, while a standalone Skill uses `$experience-loop`. Match the installation fingerprint when one was supplied.
- Identity, Plugin registration, Skill availability, current-turn activation, and Hook observation are separate facts. Never let one stand in for another.
- A host-injected `experience-loop.host-hook/v1` marker proves only that the approved Hook ran in that session. It does not prove Skill availability or selection, and it never authorizes reading a repository `SKILL.md` as a fallback.
- Never create or accept a model-authored activation token or receipt as evidence. Current-turn host attachment is ephemeral; do not persist it or put it in a global prompt.
- Do not require a mode choice during initialization. The default is `auto`; honor a mode only when the user voluntarily asks to save `focus`, `deep`, or `off` as the default.
- Keep `default_mode` and `activation_scope` separate. The mode controls the learning intent after activation; the scope controls only when a host adapter may wake the Skill.
- Save only explicit answers. Do not infer missing profile fields during onboarding.
- Do not scan a project, ingest a document, edit `AGENTS.md`, install another tool, or enable a network service without separate authorization.
- If urgent or active work is waiting, defer onboarding and complete that work first.
- Ask once whether the user wants the short tutorial. A refusal ends onboarding cleanly.

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
初始化完成。要不要现在看一个不超过 60 秒的微型教学？它只演示“继续”“跳过”和“本次只交付”；回复“要”或“跳过”即可。
```

If the user skips, finish by stating the saved mode and activation scope. Explain that `auto` decides from evidence rather than following a fixed lesson recipe, and give the verified explicit invocation as the reliable control path.

## Optional micro tutorial

Run this only after the user opts in. It teaches control, not a fixed lesson or an artificial incident. Present one message and wait:

```text
Experience Loop 会在真实任务中自动检测任务风险和能力机会，但你始终可以直接控制当前交互：

- “继续”：按当前任务继续，是否加入学习互动由证据动态决定。
- “跳过”：跳过眼前这次提问或练习，立即继续交付。
- “本次只交付”：本任务使用 off，不读取画像、不追加学习互动或学习总结，原本的实现与验证质量不降低。

任选一句回复，或者直接给我真实任务。
```

Honor the answer literally. `off` here is task-scoped unless the user explicitly asks to save it. Do not follow the micro tutorial with a mode table, questionnaire, synthetic exercise, or another choice. If the user gives a real task, begin it immediately.

Explain advanced controls only on request. Then concise examples may include task-scoped `focus` for one named capability, task-scoped `deep` for maximum useful learning depth, and saved `project/global` routing preferences whose host support still requires later-session verification. Natural-language profile updates, documents, data, indexing, and project scans remain separate opt-in operations.

Close only when a close is still useful:

```text
教学完成。以后直接说“继续”“跳过”或“本次只交付”即可；具体方法由当时的 Agent 能力和任务证据决定，不是一套固定流程。
```
