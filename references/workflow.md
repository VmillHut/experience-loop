# Delivery-first workflow

Use this reference to choose checkpoints, tune learning depth, review agent work, or run a retrospective.

## What the loop optimizes

Optimize two outcomes together:

- complete the requested engineering work with appropriate evidence;
- increase the developer's ability to make or audit a similar decision later.

Do not optimize for explanation length, quiz count, or how much code the developer types manually.

## Choose one high-leverage target

A useful learning target is both relevant to the current task and reusable. Prefer:

- locating the true system boundary;
- selecting evidence that distinguishes competing diagnoses;
- understanding why an abstraction or data model fits;
- identifying failure modes and rollback strategy;
- recognizing a security, concurrency, performance, or compatibility constraint;
- reviewing generated code for hidden assumptions;
- deciding what not to change.

Skip a checkpoint when the task is mechanical, the answer is already obvious to the user, the decision is reversible and low-risk, or the explanation would exceed its future value.

## Mode recipes

### Ship

1. State the task and acceptance evidence.
2. Inspect and execute normally.
3. At one important fork, state the recommended choice and trade-off; let the user challenge it.
4. Validate.
5. End with one reusable cue only if it is genuinely useful.

Target overhead: seconds, not minutes.

### Coach

1. Ask for one prediction before inspecting decisive evidence.
2. Execute while explaining the chosen boundary or test strategy.
3. Ask the user to review one meaningful seam.
4. Compare prediction with evidence.
5. Record a transfer cue.

### Deep

1. Establish a specific capability goal.
2. Elicit the user's model and alternatives.
3. Inspect the project and, when relevant, retrieve Knowledge Lens evidence.
4. Let the user make one consequential decision.
5. Execute and test the hypothesis.
6. Run a full After Action Review.
7. Create a later variation that requires transfer, not recall.

### Incident

1. Define health and containment signals.
2. Triage, mitigate, fix, and validate without teaching interruptions.
3. Preserve a decision/evidence timeline.
4. After stability, reconstruct expected versus observed behavior.
5. Extract one detection or prevention improvement and one transfer cue.

### Off

Execute the request normally. Do not add checkpoints, teaching sections, ledger events, reminders, or source-based lessons unless the user explicitly asks.

## Recording policy

The Agent, not the user, handles routine ledger plumbing. After a non-trivial task, record no more than one or two events and only when the final evidence supports a durable decision, verification, correction, or reflection. Never record generated-code volume, tool use, or task completion alone.

Use a transfer event only on a later task with a materially different context. It must link to the earlier event, name the shared concept and changed context, and include an observable outcome plus verifiable evidence. Otherwise it is rehearsal or a future transfer cue, not demonstrated transfer.

## Prediction checkpoints

Ask predictions before revealing decisive evidence, but never hide safety-critical information. Good prompts take under a minute to answer:

- “Which component owns this invariant?”
- “What result would falsify the caching hypothesis?”
- “Which test would catch the regression with the smallest scope?”
- “What compatibility risk do you expect from this API change?”

Bad prompts test trivia, require long essays, repeat facts already stated, or ask the user to guess information only the tool can inspect.

If the user does not answer, proceed with a stated hypothesis. Do not repeatedly ask.

## Decision records

For consequential choices, capture:

```text
Context: observable problem and constraints
Options: credible alternatives
Decision: selected option
Why: mechanism and trade-off
Expected evidence: what should become true
Failure/rollback: how to detect and recover
```

Do not create formal architecture records for routine local choices. A compact ledger event is enough.

## Agent-work review

Help the developer review by directing attention to seams where generated work commonly fails:

- input and trust boundaries;
- ownership and lifecycle;
- state transitions and error paths;
- concurrency and idempotency;
- compatibility and migrations;
- resource and performance costs;
- tests that could pass for the wrong reason;
- scope creep or duplicated abstractions.

Ask for an acceptance judgment tied to evidence: “Does this test prove the invariant?” is better than “Do you understand?”

## Verification quality

Match verification to the failure mode. A green command is evidence only after checking what it covers. Distinguish:

- static consistency;
- unit behavior;
- integration boundaries;
- runtime behavior;
- build/package success;
- production or device behavior.

Never upgrade a narrow check into a broad claim. If a check cannot run, identify the missing authority or environment and provide the next best check.

## After Action Review

Use these prompts selectively:

1. What did we expect, and why?
2. What happened, with what evidence?
3. Which assumption was wrong or incomplete?
4. Which behavior should we repeat or change?
5. In what different situation should this lesson reappear?

Focus on the decision process, not hindsight blame. Record contradictions and corrections because they are stronger learning evidence than a smooth narrative.

## Transfer exercises

Prefer a small variation that changes one dimension:

- same invariant in another module;
- same failure mode in another technology;
- same architecture choice under a different constraint;
- review an intentionally flawed patch;
- choose validation for a similar bug without seeing the prior solution.

Do not schedule transfer during an active deadline unless requested. A reminder without a future task is not evidence of transfer.

## Anti-patterns

Avoid:

- tutorials before every code change;
- quizzes unrelated to the deliverable;
- forcing manual coding as proof of learning;
- hiding the answer to manufacture struggle;
- generic praise or XP for clicking through;
- long retrospectives for trivial work;
- teaching from a book when project evidence contradicts it;
- turning every local decision into architecture ceremony.
