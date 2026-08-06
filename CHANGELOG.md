# Changelog

All notable user-facing changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Adaptive task control that silently balances delivery pressure, consequence, uncertainty, and learning value.
- A six-direction capability compass and evidence summaries for problem framing, system modeling, verification, reliability, Agent leverage, and ownership.
- Cognitive-coverage, delegation-calibration, and real-user or production feedback guidance for consequential work.
- Progressive personalization that keeps profiles, Knowledge Lens inputs, data and article paths, and exemplar-project comparison available through one-sentence or one-path inputs.

### Changed

- Simplified user-facing modes to `auto`, `focus`, and `off`; legacy `ship`/`incident` and `coach`/`deep` inputs remain compatible and normalize automatically.
- Made first-run setup zero-configuration by default and removed routine mode-selection prompts.

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
