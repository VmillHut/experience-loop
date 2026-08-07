# Deep mode experience evaluation — 2026-08-06

This evaluation used two simulated-user tracks and three independent Agent executions across six queued rounds. No more than two simulated users were active concurrently, and later prompts were issued only after reviewing the earlier responses. The evaluators did not modify the Experience Loop repository.

## Purpose

Test the clarified learning contract:

- `auto` and `deep` share the same high-quality task and learning capabilities;
- `auto` automatically detects whether practice or a decision debrief is worthwhile and intelligently chooses its timing and depth;
- explicit `deep` proactively seeks meaningful opportunities for the user to frame, decide, and review real work;
- depth follows task value rather than a fixed round count, syllabus, or question quota;
- after the user decides, feedback is fair, independent, multidimensional only where relevant, and useful for transfer;
- stronger learning must remain a sidecar and must not reduce native analysis, implementation, verification, or recovery quality.

## Scenario

The main scenario extracted a pricing service from a monolith. The simulated user owned a cart estimate, a five-minute signed checkout quote, atomic coupon reservation, audited support overrides, independent team releases, and a known stale-cache undercharge risk. A later review introduced a deliberately flawed Agent proposal involving mutable rules, synchronous quote validation, shared runtime resources, order-before-coupon commit, and a rollback path that could not read historical state.

A separate narrow scenario compared `delete(id, force=false)` with an explicit deletion mode or a distinct permanent-delete command.

## Results

| Round | Conditions | Observation | Judgment |
| --- | --- | --- | --- |
| 1 — framing contrast | The same initial architecture task was run in `auto` and `deep`. | `auto` asked one decisive question about whether the cart value was an estimate, a commitment, or a transactional result. `deep` proactively engaged the user on the consistency boundary, caller-specific semantics, and the actual reasons for separating the service. | Both stayed task-grounded. `deep` created a broader but coherent decision surface instead of merely producing a longer explanation. |
| 2 — evidence-driven continuation | The user supplied quote lifetime, coupon atomicity, override audit, release ownership, load, and undercharge constraints. | `auto` produced a complete architecture and migration recommendation. `deep` used the new evidence to continue the user's reasoning about quote revocation, coupon failure semantics, and resource isolation. | `deep` was more proactive than `auto`, while each follow-up depended on real constraints rather than a predetermined curriculum. |
| 3 — Agent-output review | Both modes received the same flawed five-part Agent proposal. | `auto` independently found and corrected all five defects. `deep` preserved an acceptance baseline and asked the user to classify blockers, construct failure chains, judge whether traffic switching was real rollback, and choose approval evidence. | Native review quality remained available in both modes. `deep` additionally exercised the user's architecture and Agent-review judgment without hiding material facts. |
| 4 — narrow decision | `deep` received a small public-API design choice and permission to use one dense exchange if sufficient. | The evaluator recommended an explicit deletion mode, or a separate `purge` command when authorization, audit, or lifecycle differed, and extracted a reusable rule about risky boolean parameters. It did not manufacture extra rounds. | One exchange can be genuinely deep when the decision is narrow. Round count was not used as a proxy for learning quality. |
| 5 — completed-decision debrief | The user had already chosen `delete(id, force=false)`. The same decision was evaluated sequentially in `auto` and `deep`. | `auto` gave a compact conditional review and runtime guardrails without reopening the whole design exercise. `deep` fairly reconstructed the rationale, separated facts, inferences, and unknowns, independently preferred more explicit semantics for a new cross-language API, stated acceptable conditions for retaining the boolean, and distilled a transfer rule. | The post-decision capability is shared, but `auto` decides whether and how far to use it; `deep` more actively develops and internalizes the decision framework. |
| 6 — strict narrow compactness probe | A fresh Agent with no prior evaluation conclusions used `deep` for one process-local cache API choice: whether `ttlSeconds = 0` should mean no expiry or the type should express that policy explicitly. | The first response used one 30-second checkpoint about the failure cost of an accidental computed zero and call-site ambiguity. After a one-sentence user choice, the second response closed the task with an explicit union type, boundary validation, four focused tests, and one transfer rule. It asked no further questions. | `deep` produced real practice and independent advice in two compact exchanges. It did not equate depth with a long answer, a broad risk matrix, or extra rounds. |

## Decision-debrief quality

The `deep` response did not simply reward or reject the user's choice. It:

- recognized the real advantages of a safe default, compatibility, and a smaller public surface;
- identified the central weakness as call-site reviewability rather than claiming a boolean could not be implemented safely;
- distinguished known constraints from reasonable inferences and missing context;
- gave an independent recommendation with confidence, conditions, and a viable fallback;
- named runtime authorization, retention, audit, idempotency, concurrency, and test evidence only because permanent deletion activated them;
- ended with a compact rule that could transfer to other public API decisions.

The `auto` response used a smaller intervention because a complete redesign exercise was not necessary. It still surfaced the material irreversible-operation risks, showing that `auto` is not defined as low intervention or shallow advice.

## Contract changes caused by the evaluation

- Defined `deep` as adaptive dialogic practice with no preset minimum, maximum, or default round count.
- Made proactive user framing, prediction, decision, and Agent-output review the meaningful distinction from `auto`, without creating a second task workflow.
- Required each exchange to use the smallest coherent question set and to stop or deepen according to marginal value.
- Added an adaptive decision-debrief contract that fairly reconstructs the user's reasoning, evaluates only relevant dimensions, separates decision quality from eventual outcome, and gives an evidence-bounded independent recommendation.
- Made decision debriefs available in both `auto` and `deep`: `auto` decides whether, when, and how deeply to use them; `deep` proactively seeks and continues worthwhile debrief seams.
- Prohibited generic praise, arbitrary scores, fixed dimension matrices, performative disagreement, forced restatement, and mandatory debriefs after every choice.

## Attention and task-quality observations

- Neither mode created a second implementation or verification plan.
- `auto` retained full architecture-review quality and corrected the flawed proposal directly.
- `deep` concentrated on one coherent pricing decision framework rather than exposing every possible engineering category.
- Risk dimensions appeared only when activated by the concrete pricing or deletion semantics.
- The narrow API task did not expand into artificial multi-round questioning.
- The strict compactness probe closed after one decision checkpoint and one answer; no fixed syllabus, second unrelated seam, or ceremonial retrospective appeared.
- The completed-decision comparison showed a meaningful intensity difference without making `auto` weak or making `deep` ceremonial.

## Limits

- These were simulated design conversations, not production changes or longitudinal capability measurements.
- Three Agent executions and six queued rounds cannot prove behavior across every model, host, user profile, or future Agent release.
- A transferable rule in one response is not proof that the user has internalized it. Durable transfer still requires later performance on a materially different real task.
- Prompt contracts reduce but cannot eliminate model variance. Future releases should rerun the same contrast and compare each evaluator against its own native-quality baseline.

## Overall judgment

The revised modes meet the intended distinction in these trials. `auto` automatically decides whether a decision or debrief deserves intervention and can become locally intensive when evidence warrants it. `deep` begins with explicit authorization for proactive capability growth, gives the user meaningful work in framing and review, and continues only while another exchange adds value. The post-decision loop now supplies objective analysis, independent advice, evidence correction, and a transferable model without turning real work into a fixed course or reducing Agent task quality.
