# Setup and profiles

Use this reference for first-run onboarding, workspace discovery, external state, migration, or the optional global router.

## Setup goals

Complete setup in a few minutes without making the user design a curriculum. Gather only information that changes behavior:

1. Current role and approximate experience.
2. Near-term delivery responsibilities.
3. One to three learning directions, such as debugging, architecture, testing, security, performance, or code review.
4. Preferred default mode and maximum acceptable interruption.
5. Main project path, when available.
6. Privacy boundary for profiles, ledger, and knowledge sources.

Accept “scan this project and infer it” as a valid answer. Inspect first, then present inferred values for correction. Do not require every field.

## First-run sequence

1. Run the runtime's `doctor` or status command.
2. If required local directories or metadata are missing, run setup.
3. Show the proposed external data location.
4. Ask the minimum onboarding questions, or scan the supplied project.
5. Save a versioned personal profile.
6. Save a separate project profile when a project was scanned.
7. Explain the five modes in one sentence each and choose `ship` by default.
8. Offer, but do not require, a global Agent router.
9. Run doctor again and report readiness plus any optional capability limits.

Setup is idempotent. Re-running it must preserve existing data unless the user explicitly confirms reset or replacement.

Interpret runtime status fields literally: `knowledge_sources` counts active logical sources, `knowledge_materialized_sources` counts sources with a local indexed revision, `knowledge_placeholder_sources` counts portable records waiting for their original file, and `knowledge_storage_files` counts physical files under Knowledge Lens storage. If source metadata cannot be read, the source counts are `null` with an explicit status/error; do not reinterpret them as zero.

Use `profile show` to inspect the current profile and `profile update` to append, replace, or clear goals and learning directions as the user's responsibilities change. Do not edit `profile.json` by hand during normal use.

## External state

Keep runtime state outside the installed Skill and source repositories. Resolve the home directory in this order:

1. explicit command option;
2. `EXPERIENCE_LOOP_HOME` environment variable;
3. runtime default for the current user.

The logical layout is:

```text
<experience-loop-home>/
  state.json
  profile.json
  projects/
    index.json
    <project-id>.json
  ledger/
    events.jsonl
  knowledge/
    library.sqlite
    objects/sha256/
```

Do not assume every runtime version uses exactly these filenames. Use its commands for writes and migrations. Read raw files only for diagnosis, backup, or recovery.

## Personal profile

Record stable preferences, not a personality verdict. Useful fields include:

- role and experience range;
- delivery context;
- active learning directions;
- default mode;
- interruption budget;
- explanation style;
- current hypotheses about strengths and gaps;
- consent settings and schema version.

Treat inferred strengths and gaps as hypotheses with confidence, evidence references, and last-updated timestamps. Never label the user from a single task.

Privacy modes are operational boundaries:

- `normal`: a user-authorized task may read allowed project and source text;
- `restricted`: every content-bearing scan, ingestion, query, chunk inspection, or reindex requires explicit confirmation for that operation;
- `metadata-only`: retain only metadata and approved derived concepts; do not read project or source text.

Changing a mode does not authorize unrelated files, secrets, uploads, or external services.

## Project profile

Derive a project ID from a canonical workspace identity rather than a display name alone. Capture:

- repository root and remote identity when available;
- languages, frameworks, and build systems;
- authoritative instructions and docs;
- test, lint, type-check, build, and run commands;
- architecture boundaries and module map;
- generated, vendor, secret, and high-risk paths;
- current learning opportunities tied to real responsibilities;
- scan timestamp and confidence.

Prefer a targeted scan. Skip dependency caches, build outputs, generated artifacts, `.git`, vendored code, conventional backup directories, and known secret locations. Prioritize conventional live source roots so a large backup or plugin tree cannot consume the whole scan budget. If a backup directory is itself the intended subject, scan that directory explicitly as the root. Never ingest a repository into Knowledge Lens merely because it was scanned.

Refresh stale or contradicted fields from current source. Project profiles are navigation aids, not authority.

## Mode and interruption budget

Store a default, but select per task. A reasonable initial budget is:

- `ship`: zero required questions, at most one optional checkpoint;
- `coach`: at most two short checkpoints;
- `deep`: negotiated with the user;
- `incident`: zero until health is restored;
- `off`: no learning behavior or ledger writes.

When a deadline, outage, failing release, or explicit “just fix it” request conflicts with the saved mode, temporarily choose `ship` or `incident` and explain the switch briefly.

## Optional global Agent router

The Skill must work without a global prompt. Offer a minimal router only to users who want implicit activation across projects.

Before writing:

1. Locate the user's global Agent instruction file supported by the current Codex installation.
2. Read it and preserve unrelated content.
3. Run `python scripts/global_router.py` to obtain the no-write preview when using the bundled router.
4. Show the exact proposed insertion or diff.
5. Explain that it changes behavior in all workspaces.
6. Obtain explicit consent before running `python scripts/global_router.py --apply --yes`.

Keep the router short and avoid copying this Skill into the global prompt. A suitable intent is:

```text
Use $experience-loop for substantive programming work when it can preserve delivery speed while improving engineering judgment. Default to ship mode; honor “off” or “just do it”; never require project-level installation.
```

Do not write a project-level router unless the user explicitly asks for team-wide behavior.

## Portability and backups

Separate the portable Skill code from personal data:

- publish or clone the Skill repository normally;
- export personal state through the runtime;
- exclude raw copyrighted sources by default;
- encrypt or protect exported private data using the user's chosen mechanism;
- import into a new machine only after showing what categories will be restored.

An export must contain schema/version metadata and checksums. Import must validate before replacing current state. In archive receipts, `files` means actual ZIP entries including `manifest.json`, while `payload_files` means entries declared by the manifest. Prefer merge with a conflict report over silent overwrite.

## Repair and reset

Use doctor first. Repair indexes from immutable sources and ledger facts where possible. Never fabricate missing evidence.

For reset or deletion:

1. show the resolved data path and affected categories;
2. distinguish derived indexes from original sources and profile/ledger data;
3. require explicit confirmation for irreversible deletion;
4. verify the result and report leftovers.
