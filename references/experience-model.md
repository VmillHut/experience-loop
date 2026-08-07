# Experience evidence model

Use this reference when recording events, estimating confidence, interpreting capability evidence, creating progress summaries, or deciding whether learning transferred.

## Contents

- [Principle](#principle)
- [Evidence ladder](#evidence-ladder)
- [Event semantics](#event-semantics)
- [Capability directions](#capability-directions)
- [Assistance levels](#assistance-levels)
- [Confidence](#confidence)
- [Corrections](#corrections)
- [Capability and progress summaries](#capability-and-progress-summaries)
- [Learning targets](#learning-targets)
- [Transfer criteria](#transfer-criteria)

## Principle

Treat experience as evidence of increasingly independent judgment under real constraints. Do not equate exposure, generated output, fluent explanation, task completion, or activity counts with capability.

## Evidence ladder

From weakest to strongest:

1. **Exposure** — the developer saw an explanation or solution.
2. **Recognition** — the developer identified the relevant concept with cues.
3. **Prediction** — the developer predicted behavior or useful evidence before seeing the result.
4. **Decision** — the developer selected an option and articulated a trade-off.
5. **Verification** — the developer chose or audited evidence that actually covered the claim.
6. **Correction** — the developer found an Agent error, weak assumption, or misleading test.
7. **Transfer** — the developer applied the principle in a materially different context.
8. **Reduced scaffolding** — the developer repeated the capability with fewer prompts while preserving quality.
9. **Ownership** — the developer connected the decision to real-user or production outcomes and accepted responsibility for follow-through.

Use levels as descriptors, not grades. A single strong event should not imply mastery.

## Event semantics

Keep the ledger append-only. An event should identify only what the evidence supports:

- event ID and timestamp;
- user/project/task identity without unnecessary personal content;
- saved mode and relevant task pressure;
- at most one capability direction;
- prediction, decision, verification, correction, reflection, or transfer;
- evidence observed and verification scope;
- outcome, including later user or production evidence when available;
- assistance level;
- source citations when Knowledge Lens contributed;
- reusable cue;
- confidence and reason;
- links to later corrections or transfer events.

Use a strict relevance budget rather than a numeric quota: record the smallest coherent set of consequential evidence with durable reuse value after healthy delivery; `off` records nothing. Auxiliary ledger failure must not change the task result.

Record references to source material or project artifacts, not large copies of them. Omit the capability direction when the mapping is ambiguous; do not force every event into a taxonomy.

## Capability directions

Use the six stable directions from [capability-compass.md](capability-compass.md):

- `problem-framing`;
- `system-modeling`;
- `verification`;
- `reliability`;
- `agent-leverage`;
- `ownership`.

The runtime's capability summary reports observed events, evidence-bearing events, independent events, caught-Agent corrections, transfer events, and recency. Treat these as provenance for a judgment, not as a balanced scorecard.

Do not infer weakness merely because a direction has few or no events. The task history may not have supplied an opportunity, the Agent may have omitted a record, or the work may live outside the indexed projects.

## Assistance levels

Distinguish:

- Agent supplied the decision and user observed;
- Agent narrowed options and user chose;
- user predicted with hints;
- user chose and Agent verified;
- user independently identified and verified;
- user corrected the Agent.

Do not hide assistance when summarizing progress. Reduced assistance matters only when task difficulty, consequence, and validation quality remain comparable.

## Confidence

Update confidence conservatively from multiple signals:

- recency;
- number of independent contexts;
- strength and scope of verification;
- assistance level;
- contradictions and caught errors;
- delayed transfer;
- real-user or production outcomes;
- comparable performance with less scaffolding.

Keep uncertainty explicit. Prefer “two independently verified decisions in similar contexts” over “advanced at architecture.”

Decay should prompt retrieval practice, not erase historical evidence. Never penalize inactivity as failure.

## Corrections

Append a correction that links to the earlier event. Preserve what was believed, what evidence supported it, and why it changed. Do not rewrite history or silently mutate an incorrect event.

A discovered Agent mistake is valuable evidence when the user identifies the mismatch and grounds the correction in source, test, log, runtime behavior, or production feedback.

## Capability and progress summaries

Summarize a bounded period with:

- delivery and real-world outcomes;
- decisions the user increasingly owns;
- verification quality improvements;
- caught errors, contradictions, or recurring blind spots;
- transferred capabilities;
- Agent delegation that reduced or increased net work;
- one next practice opportunity tied to upcoming work;
- one next responsibility or depth bet when a broader trajectory review is requested.

Separate observations from inference. For example:

```text
Observed: three verification events, two independently selected tests, one caught Agent error.
Inference: evidence selection may be becoming more independent in this project.
Unknown: no materially different context has yet demonstrated transfer.
```

Avoid leaderboards, streak pressure, category completeness goals, inflated XP, and false precision. If a numerical score is exposed, explain its evidence and limitations; never make it the primary claim.

## Learning targets

Keep few active targets. Each target should contain:

```text
Capability: one concrete engineering judgment
Current evidence: strongest observed level and contexts
Next evidence: a realistic stronger behavior
Opportunity: likely project situation where it can occur
Do-not-force: conditions where delivery should take precedence
```

Archive stale or irrelevant targets without deleting their evidence. Do not ask the user to maintain this structure manually.

## Transfer criteria

Count transfer only when:

1. the later context differs in a meaningful dimension;
2. the developer recognizes or applies the underlying mechanism;
3. an outcome or review provides evidence;
4. the event can be traced to the prior cue without assuming causation.

Simply recalling terminology, repeating the same procedure in the same file, or following a fully specified Agent instruction is rehearsal, not transfer.

The bundled ledger enforces this boundary. A `transfer` record must provide `--prior-event`, at least one concept shared with that earlier event, `--context-difference`, `--outcome`, and `--evidence`. Do not invent these fields to obtain XP; leave the cue unrecorded until a real later application exists.
