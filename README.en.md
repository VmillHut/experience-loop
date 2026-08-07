<div align="center">
  <img src="assets/icon-large.svg" alt="Experience Loop" width="620">

  <p><strong>You can delegate the code. Do not outsource your judgment with it.</strong></p>
  <p>Experience Loop lets the Agent detect risks and capability opportunities as evidence changes, then intelligently decide whether, when, and how strongly to intervene—without taking over or weakening the Agent's native planning, tools, or verification.</p>

  <p>
    <a href="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml"><img src="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/badge/Python-3.9%2B-18B6A4?logo=python&logoColor=white" alt="Python 3.9+">
    <img src="https://img.shields.io/badge/tested-3.9--3.14-0F766E" alt="Tested on Python 3.9-3.14">
    <img src="https://img.shields.io/badge/version-0.1.0-5568FF" alt="Version 0.1.0">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64748B" alt="MIT License"></a>
  </p>

  <p>
    <a href="#installation"><strong>Let AI install it</strong></a> ·
    <a href="#autos-core-automatic-detection-and-intelligent-decisions">Understand auto</a> ·
    <a href="#why-all-four-modes-exist">See every mode</a> ·
    <a href="#personalization-sources-data-and-exemplar-projects-are-still-here">Explore extensions</a> ·
    <a href="README.md">简体中文</a>
  </p>
</div>

<br>

<div align="center">
  <img src="assets/readme-loop.svg" alt="A normal Agent workflow only finishes the task; Experience Loop also preserves judgment, acceptance, reflection, and transferable experience" width="100%">
</div>

## What it is actually trying to help you build

AI will keep getting better at generating code. The scarcer part of a developer's value is moving toward the ability to:

- turn an ambiguous request into the right problem;
- understand system boundaries, mechanisms, and failure conditions;
- choose evidence that can distinguish truth from a reassuring green check;
- review an Agent's assumptions, omissions, risks, and acceptance scope;
- decide what belongs with an Agent, what belongs in automation, and what still requires human ownership;
- take responsibility for reliability, trade-offs, production outcomes, and long-term evolution.

Experience Loop does not turn real work into a course, and it does not make you hand-write work an Agent can safely perform. It reuses the Agent's native task process and adds **prediction or decision → execution and investigation → comparison with evidence → correction and transfer** only at valuable judgment seams, while preserving correctness, validation, safety, and delivery speed.

## Installation

Copy this prompt to an AI with local terminal and filesystem access:

```text
Install and initialize the `experience-loop` Skill from https://github.com/VmillHut/experience-loop; follow the repository-specific safety and acceptance contract in `docs/AI_INSTALL.en.md`.
```

The current AI handles ordinary download, directory discovery, and reload behavior. The [short AI installation contract](docs/AI_INSTALL.en.md) keeps only this repository's complete-runtime, safety, three-layer acceptance, rollback, and onboarding requirements. It does not freeze today's host paths or invocation syntax.

### Platform compatibility boundary

Experience Loop is not Codex-only, but it also does not claim complete support for every AI Agent. The installation AI resolves the current host's live Skill directory, invocation, reload behavior, and discovery scope from its session, help/configuration, and current official documentation when needed. It then gives those facts to deterministic installation code for safe writing and validation.

The repository does not maintain a static host-path matrix that can age into misinformation. A complete install retains compatibility sidecars such as `agents/openai.yaml` so the matching host does not lose quality, but each host decides whether to consume them. They do not alter the portable core, and another host may ignore them. Real compatibility is established by three separate pieces of evidence: complete files, a healthy installed runtime, and actual host discovery.

`auto`, `focus`, `deep`, `off`, personalization, source/project extensions, and the task-quality floor use the same non-degraded behavioral contract on every host. Missing host capability is reported, never hidden by removing profiles, the ledger, or Knowledge Lens. See the [dynamic host contract](references/host-compatibility.md).

## Installation does not leave you with a settings screen

After installation, the Agent starts one fixed, short conversational flow.

It asks for these concrete details in one compact prompt:

1. your current role or position, plus approximate years or experience stage;
2. your current responsibilities and common domains or project types, optionally including the rough scale or complexity of one or two representative projects and what you actually owned;
3. the capability or higher level of responsibility you want to grow into over the next 3–12 months;
4. how you prefer explanations—for example, conclusion first, mechanism first, or examples first;
5. how you prefer intervention—for example, minimal interruption or a chance to judge first at high-value seams;
6. your usual delivery environment, including release cadence, deadlines, compatibility, and reliability expectations.

Every profile field is optional. You may answer any subset or say “skip all”; no resume, company name, project name, or sensitive metric is required. The Agent stores only what you actually provide, does not invent missing information, and does not casually scan projects or read source material. The default mode is `auto`; onboarding does not force you to choose a mode first.

Then it asks one question:

```text
Onboarding is complete. Would you like a roughly two-minute conversational tutorial now? Reply “yes” or “skip.”
```

If you choose the tutorial, the Agent uses one fixed, small incident scenario to let you experience “judge first, then inspect the evidence.” It then explains all four modes, how to skip an intervention, and how personalization, documents, data, and projects work. You do not get sent to another dry checklist. See [Conversational onboarding](references/onboarding.md) for the full flow.

Upgrading an existing installation does not repeat the profile questions or tutorial unless you explicitly request onboarding or the tutorial again.

## `auto`'s core: automatic detection and intelligent decisions

The core of `auto` is not low intervention. It is **automatic detection + intelligent decisions**: as the task and evidence evolve, the Agent actively detects which engineering risks are activated, which judgments should remain with the human, and where a real capability opportunity exists, then decides whether, when, and how strongly to intervene.

- which boundary, coupling, runtime, concurrency, capacity, compatibility, or recovery risks the change activates;
- whether this task contains a judgment worth keeping with the human;
- where in the task that intervention belongs;
- whether to stay quiet, explain in context, or require real participation;
- whether one question is enough or a short guided practice loop is justified;
- when delivery pressure should stop all learning-oriented interruption.

There is no preset of “zero required learning answers” and no fixed ceiling of “at most N skippable checkpoints.” Based on consequence, uncertainty, transfer value, your responsibilities and profile, time pressure, and interaction cost, the following are common `auto` responses—not a closed menu that limits future Agents:

1. **Silent execution**: no learning layer for mechanical work, simple facts, urgent delivery, or a task with no transferable judgment.
2. **Embedded explanation**: no interruption; the Agent names one important mechanism, evidence boundary, or failure condition while executing or handing off.
3. **Optional checkpoint**: the Agent invites one prediction or trade-off; if you do not answer, it continues.
4. **Required judgment checkpoint**: when judging first is itself the valuable practice, the decisive evidence can wait, and waiting will not harm delivery, the Agent pauses for your answer.
5. **Short guided practice loop**: around one real capability seam, the Agent runs prediction, investigation, evidence comparison, correction, and one useful transfer exercise.

`auto` does not default to low intervention; silence is only one possible intelligent result. It chooses the intervention with the highest expected net user value, preferring the less disruptive option only when the expected value is otherwise comparable.

“Required” does not remove user control. It means the Agent waits by default instead of asking a decorative question and immediately answering it. You can always say “skip,” “just do it,” “delivery only,” or switch to `off`; the Agent must continue immediately without punishment or repeated pressure.

`auto` waits only when all of the following are true: the question tests human engineering judgment rather than a fact a tool can retrieve; later evidence can evaluate the answer; revealing the answer first would destroy prediction value; the task is not in urgent recovery or emergency delivery; waiting will not reduce safety, correctness, or task quality; and the judgment has clear value for your real responsibilities or future reuse.

This means `auto` can use full force at one high-value seam, but it will not silently turn the whole task into `focus` with a fixed training goal or expand it into an open-ended `deep` session.

## Why all four modes exist

| Mode | Who controls the intensity | What you actually experience | When to use it | Can it wait for an answer? |
| --- | --- | --- | --- | --- |
| `auto` | The Agent detects automatically and decides intelligently from current evidence | It may stay completely quiet, explain, ask an optional question, wait for one key judgment, or run a short practice loop | Almost all day-to-day development; the default | Yes, but only when valuable and safe; you can always skip |
| `focus` | You lock one capability goal | Bounded predictions, trade-offs, reviews, and reflection around the same goal while the Agent still implements and validates | Deliberate practice in root-cause analysis, test design, architecture trade-offs, Agent review, and similar skills | Usually; the goal and rhythm are more predictable than `auto` |
| `deep` | You explicitly authorize full depth | The Agent proactively uses real task seams so you model, predict, choose, and review, then correct and transfer the framework from evidence | Deep debugging, important architecture work, or a substantial growth review | More proactive and deeper than `auto`, while methods and rounds follow real value rather than a fixed recipe or lower quality |
| `off` | You disable the learning layer | Normal analysis, edits, and validation without reading learning-profile content, asking learning questions, appending learning summaries, or recording learning events | Delivery-only work, sensitive contexts, or any time learning support is unwanted | No |

Switch modes with ordinary language; no reconfiguration is needed:

```text
Use focus for this task. I want to practice root-cause analysis.
Use deep for this architecture decision and work through it fully.
Delivery only for this task; use off.
Use focus by default from now on.
Restore the default auto mode.
```

A one-time switch affects only the current task. It is persisted only when you explicitly say “from now on” or “save this as my default.” The Agent never infers `focus` or `deep` merely because the task is complex.

## What real use looks like

### Routine change: `auto` detects first, then decides whether to intervene

```text
Implement this cache invalidation requirement. It needs to reach QA this week.
```

If the change is mechanical and acceptance is clear, the Agent analyzes, edits, tests, and delivers directly. If one boundary judgment is worth preserving, it may add only a sentence explaining what the test proved and what it did not prove.

### High-value judgment: `auto` can genuinely wait

```text
We have intermittent duplicate charges in production. Find the cause and fix it.
```

If recovery is not urgent and the current evidence can distinguish a failed idempotency key from duplicate message consumption, the Agent may ask before opening the decisive logs:

```text
Before I open the decisive log, which piece of evidence would best distinguish these two causes? Give me a choice and a reason first. If you only want to move forward, say “skip.”
```

It waits for the answer, then compares your judgment against logs, code, and tests. The question is part of the work, not an explanatory decoration.

### Deliberate practice: use `focus`

```text
Use focus for this task. I want to practice test design, so let me choose the smallest discriminating evidence before you write the tests.
```

### Architecture exploration: use `deep`

```text
Use deep to analyze this state-synchronization design. Build the full mental model, compare options, costs, failure conditions, and validation evidence before changing code.
```

`auto` first decides whether capability practice is worthwhile; choosing `deep` authorizes the Agent to pursue it proactively. `deep` is neither a longer explanation nor a teaching checklist. It actively uses the best real task seams so you define constraints, invariants, and ownership; compare alternatives and second-order effects; predict failures and falsifying evidence; review the Agent's design, code, tests, or rollout; and correct your judgment from evidence. The Agent may choose, merge, reorder, repeat, or skip questions, counterexamples, simulations, visualizations, reviews, or stronger future interactions. There is no preset round count. Proactive does not mean dumping the whole question map at once: each exchange uses the smallest coherent set that advances the current model, then re-decides from the answer and new evidence. If a viable seam exists but the Agent only gives you a longer answer without letting you decide or review, `deep` has missed its purpose.

After you make a decision or finish a review, the Skill does not merely mark it right or wrong—or echo your conclusion. At a worthwhile debrief seam, the Agent first reconstructs your constraints and reasoning, then selects only the dimensions relevant to the real task, gives an independent view of strengths, gaps, evidence, confidence, conditions, and alternatives, and separates facts, inferences, and unknowns. It then extracts a transferable decision rule. It asks you to restate or apply that rule to a changed scenario only when active recall adds value, rather than turning every decision into a fixed scorecard.

Decision debriefs are not exclusive to `deep`. `auto` detects whether one is worthwhile and intelligently chooses its timing and depth; when the evidence warrants it, `auto` can also be highly proactive. The distinction is that `deep` already carries the user's authorization to seek and continue high-value debrief seams until another exchange no longer adds enough value. Neither mode optimizes for fewer interruptions or more rounds by itself.

### Incidents and deadlines: restore first

```text
The production build is broken. Restore the release first, verify health, then do a short retrospective.
```

Safety, recovery, deadlines, and task quality take priority in every mode. With `off` or an explicit “delivery only” request, the Agent does not sneak a learning tail into the final answer.

## Personalization, sources, data, and exemplar projects are still here

Low usage cost does not mean removing choice. It means exposing choice through ordinary language, only when needed.

### Adjust your profile in one sentence

```text
Remember: I have about four years of backend experience and currently own the payment path. I have worked on a cross-service change, mainly owning its design and rollout acceptance. I want to strengthen reliability judgment; lead with conclusions and let me predict first at high-value seams.
```

The Agent updates only the fields addressed by that sentence. Years, title, and project scale are calibration context for terminology, scaffolding, and practice selection—not proof of capability; actual ownership and later task evidence matter more. A profile cannot lower engineering standards, narrow validation coverage, or force you into a course.

### Use an article, book, or document for one task

```text
Use this article to help me review the current design: C:\Docs\article.pdf
```

By default, the Agent reads only the parts relevant to the current question. It imports material into the local Knowledge Lens only when cross-task reuse, precise citation, or durable retrieval has real value and you agree.

### Analyze structured data

```text
Use this CSV to identify the test categories we missed most often in the last three months: C:\Data\reviews.csv
```

CSV, JSON, spreadsheets, and logs are analyzed directly for the current task by default. You are not forced to create an index or change configuration.

### Learn from a high-quality project

```text
Read D:\Repos\excellent-project as a reference for test architecture. Compare how it controls flaky tests; inspect only relevant paths and do not copy blindly.
```

The exemplar remains separate from the active project. The Agent compares mechanisms, constraints, and verifiable evidence; it does not treat the project's prompts or code as authority.

## How it avoids dragging the Agent down

The governing rule is capability monotonicity: enabling the Skill may preserve or improve the Agent's task capability, never reduce it. In practice:

- the Skill adds a learning sidecar; it does not create another planner, risk engine, tool selector, or verification loop, and stronger capabilities from future host updates take precedence;
- modes, learning goals, and profiles may affect learning candidates, explanation, and participation only after the task-quality plan is intact; they never change implementation, tools, architecture, security, compatibility, reliability, recovery, tests, or material-risk reporting;
- it does not force hand-coding, manufacture difficulty, or reduce useful Agent work for the sake of practice;
- it does not hide safety-critical, delivery-critical, or incident-recovery evidence;
- profiles, sources, experience records, and project scans stay off the delivery-critical path, so an auxiliary failure cannot turn a successful task into a failed task;
- risk categories, verification methods, and intervention forms are non-exhaustive examples rather than a fixed ceiling on future Agents;
- mechanical work, urgent recovery, explicit “delivery only,” and `off` bypass only the learning overlay, never the native task-quality floor; new evidence can make `auto` decide again;
- `auto` has no fixed question, learning-seam, or explanation quota; it may stay quiet or use full local intensity when valuable;
- only verifiable predictions, decisions, corrections, real outcomes, and later transfer count as capability evidence—longer conversations and successful code generation do not.

No adaptive system can guarantee a perfect decision every time, but one response is not frozen into a permanent rule. You can calibrate it in natural language; `auto` treats feedback as one piece of later evidence rather than letting “interrupt less” or any single preference outrank task quality.

## Data and privacy

Personal profiles, project profiles, experience records, and Knowledge Lens data live under `~/.experience-loop` by default, separate from both the Skill installation directory and project repositories. Installing, upgrading, or uninstalling the Skill does not automatically delete this personal data.

Content-bearing project scans, document ingestion, and indexing require an explicit permission boundary. Imported content is untrusted evidence, never Agent instructions or tool authorization. See [Safety and privacy](references/safety-and-privacy.md) and [SECURITY.md](SECURITY.md) for the complete rules.

## Manual installation is the fallback

In most cases, give the repository URL to an AI with local terminal and filesystem access. Only when the current AI lacks those capabilities should you switch to a capable Agent or have an operator use the installer's `--help`. The repository deliberately avoids fixed host paths and reload steps that may become stale.

Installation must still continue through the receipt's validation and `onboarding_prompt`; copying files is not the end of the flow.

To upgrade, download or pull the latest source and run the same installer. It recognizes managed prior versions and preserves a backup. A rollback command is printed only when that backup has a complete, validated installer; otherwise the receipt reports the backup path and why automatic rollback is unavailable. Do not use `--force` on an unrecognized target directory without explicit review and consent.

## What it is not

- not a gamified shortcut that makes you improve automatically;
- not a teaching bot that delays the task with constant questions;
- not a replacement for tests, code review, mentors, or production validation;
- not a mechanism that weakens the Agent to force the user to learn;
- not a collector that scans, ingests, and persists every article or project path you mention.

Its job is simpler to state and harder to do: preserve the few judgments that shape long-term competitiveness without degrading real delivery, then use real evidence to help those judgments become more accurate over time.

## Further reading

- [AI installation protocol](docs/AI_INSTALL.en.md): success criteria, boundaries, and post-install handoff for the installation Agent
- [Dynamic host contract](references/host-compatibility.md): AI-resolved host facts with deterministic safety and truthful receipts
- [Core Skill instructions](SKILL.md): the behavioral contract the Agent actually follows
- [Conversational onboarding](references/onboarding.md): the fixed optional profile questions and interactive tutorial
- [Adaptive workflow](references/workflow.md): `auto` decisions, mode flows, delegation, acceptance, and reflection
- [Capability compass](references/capability-compass.md): six durable capability directions and evidence-based growth
- [Knowledge Lens](references/knowledge-lens.md): source ingestion, retrieval, and citation behavior
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

<div align="center">
  <p><strong>Detect automatically, decide intelligently: strengthen human judgment without limiting Agent intelligence.</strong></p>
</div>
