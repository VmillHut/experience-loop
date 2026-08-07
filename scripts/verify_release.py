#!/usr/bin/env python3
"""Run the repository's self-contained release checks."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent.parent

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHANGELOG_VERSION_PATTERN = re.compile(
    r"^## \[([^\]]+)\] - \d{4}-\d{2}-\d{2}\s*$", re.MULTILINE
)
PUBLISH_PLACEHOLDER_PATTERNS = (
    re.compile(r"<(?:owner|org|organization|username)>", re.IGNORECASE),
    re.compile(
        r"https://github\.com/(?:<[^>]+>|YOUR_[^/\s]+|REPLACE_ME|"
        r"(?:your|example)[_-]?(?:owner|org|organization|username)|"
        r"owner|org|organization|username)(?:/|$)",
        re.IGNORECASE,
    ),
)
PUBLISH_TEXT_FILES = ("README.md", "README.en.md")
PERSONAL_STATE_DIRECTORIES = {
    ".experience-loop",
    ".tmp-experience-loop",
    "experience-loop-data",
}
PERSONAL_STATE_FILES = {
    ".experience-loop-install.json",
    ".experience-loop.lock",
    "events.jsonl",
    "library.sqlite",
    "library.sqlite-shm",
    "library.sqlite-wal",
    "controls.json",
    "profile.json",
    "state.json",
}


def _parse_single_quoted_yaml(value: str, source: str, line_number: int) -> str:
    if len(value) < 2 or not value.endswith("'"):
        raise ValueError(f"{source}:{line_number}: unterminated single-quoted scalar")
    body = value[1:-1]
    output: list[str] = []
    index = 0
    while index < len(body):
        if body[index] != "'":
            output.append(body[index])
            index += 1
            continue
        if index + 1 >= len(body) or body[index + 1] != "'":
            raise ValueError(f"{source}:{line_number}: invalid single-quoted scalar")
        output.append("'")
        index += 2
    return "".join(output)


def _parse_yaml_scalar(value: str, source: str, line_number: int) -> Any:
    rendered = value.strip()
    if rendered.startswith('"'):
        try:
            parsed = json.loads(rendered)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{source}:{line_number}: invalid double-quoted scalar: {exc.msg}"
            ) from exc
        if not isinstance(parsed, str):
            raise ValueError(f"{source}:{line_number}: quoted scalar must be text")
        return parsed
    if rendered.startswith("'"):
        return _parse_single_quoted_yaml(rendered, source, line_number)
    if " #" in rendered:
        rendered = rendered.split(" #", 1)[0].rstrip()
    if not rendered:
        raise ValueError(f"{source}:{line_number}: empty scalar")
    lowered = rendered.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if rendered[0] in "[{&*!|>@`" or ": " in rendered:
        raise ValueError(f"{source}:{line_number}: unsupported YAML scalar syntax")
    return rendered


def _parse_yaml_mapping(lines: list[str], source: str) -> dict[str, Any]:
    """Parse the strict mapping/scalar YAML subset used by Skill metadata."""

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-2, root)]
    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
            raise ValueError(f"{source}:{line_number}: tabs are not allowed for indentation")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent % 2:
            raise ValueError(f"{source}:{line_number}: indentation must use two-space levels")
        content = raw_line[indent:]
        if content.startswith("-"):
            raise ValueError(f"{source}:{line_number}: sequences are not supported here")
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:[ ]*(.*))?", content)
        if match is None:
            raise ValueError(f"{source}:{line_number}: malformed mapping entry")
        while indent <= stack[-1][0]:
            stack.pop()
        expected_indent = stack[-1][0] + 2
        if indent != expected_indent:
            raise ValueError(f"{source}:{line_number}: invalid indentation depth")
        parent = stack[-1][1]
        key = match.group(1)
        if key in parent:
            raise ValueError(f"{source}:{line_number}: duplicate key {key!r}")
        raw_value = (match.group(2) or "").strip()
        if not raw_value or raw_value.startswith("#"):
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_yaml_scalar(raw_value, source, line_number)
    return root


def _force_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def check_skill(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    skill_path = root / "SKILL.md"
    try:
        text = skill_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read SKILL.md: {exc}"]
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append("SKILL.md must begin with YAML frontmatter.")
        return errors
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        errors.append("SKILL.md frontmatter is missing its closing delimiter.")
        return errors
    try:
        fields = _parse_yaml_mapping(lines[1:closing_index], "SKILL.md frontmatter")
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    unknown = sorted(set(fields) - {"name", "description"})
    if unknown:
        errors.append("SKILL.md frontmatter has unsupported field(s): " + ", ".join(unknown))
    name = fields.get("name", "")
    if not isinstance(name, str):
        errors.append("SKILL.md frontmatter name must be text.")
        name = ""
    if name != "experience-loop":
        errors.append("SKILL.md frontmatter name must be experience-loop.")
    if name and (len(name) > 64 or not SKILL_NAME_PATTERN.fullmatch(name)):
        errors.append("SKILL.md frontmatter name must be lowercase kebab-case and at most 64 characters.")
    description = fields.get("description", "")
    if not isinstance(description, str):
        errors.append("SKILL.md frontmatter description must be text.")
        description = ""
    if not description:
        errors.append("SKILL.md frontmatter needs a non-empty description.")
    elif len(description) > 1024 or "<" in description or ">" in description:
        errors.append(
            "SKILL.md description must be at most 1024 characters and contain no angle brackets."
        )
    if not any(line.strip() for line in lines[closing_index + 1 :]):
        errors.append("SKILL.md needs a non-empty instruction body.")
    if "TODO" in text:
        errors.append("SKILL.md still contains TODO text.")
    if len(text.splitlines()) > 500:
        errors.append("SKILL.md exceeds the 500-line progressive-disclosure limit.")
    return errors


def check_openai_metadata(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    metadata_path = root / "agents" / "openai.yaml"
    try:
        text = metadata_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read agents/openai.yaml: {exc}"]
    if "�" in text:
        errors.append("agents/openai.yaml contains invalid replacement characters.")
    try:
        metadata = _parse_yaml_mapping(text.splitlines(), "agents/openai.yaml")
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    interface = metadata.get("interface")
    policy = metadata.get("policy")
    if not isinstance(interface, dict):
        errors.append("agents/openai.yaml interface must be a mapping.")
        interface = {}
    if not isinstance(policy, dict):
        errors.append("agents/openai.yaml policy must be a mapping.")
        policy = {}
    display_name = interface.get("display_name")
    if display_name != "Experience Loop":
        errors.append("agents/openai.yaml display_name must be 'Experience Loop'.")
    short_description = interface.get("short_description")
    if not isinstance(short_description, str) or not short_description.strip():
        errors.append("agents/openai.yaml short_description must be non-empty text.")
    default_prompt = interface.get("default_prompt")
    if (
        not isinstance(default_prompt, str)
        or not default_prompt.strip()
        or "$experience-loop" not in default_prompt
    ):
        errors.append(
            "agents/openai.yaml default_prompt must be non-empty text invoking $experience-loop."
        )
    if policy.get("allow_implicit_invocation") is not False:
        errors.append(
            "agents/openai.yaml allow_implicit_invocation must be false; "
            "automatic scope is enforced by the controls-aware Plugin hook."
        )
    root_resolved = root.resolve()
    for key in ("icon_small", "icon_large"):
        relative = interface.get(key)
        if not isinstance(relative, str) or not relative.strip():
            errors.append(f"agents/openai.yaml {key} must be a non-empty relative path.")
            continue
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"agents/openai.yaml {key} must stay inside the Skill root.")
            continue
        candidate = (root_resolved / path).resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            errors.append(f"agents/openai.yaml {key} escapes the Skill root.")
            continue
        if not candidate.is_file():
            errors.append(f"agents/openai.yaml references missing asset: {relative}")
    return errors


def _runtime_version(root: Path) -> str:
    path = root / "scripts" / "experience_loop_lib" / "common.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "VERSION"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value.strip()
    raise ValueError("scripts/experience_loop_lib/common.py does not define a string VERSION.")


def check_version_consistency(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        file_version = (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        return [f"Cannot read VERSION: {exc}"]
    if not SEMVER_PATTERN.fullmatch(file_version):
        errors.append(f"VERSION is not valid SemVer: {file_version!r}")
    try:
        runtime_version = _runtime_version(root)
    except (OSError, SyntaxError, ValueError) as exc:
        errors.append(f"Cannot read runtime VERSION: {exc}")
        runtime_version = None
    try:
        changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"Cannot read CHANGELOG.md: {exc}")
        changelog_version = None
    else:
        match = CHANGELOG_VERSION_PATTERN.search(changelog)
        changelog_version = match.group(1).strip() if match else None
        if changelog_version is None:
            errors.append("CHANGELOG.md has no dated release heading such as ## [0.1.0] - 2026-08-05.")
    if runtime_version is not None and runtime_version != file_version:
        errors.append(
            f"Version mismatch: VERSION={file_version!r}, runtime VERSION={runtime_version!r}."
        )
    if changelog_version is not None and changelog_version != file_version:
        errors.append(
            f"Version mismatch: VERSION={file_version!r}, CHANGELOG={changelog_version!r}."
        )
    return errors


def check_tag_consistency(expected_tag: str, root: Path = ROOT) -> list[str]:
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        return [f"Cannot read VERSION for tag validation: {exc}"]
    actual = expected_tag.strip()
    if actual.startswith("refs/tags/"):
        actual = actual[len("refs/tags/") :]
    expected = "v" + version
    if actual != expected:
        return [f"Release tag mismatch: expected {expected!r}, received {actual!r}."]
    return []


def check_publish_placeholders(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative in PUBLISH_TEXT_FILES:
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Cannot read {relative}: {exc}")
            continue
        for pattern in PUBLISH_PLACEHOLDER_PATTERNS:
            match = pattern.search(text)
            if match:
                errors.append(
                    f"Publish placeholder remains in {relative}: {match.group(0)!r}."
                )
    return errors


def check_release_artifacts(root: Path = ROOT) -> list[str]:
    forbidden: list[str] = []
    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if ".git" in relative.parts:
            continue
        if "__pycache__" in relative.parts:
            forbidden.append(relative.as_posix())
            continue
        if any(part.lower() in PERSONAL_STATE_DIRECTORIES for part in relative.parts):
            forbidden.append(relative.as_posix())
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in {".pyc", ".pyo"}:
            forbidden.append(relative.as_posix())
        elif path.name.lower() in PERSONAL_STATE_FILES:
            forbidden.append(relative.as_posix())
        elif path.name.endswith(".experience-loop-export.zip"):
            forbidden.append(relative.as_posix())
    unique = sorted(set(forbidden))
    if not unique:
        return []
    shown = unique[:20]
    remainder = len(unique) - len(shown)
    rendered = ", ".join(shown)
    if remainder:
        rendered += f", ... and {remainder} more"
    return ["Release tree contains generated or personal-state artifacts: " + rendered]


def check_python39(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    paths = [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and ".git" not in path.parts
    ]
    for path in sorted(paths):
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path), feature_version=(3, 9))
        except (OSError, SyntaxError) as exc:
            errors.append(f"Python 3.9 parse failed for {path.relative_to(root)}: {exc}")
    return errors


def _relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def check_vendor(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    vendor_root = (root / "vendor").resolve()
    wheels_root = (vendor_root / "wheels").resolve()
    licenses_root = (root / "licenses").resolve()
    manifest_path = vendor_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Cannot read vendor manifest: {exc}"]
    packages = manifest.get("packages") if isinstance(manifest, dict) else None
    if not isinstance(packages, list):
        return ["vendor/manifest.json packages must be a list."]
    manifest_files: set[str] = set()
    package_names: set[str] = set()
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            errors.append(f"Vendor package entry {index} is not an object.")
            continue
        name = str(package.get("name") or "").strip()
        version = str(package.get("version") or "").strip()
        relative_file = str(package.get("file") or "").strip()
        expected_hash = str(package.get("sha256") or "").strip().lower()
        relative_license = str(package.get("license_file") or "").strip()
        if not name or not version or not relative_file or not relative_license:
            errors.append(
                f"Vendor package entry {index} is missing name, version, file, or license_file."
            )
            continue
        if name in package_names:
            errors.append(f"Duplicate vendor package name: {name}")
        package_names.add(name)
        path = (vendor_root / relative_file).resolve()
        if not _relative_to(path, wheels_root) or path.suffix.lower() != ".whl":
            errors.append(
                "Vendored artifact path is outside vendor/wheels or is not a wheel: "
                + relative_file
            )
            continue
        normalized_file = path.relative_to(vendor_root).as_posix()
        if normalized_file in manifest_files:
            errors.append(f"Duplicate vendored artifact entry: {normalized_file}")
        manifest_files.add(normalized_file)
        if not path.is_file():
            errors.append(f"Missing vendored artifact: vendor/{normalized_file}")
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                errors.append(f"Invalid SHA-256 in vendor manifest: {normalized_file}")
            elif digest != expected_hash:
                errors.append(f"Hash mismatch: vendor/{normalized_file}")
        license_path = (vendor_root / relative_license).resolve()
        if not _relative_to(license_path, licenses_root):
            errors.append(f"Vendor license path is outside licenses/: {relative_license}")
        elif not license_path.is_file():
            errors.append(f"Missing vendor license file: {license_path.relative_to(root)}")
    actual_files = (
        {
            path.resolve().relative_to(vendor_root).as_posix()
            for path in wheels_root.rglob("*.whl")
            if path.is_file()
        }
        if wheels_root.is_dir()
        else set()
    )
    unmanifested = sorted(actual_files - manifest_files)
    missing_from_tree = sorted(manifest_files - actual_files)
    if unmanifested:
        errors.append("Unmanifested vendored wheel(s): " + ", ".join(unmanifested))
    if missing_from_tree:
        errors.append(
            "Manifested wheel(s) missing from vendor/wheels: "
            + ", ".join(missing_from_tree)
        )
    return errors


def run_tests(root: Path = ROOT) -> tuple[int, str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env=environment,
    )
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    _force_utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--expected-tag",
        help="Require an exact release tag matching v<VERSION>, for example v0.1.0.",
    )
    args = parser.parse_args()

    errors = (
        check_skill()
        + check_openai_metadata()
        + check_version_consistency()
        + (check_tag_consistency(args.expected_tag) if args.expected_tag else [])
        + check_publish_placeholders()
        + check_release_artifacts()
        + check_python39()
        + check_vendor()
    )
    test_output = ""
    tests_ran = False
    if not args.skip_tests and not errors:
        tests_ran = True
        code, test_output = run_tests()
        if code != 0:
            errors.append("Unit/integration tests failed.")
        for error in check_release_artifacts():
            if error not in errors:
                errors.append(error)

    result = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "tests_ran": tests_ran,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Experience Loop release check: " + result["status"])
        for error in errors:
            print("- " + error)
        if test_output:
            print(test_output.rstrip())
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
