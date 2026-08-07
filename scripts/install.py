#!/usr/bin/env python3
"""Install Experience Loop into an Agent skill directory resolved at runtime.

The installer copies only runtime files. Personal data always lives outside the
skill directory and is therefore untouched by installs and upgrades. Dynamic host
metadata affects receipts and duplicate checks only; it cannot change Skill behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

SKILL_NAME = "experience-loop"
INSTALLER_VERSION = 6
HOST_FACTS_SCHEMA = "experience-loop.host-facts/v1"
LEGACY_ACTIVATION_RECEIPT_SCHEMA = "experience-loop.activation/v1"
LEGACY_ACTIVATION_RECEIPT_STATUS = "deprecated-advisory"
PORTABLE_SKILL_PAYLOAD_FILES = (
    "SKILL.md",
    "LICENSE",
    "VERSION",
    "THIRD_PARTY_NOTICES.md",
    "agents/openai.yaml",
    "assets/icon-large.svg",
    "assets/icon-small.svg",
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
    "scripts/install.py",
    "scripts/uninstall.py",
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
    "vendor/manifest.json",
    "vendor/wheels/pypdf-6.14.2-py3-none-any.whl",
    "vendor/wheels/typing_extensions-4.16.0-py3-none-any.whl",
    "licenses/pypdf-LICENSE",
    "licenses/typing_extensions-LICENSE",
)
SOURCE_ONLY_CONTAMINATION = (
    "AGENTS.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "README.en.md",
    "docs",
    "evals",
    "tests",
    "packaging",
    "scripts/build_plugin.py",
    "scripts/verify_release.py",
)
MARKER_NAME = ".experience-loop-install.json"
CURRENT_RUNTIME_CONTRACT = 3
COMPATIBLE_INSTALL_FILES = (
    "SKILL.md",
    "VERSION",
    "agents/openai.yaml",
    "assets/icon-large.svg",
    "assets/icon-small.svg",
    "references/capability-compass.md",
    "references/experience-model.md",
    "references/knowledge-lens.md",
    "references/safety-and-privacy.md",
    "references/setup-and-profiles.md",
    "references/workflow.md",
    "scripts/experience_loop.py",
    "scripts/experience_loop_lib/__init__.py",
    "scripts/experience_loop_lib/archive.py",
    "scripts/experience_loop_lib/cli.py",
    "scripts/experience_loop_lib/common.py",
    "scripts/experience_loop_lib/extractors.py",
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
RUNTIME_CONTRACT_1_FILES = COMPATIBLE_INSTALL_FILES + (
    "references/onboarding.md",
)
RUNTIME_CONTRACT_2_FILES = RUNTIME_CONTRACT_1_FILES + (
    "references/host-compatibility.md",
)
CURRENT_SOURCE_REQUIRED_FILES = RUNTIME_CONTRACT_2_FILES + (
    "scripts/global_router.py",
    "scripts/experience_loop_lib/controls.py",
    "scripts/experience_loop_lib/identity.py",
)
RUNTIME_CONTRACT_FILES = {
    1: RUNTIME_CONTRACT_1_FILES,
    2: RUNTIME_CONTRACT_2_FILES,
    CURRENT_RUNTIME_CONTRACT: CURRENT_SOURCE_REQUIRED_FILES,
}
BACKUP_DIRECTORY_NAME = "skill-backups"
LOCAL_TRANSACTION_DIRECTORY_NAME = ".experience-loop-transactions"
DORMANT_SKILL_MANIFEST = ".experience-loop-SKILL.md"
LIFECYCLE_INSTALLER_NAME = "install.py"
LIFECYCLE_UNINSTALLER_NAME = "uninstall.py"
HOST_SCOPES = ("user", "project", "custom")


def validated_contract_text(
    value: Optional[str], field: str, maximum: int, *, default: Optional[str] = None
) -> Optional[str]:
    if value is None:
        return default
    if not isinstance(value, str):
        raise RuntimeError(f"{field} must be text.")
    cleaned = value.strip()
    if not cleaned:
        return default
    if len(cleaned) > maximum:
        raise RuntimeError(f"{field} exceeds the {maximum}-character safety limit.")
    if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
        raise RuntimeError(f"{field} must be a single printable line.")
    return cleaned


def first_reparse_component(path: Path) -> Optional[Path]:
    normalized = normalized_target(path)
    current = Path(normalized.anchor)
    parts = normalized.parts[1:] if normalized.anchor else normalized.parts
    for part in parts:
        current = current / part
        if _is_reparse_point(current):
            return current
    return None


def validate_discovery_root(path: Path) -> Path:
    root = normalized_target(path)
    dangerous = (Path(root.anchor), normalized_target(Path.home()))
    if any(_same_path(root, candidate) for candidate in dangerous):
        raise RuntimeError(f"Refusing broad discovery root: {root}")
    reparse_component = first_reparse_component(root)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing discovery root with a symlink, junction, or reparse-point "
            f"component: {reparse_component}"
        )
    return root


def unique_discovery_roots(target: Path, supplied: list[Path]) -> list[Path]:
    roots = [validate_discovery_root(target.parent)]
    for candidate in supplied:
        root = validate_discovery_root(candidate)
        if not any(_same_path(root, existing) for existing in roots):
            roots.append(root)
    return roots


def build_host_contract(args: argparse.Namespace, target: Path) -> dict[str, object]:
    host = validated_contract_text(args.host, "--host", 80, default="current-agent")
    invocation = validated_contract_text(args.invocation, "--invocation", 160)
    reload_hint = validated_contract_text(args.reload_hint, "--reload-hint", 500)
    evidence = validated_contract_text(args.host_evidence, "--host-evidence", 500)
    affected_hosts: list[str] = []
    for raw_host in args.affected_host or []:
        label = validated_contract_text(raw_host, "--affected-host", 80)
        if label and label not in affected_hosts:
            affected_hosts.append(label)
    if not affected_hosts and host:
        affected_hosts.append(host)
    roots = unique_discovery_roots(target, args.discovery_root or [])
    return {
        "host": host,
        "scope": args.scope or "custom",
        "target": str(target),
        "invocation": invocation,
        "reload_hint": reload_hint,
        "host_evidence": evidence,
        "discovery_roots": [str(root) for root in roots],
        "affected_hosts": affected_hosts,
    }


def host_receipt(contract: dict[str, object]) -> dict[str, object]:
    reload_hint = contract.get("reload_hint")
    has_report = bool(contract.get("host_evidence"))
    return {
        **contract,
        "host_contract_status": (
            "reported-by-installing-agent"
            if has_report
            else "missing-installing-agent-report"
        ),
        "host_evidence_status": "reported-unverified" if has_report else "missing",
        "host_evidence_note": (
            "Installing-Agent text is advisory context only. It is not Plugin "
            "registration, Skill availability, current-turn attachment provenance, "
            "or Hook observation."
        ),
        "support_level": "dynamic-host-contract-requires-session-validation",
        "reload_hint": reload_hint
        or "Resolve and use the current host's documented reload procedure.",
        "host_verification_hint": (
            "Use the current host's independently verified discovery mechanism and "
            "prove that it loads this exact installed SKILL.md. Invocation metadata "
            "is reported separately and is never executed by the installer."
        ),
        "discovery_status": "requires-host-session-validation",
        "discovery_roots_coverage": "reported-by-installing-agent",
        "discovery_roots_note": (
            "Duplicate protection covers only the discovery roots declared by the "
            "installation AI in this receipt; the report is not host-discovery proof."
        ),
        "global_router": "not-authorized-by-installation",
        "core_behavior_contract": "unchanged-across-hosts",
        "capabilities": {
            "guidance": "installed-core",
            "profile": "requires-runtime-validation",
            "ledger": "requires-runtime-validation",
            "knowledge_lens": "requires-runtime-validation",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install Experience Loop using host facts resolved by the calling AI; "
            "the Skill behavior and runtime remain identical across hosts."
        )
    )
    parser.add_argument(
        "--host",
        default=None,
        help=(
            "Informational current-host label reported by the installation AI. "
            "It does not select a hard-coded adapter."
        ),
    )
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help=(
            "Current host Skill directory reported by the installation AI and "
            "validated only as an installation filesystem target by this script."
        ),
    )
    parser.add_argument(
        "--transaction-root",
        type=Path,
        help=(
            "Optional same-volume transaction directory. If omitted, the installer "
            "probes safe candidates and falls back inside the writable Skill root."
        ),
    )
    parser.add_argument(
        "--restore-from",
        type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help=(
            "Validate a complete host-managed copy without writing or taking over "
            "its install lifecycle. The target must be this installer copy's root."
        ),
    )
    parser.add_argument("--scope", choices=HOST_SCOPES, default=None)
    parser.add_argument(
        "--invocation",
        help=(
            "Invocation selector reported by the installation AI; recorded verbatim "
            "and never executed. It remains advisory until the current host supplies "
            "attachment provenance in a fresh turn."
        ),
    )
    parser.add_argument(
        "--reload-hint",
        help="Current host reload instruction, recorded as text and never executed.",
    )
    parser.add_argument(
        "--host-evidence",
        help=(
            "Short Installing-Agent report about the host contract. The installer "
            "stores it as unverified advisory context, never as host evidence."
        ),
    )
    parser.add_argument(
        "--discovery-root",
        action="append",
        type=Path,
        default=[],
        help="Additional current-host Skill scan root to check for duplicate installs.",
    )
    parser.add_argument(
        "--replace-discovery-roots",
        action="store_true",
        help=(
            "Replace stored discovery roots with the current target parent and the "
            "--discovery-root values supplied now. Requires fresh --host-evidence."
        ),
    )
    parser.add_argument(
        "--affected-host",
        action="append",
        default=[],
        help="Host label that may discover this target; repeat for shared directories.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate and show the target only."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an unrecognized existing directory after preserving a backup.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def expected_skill_identity(
    target: Path, content_root: Path, version: str
) -> dict[str, object]:
    identity_module_path = (
        content_root.resolve()
        / "scripts"
        / "experience_loop_lib"
        / "identity.py"
    )
    if not identity_module_path.is_file():
        marker = read_marker(content_root)
        declared_contract = marker.get("runtime_contract") if marker else None
        controls_module = (
            content_root.resolve()
            / "scripts"
            / "experience_loop_lib"
            / "controls.py"
        )
        if controls_module.exists() or (
            type(declared_contract) is int
            and declared_contract >= CURRENT_RUNTIME_CONTRACT
        ):
            raise RuntimeError(
                "Current runtime contract is missing its v2 identity module; "
                "refusing to downgrade the activation proof."
            )
        # Compatibility for rollback to pre-identity runtime contracts. Current
        # installs must use the shared v2 implementation below; this narrower
        # proof is never selected merely because a current manifest is damaged.
        skill_payload = (content_root / "SKILL.md").read_bytes()
        runtime_payload = (
            content_root / "scripts" / "experience_loop.py"
        ).read_bytes()
        fingerprint_input = {
            "name": SKILL_NAME,
            "root": os.path.normcase(str(target.resolve())),
            "version": version,
            "skill_sha256": hashlib.sha256(skill_payload).hexdigest(),
            "runtime_sha256": hashlib.sha256(runtime_payload).hexdigest(),
        }
        canonical = json.dumps(
            fingerprint_input,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {
            **fingerprint_input,
            "skill_manifest": str((target / "SKILL.md").resolve()),
            "runtime": str((target / "scripts" / "experience_loop.py").resolve()),
            "fingerprint_algorithm": "sha256:experience-loop-identity-v1",
            "fingerprint": "sha256:" + hashlib.sha256(canonical).hexdigest(),
            "compatibility_scope": "legacy-pre-v2-runtime-contract",
        }

    scripts_directory = str(content_root.resolve() / "scripts")
    added_path = scripts_directory not in sys.path
    if added_path:
        sys.path.insert(0, scripts_directory)
    try:
        identity_module = importlib.import_module("experience_loop_lib.identity")
        return identity_module.build_installed_identity(target, content_root, version)
    finally:
        if added_path:
            sys.path.remove(scripts_directory)


def onboarding_prompt(
    target: Path,
    host_contract: dict[str, object],
    identity: dict[str, object],
) -> str:
    reference = (target / "references" / "onboarding.md").resolve()
    invocation = host_contract.get("invocation")
    if isinstance(invocation, str) and invocation:
        activation = (
            f'请在新一条消息中使用当前宿主的显式调用方式 "{invocation}" 激活 '
            f'Experience Loop，并先核对安装回执中的身份指纹 "{identity["fingerprint"]}"。'
        )
    else:
        activation = (
            "当前宿主的显式调用方式尚未解析；请先通过宿主真实的 Skill 列表或"
            "选择器解析并显式激活 Experience Loop。"
        )
    return (
        "Experience Loop 完整核心已安装，但安装轮不能证明 Skill 已进入当前模型"
        f"上下文。{activation}只有宿主在当前轮提供 attachment provenance，且"
        "独立身份比对匹配后，才检查是否已经"
        "初始化；若尚未初始化，读取 "
        f'"{reference}" 并开始对话式初始化。所有画像问题都可跳过，最后只询问我'
        "是否需要不超过 60 秒的控制微型教学；若已经初始化，请保留现有画像且不要重复"
        "新手教学，除非我明确要求。"
    )


def independent_lifecycle_facts(
    identity: dict[str, object],
    *,
    identity_status: str,
    identity_evidence: str,
    host_status: str,
) -> dict[str, object]:
    """Report five independent facts without converting model text into host proof."""

    return {
        "identity": {
            "status": identity_status,
            "evidence": identity_evidence,
            "fingerprint": identity["fingerprint"],
            "fingerprint_algorithm": identity["fingerprint_algorithm"],
        },
        "plugin_registration": {
            "status": host_status,
            "evidence": "requires-host-plugin-manager-provenance",
        },
        "skill_availability": {
            "status": host_status,
            "evidence": "requires-current-host-skill-registry-provenance",
        },
        "current_turn_activation": {
            "status": host_status,
            "evidence": "requires-current-turn-host-attachment-provenance",
            "identity_substitution": "forbidden",
        },
        "hook_observed": {
            "status": host_status,
            "evidence": "requires-host-injected-hook-marker",
        },
    }


def completed_install_protocol(
    target: Path,
    content_root: Path,
    version: str,
    host_contract: dict[str, object],
    filesystem_status: str,
    runtime_validation_status: str,
) -> dict[str, object]:
    target = target.resolve()
    identity = expected_skill_identity(target, content_root, version)
    invocation = host_contract.get("invocation")
    has_invocation = isinstance(invocation, str) and bool(invocation)
    if has_invocation:
        handoff_state = "awaiting-explicit-invocation"
        prompt = (
            f"通过宿主真实选择 UI 使用 {invocation}；只有当前轮 attachment "
            "provenance 被宿主观察到后，才从宿主附加的副本核对安装身份指纹 "
            f"{identity['fingerprint']}。不要生成激活回执来替代宿主证据。"
        )
        next_action = {
            "kind": "explicit-skill-invocation",
            "message": (
                "在新一条消息中通过宿主真实选择 UI 附加 Experience Loop；"
                "观察 attachment provenance 后再独立核对身份。"
            ),
            "invocation": invocation,
            "prompt": prompt,
            "required_observations": [
                "facts.current_turn_activation.status=observed",
                "facts.identity.status=verified",
            ],
            "expected_receipt": LEGACY_ACTIVATION_RECEIPT_SCHEMA,
            "expected_receipt_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "expected_receipt_note": (
                "Compatibility metadata only; a model-authored receipt never proves "
                "or validates current-turn activation."
            ),
        }
    else:
        handoff_state = "awaiting-invocation-resolution"
        prompt = None
        next_action = {
            "kind": "resolve-explicit-invocation",
            "message": (
                "先从当前宿主真实的 Skill 列表、选择器或帮助中解析显式调用方式；"
                "不要在未激活 Skill 的安装轮开始初始化。"
            ),
            "required_observations": [
                "facts.current_turn_activation.status=observed",
                "facts.identity.status=verified",
            ],
            "expected_receipt": LEGACY_ACTIVATION_RECEIPT_SCHEMA,
            "expected_receipt_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "expected_receipt_note": (
                "Compatibility metadata only; a model-authored receipt never proves "
                "or validates current-turn activation."
            ),
        }
    if identity["fingerprint_algorithm"] == "sha256:experience-loop-identity-v2":
        identity_proof_scope = (
            "The v2 identity fingerprint binds the expected root, version, and "
            "versioned runtime-contract manifest digest. Plugin manifests and "
            "Hooks remain separately validated distribution layers. "
        )
    else:
        identity_proof_scope = (
            "This rollback restored a pre-v2 runtime contract, so its legacy "
            "identity binds only the expected root, Skill manifest, runtime entry, "
            "and version. Reinstall or upgrade to obtain full manifest identity. "
        )
    return {
        "receipt_schema": "experience-loop.install/v2",
        "facts_schema": HOST_FACTS_SCHEMA,
        "facts": independent_lifecycle_facts(
            identity,
            identity_status="verified",
            identity_evidence="deterministic-installed-copy-comparison",
            host_status="not-observed",
        ),
        "acceptance": {
            "host_lifecycle_fields_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "host_lifecycle_fields_note": (
                "Use top-level facts for host lifecycle. The legacy host_discovery "
                "and current_turn_activation fields are advisory only."
            ),
            "filesystem": {
                "status": "verified",
                "evidence": filesystem_status,
            },
            "runtime": {
                "status": "pending",
                "evidence": runtime_validation_status,
            },
            "host_discovery": {
                "status": "pending",
                "evidence": "requires-host-session-validation",
                "status_semantics": LEGACY_ACTIVATION_RECEIPT_STATUS,
                "replacement": "facts.skill_availability",
            },
            "current_turn_activation": {
                "status": "pending",
                "evidence": "requires-current-turn-host-attachment-provenance",
                "status_semantics": LEGACY_ACTIVATION_RECEIPT_STATUS,
                "replacement": "facts.current_turn_activation",
            },
        },
        "activation_handoff": {
            "required": True,
            "state": handoff_state,
            "session_requirement": "new-prompt-or-refreshed-session",
            "invocation": invocation if has_invocation else None,
            "reload_hint": host_contract.get("reload_hint"),
            "required_fact": "facts.current_turn_activation",
            "required_provenance": "host-attachment",
            "identity_requirement": "facts.identity.status=verified",
            "required_receipt": LEGACY_ACTIVATION_RECEIPT_SCHEMA,
            "required_receipt_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "required_receipt_note": (
                "Retained for JSON compatibility only; it is not a gate and cannot "
                "be generated or validated by the model as host evidence."
            ),
            "expected_identity": identity,
            "prompt": prompt,
            "proof_scope": identity_proof_scope + (
                "The surrounding host session must still prove explicit activation; "
                "identity and Installing-Agent reports cannot substitute for current-turn "
                "host attachment provenance."
            ),
        },
        "onboarding_gate": {
            "allowed": False,
            "status": "blocked-pending-explicit-activation",
            "decision_owner": "current-host-session",
            "required_facts": {
                "identity": "verified",
                "current_turn_activation": "observed-from-host-attachment-provenance",
            },
            "required_receipt": LEGACY_ACTIVATION_RECEIPT_SCHEMA,
            "required_receipt_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "required_receipt_note": (
                "Retained for JSON compatibility only; it never opens this gate."
            ),
            "required_identity_fingerprint": identity["fingerprint"],
            "reference": str((target / "references" / "onboarding.md").resolve()),
        },
        "next_action": next_action,
        # Compatibility fields retained for one receipt cycle. New consumers should
        # use acceptance, activation_handoff, onboarding_gate, and next_action.
        "runtime": identity["runtime"],
        "onboarding_reference": str(
            (target / "references" / "onboarding.md").resolve()
        ),
        "onboarding_prompt": onboarding_prompt(target, host_contract, identity),
        "onboarding_state": "blocked-pending-explicit-activation",
        "filesystem_status": filesystem_status,
        "runtime_validation_status": runtime_validation_status,
    }


def preview_install_protocol(
    source: Path,
    target: Path,
    version: str,
    host_contract: dict[str, object],
    *,
    blocked: bool,
) -> dict[str, object]:
    identity = expected_skill_identity(target, source, version)
    return {
        "receipt_schema": "experience-loop.install/v2",
        "facts_schema": HOST_FACTS_SCHEMA,
        "facts": independent_lifecycle_facts(
            identity,
            identity_status="preview",
            identity_evidence="preview-of-expected-installed-copy",
            host_status="not-run",
        ),
        "acceptance": {
            "host_lifecycle_fields_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "host_lifecycle_fields_note": (
                "Use top-level facts for host lifecycle. The legacy host_discovery "
                "and current_turn_activation fields are advisory only."
            ),
            "filesystem": {
                "status": "blocked" if blocked else "preview",
                "evidence": "preview-only",
            },
            "runtime": {
                "status": "not-run",
                "evidence": "not-run-during-dry-run",
            },
            "host_discovery": {
                "status": "not-run",
                "status_semantics": LEGACY_ACTIVATION_RECEIPT_STATUS,
                "replacement": "facts.skill_availability",
            },
            "current_turn_activation": {
                "status": "not-run",
                "status_semantics": LEGACY_ACTIVATION_RECEIPT_STATUS,
                "replacement": "facts.current_turn_activation",
            },
        },
        "activation_handoff": {
            "required": False,
            "state": "blocked-before-installation" if blocked else "awaiting-installation",
            "invocation": host_contract.get("invocation"),
            "required_receipt": LEGACY_ACTIVATION_RECEIPT_SCHEMA,
            "required_receipt_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "required_receipt_note": (
                "Retained for JSON compatibility only; it is not an activation gate."
            ),
            "expected_identity": identity,
            "prompt": None,
        },
        "onboarding_gate": {
            "allowed": False,
            "status": "blocked-before-installation",
            "required_receipt": LEGACY_ACTIVATION_RECEIPT_SCHEMA,
            "required_receipt_status": LEGACY_ACTIVATION_RECEIPT_STATUS,
            "required_receipt_note": (
                "Retained for JSON compatibility only; it never opens this gate."
            ),
        },
        "next_action": {
            "kind": "resolve-install-blockers" if blocked else "complete-installation",
            "message": (
                "Resolve the reported installation blockers, then preview again."
                if blocked
                else "Run the same validated installation without --dry-run."
            ),
        },
        "filesystem_status": "preview-only",
        "runtime_validation_status": "not-run-during-dry-run",
    }


def source_provenance(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(root.resolve()),
        "repository": None,
        "commit": None,
        "dirty": None,
        "git_note": None,
    }
    try:
        top_level = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        result["git_note"] = f"Git metadata unavailable: {exc}"
        return result
    if top_level.returncode != 0 or not top_level.stdout.strip():
        result["git_note"] = (
            top_level.stderr.strip() or "Source is not a standalone Git checkout"
        )
        return result
    discovered_root = Path(top_level.stdout.strip()).resolve()
    if not _same_path(discovered_root, root.resolve()):
        result["git_note"] = (
            f"Source is inside a different Git worktree: {discovered_root}"
        )
        return result

    commands = {
        "repository": [
            "git",
            "-C",
            str(root),
            "config",
            "--get",
            "remote.origin.url",
        ],
        "commit": ["git", "-C", str(root), "rev-parse", "HEAD"],
    }
    failures = []
    for field, command in commands.items():
        try:
            completed = subprocess.run(
                command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            failures.append(f"{field}: {exc}")
            continue
        if completed.returncode == 0 and completed.stdout.strip():
            result[field] = completed.stdout.strip()
        else:
            detail = completed.stderr.strip() or "Git metadata unavailable"
            failures.append(f"{field}: {detail}")
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        failures.append(f"dirty: {exc}")
    else:
        if completed.returncode == 0:
            result["dirty"] = bool(completed.stdout.strip())
        else:
            detail = completed.stderr.strip() or "Git worktree status unavailable"
            failures.append(f"dirty: {detail}")
    if failures:
        result["git_note"] = "; ".join(failures)
    return result


def validate_source(root: Path) -> None:
    problems = [
        problem
        for relative in PORTABLE_SKILL_PAYLOAD_FILES
        if (problem := required_file_validation_error(root, relative)) is not None
    ]
    if problems:
        raise RuntimeError("Skill source is incomplete or unsafe: " + "; ".join(problems))
    if read_skill_name(root) != SKILL_NAME:
        raise RuntimeError(f"Skill source does not declare name: {SKILL_NAME}")
    vendor_error = vendor_bundle_validation_error(root)
    if vendor_error is not None:
        raise RuntimeError(vendor_error)


def normalized_target(path: Path) -> Path:
    """Return an absolute lexical path without following the final entry."""

    expanded = os.path.expanduser(str(path))
    return Path(os.path.abspath(expanded))


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def openai_plugin_context(skill_root: Path) -> Optional[dict[str, object]]:
    """Recognize the Skill only when nested in a valid OpenAI Plugin bundle."""

    root = normalized_target(skill_root)
    if root.name.casefold() != SKILL_NAME or root.parent.name.casefold() != "skills":
        return None
    plugin_root = root.parent.parent
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    if _is_reparse_point(plugin_root) or _is_reparse_point(manifest_path):
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict) or manifest.get("name") != SKILL_NAME:
        return None
    version = manifest.get("version")
    skills_path = manifest.get("skills")
    if not isinstance(version, str) or not version.strip():
        return None
    if not isinstance(skills_path, str) or Path(skills_path).is_absolute():
        return None
    normalized_skills = Path(skills_path).as_posix().rstrip("/")
    if normalized_skills not in {"skills", "./skills"}:
        return None
    expected_root = normalized_target(plugin_root / normalized_skills / SKILL_NAME)
    if not _same_path(expected_root, root):
        return None
    return {
        "kind": "openai-plugin",
        "plugin_name": SKILL_NAME,
        "plugin_version": version,
        "plugin_root": str(plugin_root),
        "skill_root": str(root),
        "manifest": str(manifest_path),
    }


def source_only_contamination(root: Path) -> list[str]:
    """List obvious repository/development content that must not ship to users."""

    found = [relative for relative in SOURCE_ONLY_CONTAMINATION if (root / relative).exists()]
    assets = root / "assets"
    if assets.is_dir():
        found.extend(
            path.relative_to(root).as_posix()
            for path in sorted(assets.glob("readme-*.svg"))
            if path.is_file()
        )
    return sorted(set(found))


def validate_host_managed_distribution(root: Path) -> None:
    contamination = source_only_contamination(root)
    if contamination:
        raise RuntimeError(
            "Host-managed copy contains source-only development content: "
            + ", ".join(contamination)
        )


def plugin_manager_required_receipt(
    skill_root: Path, operation: str
) -> dict[str, object]:
    context = openai_plugin_context(skill_root)
    if context is None:
        raise RuntimeError("The current Skill copy is not a validated OpenAI Plugin bundle.")
    return {
        "status": "host-manager-required",
        "operation": operation,
        "distribution": context,
        "lifecycle_owner": "codex-plugin-manager",
        "facts_schema": HOST_FACTS_SCHEMA,
        "facts": {
            "identity": {
                "status": "not-evaluated",
                "evidence": "run-verify-only-from-the-installed-copy",
            },
            "plugin_registration": {
                "status": "unknown",
                "evidence": "requires-host-plugin-manager-provenance",
            },
            "skill_availability": {
                "status": "unknown",
                "evidence": "requires-current-host-skill-registry-provenance",
            },
            "current_turn_activation": {
                "status": "unknown",
                "evidence": "requires-current-turn-host-attachment-provenance",
                "identity_substitution": "forbidden",
            },
            "hook_observed": {
                "status": "unknown",
                "evidence": "requires-host-injected-hook-marker",
            },
        },
        "registration_status": "unknown",
        "enabled_status": "unknown",
        "hook_trust_status": "unknown",
        "hook_observation_status": "unknown",
        "host_discovery_status": "unknown",
        "current_turn_activation_status": "unknown",
        "personal_data_preserved": True,
        "personal_data_note": (
            "No personal Experience Loop data was inspected or changed. The bundled "
            "Plugin manifest was read only to identify the lifecycle owner; no host "
            "Plugin cache file was changed."
        ),
        "next_action": {
            "kind": "use-host-plugin-manager",
            "message": (
                "Resolve the installed Plugin id with the host Plugin manager, then perform "
                "this lifecycle operation through that manager. Do not copy to or delete "
                "from the host Plugin cache directly."
            ),
            "list_command": "codex plugin list --json",
            "remove_command_template": (
                "codex plugin remove <plugin-id-from-list> --json"
            ),
            "install_command_template": (
                "codex plugin add <plugin-name@marketplace> --json"
            ),
            "session_requirement": "start-a-new-task-after-install-or-update",
        },
    }


def _is_reparse_point(path: Path) -> bool:
    try:
        value = os.lstat(str(path))
    except OSError:
        return False
    if stat.S_ISLNK(value.st_mode):
        return True
    attributes = getattr(value, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(reparse_flag and attributes & reparse_flag)


def required_file_validation_error(
    root: Path, relative: str, skill_manifest: str = "SKILL.md"
) -> Optional[str]:
    """Reject missing files and reparse points in every path component."""

    actual_relative = skill_manifest if relative == "SKILL.md" else relative
    relative_path = Path(actual_relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return f"Unsafe required path: {actual_relative}"
    current = root
    for part in relative_path.parts:
        current = current / part
        if _is_reparse_point(current):
            return (
                "Required path contains a symlink, junction, or reparse point: "
                f"{actual_relative}"
            )
    if not current.is_file():
        return f"Required file is missing: {actual_relative}"
    return None


def vendor_bundle_validation_error(root: Path) -> Optional[str]:
    """Statically validate bundled wheels and licenses without importing backup code."""

    manifest_problem = required_file_validation_error(root, "vendor/manifest.json")
    if manifest_problem is not None:
        return manifest_problem
    manifest_path = root / "vendor" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"vendor/manifest.json is invalid: {exc}"
    packages = manifest.get("packages") if isinstance(manifest, dict) else None
    if not isinstance(packages, list):
        return "vendor/manifest.json packages must be a list."
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            return f"Vendor package entry {index} is not an object."
        relative_file = package.get("file")
        relative_license = package.get("license_file")
        expected_hash = package.get("sha256")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (relative_file, relative_license, expected_hash)
        ):
            return f"Vendor package entry {index} has incomplete file metadata."
        wheel_manifest_path = PurePosixPath(relative_file)
        license_manifest_path = PurePosixPath(relative_license)
        if (
            wheel_manifest_path.is_absolute()
            or ".." in wheel_manifest_path.parts
            or not wheel_manifest_path.parts
            or wheel_manifest_path.parts[0] != "wheels"
            or wheel_manifest_path.suffix.lower() != ".whl"
        ):
            return f"Vendored artifact path is unsafe: {relative_file}"
        if (
            license_manifest_path.is_absolute()
            or len(license_manifest_path.parts) < 3
            or license_manifest_path.parts[:2] != ("..", "licenses")
            or ".." in license_manifest_path.parts[2:]
        ):
            return f"Vendor license path is unsafe: {relative_license}"
        wheel_relative = Path("vendor", *wheel_manifest_path.parts)
        license_relative = Path("licenses", *license_manifest_path.parts[2:])
        for relative in (wheel_relative, license_relative):
            problem = required_file_validation_error(root, str(relative))
            if problem is not None:
                return problem
        wheel = root / wheel_relative
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if digest != expected_hash.lower():
            return f"Bundled wheel hash mismatch: {relative_file}"
    return None


def validate_target_path(path: Path) -> Path:
    """Reject paths whose removal or replacement could affect a broad directory."""

    target = normalized_target(path)
    anchor = Path(target.anchor)
    dangerous = (
        anchor,
        normalized_target(Path.home()),
    )
    if any(_same_path(target, candidate) for candidate in dangerous):
        raise RuntimeError(f"Refusing dangerous installation target: {target}")
    if target.name.casefold() != SKILL_NAME.casefold():
        raise RuntimeError(
            f"Installation target must end with '{SKILL_NAME}': {target}"
        )
    home = normalized_target(Path.home())
    if (
        target.parent == target
        or target.parent.parent == target.parent
        or _same_path(target.parent.parent, anchor)
        or _same_path(target.parent, home)
    ):
        raise RuntimeError(f"Installation target is too close to a filesystem root: {target}")
    reparse_component = first_reparse_component(target)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing installation target with a symlink, junction, or reparse-point "
            f"component: {reparse_component}"
        )
    return target


def read_skill_name(path: Path, skill_manifest: str = "SKILL.md") -> Optional[str]:
    skill_file = path / skill_manifest
    if not skill_file.is_file() or _is_reparse_point(skill_file):
        return None
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    declared_name: Optional[str] = None
    for line in lines[1:]:
        if line.strip() == "---":
            return declared_name
        key, separator, value = line.partition(":")
        if separator and key.strip() == "name":
            declared_name = value.strip().strip("\"'")
    return None


def read_marker(path: Path) -> Optional[dict[str, Any]]:
    marker = path / MARKER_NAME
    if not marker.is_file() or _is_reparse_point(marker):
        return None
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("skill") != SKILL_NAME:
        return None
    return value


def stored_host_contract_validation_error(
    value: object, *, validate_discovery_roots: bool = True
) -> Optional[str]:
    if not isinstance(value, dict):
        return "Dynamic host contract must be an object."
    try:
        roots = value.get("discovery_roots")
        if validate_discovery_roots and (not isinstance(roots, list) or not roots):
            return "Dynamic host safety context has no discovery roots."
        if roots is not None and not isinstance(roots, list):
            return "Dynamic host safety context has an invalid discovery root."
        if isinstance(roots, list):
            if not all(isinstance(root, str) and root.strip() for root in roots):
                return "Dynamic host safety context has an invalid discovery root."
            if validate_discovery_roots:
                for root in roots:
                    validate_discovery_root(Path(root))
    except RuntimeError as exc:
        return str(exc)
    return None


def explicit_host_contract_arguments(args: argparse.Namespace) -> bool:
    return any(
        (
            args.host is not None,
            args.scope is not None,
            bool(args.invocation),
            bool(args.reload_hint),
            bool(args.host_evidence),
            bool(args.discovery_root),
            args.replace_discovery_roots,
            bool(args.affected_host),
        )
    )


def normalized_stored_host_contract(
    value: dict[str, object], target: Path, *, include_discovery_roots: bool = True
) -> dict[str, object]:
    error = stored_host_contract_validation_error(
        value, validate_discovery_roots=include_discovery_roots
    )
    if error is not None:
        raise RuntimeError("Stored dynamic host contract is invalid: " + error)
    roots = unique_discovery_roots(
        target,
        (
            [Path(str(root)) for root in value["discovery_roots"]]
            if include_discovery_roots
            else []
        ),
    )
    def optional_text(field: str, maximum: int, default: Optional[str] = None) -> Optional[str]:
        try:
            return validated_contract_text(value.get(field), field, maximum, default=default)
        except RuntimeError:
            return default

    host = optional_text("host", 80, "current-agent") or "current-agent"
    scope = value.get("scope") if value.get("scope") in HOST_SCOPES else "custom"
    affected_hosts: list[str] = []
    raw_affected = value.get("affected_hosts")
    if isinstance(raw_affected, list):
        for raw_host in raw_affected:
            try:
                label = validated_contract_text(str(raw_host), "affected host", 80)
            except RuntimeError:
                continue
            if label and label not in affected_hosts:
                affected_hosts.append(label)
    if host not in affected_hosts:
        affected_hosts.append(host)
    return {
        "host": host,
        "scope": scope,
        "target": str(target),
        "invocation": optional_text("invocation", 160),
        "reload_hint": optional_text("reload_hint", 500),
        "host_evidence": optional_text("host_evidence", 500),
        "discovery_roots": [str(root) for root in roots],
        "affected_hosts": affected_hosts,
    }


def effective_host_contract(
    args: argparse.Namespace, target: Path
) -> dict[str, object]:
    if args.replace_discovery_roots and not args.host_evidence:
        raise RuntimeError(
            "--replace-discovery-roots requires fresh --host-evidence for the new roots."
        )
    if not target.is_dir() or managed_install_validation_error(target) is not None:
        return build_host_contract(args, target)
    marker = read_marker(target)
    stored = marker.get("host_contract") if marker is not None else None
    installer_version = marker.get("installer_version") if marker is not None else None
    if not isinstance(stored, dict):
        if isinstance(installer_version, int) and installer_version >= 4:
            raise RuntimeError("Stored dynamic host safety context is missing.")
        return build_host_contract(args, target)

    base = normalized_stored_host_contract(
        stored,
        target,
        include_discovery_roots=not args.replace_discovery_roots,
    )
    if not explicit_host_contract_arguments(args):
        return base

    host = validated_contract_text(
        args.host if args.host is not None else str(base["host"]),
        "--host",
        80,
        default="current-agent",
    )
    scope = args.scope or str(base["scope"])
    invocation = (
        validated_contract_text(args.invocation, "--invocation", 160)
        if args.invocation is not None
        else base.get("invocation")
    )
    reload_hint = (
        validated_contract_text(args.reload_hint, "--reload-hint", 500)
        if args.reload_hint is not None
        else base.get("reload_hint")
    )
    evidence = (
        validated_contract_text(args.host_evidence, "--host-evidence", 500)
        if args.host_evidence is not None
        else base.get("host_evidence")
    )
    base_roots = (
        []
        if args.replace_discovery_roots
        else [Path(str(root)) for root in base["discovery_roots"]]
    )
    roots = unique_discovery_roots(target, base_roots + list(args.discovery_root or []))
    affected_hosts = list(base["affected_hosts"])
    for raw_host in args.affected_host or []:
        label = validated_contract_text(raw_host, "--affected-host", 80)
        if label and label not in affected_hosts:
            affected_hosts.append(label)
    if host and host not in affected_hosts:
        affected_hosts.append(host)
    return {
        "host": host,
        "scope": scope,
        "target": str(target),
        "invocation": invocation,
        "reload_hint": reload_hint,
        "host_evidence": evidence,
        "discovery_roots": [str(root) for root in roots],
        "affected_hosts": affected_hosts,
    }


def required_files_for_marker(
    marker: dict[str, Any],
) -> tuple[Optional[tuple[str, ...]], Optional[str]]:
    contract = marker.get("runtime_contract")
    if contract is None:
        return COMPATIBLE_INSTALL_FILES, None
    if not isinstance(contract, int):
        return None, f"Install marker runtime_contract must be an integer: {contract!r}."
    files = RUNTIME_CONTRACT_FILES.get(contract)
    if files is None:
        return None, f"Unsupported runtime contract in install marker: {contract!r}."
    return files, None


def has_required_runtime(path: Path, skill_manifest: str = "SKILL.md") -> bool:
    for relative in COMPATIBLE_INSTALL_FILES:
        if required_file_validation_error(path, relative, skill_manifest) is not None:
            return False
    return (
        read_skill_name(path, skill_manifest) == SKILL_NAME
        and vendor_bundle_validation_error(path) is None
    )


def managed_install_validation_error(
    path: Path, skill_manifest: str = "SKILL.md"
) -> Optional[str]:
    if not path.is_dir():
        return "The target is not a directory."
    if _is_reparse_point(path):
        return "The target is a symlink, junction, or reparse point."
    marker = read_marker(path)
    if marker is None:
        return (
            f"{MARKER_NAME} is missing, invalid JSON, or does not declare "
            f"skill == {SKILL_NAME}."
        )
    required_files, contract_error = required_files_for_marker(marker)
    if contract_error is not None or required_files is None:
        return contract_error
    if read_skill_name(path, skill_manifest) != SKILL_NAME:
        return f"{skill_manifest} does not declare name: {SKILL_NAME}."
    problems = [
        problem
        for relative in required_files
        if (
            problem := required_file_validation_error(
                path, relative, skill_manifest
            )
        )
        is not None
    ]
    if problems:
        return "Required installed files are missing or unsafe: " + "; ".join(problems)
    vendor_error = vendor_bundle_validation_error(path)
    if vendor_error is not None:
        return vendor_error
    return None


def is_managed_install(path: Path, skill_manifest: str = "SKILL.md") -> bool:
    return managed_install_validation_error(path, skill_manifest) is None


def is_legacy_install(path: Path, skill_manifest: str = "SKILL.md") -> bool:
    """Recognize a pre-marker install without weakening uninstall validation."""

    return (
        path.is_dir()
        and not (path / MARKER_NAME).exists()
        and has_required_runtime(path, skill_manifest)
    )


def is_discoverable_experience_loop(path: Path) -> bool:
    return path.is_dir() and read_skill_name(path) == SKILL_NAME


def _is_within(path: Path, parent: Path) -> bool:
    try:
        normalized_target(path).relative_to(normalized_target(parent))
        return True
    except ValueError:
        return False


def backup_root_for_target(target: Path) -> Path:
    """Return the preferred transaction root outside the direct Skill scan root."""

    root = target.parent.parent / BACKUP_DIRECTORY_NAME / SKILL_NAME
    if _same_path(root, target) or _same_path(root.parent, target.parent):
        raise RuntimeError(f"Could not choose a backup directory outside: {target.parent}")
    try:
        root.relative_to(target.parent)
    except ValueError:
        pass
    else:
        raise RuntimeError(f"Backup directory must be outside the Skill scan root: {root}")
    reparse_component = first_reparse_component(root)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing backup root with a symlink, junction, or reparse-point "
            f"component: {reparse_component}"
        )
    return root


def local_transaction_root_for_target(target: Path) -> Path:
    """Return a same-volume fallback beneath a non-Skill container."""

    return (
        normalized_target(target).parent
        / LOCAL_TRANSACTION_DIRECTORY_NAME
        / SKILL_NAME
    )


def stored_transaction_root(target: Path) -> Optional[Path]:
    marker = read_marker(target)
    value = marker.get("transaction_root") if marker is not None else None
    if not isinstance(value, str) or not value.strip():
        return None
    return normalized_target(Path(value))


def _nearest_existing_directory(path: Path) -> Path:
    current = normalized_target(path)
    while not current.exists():
        parent = current.parent
        if parent == current:
            raise RuntimeError(f"No existing directory anchors transaction path: {path}")
        current = parent
    if not current.is_dir():
        raise RuntimeError(f"Transaction path crosses a non-directory entry: {current}")
    return current


def _same_volume(left: Path, right: Path) -> bool:
    left = normalized_target(left)
    right = normalized_target(right)
    if os.name == "nt" and left.anchor and right.anchor:
        return os.path.normcase(left.anchor) == os.path.normcase(right.anchor)
    left_anchor = _nearest_existing_directory(left)
    right_anchor = _nearest_existing_directory(right)
    try:
        return os.stat(left_anchor).st_dev == os.stat(right_anchor).st_dev
    except OSError as exc:
        raise RuntimeError(f"Could not compare transaction filesystems: {exc}") from exc


def validate_transaction_root(
    target: Path, root: Path, discovery_roots: list[Path]
) -> Path:
    target = validate_target_path(target)
    root = normalized_target(root)
    if _same_path(root, target) or _is_within(root, target) or _is_within(target, root):
        raise RuntimeError(f"Transaction root must be separate from the target: {root}")
    for discovery_root in discovery_roots:
        discovery_root = validate_discovery_root(discovery_root)
        if _same_path(root, discovery_root):
            raise RuntimeError(
                f"Transaction root cannot equal a Skill discovery root: {root}"
            )
        if _is_within(root, discovery_root):
            allowed = discovery_root / LOCAL_TRANSACTION_DIRECTORY_NAME / SKILL_NAME
            if not _same_path(root, allowed):
                raise RuntimeError(
                    "A transaction root inside a Skill discovery root must use the "
                    f"reserved dormant container: {allowed}"
                )
    reparse_component = first_reparse_component(root)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing transaction root with a symlink, junction, or reparse-point "
            f"component: {reparse_component}"
        )
    if root.exists() and not root.is_dir():
        raise RuntimeError(f"Transaction root is not a directory: {root}")
    if read_skill_name(root) is not None:
        raise RuntimeError(f"Transaction root must not be a discoverable Skill: {root}")
    if not _same_volume(target.parent, root):
        raise RuntimeError(
            f"Transaction root must be on the same filesystem as the target: {root}"
        )
    return root


def _create_missing_probe_directories(path: Path, created: list[Path]) -> None:
    missing: list[Path] = []
    current = normalized_target(path)
    while not current.exists():
        missing.append(current)
        parent = current.parent
        if parent == current:
            raise RuntimeError(f"Cannot create transaction path: {path}")
        current = parent
    if not current.is_dir():
        raise RuntimeError(f"Transaction path crosses a non-directory entry: {current}")
    for candidate in reversed(missing):
        try:
            candidate.mkdir()
        except FileExistsError:
            if not candidate.is_dir():
                raise RuntimeError(
                    f"Transaction path became a non-directory entry: {candidate}"
                )
        else:
            created.append(candidate)


def probe_transaction_capabilities(target: Path, root: Path) -> None:
    """Verify reversible create/write and cross-directory rename capabilities."""

    target = validate_target_path(target)
    root = normalized_target(root)
    created: list[Path] = []
    source_probe: Optional[Path] = None
    moved_probe: Optional[Path] = None
    primary_error: Optional[Exception] = None
    cleanup_errors: list[str] = []
    try:
        _create_missing_probe_directories(target.parent, created)
        _create_missing_probe_directories(root, created)
        source_probe = Path(
            tempfile.mkdtemp(
                prefix=".experience-loop-write-probe-", dir=str(target.parent)
            )
        )
        (source_probe / "probe.txt").write_text("probe\n", encoding="utf-8")
        moved_probe = root / f"{source_probe.name}-moved-{uuid4().hex[:8]}"
        source_probe.replace(moved_probe)
        source_probe = target.parent / source_probe.name
        moved_probe.replace(source_probe)
        moved_probe = None
    except Exception as exc:
        primary_error = exc
    finally:
        for candidate in (moved_probe, source_probe):
            if candidate is None or not candidate.exists():
                continue
            try:
                shutil.rmtree(candidate)
            except OSError as exc:
                cleanup_errors.append(f"could not remove probe {candidate}: {exc}")
        for candidate in sorted(
            set(created), key=lambda value: len(value.parts), reverse=True
        ):
            if not candidate.exists():
                continue
            try:
                candidate.rmdir()
            except OSError as exc:
                cleanup_errors.append(
                    f"could not remove temporary directory {candidate}: {exc}"
                )
    if primary_error is not None:
        detail = f"Transaction capability probe failed for {root}: {primary_error}"
        if cleanup_errors:
            detail += ". Cleanup also failed: " + "; ".join(cleanup_errors)
        raise RuntimeError(detail) from primary_error
    if cleanup_errors:
        raise RuntimeError(
            "Transaction capability probe left temporary state: "
            + "; ".join(cleanup_errors)
        )


def transaction_root_candidates(
    target: Path,
    requested: Optional[Path] = None,
    stored: Optional[Path] = None,
) -> list[tuple[str, Path]]:
    if requested is not None:
        return [("explicit", normalized_target(requested))]
    candidates: list[tuple[str, Path]] = []
    if stored is not None:
        candidates.append(("stored", normalized_target(stored)))
    preferred = (
        normalized_target(target).parent.parent / BACKUP_DIRECTORY_NAME / SKILL_NAME
    )
    candidates.extend(
        (
            ("outside-discovery-root", preferred),
            ("dormant-discovery-root-fallback", local_transaction_root_for_target(target)),
        )
    )
    unique: list[tuple[str, Path]] = []
    for kind, candidate in candidates:
        if not any(_same_path(candidate, existing) for _, existing in unique):
            unique.append((kind, candidate))
    return unique


def select_transaction_root(
    target: Path,
    discovery_roots: list[Path],
    requested: Optional[Path] = None,
    stored: Optional[Path] = None,
) -> tuple[Optional[Path], list[dict[str, str]]]:
    attempts: list[dict[str, str]] = []
    for kind, candidate in transaction_root_candidates(target, requested, stored):
        try:
            candidate = validate_transaction_root(target, candidate, discovery_roots)
            probe_transaction_capabilities(target, candidate)
        except Exception as exc:
            attempts.append(
                {
                    "kind": kind,
                    "path": str(candidate),
                    "status": "unavailable",
                    "error": str(exc),
                }
            )
            continue
        attempts.append(
            {
                "kind": kind,
                "path": str(candidate),
                "status": "ready",
                "error": "",
            }
        )
        return candidate, attempts
    return None, attempts


def park_skill_manifest(path: Path) -> bool:
    active = path / "SKILL.md"
    dormant = path / DORMANT_SKILL_MANIFEST
    if dormant.exists():
        raise RuntimeError(f"Dormant Skill manifest already exists: {dormant}")
    if not active.exists():
        return False
    if _is_reparse_point(active):
        raise RuntimeError(f"Refusing to park a linked Skill manifest: {active}")
    active.replace(dormant)
    return True


def activate_parked_skill_manifest(path: Path) -> bool:
    active = path / "SKILL.md"
    dormant = path / DORMANT_SKILL_MANIFEST
    if active.exists():
        if dormant.exists():
            raise RuntimeError(f"Both active and dormant Skill manifests exist: {path}")
        return False
    if not dormant.exists():
        return False
    if _is_reparse_point(dormant):
        raise RuntimeError(f"Refusing to activate a linked Skill manifest: {dormant}")
    dormant.replace(active)
    return True


def _unique_backup_path(root: Path, label: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    safe_label = "".join(
        character if character.isalnum() or character in {"-", "."} else "-"
        for character in label
    ).strip("-.")
    return root / f"{safe_label or SKILL_NAME}-{timestamp}-{uuid4().hex[:8]}"


def _move_to_backup(path: Path, backup_root: Path, label: str) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    reparse_component = first_reparse_component(backup_root)
    if reparse_component is not None:
        raise RuntimeError(
            "Refusing backup write through a symlink, junction, or reparse point: "
            f"{reparse_component}"
        )
    destination = _unique_backup_path(backup_root, label)
    path.replace(destination)
    return destination


def planned_legacy_sibling_backups(target: Path) -> list[Path]:
    """Return recognized legacy sibling backups after validating every candidate."""

    candidates: list[Path] = []
    if not target.parent.is_dir():
        return candidates
    for candidate in sorted(target.parent.glob(f"{target.name}.backup-*")):
        if _is_reparse_point(candidate):
            raise RuntimeError(
                "Refusing unsafe legacy backup symlink/junction in Skill scan root: "
                f"{candidate}"
            )
        marker_claims_skill = read_marker(candidate) is not None
        if not marker_claims_skill and not is_discoverable_experience_loop(candidate):
            continue
        candidates.append(candidate)
    return candidates


def restore_legacy_sibling_backups(migrations: list[tuple[Path, Path]]) -> None:
    for original, destination in reversed(migrations):
        if not destination.exists():
            continue
        if original.exists():
            raise RuntimeError(
                "Could not restore a migrated legacy backup because its original "
                f"path is occupied: {original}"
            )
        destination.replace(original)
        activate_parked_skill_manifest(original)


def migrate_legacy_sibling_backups(
    target: Path, transaction_root: Optional[Path] = None
) -> list[tuple[Path, Path]]:
    """Move legacy sibling backups transactionally outside the Skill scan root."""

    backup_root = transaction_root or backup_root_for_target(target)
    migrations: list[tuple[Path, Path]] = []
    try:
        for candidate in planned_legacy_sibling_backups(target):
            parked = park_skill_manifest(candidate)
            try:
                destination = _move_to_backup(
                    candidate, backup_root, f"legacy-{candidate.name}"
                )
            except Exception:
                if parked and candidate.exists():
                    activate_parked_skill_manifest(candidate)
                raise
            migrations.append((candidate, destination))
    except Exception:
        restore_legacy_sibling_backups(migrations)
        raise
    return migrations


def discoverable_installations(
    target: Path, discovery_roots: Optional[list[Path]] = None
) -> list[Path]:
    discovered: list[Path] = []
    roots = discovery_roots or [normalized_target(target).parent]
    for root in roots:
        if not root.is_dir():
            continue
        for candidate in root.iterdir():
            if _is_reparse_point(candidate):
                if candidate.name.casefold().startswith(SKILL_NAME.casefold()):
                    raise RuntimeError(
                        "Refusing a possible duplicate Experience Loop Skill through "
                        "a symlink, junction, or reparse point in a declared discovery "
                        f"root: {candidate}"
                    )
                continue
            if is_discoverable_experience_loop(candidate) and not any(
                _same_path(candidate, existing) for existing in discovered
            ):
                discovered.append(candidate)
    return discovered


def other_discoverable_installations(
    target: Path,
    discovery_roots: Optional[list[Path]] = None,
    ignored: Optional[list[Path]] = None,
) -> list[Path]:
    ignored_paths = ignored or []
    return [
        path
        for path in discoverable_installations(target, discovery_roots)
        if not _same_path(path, normalized_target(target))
        and not any(_same_path(path, candidate) for candidate in ignored_paths)
    ]


def ensure_no_other_discoverable_install(
    target: Path,
    discovery_roots: Optional[list[Path]] = None,
    ignored: Optional[list[Path]] = None,
) -> None:
    others = other_discoverable_installations(target, discovery_roots, ignored)
    if others:
        rendered = ", ".join(str(path) for path in others)
        raise RuntimeError(
            "Another discoverable experience-loop Skill remains in a scan root "
            f"declared by the installation AI: {rendered}. Move it outside that "
            "host's Skill discovery roots before continuing."
        )


def install_plan(
    target: Path,
    force: bool,
    host_contract: dict[str, object],
    requested_transaction_root: Optional[Path] = None,
) -> dict[str, object]:
    target = validate_target_path(target)
    discovery_roots = [Path(str(root)) for root in host_contract["discovery_roots"]]
    legacy_candidates = planned_legacy_sibling_backups(target)
    duplicates = other_discoverable_installations(
        target, discovery_roots, legacy_candidates
    )
    if not target.exists():
        existing_target_class = "absent"
    elif is_managed_install(target):
        existing_target_class = "managed"
    elif is_legacy_install(target):
        existing_target_class = "legacy"
    else:
        existing_target_class = "unrecognized"
    stored_root = (
        stored_transaction_root(target)
        if existing_target_class == "managed"
        else None
    )
    transaction_root, transaction_attempts = select_transaction_root(
        target,
        discovery_roots,
        requested=requested_transaction_root,
        stored=stored_root,
    )
    requires_force = existing_target_class == "unrecognized"
    blockers: list[str] = []
    if requires_force and not force:
        blockers.append(
            f"Target already exists and is not a recognized {SKILL_NAME} install: "
            f"{target}. Re-run with --force only after reviewing that directory."
        )
    if duplicates:
        rendered = ", ".join(str(path) for path in duplicates)
        blockers.append(
            "Another discoverable experience-loop Skill remains in a scan root "
            f"declared by the installation AI: {rendered}. Move it outside that "
            "host's Skill discovery roots before continuing."
        )
    if transaction_root is None:
        rendered = "; ".join(
            f"{attempt['path']}: {attempt['error']}"
            for attempt in transaction_attempts
        )
        blockers.append(
            "No safe writable same-volume transaction root is available. "
            + rendered
        )
    return {
        "existing_target_class": existing_target_class,
        "requires_force": requires_force,
        "backup_root": str(transaction_root) if transaction_root is not None else None,
        "transaction_root": (
            str(transaction_root) if transaction_root is not None else None
        ),
        "transaction_capability": (
            "verified" if transaction_root is not None else "blocked"
        ),
        "transaction_attempts": transaction_attempts,
        "will_backup_existing_target": target.exists(),
        "legacy_migrations": [str(path) for path in legacy_candidates],
        "duplicates": [str(path) for path in duplicates],
        "blockers": blockers,
    }


def copy_runtime(
    source: Path,
    staging: Path,
    host_contract: dict[str, object],
    transaction_root: Path,
    transaction_id: str,
) -> None:
    for relative in PORTABLE_SKILL_PAYLOAD_FILES:
        source_file = source.joinpath(*relative.split("/"))
        destination_relative = (
            DORMANT_SKILL_MANIFEST if relative == "SKILL.md" else relative
        )
        destination = staging.joinpath(*destination_relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)

    marker = {
        "skill": SKILL_NAME,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "installer_version": INSTALLER_VERSION,
        "runtime_contract": CURRENT_RUNTIME_CONTRACT,
        "host_contract": host_contract,
        "transaction_root": str(transaction_root),
        "transaction_id": transaction_id,
    }
    (staging / MARKER_NAME).write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _quoted_command(parts: list[str]) -> str:
    if os.name == "nt":
        quoted = ["'" + part.replace("'", "''") + "'" for part in parts]
        return "& " + " ".join(quoted)
    return shlex.join(parts)


def rollback_source_error(backup: Optional[Path]) -> Optional[str]:
    if backup is None:
        return None
    if (backup / MARKER_NAME).exists():
        return managed_install_validation_error(backup, DORMANT_SKILL_MANIFEST)
    if not is_legacy_install(backup, DORMANT_SKILL_MANIFEST):
        return (
            "The backup is not a recognized managed or legacy Experience Loop "
            "install with a complete installer."
        )
    return None


def rollback_note(backup: Optional[Path]) -> Optional[str]:
    error = rollback_source_error(backup)
    if error is None:
        return None
    return (
        f"Backup was preserved at {backup}, but no executable rollback command was "
        f"issued because the backup is not a self-contained install source: {error}"
    )


def lifecycle_manager_paths(transaction_root: Path) -> tuple[Path, Path]:
    return (
        transaction_root / LIFECYCLE_INSTALLER_NAME,
        transaction_root / LIFECYCLE_UNINSTALLER_NAME,
    )


def install_lifecycle_manager(transaction_root: Path) -> tuple[Path, Path]:
    transaction_root.mkdir(parents=True, exist_ok=True)
    installer_destination, uninstaller_destination = lifecycle_manager_paths(
        transaction_root
    )
    sources = (
        (Path(__file__).resolve(), installer_destination),
        (Path(__file__).resolve().with_name("uninstall.py"), uninstaller_destination),
    )
    for source, destination in sources:
        if not source.is_file():
            raise RuntimeError(f"Lifecycle manager source is missing: {source}")
        temporary = destination.with_name(
            f".{destination.name}.tmp-{uuid4().hex[:8]}"
        )
        try:
            shutil.copy2(source, temporary)
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
    return installer_destination, uninstaller_destination


def cleanup_empty_transaction_root(transaction_root: Path) -> None:
    if transaction_root.exists():
        try:
            transaction_root.rmdir()
        except OSError:
            return
    container = transaction_root.parent
    if container.name == LOCAL_TRANSACTION_DIRECTORY_NAME and container.exists():
        try:
            container.rmdir()
        except OSError:
            return


def contract_install_argv(
    contract: dict[str, object], target: Path
) -> list[str]:
    arguments = [
        "--host",
        str(contract["host"]),
        "--scope",
        str(contract["scope"]),
        "--target",
        str(target),
    ]
    optional_fields = (
        ("invocation", "--invocation"),
        ("reload_hint", "--reload-hint"),
        ("host_evidence", "--host-evidence"),
    )
    for field, flag in optional_fields:
        value = contract.get(field)
        if isinstance(value, str) and value:
            arguments.extend([flag, value])
    for raw_root in contract.get("discovery_roots", []):
        root = Path(str(raw_root))
        if not _same_path(root, target.parent):
            arguments.extend(["--discovery-root", str(root)])
    for affected in contract.get("affected_hosts", []):
        arguments.extend(["--affected-host", str(affected)])
    return arguments


def contract_uninstall_argv(
    contract: dict[str, object], target: Path
) -> list[str]:
    arguments = ["--host", str(contract["host"]), "--target", str(target)]
    for raw_root in contract.get("discovery_roots", []):
        root = Path(str(raw_root))
        if not _same_path(root, target.parent):
            arguments.extend(["--discovery-root", str(root)])
    for affected in contract.get("affected_hosts", []):
        arguments.extend(["--affected-host", str(affected)])
    return arguments


def lifecycle_argv(
    source: Path,
    target: Path,
    backup: Optional[Path],
    host_contract: dict[str, object],
    transaction_root: Path,
) -> dict[str, Optional[list[str]]]:
    python = str(Path(sys.executable).resolve())
    source = source.resolve()
    target = target.resolve()
    if backup is not None:
        backup = backup.resolve()
    transaction_root = transaction_root.resolve()
    manager_installer, manager_uninstaller = lifecycle_manager_paths(transaction_root)
    uninstall_script = (
        manager_uninstaller
        if manager_installer.is_file() and manager_uninstaller.is_file()
        else target / "scripts" / "uninstall.py"
    )
    commands: dict[str, Optional[list[str]]] = {
        "version": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--version",
        ],
        "mode": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "mode",
        ],
        "status": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "status",
        ],
        "setup": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "setup",
        ],
        "doctor": [
            python,
            str(target / "scripts" / "experience_loop.py"),
            "--json",
            "doctor",
        ],
        "uninstall": [
            python,
            str(uninstall_script),
            *contract_uninstall_argv(host_contract, target),
            "--yes",
        ],
        "upgrade_from_current_checkout": (
            None
            if _same_path(source, target)
            else [
                python,
                str(source / "scripts" / "install.py"),
                *contract_install_argv(host_contract, target),
            ]
        ),
        "rollback": None,
    }
    if (
        backup is not None
        and rollback_source_error(backup) is None
        and manager_installer.is_file()
    ):
        rollback_command = [
            python,
            str(manager_installer),
            "--restore-from",
            str(backup),
            "--transaction-root",
            str(transaction_root),
            "--target",
            str(target),
        ]
        commands["rollback"] = rollback_command
    return commands


def lifecycle_commands(
    source: Path,
    target: Path,
    backup: Optional[Path],
    host_contract: dict[str, object],
    transaction_root: Path,
) -> dict[str, Optional[str]]:
    return {
        name: _quoted_command(parts) if parts is not None else None
        for name, parts in lifecycle_argv(
            source, target, backup, host_contract, transaction_root
        ).items()
    }


def managed_transaction_id(
    path: Path, skill_manifest: str = "SKILL.md"
) -> Optional[str]:
    if managed_install_validation_error(path, skill_manifest) is not None:
        return None
    marker = read_marker(path)
    value = marker.get("transaction_id") if marker is not None else None
    return value if isinstance(value, str) and value else None


def persist_restored_host_contract(
    target: Path,
    host_contract: dict[str, object],
    transaction_root: Path,
) -> None:
    marker = read_marker(target)
    if marker is None:
        if not is_legacy_install(target):
            raise RuntimeError(
                "Cannot attach the current host contract to an invalid restored target."
            )
        marker = {
            "skill": SKILL_NAME,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "source": str(target),
            "transaction_id": uuid4().hex,
        }
    marker["installer_version"] = INSTALLER_VERSION
    marker["host_contract"] = host_contract
    marker["transaction_root"] = str(transaction_root)
    marker_path = target / MARKER_NAME
    temporary = marker_path.with_name(f".{MARKER_NAME}.tmp-{uuid4().hex[:8]}")
    try:
        temporary.write_text(
            json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporary.replace(marker_path)
    except Exception as exc:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError as cleanup_exc:
                raise RuntimeError(
                    f"Could not persist the restored host contract: {exc}. "
                    f"Temporary marker cleanup also failed: {cleanup_exc}"
                ) from exc
        raise
    validation_error = managed_install_validation_error(target)
    if validation_error is not None:
        raise RuntimeError(
            "Restored target failed validation after host-contract persistence: "
            + validation_error
        )


def restore_backup(
    target: Path,
    backup: Path,
    host_contract: dict[str, object],
    transaction_root: Path,
) -> dict[str, object]:
    target = validate_target_path(target)
    transaction_root = validate_transaction_root(
        target,
        transaction_root,
        [Path(str(root)) for root in host_contract["discovery_roots"]],
    )
    probe_transaction_capabilities(target, transaction_root)
    backup = normalized_target(backup)
    if not _same_path(backup.parent, transaction_root):
        raise RuntimeError(
            "Rollback source must be a direct child of the selected transaction root: "
            f"{backup}"
        )
    backup_error = rollback_source_error(backup)
    if backup_error is not None:
        raise RuntimeError(f"Rollback source is invalid: {backup_error}")
    if not is_managed_install(target):
        raise RuntimeError(
            "Rollback requires a complete currently managed Experience Loop target."
        )

    discovery_roots = [Path(str(root)) for root in host_contract["discovery_roots"]]
    ensure_no_other_discoverable_install(target, discovery_roots)
    install_lifecycle_manager(transaction_root)
    current_backup: Optional[Path] = None
    current_manifest_parked = False
    restored_moved = False
    restored_activated = False
    try:
        current_manifest_parked = park_skill_manifest(target)
        current_backup = _move_to_backup(
            target, transaction_root, "pre-rollback-current"
        )
        backup.replace(target)
        restored_moved = True
        restored_activated = activate_parked_skill_manifest(target)
        if not (is_managed_install(target) or is_legacy_install(target)):
            raise RuntimeError("Restored Skill failed managed or legacy validation.")
        persist_restored_host_contract(target, host_contract, transaction_root)
        discovered = discoverable_installations(target, discovery_roots)
        if len(discovered) != 1 or not _same_path(discovered[0], target):
            raise RuntimeError(
                "Rollback did not leave exactly one discoverable Experience Loop Skill."
            )
    except Exception as exc:
        recovery_errors: list[str] = []
        try:
            if restored_moved and target.exists():
                if restored_activated:
                    park_skill_manifest(target)
                target.replace(backup)
            if (
                current_backup is not None
                and current_backup.exists()
                and not target.exists()
            ):
                current_backup.replace(target)
                if current_manifest_parked:
                    activate_parked_skill_manifest(target)
            elif current_manifest_parked and target.exists():
                activate_parked_skill_manifest(target)
            if target.exists():
                restored_error = managed_install_validation_error(target)
                if restored_error is not None:
                    raise RuntimeError(
                        "Recovered current target failed validation: " + restored_error
                    )
        except Exception as recovery_exc:
            recovery_errors.append(f"rollback recovery failed: {recovery_exc}")
        if recovery_errors:
            raise RuntimeError(
                f"Rollback failed: {exc}. Recovery also failed: "
                + "; ".join(recovery_errors)
            ) from exc
        raise

    return {
        "status": "rolled-back",
        "version": read_version(target),
        "source": str(target),
        "source_provenance": source_provenance(target),
        "target": str(target),
        "backup": str(current_backup) if current_backup else None,
        "backup_root": str(transaction_root),
        "transaction_root": str(transaction_root),
        "transaction_capability": "verified",
        "migrated_legacy_backups": [],
        **host_receipt(host_contract),
        "commands": lifecycle_commands(
            target, target, current_backup, host_contract, transaction_root
        ),
        "command_argv": lifecycle_argv(
            target, target, current_backup, host_contract, transaction_root
        ),
        "command_shell": "powershell" if os.name == "nt" else "posix",
        **completed_install_protocol(
            target,
            target,
            read_version(target),
            host_contract,
            "managed-install-rollback-validated",
            "required-from-installed-copy",
        ),
        "rollback_available": (
            current_backup is not None
            and rollback_source_error(current_backup) is None
        ),
        "rollback_note": rollback_note(current_backup),
    }


def install(
    source: Path,
    target: Path,
    force: bool,
    host_contract: dict[str, object],
    requested_transaction_root: Optional[Path] = None,
) -> dict[str, object]:
    source = source.resolve()
    target = validate_target_path(target)
    if _same_path(source, target):
        if not is_managed_install(target):
            raise RuntimeError(
                "The active Skill directory is incomplete or is missing a valid install marker."
            )
    plan = install_plan(
        target,
        force,
        host_contract,
        requested_transaction_root=requested_transaction_root,
    )
    blockers = plan["blockers"]
    if isinstance(blockers, list) and blockers:
        raise RuntimeError(" ".join(str(blocker) for blocker in blockers))
    transaction_root_value = plan.get("transaction_root")
    if not isinstance(transaction_root_value, str) or not transaction_root_value:
        raise RuntimeError("The installation plan has no usable transaction root.")
    transaction_root = Path(transaction_root_value)
    if _same_path(source, target):
        return {
            "status": "already-active",
            "version": read_version(source),
            "source": str(source),
            "source_provenance": source_provenance(source),
            "target": str(target),
            "backup": None,
            "backup_root": str(transaction_root),
            "transaction_root": str(transaction_root),
            "transaction_capability": "verified",
            "migrated_legacy_backups": [],
            **host_receipt(host_contract),
            "commands": lifecycle_commands(
                source, target, None, host_contract, transaction_root
            ),
            "command_argv": lifecycle_argv(
                source, target, None, host_contract, transaction_root
            ),
            "command_shell": "powershell" if os.name == "nt" else "posix",
            **completed_install_protocol(
                target,
                target,
                read_version(source),
                host_contract,
                "managed-install-validated",
                "required-from-installed-copy",
            ),
            "rollback_available": False,
            "rollback_note": None,
        }

    discovery_roots = [Path(str(root)) for root in host_contract["discovery_roots"]]
    target.parent.mkdir(parents=True, exist_ok=True)
    transaction_root.mkdir(parents=True, exist_ok=True)
    transaction_root = validate_transaction_root(
        target, transaction_root, discovery_roots
    )
    transaction_id = uuid4().hex
    staging = Path(
        tempfile.mkdtemp(prefix=f".install-{transaction_id[:8]}-", dir=str(transaction_root))
    )
    backup: Optional[Path] = None
    migrated: list[tuple[Path, Path]] = []
    target_manifest_parked = False
    staging_moved = False
    activated = False
    try:
        copy_runtime(
            source,
            staging,
            host_contract,
            transaction_root,
            transaction_id,
        )
        if not is_managed_install(staging, DORMANT_SKILL_MANIFEST):
            raise RuntimeError("Staged Skill failed managed-install validation.")

        refreshed_plan = install_plan(
            target,
            force,
            host_contract,
            requested_transaction_root=transaction_root,
        )
        refreshed_blockers = refreshed_plan["blockers"]
        if isinstance(refreshed_blockers, list) and refreshed_blockers:
            raise RuntimeError(" ".join(str(blocker) for blocker in refreshed_blockers))
        install_lifecycle_manager(transaction_root)
        migrated = migrate_legacy_sibling_backups(target, transaction_root)
        ensure_no_other_discoverable_install(target, discovery_roots)
        if target.exists():
            target_manifest_parked = park_skill_manifest(target)
            try:
                backup = _move_to_backup(target, transaction_root, SKILL_NAME)
            except Exception:
                if target_manifest_parked and target.exists():
                    activate_parked_skill_manifest(target)
                    target_manifest_parked = False
                raise
        staging.replace(target)
        staging_moved = True
        activated = activate_parked_skill_manifest(target)
        if managed_transaction_id(target) != transaction_id:
            raise RuntimeError("Activated Skill does not belong to this transaction.")
        discovered = discoverable_installations(target, discovery_roots)
        if len(discovered) != 1 or not _same_path(discovered[0], target):
            raise RuntimeError(
                "Installation did not leave exactly one discoverable Experience Loop Skill."
            )
    except Exception as exc:
        recovery_errors: list[str] = []
        try:
            if staging_moved and target.exists():
                installed_transaction = managed_transaction_id(
                    target,
                    "SKILL.md" if activated else DORMANT_SKILL_MANIFEST,
                )
                if installed_transaction != transaction_id:
                    raise RuntimeError(
                        "Refusing to remove a target not created by this transaction."
                    )
                shutil.rmtree(target)
            elif target_manifest_parked and target.exists() and backup is None:
                activate_parked_skill_manifest(target)
            if not target.exists() and backup is not None and backup.exists():
                backup.replace(target)
                activate_parked_skill_manifest(target)
        except Exception as recovery_exc:
            recovery_errors.append(f"target restore failed: {recovery_exc}")
        try:
            restore_legacy_sibling_backups(migrated)
        except Exception as recovery_exc:
            recovery_errors.append(f"legacy-backup restore failed: {recovery_exc}")
        if staging.exists():
            try:
                shutil.rmtree(staging)
            except OSError as recovery_exc:
                recovery_errors.append(f"staging cleanup failed: {recovery_exc}")
        if recovery_errors:
            raise RuntimeError(
                f"Installation failed: {exc}. Recovery also failed: "
                + "; ".join(recovery_errors)
            ) from exc
        raise
    else:
        if staging.exists():
            try:
                shutil.rmtree(staging)
            except OSError as cleanup_exc:
                raise RuntimeError(
                    f"Could not remove staging directory: {cleanup_exc}"
                ) from cleanup_exc

    cleanup_warnings: list[str] = []
    if backup is None and not migrated:
        manager_installer, manager_uninstaller = lifecycle_manager_paths(
            transaction_root
        )
        for manager in (manager_installer, manager_uninstaller):
            if manager.exists():
                try:
                    manager.unlink()
                except OSError as cleanup_exc:
                    cleanup_warnings.append(
                        f"Installed Skill is active, but lifecycle cleanup failed for "
                        f"{manager}: {cleanup_exc}"
                    )
        cleanup_empty_transaction_root(transaction_root)

    return {
        "status": "installed",
        "version": read_version(source),
        "source": str(source),
        "source_provenance": source_provenance(source),
        "target": str(target),
        "backup": str(backup) if backup else None,
        "backup_root": str(transaction_root),
        "transaction_root": str(transaction_root),
        "transaction_capability": "verified",
        "warnings": cleanup_warnings,
        "migrated_legacy_backups": [
            str(destination) for _, destination in migrated
        ],
        **host_receipt(host_contract),
        "commands": lifecycle_commands(
            source, target, backup, host_contract, transaction_root
        ),
        "command_argv": lifecycle_argv(
            source, target, backup, host_contract, transaction_root
        ),
        "command_shell": "powershell" if os.name == "nt" else "posix",
        **completed_install_protocol(
            target,
            target,
            read_version(source),
            host_contract,
            "managed-install-validated",
            "required-from-installed-copy",
        ),
        "rollback_available": rollback_source_error(backup) is None
        and backup is not None,
        "rollback_note": rollback_note(backup),
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    args = parse_args()
    if sys.version_info < (3, 9):
        message = "Experience Loop requires Python 3.9 or newer."
        if args.json:
            print(json.dumps({"status": "error", "error": message}, ensure_ascii=False))
        else:
            print("安装失败 / Installation failed: " + message, file=sys.stderr)
        return 4
    source = repo_root()
    plugin_context = openai_plugin_context(source)
    if plugin_context is not None and not args.verify_only:
        result = plugin_manager_required_receipt(source, "install-or-update")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("Experience Loop: host-manager-required")
            print("OpenAI Plugin lifecycle is owned by the Codex Plugin manager.")
            print(result["next_action"]["message"])
        return 3
    exit_code = 0
    try:
        target = validate_target_path(args.target)
        host_contract = effective_host_contract(args, target)
        if args.verify_only:
            if args.restore_from is not None or args.dry_run or args.force:
                raise RuntimeError(
                    "--verify-only cannot be combined with --restore-from, --dry-run, or --force."
                )
            validate_source(source)
            validate_host_managed_distribution(source)
            if not _same_path(source, target):
                raise RuntimeError(
                    "--verify-only must run from the exact host-managed target copy."
                )
            ensure_no_other_discoverable_install(
                target,
                [Path(str(root)) for root in host_contract["discovery_roots"]],
            )
            result = {
                "status": "host-managed-copy-validated",
                "version": read_version(source),
                "source": str(source),
                "source_provenance": source_provenance(source),
                "target": str(target),
                "install_manager": (
                    "codex-plugin-manager" if plugin_context else "host-native"
                ),
                **host_receipt(host_contract),
                **completed_install_protocol(
                    target,
                    target,
                    read_version(source),
                    host_contract,
                    "complete-host-managed-copy-validated",
                    "required-from-installed-copy",
                ),
                "lifecycle_owner": (
                    "codex-plugin-manager"
                    if plugin_context
                    else "current-host-native-install-manager"
                ),
            }
            if plugin_context:
                result["distribution"] = plugin_context
                result["plugin_lifecycle"] = {
                    "registration_status": "unknown",
                    "enabled_status": "unknown",
                    "hook_trust_status": "unknown",
                    "hook_observation_status": "unknown",
                    "host_discovery_status": "unknown",
                    "current_turn_activation_status": "unknown",
                    "session_requirement": "start-a-new-task-after-install-or-update",
                }
        elif args.restore_from is not None:
            if args.dry_run:
                raise RuntimeError("--restore-from cannot be combined with --dry-run.")
            transaction_root = args.transaction_root or args.restore_from.parent
            result = restore_backup(
                target,
                args.restore_from,
                host_contract,
                transaction_root,
            )
        else:
            validate_source(source)
        if not args.verify_only and args.restore_from is None and args.dry_run:
            plan = install_plan(
                target,
                args.force,
                host_contract,
                requested_transaction_root=args.transaction_root,
            )
            blocked = bool(plan["blockers"])
            result: dict[str, object] = {
                "status": "blocked" if blocked else "dry-run",
                "version": read_version(source),
                "source": str(source),
                "source_provenance": source_provenance(source),
                "target": str(target),
                "backup_root": plan["backup_root"],
                "transaction_root": plan["transaction_root"],
                "transaction_capability": plan["transaction_capability"],
                "install_plan": plan,
                **host_receipt(host_contract),
                **preview_install_protocol(
                    source,
                    target,
                    read_version(source),
                    host_contract,
                    blocked=blocked,
                ),
            }
            if blocked:
                exit_code = 4
        elif not args.verify_only and args.restore_from is None:
            result = install(
                source,
                target,
                args.force,
                host_contract,
                requested_transaction_root=args.transaction_root,
            )
    except Exception as exc:  # User-facing CLI boundary.
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"安装失败 / Installation failed: {exc}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Experience Loop: {result['status']}")
        print(f"Agent host / 宿主: {result['host']}")
        print(f"Skill 目标目录 / Skill target directory: {result['target']}")
        if result.get("backup"):
            print(f"上一版本备份 / Previous version backup: {result['backup']}")
        commands = result.get("commands")
        if isinstance(commands, dict):
            print("已安装命令 / Installed commands:")
            print(f"  version: {commands['version']}")
            print(f"  mode: {commands['mode']}")
            print(f"  status: {commands['status']}")
            print(f"  setup: {commands['setup']}")
            print(f"  doctor: {commands['doctor']}")
            print(f"  uninstall: {commands['uninstall']}")
            if commands.get("upgrade_from_current_checkout"):
                print(
                    "  upgrade (this checkout must still exist; otherwise re-download it): "
                    f"{commands['upgrade_from_current_checkout']}"
                )
            else:
                print("  upgrade: re-download the repository and run its installer")
            if commands.get("rollback"):
                print(f"  rollback: {commands['rollback']}")
            elif result.get("rollback_note"):
                print(f"  rollback unavailable: {result['rollback_note']}")
        warnings = result.get("warnings")
        if isinstance(warnings, list) and warnings:
            print("警告 / Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        if result["status"] == "blocked":
            print("预演被阻止 / Preview blocked:")
            for blocker in result["install_plan"]["blockers"]:
                print(f"  - {blocker}")
        elif result["status"] == "dry-run":
            print(
                "下一步 / Next: review the target above, then run the installer "
                "again without --dry-run."
            )
        else:
            print(f"宿主发现 / Host discovery: {result['discovery_status']}")
            print(f"验证提示 / Verify: {result['host_verification_hint']}")
            print(f"重载提示 / Reload: {result['reload_hint']}")
            print("下一步 / Next: after host discovery is verified, send:")
            print(f"  {result['onboarding_prompt']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
