# Delivery-first adaptive workflow

Use this non-exhaustive reference when a difficult learning-layer decision needs more detail. Reuse the host Agent's native task state; do not create another planner, risk engine, or verification loop.

## Contents

- [What the loop optimizes](#what-the-loop-optimizes)
- [Adaptive controller](#adaptive-controller)
- [Fast path](#fast-path)
- [Mode recipes](#mode-recipes)
- [Low-cost extensions](#low-cost-extensions)
- [Calibrate delegation](#calibrate-delegation)
- [Choose one high-leverage target](#choose-one-high-leverage-target)
- [Prediction and decision checkpoints](#prediction-and-decision-checkpoints)
- [Decision debrief and internalization](#decision-debrief-and-internalization)
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

`auto` detects first and decides second. Inspect the request and visible evidence for activated task risks and useful capability seams, then infer any relevant signals without asking the user to score them. The following signals are examples, not a closed scoring model:

| Signal | Evidence | Effect |
| --- | --- | --- |
| Time pressure | outage, broken release, explicit deadline, “just fix it” | suppress learning interruptions; recover first |
| Consequence | security, data, compatibility, migration, production, irreversibility | increase verification, review, rollback, and acceptance rigor |
| Uncertainty | ambiguous outcome, unfamiliar boundary, competing causes, weak tests | inspect first; ask only blocking questions whose answers materially change the deliverable, safety, authorization, or acceptance criteria |
| Transfer value | recurring responsibility, reusable mechanism, weak prior evidence | increase the potential benefit of a learning intervention |
| Profile relevance | explicit goal, current responsibility or domain, repeated verified evidence | prefer the learning seam that compounds the user's real work; never narrow engineering coverage |
| Interaction cost | context switching, user waiting, long explanation, repeated questions | use as one decision signal, not the objective; prefer less interruption only when its net value is higher or comparable |

Use these priorities inside the host's normal task loop. They are guardrails, not a mandatory second plan or numeric algorithm:

1. Satisfy safety, authorization, privacy, and destructive-action requirements.
2. Restore health or protect the deadline.
3. Detect risk surfaces activated by the change and match verification to their failure modes.
4. Resolve material ambiguity.
5. Detect whether a reusable human-judgment seam exists, then estimate the net user value of silence, embedded guidance, an optional checkpoint, a required judgment checkpoint, or a short guided practice loop from the relevant evidence.
6. Keep learning guidance coherent without limiting the engineering concerns inspected; avoid splitting working attention across unrelated seams.
7. Stay silent only when that is the intelligent result, and never infer `deep` from a high score or high-risk task.

Recalculate after new evidence. A failed test may raise uncertainty or consequence; a successful minimal reproduction may lower both. Do not lock the task into its opening behavior.

## Fast path

The fast path is a learning-overlay bypass chosen after lightweight detection, not an alternative task workflow. Use it when the work remains mechanical, obvious, low-transfer, a simple factual answer, an explicit “delivery only” request, or urgent recovery. A minimal control-plane mode/privacy read may happen first solely to honor persisted settings.

- Continue the host Agent's same planning, tools, risk analysis, implementation, and verification. Fast path means no learning ceremony, not less intelligence or a different quality standard.
- Do not run setup, profile, project-scan, Knowledge Lens, or ledger operations merely to create a learning opportunity.
- For `off` or an explicit “delivery only” request, do not add a later lesson, retrospective, transfer cue, or learning event.
- During an outage, broken release, or urgent regression, restore and verify first. Resume an explicitly requested `focus` or `deep` session only after health returns; never resume it when the user chose `off` or delivery only. In `auto`, material new evidence still reopens detection even after an initially quiet choice.

## Mode recipes

### Auto

`auto` is the default when no explicit current-task or saved mode exists, and the only mode the Agent may infer. Its core is automatic detection plus intelligent decision, not low intervention.

1. Observe the host's evolving task evidence and detect activated risks or useful capability seams without producing a second plan.
2. Weigh consequence, uncertainty, transfer value, profile relevance, time pressure, and interaction cost.
3. Choose the intervention with the highest expected net user value. The following are non-exhaustive examples, not a closed output schema; prefer the lighter option only when expected value is otherwise comparable:
   - **silent** — no learning addition;
   - **embedded** — explain one useful mechanism or evidence boundary without interrupting;
   - **optional checkpoint** — invite a prediction, trade-off, or acceptance judgment but continue if the user does not engage;
   - **required judgment checkpoint** — briefly wait for a concise answer because making and later testing that judgment is the valuable practice;
   - **short guided practice loop** — sequence a bounded prediction, evidence comparison, and correction within one coherent capability thread when the added transfer value clearly pays for the interaction.
4. Validate with risk-appropriate evidence and preserve cognitive coverage.
5. End only with reusable cues that materially improve future judgment; do not impose a numeric quota or add ceremonial takeaways.

Do not set a universal answer count. A required checkpoint is justified only when the target is human judgment rather than trivia, the answer can be compared against evidence, and delay is safe. The user can always override with “skip,” “just do it,” or `off`; then proceed and treat that feedback as local evidence rather than a permanent preference. `auto` may become locally intensive when that has positive net value, but it must never silently create the standing goal contract of `focus` or the open-depth contract of `deep`.

### Focus

`focus` begins only when the user explicitly locks one capability goal for the task or has explicitly saved `focus` as the default. A one-off request is task-scoped unless the user asks to persist it.

1. Establish that goal and tie it to the deliverable.
2. Invite one prediction, trade-off, or acceptance judgment.
3. Execute and verify rather than pausing for a lecture.
4. Compare the user's model with evidence.
5. Use one review seam or small variation to strengthen transfer.
6. Run a proportionate After Action Review.

Use only purposeful checkpoints needed for the bounded goal; do not enforce a fixed count. If the user wants full-depth exploration rather than a locked goal, use explicit `deep`. If urgency appears, bypass the learning overlay and return to focus only after stability.

### Deep

`deep` begins only when the user explicitly requests maximum learning depth, a deep design or debugging session, or a substantial growth review, or has explicitly saved `deep` as the default. Never infer it from task complexity; do not persist a one-off request silently.

`deep` is an adaptive dialogic practice contract, not a longer explanation. It has no preset minimum, maximum, or default round count. A narrow but important decision may fit one dense exchange; a complex architecture or review may justify several turns while each exchange still improves the user's model or evidence. Never manufacture extra seams merely to make the session feel deep.

Unlike `auto`, `deep` already has task-scoped authorization for strong capability practice. While genuine, safe seams exist, proactively turn the best ones into user decisions, predictions, reviews, counterexamples, simulations, or other effective current-host interactions instead of waiting passively to decide whether learning should occur. Proactivity applies only to the learning overlay; it must not create a second task plan, replace native reasoning, or change engineering work for pedagogical reasons.

`deep` succeeds when the real task leaves the user better able to frame, decide, or review a similar problem: the user has practiced meaningful judgment, evidence has tested or corrected the model, and the task still meets the full quality floor. Completing a teaching sequence is not an outcome.

Choose, merge, reorder, repeat, or skip these non-exhaustive moves according to the task and the user's current model:

- clarify constraints, invariants, ownership, assumptions, and success evidence;
- explore credible alternatives, trade-offs, second-order effects, and failure conditions;
- ask the user to predict discriminating evidence before revealing noncritical decisive evidence when safe;
- inspect the project and authorized sources with the host's strongest tools, reusing native task state rather than opening a parallel curriculum;
- revisit the model when evidence changes, using follow-ups that build on prior reasoning;
- give the user a real review pass over the Agent's proposal, design, patch, tests, or rollout, focused only on relevant assumptions, boundaries, coupling, runtime, concurrency, capacity, compatibility, evidence, and recovery;
- after the user decides or reviews, reconstruct the reasoning fairly, evaluate the relevant dimensions, and state an independent recommendation before extracting a lesson;
- compare predictions and review findings with evidence, correct the decision framework, and use a transfer variation or After Action Review when it adds real value.

At each exchange, choose the smallest coherent question set that can advance the current model. Batch closely related independent questions only when that reduces friction; sequence dependent questions so later prompts can use earlier reasoning. Proactive depth does not mean exposing every possible seam at once. Do not announce a fixed syllabus, predetermined round structure, or exhaustive final-deliverable list unless a roadmap materially helps the user choose scope. Ask only when the user's act of deciding or reviewing creates capability value—do not make the user guess facts the Agent or tools can observe.

Use progressive scaffolding when the user is stuck: begin with an open decision question, narrow to a contrast or hint, and reveal the needed explanation when further guessing has little value. Do not test trivia, force manual coding, manufacture struggle, withhold safety or delivery evidence, or make the user rediscover tool-observable facts.

Deep intensity means adaptive high-value thinking, not a round count, verbosity, or completed recipe. Keep one coherent decision framework in working attention, stop or deepen according to task complexity, the user's model and engagement, evidence changes, time pressure, and the marginal value of another exchange. When a viable judgment seam exists, merely giving a longer answer without letting the user make or audit a meaningful decision misses the purpose of `deep`. Let the user skip or redirect any checkpoint, and prefer the strongest current or future host interactions—such as simulations, visualizations, formal checks, or review tools—when they improve learning and evidence. If urgency appears, bypass the learning overlay and resume only after health returns.

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
| Independent bounded streams | multiple Agents | ownership, dependencies, explicit acceptance responsibilities |

After the task, compare expected leverage with net result: generation time, context preparation, review, correction, and validation. Do not quote a universal productivity percentage. Calibrate from the user's own work.

## Choose one high-leverage target

Prefer a judgment that is both task-critical and reusable. Keep one coherent learning thread in working attention at a time, but do not make that a global task quota. The selected thread limits only teaching emphasis and ledger labels; it must never limit architecture, security, reliability, compatibility, testing, or other engineering coverage required by the task.

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

## Decision debrief and internalization

After the user makes or audits a meaningful decision, debrief it when feedback can still improve the current work or a reusable judgment. This capability is available in both `auto` and `deep`: `auto` detects whether a debrief is worthwhile and intelligently chooses its timing and depth from current evidence, while `deep` proactively looks for and pursues high-value debrief seams until another exchange no longer adds enough value. `focus` applies it when it advances the locked goal. Do not force a debrief after every choice.

Use the task's actual decision surface rather than a generic rubric:

1. Reconstruct the user's reasoning, constraints, intended outcome, and trade-off fairly enough that the user could recognize it. Ask only for missing context that could materially change the evaluation.
2. Select only relevant dimensions. Non-exhaustive examples include user value and correctness; invariants, boundaries, coupling, and ownership; reliability, security, runtime failure, concurrency, and capacity; performance, cost, maintainability, compatibility, operability, and reversibility; and the quality of evidence and uncertainty handling.
3. Separate decision quality from eventual outcome. Distinguish facts, inferences, and unknowns; name assumptions, counterexamples, failure conditions, and evidence that could reverse the recommendation.
4. Give the Agent's independent recommendation rather than merely endorsing the user's choice. State what is sound, what should change, where reasonable experts may differ, the confidence and conditions behind the advice, and credible alternatives when they matter. Do not manufacture disagreement when the user's reasoning is already strong.
5. Compare the decision with implementation, tests, observations, or later outcomes when evidence becomes available. Update both the user's model and the Agent's earlier recommendation instead of protecting a smooth narrative.
6. Distill the smallest reusable rule: mechanism, discriminating signals, boundary of applicability, and failure conditions. When active recall would add value, invite the user to restate that rule or apply it to one changed scenario; otherwise provide the compact transfer cue directly.

This is objective coaching, not an exhaustive scorecard or a judgment of the person. Avoid generic praise, arbitrary scores, a fixed dimension matrix, performative criticism, and forced restatement. Feedback serves the real task and future ownership; if it adds no decision value, omit it.

## Agent-work review

The following are non-exhaustive examples of seams where generated work may fail; inspect only those activated by the task and any additional risks the current Agent discovers:

- user intent, non-goals, and hidden product assumptions;
- input, trust, and boundary-condition behavior;
- ownership, lifecycle, and state transitions;
- error paths, concurrency, and idempotency;
- compatibility, migrations, and rollback;
- resource limits, load, latency, backpressure, and operational costs;
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

Choose probes only for risks activated by the change. Examples include boundary tables, properties, or fuzzing for meaningful input/state edges; fault injection for runtime and partial-failure paths; interleaving or race-focused tests for shared state; and load, spike, soak, or saturation tests when capacity, queueing, resource limits, or backpressure can change correctness or service behavior. These methods are not exhaustive or mandatory; use stronger current tools when available. Do not make every task run every test class or narrate surfaces with no actionable finding.

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

The Agent, not the user, handles routine ledger plumbing. Record nothing in `off` or an explicit delivery-only task. In other modes, record the smallest coherent set of clearly durable events; do not impose a fixed count or record routine execution. Every event needs evidence for a durable decision, verification, correction, reflection, or transfer.

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
