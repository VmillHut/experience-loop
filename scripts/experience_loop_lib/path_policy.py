"""Filesystem boundary and Git-ignore policy for read-only discovery.

The project scanner treats paths as untrusted input.  This module deliberately
prefers skipping an ambiguous entry over following it outside the requested
root.  It has no dependency on Git or third-party glob libraries.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
MAX_GITIGNORE_BYTES = 1024 * 1024


class PathPolicyError(ValueError):
    """A path cannot be proven to remain inside the allowed root."""


def is_reparse_point(path: Path) -> bool:
    """Return whether *path* is a symlink or Windows reparse point.

    ``Path.is_symlink`` does not consistently identify directory junctions on
    every Python/Windows combination.  ``st_file_attributes`` covers those
    junctions as well as other name-surrogate reparse points.
    """

    try:
        value = os.lstat(str(path))
    except (OSError, ValueError):
        return False
    if stat.S_ISLNK(value.st_mode):
        return True
    attributes = getattr(value, "st_file_attributes", 0)
    return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        return os.path.normcase(os.path.commonpath((str(root), str(candidate)))) == os.path.normcase(str(root))
    except (OSError, ValueError):
        return False


def _existing_components(path: Path) -> Sequence[Path]:
    parts = path.parts
    if not parts:
        return ()
    current = Path(parts[0])
    result = []  # type: List[Path]
    for part in parts[1:]:
        current = current / part
        if not os.path.lexists(str(current)):
            break
        result.append(current)
    return result


def safe_resolve(
    root: Path,
    candidate: Path,
    *,
    reject_reparse: bool = True,
    require_exists: bool = True,
) -> Path:
    """Resolve *candidate* only when it stays inside *root*.

    Both the lexical path and the fully resolved path must be contained.  When
    requested, every existing component is rejected if it is a symlink,
    junction, or other Windows reparse point.  This closes the common junction
    escape that ``follow_symlinks=False`` alone does not cover.
    """

    lexical_root = _absolute(Path(root))
    lexical_candidate = _absolute(Path(candidate))
    if not _is_within(lexical_root, lexical_candidate):
        raise PathPolicyError("path escapes the requested root")
    if reject_reparse:
        for component in _existing_components(lexical_root):
            if is_reparse_point(component):
                raise PathPolicyError("project root traverses a reparse point")
        relative_parts = lexical_candidate.relative_to(lexical_root).parts
        current = lexical_root
        if is_reparse_point(current):
            raise PathPolicyError("project root is a reparse point")
        for part in relative_parts:
            current = current / part
            if os.path.lexists(str(current)) and is_reparse_point(current):
                raise PathPolicyError("path traverses a reparse point")
    try:
        resolved_root = lexical_root.resolve(strict=True)
        resolved_candidate = lexical_candidate.resolve(strict=require_exists)
    except (OSError, RuntimeError) as exc:
        raise PathPolicyError("path cannot be resolved safely") from exc
    if not _is_within(resolved_root, resolved_candidate):
        raise PathPolicyError("resolved path escapes the requested root")
    return resolved_candidate


def _strip_unescaped_trailing_spaces(value: str) -> str:
    while value.endswith(" "):
        backslashes = 0
        index = len(value) - 2
        while index >= 0 and value[index] == "\\":
            backslashes += 1
            index -= 1
        if backslashes % 2:
            return value[:-2] + " "
        value = value[:-1]
    return value


def _glob_regex(pattern: str) -> re.Pattern[str]:
    output = ["^"]
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "\\" and index + 1 < len(pattern):
            index += 1
            output.append(re.escape(pattern[index]))
        elif character == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                while index + 1 < len(pattern) and pattern[index + 1] == "*":
                    index += 1
                if index + 1 < len(pattern) and pattern[index + 1] == "/":
                    index += 1
                    output.append("(?:.*/)?")
                else:
                    output.append(".*")
            else:
                output.append("[^/]*")
        elif character == "?":
            output.append("[^/]")
        elif character == "[":
            closing = pattern.find("]", index + 1)
            if closing < 0:
                output.append("\\[")
            else:
                content = pattern[index + 1:closing]
                if content.startswith("!"):
                    content = "^" + content[1:]
                elif content.startswith("^"):
                    content = "\\" + content
                output.append("[" + content.replace("/", "") + "]")
                index = closing
        else:
            output.append(re.escape(character))
        index += 1
    output.append("$")
    flags = re.IGNORECASE if os.name == "nt" else 0
    return re.compile("".join(output), flags)


class _IgnoreRule:
    def __init__(
        self,
        base: str,
        pattern: str,
        negated: bool,
        directory_only: bool,
        anchored: bool,
    ):
        self.base = base
        self.pattern = pattern
        self.negated = negated
        self.directory_only = directory_only
        self.anchored = anchored
        self.has_slash = "/" in pattern
        self.regex = _glob_regex(pattern)

    def matches(self, relative: str, is_directory: bool) -> bool:
        if self.base:
            if relative == self.base:
                local = ""
            elif relative.startswith(self.base + "/"):
                local = relative[len(self.base) + 1:]
            else:
                return False
        else:
            local = relative
        if not local or (self.directory_only and not is_directory):
            return False
        target = local if self.anchored or self.has_slash else local.rsplit("/", 1)[-1]
        return self.regex.match(target) is not None


class GitIgnoreMatcher:
    """Apply root and nested ``.gitignore`` files with common Git semantics."""

    def __init__(self, root: Path, *, read_rules: bool = True):
        self.root = safe_resolve(Path(root), Path(root))
        self._read_rules = bool(read_rules)
        self._root_rules = (
            self._load_rules("", self.root / ".gitignore") if self._read_rules else []
        )
        self._directory_cache = {"": (self._root_rules, True)}  # type: Dict[str, Tuple[List[_IgnoreRule], bool]]

    def _load_rules(self, base: str, path: Path) -> List[_IgnoreRule]:
        try:
            safe_path = safe_resolve(self.root, path)
            details = safe_path.stat()
            if not safe_path.is_file() or details.st_size > MAX_GITIGNORE_BYTES:
                return []
            with safe_path.open("r", encoding="utf-8", errors="replace") as handle:
                raw_lines = handle.readlines()
        except (OSError, PathPolicyError):
            return []
        rules = []  # type: List[_IgnoreRule]
        for raw in raw_lines:
            line = _strip_unescaped_trailing_spaces(raw.rstrip("\r\n"))
            if not line:
                continue
            escaped_leader = line.startswith("\\#") or line.startswith("\\!")
            if line.startswith("#") and not escaped_leader:
                continue
            negated = line.startswith("!") and not escaped_leader
            if negated:
                line = line[1:]
            directory_only = line.endswith("/") and not line.endswith("\\/")
            if directory_only:
                line = line[:-1]
            anchored = line.startswith("/")
            if anchored:
                line = line[1:]
            if line:
                rules.append(_IgnoreRule(base, line, negated, directory_only, anchored))
        return rules

    @staticmethod
    def _ignored_by_rules(relative: str, is_directory: bool, rules: Sequence[_IgnoreRule]) -> bool:
        ignored = False
        for rule in rules:
            if rule.matches(relative, is_directory):
                ignored = not rule.negated
        return ignored

    def _rules_for_directory(self, relative_directory: str) -> Tuple[List[_IgnoreRule], bool]:
        relative_directory = relative_directory.replace("\\", "/").strip("/")
        cached = self._directory_cache.get(relative_directory)
        if cached is not None:
            return cached
        parent, _, _ = relative_directory.rpartition("/")
        parent_rules, parent_accessible = self._rules_for_directory(parent)
        if not parent_accessible or self._ignored_by_rules(relative_directory, True, parent_rules):
            value = (parent_rules, False)
            self._directory_cache[relative_directory] = value
            return value
        ignore_path = self.root.joinpath(*relative_directory.split("/"), ".gitignore")
        rules = parent_rules + (
            self._load_rules(relative_directory, ignore_path) if self._read_rules else []
        )
        value = (rules, True)
        self._directory_cache[relative_directory] = value
        return value

    def is_ignored(self, path: Path, is_dir: bool) -> bool:
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                relative = candidate.relative_to(self.root).as_posix()
            except ValueError:
                return True
        else:
            relative = candidate.as_posix()
        relative = relative.replace("\\", "/").strip("/")
        if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
            return bool(relative)
        parent = relative.rpartition("/")[0]
        rules, accessible = self._rules_for_directory(parent)
        if not accessible:
            return True
        parts = relative.split("/")
        for count in range(1, len(parts)):
            ancestor = "/".join(parts[:count])
            if self._ignored_by_rules(ancestor, True, rules):
                return True
        return self._ignored_by_rules(relative, is_dir, rules)

    # Compatibility with the original scanner's small matcher interface.
    def ignored(self, relative: str, is_directory: bool) -> bool:
        return self.is_ignored(Path(relative), is_directory)
