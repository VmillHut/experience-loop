# Delivery-first adaptive workflow

Use this reference to control intervention cost, choose checkpoints, calibrate delegation, review Agent work, or run a retrospective.

## Contents

- [What the loop optimizes](#what-the-loop-optimizes)
- [Adaptive controller](#adaptive-controller)
- [Fast path](#fast-path)
- [Mode recipes](#mode-recipes)
- [Low-cost extensions](#low-cost-extensions)
- [Calibrate delegation](#calibrate-delegation)
- [Choose one high-leverage target](#choose-one-high-leverage-target)
- [Prediction and decision checkpoints](#prediction-and-decision-checkpoints)
- [Agent-work review](#agent-work-review)
- [Verification and cognitive coverage](#verification-and-cognitive-coverage)
- [Three feedback loops](#three-feedback-loops)
- [Recording policy](#recording-policy)
- [After Action Review](#after-action-review)
- [Transfer and ownership practice](#transfer-and-ownership-practice)
- [Anti-patterns](#anti-patterns)

## What the loop optimizes

Optimize three outcomes together:

- complete the requested engineering work with appropriate evidence;
- increase the developer's ability to make or audit a similar decision later;
- reduce future Agent failure and review cost by improving the surrounding harness.

Do not optimize for explanation length, quiz count, mode usage, generated-code volume, or how much code the developer types manually.

## Adaptive controller

Infer these signals from the request and visible evidence. Do not ask the user to score them:

| Signal | Evidence | Effect |
| --- | --- | --- |
| Time pressure | outage, broken release, explicit deadline, “just fix it” | suppress learning interruptions; recover first |
| Consequence | security, data, compatibility, migration, production, irreversibility | increase verification, review, rollback, and acceptance rigor |
| Uncertainty | ambiguous outcome, unfamiliar boundary, competing causes, weak tests | inspect first; ask one blocking question only if the answer changes the deliverable |
| Transfer value | recurring responsibility, reusable mechanism, weak prior evidence | increase the potential benefit of a learning intervention |
| Profile relevance | explicit goal, current responsibility or domain, repeated verified evidence | prefer the learning seam that compounds the user's real work; never narrow engineering coverage |
| Interaction cost | context switching, user waiting, long explanation, repeated questions | prefer silence or embedded guidance when interruption cost outweighs future value; permit a bounded pause when participation clearly pays back |

Apply this decision order:

1. Satisfy safety, authorization, privacy, and destructive-action requirements.
2. Restore health or protect the deadline.
3. Match verification depth to consequence and failure mode.
4. Resolve material ambiguity.
5. Estimate the net user value of silence, embedded guidance, an optional checkpoint, a required judgment checkpoint, or a short guided practice loop from all six signals.
6. Use at most one learning seam without limiting the engineering concerns inspected.
7. Stay silent when no durable value remains, and never infer `deep` from a high score or high-risk task.

Recalculate after new evidence. A failed test may raise uncertainty or consequence; a successful minimal reproduction may lower both. Do not lock the task into its opening behavior.

## Fast path

Use the fast path before loading content-bearing learning state or references when the work is mechanical, obvious, low-transfer, a simple factual answer, an explicit “delivery only” request, or urgent recovery. A minimal control-plane mode/privacy read may happen first solely to honor persisted settings.

- Execute and verify with normal engineering rigor. Fast path means no learning ceremony, not lower task quality.
- Do not run setup, profile, project-scan, Knowledge Lens, or ledger operations merely to create a learning opportunity.
- For `off` or an explicit “delivery only” request, do not add a later lesson, retrospective, transfer cue, or learning event.
- During an outage, broken release, or urgent regression, restore and verify first. Resume an explicitly requested `focus` or `deep` session only after health returns; never resume it when the user chose `off` or delivery only.

## Mode recipes

### Auto

`auto` is the default when no explicit current-task or saved mode exists, and the only mode the Agent may infer. It is an expected-net-value controller, not a synonym for low intervention.

1. State the outcome and acceptance evidence, then inspect and execute normally.
2. Weigh consequence, uncertainty, transfer value, profile relevance, time pressure, and interaction cost.
3. Choose the intervention with the highest expected net user value. Prefer the lighter option only when expected value is otherwise comparable:
   - **silent** — no learning addition;
   - **embedded** — explain one useful mechanism or evidence boundary without interrupting;
   - **optional checkpoint** — invite a prediction, trade-off, or acceptance judgment but continue if the user does not engage;
   - **required judgment checkpoint** — briefly wait for a concise answer because making and later testing that judgment is the valuable practice;
   - **short guided practice loop** — sequence a bounded prediction, evidence comparison, and correction within one learning seam when the added transfer value clearly pays for the interaction.
4. Validate with risk-appropriate evidence and preserve cognitive coverage.
5. End with at most one reusable cue when one truly emerged.

Do not set a universal answer count. A required checkpoint is justified only when the target is human judgment rather than trivia, the answer can be compared against evidence, and delay is safe. The user can always override with “skip,” “just do it,” or `off`; then proceed and lower later interruption. `auto` may become locally intensive when that has positive net value, but it must never silently create the standing goal contract of `focus` or the open-depth contract of `deep`.

### Focus

`focus` begins only when the user explicitly locks one capability goal for the task or has explicitly saved `focus` as the default. A one-off request is task-scoped unless the user asks to persist it.

1. Establish that goal and tie it to the deliverable.
2. Invite one prediction, trade-off, or acceptance judgment.
3. Execute and verify rather than pausing for a lecture.
4. Compare the user's model with evidence.
5. Use one review seam or small variation to strengthen transfer.
6. Run a proportionate After Action Review.

Use one or two purposeful checkpoints. If the user wants full-depth exploration rather than a locked, bounded goal, use explicit `deep`. If urgency appears, take the fast path and return to focus only after stability.

### Deep

`deep` begins only when the user explicitly requests maximum learning depth, a deep design or debugging session, or a substantial growth review, or has explicitly saved `deep` as the default. Never infer it from task complexity; do not persist a one-off request silently.

1. Establish the deliverable and the mental model or capability question to resolve.
2. Elicit the user's current model, credible alternatives, and expected evidence without hiding information needed for safe delivery.
3. Inspect the project and relevant sources, data, or exemplar mechanisms when the request authorizes them.
4. Use usually two to four purposeful checkpoints at genuine decision seams.
5. Execute or test the hypothesis with the same or stronger task-quality floor as every other mode.
6. Compare predictions with evidence, analyze failure conditions, and run a full but relevant After Action Review.
7. Create one realistic transfer variation when it adds value.

Full intensity is positive, not punitive: never force manual coding, manufacture struggle, withhold decisive answers, or trade correctness, verification, safety, or useful Agent work for pedagogy. If urgency appears, take the fast path and resume only after health returns.

### Off

Execute the request normally. Apart from a minimal control-plane read needed to honor a saved `off`, do not consume learning-profile context, add checkpoints, teaching sections, learning summaries, ledger events, reminders, or an after-the-fact learning tail. A source, structured-data, or exemplar-project operation the user explicitly requested remains part of the task and should still run without a learning overlay.

Accept legacy mode names for compatibility, but never make the user learn them: `ship` and `incident` map to `auto`; `coach` maps to `focus`; `deep` is a first-class current mode.

## Low-cost extensions

Keep these capabilities orthogonal to mode and load them only when the current request benefits:

- **Articles, books, and documents** — inspect only relevant material for one-off use; ingest into Knowledge Lens when reuse, precise citation, or cross-task retrieval justifies persistence.
- **Structured data** — analyze CSV, JSON, tables, logs, or similar data directly for the current question. Do not imply that every data format belongs in Knowledge Lens.
- **High-quality or exemplar projects** — require a path and one comparison question, inspect read-only and only along relevant paths, keep the project separate from the active workspace, and compare mechanisms and evidence instead of copying patterns blindly.

No mode should ingest a source or scan an exemplar merely because a path was mentioned. `focus` and `deep` may use these extensions more deeply when explicitly requested; `off` still honors an explicit analysis request without adding a learning layer.

## Calibrate delegation

Choose the worker from task properties, not habit:

| Work shape | Default owner | Required control |
| --- | --- | --- |
| Stable, repetitive, deterministic | script or traditional automation | exact input/output checks |
| Bounded, reversible, testable implementation | Agent | narrow scope, tests, diff review |
| Ambiguous product or architecture choice | human decision with Agent analysis | options, consequences, explicit acceptance |
| High-consequence or irreversible action | human authority plus guarded tools | approval, least privilege, rollback, audit |
| Independent bounded streams | multiple Agents | ownership, dependencies, shared acceptance gate |

After the task, compare expected leverage with net result: generation time, context preparation, review, correction, and validation. Do not quote a universal productivity percentage. Calibrate from the user's own work.

## Choose one high-leverage target

Prefer a judgment that is both task-critical and reusable. Selecting one learning seam limits only the teaching intervention and ledger label; it must never limit architecture, security, reliability, compatibility, testing, or other engineering coverage required by the task.

- defining the actual outcome or non-goal;
- locating the true system boundary;
- selecting evidence that distinguishes competing diagnoses;
- understanding why an abstraction or data model fits;
- identifying failure modes and rollback strategy;
- recognizing a security, concurrency, performance, or compatibility constraint;
- reviewing generated code for hidden assumptions;
- deciding what not to change;
- deciding whether Agent delegation is appropriate at all.

Skip a checkpoint when the task is mechanical, the answer is already obvious, the decision is reversible and low-risk, or the explanation would exceed its future value.

## Prediction and decision checkpoints

Ask before revealing noncritical decisive evidence in `focus`, `deep`, or an `auto` checkpoint only when the pause adds value. In `auto`, mark the prompt as optional or required through the conversational behavior: continue immediately for optional prompts; briefly wait for required judgment prompts. Never hide safety-critical or delivery-critical information.

Good prompts take under a minute to answer:

- “Which component owns this invariant?”
- “What result would falsify the caching hypothesis?”
- “Which test would catch the regression with the smallest scope?”
- “What compatibility risk do you expect from this API change?”
- “Should this be Agent work or deterministic automation next time, and why?”

Bad prompts test trivia, require long essays, repeat known facts, ask the user to guess tool-discoverable information, or delay an urgent fix.

If the user does not answer an optional checkpoint, proceed immediately with a stated hypothesis. If the user explicitly skips a required checkpoint, proceed without penalty and adapt later intervention downward. Do not ask the same question again.

For consequential choices, capture:

```text
Context: observable problem and constraints
Options: credible alternatives
Decision: selected option and owner
Why: mechanism and trade-off
Expected evidence: what should become true
Failure/rollback: how to detect and recover
```

Do not create formal architecture records for routine local choices.

## Agent-work review

Direct attention to seams where generated work commonly fails:

- user intent, non-goals, and hidden product assumptions;
- input and trust boundaries;
- ownership, lifecycle, and state transitions;
- error paths, concurrency, and idempotency;
- compatibility, migrations, and rollback;
- resource, latency, and operational costs;
- tests that can pass for the wrong reason;
- scope creep, duplicated abstractions, and unrelated changes;
- claims that exceed local or production evidence.

Ask for an acceptance judgment tied to evidence only when user ownership benefits from it. “Does this test prove the invariant?” is better than “Do you understand?”

## Verification and cognitive coverage

Match verification to the failure mode. A green command is evidence only after checking what it covers. Distinguish:

- static consistency;
- unit behavior;
- integration boundaries;
- runtime behavior;
- build and packaging success;
- production, device, or real-user behavior.

Before accepting consequential work, ensure a maintainer can recover:

1. what changed;
2. why the mechanism should work;
3. what evidence supports it;
4. what remains unknown;
5. how failure will be detected and reversed.

Scale review by consequence:

- high consequence: deep human review, strict tests, approvals, observability, and rollback;
- normal reversible change: automated gates plus one meaningful seam;
- low-risk quick rollback: automated evidence, monitoring, and compact diff review.

Never upgrade a narrow check into a broad claim. If a check cannot run, identify the missing authority or environment and name the next best check.

## Three feedback loops

Keep all three loops visible without forcing all three into every task:

1. **Agent loop** — implementation, tests, tools, and immediate feedback.
2. **Developer loop** — correction of requirements, trade-offs, evidence, and acceptance.
3. **Reality loop** — user behavior, production telemetry, incidents, business outcomes, and maintenance cost.

Local completion closes only the first two. When the claimed value depends on reality, state the later signal, owner, or monitoring boundary instead of pretending the result is fully proven.

## Recording policy

The Agent, not the user, handles routine ledger plumbing. Record nothing in `off` or an explicit delivery-only task. In `auto`, record at most one clearly durable event; in `focus` or `deep`, record no more than one or two events. In every mode, final evidence must support a durable decision, verification, correction, reflection, or transfer.

Assign one of the six capability directions only when the mapping is clear. Omit it rather than forcing a label. Never record generated-code volume, tool use, task completion alone, or an inferred weakness without evidence.

Use a transfer event only on a later task with a materially different context. It must link to the earlier event, name the shared concept and changed context, and include an observable outcome plus verifiable evidence.

## After Action Review

Use these prompts selectively:

1. What did we expect, and why?
2. What happened, with what evidence?
3. Which assumption was wrong or incomplete?
4. Did Agent delegation reduce net work after review and correction?
5. Which test, rule, tool, or observable signal would prevent recurrence?
6. In what different situation should this lesson reappear?

Focus on the decision process, not hindsight blame. Contradictions and caught-Agent errors are stronger learning evidence than a smooth narrative.

## Transfer and ownership practice

Prefer a later real task or a small variation that changes one dimension:

- the same invariant in another module;
- the same failure mode in another technology;
- the same architecture choice under a different constraint;
- review an intentionally flawed patch;
- choose validation for a similar bug without seeing the prior solution;
- decide whether a similar task should use an Agent or a deterministic script.

Suggest a short no-Agent ownership exercise only after repeated evidence of lost mental models or excessive scaffolding. Keep it optional, under about ten minutes when possible, and attached to a real system. A reminder without a future task is not transfer evidence.

## Anti-patterns

Avoid:

- asking the user to choose a mode for every task;
- exposing an internal risk or learning score;
- tutorials before code changes;
- quizzes unrelated to the deliverable;
- forcing manual coding as proof of learning;
- hiding the answer to manufacture struggle;
- generic praise, streaks, or XP for activity;
- long retrospectives for trivial work;
- teaching from a book when project evidence contradicts it;
- treating all missing capability categories as deficits;
- using Agent output volume as productivity evidence;
- turning every local decision into architecture ceremony.
