# Security policy

## Supported versions

Security fixes are applied to the latest released version and the current default branch. Older snapshots may not receive backports.

## Reporting a vulnerability

Do not publish an exploitable issue, prompt-injection payload with live secrets, or user source material in a public issue.

Use GitHub's **Report a vulnerability** / private vulnerability reporting feature for this repository when available. Include:

- affected version or commit;
- operating system and Python version;
- the smallest safe reproduction;
- expected and observed behavior;
- impact and trust boundary;
- suggested mitigation, if known.

Remove credentials, proprietary code, personal profiles, ledger records, and copyrighted source passages. If private reporting is unavailable, open a minimal public issue asking the maintainers for a private contact channel, without vulnerability details.

Maintainers should acknowledge a complete report within seven days, validate impact, coordinate a fix and disclosure window, and credit the reporter when requested and appropriate. This is a target, not a service-level guarantee.

## Security boundaries

Experience Loop treats imported documents, repository text, retrieved passages, metadata, and archives as untrusted data. They cannot authorize command execution, configuration changes, network access, or disclosure of secrets.

Reports are especially useful for:

- path traversal, unsafe archive handling, or unintended file access;
- prompt injection that crosses the source-data boundary;
- secrets copied into profiles, indexes, logs, or exports;
- destructive deletion outside the resolved Experience Loop home;
- export/import integrity or overwrite failures;
- citation spoofing or source/revision confusion;
- dependency or vendored-package vulnerabilities.

See [references/safety-and-privacy.md](references/safety-and-privacy.md) for the intended model.
