# Experience Loop development instructions

Before modifying product behavior, Skill instructions, host adapters, packaging,
installation, onboarding, persistence, privacy, or evaluations, read
`docs/DEVELOPMENT_COMPASS.md` completely once for the current task.

Use the compass as decision context, not as a fixed implementation checklist.
Preserve its mission and boundaries while choosing the best method from current
evidence and the strongest capabilities available in the present Agent and host.
Do not reread it in the same task unless it changes.

Before editing, identify the intended user outcome, the native-Agent baseline,
the likely attention or delivery cost, and the evidence that could disprove the
proposed improvement. If a proposed change conflicts with the compass, surface
the conflict and trade-off instead of silently weakening either side.

`AGENTS.md` and `docs/DEVELOPMENT_COMPASS.md` are source-only development
material. Never add them to a standalone Skill or Plugin runtime payload.
