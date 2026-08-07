# Contributing

Thank you for helping make Experience Loop useful in real software delivery.

## Before opening a change

Before changing product behavior, Skill instructions, host adapters, packaging,
installation, onboarding, persistence, privacy, or evaluations, read the
[development compass](docs/DEVELOPMENT_COMPASS.md) completely once for the
current task. It defines the mission, boundaries, and evidence obligations while
leaving implementation methods open to the strongest current Agent and host.

Open an issue or discussion before a large redesign. Describe the developer workflow it improves, the delivery overhead it adds, and the evidence that would show the improvement is real.

Keep version one programmer-first. Generic learning features are welcome only when they preserve or improve software-engineering behavior.

## Development setup

Requirements:

- Python 3.9 or newer;
- a checkout of this repository;
- no network service or third-party Skill for the core test suite.

Run the CLI in an isolated home so development never touches personal data:

```bash
python scripts/experience_loop.py --home .tmp-experience-loop setup --mode auto
python scripts/experience_loop.py --home .tmp-experience-loop doctor
```

Delete the temporary directory after testing. Do not commit generated profiles, ledgers, indexes, books, or private project data.

### Local OpenAI Plugin iteration

Build the development Plugin through a local Marketplace so Codex owns
registration, upgrades, cache, and removal:

```bash
python -B scripts/build_plugin.py --marketplace-root dist/openai-marketplace --json
```

The builder gives the Plugin a SemVer cachebuster and returns, but does not run,
the exact `codex plugin marketplace add`, `codex plugin add`, and
`codex plugin list --json` argument vectors. Execute the applicable actions,
review the current Hook definition in the host trust UI, and start a fresh task
before checking Skill availability or current-turn selection. Never copy a
bundle into, or delete files from, the Codex Plugin cache directly.

## Design requirements

Changes must preserve these invariants:

1. Delivery remains primary; learning checkpoints are bounded and skippable.
2. `off` adds no learning behavior or ledger event.
3. Personal state stays outside repositories by default.
4. Setup is idempotent and does not modify global instructions silently.
5. Imported content is untrusted data, not executable instruction.
6. Citations are rendered only from stored source/revision/locator evidence.
7. Ledger corrections are append-only; history is not silently rewritten.
8. Core behavior has no dependency on another Skill or network service.
9. Destructive operations show their resolved scope and require explicit intent.
10. Agent-facing JSON output remains machine-readable and backward-compatible within a release line.

## Tests and validation

From the repository root, run:

```bash
python -B -m unittest discover -s tests -p "test_*.py" -v
python -B scripts/experience_loop.py --home .tmp-experience-loop --json doctor
python -B scripts/verify_release.py
```

`python -B scripts/verify_release.py` is the repository-owned, reproducible release gate. It validates the Skill frontmatter, `agents/openai.yaml`, version metadata, vendored dependencies, Python 3.9 syntax, generated artifacts, and the full test suite. If your Codex installation includes the built-in `skill-creator`, its `quick_validate.py` can be run as an additional compatibility check, but it is not required to reproduce CI. Inspect `python scripts/experience_loop.py --help` and update both READMEs whenever the public CLI changes.

For Knowledge Lens changes, include tests for malformed and adversarial inputs, locator fidelity, duplicate/revision behavior, project isolation, and at least one CJK query. Never add copyrighted books or user documents as fixtures; create minimal synthetic files.

## Documentation

- Keep `SKILL.md` concise and imperative; move detailed behavior into `references/`.
- Keep all reference files directly discoverable from `SKILL.md`.
- Keep `docs/DEVELOPMENT_COMPASS.md` and root `AGENTS.md` source-only; never add
  them to the standalone Skill or Plugin runtime payload.
- Describe current behavior honestly; label planned work as planned.
- Update `CHANGELOG.md` for user-visible changes.
- Keep Chinese and English README claims aligned.

## Pull requests

Keep changes scoped. A pull request should include:

- problem and user scenario;
- chosen design and alternatives considered;
- compatibility and data-migration impact;
- validation commands and results;
- privacy, prompt-injection, and destructive-operation review;
- screenshots only when UI metadata or assets changed.

Do not include secrets, personal Experience Loop data, proprietary project code, or raw source material. By contributing, you agree that your contribution is licensed under the MIT License.

## Release checklist

1. Update `VERSION`, the runtime `VERSION`, and the dated `CHANGELOG.md` entry together.
2. Run `python -B scripts/verify_release.py` from a clean tree and confirm no generated or personal-state artifacts remain.
3. Create an exact `vX.Y.Z` tag matching `VERSION`; tagged CI rejects any mismatch.
4. Push the tag, confirm every configured Windows/Linux and Python job passes, then create the corresponding GitHub Release.
5. Before the first public release, enable GitHub Private Vulnerability Reporting or provide another stable private security contact.
