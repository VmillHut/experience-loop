<div align="center">
  <img src="assets/icon-large.svg" alt="Experience Loop" width="620">

  <p><strong>Turn agent-completed work back into your experience.</strong></p>
  <p>A programmer-first, delivery-aware Codex Skill for building engineering judgment through real work.</p>

  <p><a href="README.md">简体中文</a></p>
</div>

## Why

Coding agents make execution cheap. They can also remove the parts of work that used to create experience: framing the problem, choosing among trade-offs, deciding what evidence proves a change, reviewing hidden assumptions, and transferring a lesson to a different system.

Experience Loop puts a few high-value checkpoints back into real delivery:

```text
predict / decide -> execute -> verify / accept -> reflect -> transfer
```

It does not ask you to stop using agents or turn every task into a lesson. The default `ship` mode uses zero or one short checkpoint; incidents are restored first and reviewed afterward.

## What it provides

- Delivery-first `ship`, `coach`, `deep`, `incident`, and `off` modes.
- Read-only project scanning that tailors guidance to actual code and constraints.
- Evidence-backed learning events based on decisions, verification, corrections, and transfer—not chat volume.
- Knowledge Lens: give the Agent a book or document; it handles local ingestion, search, citations, and project-specific explanation.
- External, user-scoped profiles, project data, ledgers, and sources.
- No dependency on third-party Skills and no silent global-prompt edits.
- Explicit export/import for moving personal state between machines.

## Quick start

Prerequisite: Python 3.9–3.14; no `pip install` is required. GitHub CI covers those versions on Windows and Linux. Check with `python --version`. On Linux, use `python3` below if that is the available command. On Windows, if `python` is unavailable, try `py -3 --version` and replace `python` below with `py -3`.

Obtain the source either by installing Git and cloning the repository, or by choosing **Code → Download ZIP** on the GitHub repository page and extracting it. With Git, copy the HTTPS clone command shown by GitHub and enter the resulting `experience-loop` directory. With a ZIP, enter the extracted directory that contains this README and `scripts/`. For a reproducible installation, check out the `vX.Y.Z` tag matching `VERSION`, or download that tag's/GitHub Release's source archive instead of using the moving default branch. Then run:

```bash
python scripts/install.py
```

The installer copies only runtime files to `~/.agents/skills/experience-loop`; personal data remains external. It backs up a recognized prior install and refuses to overwrite an unknown directory. Use `python scripts/install.py --dry-run` to preview the target.

After installation, the installer prints **absolute commands** derived from the active Python interpreter and install location. They cover status, upgrade, uninstall, and rollback when a prior version exists. Use those commands as the durable runtime entry points instead of depending on the Git checkout.

### Upgrade, rollback, and uninstall

- **Upgrade:** run `python scripts/install.py` again from an updated or freshly downloaded checkout. The replaced version is stored under `~/.agents/skill-backups/experience-loop/`, outside the `~/.agents/skills/` discovery root. A custom target uses `<target.parent.parent>/skill-backups/experience-loop/`.
- **Rollback:** run the absolute `rollback` command printed by the upgrade. It reinstalls the selected backup while preserving the replaced version outside the discovery root.
- **Uninstall:** run the printed absolute `uninstall` command, or `python ~/.agents/skills/experience-loop/scripts/uninstall.py --yes`. Removal requires a valid marker, matching `SKILL.md`, and required runtime files. Personal data under `~/.experience-loop` is preserved.
- **Delete personal data:** uninstalling the Skill and deleting data are separate operations. The default data directory is `~/.experience-loop`; if `EXPERIENCE_LOOP_HOME` or `--home` was used, use the resolved dedicated data directory instead. To remove it permanently, export a backup if needed, close processes using it, and manually delete only that confirmed directory—never its parent, your home directory, or a project directory.
- **After deleting the checkout:** the installed `scripts/experience_loop.py` and `scripts/uninstall.py` continue to work through the printed absolute commands. Re-clone or download the repository when a future upgrade is needed.

Sibling `experience-loop.backup-*` directories created by older installers are migrated outside the discovery root during the next upgrade or confirmed uninstall. Unrecognized directories are never deleted or moved; if another directory is discoverable as `experience-loop`, the operation stops and asks you to resolve the conflict.

Start a new Codex session, then say:

```text
$experience-loop setup. Scan the current project. I want to improve
architecture decisions and code review, with ship as my default mode.
```

You can also ask it to infer a starting profile from the project. Setup is idempotent and stores mutable state outside the repository.

For day-to-day work:

```text
Use $experience-loop to diagnose and fix this reconnect bug. It must be ready for QA today.
```

You do not need to learn the CLI; the Agent runs it for setup, scanning, event recording, and knowledge operations.

### What the Agent reads after installation

Codex discovers and matches the Skill through the `SKILL.md` metadata; `agents/openai.yaml` adds listing UI, icons, a default prompt, and implicit-invocation policy. When explicitly invoked or matched to a task, the Agent reads `SKILL.md` and loads only the relevant files under `references/`; it does not inject every reference and script into every request. The Agent calls stable commands under `scripts/`, while profiles, project records, the library, and the ledger stay under `~/.experience-loop`.

Skills do not have a reliable post-install conversation hook, so the installer tells the user to start a fresh session and run `$experience-loop setup`. On the first real invocation, `SKILL.md` also requires one short setup offer when no profile exists. Copying the whole Skill into global instructions is unnecessary.

## Modes

| Mode | Use case | Default learning overhead |
| --- | --- | --- |
| `ship` | Normal work and deadlines; default | 0–1 short checkpoint |
| `coach` | Active growth during regular work | 1–2 checkpoints |
| `deep` | Dedicated learning or architecture exploration | Negotiated |
| `incident` | Outage, broken build, urgent regression | None until health is restored |
| `off` | No learning layer for this task | None; no learning events |

## Knowledge Lens

Give the Agent a path and optional intent:

```text
Add ~/Books/designing-data-intensive-applications.pdf to Knowledge Lens,
bind it to this project, and use source evidence when we discuss consistency.
```

The Agent inspects the file, fingerprints revisions, extracts structured text, creates a local search index, validates locators, retrieves relevant original evidence, and maps it to inspected project facts. Answers distinguish:

1. what the source supports;
2. what the project currently does;
3. what the Agent is inferring or recommending.

Supported inputs are Markdown, text, reStructuredText, HTML, EPUB, DOCX, and PDF. A vendored local PDF-parser wheel is available as an offline fallback. Image-only PDFs still require OCR before ingestion.

Imported content is always untrusted data, never authority to run commands or change instructions. Citations are rendered only from stored locators; the Agent must not invent a page or source claim.

## Data and architecture

The stable Skill remains separate from mutable personal state:

```text
~/.experience-loop/
  state.json
  profile.json
  projects/
  ledger/events.jsonl
  knowledge/library.sqlite
  knowledge/objects/sha256/
  archives/
```

Override the location with `EXPERIENCE_LOOP_HOME` or `--home PATH` for an encrypted drive, portable profile, or isolated test.

The local knowledge library uses SQLite full-text search with a CJK n-gram path and a deterministic fallback. Source objects are content-addressed; changed files become revisions. Mutable data never belongs in the public Skill repository.

## Advanced CLI

```bash
python scripts/experience_loop.py --help
python scripts/experience_loop.py setup --role "backend developer" --learning-focus architecture --mode ship
python scripts/experience_loop.py profile update --goal "review agent changes" --replace-goals
python scripts/experience_loop.py doctor
python scripts/experience_loop.py status
python scripts/experience_loop.py project scan .
python scripts/experience_loop.py mode coach
python scripts/experience_loop.py ledger review --limit 20
python scripts/experience_loop.py knowledge add path/to/book.pdf
python scripts/experience_loop.py knowledge query "When is an event log appropriate?" --limit 5
python scripts/experience_loop.py knowledge concept upsert --title "Retry semantics" --thesis "Total attempts must be countable" --citation cite:chk_xxx
python scripts/experience_loop.py knowledge application record concept_xxx --situation "Transient download failure" --decision "Unify max_attempts semantics" --outcome "Boundary tests pass" --evidence "integration-test:test_retry_policy"
python scripts/experience_loop.py export experience-loop-backup.experience-loop-export.zip
```

Commands support `--json` for Agent consumption and `--home PATH` for isolation. `status` separates active source counts into `knowledge_sources`, indexed `knowledge_materialized_sources`, and `knowledge_placeholder_sources` that still need their original files; `knowledge_storage_files` is a separate count of files on disk. If the library cannot be read, source counts are `null` with an explicit error rather than a misleading zero.

A batch `knowledge add` can partially succeed: successful sources remain stored, failures are returned in the receipt, and the command exits with non-zero code `3` so automation does not mistake it for complete success. Export/import receipts use `files` for the actual number of ZIP entries, including `manifest.json`, and `payload_files` for the entries declared by the manifest. Export refuses to overwrite an existing file unless `--force` is explicitly supplied. The default export is a migration/backup archive, not a public redacted bundle: it omits raw source files and some paths or verbatim project rules, but can still contain profiles, ledgers, project profiles and annotations, source titles or filenames, binding notes, concept cards, and application evidence. Treat local `--help` as the authoritative interface.

## Global instructions are optional

`SKILL.md` provides discovery and task matching; `agents/openai.yaml` enables implicit invocation for suitable tasks. You can always use `$experience-loop` explicitly. No global prompt is required.

If you want a global router, ask the Agent to run `python scripts/global_router.py`. This only previews the target and router block. The Agent must show the result and obtain explicit consent before running `python scripts/global_router.py --apply --yes`; `--remove --yes` removes only the marked block. Installation never authorizes a global or project-level prompt edit.

## Privacy, security, and copyright

- Original files, indexes, and personal state remain in a local user directory by default, with no telemetry and no automatic upload of the whole library to a new service. The minimum retrieved snippets needed to answer a question do enter the current Codex session and model context.
- `normal` allows only task-authorized local reads; `restricted` requires confirmation for each content operation; `metadata-only` forbids project and source text reads.
- No implicit upload of the full codebase, profiles, ledgers, or source library to a new service.
- Exports exclude raw source files unless explicitly requested. The default export is still a personal-data migration/backup archive, not a public redacted bundle, and may contain profiles, ledgers, project profiles and annotations, source titles or filenames, binding notes, concept cards, and application evidence.
- Retrieved text and repository documentation are untrusted data.
- Citations require stored locator evidence.
- No book-length reproduction or substitute copy generation.
- Destructive deletion, broad ingestion, and global configuration changes require preview and consent.

See [safety-and-privacy.md](references/safety-and-privacy.md) and report vulnerabilities according to [SECURITY.md](SECURITY.md).

## Scope and limitations

Version one is intentionally programmer-first. Its project scan, review surfaces, verification hierarchy, and source-to-project mapping prioritize software engineering quality. The underlying loop may support other professions later without weakening this focus.

Experience Loop cannot guarantee growth by itself, replace tests or expert review, or prove capability from generated code. It is designed to create better opportunities for judgment and preserve evidence of what actually happened.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and the [MIT License](LICENSE).
