# Experience evidence model

Use this reference when recording events, estimating confidence, creating progress summaries, or deciding whether learning transferred.

## Principle

Treat experience as evidence of increasingly independent judgment under real constraints. Do not equate exposure, generated output, or fluent explanation with capability.

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

Use levels as descriptors, not grades. A single strong event should not imply mastery.

## Event semantics

Keep the ledger append-only. An event should identify:

- event ID and timestamp;
- user/project/task identity without unnecessary personal content;
- mode and task pressure;
- target capability;
- prediction or decision;
- evidence observed;
- outcome and verification scope;
- assistance level;
- source citations when Knowledge Lens contributed;
- reusable cue;
- confidence and reason;
- links to later corrections or transfer events.

Record references to source material or project artifacts, not large copies of them.

## Assistance levels

Distinguish:

- Agent supplied the decision and user observed;
- Agent narrowed options and user chose;
- user predicted with hints;
- user chose and Agent verified;
- user independently identified and verified;
- user corrected the Agent.

Do not hide assistance when summarizing progress. Reduced assistance matters only when task difficulty and validation quality remain comparable.

## Confidence

Update confidence conservatively from multiple signals:

- recency;
- number of independent contexts;
- strength of verification;
- assistance level;
- contradictions;
- delayed transfer.

Keep uncertainty explicit. Prefer “two successful decisions in similar contexts” over “advanced at architecture.”

Decay should prompt retrieval practice, not erase historical evidence. Never penalize inactivity as failure.

## Corrections

Append a correction that links to the earlier event. Preserve what was believed and why it changed. Do not rewrite history or silently mutate an incorrect event.

A discovered Agent mistake is valuable evidence when the user identifies the mismatch and grounds the correction in source, test, log, or runtime behavior.

## Progress summaries

Summarize a bounded period with:

- delivery outcomes;
- decisions the user increasingly owns;
- evidence quality improvements;
- recurring blind spots or unresolved contradictions;
- transferred capabilities;
- one next practice opportunity tied to upcoming work.

Avoid leaderboards, streak pressure, inflated XP, and false precision. If a numerical score is exposed, explain its evidence and limitations; never make it the primary claim.

## Learning targets

Keep few active targets. Each target should contain:

```text
Capability: concrete engineering judgment
Current evidence: strongest observed level and contexts
Next evidence: a realistic stronger behavior
Opportunity: likely project situation where it can occur
Do-not-force: conditions where delivery should take precedence
```

Archive stale or irrelevant targets without deleting their evidence.

## Transfer criteria

Count transfer only when:

1. the later context differs in a meaningful dimension;
2. the developer recognizes or applies the underlying mechanism;
3. an outcome or review provides evidence;
4. the event can be traced to the prior cue without assuming causation.

Simply recalling terminology or repeating the same procedure in the same file is rehearsal, not transfer.

The bundled ledger enforces this boundary. A `transfer` record must provide `--prior-event`, at least one concept shared with that earlier event, `--context-difference`, `--outcome`, and `--evidence`. Do not invent these fields to obtain XP; leave the cue unrecorded until a real later application exists.
