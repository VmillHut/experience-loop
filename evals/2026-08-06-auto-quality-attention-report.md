# Auto quality and attention evaluation — 2026-08-06

This evaluation used two independent simulated Agents and five queued rounds. No more than two simulated users ran concurrently. The evaluators produced task-like final answers without modifying the Experience Loop repository.

## Purpose

Test the clarified contract:

- `auto` detects task risks and capability opportunities before deciding how to help;
- the Skill remains a thin learning sidecar and does not replace native planning, tools, implementation, or verification;
- profiles change learning presentation, not engineering quality;
- stronger host capabilities remain usable even when the Skill does not name them;
- attention is protected by avoiding duplicate plans, irrelevant state loading, static checklists, and fixed interaction quotas.

## Simulated evaluators

- **Evaluator A** consistently preferred a defense-in-depth cache design with capacity, source concurrency, timeout, rollback, and operational controls.
- **Evaluator B** consistently preferred a smaller single-flight implementation and explicitly reported high-cardinality load, memory, and multi-process behavior as remaining risks.

Their different native styles were useful for checking whether the Skill or profile changed engineering behavior.

## Results

| Round | Conditions | Observation | Judgment |
| --- | --- | --- | --- |
| 1 — native-quality parity | A used the native Agent without the Skill; B used current `auto`. Both received a mechanical semantic rename and stronger host rename/test-selection capabilities. | Both made the same behavior-preserving rename, used the affected-test capability, and added no duplicate plan or learning tail. | `auto` matched native task quality and did not ignore a stronger host capability. |
| 2 — detection after new evidence | Both used `auto`. A simple `limit=50` request later exposed `limit <= 0` runtime failure, a public maximum of `100`, and missing invalid-boundary tests. | Both changed the implementation to validate `1..100` and tested default, legal boundaries, negative/zero, and `101`. | Initial simplicity did not become a sticky quiet path; material evidence changed the decision and verification. |
| 3 — profile contrast | A received a developing-engineer reliability profile; B received a concise technical-lead profile. Both implemented a TTL cache for a possible 10x traffic spike and were told stronger interleaving/load tools existed. | Both used the stronger tools and covered TTL, same-key concurrency, cancellation, failure recovery, and multi-process limits. A also implemented capacity, global source concurrency, and timeout; B reported capacity/high-cardinality exposure as remaining risk. | The output difference raised a real concern that profile wording might leak into engineering depth, so the contract was strengthened before the next round. |
| 4 — counterbalanced profile swap | The two profiles were swapped and both reran an equivalent independent cache task under the strengthened contract. | A remained defense-in-depth under the concise profile; B remained minimal under the learning-oriented profile. Explanation detail followed the profile, while engineering style followed evaluator identity. | No evidence that profile changed implementation or verification. The Skill now explicitly applies profiles only after the task-quality plan is intact. |
| 5 — high-risk baseline | Both evaluators reran an equivalent cache task without Experience Loop, keeping the same profiles and stronger host tools. | A again implemented capacity, concurrency, timeout, and rollback controls. B again implemented single-flight and reported capacity/high-cardinality/multi-process risks. | The engineering difference existed in the native baseline. `auto` did not reduce either evaluator's quality or tool use. |

## Contract changes caused by the evaluation

- Replaced the early hard fast path with detection-first `auto`; the fast path is now only a learning-overlay bypass.
- Added capability monotonicity: current or future host planning, reasoning, tools, engineering coverage, verification, and autonomy must not be narrowed.
- Removed global per-task limits on questions, learning seams, checkpoints, and takeaways.
- Kept one coherent learning thread in working attention without making it a global task quota.
- Made risk categories, intervention forms, and verification methods non-exhaustive examples.
- Prevented profiles from changing implementation, tools, risk coverage, verification, recovery, or material-risk reporting.
- Reduced duplicated controller logic in host metadata and the optional global router; both now activate the Skill instead of freezing its current algorithm.

## Attention observations

- The mechanical `auto` answer was as short as the native answer and did not create a second plan.
- Boundary and concurrency checks appeared only when evidence activated them; no transcript dumped every risk category.
- Both evaluators used host capabilities not listed in the Skill (`semantic_rename`, `affected_test_selection`, `async_interleaving_checker`, and `load_modeler`).
- Profile-specific explanation was visible only in the learning-oriented cache result; required engineering findings remained visible in concise results.

## Limits

- These are simulated task responses, not executions against a production repository. Tool and test success statements were part of the simulation and are not independent runtime evidence.
- Two evaluators and five rounds cannot prove universal non-regression across models, hosts, or future releases.
- Prompt contracts cannot eliminate model-to-model engineering variance. Release evaluation should continue comparing each evaluator against its own baseline rather than demanding identical implementations from different Agents.
- Long-term developer capability transfer still requires later real-task evidence; this evaluation covers task quality, adaptive behavior, and attention overhead only.

## Overall judgment

The revised design meets the intended balance in these trials: automatic detection precedes the learning decision, `auto` changes behavior when task evidence changes, profiles affect learning presentation without defining engineering work, and the Skill does not block stronger host capabilities. No simulated round showed lower task quality than the same evaluator's native baseline.
