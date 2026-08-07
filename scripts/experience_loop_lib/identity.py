"""Deterministic identity for the exact installed Experience Loop copy."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .common import APP_NAME, VERSION, DataCorruptionError


FINGERPRINT_ALGORITHM = "sha256:experience-loop-identity-v2"
RUNTIME_MANIFEST_SCHEMA = "experience-loop.runtime-contract/v1"
RUNTIME_MANIFEST_DIGEST_ALGORITHM = "sha256"

# This is the activation identity boundary for the installed Skill runtime.
# OpenAI Plugin manifests and Hooks are distribution adapters and are validated
# by the Plugin package contract instead of being folded into this digest.
RUNTIME_IDENTITY_FILES = (
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "references/capability-compass.md",
    "references/experience-model.md",
    "references/host-compatibility.md",
    "references/knowledge-lens.md",
    "references/onboarding.md",
    "references/safety-and-privacy.md",
    "references/setup-and-profiles.md",
    "references/workflow.md",
    "scripts/experience_loop.py",
    "scripts/global_router.py",
    "scripts/experience_loop_lib/__init__.py",
    "scripts/experience_loop_lib/archive.py",
    "scripts/experience_loop_lib/cli.py",
    "scripts/experience_loop_lib/common.py",
    "scripts/experience_loop_lib/controls.py",
    "scripts/experience_loop_lib/extractors.py",
    "scripts/experience_loop_lib/identity.py",
    "scripts/experience_loop_lib/knowledge.py",
    "scripts/experience_loop_lib/ledger.py",
    "scripts/experience_loop_lib/path_policy.py",
    "scripts/experience_loop_lib/profile.py",
    "scripts/experience_loop_lib/project.py",
    "scripts/experience_loop_lib/storage.py",
    "scripts/install.py",
    "scripts/uninstall.py",
    "vendor/manifest.json",
)


def _file_identity(path: Path, relative: str) -> Dict[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DataCorruptionError(
            "安装副本缺少身份校验文件：%s" % path,
            {"path": str(path), "relative_path": relative, "reason": str(exc)},
        ) from exc
    return {
        "path": relative,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def runtime_contract_manifest(content_root: Path) -> Dict[str, Any]:
    """Return the deterministic manifest and digest for runtime identity files."""

    resolved_root = content_root.resolve()
    files = [
        _file_identity(resolved_root.joinpath(*relative.split("/")), relative)
        for relative in RUNTIME_IDENTITY_FILES
    ]
    canonical = json.dumps(
        {"schema": RUNTIME_MANIFEST_SCHEMA, "files": files},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "schema": RUNTIME_MANIFEST_SCHEMA,
        "digest_algorithm": RUNTIME_MANIFEST_DIGEST_ALGORITHM,
        "digest": "sha256:" + hashlib.sha256(canonical).hexdigest(),
        "file_count": len(files),
        "files": files,
    }


def build_installed_identity(
    installed_root: Path, content_root: Path, version: str
) -> Dict[str, Any]:
    """Build one identity using shared installer/runtime canonicalization."""

    resolved_installed_root = installed_root.resolve()
    resolved_content_root = content_root.resolve()
    manifest = runtime_contract_manifest(resolved_content_root)
    hashes = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    fingerprint_input = {
        "name": APP_NAME,
        "root": os.path.normcase(str(resolved_installed_root)),
        "version": version,
        "runtime_manifest_schema": manifest["schema"],
        "runtime_manifest_digest": manifest["digest"],
    }
    canonical = json.dumps(
        fingerprint_input,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **fingerprint_input,
        "skill_manifest": str((resolved_installed_root / "SKILL.md").resolve()),
        # Retained as diagnostics for one compatibility cycle. The v2
        # fingerprint is bound to the complete manifest digest, not just these.
        "skill_sha256": hashes["SKILL.md"],
        "runtime": str(
            (resolved_installed_root / "scripts" / "experience_loop.py").resolve()
        ),
        "runtime_sha256": hashes["scripts/experience_loop.py"],
        "runtime_contract_manifest": {
            "schema": manifest["schema"],
            "digest_algorithm": manifest["digest_algorithm"],
            "digest": manifest["digest"],
            "file_count": manifest["file_count"],
        },
        "fingerprint_algorithm": FINGERPRINT_ALGORITHM,
        "fingerprint": "sha256:" + hashlib.sha256(canonical).hexdigest(),
    }


def runtime_root() -> Path:
    """Return the Skill root containing SKILL.md and scripts/."""

    return Path(__file__).resolve().parents[2]


def installed_identity(root: Optional[Path] = None) -> Dict[str, Any]:
    """Describe and fingerprint the current installed runtime contract."""

    resolved_root = (root or runtime_root()).resolve()
    return build_installed_identity(resolved_root, resolved_root, VERSION)


def identity_probe(expected_fingerprint: Optional[str] = None) -> Dict[str, Any]:
    """Observe or compare runtime identity without claiming host activation."""

    identity = installed_identity()
    expected = expected_fingerprint.strip() if expected_fingerprint else None
    matched = None if expected is None else expected == identity["fingerprint"]
    status = (
        "observed"
        if matched is None
        else ("matched" if matched else "mismatch")
    )
    return {
        "ok": matched is not False,
        "receipt_schema": "experience-loop.identity/v1",
        "status": status,
        "identity": identity,
        "expected_fingerprint": expected,
        "match": matched,
        "comparison": {
            "requested": expected is not None,
            "status": "not-requested" if matched is None else status,
        },
        "host_activation": {
            "status": "not_evaluated",
            "reason": "runtime identity is independent from host activation",
        },
        "proof_scope": {
            "proves": [
                "exact installed Skill root",
                "versioned runtime-contract manifest digest",
                "contents of every enumerated runtime contract file",
                "runtime version",
            ],
            "does_not_prove": [
                "absence or safety of unlisted extra files",
                "Plugin manifest or Hook package integrity",
                "host discovery",
                "current-turn explicit activation",
                "future automatic activation",
            ],
        },
    }
