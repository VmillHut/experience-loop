# Changelog

All notable user-facing changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Detection-first `auto` control that observes task evidence, detects activated risks and reusable capability seams, then intelligently chooses the useful learning response without a default strength or fixed answer quota.
- A six-direction capability compass and evidence summaries for problem framing, system modeling, verification, reliability, Agent leverage, and ownership.
- Cognitive-coverage, delegation-calibration, and real-user or production feedback guidance for consequential work.
- Progressive personalization that keeps profiles, on-demand article and document use, one-off structured-data analysis, and read-only exemplar-project comparison available through one-sentence or one-path inputs.
- An AI-first installation contract with dry-run, validation, consent, rollback, and post-install handoff boundaries.
- A fixed conversational onboarding flow with optional concrete profile questions and an opt-in interactive tutorial.
- A dedicated guidance-preference profile field so interruption and participation preferences remain separate from explanation style.

### Changed

- Unified user-facing modes as `auto`, `focus`, `deep`, and `off`: `focus` explicitly locks one capability goal, `deep` is explicit full-intensity learning with task quality first, and `off` never adds a learning tail. Legacy `ship`/`incident` inputs normalize to `auto`, while `coach` normalizes to `focus`.
- Reframed the fast path as a learning-overlay bypass after lightweight detection, so it never replaces the host Agent's native planning, tools, risk analysis, or verification and can be reconsidered when material evidence changes.
- Added a capability-monotonicity contract: the Skill may add learning support but must not narrow current or future host reasoning, tool choice, engineering coverage, validation, or useful autonomy.
- Made coupling, boundary, runtime, concurrency, capacity, compatibility, and recovery checks conditional, non-exhaustive risk examples rather than a mandatory checklist or ceiling on stronger future Agents.
- Removed fixed per-task question, learning-seam, checkpoint, and takeaway limits from the adaptive controller; attention is protected by keeping guidance coherent and loading detailed state or references only when they can change the task.
- Strengthened explicit `deep` into adaptive progressive practice: it can use one dense exchange or multiple evidence-driven turns to build a decision framework, explore trade-offs and failures, review Agent output, correct against evidence, and transfer the model without any preset round count.
- Added an adaptive decision-debrief contract: after meaningful user judgments, the Agent fairly reconstructs the reasoning, evaluates only relevant dimensions, gives an evidence-bounded independent recommendation, and distills transferable rules without fixed scorecards or mandatory ceremony.
- Expanded optional personalization with a compact representative-project context covering rough scale, complexity, and actual ownership; title and years calibrate guidance but never count as capability evidence or require a resume.
- Tightened optional implicit routing so only `auto` may be inferred; `focus` and `deep` require an explicit current-task request or an explicitly saved default.
- Replaced dry manual first-run steps with one compact optional profile conversation followed by a single tutorial offer; default `auto` still requires no mode choice.
- Expanded installer receipts with installed runtime/onboarding paths and machine-ready version, mode, status, setup, doctor, uninstall, upgrade, and rollback commands.
- Added platform-copyable shell commands, structured command argv, and repository/commit/dirty provenance so installation Agents do not need to reconstruct or misparse validation steps.
- Made empty onboarding expose no invented role while retaining a backward-compatible nonempty on-disk sentinel, and made repeated setup preserve existing state without offering the beginner tutorial again.
- Guarded rollback receipts so incomplete or unrecognized backups are preserved and reported without emitting an invalid executable rollback command.

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
