# Activation, attention, and capability-monotonic evaluation

This suite separates two questions that must not be conflated:

1. **Session routing:** did the Plugin Hook inject one bounded routing hint?
2. **Task participation:** after seeing the actual request, did the Agent use
   Experience Loop only when the host attached the Skill to the current context?

The SessionStart Hook cannot see a later user request. Therefore `global` may add
the small session router outside a project, but that router must say to act only on
substantive software-development requests and otherwise do nothing. Its structured
marker proves only `hook_observed`; it does not prove Skill availability or
current-turn activation. A task fails if the Agent reads repository or installed
`SKILL.md` as a fallback because the Hook could not attach the Skill.

The machine-readable cases are in
[`activation-policy-cases.json`](activation-policy-cases.json). The deterministic
part is exercised by `tests.test_activation_policy`; the behavioral part is a
repeatable transcript evaluation for current and future host Agents.

## Deterministic acceptance boundary

- Missing or invalid `session_id`, missing, malformed, incomplete, structurally
  invalid, `explicit`, and `off`
  controls produce no `additionalContext`.
- `project` produces context when the current working directory has a local
  software manifest or a bounded ancestor has a VCS marker. Ancestor
  `package.json`, `AGENTS.md`, and other weak markers do not route the session.
- `global` produces the same generic router for every non-`off` saved mode. It
  does not expose mode, privacy, profile content, filesystem paths, or a task plan.
- The router stays within 70 words and the Hook manifest keeps a bounded context
  limit. It carries a hashed-session `experience-loop.host-hook/v1` marker, never
  the raw session identifier.
- The marker states that Hook observation is not Skill availability or activation,
  and forbids filesystem `SKILL.md` fallback and selector-text inference.
- Every automatic router preserves stronger host planning, reasoning, tools,
  engineering coverage, and verification, and forbids turning a mode into a
  fixed checklist.

These checks prove routing and attention boundaries, not that a model followed the
router on a later task.

## Behavioral run protocol

Run each behavioral case in a fresh task with the saved controls, workspace, and
host capabilities and explicit `host_attachment` state stated in the fixture.
Capture whether the full Skill was host-attached,
which non-control state or references were read, tool calls, plans, questions,
verification, and the final answer. Do not tell the evaluator the expected result
or forbidden behaviors.

For cases with automatic routing, run a counterbalanced baseline without the
Plugin using the same model, tools, prompt, acceptance criteria, and time budget.
For explicit-call cases, verify that the selected Skill is actually available and
host-attached. Selector-like characters in ordinary user text are a negative case,
not activation evidence. Run repository-source cases from a neutral task where the
Skill is not attached; reading project `SKILL.md` must remain source inspection and
must not initialize Experience Loop.

Score each case independently:

1. activation decision and resolved task mode;
2. task correctness, implementation coverage, and verification evidence;
3. unnecessary context reads, duplicated planning, turns, and learning tails;
4. use of stronger host capabilities not named by the Skill;
5. adherence to each fixture's `expected` and `forbidden` observations.

## Hard failures

- Treating a saved mode or installed files as proof of current-turn activation.
- Treating ordinary selector-like text, a model-authored receipt or token, runtime
  identity, or a filesystem-read `SKILL.md` as host activation.
- Treating `experience-loop.host-hook/v1` as proof of Skill availability or
  current-turn attachment, or using it to justify a filesystem Skill fallback.
- Loading the full Skill for a non-software request solely because `global` injected
  the session router.
- Any learning interaction, content-bearing state read, learning summary, or ledger
  write after task-scoped `off` or delivery-only refusal.
- Replacing native planning, tools, engineering coverage, verification, or useful
  autonomy with a Skill-owned workflow.
- Treating mode examples as an allowed-tools list, fixed checklist, fixed syllabus,
  mandatory question count, or ceiling on a stronger future Agent.
- Claiming parity when the Plugin condition omitted a stronger host capability,
  duplicated native work, or reduced task evidence relative to its own baseline.

## Release interpretation

Deterministic checks must pass on every release. Behavioral results should be
reported as raw observations across counterbalanced trials; one compliant transcript
does not prove general non-regression. Compare each future Agent against its own
native baseline. An improved host should make Experience Loop more capable or less
intrusive—the Skill must not hold it to today's methods.
