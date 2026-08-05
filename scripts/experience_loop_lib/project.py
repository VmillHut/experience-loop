"""Read-only, bounded project discovery."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from .common import (
    SCHEMA_VERSION,
    ExperienceLoopError,
    atomic_write_json,
    load_json,
    sha256_bytes,
    stable_id,
    utc_now,
)
from .path_policy import GitIgnoreMatcher, PathPolicyError, is_reparse_point, safe_resolve
from .profile import load_profile
from .storage import Store


DEFAULT_MAX_FILES = 5000
DEFAULT_MAX_TOTAL_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_FILE_BYTES = 256 * 1024

EXCLUDED_DIRECTORIES = {
    ".git", ".hg", ".svn", ".idea", ".vs", ".vscode", ".gradle",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv",
    "__pycache__", "node_modules", "bower_components", "vendor",
    "library", "temp", "obj", "logs", "userSettings".lower(),
    "build", "builds", "dist", "out", "target", "bin", "coverage",
    ".next", ".nuxt", ".output", ".cache", "packages-lock.json.cache",
}
BACKUP_DIRECTORY_NAMES = {"backup", "backups", ".backup", ".backups", "_backup", "_backups"}
BACKUP_DIRECTORY_PREFIXES = (
    "_backup_", "_backup-", "_backup.",
    "_backups_", "_backups-", "_backups.",
)
SOURCE_DIRECTORY_NAMES = {
    "app", "apps", "client", "code", "codehotupdate", "hotupdate_share",
    "lib", "libs", "scripts", "server", "services", "source", "sources", "src",
}

SECRET_EXACT_NAMES = {
    ".env", ".npmrc", ".pypirc", ".netrc", "credentials", "credentials.json",
    "secrets.json", "secrets.yml", "secrets.yaml", "id_rsa", "id_ed25519",
    "service-account.json", "service_account.json",
}
SECRET_EXTENSIONS = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
TEXT_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".cs", ".java", ".kt", ".kts", ".go", ".rs", ".rb", ".php",
    ".cpp", ".cc", ".c", ".h", ".hpp", ".swift", ".scala", ".sh",
    ".ps1", ".sql", ".lua", ".vue", ".svelte", ".dart", ".ex", ".exs",
    ".json", ".jsonc", ".toml", ".yaml", ".yml", ".xml", ".props",
    ".targets", ".gradle", ".md", ".rst", ".txt", ".sln", ".csproj",
    ".fsproj", ".vbproj", ".asmdef",
}
IMPORTANT_NAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "poetry.lock",
    "cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
    "composer.json", "gemfile", "mix.exs", "pubspec.yaml", "makefile",
    "cmakelists.txt", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "projectsettings.asset", "packages-lock.json", "manifest.json",
}
PROJECT_DOCUMENT_NAMES = {"agents.md", "readme.md", "contributing.md"}
MAX_HIGH_SIGNAL_DEPTH = 4

IDENTITY_MANIFEST_PATHS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "projectsettings/projectversion.txt",
    "packages/manifest.json",
}
PROJECT_ID_PATTERN = re.compile(r"^prj_[A-Za-z0-9][A-Za-z0-9_-]{0,199}$")
ANNOTATION_FIELDS = (
    "architecture_notes",
    "learning_opportunities",
    "verification_notes",
)
MAX_ANNOTATIONS_PER_FIELD = 100
MAX_ANNOTATION_LENGTH = 2000

# Always inspect these small, high-signal files before breadth-limited traversal
# so a large Assets/src tree cannot hide the actual build system or engine.
PRIORITY_RELATIVE_PATHS = (
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "ProjectSettings/ProjectVersion.txt",
    "Packages/manifest.json",
    "Packages/packages-lock.json",
)

LANGUAGE_BY_EXTENSION = {
    ".py": "Python", ".pyi": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".cs": "C#", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
    ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".c": "C", ".h": "C/C++",
    ".swift": "Swift", ".scala": "Scala", ".dart": "Dart", ".lua": "Lua",
    ".vue": "Vue", ".svelte": "Svelte", ".ex": "Elixir", ".exs": "Elixir",
}


def _is_secret(relative: str) -> bool:
    path = Path(relative)
    lowered = [part.lower() for part in path.parts]
    name = path.name.lower()
    if any(part in {".ssh", ".aws", ".gnupg", ".azure"} for part in lowered):
        return True
    if name in SECRET_EXACT_NAMES or name.startswith(".env."):
        return True
    if path.suffix.lower() in SECRET_EXTENSIONS:
        return True
    return False


def _is_excluded_directory(name: str) -> bool:
    normalized = name.casefold()
    return (
        normalized in EXCLUDED_DIRECTORIES
        or normalized in BACKUP_DIRECTORY_NAMES
        or normalized.startswith(BACKUP_DIRECTORY_PREFIXES)
    )


def _directory_scan_priority(name: str, *, unity_layout: bool) -> int:
    normalized = name.casefold()
    if normalized in SOURCE_DIRECTORY_NAMES:
        return 0
    if unity_layout and normalized == "assets":
        return 0
    return 1


def _validate_project_id(project_id: str) -> str:
    value = str(project_id or "").strip()
    if not PROJECT_ID_PATTERN.match(value):
        raise ExperienceLoopError("项目 ID 格式无效。")
    return value


def _normalize_annotations(values: Optional[Iterable[str]]) -> Optional[List[str]]:
    if values is None:
        return None
    raw_values = [values] if isinstance(values, str) else values
    result = []  # type: List[str]
    seen = set()
    for value in raw_values:
        cleaned = str(value).strip()
        if not cleaned:
            continue
        if len(cleaned) > MAX_ANNOTATION_LENGTH:
            raise ExperienceLoopError(
                "单条项目注释不能超过 %s 个字符。" % MAX_ANNOTATION_LENGTH
            )
        if any(ord(character) < 32 and character not in "\n\t" for character in cleaned):
            raise ExperienceLoopError("项目注释不能包含控制字符。")
        if cleaned not in seen:
            result.append(cleaned)
            seen.add(cleaned)
    if len(result) > MAX_ANNOTATIONS_PER_FIELD:
        raise ExperienceLoopError(
            "每类项目注释不能超过 %s 条。" % MAX_ANNOTATIONS_PER_FIELD
        )
    return result


def _iter_files(root: Path, matcher: GitIgnoreMatcher, max_files: int) -> Tuple[List[Tuple[Path, str]], Dict[str, int], bool]:
    files = []  # type: List[Tuple[Path, str]]
    skipped = Counter()
    seen = set()

    for configured_relative in PRIORITY_RELATIVE_PATHS:
        candidate = root.joinpath(*Path(configured_relative).parts)
        relative = Path(configured_relative).as_posix()
        key = os.path.normcase(relative)
        try:
            if (
                not matcher.ignored(relative, False)
                and not _is_secret(relative)
            ):
                safe_candidate = safe_resolve(root, candidate)
                if not safe_candidate.is_file():
                    continue
                files.append((safe_candidate, relative))
                seen.add(key)
                if len(files) >= max_files:
                    return files, dict(skipped), True
        except PathPolicyError:
            if os.path.lexists(str(candidate)):
                skipped["unsafe_path"] += 1
        except OSError:
            skipped["unreadable"] += 1

    unity_layout = os.path.normcase("ProjectSettings/ProjectVersion.txt") in seen
    stack = [root]
    truncated = False
    while stack:
        current = stack.pop()
        try:
            entries = sorted(
                os.scandir(str(current)),
                key=lambda item: (
                    _directory_scan_priority(item.name, unity_layout=unity_layout),
                    item.name.casefold(),
                ),
                reverse=True,
            )
        except (OSError, PermissionError):
            skipped["unreadable"] += 1
            continue
        for entry in entries:
            try:
                entry_path = Path(entry.path)
                if is_reparse_point(entry_path):
                    skipped["reparse_point"] += 1
                    continue
                # Every traversed ancestor was accepted before it entered the
                # stack, and reparse points are rejected at each child. Avoid
                # resolving every ordinary file: on large repositories that
                # turns a metadata scan into thousands of unnecessary I/O
                # operations without strengthening the boundary.
                relative = entry_path.relative_to(root).as_posix()
                if entry.is_dir(follow_symlinks=False):
                    if _is_excluded_directory(entry.name):
                        skipped["excluded_directory"] += 1
                    elif matcher.ignored(relative, True):
                        skipped["gitignored"] += 1
                    else:
                        stack.append(Path(entry.path))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    skipped["non_regular"] += 1
                    continue
            except (PathPolicyError, ValueError):
                skipped["unsafe_path"] += 1
                continue
            except OSError:
                skipped["unreadable"] += 1
                continue
            if _is_secret(relative):
                skipped["secret"] += 1
                continue
            if matcher.ignored(relative, False):
                skipped["gitignored"] += 1
                continue
            key = os.path.normcase(relative)
            if key in seen:
                continue
            files.append((entry_path, relative))
            seen.add(key)
            if len(files) >= max_files:
                truncated = True
                return files, dict(skipped), truncated
    return files, dict(skipped), truncated


def _detect_frameworks(relative_paths: Sequence[str]) -> List[Dict[str, Any]]:
    lowered = {path.lower(): path for path in relative_paths}
    frameworks = []  # type: List[Dict[str, Any]]

    def add(name: str, evidence: Iterable[str]) -> None:
        found = [lowered[item] for item in evidence if item in lowered]
        if found:
            frameworks.append({"name": name, "evidence": found[:5]})

    add("Node.js", ("package.json",))
    add("Python", ("pyproject.toml", "requirements.txt", "setup.py"))
    add("Rust/Cargo", ("cargo.toml",))
    add("Go modules", ("go.mod",))
    add("Java/Maven", ("pom.xml",))
    add("Java/Gradle", ("build.gradle", "build.gradle.kts"))
    add("PHP/Composer", ("composer.json",))
    add("Ruby/Bundler", ("gemfile",))
    add("Flutter/Dart", ("pubspec.yaml",))
    unity_evidence = []
    for lower, original in lowered.items():
        if lower == "projectsettings/projectversion.txt" or lower == "packages/manifest.json":
            unity_evidence.append(original)
    if unity_evidence:
        frameworks.append({"name": "Unity/Tuanjie", "evidence": unity_evidence[:5]})
    if any(path.endswith(".sln") or path.endswith(".csproj") for path in lowered):
        evidence = [lowered[path] for path in lowered if path.endswith(".sln") or path.endswith(".csproj")]
        frameworks.append({"name": ".NET", "evidence": evidence[:5]})
    return frameworks


COMMAND_PATTERN = re.compile(
    r"^(?:\$\s*)?((?:python(?:3)?\s+-m\s+(?:pytest(?:\s+[^\r\n]+)?|unittest(?:\s+[^\r\n]+)?)|pytest(?:\s+[^\r\n]+)?|npm\s+(?:test|run\s+[\w:.-]+)|"
    r"pnpm\s+(?:test|run\s+[\w:.-]+)|yarn\s+(?:test|[\w:.-]+)|dotnet\s+(?:test|build)|"
    r"cargo\s+test|go\s+test(?:\s+\./\.\.\.)?|mvnw?(?:\.cmd)?\s+test|"
    r"\.?[\\/]?gradlew(?:\.bat)?\s+test|make\s+(?:test|check)|"
    r"[^\s]+unicli(?:\.cmd)?\s+[^\r\n]+))\s*$",
    re.IGNORECASE,
)

# Project documentation is untrusted input. Never preserve a shell chain as a
# runnable-looking validation command, even when its prefix is familiar.
UNSAFE_COMMAND_SYNTAX = re.compile(r"&&|\|\||[;&|<>`]|\$\(|\r|\n")


def _suggest_commands(relative_paths: Sequence[str], texts: Dict[str, str]) -> List[Dict[str, str]]:
    lowered = {path.lower() for path in relative_paths}
    suggestions = []  # type: List[Dict[str, str]]
    seen = set()

    def add(purpose: str, command: str, evidence: str, confidence: str) -> None:
        if UNSAFE_COMMAND_SYNTAX.search(command):
            return
        key = command.lower()
        if key in seen:
            return
        seen.add(key)
        suggestions.append({
            "purpose": purpose,
            "command": command,
            "evidence": evidence,
            "confidence": confidence,
            "status": "declared_not_executed" if confidence == "declared" else "suggested_not_executed",
            "untrusted_content": True,
            "execution_authorized": False,
            "requires_verification": True,
        })

    for relative, text in texts.items():
        lower_relative = relative.lower()
        if lower_relative == "package.json":
            try:
                package = json.loads(text)
            except json.JSONDecodeError:
                package = None
            scripts = package.get("scripts") if isinstance(package, dict) else None
            if isinstance(scripts, dict):
                for script_name in ("test", "check", "lint", "build"):
                    script = scripts.get(script_name)
                    if isinstance(script, str) and script.strip():
                        purpose = "test" if script_name in {"test", "check"} else script_name
                        add(purpose, "npm run %s" % script_name, "%s:scripts.%s" % (relative, script_name), "declared")
        if lower_relative == "pyproject.toml":
            for match in re.finditer(r"(?im)^\s*(?:test-command|test_command)\s*=\s*['\"]([^'\"]+)['\"]", text):
                add("test", match.group(1).strip(), "%s:test-command" % relative, "declared")
        if Path(relative).name.lower() in {"readme.md", "agents.md", "contributing.md"}:
            in_fence = False
            for line_number, raw_line in enumerate(text.splitlines(), 1):
                if raw_line.strip().startswith("```"):
                    in_fence = not in_fence
                    continue
                stripped = raw_line.strip().strip("`")
                candidates = [stripped]
                candidates.extend(
                    match.group(1).strip()
                    for match in re.finditer(r"`([^`\r\n]{1,500})`", raw_line)
                )
                for raw_candidate in candidates:
                    candidate = (
                        raw_candidate[2:].strip()
                        if raw_candidate.startswith(("- ", "* "))
                        else raw_candidate.strip()
                    )
                    match = COMMAND_PATTERN.match(candidate)
                    if not match:
                        continue
                    command = match.group(1).strip()
                    if re.search(r"test|pytest|check", command, re.IGNORECASE):
                        purpose = "test"
                    elif re.search(r"build", command, re.IGNORECASE):
                        purpose = "build"
                    else:
                        purpose = "validation"
                    add(purpose, command, "%s:%s" % (relative, line_number), "declared")

    if "pyproject.toml" in lowered or "requirements.txt" in lowered:
        combined = "\n".join(texts.get(path, "") for path in texts if path.lower() in {"pyproject.toml", "requirements.txt"})
        if "pytest" in combined.lower():
            add("test", "python -m pytest", "pyproject.toml/requirements.txt mentions pytest", "declared")
    if "package.json" in lowered:
        add("test", "npm test", "package.json", "heuristic")
    if "cargo.toml" in lowered:
        add("test", "cargo test", "Cargo.toml", "heuristic")
    if "go.mod" in lowered:
        add("test", "go test ./...", "go.mod", "heuristic")
    if "pom.xml" in lowered:
        add("test", "mvn test", "pom.xml", "heuristic")
    if "build.gradle" in lowered or "build.gradle.kts" in lowered:
        add("test", "./gradlew test", "Gradle build file", "heuristic")
    if any(path.endswith(".sln") or path.endswith(".csproj") for path in lowered):
        add("test", "dotnet test", ".sln/.csproj", "heuristic")
    return suggestions[:20]


def _extract_project_rules(texts: Dict[str, str]) -> List[Dict[str, Any]]:
    rules = []
    pattern = re.compile(
        r"(?:\bmust\b|\bmust not\b|\bshould\b|\brequired\b|\bdo not\b|禁止|不得|必须|应当|不要)",
        re.IGNORECASE,
    )
    for relative, text in texts.items():
        if Path(relative).name.lower() not in {"agents.md", "readme.md", "contributing.md"}:
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            cleaned = line.strip().lstrip("-*0123456789. ").strip()
            is_agents_bullet = Path(relative).name.lower() == "agents.md" and line.lstrip().startswith(("- ", "* "))
            if (pattern.search(cleaned) or is_agents_bullet) and 8 <= len(cleaned) <= 500:
                rules.append({
                    "text": cleaned[:300],
                    "evidence": "%s:%s" % (relative, line_number),
                    "untrusted_content": True,
                })
                if len(rules) >= 30:
                    return rules
    return rules


def _learning_opportunities(languages: Sequence[Dict[str, Any]], frameworks: Sequence[Dict[str, Any]], modules: Sequence[str]) -> List[Dict[str, Any]]:
    result = []
    if languages:
        result.append({
            "capability": "验证与审查",
            "why_now": "当前仓库有可识别的实现代码，适合在真实改动中练习证据驱动验收。",
            "evidence": languages[0].get("evidence", [])[:3],
        })
    if len(modules) >= 2:
        result.append({
            "capability": "架构边界判断",
            "why_now": "项目存在多个顶层模块，可在需求落点和依赖方向上练习边界决策。",
            "evidence": list(modules[:5]),
        })
    if frameworks:
        result.append({
            "capability": "工具链与约束识别",
            "why_now": "构建清单提供了可核验的工程约束，适合在执行前形成验证计划。",
            "evidence": frameworks[0].get("evidence", [])[:3],
        })
    return result


def _normalize_remote_url(value: str) -> Optional[str]:
    """Normalize common HTTPS/SSH Git remotes without retaining credentials."""

    raw = value.strip().strip('"\'')
    if (
        not raw
        or raw.startswith(("/", "\\", "./", "../", "file:"))
        or re.match(r"^[A-Za-z]:[\\/]", raw)
    ):
        return None
    host = ""
    path = ""
    port = None  # type: Optional[int]
    scp_match = re.match(r"^(?:[^@/\s]+@)?([^:/\s]+):(.+)$", raw)
    if scp_match and "://" not in raw:
        host = scp_match.group(1)
        path = scp_match.group(2)
    else:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https", "ssh", "git"} or not parsed.hostname:
            return None
        host = parsed.hostname
        path = parsed.path
        try:
            port = parsed.port
        except ValueError:
            return None
    host = host.lower().rstrip(".")
    if port is not None and port not in {22, 80, 443, 9418}:
        host = "%s:%s" % (host, port)
    path = re.sub(r"/+", "/", path.replace("\\", "/")).strip("/")
    if path.lower().endswith(".git"):
        path = path[:-4]
    if not host or not path or any(part in {"", ".", ".."} for part in path.split("/")):
        return None
    if host in {"github.com", "gitlab.com", "gitee.com", "bitbucket.org"}:
        path = path.lower()
    return "%s/%s" % (host, path)


def _git_remote_identity(root: Path) -> Optional[Dict[str, str]]:
    """Read a bounded in-root .git/config and return hashes only."""

    git_directory = root / ".git"
    try:
        safe_git = safe_resolve(root, git_directory)
        if not safe_git.is_dir():
            return None
        config_path = safe_resolve(root, safe_git / "config")
        if not config_path.is_file() or config_path.stat().st_size > 1024 * 1024:
            return None
        with config_path.open("r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except (OSError, PathPolicyError):
        return None

    remotes = []  # type: List[Tuple[str, str]]
    current_name = None  # type: Optional[str]
    for raw_line in text.splitlines():
        section = re.match(r'^\s*\[\s*remote\s+"([^"]+)"\s*\]\s*$', raw_line, re.IGNORECASE)
        if section:
            current_name = section.group(1).strip()
            continue
        if raw_line.lstrip().startswith("["):
            current_name = None
            continue
        if current_name:
            setting = re.match(r"^\s*url\s*=\s*(.*?)\s*$", raw_line, re.IGNORECASE)
            if setting:
                normalized = _normalize_remote_url(setting.group(1))
                if normalized:
                    remotes.append((current_name, normalized))
    if not remotes:
        return None
    remotes.sort(key=lambda item: (item[0].lower() != "origin", item[0].lower(), item[1]))
    remote_name, normalized_remote = remotes[0]
    return {
        "hash": sha256_bytes(normalized_remote.encode("utf-8")),
        "evidence": "git:remote:%s" % remote_name,
    }


def _project_identity(
    root: Path,
    manifest_hashes: Dict[str, str],
    *,
    allow_git_remote: bool = True,
) -> Dict[str, Any]:
    remote = _git_remote_identity(root) if allow_git_remote else None
    manifest_fingerprint = None  # type: Optional[str]
    manifest_evidence = sorted(manifest_hashes)
    if manifest_evidence:
        material = "\n".join(
            "%s:%s" % (relative.lower(), manifest_hashes[relative])
            for relative in manifest_evidence
        )
        manifest_fingerprint = sha256_bytes(material.encode("utf-8"))
    if remote:
        kind = "git-remote"
        primary = "git:%s" % remote["hash"]
    elif manifest_fingerprint:
        kind = "manifest-fingerprint"
        primary = "manifest:%s" % manifest_fingerprint
    else:
        kind = "path-only"
        primary = None
    return {
        "kind": kind,
        "strength": "strong" if primary else "weak",
        "primary_key": primary,
        "git_remote_hash": remote["hash"] if remote else None,
        "manifest_fingerprint": manifest_fingerprint,
        "evidence": ([remote["evidence"]] if remote else []) + manifest_evidence,
        "raw_remote_stored": False,
    }


def _identity_matches(current: Dict[str, Any], previous: Any) -> bool:
    if not isinstance(previous, dict):
        return False
    current_remote = current.get("git_remote_hash")
    previous_remote = previous.get("git_remote_hash")
    if current_remote or previous_remote:
        return bool(current_remote and previous_remote and current_remote == previous_remote)
    current_manifest = current.get("manifest_fingerprint")
    previous_manifest = previous.get("manifest_fingerprint")
    return bool(current_manifest and previous_manifest and current_manifest == previous_manifest)


def _candidate(project_id: str, summary: Dict[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "id": project_id,
        "name": summary.get("name"),
        "path": summary.get("path") or None,
        "reason": reason,
    }


def _resolve_project_identity(
    index: Dict[str, Any],
    canonical: str,
    project_name: str,
    identity: Dict[str, Any],
) -> Tuple[Optional[str], Dict[str, Any]]:
    projects = index["projects"]
    for project_id, summary in projects.items():
        if os.path.normcase(str(summary.get("path", ""))) == canonical:
            return project_id, {
                "status": "matched-path",
                "needs_confirmation": False,
                "candidates": [],
            }

    portable = [
        (project_id, summary) for project_id, summary in projects.items()
        if _identity_matches(identity, summary.get("identity"))
    ]
    if len(portable) == 1:
        return portable[0][0], {
            "status": "matched-portable-identity",
            "needs_confirmation": False,
            "candidates": [],
        }
    if len(portable) > 1:
        return None, {
            "status": "needs-confirmation",
            "needs_confirmation": True,
            "candidates": [_candidate(project_id, summary, "duplicate-portable-identity") for project_id, summary in portable],
        }

    placeholders = [
        (project_id, summary) for project_id, summary in projects.items()
        if not summary.get("path") and summary.get("name") == project_name
    ]
    if placeholders:
        return None, {
            "status": "needs-confirmation",
            "needs_confirmation": True,
            "candidates": [_candidate(project_id, summary, "legacy-name-placeholder") for project_id, summary in placeholders],
        }
    return None, {
        "status": "new",
        "needs_confirmation": False,
        "candidates": [],
    }


def _resolution_candidate_ids(value: Any) -> List[str]:
    if not isinstance(value, dict):
        return []
    candidates = value.get("candidates")
    if not isinstance(candidates, list):
        return []
    return [
        str(candidate.get("id"))
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("id")
    ]


def _project_has_attached_history(store: Store, project_id: str) -> bool:
    """Protect interim project IDs from being discarded after they were used."""

    if store.ledger_path.is_file():
        try:
            with store.ledger_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if isinstance(event, dict) and event.get("project_id") == project_id:
                        return True
        except (OSError, json.JSONDecodeError) as exc:
            raise ExperienceLoopError(
                "无法安全确认待合并项目是否已有账本历史：%s" % exc
            ) from exc
    database = store.knowledge_dir / "library.sqlite"
    if not database.is_file():
        return False
    try:
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        try:
            for table in (
                "bindings",
                "pending_source_bindings",
                "concept_cards",
                "application_evidence",
            ):
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                if exists and connection.execute(
                    "SELECT 1 FROM %s WHERE project_id = ? LIMIT 1" % table,
                    (project_id,),
                ).fetchone():
                    return True
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise ExperienceLoopError(
            "无法安全确认待合并项目是否已有知识库历史：%s" % exc
        ) from exc
    return False


def scan_project(
    store: Store,
    path: str,
    *,
    name: Optional[str] = None,
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    content_access_confirmed: bool = False,
    adopt_project_id: Optional[str] = None,
) -> Dict[str, Any]:
    store.require_initialized()
    if max_files < 1 or max_total_bytes < 1 or max_file_bytes < 1:
        raise ExperienceLoopError("扫描限制必须是正整数。")
    requested_root = Path(path).expanduser()
    if not requested_root.is_dir():
        raise ExperienceLoopError("项目目录不存在：%s" % requested_root)
    try:
        root = safe_resolve(requested_root, requested_root)
    except PathPolicyError as exc:
        raise ExperienceLoopError(
            "为防止越界扫描，项目根目录不能经过符号链接、目录联接或重解析点。",
            details={"path": str(requested_root), "reason": str(exc)},
        ) from exc

    profile = load_profile(store)
    privacy = profile.get("privacy", "normal")
    content_read_allowed = privacy == "normal" or (
        privacy == "restricted" and bool(content_access_confirmed)
    )
    # Ignore files are treated as traversal-control metadata so secret and
    # generated paths remain excluded even when project text reads are off.
    matcher = GitIgnoreMatcher(root)
    files, skipped, truncated = _iter_files(root, matcher, max_files)
    extension_counts = Counter()
    language_evidence = defaultdict(list)  # type: Dict[str, List[str]]
    analyzed = 0
    bytes_read = 0
    relevant_paths = []  # type: List[str]
    read_texts = {}  # type: Dict[str, str]
    manifest_hashes = {}  # type: Dict[str, str]
    read_limited = False

    for file_path, relative in files:
        extension = file_path.suffix.lower()
        extension_counts[extension or "<none>"] += 1
        language = LANGUAGE_BY_EXTENSION.get(extension)
        if language and len(language_evidence[language]) < 8:
            language_evidence[language].append(relative)
        lower_name = file_path.name.lower()
        lower_relative = relative.lower()
        if extension in TEXT_EXTENSIONS or lower_name in IMPORTANT_NAMES:
            relevant_paths.append(relative)
            depth = len(Path(relative).parts)
            should_read = (
                lower_relative in IDENTITY_MANIFEST_PATHS
                or (lower_name in IMPORTANT_NAMES and depth <= MAX_HIGH_SIGNAL_DEPTH)
                or (lower_name in PROJECT_DOCUMENT_NAMES and depth <= MAX_HIGH_SIGNAL_DEPTH)
            )
            if not content_read_allowed or not should_read:
                continue
            try:
                safe_file = safe_resolve(root, file_path)
                size = safe_file.stat().st_size
            except (OSError, PathPolicyError):
                skipped["unreadable"] = skipped.get("unreadable", 0) + 1
                continue
            if size > max_file_bytes:
                skipped["oversized"] = skipped.get("oversized", 0) + 1
                continue
            if bytes_read + size > max_total_bytes:
                read_limited = True
                continue
            try:
                safe_file = safe_resolve(root, safe_file)
                with safe_file.open("rb") as handle:
                    content = handle.read()
                analyzed += 1
                bytes_read += size
                if lower_relative in IDENTITY_MANIFEST_PATHS:
                    manifest_hashes[relative] = sha256_bytes(content)
                if lower_name in IMPORTANT_NAMES or lower_name in PROJECT_DOCUMENT_NAMES:
                    if b"\x00" not in content:
                        read_texts[relative] = content.decode("utf-8", errors="replace")
            except (OSError, PathPolicyError):
                skipped["unreadable"] = skipped.get("unreadable", 0) + 1

    languages = [
        {"name": language, "files": sum(1 for file_path, _ in files if LANGUAGE_BY_EXTENSION.get(file_path.suffix.lower()) == language),
         "evidence": evidence}
        for language, evidence in language_evidence.items()
    ]
    languages.sort(key=lambda item: (-item["files"], item["name"]))
    frameworks = _detect_frameworks(relevant_paths)
    top_level = sorted({relative.split("/", 1)[0] for _, relative in files if "/" in relative})[:30]
    commands = _suggest_commands(relevant_paths, read_texts)
    project_rules = _extract_project_rules(read_texts)

    canonical = os.path.normcase(str(root))
    index = store.load_projects_index()
    project_name = (name or root.name or "project").strip()
    identity = _project_identity(
        root,
        manifest_hashes,
        allow_git_remote=content_read_allowed,
    )
    existing_id, identity_resolution = _resolve_project_identity(
        index,
        canonical,
        project_name,
        identity,
    )
    provisional_project_id = None  # type: Optional[str]
    normalized_adopt_id = (
        _validate_project_id(adopt_project_id) if adopt_project_id else None
    )
    if normalized_adopt_id:
        if normalized_adopt_id not in index["projects"]:
            raise ExperienceLoopError("待采用的项目不存在：%s" % normalized_adopt_id)
        allowed_candidates = _resolution_candidate_ids(identity_resolution)
        if existing_id and normalized_adopt_id not in allowed_candidates:
            existing_record = load_json(store.project_path(existing_id), missing=None)
            if isinstance(existing_record, dict):
                allowed_candidates = _resolution_candidate_ids(
                    existing_record.get("identity_resolution")
                )
        if normalized_adopt_id not in allowed_candidates:
            raise ExperienceLoopError(
                "--adopt-project 只能选择本次身份确认候选：%s"
                % (", ".join(allowed_candidates) or "无")
            )
        if existing_id and existing_id != normalized_adopt_id:
            if _project_has_attached_history(store, existing_id):
                raise ExperienceLoopError(
                    "当前临时项目 ID 已有关联账本或知识记录，拒绝自动合并；"
                    "请先迁移这些记录或重新扫描一个尚未使用的副本。"
                )
            provisional_project_id = existing_id
        existing_id = normalized_adopt_id
        identity_resolution = {
            "status": "adopted-by-user-confirmation",
            "needs_confirmation": False,
            "adopted_project_id": normalized_adopt_id,
            "replaced_provisional_project_id": provisional_project_id,
            "candidates": [],
        }
    if existing_id:
        project_id = existing_id
    else:
        identity_key = identity.get("primary_key")
        project_id = stable_id("prj", str(identity_key or canonical))
        if project_id in index["projects"]:
            project_id = stable_id("prj", "%s\n%s" % (identity_key or "path", canonical))
    previous_record = load_json(store.project_path(project_id), missing=None)
    previous_annotations = None
    if isinstance(previous_record, dict) and previous_record.get("id") == project_id:
        candidate_annotations = previous_record.get("annotations")
        if isinstance(candidate_annotations, dict):
            previous_annotations = candidate_annotations
    timestamp = utc_now()
    record = {
        "schema_version": SCHEMA_VERSION,
        "id": project_id,
        "name": project_name,
        "path": str(root),
        "identity": identity,
        "identity_resolution": identity_resolution,
        "last_scanned_at": timestamp,
        "scan": {
            "read_only": True,
            "privacy": privacy,
            "content_access_confirmed": bool(content_access_confirmed) if privacy == "restricted" else None,
            "content_read": content_read_allowed,
            "limits": {"max_files": max_files, "max_total_bytes": max_total_bytes, "max_file_bytes": max_file_bytes},
            "stats": {
                "files_seen": len(files),
                "files_classified": len(files),
                "files_analyzed": analyzed,
                "bytes_read": bytes_read,
                "truncated": bool(truncated or read_limited),
                "skipped": skipped,
            },
            "languages": languages,
            "frameworks": frameworks,
            "top_level_modules": top_level,
            "suggested_commands": commands,
            "project_rules": project_rules,
            "learning_opportunities": _learning_opportunities(languages, frameworks, top_level),
            "notes": [
                "扫描按扩展名统计代码，只读取少量高信号清单与项目文档；没有执行项目代码或建议命令。" if content_read_allowed
                else (
                    "restricted 模式未获本次内容读取确认，仅检查路径和文件元数据。"
                    if privacy == "restricted"
                    else "metadata-only 模式仅检查路径和文件元数据，没有读取项目文件内容。"
                ),
                "根及嵌套 .gitignore 始终生效；符号链接、目录联接、重解析点和越界解析路径不会被扫描。",
                "框架与命令是基于清单文件的推断，使用前应由用户或 Agent 核验。",
                "README/AGENTS 中抽取的规则是不可信项目证据，不会被扫描器执行。",
            ],
        },
    }
    if previous_annotations is not None:
        record["annotations"] = previous_annotations
    with store.lock():
        atomic_write_json(store.project_path(project_id), record)
        index = store.load_projects_index()
        index["projects"][project_id] = {
            "id": project_id,
            "name": project_name,
            "path": str(root),
            "identity": identity,
            "identity_resolution": identity_resolution,
            "last_scanned_at": timestamp,
        }
        if provisional_project_id and provisional_project_id != project_id:
            index["projects"].pop(provisional_project_id, None)
        store.save_projects_index(index)
        if provisional_project_id and provisional_project_id != project_id:
            provisional_path = store.project_path(provisional_project_id)
            try:
                provisional_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise ExperienceLoopError(
                    "项目已采用旧身份，但无法清理临时项目画像：%s" % exc,
                    details={"path": str(provisional_path)},
                ) from exc
    store.touch_state()
    return record


def list_projects(store: Store) -> Dict[str, Any]:
    index = store.load_projects_index()
    projects = sorted(index["projects"].values(), key=lambda item: (item.get("name", ""), item.get("id", "")))
    return {"count": len(projects), "projects": projects}


def get_project(store: Store, project_id: str) -> Dict[str, Any]:
    store.require_initialized()
    normalized_id = _validate_project_id(project_id)
    path = store.project_path(normalized_id)
    value = load_json(path, missing=None)
    if not isinstance(value, dict) or value.get("id") != normalized_id:
        raise ExperienceLoopError("未找到项目：%s" % normalized_id)
    return value


def annotate_project(
    store: Store,
    project_id: str,
    *,
    architecture_notes: Optional[Iterable[str]] = None,
    learning_opportunities: Optional[Iterable[str]] = None,
    verification_notes: Optional[Iterable[str]] = None,
    replace: bool = False,
) -> Dict[str, Any]:
    """Persist non-authoritative project understanding for later Agent use.

    Annotations are explicitly marked as untrusted and verification-required;
    they never replace scanner evidence, manifests, or repository rules.
    ``replace`` applies only to note categories supplied by the caller, so an
    empty supplied list can deliberately clear one category.
    """

    store.require_initialized()
    normalized_id = _validate_project_id(project_id)
    supplied = {
        "architecture_notes": _normalize_annotations(architecture_notes),
        "learning_opportunities": _normalize_annotations(learning_opportunities),
        "verification_notes": _normalize_annotations(verification_notes),
    }
    if all(value is None for value in supplied.values()):
        raise ExperienceLoopError("至少提供一类项目注释。")
    with store.lock():
        path = store.project_path(normalized_id)
        record = load_json(path, missing=None)
        if not isinstance(record, dict) or record.get("id") != normalized_id:
            raise ExperienceLoopError("未找到项目：%s" % normalized_id)
        current = record.get("annotations")
        if not isinstance(current, dict):
            current = {}
        annotations = {
            "authority": "non-authoritative-user-context",
            "untrusted_content": True,
            "requires_verification": True,
            "architecture_notes": list(current.get("architecture_notes", [])),
            "learning_opportunities": list(current.get("learning_opportunities", [])),
            "verification_notes": list(current.get("verification_notes", [])),
            "updated_at": utc_now(),
        }
        for field in ANNOTATION_FIELDS:
            incoming = supplied[field]
            if incoming is None:
                continue
            if replace:
                annotations[field] = incoming
                continue
            merged = annotations[field] + incoming
            annotations[field] = list(dict.fromkeys(merged))
            if len(annotations[field]) > MAX_ANNOTATIONS_PER_FIELD:
                raise ExperienceLoopError(
                    "每类项目注释不能超过 %s 条。" % MAX_ANNOTATIONS_PER_FIELD
                )
        record["annotations"] = annotations
        atomic_write_json(path, record)
    store.touch_state()
    return record


def remove_project(store: Store, project_id: str) -> Dict[str, Any]:
    """Remove a project profile without deleting historical learning data."""

    store.require_initialized()
    normalized_id = _validate_project_id(project_id)
    with store.lock():
        path = store.project_path(normalized_id)
        record = load_json(path, missing=None)
        if not isinstance(record, dict) or record.get("id") != normalized_id:
            raise ExperienceLoopError("未找到项目：%s" % normalized_id)
        index = store.load_projects_index()
        index["projects"].pop(normalized_id, None)
        try:
            path.unlink()
            store.save_projects_index(index)
        except (OSError, ExperienceLoopError) as exc:
            if not path.exists():
                atomic_write_json(path, record)
            raise ExperienceLoopError(
                "无法解除项目：%s" % normalized_id,
                details={"path": str(path), "reason": str(exc)},
            ) from exc
    store.touch_state()
    return {
        "removed": True,
        "project_id": normalized_id,
        "project_name": record.get("name"),
        "retained_history": True,
        "retained_knowledge": True,
        "message": "项目画像已解除；经验账本和知识资料未被删除。",
    }
