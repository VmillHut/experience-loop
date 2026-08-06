# Experience Loop: short contract for the installation AI

The user sends only:

```text
Install and initialize the `experience-loop` Skill from https://github.com/VmillHut/experience-loop; follow the repository-specific safety and acceptance contract in `docs/AI_INSTALL.en.md`.
```

The current AI handles ordinary download, host identification, Skill-directory discovery, command choice, and reload behavior. This document does not repeat a generic installation tutorial; it contains only repository-specific facts that must not be guessed.

## Resolve the live host instead of trusting a static table

Use the current session, host help/configuration, the existing Skill registry, and current official documentation when needed to determine the target, scope, invocation, reload action, every relevant discovery root, and every host that may observe a shared directory.

Pass those facts to the bundled installer; `python scripts/install.py --help` is the current parameter contract. Paths, invocation syntax, and reload behavior may change with the host, so the repository does not freeze them. Stop when evidence is insufficient. Do not infer the active host merely because a CLI is installed, and do not write to multiple Agents by default.

Do not hand host-directory, installer-argument, or reload choices back to the user. Resolve them when the current context is sufficient. Stop only when continuing would require a risky guess, then state that installation has not occurred and identify the missing evidence.

## What this repository uniquely needs guaranteed

1. **Complete core** — install the complete `SKILL.md`, references, scripts, vendor bundle, and runtime resources. Never remove profiles, the ledger, Knowledge Lens, or mode behavior and replace them with a prompt-only imitation.
2. **Transactional safety** — every write must use the bundled installer for preview, completeness validation, staging, managed backup, and atomic replacement; otherwise report “not installed.” Never apply `--force` silently to an unknown directory.
3. **Three acceptance layers** — separately validate filesystem installation, installed-copy `version`/`mode`/`status`, and actual discovery or invocation by the current host. None proves the others.
4. **Truthful rollback** — use only the receipt's backup and rollback information. When `rollback_available` is false, report `rollback_note`; do not execute scripts from an incomplete backup.
5. **State isolation** — personal and project profiles, experience records, and the knowledge library live under `~/.experience-loop` by default, outside the Skill target. Install, upgrade, and uninstall must not remove them incidentally.
6. **First install differs from upgrade** — enter `references/onboarding.md` only when state is uninitialized. Preserve an existing profile and do not repeat onboarding or the tutorial unless requested.
7. **No fake compatibility** — if host discovery or the Python runtime cannot be verified, report the limitation. Never fabricate success through a silent downgrade.

Only four security steps are fixed: verify that the exact repository remote is this project and record commit/dirty state; run `--dry-run --json` with the complete host contract; install with that identical contract only when no blocker remains; then perform separate filesystem, runtime, and host-discovery acceptance. Do not replace this with manual copying or a remote script pipe.

## Installation does not also authorize

- editing global or project Agent instructions, system prompts, hooks, editor configuration, or another Skill;
- scanning projects, reading user articles/data, or creating a Knowledge Lens index;
- uploading code, profiles, or sources, enabling external services, or granting extra tools;
- deleting personal data, prior backups, repositories, or unknown directories;
- using a remote script pipe that cannot be reviewed first.

A shared discovery directory, unknown-directory replacement, optional global router, or any extra permission requires a separate impact preview and explicit consent.

## Initialization and follow-through are required after installation

This is not a host-installation tutorial. It is Experience Loop's own first-use and upgrade contract, so the installation AI must complete it or hand it off precisely when the current session cannot discover the new Skill.

Installation must not stop at “files copied.” Complete this state machine:

1. Use the receipt's `command_argv` to run the installed copy's `version`, `mode`, and `status`.
2. If `status` shows existing initialized state, treat this as an upgrade: preserve the profile and saved mode, do not repeat the questionnaire or tutorial, and finish health validation.
3. If state is uninitialized, first prove that the current host discovers the Skill, then send the receipt's `onboarding_prompt` to the current or refreshed session.
4. Follow `references/onboarding.md` and ask one concrete profile batch. Every field is optional; the user may answer any subset or “skip all.” Save only actual answers, invent nothing, perform no project scan or source read, and do not force a mode choice.
5. Ask once whether the user wants the roughly two-minute conversational tutorial. Run the fixed interactive example after consent; when skipped, finish without another configuration flow.
6. After state is written, run `doctor` and `status` again in the same data-home context and verify health plus `initialized`; reuse an explicit `--home` on every follow-up command. Report a real failure instead of treating completed dialogue as persisted success.

Continue automatically whenever possible. If host refresh genuinely requires user action, end with exactly one currently necessary `next_action`, not a menu of paths, commands, or modes. The refreshed session resumes this state machine instead of restarting installation.

The final user receipt needs only source/version, target and affected hosts, the separate filesystem/runtime/discovery results, backup and rollback, onboarding state, and real limitations. If the current AI lacks terminal or filesystem access, say “installation was not executed”; reading this document is not installation.
