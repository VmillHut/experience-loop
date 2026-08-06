# Auto and onboarding experience evaluation — 2026-08-06

This evaluation used two simulated users and three queued rounds. No more than two simulated users ran concurrently. Both worked only in isolated temporary copies and were instructed not to read `.env` or modify the Experience Loop source repository.

## Simulated users

- **User A — developing engineer:** 1–3 years of experience, dislikes configuration and interruptions, wants fast delivery under pressure but accepts a high-value prediction when time allows.
- **User B — technical lead:** prioritizes architecture judgment, verifiable evidence, and delivery quality; accepts a bounded wait when the decision will recur.

## Results

| Round | User A | User B | Outcome |
| --- | --- | --- | --- |
| 1 — AI-first install and onboarding | Ran dry-run, install, default setup after “skip all,” doctor, and status in isolated target/home directories | Ran install, partial-profile setup, doctor/status, upgrade preservation, and command handoff checks | Found three real defects: skipped role still persisted a default, Windows command strings were not directly executable in PowerShell, and repeat setup offered the tutorial again. All three were fixed and covered by regression tests. |
| 2 — adaptive intervention | Urgent release-blocking retry fix with “directly do it” | Non-urgent, recurring abstraction-timing judgment before decisive code/test evidence | User A received zero learning questions and shipped a 2/2-tested minimal fix. User B received one required judgment checkpoint and the Agent genuinely stopped before decisive evidence. |
| 3 — adaptation after user response | Replied “skip, just do it” to a required checkpoint | Chose “fix in place; abstract after a second change axis or consumer” | User A saw zero follow-up interruption and a 2/2-tested fix. User B's prediction was compared with implementation/tests, confirmed with one nuance, and completed with no extra training questions. |

## Round 1 defects and corrections

### Skipped profile information was not truly empty

The initial default profile persisted `role: software-developer` after the user skipped every question. Although `customized` stayed false, this contradicted the user-facing promise to save only answered fields.

Correction: new default profiles now store `role: null`; validation and reset behavior accept `null`, while legacy `software-developer` profiles remain compatible and non-customized.

### Windows command receipts were not copyable

The original JSON command looked like:

```text
"C:\...\python.exe" "C:\...\experience_loop.py" "--version"
```

PowerShell parsed the second quoted token as unexpected because the call operator was missing.

Correction:

- Windows `commands` now use PowerShell-native `& 'executable' 'argument'` syntax.
- POSIX `commands` use shell-safe quoting.
- `command_shell` identifies the intended shell.
- `command_argv` provides structured argument arrays so an installer Agent does not need to parse shell text.
- Tests execute both the structured argv and the copyable command on the current platform.

### Upgrade setup repeated the tutorial offer

The runtime returned `offer_short_tutorial` even when `already_initialized` was true.

Correction: a repeated setup now preserves the profile, returns no onboarding action, and explicitly says not to repeat the beginner tutorial. Installation JSON also marks onboarding as `check_runtime_before_onboarding`, and the handoff prompt requires state inspection before initialization.

## Adaptive behavior evidence

### Fast path did not weaken delivery

For the release-blocking retry defect, `auto` used no profile, setup, Knowledge Lens, ledger, teaching question, or learning tail. It changed only the loop bound so `max_attempts=3` performs three calls, kept the public API unchanged, and passed both focused tests.

### Required participation was real, not explanatory decoration

For the non-urgent abstraction question, the Agent asked the user to choose among extracting a policy, fixing in place, or partially extracting one concern. It then stopped before reading `asset_service.py`, its tests, or running the decisive test suite. The prompt targeted a recurring human judgment, could be checked against later evidence, was answerable in under a minute, and did not delay recovery or safety-critical work.

### Skip remained a complete override

When User A replied “skip, just do it,” the Agent continued immediately, did not repeat the checkpoint, did not add a learning tail, did not infer `focus` or `deep`, and still delivered the minimal 2/2-tested fix.

### Engagement did not silently become a deep session

User B's prediction was confirmed: there was one consumer and no independent cache implementation or second change axis, so a new strategy abstraction was not justified. The Agent added only the useful nuance that a thin `RetryPolicy(max_attempts)` value object already existed and should remain. It did not add further training prompts.

## Regression evidence

- `python -B -m unittest tests.test_runtime_cli tests.test_install tests.test_repository_contract`: 29 tests passed after the fixes.
- The install tests execute structured argv, execute the returned copyable command on the current shell, verify absolute runtime/onboarding paths, and cover `already-active` receipts.
- Runtime tests cover optional `guidance_preference`, `role: null` after empty setup, no repeated tutorial offer, field clearing, legacy backfill, and type validation.
- Release validation passed with no generated or personal-state artifacts after cleanup.

## Remaining limits

- These are controlled simulations over one small Python fixture, not evidence of long-term capability transfer.
- Host discovery of a newly installed Skill still depends on Codex session lifecycle; the protocol can verify files and runtime commands but cannot guarantee hot discovery in the current task.
- Windows `doctor` may report that ACLs were not deeply audited while still returning healthy status; the warning is accurate but may need clearer user-facing severity in a future release.
- A required checkpoint is only positive when the Agent correctly identifies a reusable judgment seam. Ongoing evaluation should include false-positive and high-pressure cases, not reward question count.

## Overall judgment

The redesigned contract met the intended balance in rounds 2 and 3: `auto` was silent under pressure, genuinely waited at a high-value judgment, adapted immediately to “skip,” and kept an engaged path bounded. Round 1 exposed meaningful installation/onboarding friction that static documentation review had missed; the resulting fixes reduce the burden on both users and weaker installation Agents.
