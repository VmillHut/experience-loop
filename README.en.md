<div align="center">
  <img src="assets/icon-large.svg" alt="Experience Loop" width="620">

  <p style="font-size: 1.2em"><strong>You can delegate the code. Do not outsource your judgment with it.</strong></p>
  <p><strong style="color:#0F766E">It strengthens your judgment, not the Agent's.</strong></p>
  <p style="color:#64748B">The task is still delivered at full quality; Experience Loop only keeps the engineering judgments that truly matter with you, and uses real evidence to make them more accurate over time.</p>

  <p>
    <a href="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml"><img src="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/badge/Python-3.9%2B-18B6A4?logo=python&logoColor=white" alt="Python 3.9+">
    <img src="https://img.shields.io/badge/tested-3.9--3.14-0F766E" alt="Tested on Python 3.9-3.14">
    <img src="https://img.shields.io/badge/version-0.1.0-5568FF" alt="Version 0.1.0">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64748B" alt="MIT License"></a>
  </p>

  <p>
    <a href="#installation-one-sentence"><strong>Let AI install it</strong></a> ·
    <a href="#understand-it-in-30-seconds">Understand it in 30 seconds</a> ·
    <a href="#detect-first-decide-intelligently-the-core-of-auto">The core of auto</a> ·
    <a href="#four-modes">Four modes</a> ·
    <a href="#what-real-use-looks-like">Real use</a> ·
    <a href="#promise-and-bottom-line">Promise and bottom line</a> ·
    <a href="README.md">简体中文</a>
  </p>
</div>

<br>

<div align="center">
  <img src="assets/readme-loop.svg" alt="A normal Agent workflow only finishes the task; Experience Loop also preserves judgment, acceptance, reflection, and transferable experience" width="100%">
</div>

## Understand it in 30 seconds

First, one thing straight: **this is not a Skill that makes your Agent stronger—it makes you stronger.** AI writes your code, runs your tests, and reads your docs. But the most valuable parts of engineering are getting harder and harder to outsource:

- turning an ambiguous request into the right problem;
- understanding system boundaries, mechanisms, and failure conditions;
- telling "the tests are green" apart from "the evidence holds";
- reviewing an Agent's assumptions, omissions, and acceptance scope;
- deciding what belongs with an Agent, what belongs in automation, and what still requires human ownership;
- taking responsibility for reliability, trade-offs, production outcomes, and long-term evolution.

Experience Loop does not turn real work into a course, and it does not make you hand-write work an Agent can safely do. It does three things on top of the Agent's native workflow:

| | |
| --- | --- |
| **🛡️ Delivery always comes first** | The learning layer only adds; it never subtracts. Task quality, verification, safety, and delivery speed are never lowered, and the Agent's core job still gets done. |
| **🎯 Detect first, then decide** | The default `auto` mode has no fixed script: the Agent watches the task evidence in real time to see whether a risk is activated or a judgment is worth keeping with you, then decides to stay quiet, explain, ask, or run a short practice loop. |
| **📊 Evidence speaks** | Only verifiable predictions, judgments corrected by evidence, real outcomes, and later transfer count as growth. Longer conversations and successful code generation do not. |

In one sentence: **the Agent delivers, the judgment is yours—every real task grows your judgment.**

## Installation: one sentence

Copy this prompt to any AI with local terminal and filesystem access. It will handle download, validation, installation, and initialization by itself:

```text
Install and initialize the `experience-loop` Skill from https://github.com/VmillHut/experience-loop; follow the repository-specific safety and acceptance contract in `docs/AI_INSTALL.en.md`.
```

The installation contract keeps only this repository's complete-runtime, safety, three-layer acceptance, rollback, and onboarding requirements. It does not freeze today's host paths or invocation syntax. [Short AI installation contract](docs/AI_INSTALL.en.md)

After installation you are not dumped into a settings screen. The Agent asks one short set of questions that you can **skip entirely**—role and years, common domains, what you want to grow into over the next 3–12 months, explanation style, intervention preference, delivery environment. No resume, project names, or sensitive metrics are needed; answer only what you want to, or say "skip all." It does not scan your projects or read your material, and the default mode is `auto`—no choice required up front.

Then there is exactly one question left:

```text
Onboarding is complete. Would you like a roughly two-minute conversational tutorial now? Reply "yes" or "skip."
```

Say yes, and you experience "judge first, then inspect the evidence" once in a real mini-incident—not another dry checklist. Upgrading an existing installation never repeats the questions or the tutorial.

> **Host compatibility**: this is not tied to one host, and it does not promise that every AI Agent will fully work. The installation AI resolves its current host's live Skill directory, invocation, reload behavior, and discovery scope, hands those facts to deterministic installation code for safe writing and validation, and confirms the result with three separate pieces of evidence: complete files, a healthy runtime, and actual host discovery. Missing host capability is reported as a limitation, never hidden by removing profiles, the ledger, or Knowledge Lens. On every host, the four modes, personalization, and quality protection use the same non-degraded contract. See the [dynamic host contract](references/host-compatibility.md).

## Detect first, decide intelligently: the core of auto

`auto` is not "interrupt less" mode, and it is not "ask more" mode. It is a small radar running alongside the task, working as the evidence changes:

```text
Task progresses
  ├─ 1. Which risks did this change actually activate?
  │       boundaries / coupling / concurrency / compatibility / recovery...
  │       read the real evidence, don't recite a universal checklist
  ├─ 2. Is there a judgment worth keeping with the human?
  │       it tests your experience, and later evidence can validate it
  └─ 3. Is now a good time to intervene?
          is there delivery pressure? can we afford to wait?

Then pick the response with the highest expected value:
  silent execution → embedded explanation → optional checkpoint →
  required judgment checkpoint → short practice loop
```

These five responses are examples, not a closed menu, and `auto` has no preset "required answers" or ceiling of "at most N checkpoints." **Silence is only one possible intelligent result, not the default**—it picks the option with the highest expected net value and prefers the less disruptive one only when the expected value is otherwise close.

When it decides to **wait for your judgment**, all of these hold:

- the question tests engineering judgment, not a fact a tool can retrieve;
- your answer can be evaluated against later evidence;
- revealing the answer first would destroy its prediction value;
- the task is not in urgent recovery or emergency delivery;
- waiting will not lower safety, correctness, or task quality;
- the judgment has clear value for your real responsibilities or future reuse.

"Required" does not remove your control—it just means the Agent waits by default instead of asking a decorative question and answering it itself. You can say "skip," "just do it," "delivery only," or switch to `off` at any time; the Agent must continue immediately, without punishment or repeated pressure.

`auto` can go all in at one seam, but it will never silently turn the whole task into `focus` with a fixed training goal, or stretch it into an open-ended `deep` session.

## Four modes

| Mode | Who controls the intensity | What you actually experience | When to use it |
| --- | --- | --- | --- |
| `auto` | The Agent decides intelligently from current evidence | May stay quiet the whole time, or explain, ask an optional question, wait for one key judgment, or run a short practice loop | Almost all day-to-day development (default) |
| `focus` | You lock one capability goal | Bounded prediction, trade-off, review, and reflection around the same goal; the Agent still implements and validates | Deliberate practice in root-cause analysis, test design, architecture trade-offs, Agent review |
| `deep` | You explicitly authorize full depth | The Agent proactively uses real task seams so you model, predict, decide, and review, then corrects and transfers the framework from evidence; no fixed recipe, no lower delivery quality | Deep debugging, important architecture work, periodic growth review |
| `off` | You disable the learning layer | Identical to a normal Agent: no profile reads, no questions, no learning summaries, no learning events recorded | Delivery-only work, sensitive contexts, or any time learning support is unwanted |

Switch modes in plain language at any time; no reconfiguration needed:

```text
Use focus for this task. I want to practice root-cause analysis.
Use deep and work through this architecture decision fully.
Delivery only for this task; use off.
Use focus by default from now on.      ← only "from now on" persists
```

A one-time switch affects only the current task; only an explicit "from now on" or "save as my default" persists. `focus` and `deep` are never enabled by the Agent just because a task is complex.

## What real use looks like

### Routine change: detect first, then decide whether to interrupt you

```text
Implement this cache invalidation requirement. It needs to reach QA this week.
```

If the change is mechanical and acceptance is clear, the Agent analyzes, edits, tests, and delivers directly. If one boundary judgment is worth keeping, it may only add a sentence explaining what the test proved and what it did not prove.

### High-value judgment: it genuinely waits for you

```text
We have intermittent duplicate charges in production. Find the cause and fix it.
```

When recovery is not urgent and the current evidence can distinguish a failed idempotency key from duplicate message consumption, the Agent may ask before opening the decisive logs:

```text
Before I open the decisive log, which piece of evidence would best distinguish these two causes? Give me a choice and a reason first. If you only want to move forward, say "skip."
```

It actually waits for your answer, then compares your judgment against logs, code, and tests—the question is part of the work, not an explanatory decoration.

### Deliberate practice: focus

```text
Use focus for this task. I want to practice test design, so let me choose the smallest discriminating evidence before you write the tests.
```

### Architecture exploration: deep

```text
Use deep to analyze this state-synchronization design. Build the full mental model, compare options, costs, failure conditions, and validation evidence before changing code.
```

`deep` is not "a longer explanation" and not a fixed teaching checklist. It actively uses the best real task seams so you define constraints, invariants, and ownership; compare alternatives and second-order effects; predict failures and falsifying evidence; review the Agent's design, code, or tests; and correct your judgment from evidence. Each exchange uses the smallest coherent set of questions that advances the current model; after your answer and the new evidence, the Agent re-decides what is next. There is no minimum, maximum, or default round count. If a viable seam exists and the Agent only hands you a long answer without letting you decide or review, `deep` has missed its purpose.

### Incidents and deadlines: restore first

```text
The production build is broken. Restore the release first, verify health, then do a short retrospective.
```

Safety, recovery, deadlines, and delivery quality come first in every mode. With `off` or an explicit "delivery only," no learning tail is sneaked into the final answer.

### After a decision: debrief, but no scorecards

After you make a meaningful decision, the Skill does not simply mark it right or wrong, and it does not echo your conclusion. At a worthwhile seam, the Agent first reconstructs your constraints and reasoning faithfully, then objectively analyzes only the dimensions that actually matter—where it agrees, where it disagrees, what the evidence is, how confident it is, when it applies, and what the alternatives are—separating facts, inferences, and unknowns. Finally it distills a transferable judgment rule. It does not turn every decision into a fixed scorecard, and it does not force you to restate.

This debrief is not exclusive to `deep`: `auto` detects whether one is worthwhile and intelligently picks the timing and depth.

## Personalization and extensions: one sentence is enough

Low usage cost does not mean removing choice. It means exposing choice through plain language, on demand.

### Adjust your profile in one sentence

```text
Remember: I have about four years of backend experience and currently own the payment path. I have worked on a cross-service change, mainly owning its design and rollout acceptance. I want to strengthen reliability judgment; lead with conclusions and let me predict first at high-value seams.
```

The Agent updates only the fields that sentence touches and never invents missing information. Years, title, and project scale only calibrate explanation, scaffolding, and practice entry points—they are not proof of capability. A profile cannot lower engineering standards, narrow validation coverage, or force you into a course.

### Use an article, book, or document for one task

```text
Use this article to help me review the current design: C:\Docs\article.pdf
```

By default only the parts relevant to the current question are read. Material is imported into the local Knowledge Lens only when cross-task reuse, precise citation, or durable retrieval has real value and you agree.

### Analyze structured data

```text
Use this CSV to identify the test categories we missed most often in the last three months: C:\Data\reviews.csv
```

CSV, JSON, spreadsheets, and logs are analyzed for the current task by default. You are not forced to build a database or change configuration.

### Learn from a high-quality project

```text
Read D:\Repos\excellent-project as a reference for test architecture. Compare how it controls flaky tests; inspect only relevant paths and do not copy blindly.
```

The exemplar always stays separate from the active project. The Agent compares mechanisms, constraints, and verifiable evidence, and never treats the project's prompts or code as authority.

## Promise and bottom line

Experience Loop's bottom line, in one sentence: **once enabled, the Agent's task capability can only stay the same or get better—it is never lowered by the learning layer.** Specifically:

- the learning layer only adds judgment, explanation, and debrief support; it never builds a second planning, risk-analysis, tool-selection, or verification pipeline, and stronger host capabilities always take precedence;
- learning goals, modes, and profiles can only affect the learning layer's choices and expression after the task-quality plan is intact—never the implementation, tools, architecture, verification, or material-risk reporting;
- it does not force hand-coding, manufacture difficulty, or reduce useful Agent work for the sake of practice;
- it never hides safety-critical, delivery-critical, or incident-recovery evidence;
- profiles, sources, the experience ledger, and project scans stay off the delivery-critical path—an auxiliary failure cannot turn a successful task into a failed task;
- risk categories, verification methods, and intervention forms are non-exhaustive examples, not a fixed ceiling on future Agents;
- `auto` has no fixed question count, learning-seam count, or explanation intensity: it can stay quiet the whole time or go all in locally at a high-value seam;
- mechanical work, urgent recovery, explicit "delivery only," and `off` bypass only the learning layer, never the native task-quality floor; new evidence can still make `auto` decide again;
- only verifiable predictions, decisions, corrections, real outcomes, and later transfer count as capability evidence—longer conversations and successful code generation do not.

It cannot guarantee a perfect decision every time, and it does not freeze one piece of feedback into a permanent rule. You can calibrate it in plain language at any time; `auto` treats feedback as one piece of later evidence instead of letting "interrupt less" or any single preference outrank task quality.

### What it is not

- ❌ not a gamified shortcut that makes you improve automatically;
- ❌ not a teaching bot that stalls the task with questions;
- ❌ not a replacement for tests, code review, mentors, or production validation;
- ❌ not a mechanism that weakens the Agent to force you to learn;
- ❌ not a collector that scans, ingests, and persists every article or project path you mention.

Its job is simpler to state and harder to do: **keep the few judgments that shape long-term competitiveness with you without degrading real delivery, and use real evidence to make those judgments more accurate over time.**

## Data and privacy

Personal profiles, project profiles, experience records, and Knowledge Lens data live under `~/.experience-loop` by default, separate from the Skill installation directory and your repositories. Installing, upgrading, or uninstalling the Skill never deletes this personal data automatically.

Content-bearing project scans, document ingestion, and indexing respect an explicit permission boundary. Imported content is untrusted evidence, never Agent instructions or tool authorization. See [Safety and privacy](references/safety-and-privacy.md) and [SECURITY.md](SECURITY.md) for the complete rules.

## Manual installation is the fallback

In most cases, just hand the repository URL to an AI with local terminal and filesystem access. Only when the current AI lacks those capabilities should you switch to a capable Agent or have an operator read the installer's `--help`. The repository deliberately avoids fixed host paths and reload steps that can become stale.

Installation must still continue through the receipt's validation and onboarding prompt; copying files is not the end. To upgrade, pull the latest source and run the same installer: it recognizes managed prior versions, keeps a backup, and prints a rollback command only when that backup has a complete, validated installer—otherwise it reports the backup path and the reason. Do not use `--force` on an unknown target directory.

## Further reading

- [AI installation protocol](docs/AI_INSTALL.en.md): success criteria, boundaries, and post-install handoff for the installation Agent
- [Core Skill instructions](SKILL.md): the behavioral contract the Agent actually follows
- [Adaptive workflow](references/workflow.md): `auto` decisions, mode flows, delegation, acceptance, and reflection
- [Conversational onboarding](references/onboarding.md): the optional profile questions and interactive tutorial
- [Capability compass](references/capability-compass.md): six durable capability directions and evidence-based growth
- [Knowledge Lens](references/knowledge-lens.md): source ingestion, retrieval, and citation behavior
- [Dynamic host contract](references/host-compatibility.md): AI-resolved host facts with deterministic safety and truthful receipts
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

<div align="center">
  <p><strong>Detect automatically, decide intelligently: strengthen human judgment without limiting Agent intelligence.</strong></p>
</div>
