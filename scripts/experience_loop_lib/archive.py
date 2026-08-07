"""Portable, integrity-checked export and import."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Tuple

from .common import (
    APP_NAME,
    EXIT_OPERATION_FAILED,
    SCHEMA_VERSION,
    DataCorruptionError,
    ExperienceLoopError,
    utc_now,
)
from .ledger import load_events
from .controls import load_controls, update_controls_locked
from .profile import configure_profile, load_profile
from .storage import Store


MAX_IMPORT_BYTES = 1024 * 1024 * 1024
ARCHIVE_SCHEMA_VERSION = 2
PORTABLE_CATALOG = "knowledge/portable-catalog.json"
BASE_REQUIRED_ARCHIVE_ENTRIES = {
    "state.json",
    "profile.json",
    "projects/index.json",
    "ledger/events.jsonl",
}
REQUIRED_ARCHIVE_ENTRIES = {
    1: BASE_REQUIRED_ARCHIVE_ENTRIES,
    ARCHIVE_SCHEMA_VERSION: BASE_REQUIRED_ARCHIVE_ENTRIES | {"controls.json"},
}
PROJECT_ID_PATTERN = re.compile(r"^prj_[0-9a-f]{16}$")


def _iter_export_files(store: Store, include_sources: bool) -> Iterable[Tuple[Path, str]]:
    fixed = [
        store.state_path,
        store.controls_path,
        store.profile_path,
        store.projects_index_path,
        store.ledger_path,
    ]
    for path in fixed:
        if path.is_file():
            yield path, path.relative_to(store.home).as_posix()
    if store.projects_dir.is_dir():
        for path in sorted(store.projects_dir.glob("*.json")):
            if path != store.projects_index_path and path.is_file() and not path.is_symlink():
                yield path, path.relative_to(store.home).as_posix()
    if store.knowledge_dir.is_dir():
        for path in sorted(store.knowledge_dir.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(store.home).as_posix()
            if relative == PORTABLE_CATALOG:
                continue
            if relative in {"knowledge/library.sqlite-wal", "knowledge/library.sqlite-shm"}:
                continue
            lowered_parts = {part.lower() for part in Path(relative).parts}
            if include_sources:
                yield path, relative
            elif path.suffix.lower() in {".json", ".jsonl"} and not lowered_parts.intersection({"objects", "sources", "raw", "originals"}):
                yield path, relative


def _knowledge_catalog_payload(store: Store) -> bytes:
    database = store.knowledge_dir / "library.sqlite"
    if not database.is_file():
        return b""
    try:
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sources'"
        ).fetchone()
        if table is None:
            return b""
        sources = [
            dict(row)
            for row in connection.execute(
                """
                SELECT s.source_id, s.title, s.file_name, s.extension, s.media_type,
                       s.status, s.created_at, s.updated_at, r.sha256 AS content_fingerprint,
                       r.metadata_json
                FROM sources s
                LEFT JOIN revisions r ON r.revision_id = s.current_revision_id
                ORDER BY s.source_id
                """
            ).fetchall()
        ]
        bindings = [
            dict(row)
            for row in connection.execute(
                "SELECT project_id, source_id, note, created_at, updated_at "
                "FROM bindings ORDER BY project_id, source_id"
            ).fetchall()
        ]
    except sqlite3.Error as exc:
        raise DataCorruptionError("无法导出知识目录元数据：%s" % exc) from exc
    finally:
        if "connection" in locals():
            connection.close()
    catalog = {
        "application": APP_NAME,
        "schema_version": SCHEMA_VERSION,
        "kind": "portable-knowledge-catalog",
        "created_at": utc_now(),
        "contains_source_text": False,
        "sources": sources,
        "bindings": bindings,
        "restore_note": "资料目录与项目绑定已恢复；重新提供原文件后才能重建可引用正文索引。",
    }
    return (json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _restore_knowledge_catalog(home: Path) -> int:
    catalog_path = home.joinpath(*PurePosixPath(PORTABLE_CATALOG).parts)
    database = home / "knowledge" / "library.sqlite"
    if not catalog_path.is_file() or database.is_file():
        return 0
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DataCorruptionError("portable knowledge catalog 已损坏。") from exc
    if (
        not isinstance(catalog, dict)
        or catalog.get("application") != APP_NAME
        or catalog.get("schema_version") != SCHEMA_VERSION
        or not isinstance(catalog.get("sources"), list)
        or not isinstance(catalog.get("bindings"), list)
    ):
        raise DataCorruptionError("portable knowledge catalog 格式或版本无效。")
    try:
        from .knowledge import _connect

        connection = _connect(home)
        with connection:
            for source in catalog["sources"]:
                if not isinstance(source, dict):
                    raise DataCorruptionError("portable knowledge catalog 包含无效资料条目。")
                source_id = str(source.get("source_id", ""))
                file_name = str(source.get("file_name", ""))
                status = str(source.get("status", "active"))
                if not source_id or not file_name or status not in {"active", "removed"}:
                    raise DataCorruptionError("portable knowledge catalog 资料标识无效。")
                connection.execute(
                    """
                    INSERT INTO sources(
                        source_id, logical_key, title, source_path, file_name,
                        extension, media_type, current_revision_id, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
                    ON CONFLICT(source_id) DO NOTHING
                    """,
                    (
                        source_id,
                        "portable:" + source_id,
                        str(source.get("title") or file_name),
                        "portable://re-add-required/" + file_name.replace("\\", "/"),
                        file_name,
                        str(source.get("extension") or Path(file_name).suffix.lower()),
                        str(source.get("media_type") or "application/octet-stream"),
                        status,
                        str(source.get("created_at") or utc_now()),
                        str(source.get("updated_at") or utc_now()),
                    ),
                )
            for binding in catalog["bindings"]:
                if not isinstance(binding, dict):
                    raise DataCorruptionError("portable knowledge catalog 包含无效绑定条目。")
                project_id = str(binding.get("project_id", ""))
                source_id = str(binding.get("source_id", ""))
                if not project_id or not source_id:
                    raise DataCorruptionError("portable knowledge catalog 绑定标识无效。")
                connection.execute(
                    """
                    INSERT INTO bindings(project_id, source_id, note, created_at, updated_at)
                    SELECT ?, ?, ?, ?, ?
                    WHERE EXISTS (SELECT 1 FROM sources WHERE source_id = ?)
                    ON CONFLICT(project_id, source_id) DO UPDATE SET
                        note = excluded.note,
                        updated_at = excluded.updated_at
                    """,
                    (
                        project_id,
                        source_id,
                        binding.get("note"),
                        str(binding.get("created_at") or utc_now()),
                        str(binding.get("updated_at") or utc_now()),
                        source_id,
                    ),
                )
        connection.close()
    except DataCorruptionError:
        raise
    except (ImportError, sqlite3.Error, ValueError) as exc:
        raise DataCorruptionError("无法恢复知识目录元数据：%s" % exc) from exc
    return len(catalog["sources"])


def _knowledge_database_snapshot_payload(store: Store) -> bytes:
    """Create one self-contained SQLite snapshot instead of copying WAL files."""

    database = store.knowledge_dir / "library.sqlite"
    if not database.is_file():
        return b""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".experience-loop-knowledge-", suffix=".sqlite"
    )
    os.close(descriptor)
    source = None
    destination = None
    try:
        source = sqlite3.connect(str(database), timeout=30.0)
        destination = sqlite3.connect(temporary_name)
        source.backup(destination)
        destination.close()
        destination = None
        source.close()
        source = None
        return Path(temporary_name).read_bytes()
    except (OSError, sqlite3.Error) as exc:
        raise ExperienceLoopError("无法创建 Knowledge Lens 一致性快照：%s" % exc) from exc
    finally:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        with contextlib.suppress(OSError):
            os.unlink(temporary_name)


def _sanitized_payload(path: Path, archive_name: str) -> bytes:
    data = path.read_bytes()
    if archive_name.startswith("projects/") and archive_name.endswith(".json"):
        try:
            value = json.loads(data.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return data
        if isinstance(value, dict):
            if archive_name == "projects/index.json":
                projects = value.get("projects", {})
                if isinstance(projects, dict):
                    for summary in projects.values():
                        if isinstance(summary, dict):
                            summary["path"] = None
            else:
                value["path"] = None
                scan = value.get("scan")
                if isinstance(scan, dict):
                    rules = scan.get("project_rules", [])
                    if isinstance(rules, list):
                        for rule in rules:
                            if isinstance(rule, dict) and isinstance(rule.get("text"), str):
                                rule["text_sha256"] = hashlib.sha256(
                                    rule["text"].encode("utf-8")
                                ).hexdigest()
                                rule.pop("text", None)
                                rule["redacted_from_export"] = True
                    commands = scan.get("suggested_commands", [])
                    if isinstance(commands, list):
                        for command in commands:
                            if isinstance(command, dict) and isinstance(
                                command.get("command"), str
                            ):
                                command["command_sha256"] = hashlib.sha256(
                                    command["command"].encode("utf-8")
                                ).hexdigest()
                                command.pop("command", None)
                                command["redacted_from_export"] = True
            return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return data


def export_archive(
    store: Store,
    destination: str,
    *,
    include_sources: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    store.require_initialized()
    with store.lock():
        return _export_archive_locked(
            store,
            destination,
            include_sources=include_sources,
            force=force,
        )


def _export_archive_locked(
    store: Store,
    destination: str,
    *,
    include_sources: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    store.require_initialized()
    if store.controls_path.exists():
        load_controls(store)
    else:
        update_controls_locked(store)
    output = Path(destination).expanduser().resolve()
    if output.exists() and not force:
        raise ExperienceLoopError(
            "导出目标已存在：%s。确认内容后使用 --force 覆盖。" % output,
            EXIT_OPERATION_FAILED,
        )
    if output.exists() and not output.is_file():
        raise ExperienceLoopError("导出目标不是普通文件：%s" % output)
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    payloads = []  # type: List[Tuple[str, bytes]]
    for path, archive_name in _iter_export_files(store, include_sources):
        try:
            if include_sources and archive_name == "knowledge/library.sqlite":
                payload = _knowledge_database_snapshot_payload(store)
            else:
                payload = _sanitized_payload(path, archive_name)
        except OSError as exc:
            raise ExperienceLoopError("导出时无法读取 %s：%s" % (path, exc)) from exc
        digest = hashlib.sha256(payload).hexdigest()
        entries.append({"path": archive_name, "size": len(payload), "sha256": digest})
        payloads.append((archive_name, payload))
    if not include_sources:
        catalog_payload = _knowledge_catalog_payload(store)
        if catalog_payload:
            entries.append({
                "path": PORTABLE_CATALOG,
                "size": len(catalog_payload),
                "sha256": hashlib.sha256(catalog_payload).hexdigest(),
            })
            payloads.append((PORTABLE_CATALOG, catalog_payload))
    manifest = {
        "application": APP_NAME,
        "archive_schema_version": ARCHIVE_SCHEMA_VERSION,
        "created_at": utc_now(),
        "includes_raw_sources": include_sources,
        "project_paths_removed": True,
        "entries": entries,
    }
    descriptor, temporary_name = tempfile.mkstemp(prefix=".%s." % output.name, suffix=".tmp", dir=str(output.parent))
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            for archive_name, payload in payloads:
                archive.writestr(archive_name, payload)
        os.replace(temporary_name, str(output))
        temporary_name = ""
    except (OSError, zipfile.BadZipFile) as exc:
        raise ExperienceLoopError("无法创建导出归档：%s" % exc) from exc
    finally:
        if temporary_name:
            with contextlib.suppress(OSError):
                os.unlink(temporary_name)
    return {
        "archive": str(output),
        "files": len(entries) + 1,
        "payload_files": len(entries),
        "bytes": sum(item["size"] for item in entries),
        "includes_raw_sources": include_sources,
        "privacy_note": (
            "默认不包含原始资料、项目源码、结构化项目路径或逐字项目规则/命令；但这不是可公开分享的脱敏包，仍包含画像、账本、项目画像与注释、资料目录与绑定备注、概念卡及应用证据，可能泄露敏感信息，分享前必须检查。"
            if not include_sources
            else "已明确包含知识库原始资料，并包含画像、账本、项目画像与注释、绑定备注、概念卡及应用证据；这不是公开脱敏包，请按高敏感备份保护。"
        ),
    }


def _safe_archive_name(name: str, archive_schema_version: int) -> str:
    if not name or "\\" in name or ":" in name or "\x00" in name:
        raise DataCorruptionError("归档包含不安全路径：%s" % name)
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise DataCorruptionError("归档包含不安全路径：%s" % name)
    allowed_roots = {"state.json", "profile.json", "projects", "ledger", "knowledge"}
    if archive_schema_version >= 2:
        allowed_roots.add("controls.json")
    if pure.parts[0] not in allowed_roots:
        raise DataCorruptionError("归档包含未知路径：%s" % name)
    if pure.parts[0] in {"state.json", "controls.json", "profile.json"} and len(pure.parts) != 1:
        raise DataCorruptionError("归档包含无效状态路径：%s" % name)
    return pure.as_posix()


def _read_manifest(archive: zipfile.ZipFile) -> Dict[str, Any]:
    try:
        raw = archive.read("manifest.json")
        manifest = json.loads(raw.decode("utf-8"))
    except (KeyError, UnicodeError, json.JSONDecodeError, OSError) as exc:
        raise DataCorruptionError("归档缺少有效 manifest.json。") from exc
    if not isinstance(manifest, dict) or manifest.get("application") != APP_NAME:
        raise DataCorruptionError("这不是 Experience Loop 归档。")
    archive_schema_version = manifest.get("archive_schema_version")
    if (
        type(archive_schema_version) is not int
        or archive_schema_version not in REQUIRED_ARCHIVE_ENTRIES
    ):
        raise DataCorruptionError("不支持的归档版本。")
    if not isinstance(manifest.get("entries"), list):
        raise DataCorruptionError("归档 manifest 的 entries 无效。")
    return manifest


def _validate_import_staging(home: Path, archive_schema_version: int) -> None:
    """Validate every required state layer before replacing an existing HOME."""

    staged_store = Store(str(home))
    staged_store.require_initialized()
    load_profile(staged_store)
    if archive_schema_version >= 2:
        load_controls(staged_store)
    else:
        # v1 stored mode/privacy in profile.json. Materialize the new controls
        # layer inside staging before the directory becomes authoritative.
        configure_profile(staged_store)
    projects_index = staged_store.load_projects_index()
    for project_id, summary in projects_index["projects"].items():
        if not isinstance(project_id, str) or not PROJECT_ID_PATTERN.match(project_id):
            raise DataCorruptionError("项目索引包含非法 project_id：%r" % project_id)
        if not isinstance(summary, dict) or summary.get("id") != project_id:
            raise DataCorruptionError("项目索引摘要与 project_id 不一致：%s" % project_id)
        project_path = staged_store.project_path(project_id)
        if not project_path.is_file():
            raise DataCorruptionError("归档缺少项目画像：%s" % project_id)
        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DataCorruptionError("项目画像损坏：%s" % project_id) from exc
        if (
            not isinstance(project, dict)
            or project.get("schema_version") != SCHEMA_VERSION
            or project.get("id") != project_id
        ):
            raise DataCorruptionError("项目画像格式或版本无效：%s" % project_id)
    load_events(staged_store)

    knowledge_root = staged_store.knowledge_dir
    if knowledge_root.exists() and any(knowledge_root.iterdir()):
        try:
            from .knowledge import (
                list_application_evidence,
                list_concept_cards,
                list_sources,
            )

            list_sources(data_dir=str(home), include_removed=True)
            list_concept_cards(data_dir=str(home), include_retired=True)
            list_application_evidence(data_dir=str(home), limit=1_000)
        except Exception as exc:
            raise DataCorruptionError("知识库或派生知识无法恢复：%s" % exc) from exc


def import_archive(store: Store, source: str, *, replace: bool = False) -> Dict[str, Any]:
    archive_path = Path(source).expanduser().resolve()
    if not archive_path.is_file():
        raise ExperienceLoopError("归档不存在：%s" % archive_path)
    if store.home.exists() and any(store.home.iterdir()) and replace:
        store.assert_managed_home()
    store.home.parent.mkdir(parents=True, exist_ok=True)
    with store.lock():
        return _import_archive_locked(store, str(archive_path), replace=replace)


def _import_archive_locked(store: Store, source: str, *, replace: bool = False) -> Dict[str, Any]:
    archive_path = Path(source).expanduser().resolve()
    if not archive_path.is_file():
        raise ExperienceLoopError("归档不存在：%s" % archive_path)
    home_path = store.home.expanduser().resolve()
    try:
        archive_inside_home = os.path.commonpath(
            [os.path.normcase(str(archive_path)), os.path.normcase(str(home_path))]
        ) == os.path.normcase(str(home_path))
    except ValueError:
        archive_inside_home = False
    if archive_inside_home:
        raise ExperienceLoopError(
            "导入归档位于目标个人数据目录内；--replace 会删除该文件。请先把归档复制到目录外。",
            EXIT_OPERATION_FAILED,
        )
    if store.home.exists() and any(store.home.iterdir()):
        if not replace:
            raise ExperienceLoopError("目标数据目录已有内容。确认后使用 --replace，或指定新的 --home。")
        store.assert_managed_home()
    staging_parent = store.home.parent
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".%s-import-" % store.home.name, dir=str(staging_parent)))
    backup = None
    total = 0
    archive_file_count = 0
    try:
        try:
            archive = zipfile.ZipFile(str(archive_path), "r")
        except (OSError, zipfile.BadZipFile) as exc:
            raise DataCorruptionError("无法打开归档：%s" % exc) from exc
        with archive:
            archive_file_count = len(archive.infolist())
            manifest = _read_manifest(archive)
            archive_schema_version = int(manifest["archive_schema_version"])
            seen = set()
            for entry in manifest["entries"]:
                if not isinstance(entry, dict):
                    raise DataCorruptionError("归档条目格式无效。")
                name = _safe_archive_name(
                    str(entry.get("path", "")), archive_schema_version
                )
                if name in seen:
                    raise DataCorruptionError("归档包含重复条目：%s" % name)
                seen.add(name)
                expected_size = entry.get("size")
                expected_hash = entry.get("sha256")
                if (
                    type(expected_size) is not int
                    or expected_size < 0
                    or not isinstance(expected_hash, str)
                ):
                    raise DataCorruptionError("归档条目元数据无效：%s" % name)
                total += expected_size
                if total > MAX_IMPORT_BYTES:
                    raise DataCorruptionError("归档解压后超过 1 GiB 安全限制。")
                try:
                    source_handle = archive.open(name, "r")
                except KeyError as exc:
                    raise DataCorruptionError("归档缺少声明文件：%s" % name) from exc
                target = staging.joinpath(*PurePosixPath(name).parts)
                staging_root = Path(os.path.abspath(str(staging)))
                target_absolute = Path(os.path.abspath(str(target)))
                try:
                    inside_staging = os.path.commonpath(
                        [os.path.normcase(str(staging_root)), os.path.normcase(str(target_absolute))]
                    ) == os.path.normcase(str(staging_root))
                except ValueError:
                    inside_staging = False
                if not inside_staging:
                    raise DataCorruptionError("归档路径越过导入暂存目录：%s" % name)
                target = target_absolute
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                written = 0
                with source_handle, target.open("wb") as output:
                    while True:
                        chunk = source_handle.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > expected_size:
                            raise DataCorruptionError("归档文件大小与 manifest 不符：%s" % name)
                        digest.update(chunk)
                        output.write(chunk)
                if written != expected_size or digest.hexdigest() != expected_hash:
                    raise DataCorruptionError("归档完整性校验失败：%s" % name)
            missing_required = sorted(
                REQUIRED_ARCHIVE_ENTRIES[archive_schema_version] - seen
            )
            if missing_required:
                raise DataCorruptionError(
                    "归档缺少必要状态文件：%s" % ", ".join(missing_required)
                )
            raw_entries_present = (
                "knowledge/library.sqlite" in seen
                or any(name.startswith("knowledge/objects/") for name in seen)
            )
            if raw_entries_present and not bool(manifest.get("includes_raw_sources")):
                raise DataCorruptionError("归档声明不含原始资料，但实际包含原始知识库内容。")
        restored_knowledge_sources = _restore_knowledge_catalog(staging)
        _validate_import_staging(staging, archive_schema_version)
        if store.home.exists():
            backup = store.home.with_name(".%s-backup-%s" % (store.home.name, os.getpid()))
            if backup.exists():
                shutil.rmtree(str(backup))
            os.replace(str(store.home), str(backup))
        os.replace(str(staging), str(store.home))
        staging = None
        store.harden_known_permissions(deep=True)
        if backup is not None:
            shutil.rmtree(str(backup), ignore_errors=True)
            backup = None
    except Exception:
        if backup is not None and backup.exists() and not store.home.exists():
            os.replace(str(backup), str(store.home))
            backup = None
        raise
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(str(staging), ignore_errors=True)
        if backup is not None and backup.exists():
            shutil.rmtree(str(backup), ignore_errors=True)
    includes_raw_sources = bool(manifest.get("includes_raw_sources"))
    next_actions = ["重新扫描项目，以确认这台电脑上的项目身份和路径。"]
    if not includes_raw_sources and restored_knowledge_sources:
        next_actions.append("重新提供原资料文件，以恢复全文检索并重新核验概念卡引用。")
    return {
        "imported": True,
        "archive": str(archive_path),
        "home": str(store.home),
        "files": archive_file_count,
        "payload_files": len(manifest["entries"]),
        "includes_raw_sources": includes_raw_sources,
        "restored_knowledge_sources": restored_knowledge_sources,
        "next_action": next_actions[0],
        "next_actions": next_actions,
    }
