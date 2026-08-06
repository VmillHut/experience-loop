<div align="center">
  <img src="assets/icon-large.svg" alt="Experience Loop" width="620">

  <p><strong>You can delegate the code. Do not outsource your judgment with it.</strong></p>
  <p>Experience Loop lets the Agent decide when to stay quiet, when to explain, and when to ask you to make the judgment first—so real work still ships at full quality while the important experience stays with you.</p>

  <p>
    <a href="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml"><img src="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/badge/Python-3.9%2B-18B6A4?logo=python&logoColor=white" alt="Python 3.9+">
    <img src="https://img.shields.io/badge/tested-3.9--3.14-0F766E" alt="Tested on Python 3.9-3.14">
    <img src="https://img.shields.io/badge/version-0.1.0-5568FF" alt="Version 0.1.0">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64748B" alt="MIT License"></a>
  </p>

  <p>
    <a href="#installation"><strong>Let AI install it</strong></a> ·
    <a href="#auto-is-not-the-weak-mode">Understand auto</a> ·
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

Experience Loop does not turn real work into a course, and it does not make you hand-write work an Agent can safely perform. It intervenes only at valuable judgment seams, creating a loop of **prediction or decision → Agent execution and investigation → comparison with evidence → correction and transfer**, while preserving correctness, validation, safety, and delivery speed.

## Installation

Copy this prompt to an AI with local terminal and filesystem access:

```text
Using `docs/AI_INSTALL.en.md` in https://github.com/VmillHut/experience-loop, install and initialize the `experience-loop` Skill.
```

The [AI installation protocol](docs/AI_INSTALL.en.md) contains the preview, permission boundaries, validation, upgrade, rollback, and post-install handoff. The README does not require you to perform those steps manually.

## Installation does not leave you with a settings screen

After installation, the Agent starts one fixed, short conversational flow.

It asks for these concrete details in one compact prompt:

1. your role and approximate experience stage;
2. your current responsibilities and common domains or project types;
3. the capability or higher level of responsibility you want to grow into over the next 3–12 months;
4. how you prefer explanations—for example, conclusion first, mechanism first, or examples first;
5. how you prefer intervention—for example, minimal interruption or a chance to judge first at high-value seams;
6. your usual delivery environment, including release cadence, deadlines, compatibility, and reliability expectations.

Every profile field is optional. You may answer any subset or say “skip all.” The Agent stores only what you actually provide, does not invent missing information, and does not casually scan projects or read source material. The default mode is `auto`; onboarding does not force you to choose a mode first.

Then it asks one question:

```text
Onboarding is complete. Would you like a roughly two-minute conversational tutorial now? Reply “yes” or “skip.”
```

If you choose the tutorial, the Agent uses one fixed, small incident scenario to let you experience “judge first, then inspect the evidence.” It then explains all four modes, how to skip an intervention, and how personalization, documents, data, and projects work. You do not get sent to another dry checklist. See [Conversational onboarding](references/onboarding.md) for the full flow.

Upgrading an existing installation does not repeat the profile questions or tutorial unless you explicitly request onboarding or the tutorial again.

## `auto` is not the weak mode

“Automatic” means the Agent automatically decides:

- whether this task contains a judgment worth keeping with the human;
- where in the task that intervention belongs;
- whether to stay quiet, explain in context, or require real participation;
- whether one question is enough or a short guided practice loop is justified;
- when delivery pressure should stop all learning-oriented interruption.

There is no preset of “zero required learning answers” and no fixed ceiling of “at most N skippable checkpoints.” Based on consequence, uncertainty, transfer value, your responsibilities and profile, time pressure, and interaction cost, `auto` can choose among five responses:

1. **Silent execution**: no learning layer for mechanical work, simple facts, urgent delivery, or a task with no transferable judgment.
2. **Embedded explanation**: no interruption; the Agent names one important mechanism, evidence boundary, or failure condition while executing or handing off.
3. **Optional checkpoint**: the Agent invites one prediction or trade-off; if you do not answer, it continues.
4. **Required judgment checkpoint**: when judging first is itself the valuable practice, the decisive evidence can wait, and waiting will not harm delivery, the Agent pauses for your answer.
5. **Short guided practice loop**: around one real capability seam, the Agent runs prediction, investigation, evidence comparison, correction, and one useful transfer exercise.

`auto` does not default to the lightest option. It chooses the intervention with the highest expected net user value, preferring the less disruptive option only when the expected value is otherwise comparable.

“Required” does not remove user control. It means the Agent waits by default instead of asking a decorative question and immediately answering it. You can always say “skip,” “just do it,” “delivery only,” or switch to `off`; the Agent must continue immediately without punishment or repeated pressure.

`auto` waits only when all of the following are true: the question tests human engineering judgment rather than a fact a tool can retrieve; later evidence can evaluate the answer; revealing the answer first would destroy prediction value; the task is not in urgent recovery or emergency delivery; waiting will not reduce safety, correctness, or task quality; and the judgment has clear value for your real responsibilities or future reuse.

This means `auto` can use full force at one high-value seam, but it will not silently turn the whole task into `focus` with a fixed training goal or expand it into an open-ended `deep` session.

## Why all four modes exist

| Mode | Who controls the intensity | What you actually experience | When to use it | Can it wait for an answer? |
| --- | --- | --- | --- | --- |
| `auto` | The Agent adapts from current evidence | It may stay completely quiet, explain, ask an optional question, wait for one key judgment, or run a short practice loop | Almost all day-to-day development; the default | Yes, but only when valuable and safe; you can always skip |
| `focus` | You lock one capability goal | Bounded predictions, trade-offs, reviews, and reflection around the same goal while the Agent still implements and validates | Deliberate practice in root-cause analysis, test design, architecture trade-offs, Agent review, and similar skills | Usually; the goal and rhythm are more predictable than `auto` |
| `deep` | You explicitly authorize full depth | A complete mental model, alternatives, costs, failure conditions, evidence comparison, correction, and transfer | Deep debugging, important architecture work, or a substantial growth review | Yes; it spends more dialogue and time without sacrificing delivery quality |
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

### Routine change: `auto` can stay out of the way

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

### Incidents and deadlines: restore first

```text
The production build is broken. Restore the release first, verify health, then do a short retrospective.
```

Safety, recovery, deadlines, and task quality take priority in every mode. With `off` or an explicit “delivery only” request, the Agent does not sneak a learning tail into the final answer.

## Personalization, sources, data, and exemplar projects are still here

Low usage cost does not mean removing choice. It means exposing choice through ordinary language, only when needed.

### Adjust your profile in one sentence

```text
Remember: I mainly own the payment path and want to strengthen reliability and cross-team acceptance judgment. Lead with conclusions, and let me predict first at high-value seams.
```

The Agent updates only the fields addressed by that sentence. A profile can influence which judgment seam is selected, what language is used, how an explanation is framed, and when interruption is worthwhile. It cannot lower engineering standards, narrow validation coverage, or force you into a course.

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

The goal is not “teach more.” It is positive net value:

- a learning goal may constrain teaching intervention, but never the architecture, security, compatibility, reliability, or test coverage the Agent should inspect;
- it does not force hand-coding, manufacture difficulty, or reduce useful Agent work for the sake of practice;
- it does not hide safety-critical, delivery-critical, or incident-recovery evidence;
- profiles, sources, experience records, and project scans stay off the delivery-critical path, so an auxiliary failure cannot turn a successful task into a failed task;
- mechanical work, simple facts, urgent recovery, explicit “delivery only,” and `off` use the fast path;
- high-risk work strengthens evidence, acceptance, rollback, and review instead of treating complexity itself as a reason to teach;
- only verifiable predictions, decisions, corrections, real outcomes, and later transfer count as capability evidence—longer conversations and successful code generation do not.

No adaptive system can guarantee a perfect intervention every time. You can calibrate it directly with “interrupt less,” “wait for me only at high-value seams,” “skip,” or `off`; `auto` treats that real feedback as a cost signal for later decisions.

## Data and privacy

Personal profiles, project profiles, experience records, and Knowledge Lens data live under `~/.experience-loop` by default, separate from both the Skill installation directory and project repositories. Installing, upgrading, or uninstalling the Skill does not automatically delete this personal data.

Content-bearing project scans, document ingestion, and indexing require an explicit permission boundary. Imported content is untrusted evidence, never Agent instructions or tool authorization. See [Safety and privacy](references/safety-and-privacy.md) and [SECURITY.md](SECURITY.md) for the complete rules.

## Manual installation is the fallback

Use the manual path only when you explicitly want to operate it yourself or the installation AI lacks local terminal access:

```bash
git clone https://github.com/VmillHut/experience-loop.git
cd experience-loop
python scripts/install.py --dry-run
python scripts/install.py
```

On Windows, use `py -3` if `python` is unavailable. Open a new Codex task after installation and send:

```text
$experience-loop is installed. Start the conversational onboarding. Every profile question is optional, then ask whether I want the roughly two-minute usage tutorial.
```

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
- [Core Skill instructions](SKILL.md): the behavioral contract the Agent actually follows
- [Conversational onboarding](references/onboarding.md): the fixed optional profile questions and interactive tutorial
- [Adaptive workflow](references/workflow.md): `auto` decisions, mode flows, delegation, acceptance, and reflection
- [Capability compass](references/capability-compass.md): six durable capability directions and evidence-based growth
- [Knowledge Lens](references/knowledge-lens.md): source ingestion, retrieval, and citation behavior
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

<div align="center">
  <p><strong>By default, let the Agent decide when to help you grow: full force when it matters, quiet execution when it does not.</strong></p>
</div>
