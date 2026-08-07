# Changelog

All notable user-facing changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-07

### Added

- Detection-first `auto` control that observes task evidence, detects activated risks and reusable capability seams, then intelligently chooses the useful learning response without a default strength or fixed answer quota.
- A six-direction capability compass and evidence summaries for problem framing, system modeling, verification, reliability, Agent leverage, and ownership.
- Cognitive-coverage, delegation-calibration, and real-user or production feedback guidance for consequential work.
- Progressive personalization that keeps profiles, on-demand article and document use, one-off structured-data analysis, and read-only exemplar-project comparison available through one-sentence or one-path inputs.
- An AI-first installation contract with dry-run, validation, consent, rollback, and post-install handoff boundaries.
- A host-managed `--verify-only` acceptance path so native Skill, Plugin, and Marketplace installers can retain lifecycle ownership.
- An optional OpenAI Plugin distribution layer built from the canonical portable Skill core, with a declared controls-aware SessionStart Hook instead of a second behavior implementation.
- A deterministic read-only `identity` probe and install-receipt fingerprint for proving which exact installed copy participates in first activation.
- A bounded conversational onboarding flow with optional profile questions and an opt-in control micro-tutorial capped at 60 seconds; advanced modes and extensions stay on demand.
- A dedicated guidance-preference profile field so interruption and participation preferences remain separate from explanation style.
- A versioned `controls.json` authority for `default_mode`, `activation_scope`, and `privacy`, separate from content-bearing personalization.

### Changed

- Unified user-facing modes as `auto`, `focus`, `deep`, and `off`: `focus` explicitly locks one capability goal, `deep` is explicit full-intensity learning with task quality first, and `off` never adds a learning tail. Legacy `ship`/`incident` inputs normalize to `auto`, while `coach` normalizes to `focus`.
- Reframed the fast path as a learning-overlay bypass after lightweight detection, so it never replaces the host Agent's native planning, tools, risk analysis, or verification and can be reconsidered when material evidence changes.
- Added a capability-monotonicity contract: the Skill may add learning support but must not narrow current or future host reasoning, tool choice, engineering coverage, validation, or useful autonomy.
- Defined modes as adaptive intent contracts rather than fixed teaching flows, checklists, round counts, or ceilings; stronger current and future host Agents remain free to use better reasoning, tools, and validation.
- Made coupling, boundary, runtime, concurrency, capacity, compatibility, and recovery checks conditional, non-exhaustive risk examples rather than a mandatory checklist or ceiling on stronger future Agents.
- Removed fixed per-task question, learning-seam, checkpoint, and takeaway limits from the adaptive controller; attention is protected by keeping guidance coherent and loading detailed state or references only when they can change the task.
- Strengthened explicit `deep` into adaptive progressive practice: it can use one dense exchange or multiple evidence-driven turns to build a decision framework, explore trade-offs and failures, review Agent output, correct against evidence, and transfer the model without any preset round count.
- Added an adaptive decision-debrief contract: after meaningful user judgments, the Agent fairly reconstructs the reasoning, evaluates only relevant dimensions, gives an evidence-bounded independent recommendation, and distills transferable rules without fixed scorecards or mandatory ceremony.
- Expanded optional personalization with a compact representative-project context covering rough scale, complexity, and actual ownership; title and years calibrate guidance but never count as capability evidence or require a resume.
- Tightened optional implicit routing so only `auto` may be inferred; `focus` and `deep` require an explicit current-task request or an explicitly saved default.
- Separated persistent mode from activation scope: `explicit` is the default, `project` is the recommended opt-in for software workspaces, and `global` requires explicit acceptance of its broader attention scope.
- Replaced dry manual first-run steps with a new-session activation gate, one compact optional profile conversation, and a single tutorial offer; default `auto` still requires no mode choice.
- Split acceptance into filesystem, runtime, host discovery, and current-turn activation. Installation or discovery alone can no longer open onboarding; first activation requires explicit `@`/`$` selection plus a matching identity fingerprint.
- Upgraded activation identity to the versioned v2 algorithm, binding the installed root and version to a deterministic manifest digest of the Skill contract, references, runtime modules, lifecycle scripts, and vendor manifest; Plugin manifests and Hooks remain separately verified distribution layers.
- Made `doctor` fail on stale profile compatibility mirrors and made `doctor --repair` synchronize only `mode`, `privacy`, and `customized` from authoritative controls while holding the data-directory lock.
- Expanded installer receipts with installed runtime/onboarding paths and machine-ready version, mode, status, setup, doctor, uninstall, upgrade, and rollback commands.
- Added platform-copyable shell commands, structured command argv, and repository/commit/dirty provenance so installation Agents do not need to reconstruct or misparse validation steps.
- Made empty onboarding expose no invented role while retaining a backward-compatible nonempty on-disk sentinel, and made repeated setup preserve existing state without offering the beginner tutorial again.
- Guarded rollback receipts so incomplete or unrecognized backups are preserved and reported without emitting an invalid executable rollback command.
- Made installation host-manager-neutral: each upgrade re-resolves the live manager and target instead of treating a Git URL or stale receipt as a universal install protocol.
- Reframed AI installation as an outcome contract: an uncommitted failed route acquires no ownership, and capable Agents continue through safe alternatives before reporting a genuine blocker.
- Added reversible transaction capability probes and a dormant same-volume fallback under the writable Skill root when an outer backup directory is protected.
- Dormant staging and backups no longer retain the canonical `SKILL.md` filename, and rollback is orchestrated by the new lifecycle manager instead of executing an old backup installer.
- Added the Plugin's tiny controls-aware Hook as an opt-in relevance adapter. It reads only `controls.json`, injects nothing when state is missing, corrupt, `off`, or out of scope, and never claims or performs current-turn Skill attachment; explicit selection remains authoritative until the host exposes verifiable automatic attachment.
- Demoted the static global router to an explicitly consented compatibility fallback when Plugin Hooks are unavailable; it no longer carries mode state or duplicates the controller.
- Reduced README image latency by removing remote badge images, lazy-loading below-the-fold diagrams, and losslessly minifying bundled SVG assets.

### Fixed

- **Activation truth:** repository reads, selector-like message text, identity matches, Plugin cache presence, and Hook markers can no longer be promoted into current-turn Skill activation; first onboarding now requires real host attachment provenance plus an independent identity comparison.
- **Host lifecycle:** installer output separates identity, Plugin registration, Skill availability, current-turn attachment, and Hook observation; Installing-Agent text is reported but unverified, while the legacy activation-receipt field is explicitly deprecated and cannot open the onboarding gate.
- **Routing and attention:** `explicit` remains zero-injection by default; the bounded Hook is only a relevance hint, project routing ignores ancestor weak markers such as `package.json` and `AGENTS.md`, and static routing cannot read `SKILL.md` as a fallback.
- **State integrity:** `controls.json` is authoritative, corrupt or `null` controls fail closed, profile compatibility mirrors are transactionally rolled back on write failure, and `doctor` detects and repairs stale mirrors.
- **Packaging and ownership:** standalone and Plugin builds now share one exact runtime payload, source-only development material is excluded, Plugin install/uninstall defer to the Codex Plugin Manager, and local Marketplace builds use validated cachebuster versions without directly changing the host cache.
- **Privacy and onboarding:** `metadata-only` permits only explicit object-scoped, task-scoped, non-persistent content grants; onboarding is optional, urgent work bypasses it, and the first tutorial is reduced to a sub-60-second control lesson.

### Security

- Kept profile, ledger, project, and Knowledge Lens content outside SessionStart routing; the Plugin Hook reads only schema-validated non-content controls and fails closed.
- Required normal host trust review and a new or resumed session before claiming the declared Plugin Hook is active; saving an activation scope is only a preference write.
- Replaced model-authored activation-receipt semantics with five independent lifecycle facts; current-turn activation now requires host attachment provenance and cannot be persisted or inferred from identity, selector text, Hook output copies, or Installing-Agent reports.
- Rejected boolean and floating-point archive schema versions and entry sizes instead of accepting language-level integer equivalence.

## [0.1.0] - 2026-08-05

### Added

- Programmer-first `predict/decide -> execute -> verify -> reflect -> transfer` workflow.
- Delivery-aware `ship`, `coach`, `deep`, `incident`, and `off` modes.
- Idempotent personal setup, project scanning, doctor, mode, and status commands.
- External versioned profile, project, and append-only experience-ledger storage.
- Editable learning profiles, reusable project annotations, and portable project-identity adoption after migration.
- Evidence-oriented decision, verification, reflection, and transfer events.
- Knowledge Lens ingestion, revision tracking, local search, project binding, inspection, removal, and reindexing.
- Evidence-backed concept cards, project-aware concept retrieval, and real application records.
- Markdown, text, reStructuredText, HTML, EPUB, DOCX, and PDF extraction.
- SQLite full-text retrieval with CJK n-gram support and deterministic fallback.
- Source/revision/block locators, content-addressed objects, and untrusted-source markers.
- Explicit local export/import with raw sources excluded unless requested.
- Codex metadata, progressive-disclosure references, bilingual GitHub documentation, and SVG icons.
- Managed install, upgrade backup, rollback, and validated uninstall lifecycle outside the Skill discovery root.
- Security, privacy, copyright, contribution, and vulnerability-reporting guidance.
- Offline `typing_extensions` compatibility wheel so bundled PDF extraction remains self-contained on Python 3.9 and 3.10.
- Ingestion-time warnings for instruction-like source text without elevating imported content into Agent authority.
- Explicit `restored` receipts and portable-placeholder availability semantics when source identity is recovered on another machine.
- Unambiguous Knowledge Lens status counts, query retry guidance, partial-ingest exit code `3`, and archive payload-versus-ZIP entry counts.

### Security

- Reject unsafe archive paths, links, encrypted entries, excessive extraction, and abnormal compression ratios.
- Refuse destructive replacement of filesystem roots, user homes, or non-managed data directories.
- Use cross-process advisory locking, SQLite snapshots, and private POSIX permissions for personal state.
- Make source purge preview-only until confirmed, quarantine objects transactionally, and expose retryable cleanup residue through `doctor`.
- Bound project and knowledge scans by ignore rules, secret-file rules, file counts, byte limits, and symlink/reparse-point containment.
- Keep conventional backup trees from consuming project-scan budgets and prioritize live source roots in large repositories.
- Keep imported instructions outside the Agent authority chain.
- Require preview and explicit consent before global instruction edits or irreversible data removal.
