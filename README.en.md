<div align="center">
  <img src="assets/icon-large.svg" alt="Experience Loop" width="620">

  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/readme-intro.en.dark.svg">
    <img src="assets/readme-intro.en.light.svg" alt="You can delegate the code. Do not outsource your judgment with it. It strengthens your judgment, not the Agent's. Tasks still ship at full quality; evidence keeps engineering judgment with you." width="860">
  </picture>

  <p>
    <a href="https://github.com/VmillHut/experience-loop/actions/workflows/ci.yml"><strong>CI</strong></a> ·
    <strong>Python 3.9+</strong> ·
    <strong>Tested 3.9–3.14</strong> ·
    <strong>v0.2.1</strong> ·
    <a href="LICENSE"><strong>MIT</strong></a>
  </p>

  <p>
    <a href="#install"><strong>Let AI install it</strong></a> ·
    <a href="#overview">Core idea</a> ·
    <a href="#auto">Core mechanism</a> ·
    <a href="#modes">Four modes</a> ·
    <a href="#scenarios">Real use</a> ·
    <a href="#principles">Promise and bottom line</a> ·
    <a href="#boundaries">Boundaries and docs</a> ·
    <a href="README.md">简体中文</a>
  </p>
</div>

<a name="overview"></a>

## 01 · Understand it in 30 seconds

<blockquote>
  <p><sub><strong>Experience Loop adds judgment training to the Agent workflow: it still implements, tests, and ships; at high-value moments, you predict, weigh trade-offs, and review so experience stays verifiable and transferable.</strong></sub></p>
</blockquote>

- <strong>The Agent continues to handle:</strong> analysis, implementation, testing, validation, and delivery.
- <strong>You retain and grow:</strong> defining the right problem, understanding boundaries, reviewing evidence, making trade-offs, and owning real outcomes.

It does not turn real work into a course or make you hand-write work an Agent can safely do. It adds only three things to the native workflow:

1. **Protect delivery** · `DELIVERY FIRST` — The learning layer only adds. Safety, correctness, validation coverage, and delivery effectiveness cannot be degraded.
2. **Decide from evidence** · `DECIDE FROM EVIDENCE` — `auto` watches live task evidence and chooses whether to stay quiet, explain, ask, or run a short loop.
3. **Transfer judgment** · `COMPOUND JUDGMENT` — Only predictions, corrections, real outcomes, and later reuse count as growth; longer conversations and successful code generation do not.

<div align="center">
  <img src="assets/readme-loop.en.svg" alt="A top lane that only ships work and a lower Experience Loop lane that preserves judgment, evidence, reflection, and reusable experience" width="100%" loading="lazy" decoding="async">
</div>

**The result is not more teaching steps. It is engineering judgment that has survived real evidence and can be reused later.**

<a name="install"></a>

## 02 · Installation: Skill core + optional OpenAI Plugin

> [!TIP]
> The simplest path is to give the sentence below to the current AI. It prefers the host-native install manager and, if one command, directory, or method fails, continues through safe routes within current authority, then hands first activation to a new session.

```text
Install `experience-loop` from https://github.com/VmillHut/experience-loop. Prefer the current host's native Skill, Plugin, or Marketplace manager; on an OpenAI host with a supported Plugin lifecycle, you may use the Plugin distribution layer, otherwise install the complete portable Skill core. If any command, directory, or method is unavailable, continue automatically through the safe alternatives in `docs/AI_INSTALL.en.md` within current authority, complete filesystem, runtime, and host-discovery acceptance, and hand first explicit activation to a new session. Do not assume the Skill is active or begin onboarding in the installation turn.
```

1. **Choose the package and manager** — The portable Skill is the single behavior core. The repository can also build a local OpenAI Plugin / Marketplace package containing that same core plus a bounded relevance-hint Hook. A build is not registration, enablement, trust, or activation.
2. **Keep progressing and separate acceptance** — Accept the filesystem and runtime first. Identity, Plugin registration, Skill availability, current-turn host attachment, and Hook observation are five independent lifecycle facts; none can stand in for another.
3. **Activate explicitly in a new session** — After first installation, open or refresh a session, use only the exact selector actually returned and verified by the host, and match the install receipt's identity v2 fingerprint. A generated package may provide a candidate prompt, but the invocation must never be guessed or hard-coded from its package name. Identity proves the exact installed copy, not host activation.
4. **Optional onboarding** — Only real host attachment plus a matching fingerprint opens one fully skippable questionnaire and an optional conversation targeting roughly two minutes that teaches through experience before explanation.

The installation turn does not pretend that the Skill is already active. It leaves one clear action:

```text
The installed copy is ready, but installation is not host discovery, and discovery is not current-turn activation. Explicitly select Experience Loop in a new session and match the receipt's identity fingerprint before onboarding.
```

After the activation gate, every profile question remains optional. The final offer is a conversational tutorial targeting roughly two minutes: choose yes to make one judgment in a tiny engineering incident, inspect the decisive evidence, then map that experience to `auto / focus / deep / off`; choose skip to finish immediately. The tutorial can stop at any time and never blocks real work. It is not repeated after an upgrade unless you explicitly ask for it. Skipping setup preserves the defaults `auto / explicit / normal`.

<details>

<summary><strong>Host compatibility, safety boundaries, and upgrades</strong></summary>

The installation contract never freezes today's host paths or invocation syntax. The installation AI resolves the current host and install manager again, requires the host to return the exact selector, records the invocation that was actually verified verbatim, then reports identity, Plugin registration, Skill availability, current-turn attachment, and Hook observation separately. Missing capability is reported honestly; success is never faked by deleting profiles, the experience ledger, or Knowledge Lens. Current-turn activation requires attachment provenance from the host context; a model- or installer-authored “activation receipt” cannot substitute for it or promise future automatic activation. Identity v2 binds the install root, version, and runtime-contract digest; the Plugin manifest and Hook remain separate validation layers.

The optional questionnaire covers only what you choose to share: role, experience, common domains, growth direction, explanation style, and intervention preference. It needs no resume, project names, or sensitive metrics, and it does not scan projects or read material on the side.

The goal is not to make one command succeed. One failed route is not an installation failure; the Agent stops only after every applicable safe route has failure evidence or continuing genuinely needs new authority. Upgrades normally retain their manager, while changed host rules trigger a controlled migration. The repository currently provides a validated local Plugin / Marketplace build path; the builder does not register a Marketplace, enable a Plugin, trust a Hook, start a new task, or modify host cache directly. After trust review and observation in a new task, the Hook proves only that its relevance hint ran. Because `allow_implicit_invocation: false`, explicit host selection remains the reliable path. Repository-managed installs probe real write and two-way rename capabilities, fall back to a dormant transaction container when the normal backup location is unavailable, and use the new lifecycle manager for rollback instead of executing an old backup installer. See the [AI installation protocol](docs/AI_INSTALL.en.md) and [dynamic host contract](references/host-compatibility.md).

</details>

<a name="auto"></a>

## 03 · Core mechanism: when to intervene

The core mechanism behind the default `auto` mode is not "interrupt less" and not "ask more." It is a small radar that follows changing task evidence and keeps asking: **is there an engineering judgment worth keeping with the human, and is this the right moment to intervene?**

<div align="center">
  <img src="assets/readme-auto.en.svg" alt="Experience Loop selects a response from live task evidence, the value of a human judgment, and whether it is the right moment to intervene" width="100%" loading="lazy" decoding="async">
</div>

### Three conditions for intervention

- <strong>Valuable</strong>: the question tests engineering judgment, not a retrievable fact, and clearly matters to real responsibility or later reuse.
- <strong>Verifiable</strong>: your choice can be checked against later logs, code, tests, or outcomes; revealing the answer first would reduce prediction value.
- <strong>Appropriate now</strong>: waiting will not lower safety, correctness, or delivery quality, and the task is not in urgent recovery or emergency release.

Only when all three hold may `auto` genuinely wait for your judgment. You remain in control: say "skip," "just do it," "delivery only," or switch to `off` at any time, and the Agent must continue immediately without punishment or repeated pressure.

These responses are examples, not a closed menu. `auto` has no fixed question count, checkpoint count, or explanation intensity, and it never silently upgrades a task into `focus` or `deep`.

> **Silence is not the default, and asking is not the default. The intervention with the highest expected net value is the default.**

### Six capability directions, one worthwhile learning thread at a time

`auto` looks for transferable judgment across **problem framing, system modeling, verification, reliability, Agent leverage, and engineering ownership**. These are stable but non-exhaustive coordinates for recording and calibration; they do not stop the Agent from discovering other valuable judgment dimensions. Highlighting one learning thread at a time protects attention; implementation, risk analysis, and validation still cover the full engineering scope the task actually requires. See the [capability compass](references/capability-compass.md).

<a name="modes"></a>

## 04 · Four modes

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme-modes.en.dark.svg">
  <img src="assets/readme-modes.en.light.svg" alt="auto decides from evidence, focus practices one goal, deep explores the full decision, and off keeps delivery only" width="100%" loading="lazy" decoding="async">
</picture>

| Mode | Who controls the intensity | What you actually experience |
| :---: | --- | --- |
| <strong><code>auto</code><br>Default intelligence</strong> | The Agent continuously decides from current evidence | It may stay quiet throughout, explain, ask an optional question, wait for one key judgment, or run a short practice loop. |
| <strong><code>focus</code><br>Deliberate practice</strong> | You lock one capability goal | Bounded prediction, trade-off, review, and debrief around that goal; the Agent still implements and validates. |
| <strong><code>deep</code><br>Full exploration</strong> | You explicitly authorize full depth | Build a model, compare options, predict failure, review the design, and correct or transfer judgment from evidence. |
| <strong><code>off</code><br>Delivery only</strong> | You disable the learning layer | Learning behavior reduces to normal delivery-only work: no content-bearing profile reads, questions, learning summaries, or learning events; implementation and verification continue normally. |

Switch modes in plain language at any time without rerunning setup or onboarding:

```text
Use focus for this task. I want to practice root-cause analysis.
Use deep and work through this architecture decision fully.
Delivery only for this task; use off.
Use focus by default from now on.
```

> *This setting persists only when you explicitly say "from now on" or "save as my default."*

A one-time switch affects only the current task. `focus` and `deep` are never enabled just because a task is complex. Modes express learning intent, not a fixed flow, question count, checklist, or capability ceiling. As future host Agents improve, let their stronger reasoning, tools, and verification fulfill the same intent.

### Mode is not activation scope

`controls.json` is the sole authority for `default_mode`, `activation_scope`, and `privacy`. Mode affects learning intent only after the Skill is active; activation scope only tells an approved host adapter when it may route. Neither substitutes for the other.

| Activation scope | Behavior | Guidance |
| :---: | --- | --- |
| <strong><code>explicit</code></strong> | Injects no automatic route; participates only when you explicitly select the Skill. | Default and lowest attention cost. |
| <strong><code>project</code></strong> | Permits one very short relevance hint only in sessions recognized as software projects. | Optional; it does not currently mean the Skill participates automatically. |
| <strong><code>global</code></strong> | May carry one very short relevance hint in every session before checking for substantive software work. | Broader scope; explicitly accept the persistent attention cost. It still is not activation. |

In a compatible OpenAI Plugin, the SessionStart Hook reads only this non-content control file, never the profile, and does not preload the full Skill. Missing or corrupt controls, `off`, `explicit`, and sessions outside `project` scope inject nothing. This package keeps `allow_implicit_invocation: false`, so the Hook is a relevance hint and cannot replace host attachment. Until the host exposes verifiable automatic attachment, `project/global` save adapter preferences only and explicit selection remains the reliable path. The separately consented static global router is likewise only a compatibility hint; it must never read the Skill from disk or impersonate activation.

> If the personal data directory was supplied only through a one-off `--home`, a later Hook will not remember it. Before relying on `project/global`, host sessions must persist the matching `EXPERIENCE_LOOP_HOME`; explicit selection is unaffected.

<a name="scenarios"></a>

## 05 · Real use: what you actually experience

| Situation | What you can say | How Experience Loop responds |
| :---: | --- | --- |
| <strong>Routine<br>change</strong> | `Implement this cache invalidation requirement. It needs to reach QA this week.` | If acceptance is clear, it delivers directly. Only a worthwhile boundary judgment triggers extra evidence or one minimal checkpoint. |
| <strong>High-value<br>judgment</strong> | `We have intermittent duplicate charges in production. Find the cause and fix it.` | When evidence can distinguish key causes and recovery is not urgent, it asks for one verifiable prediction and genuinely waits. |
| <strong><code>focus</code><br>Deliberate practice</strong> | `Use focus. I want to practice test design.` | A short, bounded sequence of prediction, review, and debrief stays centered on one capability goal. |
| <strong><code>deep</code><br>Architecture exploration</strong> | `Use deep to analyze this state-synchronization design. Do not change code yet.` | It models constraints, compares options and second-order effects, predicts failures, then reviews implementation and evidence. |
| <strong>Incident<br>or rush</strong> | `Restore the release first, verify health, then debrief.` | Safety, recovery, deadlines, and delivery come first. `off` or "delivery only" adds no learning tail. |

<details>

<summary><strong>Expand: a high-value judgment where the Agent really waits</strong></summary>

When current evidence can distinguish a failed idempotency key from duplicate message consumption, the Agent may ask before opening the decisive log:

```text
Before I open the decisive log, which piece of evidence would best distinguish these two causes?
Give me a choice and a reason first. If you only want to move forward, say "skip."
```

It waits for your answer, then compares your judgment against logs, code, and tests. The question is part of the work, not explanatory decoration.

</details>

<details>

<summary><strong>Expand: what `deep` actually explores</strong></summary>

`deep` is not a longer explanation and not a fixed teaching checklist. It asks you to define constraints, invariants, and ownership; compare alternatives and second-order effects; predict failures and falsifying evidence; review the Agent's design, code, or tests; and correct judgment from new evidence.

Each exchange uses the smallest coherent question set that advances the current model, then re-decides what is next after your answer and the new evidence. There is no minimum, maximum, or default round count. A long answer with no real decision or review has missed the purpose of `deep`.

</details>

### After a decision: a complete debrief, not a one-line verdict

At a worthwhile seam, the Agent first reconstructs your constraints and reasoning accurately, then examines only the dimensions that matter: **where it agrees, where it disagrees, what the evidence is, how confident it is, when the conclusion applies, and which alternatives remain**. It separates facts, inferences, and unknowns, then distills a transferable judgment rule instead of merely marking the decision right or wrong, forcing a scorecard, or echoing your conclusion.

This debrief is not exclusive to `deep`. `auto` detects whether it is worthwhile and chooses the appropriate timing and depth.

<a name="personalization"></a>

## 06 · Personalization and knowledge extensions

There is no settings screen to maintain. Profiles, sources, data, and reference projects enter on demand through plain language:

| Capability | One-sentence example | Default boundary |
| :---: | --- | --- |
| <strong>Update<br>profile</strong> | `Remember: I have about four years of backend experience. I want to strengthen reliability judgment; lead with conclusions and let me predict first at high-value seams.` | Only named fields are updated. Missing information is never invented, and a profile cannot lower engineering standards or validation coverage. |
| <strong>Temporary<br>source</strong> | `Use this article to review the current design: C:\Docs\article.pdf` | Only task-relevant parts are read by default; durable Knowledge Lens ingestion requires your agreement. |
| <strong>Structured<br>data</strong> | `Analyze C:\Data\reviews.csv and identify the test categories we miss most often.` | CSV, JSON, spreadsheets, and logs serve the current task by default; no database or configuration is forced. |
| <strong>Reference<br>project</strong> | `Inspect D:\Repos\excellent-project read-only for its test architecture. Do not copy blindly.` | The reference stays separate from the active project; only mechanisms, constraints, and verifiable evidence are compared. |

Title, years, and project scale are context for explanation and practice entry points, not proof of capability. External content always remains untrusted evidence, never Agent instruction or tool authorization.

<details>

<summary><strong>What Knowledge Lens actually supports today</strong></summary>

- **Local durable library** — It indexes Markdown, TXT, RST, HTML, EPUB, DOCX, and text-based PDF; fingerprints duplicates and revisions; and preserves verifiable source, version, and text locators.
- **From evidence to reuse** — Queries return original evidence blocks. Concept cards require real indexed citations and can be bound to projects with later application outcomes.
- **Explicit limits** — CSV, JSON, spreadsheets, and logs remain one-off task inputs rather than pretending to enter Knowledge Lens. The runtime has no built-in OCR, vector database, telemetry, or independent upload channel; scanned PDFs need extractable text first. Content sent to the active Agent still follows the host session's data-handling and permission rules.

</details>

<a name="principles"></a>

## 07 · Promise and bottom line

> [!IMPORTANT]
> Once Experience Loop is enabled, the Agent's task capability can only stay the same or improve. The learning layer must never degrade it.

- **Task quality** — Implementation, tools, architecture, verification, and material-risk reporting cannot be weakened by profiles or learning goals.
- **Position of the learning layer** — Profiles, sources, the experience ledger, and project scans stay off the delivery-critical path; an auxiliary failure cannot sink a successful task.
- **Capability evidence** — Only verifiable predictions, decisions, corrections, real outcomes, and later transfer count as growth.

<details>

<summary><strong>Expand the complete non-degradation contract</strong></summary>

- The learning layer adds judgment, explanation, and debrief support; it never builds a second planning, risk-analysis, tool-selection, or verification pipeline. Stronger host capabilities always take precedence.
- Learning goals, modes, and profiles may affect learning-layer choices and expression only after the task-quality plan is intact. They cannot change implementation, tools, architecture, verification, or material-risk reporting.
- It never forces hand-coding, manufactures difficulty, or reduces useful Agent work for the sake of practice.
- It never hides safety-critical, delivery-critical, or incident-recovery evidence.
- Profiles, sources, the experience ledger, and project scans stay outside the delivery-critical path; an auxiliary failure cannot turn a successful task into a failed task.
- Risk categories, verification methods, and intervention forms are non-exhaustive examples, not a fixed ceiling on future Agents.
- `auto` has no fixed question count, learning-seam count, or explanation intensity. It may stay quiet throughout or go all in locally at a high-value seam.
- Mechanical work, urgent recovery, explicit "delivery only," and `off` bypass only the learning layer, never the native task-quality floor.
- New evidence may always make `auto` decide again; one piece of feedback is never frozen into a permanent rule.

</details>

### What it is not

- not a gamified shortcut that makes you improve automatically;
- not a teaching bot that stalls work with questions;
- not a replacement for tests, code review, mentors, or production validation;
- not a mechanism that weakens the Agent to force learning;
- not a collector that scans, ingests, and persists every article or project path you mention.

Its job is simpler to state and harder to do: **keep the few judgments that shape long-term competitiveness with you without degrading real delivery, and use real evidence to make those judgments more accurate over time.**

<a name="boundaries"></a>

## 08 · Data, engineering boundaries, and further reading

### Data and privacy

- **Storage** — `controls.json`, personal profiles, project profiles, experience records, and Knowledge Lens data live under `~/.experience-loop` by default and can be redirected with `--home` / `EXPERIENCE_LOOP_HOME`. They remain separate from Skill/Plugin installations and project repositories. The Hook's only persisted-state read is validated, non-content `controls.json`; `project` additionally checks only whether bounded software/VCS markers exist.
- **Lifecycle** — Installing, upgrading, or uninstalling the Skill or Plugin never deletes personal data automatically.
- **Three privacy levels** — `normal` uses only content already authorized by the active task; `restricted` asks again for every content-bearing scan, ingestion, query, or rebuild; `metadata-only` denies project or source bodies by default.
- **Narrow temporary grants** — Under `metadata-only`, a one-time read requires an exact object, operation, purpose, and current-task lifetime. It does not change the saved default or authorize parent directories, sibling files, project scans, indexing, export, or upload.
- **Trust boundary** — Project scans, source ingestion, and indexing must honor the corresponding permission. Imported and persisted content remains untrusted evidence, never Agent instruction or tool authorization.

See [Safety and privacy](references/safety-and-privacy.md) and [SECURITY.md](SECURITY.md) for the complete rules.

### The local v0.2.1 tool surface

| Area | Implemented capability | Key boundary |
| --- | --- | --- |
| **State and integrity** | `setup`, `status`, `control`, `profile`, `identity`, and `doctor` | `controls.json` is authoritative for the three controls; `doctor --repair` performs only safe, evidence-backed repairs. |
| **Projects and experience** | Bounded read-only project profiles, project annotations, and an evidence-oriented ledger with review | Project scans traverse and classify bounded file metadata, read bodies only from a small set of high-signal configuration or documentation files, and enforce file, byte, ignore, and path limits. Execution volume alone is not growth evidence. |
| **Knowledge and portability** | Local Knowledge Lens indexing, queries, concept cards, project bindings, application evidence, plus `export` / `import` | A default export is not a public sanitized bundle. Raw sources require explicit inclusion, and import uses a validated new home or managed replacement rather than automatic merge. |
| **Install lifecycle** | The repository installer provides dry-run, clean-payload acceptance, standalone upgrade backup, managed rollback, and idempotent uninstall; the Codex Plugin Manager owns Plugin lifecycle | Standalone and Plugin use the same exact runtime allowlist. README, development guidance, tests, evals, and build scripts are not installed into the user copy. |

### Prefer native management; continue through safe fallbacks

After receiving the repository URL, the AI first uses the host's supported Skill, Plugin, or Marketplace manager. That manager owns paths, upgrades, and uninstall, while the installed core runs `scripts/install.py --verify-only` for read-only acceptance; never copy or delete host Plugin cache directly. The OpenAI Plugin is an optional distribution layer and must contain the same Skill core. Its short Hook may be reported as `hook_observed` only after normal trust review and observation in a new task, and still is not Skill activation. If the native route did not commit, the AI must resolve the exact target, scope, and discovery roots and mark the Installing Agent's host-contract note as `reported-unverified`. The Python 3.9+ repository installer may continue only when an identical dry-run returns `transaction_capability=verified`; that status proves file-write and two-way-rename transaction capability only, not Plugin registration, Skill discovery, Hook trust, or current-turn activation. Verified placement additionally requires reversible staging, atomic activation, and complete acceptance.

A Git URL is not itself a safe installation protocol: other repositories may contain different layouts, executable scripts, hooks, MCP, or external dependencies. The installation AI must identify the manager and permission boundary first. An uncommitted failed attempt does not lock the manager; committed upgrade ownership must not change silently, and `--force` must not be used on an unknown target directory. First explicit activation and identity matching still belong in a new session; file presence or a listed Plugin is not current-turn activation.

For contributors running directly from a source checkout, first `setup` fails closed by default so a repository read cannot impersonate an activated Skill. Only explicit local-development testing may set `EXPERIENCE_LOOP_DEVELOPER_SOURCE=1`, and that variable is never host-activation evidence.

### Further reading

- **Installation and hosts** — [AI installation protocol](docs/AI_INSTALL.en.md) · [Dynamic host contract](references/host-compatibility.md)
- **Actual Agent behavior** — [Core Skill instructions](SKILL.md) · [Adaptive workflow](references/workflow.md)
- **Onboarding and growth model** — [Conversational onboarding](references/onboarding.md) · [Capability compass](references/capability-compass.md)
- **Sources and privacy** — [Knowledge Lens](references/knowledge-lens.md) · [Safety and privacy](references/safety-and-privacy.md)
- **Project maintenance** — [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

<div align="center">
  <p><strong>Detect automatically, decide intelligently: strengthen human judgment without limiting Agent intelligence.</strong></p>
</div>
