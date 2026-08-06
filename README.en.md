<div align="center">
  <img src="assets/icon-large.svg" alt="Experience Loop" width="620">

  <p><strong>You can delegate the code. Do not delegate your judgment.</strong></p>
  <p>Put decisions, acceptance, and reflection back into real development so every agent-assisted task leaves reusable engineering experience.</p>

  <p>
    <a href="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml"><img src="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <img src="https://img.shields.io/badge/Python-3.9--3.14-18B6A4?logo=python&logoColor=white" alt="Python 3.9-3.14">
    <img src="https://img.shields.io/badge/version-0.1.0-5568FF" alt="Version 0.1.0">
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64748B" alt="MIT License"></a>
  </p>

  <p>
    <a href="#get-started-in-three-minutes"><strong>Get started</strong></a> ·
    <a href="#what-it-looks-like-in-real-work">See it in action</a> ·
    <a href="#knowledge-lens-use-books-inside-real-projects">Use books and documents</a> ·
    <a href="README.md">简体中文</a>
  </p>
</div>

<br>

<div align="center">
  <img src="assets/readme-loop.svg" alt="A normal agent workflow finishes the task; Experience Loop also preserves decisions, verification, reflection, and transferable experience" width="100%">
</div>

## You may already feel the gap

Agents keep getting faster, yet it becomes harder to answer:

- Why should this change live here rather than in another layer?
- What did the green tests actually prove, and what remains unproven?
- When several agent-generated designs look reasonable, what should decide the trade-off?
- Why does a similar problem still feel new the next time it appears?

Experience Loop does not ask you to use agents less or turn every task into a lesson. It restores your role at the moments that create experience: **deciding, accepting evidence, reviewing assumptions, and transferring lessons**.

## Get started in three minutes

Requires Python 3.9–3.14. No separate `pip install` is needed.

```bash
git clone https://github.com/VmillHut/experience-loop.git
cd experience-loop
python scripts/install.py
```

On Windows, use `py -3 scripts/install.py` if `python` is unavailable. You can also choose **Code → Download ZIP** on GitHub and run the installer from the extracted directory.

Open a new Codex session after installation and say:

```text
$experience-loop setup. Scan the current project.
I work mainly on client development and want to improve architecture decisions and code review.
```

Then delegate work as usual:

```text
Use $experience-loop to diagnose and fix this reconnect bug. It must be ready for QA today.
```

You do not need to edit project instructions or learn a separate command system. The default `auto` behavior adapts to deadline pressure, consequence, uncertainty, and the task's growth value without asking you to choose a mode every time.

Later personalization still needs no settings screen: add one sentence such as “I now own the payment path and want stronger reliability judgment,” provide an article or data path, or say “use `D:\Repos\reference-project` as a testing-architecture reference.” The Agent updates only the necessary profile fields, builds the local index, or scans the reference project read-only while leaving everything else at its defaults.

## It changes where you participate, not who types the code

| The Agent handles | You retain | The task leaves behind |
| --- | --- | --- |
| Code search, edits, and tools | Judgment at consequential forks | Why this option won |
| Tests, builds, and static checks | Whether the evidence is sufficient | What “done” actually proves |
| Logs and diff summaries | Risks and hidden assumptions | A reusable review cue |
| Retrieval from books and documents | Whether a principle fits this project | Source-backed, contextual knowledge |

You do not need to hand-write mechanical code the Agent can safely execute. Human attention is better spent on architecture boundaries, root causes, evidence selection, review, and final acceptance.

Internally, the Skill selects at most one direction worth strengthening: problem framing, system modeling, verification, reliability, Agent leverage, or end-to-end ownership. It adapts from real decisions and evidence instead of asking you to maintain a skill matrix or complete a curriculum.

## What it looks like in real work

### Daily delivery: ship on time and recover one key judgment

```text
Implement this cache invalidation change. It needs to reach QA this week.
```

The default `auto` behavior analyzes, edits, and verifies normally. Low-risk work stays quiet; a consequential fork may surface one optional challenge; deadlines and incidents recover first; high-consequence changes automatically receive stronger evidence, rollback, and acceptance coverage.

### Deliberate practice: predict before seeing the evidence

```text
Use focus mode. I want to practice root-cause analysis, so ask for one prediction before opening the decisive logs.
```

The Agent asks for one low-friction prediction and tests it against code, logs, or tests. A wrong prediction is useful when the evidence makes the correction clear.

### Incident response: restore first, reflect afterward

```text
The production build is broken. Restore the release first, then run a short retrospective after health is verified.
```

No teaching interruptions appear during recovery. Once health is restored and verified, the Agent produces a short timeline of expectations, observations, differences, and prevention cues.

### Architecture work: use the Agent as a review partner

```text
Use focus mode to review this state-synchronization design. Compare options, costs, and failure conditions before editing code.
```

`focus` is for deliberate practice, design review, and transfer work rather than every daily task.

## Will it slow delivery down?

Not significantly. `auto` requires **zero learning answers** and allows at most one skippable short checkpoint. It detects deadlines, incidents, and high-risk work itself. Use `focus` only when you want deliberate practice, or switch to `off` for execution only.

| Mode | Best for | Effect on work rhythm |
| --- | --- | --- |
| `auto` | Almost all normal work; default | Adapts internally; zero required learning answers and at most one optional checkpoint |
| `focus` | Deliberate practice, architecture, or a deeper review | 1–2 purposeful predictions, trade-offs, or review points |
| `off` | Execution only | No learning layer or event recording |

Change modes in any request without running setup again. Legacy `ship` / `incident` inputs map to `auto`, while `coach` / `deep` map to `focus`, so upgrades require no manual migration.

## Knowledge Lens: use books inside real projects

Give the Agent a path:

```text
Add D:\Books\Designing-Data-Intensive-Applications.pdf to Knowledge Lens and bind it to this project.
When consistency or event design comes up, explain it with source evidence.
```

```text
Books / design docs / technical notes
                 ↓
        Local extraction and index
                 ↓
      Retrieval during a real decision
                 ↓
 Source evidence + current code + clear inference boundaries
                 ↓
          An actionable project recommendation
```

It does not reread the whole book for every question or reduce it to a context-free summary. Material is retrieved when a real engineering decision appears and mapped to inspected code, constraints, and validation.

Supported formats include Markdown, plain text, reStructuredText, HTML, EPUB, DOCX, and PDFs with a text layer. Scanned PDFs require OCR first.

## Who it is for

Experience Loop is currently programmer-first, especially for developers who:

- entered the field in the agent era and want to rebuild missing engineering fundamentals;
- can ship features but want stronger architecture, debugging, review, and acceptance judgment;
- want to learn from real deadlines instead of leaving the project for a separate course;
- have technical books or team documents they want to apply to actual code decisions.

It is not an automatic growth hack and cannot replace tests, code review, mentors, or production validation. It creates better opportunities for real work to become experience you can retain.

## Common operations

<details>
<summary><strong>Upgrade, diagnose, and uninstall</strong></summary>

Pull or download the latest source and run the installer again:

```bash
python scripts/install.py
```

The installer keeps a recognized prior version as a backup and prints absolute commands for status, rollback, and uninstall. Common diagnostics:

```bash
python scripts/experience_loop.py doctor
python scripts/experience_loop.py status
```

Uninstalling the Skill does not automatically delete personal profiles or the knowledge library. Confirm the actual data directory before deleting data.

</details>

<details>
<summary><strong>Move to another computer</strong></summary>

Export profiles, project records, experience events, and the Knowledge Lens index:

```bash
python scripts/experience_loop.py export experience-loop-backup.experience-loop-export.zip
```

The archive may contain personal information and project clues. Treat it as a private backup rather than a public artifact.

</details>

<details>
<summary><strong>What it stores locally</strong></summary>

Personal profiles, project records, experience events, and knowledge indexes live under `~/.experience-loop` by default. Skill updates do not overwrite them. See [Safety and privacy](references/safety-and-privacy.md) for data, citation, and deletion boundaries.

</details>

## Go deeper

- [Skill instructions](SKILL.md): the workflow the Agent actually follows
- [Adaptive workflow](references/workflow.md): internal control, delegation, acceptance, and reflection
- [Capability compass](references/capability-compass.md): six durable directions and evidence-based growth
- [Knowledge Lens](references/knowledge-lens.md): ingestion, retrieval, and citations
- [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

<div align="center">
  <p><strong>Finishing the task is delivery. Understanding why is capability.</strong></p>
  <p><a href="#get-started-in-three-minutes">Start recovering the experience agents usually consume</a></p>
</div>
