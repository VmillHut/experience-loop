#!/usr/bin/env python3
"""Build a validation-ready OpenAI Plugin from the canonical Skill source."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Optional
from uuid import uuid4

import install


ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "experience-loop"
STANDALONE_SKILL_SELECTOR = "$experience-loop"
OPENAI_PLUGIN_SKILL_SELECTOR = "$experience-loop:experience-loop"
VERSION_PLACEHOLDER = "${VERSION}"
DEFAULT_PACKAGING_ROOT = ROOT / "packaging" / "openai"
DEFAULT_OUTPUT = ROOT / "dist" / PLUGIN_NAME
DEFAULT_MARKETPLACE_ROOT = ROOT / "dist" / "openai-marketplace"
DEFAULT_MARKETPLACE_NAME = "experience-loop-local"
OWNERSHIP_MARKER_NAME = ".experience-loop-plugin-build.json"
OWNERSHIP_MARKER_SCHEMA = 1
OWNERSHIP_MARKER_MANAGER = "experience-loop/scripts/build_plugin.py"
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\."
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
CACHEBUSTER_PATTERN = re.compile(r"^[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*$")
MARKETPLACE_NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")

# This exact list is the release boundary. New runtime files must be reviewed and
# added deliberately instead of being swept into the Plugin by a recursive copy.
SKILL_PAYLOAD_FILES = install.PORTABLE_SKILL_PAYLOAD_FILES
FORBIDDEN_PARTS = {"__pycache__", ".git"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}


class PluginBuildError(RuntimeError):
    """Raised when the Plugin cannot be built without weakening the contract."""


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(callable(is_junction) and is_junction())


def _checked_relative_path(raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise PluginBuildError(f"{label} must be a non-empty relative path.")
    if "\\" in raw:
        raise PluginBuildError(f"{label} must use forward slashes.")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise PluginBuildError(f"{label} must stay inside its declared source root.")
    if any(part in FORBIDDEN_PARTS for part in pure.parts):
        raise PluginBuildError(f"{label} contains a forbidden cache or metadata directory.")
    if pure.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise PluginBuildError(f"{label} contains a forbidden bytecode file.")
    return Path(*pure.parts)


def _checked_source_file(root: Path, relative: Path, label: str) -> Path:
    root = root.resolve()
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if _is_link_or_junction(cursor):
            raise PluginBuildError(f"{label} must not traverse a symlink or junction: {cursor}")
    try:
        resolved = cursor.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PluginBuildError(f"{label} is missing or unreadable: {cursor}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PluginBuildError(f"{label} escapes its declared source root: {cursor}") from exc
    if not resolved.is_file():
        raise PluginBuildError(f"{label} is not a regular file: {cursor}")
    return resolved


def _copy_file(source_root: Path, relative: Path, destination_root: Path, label: str) -> None:
    source = _checked_source_file(source_root, relative, label)
    destination = destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _rewrite_plugin_skill_metadata(skill_root: Path) -> None:
    """Namespace only the generated Plugin copy's explicit Skill selector."""
    metadata_path = skill_root / "agents" / "openai.yaml"
    metadata = metadata_path.read_text(encoding="utf-8")
    if "allow_implicit_invocation: false" not in metadata:
        raise PluginBuildError(
            "Canonical agents/openai.yaml must keep implicit invocation disabled."
        )
    default_prompt_indexes = [
        index
        for index, line in enumerate(metadata.splitlines(keepends=True))
        if line.lstrip().startswith("default_prompt:")
    ]
    if len(default_prompt_indexes) != 1:
        raise PluginBuildError(
            "Canonical agents/openai.yaml must contain exactly one default_prompt."
        )
    lines = metadata.splitlines(keepends=True)
    prompt_index = default_prompt_indexes[0]
    prompt_line = lines[prompt_index]
    if (
        OPENAI_PLUGIN_SKILL_SELECTOR in prompt_line
        or prompt_line.count(STANDALONE_SKILL_SELECTOR) != 1
    ):
        raise PluginBuildError(
            "Canonical agents/openai.yaml default_prompt must invoke the standalone "
            f"selector {STANDALONE_SKILL_SELECTOR!r} exactly once."
        )
    lines[prompt_index] = prompt_line.replace(
        STANDALONE_SKILL_SELECTOR,
        OPENAI_PLUGIN_SKILL_SELECTOR,
        1,
    )
    metadata_path.write_text("".join(lines), encoding="utf-8")


def _read_version(source_root: Path) -> str:
    version_path = _checked_source_file(source_root, Path("VERSION"), "VERSION")
    version = version_path.read_text(encoding="utf-8").strip()
    if SEMVER_PATTERN.fullmatch(version) is None:
        raise PluginBuildError(f"VERSION is not valid SemVer: {version!r}")
    return version


def _cachebusted_version(base_version: str, cachebuster: str) -> str:
    token = str(cachebuster or "").strip()
    if CACHEBUSTER_PATTERN.fullmatch(token) is None:
        raise PluginBuildError(
            "Cachebuster must contain only SemVer build identifier characters."
        )
    base = base_version.split("+", 1)[0]
    version = f"{base}+codex.{token}"
    if SEMVER_PATTERN.fullmatch(version) is None:
        raise PluginBuildError(f"Cachebusted Plugin version is invalid: {version!r}")
    return version


def _default_cachebuster() -> str:
    return datetime.now(timezone.utc).strftime("local-%Y%m%d-%H%M%S")


def _validated_marketplace_name(value: str) -> str:
    name = str(value or "").strip()
    if MARKETPLACE_NAME_PATTERN.fullmatch(name) is None:
        raise PluginBuildError(
            "Marketplace name must be lower-case hyphen-case and at most 64 characters."
        )
    return name


def _render_manifest(packaging_root: Path, version: str) -> dict[str, Any]:
    template_path = _checked_source_file(
        packaging_root,
        Path("plugin.json"),
        "OpenAI Plugin manifest template",
    )
    try:
        manifest = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginBuildError(f"OpenAI Plugin manifest template is invalid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PluginBuildError("OpenAI Plugin manifest template must contain a JSON object.")
    if manifest.get("name") != PLUGIN_NAME:
        raise PluginBuildError(f"Plugin manifest name must be {PLUGIN_NAME!r}.")
    if manifest.get("version") != VERSION_PLACEHOLDER:
        raise PluginBuildError(
            f"Plugin manifest version must remain the {VERSION_PLACEHOLDER!r} placeholder."
        )
    skills_path = manifest.get("skills")
    normalized_skills = (
        Path(skills_path).as_posix().rstrip("/")
        if isinstance(skills_path, str) and not Path(skills_path).is_absolute()
        else None
    )
    if normalized_skills != "skills":
        raise PluginBuildError("Plugin manifest skills path must resolve to 'skills'.")
    manifest["version"] = version
    return manifest


def _load_hook_files(packaging_root: Path) -> list[Path]:
    hooks_root = packaging_root / "hooks"
    if not hooks_root.exists():
        return []
    if _is_link_or_junction(hooks_root) or not hooks_root.is_dir():
        raise PluginBuildError("packaging/openai/hooks must be a regular directory.")
    manifest_path = _checked_source_file(
        hooks_root,
        Path("files.json"),
        "OpenAI Plugin hooks file list",
    )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginBuildError(f"OpenAI Plugin hooks file list is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PluginBuildError("OpenAI Plugin hooks file list must contain a JSON object.")
    unknown = sorted(set(payload) - {"schema_version", "files"})
    if unknown:
        raise PluginBuildError(
            "OpenAI Plugin hooks file list has unsupported field(s): " + ", ".join(unknown)
        )
    if payload.get("schema_version") != 1:
        raise PluginBuildError("OpenAI Plugin hooks file list schema_version must be 1.")
    raw_files = payload.get("files")
    if not isinstance(raw_files, list):
        raise PluginBuildError("OpenAI Plugin hooks file list files must be an array.")
    files: list[Path] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_files):
        relative = _checked_relative_path(raw, f"hooks.files[{index}]")
        normalized = relative.as_posix()
        if normalized == "files.json":
            raise PluginBuildError("hooks/files.json is packaging metadata and cannot be shipped.")
        if normalized in seen:
            raise PluginBuildError(f"Duplicate Hook file declaration: {normalized}")
        _checked_source_file(hooks_root, relative, f"Hook file {normalized}")
        seen.add(normalized)
        files.append(relative)
    return files


def _validate_staging_tree(staging: Path) -> tuple[int, int]:
    file_count = 0
    byte_count = 0
    for path in staging.rglob("*"):
        relative = path.relative_to(staging)
        if _is_link_or_junction(path):
            raise PluginBuildError(f"Generated Plugin contains a link or junction: {relative}")
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            raise PluginBuildError(f"Generated Plugin contains a forbidden directory: {relative}")
        if path.is_file():
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise PluginBuildError(f"Generated Plugin contains bytecode: {relative}")
            file_count += 1
            byte_count += path.stat().st_size
    return file_count, byte_count


def _run_validator(validator: Path, staging: Path) -> str:
    try:
        resolved = validator.expanduser().resolve(strict=True)
    except OSError as exc:
        raise PluginBuildError(f"Plugin validator is missing or unreadable: {validator}") from exc
    if _is_link_or_junction(resolved) or not resolved.is_file():
        raise PluginBuildError(f"Plugin validator must be a regular file: {validator}")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", str(resolved), str(staging)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env=environment,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0:
        detail = output or f"validator exited with code {completed.returncode}"
        raise PluginBuildError("Plugin validation failed before activation: " + detail)
    return output


def _validated_output_path(source_root: Path, output: Path) -> Path:
    source_root = source_root.resolve()
    output = output.expanduser().resolve(strict=False)
    if output.name != PLUGIN_NAME:
        raise PluginBuildError(f"Plugin output directory name must be {PLUGIN_NAME!r}.")
    if output == source_root:
        raise PluginBuildError("Plugin output cannot replace the source repository.")
    try:
        relative = output.relative_to(source_root)
    except ValueError:
        relative = None
    if relative is not None and (not relative.parts or relative.parts[0] != "dist"):
        raise PluginBuildError("Plugin output inside the repository must stay under dist/.")
    if output.exists() and (_is_link_or_junction(output) or not output.is_dir()):
        raise PluginBuildError("Existing Plugin output must be a regular directory.")
    return output


def _ownership_marker_payload(version: str) -> dict[str, Any]:
    return {
        "schema_version": OWNERSHIP_MARKER_SCHEMA,
        "managed_by": OWNERSHIP_MARKER_MANAGER,
        "plugin_name": PLUGIN_NAME,
        "version": version,
    }


def _ownership_marker_path(output: Path) -> Path:
    return output.parent / OWNERSHIP_MARKER_NAME


def _has_valid_ownership_marker(output: Path) -> bool:
    markers = (_ownership_marker_path(output), output / OWNERSHIP_MARKER_NAME)
    marker = next(
        (
            candidate
            for candidate in markers
            if not _is_link_or_junction(candidate) and candidate.is_file()
        ),
        None,
    )
    if marker is None:
        return False
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return (
        payload.get("schema_version") == OWNERSHIP_MARKER_SCHEMA
        and payload.get("managed_by") == OWNERSHIP_MARKER_MANAGER
        and payload.get("plugin_name") == PLUGIN_NAME
        and isinstance(payload.get("version"), str)
        and SEMVER_PATTERN.fullmatch(payload["version"]) is not None
    )


def _write_ownership_marker(output: Path, version: str) -> None:
    marker = _ownership_marker_path(output)
    temporary = marker.with_name(f"{marker.name}.tmp-{uuid4().hex}")
    try:
        temporary.write_text(
            json.dumps(
                _ownership_marker_payload(version),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(marker)
    finally:
        if temporary.exists():
            temporary.unlink()


def _authorize_output_replacement(output: Path, *, force: bool) -> None:
    if not output.exists() or _has_valid_ownership_marker(output) or force:
        return
    raise PluginBuildError(
        f"Refusing to replace unowned Plugin output at {output}. The directory does not "
        f"have a valid adjacent {OWNERSHIP_MARKER_NAME} marker. Review it and pass --force "
        "only if replacing the entire directory is intended."
    )


def _atomic_replace(staging: Path, output: Path, *, force: bool) -> None:
    backup: Optional[Path] = None
    # Re-check immediately before activation. An unrelated directory may have
    # appeared after staging started, and it must not be silently displaced.
    _authorize_output_replacement(output, force=force)
    if output.exists():
        backup = output.parent / f".{output.name}.backup-{uuid4().hex}"
        output.replace(backup)
    try:
        staging.replace(output)
    except OSError as exc:
        if backup is not None and backup.exists():
            try:
                backup.replace(output)
            except OSError as restore_exc:
                raise PluginBuildError(
                    "Plugin activation failed and the previous output could not be restored; "
                    f"backup remains at {backup}: {restore_exc}"
                ) from exc
        raise PluginBuildError(f"Plugin activation failed; previous output was preserved: {exc}") from exc
    if backup is not None:
        try:
            shutil.rmtree(backup)
        except OSError as exc:
            raise PluginBuildError(
                f"Plugin was activated, but the previous output remains at {backup}: {exc}"
            ) from exc


def build_plugin(
    *,
    source_root: Path,
    packaging_root: Path,
    output: Path,
    validator: Optional[Path] = None,
    force: bool = False,
    version_override: Optional[str] = None,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve(strict=True)
    packaging_root = packaging_root.expanduser().resolve(strict=True)
    output = _validated_output_path(source_root, output)
    _authorize_output_replacement(output, force=force)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{PLUGIN_NAME}.build-", dir=str(output.parent))
    )
    try:
        base_version = _read_version(source_root)
        version = version_override or base_version
        if SEMVER_PATTERN.fullmatch(version) is None:
            raise PluginBuildError(f"Plugin version is not valid SemVer: {version!r}")
        skill_root = staging / "skills" / PLUGIN_NAME
        for raw_relative in SKILL_PAYLOAD_FILES:
            relative = _checked_relative_path(raw_relative, "Skill payload file")
            _copy_file(source_root, relative, skill_root, f"Skill payload file {raw_relative}")
        _rewrite_plugin_skill_metadata(skill_root)

        manifest = _render_manifest(packaging_root, version)
        manifest_path = staging / ".codex-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        hook_files = _load_hook_files(packaging_root)
        hooks_source = packaging_root / "hooks"
        hooks_destination = staging / "hooks"
        for relative in hook_files:
            _copy_file(
                hooks_source,
                relative,
                hooks_destination,
                f"Hook file {relative.as_posix()}",
            )

        file_count, byte_count = _validate_staging_tree(staging)
        validator_output = _run_validator(validator, staging) if validator else None
        _atomic_replace(staging, output, force=force)
        _write_ownership_marker(output, version)
        result = {
            "status": "built",
            "output": str(output),
            "version": version,
            "base_version": base_version,
            "files": file_count,
            "bytes": byte_count,
            "hook_files": [path.as_posix() for path in hook_files],
            "validator_ran": validator is not None,
            "validator_output": validator_output,
        }
    except Exception as exc:
        if staging.exists():
            try:
                shutil.rmtree(staging)
            except OSError as cleanup_exc:
                raise PluginBuildError(
                    f"Plugin build failed ({exc}); temporary staging cleanup also failed at "
                    f"{staging}: {cleanup_exc}"
                ) from exc
        raise
    if staging.exists():
        try:
            shutil.rmtree(staging)
        except OSError as exc:
            raise PluginBuildError(
                f"Plugin build completed but temporary staging cleanup failed at {staging}: {exc}"
            ) from exc
    return result


def _read_marketplace(path: Path, marketplace_name: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "name": marketplace_name,
            "interface": {"displayName": "Experience Loop Local"},
            "plugins": [],
        }
    if _is_link_or_junction(path) or not path.is_file():
        raise PluginBuildError("Marketplace manifest must be a regular file.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PluginBuildError(f"Marketplace manifest is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PluginBuildError("Marketplace manifest must contain a JSON object.")
    if payload.get("name") != marketplace_name:
        raise PluginBuildError(
            "Existing marketplace name does not match --marketplace-name."
        )
    plugins = payload.get("plugins")
    if not isinstance(plugins, list):
        raise PluginBuildError("Marketplace plugins must be an array.")
    return payload


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid4().hex}")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_marketplace(
    *,
    source_root: Path,
    packaging_root: Path,
    marketplace_root: Path,
    marketplace_name: str = DEFAULT_MARKETPLACE_NAME,
    cachebuster: Optional[str] = None,
    validator: Optional[Path] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Build a local Marketplace without registering it or touching host cache."""

    source_root = source_root.expanduser().resolve(strict=True)
    marketplace_root = marketplace_root.expanduser().resolve(strict=False)
    if marketplace_root.exists() and (
        _is_link_or_junction(marketplace_root) or not marketplace_root.is_dir()
    ):
        raise PluginBuildError("Marketplace root must be a regular directory.")
    marketplace_name = _validated_marketplace_name(marketplace_name)
    token = cachebuster or _default_cachebuster()
    base_version = _read_version(source_root)
    version = _cachebusted_version(base_version, token)
    plugin_output = marketplace_root / "plugins" / PLUGIN_NAME
    manifest_path = marketplace_root / "marketplace.json"
    marketplace = _read_marketplace(manifest_path, marketplace_name)
    interface = marketplace.get("interface")
    if interface is None:
        marketplace["interface"] = {"displayName": "Experience Loop Local"}
    elif not isinstance(interface, dict):
        raise PluginBuildError("Marketplace interface must be an object when present.")

    plugin = build_plugin(
        source_root=source_root,
        packaging_root=packaging_root,
        output=plugin_output,
        validator=validator,
        force=force,
        version_override=version,
    )

    entry = {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        },
        "category": "Productivity",
    }
    plugins = marketplace["plugins"]
    assert isinstance(plugins, list)
    replaced = False
    updated_plugins = []
    for existing in plugins:
        if isinstance(existing, dict) and existing.get("name") == PLUGIN_NAME:
            if not replaced:
                updated_plugins.append(entry)
                replaced = True
            continue
        updated_plugins.append(existing)
    if not replaced:
        updated_plugins.append(entry)
    marketplace["plugins"] = updated_plugins
    _write_json_atomic(manifest_path, marketplace)

    return {
        "status": "marketplace-built",
        "marketplace_root": str(marketplace_root),
        "marketplace_manifest": str(manifest_path),
        "marketplace_name": marketplace_name,
        "plugin": plugin,
        "base_version": base_version,
        "version": version,
        "host_state": {
            "marketplace_registered": "unknown",
            "plugin_registered": "unknown",
            "plugin_enabled": "unknown",
            "hook_trusted": "unknown",
            "fresh_task_started": "unknown",
            "skill_available": "unknown",
            "hook_observed": "unknown",
            "current_turn_activation": "unknown",
        },
        "next_actions": [
            {
                "kind": "register-local-marketplace-if-needed",
                "command_argv": [
                    "codex",
                    "plugin",
                    "marketplace",
                    "add",
                    str(marketplace_root),
                    "--json",
                ],
            },
            {
                "kind": "install-or-update-plugin",
                "command_argv": [
                    "codex",
                    "plugin",
                    "add",
                    f"{PLUGIN_NAME}@{marketplace_name}",
                    "--json",
                ],
            },
            {
                "kind": "verify-host-registration",
                "command_argv": ["codex", "plugin", "list", "--json"],
            },
            {
                "kind": "review-hook-trust",
                "message": "Review and trust the current Hook definition in the host UI.",
            },
            {
                "kind": "start-fresh-task",
                "message": "Start a new Codex task before validating Skill availability.",
            },
        ],
        "cache_policy": "never-copy-or-delete-host-plugin-cache-directly",
    }


def _force_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _force_utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Plugin output directory; the final directory name must be experience-loop.",
    )
    parser.add_argument(
        "--marketplace-root",
        type=Path,
        help=(
            "Build a local Marketplace at this directory instead of a bare Plugin. "
            "No host registration command is executed."
        ),
    )
    parser.add_argument(
        "--marketplace-name",
        default=DEFAULT_MARKETPLACE_NAME,
        help="Local Marketplace identifier used by the generated install command.",
    )
    parser.add_argument(
        "--cachebuster",
        help="Optional SemVer build token; defaults to a UTC local timestamp.",
    )
    parser.add_argument(
        "--validator",
        type=Path,
        help="Optional path to plugin-creator/scripts/validate_plugin.py.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Replace an existing unowned output directory after reviewing it; "
            "managed build outputs do not require this flag."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    try:
        if args.marketplace_root is not None and args.output is not None:
            raise PluginBuildError(
                "--marketplace-root and --output are mutually exclusive."
            )
        if args.marketplace_root is not None:
            result = build_marketplace(
                source_root=ROOT,
                packaging_root=DEFAULT_PACKAGING_ROOT,
                marketplace_root=args.marketplace_root,
                marketplace_name=args.marketplace_name,
                cachebuster=args.cachebuster,
                validator=args.validator,
                force=args.force,
            )
        else:
            if args.cachebuster is not None:
                raise PluginBuildError(
                    "--cachebuster requires --marketplace-root."
                )
            result = build_plugin(
                source_root=ROOT,
                packaging_root=DEFAULT_PACKAGING_ROOT,
                output=args.output or DEFAULT_OUTPUT,
                validator=args.validator,
                force=args.force,
            )
    except (OSError, PluginBuildError) as exc:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Plugin build failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["status"] == "marketplace-built":
            print(f"Local Marketplace built: {result['marketplace_root']}")
            print(f"plugin version={result['version']}")
            print("No Codex Plugin registration or cache operation was performed.")
        else:
            print(f"Plugin built: {result['output']}")
            print(
                "version={0} files={1} bytes={2} hooks={3}".format(
                    result["version"],
                    result["files"],
                    result["bytes"],
                    len(result["hook_files"]),
                )
            )
            if result["validator_output"]:
                print(result["validator_output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
