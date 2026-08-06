# Delivery-first adaptive workflow

Use this reference to control intervention cost, choose checkpoints, calibrate delegation, review Agent work, or run a retrospective.

## Contents

- [What the loop optimizes](#what-the-loop-optimizes)
- [Adaptive controller](#adaptive-controller)
- [Mode recipes](#mode-recipes)
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
| Pressure | outage, broken release, explicit deadline, “just fix it” | suppress learning interruptions; recover first |
| Consequence | security, data, compatibility, migration, production, irreversibility | increase verification, review, rollback, and acceptance rigor |
| Uncertainty | ambiguous outcome, unfamiliar boundary, competing causes, weak tests | inspect first; ask one blocking question only if the answer changes the deliverable |
| Growth value | recurring responsibility, transferable mechanism, weak prior evidence | spend one checkpoint when pressure allows |

Apply this decision order:

1. Satisfy safety, authorization, privacy, and destructive-action requirements.
2. Restore health or protect the deadline.
3. Match verification depth to consequence and failure mode.
4. Resolve material ambiguity.
5. Use remaining attention for one reusable judgment.
6. Stay silent when no durable value remains.

Recalculate after new evidence. A failed test may raise uncertainty or consequence; a successful minimal reproduction may lower both. Do not lock the task into its opening behavior.

## Mode recipes

### Auto

1. State the outcome and acceptance evidence.
2. Inspect, decide, and execute normally.
3. Surface at most one consequential recommendation for optional challenge.
4. Validate with risk-appropriate evidence and preserve cognitive coverage.
5. End with at most one reusable cue when one truly emerged.

Require zero learning answers. Target overhead: seconds, not minutes.

### Focus

1. Establish one capability goal tied to the deliverable.
2. Invite one prediction, trade-off, or acceptance judgment.
3. Execute and verify rather than pausing for a lecture.
4. Compare the user's model with evidence.
5. Use one review seam or small variation to strengthen transfer.
6. Run a proportionate After Action Review.

Use no more than two purposeful checkpoints unless the user explicitly requests an open-ended study session. If urgency appears, temporarily behave like `auto` recovery and return to focus only after stability.

### Off

Execute the request normally. Do not add checkpoints, teaching sections, ledger events, reminders, or source-based lessons unless the user explicitly asks for them.

Accept legacy mode names for compatibility, but never make the user learn them: `ship` and `incident` map to `auto`; `coach` and `deep` map to `focus`.

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

Prefer a judgment that is both task-critical and reusable:

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

Ask before revealing decisive evidence only in `focus`, or as an optional challenge in `auto`. Never hide safety-critical information.

Good prompts take under a minute to answer:

- “Which component owns this invariant?”
- “What result would falsify the caching hypothesis?”
- “Which test would catch the regression with the smallest scope?”
- “What compatibility risk do you expect from this API change?”
- “Should this be Agent work or deterministic automation next time, and why?”

Bad prompts test trivia, require long essays, repeat known facts, ask the user to guess tool-discoverable information, or delay an urgent fix.

If the user does not answer an optional checkpoint, proceed immediately with a stated hypothesis. Do not ask again.

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

The Agent, not the user, handles routine ledger plumbing. After a non-trivial task, record no more than one or two events and only when final evidence supports a durable decision, verification, correction, reflection, or transfer.

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
