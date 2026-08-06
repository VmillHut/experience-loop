# Let an AI install Experience Loop

This is an execution contract for an installer Agent. The user should not need to perform a long manual setup: give an AI with terminal and filesystem access the repository URL and tell it to follow this document.

Repository: `https://github.com/VmillHut/experience-loop`

## The user sends one short prompt

```text
Using `docs/AI_INSTALL.en.md` in https://github.com/VmillHut/experience-loop, install and initialize the `experience-loop` Skill.
```

## Completion criteria

Report success only after all of these are true:

1. The bundled installer was used; files were not assembled manually.
2. Python 3.9 or newer is available, and the same interpreter is used for preview, installation, and validation. The project continuously tests Python 3.9–3.14.
3. `scripts/install.py --dry-run` was run and its resolved user Skill target and backup directory were reviewed.
4. Installation succeeded and the target contains `SKILL.md`, `agents/openai.yaml`, `scripts/experience_loop.py`, and the uninstaller.
5. The lightweight installed `mode --json` command succeeds and returns `auto` or an existing valid saved mode.
6. The user is told the install path, whether an upgrade backup was made, and whether a new Codex session is needed for discovery.
7. Post-install onboarding was invoked, or an exact handoff prompt was supplied when the current session cannot discover the new Skill.

Cloning the repository, copying some files, or assuming a command should work is not successful installation.

## Authorized boundaries

Installation authorizes only:

- cloning or downloading the repository into an isolated location;
- running the bundled installer;
- writing the installer-resolved per-user Skill directory;
- allowing the installer to create a managed backup of a recognized prior version;
- after the user answers onboarding, using runtime `setup` to write Experience Loop's own external state directory.

It does not authorize:

- editing project or global `AGENTS.md`, system prompts, editor settings, or other Skills;
- scanning projects, reading articles or datasets, or building a Knowledge Lens index;
- uploading code, profiles, or sources, enabling external services, or installing unrelated dependencies;
- deleting personal data, backups, repositories, or unknown directories;
- using `--force` on an unrecognized target without explicit user consent.
- using `curl | shell`, a remote script pipe, or another install path that cannot be reviewed first.

If an unrecognized target exists, stop and show its absolute path, the conflict, and the planned backup location. Use `--force` only after explicit consent. Never bypass the installer's path checks.

## Recommended execution

Use equivalent commands for the operating system. On Windows, replace `python` with `py -3` when necessary.

1. Obtain the source in a temporary or user-approved location. Confirm its remote URL and commit, then read this file, `SECURITY.md`, and installer help. Stop if source identity or structure is unexpected:

   ```text
   git remote get-url origin
   git rev-parse HEAD
   python scripts/install.py --help
   ```
2. Use the same Python interpreter to check the release contract and preview the installation:

   ```text
   python --version
   python -B scripts/verify_release.py --skip-tests --json
   python -B scripts/install.py --dry-run --json
   ```

3. Review the preview, then install when there is no conflict requiring new consent:

   ```text
   python -B scripts/install.py --json
   ```

4. Prefer the structured `command_argv` arrays from installation JSON. The `commands` strings are copyable for the returned `command_shell` (PowerShell on Windows, including the required `&`). Validate from the installed directory, not the temporary checkout:

   ```text
   python -B <installed-directory>/scripts/experience_loop.py --version
   python -B <installed-directory>/scripts/experience_loop.py --json mode
   python -B <installed-directory>/scripts/experience_loop.py --json status
   ```

5. Use the `mode`/`status` result to choose the handoff: initialize only when state is absent; for an upgrade, preserve the existing profile and do not repeat onboarding or the tutorial unless requested.
6. After initialization, run installed `doctor --json` and `status --json`; validate exit codes and JSON `ok`/`initialized` fields rather than treating any output as success.
7. If the current Codex session cannot discover the Skill, ask the user to open a new task first and restart Codex only if the new task still cannot discover it. Do not claim to have invoked a Skill that the session cannot see.

The installer returns platform-copyable `commands`, Agent-ready `command_argv` arrays, source repository/commit/dirty provenance, and status, uninstall, upgrade, and rollback information. A rollback command is returned only when the backup remains a validated Experience Loop install source with a complete installer. Otherwise preserve and report `backup` and `rollback_note`; do not construct a command or execute scripts from that backup. Normal install and upgrade leave personal profiles, project profiles, experience records, and the knowledge library outside the Skill directory.

## Fixed post-install handoff

For a first install whose `persisted`/`initialized` state is false, send the installer's `onboarding_prompt` to the current or new session. Its meaning is equivalent to:

```text
$experience-loop is installed. Follow references/onboarding.md to initialize it. Every profile question is optional, then ask whether I want the roughly two-minute usage tutorial.
```

The receiving Agent must ask one compact set of concrete but optional profile questions, save only answered fields, avoid project scans and source reads during onboarding, use default `auto` when no mode is volunteered, honor a user-provided saved default, and ask once about the fixed interactive tutorial. Store presentation preferences in `--explanation-style` and interruption/participation preferences in `--guidance-preference`. Pass every user value as an independent argument instead of interpolating raw answers into executable shell text. After initialization, run installed `doctor --json` and `status --json`. Report real failures; never fabricate success through a silent fallback.

## Final receipt

End with a short, verifiable receipt rather than “installed successfully” alone:

```text
Experience Loop installation
- source: <repository URL, commit, and dirty state>
- python: <absolute interpreter path and version>
- version: <Skill version>
- target: <absolute per-user Skill path>
- backup: <none or absolute backup path>
- rollback: <available, or unavailable with the installer's reason>
- validation: actual mode/status/doctor results
- discovery: available now, new task needed, or restart needed
- onboarding: started, skipped, or waiting for the handoff prompt in a new task
```

If the AI lacks local terminal or filesystem access, it must say that installation was not executed and offer the manual fallback. Reading instructions is not an installation result.

## Manual fallback

Offer manual commands only when the user explicitly wants them or the AI lacks terminal/filesystem access:

```text
git clone https://github.com/VmillHut/experience-loop.git
cd experience-loop
python scripts/install.py --dry-run
python scripts/install.py
```

Then open a new Codex session and paste the fixed handoff prompt. Do not require the user to study the full README before first use.
