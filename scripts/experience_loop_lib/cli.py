"""Command-line interface for Experience Loop."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .archive import export_archive, import_archive
from .common import (
    CAPABILITIES,
    EXIT_IO,
    EXIT_OK,
    EXIT_OPERATION_FAILED,
    EXIT_PARTIAL,
    EXIT_UNEXPECTED,
    EXIT_USAGE,
    SCHEMA_VERSION,
    VERSION,
    DataCorruptionError,
    DependencyError,
    ExperienceLoopError,
    normalize_mode,
)
from .ledger import INDEPENDENCE_LEVELS, KINDS, load_events, record_event, review_events
from .profile import (
    PRIVACY_LEVELS,
    configure_profile,
    default_profile,
    load_profile,
    load_profile_controls,
    profile_for_display,
    set_mode,
    validate_profile,
)
from .project import (
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_TOTAL_BYTES,
    annotate_project,
    get_project,
    list_projects,
    remove_project,
    scan_project,
)
from .storage import Store


def _extract_global_options(argv: Sequence[str]) -> Tuple[List[str], Optional[str], bool]:
    """Allow --home and --json before or after nested subcommands."""
    cleaned = []
    home = None
    json_mode = False
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--json":
            json_mode = True
            index += 1
            continue
        if token == "--home":
            if index + 1 >= len(argv):
                raise ExperienceLoopError("--home 需要一个目录路径。")
            home = argv[index + 1]
            index += 2
            continue
        if token.startswith("--home="):
            home = token.split("=", 1)[1]
            if not home:
                raise ExperienceLoopError("--home 不能为空。")
            index += 1
            continue
        cleaned.append(token)
        index += 1
    return cleaned, home, json_mode


class RuntimeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ExperienceLoopError("命令参数无效：%s" % message, EXIT_USAGE)


def _mode_value(value: str) -> str:
    try:
        return normalize_mode(value)
    except ExperienceLoopError as exc:
        raise argparse.ArgumentTypeError(exc.message) from exc


def _parser() -> argparse.ArgumentParser:
    parser = RuntimeArgumentParser(
        prog="experience-loop",
        description="把 Agent 完成的工作重新变成可迁移、可验证的工程经验。",
    )
    parser.add_argument("--home", help="个人数据目录（也可用 EXPERIENCE_LOOP_HOME）")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="幂等初始化个人数据目录和画像")
    setup.add_argument("--name")
    setup.add_argument("--role")
    setup.add_argument("--experience-level", help="经验阶段，例如 junior、1-3 years 或 senior")
    setup.add_argument("--responsibility", action="append", default=[])
    setup.add_argument("--domain", action="append", default=[])
    setup.add_argument("--goal", action="append", default=[])
    setup.add_argument("--learning-focus", action="append", default=[])
    setup.add_argument("--explanation-style")
    setup.add_argument(
        "--guidance-preference",
        help="指导互动偏好，例如少打断、愿意先判断或高价值时可短暂等待",
    )
    setup.add_argument("--delivery-context")
    setup.add_argument(
        "--mode", type=_mode_value, metavar="{auto,focus,deep,off}", default=None
    )
    setup.add_argument("--privacy", choices=PRIVACY_LEVELS, default=None)
    setup.add_argument("--project", help="初始化后立即只读扫描的主项目目录")
    setup.add_argument(
        "--confirm-content-access",
        action="store_true",
        help="在 restricted 模式下确认本次项目扫描可读取允许的文本内容",
    )

    commands.add_parser("status", help="查看当前模式、项目和经验账本状态")
    profile = commands.add_parser("profile", help="查看或更新个人学习画像")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser("show", help="查看当前个人学习画像")
    profile_update = profile_commands.add_parser("update", help="增补、替换或清空画像字段")
    profile_update.add_argument("--name")
    profile_update.add_argument("--clear-name", action="store_true")
    profile_update.add_argument("--role")
    profile_update.add_argument("--reset-role", action="store_true")
    profile_update.add_argument("--experience-level")
    profile_update.add_argument("--clear-experience-level", action="store_true")
    profile_update.add_argument("--responsibility", action="append")
    profile_update.add_argument("--replace-responsibilities", action="store_true")
    profile_update.add_argument("--clear-responsibilities", action="store_true")
    profile_update.add_argument("--domain", action="append")
    profile_update.add_argument("--replace-domains", action="store_true")
    profile_update.add_argument("--clear-domains", action="store_true")
    profile_update.add_argument("--goal", action="append")
    profile_update.add_argument("--replace-goals", action="store_true")
    profile_update.add_argument("--clear-goals", action="store_true")
    profile_update.add_argument("--learning-focus", action="append")
    profile_update.add_argument("--replace-learning-focus", action="store_true")
    profile_update.add_argument("--clear-learning-focus", action="store_true")
    profile_update.add_argument("--explanation-style")
    profile_update.add_argument("--clear-explanation-style", action="store_true")
    profile_update.add_argument("--guidance-preference")
    profile_update.add_argument("--clear-guidance-preference", action="store_true")
    profile_update.add_argument("--delivery-context")
    profile_update.add_argument("--clear-delivery-context", action="store_true")
    profile_update.add_argument(
        "--mode", type=_mode_value, metavar="{auto,focus,deep,off}"
    )
    profile_update.add_argument("--privacy", choices=PRIVACY_LEVELS)
    doctor = commands.add_parser("doctor", help="检查运行环境和数据完整性")
    doctor.add_argument("--repair", action="store_true", help="补齐安全的缺失目录、默认文件和私有权限")
    doctor.add_argument("--deep", action="store_true", help="额外校验每个当前资料对象的 SHA-256")

    mode = commands.add_parser("mode", help="查看或切换工作模式")
    mode.add_argument(
        "value", nargs="?", type=_mode_value, metavar="{auto,focus,deep,off}"
    )

    project = commands.add_parser("project", help="管理项目画像")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    scan = project_commands.add_parser("scan", help="只读、有界地扫描项目")
    scan.add_argument("path", nargs="?", default=".")
    scan.add_argument("--name")
    scan.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    scan.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    scan.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    scan.add_argument(
        "--adopt-project",
        help="确认当前目录就是身份候选中的既有项目，并沿用其历史 project_id",
    )
    scan.add_argument(
        "--confirm-content-access",
        action="store_true",
        help="在 restricted 模式下确认本次扫描可读取允许的文本内容",
    )
    project_commands.add_parser("list", help="列出已扫描项目")
    project_inspect = project_commands.add_parser("inspect", help="查看完整项目画像")
    project_inspect.add_argument("project_id")
    project_annotate = project_commands.add_parser(
        "annotate", help="保存需持续核验的架构理解与学习机会"
    )
    project_annotate.add_argument("project_id")
    project_annotate.add_argument("--architecture-note", action="append")
    project_annotate.add_argument("--learning-opportunity", action="append")
    project_annotate.add_argument("--verification-note", action="append")
    project_annotate.add_argument("--clear-architecture-notes", action="store_true")
    project_annotate.add_argument("--clear-learning-opportunities", action="store_true")
    project_annotate.add_argument("--clear-verification-notes", action="store_true")
    project_annotate.add_argument(
        "--replace", action="store_true", help="替换本次提供的类别，而不是追加"
    )
    project_remove = project_commands.add_parser("remove", help="解除项目画像；默认只预览")
    project_remove.add_argument("project_id")
    project_remove.add_argument("--yes", action="store_true", help="确认解除项目画像")

    ledger = commands.add_parser("ledger", help="记录和复盘真实工作证据")
    ledger_commands = ledger.add_subparsers(dest="ledger_command", required=True)
    record = ledger_commands.add_parser("record", help="记录一个决策、验证或迁移事件")
    record.add_argument("--kind", required=True, choices=KINDS)
    record.add_argument("--summary", required=True)
    record.add_argument("--project")
    record.add_argument("--evidence", action="append", default=[])
    record.add_argument("--concept", action="append", default=[])
    record.add_argument(
        "--capability",
        choices=CAPABILITIES,
        help="本事件对应的长期能力方向；通常由 Agent 自动选择",
    )
    record.add_argument("--independence", choices=INDEPENDENCE_LEVELS, default="guided")
    record.add_argument("--outcome")
    record.add_argument("--prior-event", help="迁移事件所复用的先前经验事件 ID")
    record.add_argument("--context-difference", help="迁移事件中新旧情境的关键差异")
    record.add_argument(
        "--confidence",
        type=float,
        metavar="0.0-1.0",
        help="0.0–1.0 的浮点数，用于表达这条判断的置信度",
    )
    record.add_argument("--tag", action="append", default=[])
    review = ledger_commands.add_parser("review", help="回顾经验记录和证据型 XP")
    review.add_argument("--project")
    review.add_argument("--limit", type=int, default=20)
    review.add_argument("--since-days", type=int)

    knowledge = commands.add_parser("knowledge", help="摄取、查询和绑定个人资料")
    knowledge_commands = knowledge.add_subparsers(dest="knowledge_command", required=True)
    add = knowledge_commands.add_parser(
        "add",
        help="添加资料；批量部分成功会保留成功项并以退出码 3 返回",
        description=(
            "添加资料并自动解析、索引。批量处理中若只有部分文件成功，"
            "成功项会保留，命令仍以非零退出码 3 返回。"
        ),
    )
    add.add_argument("paths", nargs="+")
    add.add_argument("--project")
    add.add_argument("--no-recursive", action="store_true")
    add.add_argument("--confirm-content-access", action="store_true")
    listing = knowledge_commands.add_parser("list", help="列出资料")
    listing.add_argument("--project")
    listing.add_argument("--include-removed", action="store_true")
    query = knowledge_commands.add_parser("query", help="检索可核验的原文证据")
    query.add_argument("query")
    query.add_argument("--project")
    query.add_argument("--top-k", "--limit", dest="top_k", type=int, default=8)
    query.add_argument("--source", action="append", default=[])
    query.add_argument("--confirm-content-access", action="store_true")
    inspect = knowledge_commands.add_parser("inspect", help="查看资料元数据和可定位文本块")
    inspect.add_argument("source_id")
    inspect.add_argument("--include-chunks", action="store_true")
    inspect.add_argument("--chunk-limit", type=int, default=20)
    inspect.add_argument("--confirm-content-access", action="store_true")
    bind = knowledge_commands.add_parser("bind", help="把资料绑定到项目")
    bind.add_argument("source_id")
    bind.add_argument("project_id")
    bind.add_argument("--note")
    remove = knowledge_commands.add_parser("remove", help="移除资料索引")
    remove.add_argument("source_id")
    remove.add_argument("--purge", action="store_true", help="同时删除本地保存的源副本")
    remove.add_argument("--yes", action="store_true", help="确认不可逆 purge")
    reindex = knowledge_commands.add_parser("reindex", help="重建一个或全部资料索引")
    reindex.add_argument("source_id", nargs="?")
    reindex.add_argument("--confirm-content-access", action="store_true")

    concept = knowledge_commands.add_parser("concept", help="管理由真实引用支撑的概念卡")
    concept_commands = concept.add_subparsers(dest="concept_command", required=True)
    concept_upsert = concept_commands.add_parser("upsert", help="创建或更新概念卡")
    concept_upsert.add_argument("--title", required=True)
    concept_upsert.add_argument("--thesis", required=True)
    concept_upsert.add_argument("--citation", action="append", required=True)
    concept_upsert.add_argument("--concept-id")
    concept_upsert.add_argument("--project")
    concept_upsert.add_argument("--status", choices=("draft", "reviewed", "retired"), default="draft")
    concept_upsert.add_argument("--applies-when", action="append", default=[])
    concept_upsert.add_argument("--does-not-apply-when", action="append", default=[])
    concept_upsert.add_argument("--common-misuse", action="append", default=[])
    concept_upsert.add_argument("--decision-trigger", action="append", default=[])
    concept_upsert.add_argument("--engineering-question", action="append", default=[])
    concept_upsert.add_argument("--tag", action="append", default=[])
    concept_list = concept_commands.add_parser("list", help="列出概念卡及其引用健康度")
    concept_list.add_argument("--project")
    concept_list.add_argument("--source")
    concept_list.add_argument("--include-retired", action="store_true")
    concept_search = concept_commands.add_parser("search", help="按当前决策检索可复用概念卡")
    concept_search.add_argument("query")
    concept_search.add_argument("--project")
    concept_search.add_argument("--source")
    concept_search.add_argument("--limit", type=int, default=20)
    concept_search.add_argument("--include-retired", action="store_true")
    concept_inspect = concept_commands.add_parser("inspect", help="查看概念卡和真实应用记录")
    concept_inspect.add_argument("concept_id")
    concept_inspect.add_argument("--application-limit", type=int, default=50)
    concept_remove = concept_commands.add_parser("remove", help="停用或彻底删除概念卡")
    concept_remove.add_argument("concept_id")
    concept_remove.add_argument("--purge", action="store_true")
    concept_remove.add_argument("--yes", action="store_true", help="确认不可逆 purge")

    application = knowledge_commands.add_parser("application", help="记录概念在真实工程中的应用证据")
    application_commands = application.add_subparsers(dest="application_command", required=True)
    application_record = application_commands.add_parser("record", help="记录一次项目应用或迁移")
    application_record.add_argument("concept_id")
    application_record.add_argument("--situation", required=True)
    application_record.add_argument("--decision", required=True)
    application_record.add_argument("--outcome", required=True)
    application_record.add_argument("--project")
    application_record.add_argument("--evidence", action="append", default=[])
    application_record.add_argument(
        "--independence", choices=INDEPENDENCE_LEVELS, default="guided"
    )
    application_list = application_commands.add_parser("list", help="列出应用与迁移证据")
    application_list.add_argument("--concept")
    application_list.add_argument("--project")
    application_list.add_argument("--limit", type=int, default=100)

    export = commands.add_parser("export", help="导出可迁移归档")
    export.add_argument("destination")
    export.add_argument("--include-sources", action="store_true", help="明确包含原始资料（可能敏感且体积较大）")
    export.add_argument("--force", action="store_true", help="明确覆盖已存在的归档文件")
    importing = commands.add_parser("import", help="校验并导入归档")
    importing.add_argument("source")
    importing.add_argument("--replace", action="store_true", help="以事务式目录替换现有个人数据")
    return parser


def _status(store: Store) -> Dict[str, Any]:
    if not store.is_initialized():
        return {
            "initialized": False,
            "home": str(store.home),
            "next_action": "运行 setup；无需手工创建或编辑配置文件。",
        }
    state = store.require_initialized()
    profile = load_profile(store)
    projects = list_projects(store)
    events = load_events(store)
    knowledge_sources = None  # type: Optional[int]
    knowledge_materialized_sources = None  # type: Optional[int]
    knowledge_placeholder_sources = None  # type: Optional[int]
    knowledge_storage_files = None  # type: Optional[int]
    knowledge_status = "ok"
    knowledge_errors = []  # type: List[Dict[str, Any]]
    try:
        listing = _call_knowledge(
            _knowledge_api()["list"],
            data_dir=str(store.home),
        )
        sources = listing.get("sources")
        if not isinstance(sources, list):
            raise ExperienceLoopError("Knowledge Lens 来源列表格式无效。")
        materialized = 0
        placeholders = 0
        for source in sources:
            if not isinstance(source, dict):
                raise ExperienceLoopError("Knowledge Lens 来源条目格式无效。")
            if source.get("current_revision_id"):
                chunk_count = source.get("chunk_count")
                if (
                    not isinstance(chunk_count, int)
                    or isinstance(chunk_count, bool)
                    or chunk_count <= 0
                ):
                    raise ExperienceLoopError(
                        "Knowledge Lens 来源存在修订但没有可用正文索引；请运行 doctor。"
                    )
                materialized += 1
            else:
                placeholders += 1
        knowledge_sources = len(sources)
        knowledge_materialized_sources = materialized
        knowledge_placeholder_sources = placeholders
    except ExperienceLoopError as exc:
        knowledge_status = "unavailable"
        knowledge_errors.append({"area": "sources", "message": exc.message, "code": exc.code})

    try:
        if store.knowledge_dir.exists():
            knowledge_storage_files = sum(
                1 for path in store.knowledge_dir.rglob("*") if path.is_file()
            )
        else:
            knowledge_storage_files = 0
    except OSError as exc:
        knowledge_status = "partial" if knowledge_status == "ok" else "unavailable"
        knowledge_errors.append({"area": "storage", "message": str(exc), "code": EXIT_IO})

    result = {
        "initialized": True,
        "home": str(store.home),
        "schema_version": state["schema_version"],
        "mode": profile["mode"],
        "profile_customized": profile.get("customized", False),
        "privacy": profile.get("privacy", "normal"),
        "projects": projects["count"],
        "ledger_events": len(events),
        "knowledge_status": knowledge_status,
        "knowledge_sources": knowledge_sources,
        "knowledge_materialized_sources": knowledge_materialized_sources,
        "knowledge_placeholder_sources": knowledge_placeholder_sources,
        "knowledge_storage_files": knowledge_storage_files,
        "updated_at": state.get("updated_at"),
    }
    if knowledge_errors:
        result["knowledge_errors"] = knowledge_errors
    return result


def _check(name: str, status: str, message: str, **details: Any) -> Dict[str, Any]:
    value = {"name": name, "status": status, "message": message}
    if details:
        value["details"] = details
    return value


def _doctor(store: Store, repair: bool, deep: bool = False) -> Dict[str, Any]:
    checks = []
    checks.append(_check(
        "python",
        "pass" if sys.version_info >= (3, 9) else "fail",
        "Python %s.%s.%s" % sys.version_info[:3],
        required=">=3.9",
    ))
    try:
        probe_database = sqlite3.connect(":memory:")
        try:
            probe_database.execute("CREATE VIRTUAL TABLE experience_loop_fts_probe USING fts5(value)")
        finally:
            probe_database.close()
        checks.append(_check("sqlite-fts5", "pass", "SQLite FTS5 可用。"))
    except sqlite3.Error as exc:
        checks.append(
            _check(
                "sqlite-fts5",
                "warning",
                "SQLite FTS5 不可用；Knowledge Lens 将使用较慢的本地词法/CJK n-gram 回退。",
                reason=str(exc),
            )
        )
    if not store.is_initialized():
        checks.append(_check("initialized", "fail", "尚未初始化；请运行 setup。", home=str(store.home)))
        return {"ok": False, "repaired": False, "checks": checks}

    repaired = []
    try:
        store.require_initialized()
        checks.append(_check("state", "pass", "状态文件与 schema 有效。", schema_version=SCHEMA_VERSION))
    except ExperienceLoopError as exc:
        checks.append(_check("state", "fail", exc.message))
        return {"ok": False, "repaired": False, "checks": checks}

    if repair:
        before = {
            "profile": store.profile_path.exists(),
            "projects_index": store.projects_index_path.exists(),
            "ledger": store.ledger_path.exists(),
        }
        store.initialize()
        if not store.profile_path.exists():
            configure_profile(store)
        for key, existed in before.items():
            if not existed:
                repaired.append(key)
        store.harden_known_permissions(deep=True)

    try:
        validate_profile(load_profile(store))
        checks.append(_check("profile", "pass", "个人画像有效。"))
    except ExperienceLoopError as exc:
        checks.append(_check("profile", "fail", exc.message))
    try:
        store.load_projects_index()
        checks.append(_check("projects", "pass", "项目索引有效。"))
    except ExperienceLoopError as exc:
        checks.append(_check("projects", "fail", exc.message))
    try:
        load_events(store)
        checks.append(_check("ledger", "pass", "经验账本有效。"))
    except ExperienceLoopError as exc:
        checks.append(_check("ledger", "fail", exc.message))

    try:
        with tempfile.NamedTemporaryFile(prefix=".doctor-", dir=str(store.home), delete=False) as handle:
            probe = Path(handle.name)
            handle.write(b"ok")
            handle.flush()
            os.fsync(handle.fileno())
        probe.unlink()
        checks.append(_check("writable", "pass", "个人数据目录可原子写入。"))
    except OSError as exc:
        checks.append(_check("writable", "fail", "个人数据目录不可写。", reason=str(exc)))

    if os.name == "nt":
        checks.append(
            _check(
                "private-permissions",
                "warning",
                "Windows 不使用 POSIX 权限位；本检查未执行 ACL 深度审计，请确保个人数据目录只对预期账户开放。",
                inspected="filesystem layout only",
            )
        )
    else:
        permission_issues = store.permission_issues(deep=deep)
        checks.append(
            _check(
                "private-permissions",
                "fail" if permission_issues else "pass",
                (
                    "部分个人数据允许组内或其他用户访问；运行 doctor --repair 收紧权限。"
                    if permission_issues
                    else "个人数据目录和敏感文件权限已收紧。"
                ),
                issues=permission_issues[:100],
            )
        )

    try:
        knowledge_api = _knowledge_api()
        integrity = _call_knowledge(
            knowledge_api["integrity"], data_dir=str(store.home), deep=deep
        )
        if integrity.get("ok"):
            checks.append(
                _check(
                    "knowledge",
                    "pass",
                    "Knowledge Lens 数据库、对象和索引一致。",
                    integrity=integrity,
                )
            )
        else:
            checks.append(
                _check(
                    "knowledge",
                    "fail",
                    "Knowledge Lens 完整性检查失败；请根据错误重新提供资料或重建索引。",
                    integrity=integrity,
                )
            )
    except DependencyError as exc:
        checks.append(_check("knowledge", "warning", exc.message))
    except ExperienceLoopError as exc:
        checks.append(_check("knowledge", "fail", exc.message))
    try:
        from .extractors import pdf_parser_info

        parser_info = pdf_parser_info()
        checks.append(
            _check(
                "pdf-parser",
                "pass" if parser_info.get("available") else "warning",
                (
                    "固定版本、哈希校验的离线 PDF 文本解析器可用。"
                    if parser_info.get("available")
                    else "PDF 解析器不可用；Markdown、TXT、HTML、EPUB 与 DOCX 不受影响。"
                ),
                parser=parser_info,
            )
        )
    except Exception as exc:
        checks.append(
            _check(
                "pdf-parser",
                "warning",
                "PDF 解析器不可用；Markdown、TXT、HTML、EPUB 与 DOCX 不受影响。",
                reason=str(exc),
            )
        )
    ok = not any(item["status"] == "fail" for item in checks)
    return {"ok": ok, "repaired": bool(repaired), "repaired_items": repaired, "checks": checks}


def _knowledge_api() -> Dict[str, Any]:
    try:
        from .knowledge import (
            add_sources,
            bind_source,
            inspect_source,
            inspect_concept_card,
            list_application_evidence,
            list_concept_cards,
            list_sources,
            integrity_check,
            query_sources,
            record_application_evidence,
            reindex_source,
            remove_concept_card,
            remove_source,
            search_concept_cards,
            upsert_concept_card,
        )
    except ImportError as exc:
        if exc.name in {"experience_loop_lib.knowledge", "%s.knowledge" % __package__}:
            raise DependencyError("Knowledge Lens 模块未安装；核心项目与经验账本仍可使用。") from exc
        raise DependencyError("Knowledge Lens 缺少运行依赖：%s" % (exc.name or str(exc))) from exc
    def locked(function: Any) -> Any:
        def call(*args: Any, **kwargs: Any) -> Any:
            data_dir = kwargs.get("data_dir")
            if not isinstance(data_dir, str) or not data_dir:
                raise ExperienceLoopError("Knowledge Lens 调用缺少 data_dir。")
            runtime_store = Store(data_dir)
            with runtime_store.lock():
                result = function(*args, **kwargs)
                runtime_store.harden_known_permissions(
                    deep=function.__name__ in {"add_sources", "reindex_source"}
                )
                return result

        return call

    return {
        "add": locked(add_sources),
        "list": locked(list_sources),
        "query": locked(query_sources),
        "inspect": locked(inspect_source),
        "bind": locked(bind_source),
        "remove": locked(remove_source),
        "reindex": locked(reindex_source),
        "integrity": locked(integrity_check),
        "concept_upsert": locked(upsert_concept_card),
        "concept_list": locked(list_concept_cards),
        "concept_search": locked(search_concept_cards),
        "concept_inspect": locked(inspect_concept_card),
        "concept_remove": locked(remove_concept_card),
        "application_record": locked(record_application_evidence),
        "application_list": locked(list_application_evidence),
    }


def _call_knowledge(function: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except ValueError as exc:
        raise ExperienceLoopError(str(exc)) from exc
    except Exception as exc:
        if any(base.__name__ == "KnowledgeError" for base in exc.__class__.__mro__):
            raise ExperienceLoopError(str(exc)) from exc
        raise


def _dispatch(namespace: argparse.Namespace, store: Store) -> Dict[str, Any]:
    command = namespace.command
    if command == "setup":
        already_initialized = store.is_initialized()
        profile = configure_profile(
            store,
            name=namespace.name,
            role=namespace.role,
            experience_level=namespace.experience_level,
            responsibilities=namespace.responsibility,
            domains=namespace.domain,
            goals=namespace.goal,
            learning_focus=namespace.learning_focus,
            explanation_style=namespace.explanation_style,
            guidance_preference=namespace.guidance_preference,
            delivery_context=namespace.delivery_context,
            mode=namespace.mode,
            privacy=namespace.privacy,
        )
        result = {
            "initialized": True,
            "already_initialized": already_initialized,
            "home": str(store.home),
            "profile": profile,
            "next_actions": (
                [] if already_initialized else ["offer_short_tutorial"]
            ),
            "message": (
                "Experience Loop 已更新；保留现有初始化状态，不重复新手教学。"
                if already_initialized
                else "Experience Loop 已可用；画像字段均可选，下一步只需询问是否需要简短教学。"
            ),
        }
        if namespace.project:
            result["project"] = scan_project(
                store,
                namespace.project,
                content_access_confirmed=namespace.confirm_content_access,
            )
        return result
    if command == "status":
        return _status(store)
    if command == "profile":
        store.require_initialized()
        if namespace.profile_command == "show":
            return {"profile": profile_for_display(load_profile(store))}
        profile = configure_profile(
            store,
            name=namespace.name,
            clear_name=namespace.clear_name,
            role=namespace.role,
            reset_role=namespace.reset_role,
            experience_level=namespace.experience_level,
            clear_experience_level=namespace.clear_experience_level,
            responsibilities=namespace.responsibility,
            replace_responsibilities=namespace.replace_responsibilities,
            clear_responsibilities=namespace.clear_responsibilities,
            domains=namespace.domain,
            replace_domains=namespace.replace_domains,
            clear_domains=namespace.clear_domains,
            goals=namespace.goal,
            replace_goals=namespace.replace_goals,
            clear_goals=namespace.clear_goals,
            learning_focus=namespace.learning_focus,
            replace_learning_focus=namespace.replace_learning_focus,
            clear_learning_focus=namespace.clear_learning_focus,
            explanation_style=namespace.explanation_style,
            clear_explanation_style=namespace.clear_explanation_style,
            guidance_preference=namespace.guidance_preference,
            clear_guidance_preference=namespace.clear_guidance_preference,
            delivery_context=namespace.delivery_context,
            clear_delivery_context=namespace.clear_delivery_context,
            mode=namespace.mode,
            privacy=namespace.privacy,
        )
        return {"updated": True, "profile": profile}
    if command == "doctor":
        return _doctor(store, namespace.repair, namespace.deep)
    if command == "mode":
        if namespace.value is None and not store.is_initialized():
            profile = default_profile()
            persisted = False
        elif namespace.value is not None:
            profile = set_mode(store, namespace.value)
            persisted = True
        else:
            store.require_initialized()
            profile = load_profile_controls(store)
            persisted = True
        return {
            "mode": profile["mode"],
            "records_learning_events": profile["mode"] != "off",
            "profile_customized": bool(profile.get("customized")),
            "privacy": profile.get("privacy", "normal"),
            "persisted": persisted,
            "home": str(store.home),
            "message": "当前模式：%s" % profile["mode"],
        }
    if command == "project":
        if namespace.project_command == "scan":
            return scan_project(
                store,
                namespace.path,
                name=namespace.name,
                max_files=namespace.max_files,
                max_total_bytes=namespace.max_total_bytes,
                max_file_bytes=namespace.max_file_bytes,
                content_access_confirmed=namespace.confirm_content_access,
                adopt_project_id=namespace.adopt_project,
            )
        if namespace.project_command == "list":
            return list_projects(store)
        if namespace.project_command == "inspect":
            return get_project(store, namespace.project_id)
        if namespace.project_command == "annotate":
            architecture_notes = namespace.architecture_note
            learning_opportunities = namespace.learning_opportunity
            verification_notes = namespace.verification_note
            replace = namespace.replace
            if namespace.clear_architecture_notes:
                if architecture_notes:
                    raise ExperienceLoopError(
                        "--architecture-note 与 --clear-architecture-notes 不能同时使用。"
                    )
                architecture_notes = []
                replace = True
            if namespace.clear_learning_opportunities:
                if learning_opportunities:
                    raise ExperienceLoopError(
                        "--learning-opportunity 与 --clear-learning-opportunities 不能同时使用。"
                    )
                learning_opportunities = []
                replace = True
            if namespace.clear_verification_notes:
                if verification_notes:
                    raise ExperienceLoopError(
                        "--verification-note 与 --clear-verification-notes 不能同时使用。"
                    )
                verification_notes = []
                replace = True
            return annotate_project(
                store,
                namespace.project_id,
                architecture_notes=architecture_notes,
                learning_opportunities=learning_opportunities,
                verification_notes=verification_notes,
                replace=replace,
            )
        project_record = get_project(store, namespace.project_id)
        if not namespace.yes:
            return {
                "removed": False,
                "requires_confirmation": True,
                "project_id": namespace.project_id,
                "project_name": project_record.get("name"),
                "impact": (
                    "仅删除项目画像和项目索引；经验账本、Knowledge Lens 资料及历史引用保留。"
                ),
                "next_command": "project remove %s --yes" % namespace.project_id,
            }
        return remove_project(store, namespace.project_id)
    if command == "ledger":
        if namespace.ledger_command == "record":
            return record_event(
                store,
                kind=namespace.kind,
                summary=namespace.summary,
                project_id=namespace.project,
                evidence=namespace.evidence,
                concepts=namespace.concept,
                capability=namespace.capability,
                independence=namespace.independence,
                outcome=namespace.outcome,
                confidence=namespace.confidence,
                tags=namespace.tag,
                prior_event_id=namespace.prior_event,
                context_difference=namespace.context_difference,
            )
        return review_events(store, project_id=namespace.project, limit=namespace.limit, since_days=namespace.since_days)
    if command == "knowledge":
        store.require_initialized()
        api = _knowledge_api()
        data_dir = str(store.home)
        privacy = load_profile(store).get("privacy", "normal")
        if namespace.knowledge_command == "add":
            if privacy == "metadata-only":
                raise ExperienceLoopError(
                    "metadata-only 隐私级别禁止读取资料内容；请先明确切换隐私级别。",
                    EXIT_OPERATION_FAILED,
                )
            if privacy == "restricted" and not namespace.confirm_content_access:
                raise ExperienceLoopError(
                    "restricted 隐私级别要求用户明确确认本次资料读取；确认后添加 --confirm-content-access。",
                    EXIT_OPERATION_FAILED,
                )
            if namespace.project:
                get_project(store, namespace.project)
            return _call_knowledge(
                api["add"], namespace.paths, data_dir=data_dir, project_id=namespace.project,
                recursive=not namespace.no_recursive,
            )
        if namespace.knowledge_command == "list":
            return _call_knowledge(
                api["list"], data_dir=data_dir, project_id=namespace.project,
                include_removed=namespace.include_removed,
            )
        if namespace.knowledge_command == "query":
            if privacy == "metadata-only":
                raise ExperienceLoopError(
                    "metadata-only 隐私级别禁止取回原文；请使用 knowledge concept list/inspect，或先明确切换隐私级别。",
                    EXIT_OPERATION_FAILED,
                )
            if privacy == "restricted" and not namespace.confirm_content_access:
                raise ExperienceLoopError(
                    "restricted 隐私级别要求用户明确确认本次原文检索；确认后添加 --confirm-content-access。",
                    EXIT_OPERATION_FAILED,
                )
            return _call_knowledge(
                api["query"], namespace.query, data_dir=data_dir, project_id=namespace.project,
                top_k=namespace.top_k, source_ids=namespace.source or None,
            )
        if namespace.knowledge_command == "inspect":
            if privacy == "metadata-only" and namespace.include_chunks:
                raise ExperienceLoopError(
                    "metadata-only 隐私级别只允许查看资料元数据，不能返回原文块。",
                    EXIT_OPERATION_FAILED,
                )
            if (
                privacy == "restricted"
                and namespace.include_chunks
                and not namespace.confirm_content_access
            ):
                raise ExperienceLoopError(
                    "restricted 隐私级别要求用户明确确认本次原文块读取；确认后添加 --confirm-content-access。",
                    EXIT_OPERATION_FAILED,
                )
            return _call_knowledge(
                api["inspect"], namespace.source_id, data_dir=data_dir,
                include_chunks=namespace.include_chunks, chunk_limit=namespace.chunk_limit,
            )
        if namespace.knowledge_command == "bind":
            get_project(store, namespace.project_id)
            return _call_knowledge(
                api["bind"], namespace.source_id, namespace.project_id,
                data_dir=data_dir, note=namespace.note,
            )
        if namespace.knowledge_command == "remove":
            if namespace.purge and not namespace.yes:
                source = _call_knowledge(
                    api["inspect"],
                    namespace.source_id,
                    data_dir=data_dir,
                    include_chunks=False,
                )
                return {
                    "purged": False,
                    "requires_confirmation": True,
                    "source": source.get("source"),
                    "impact": (
                        "将删除资料的索引、修订、引用证据和仅由该资料使用的本地源对象；"
                        "相关概念卡会失去证据或被级联删除。"
                    ),
                    "next_command": "knowledge remove %s --purge --yes"
                    % namespace.source_id,
                }
            return _call_knowledge(api["remove"], namespace.source_id, data_dir=data_dir, purge=namespace.purge)
        if namespace.knowledge_command == "reindex":
            if privacy == "metadata-only":
                raise ExperienceLoopError(
                    "metadata-only 隐私级别禁止重新读取原资料；请先明确切换隐私级别。",
                    EXIT_OPERATION_FAILED,
                )
            if privacy == "restricted" and not namespace.confirm_content_access:
                raise ExperienceLoopError(
                    "restricted 隐私级别要求用户明确确认本次原资料重建；确认后添加 --confirm-content-access。",
                    EXIT_OPERATION_FAILED,
                )
            return _call_knowledge(api["reindex"], namespace.source_id, data_dir=data_dir)
        if namespace.knowledge_command == "concept":
            if namespace.concept_command == "upsert":
                if namespace.project:
                    get_project(store, namespace.project)
                return _call_knowledge(
                    api["concept_upsert"],
                    namespace.title,
                    namespace.thesis,
                    namespace.citation,
                    data_dir=data_dir,
                    concept_id=namespace.concept_id,
                    project_id=namespace.project,
                    status=namespace.status,
                    applies_when=namespace.applies_when,
                    does_not_apply_when=namespace.does_not_apply_when,
                    common_misuses=namespace.common_misuse,
                    decision_triggers=namespace.decision_trigger,
                    engineering_questions=namespace.engineering_question,
                    tags=namespace.tag,
                )
            if namespace.concept_command == "list":
                if namespace.project:
                    get_project(store, namespace.project)
                return _call_knowledge(
                    api["concept_list"],
                    data_dir=data_dir,
                    project_id=namespace.project,
                    source_id=namespace.source,
                    include_retired=namespace.include_retired,
                )
            if namespace.concept_command == "search":
                if namespace.project:
                    get_project(store, namespace.project)
                return _call_knowledge(
                    api["concept_search"],
                    namespace.query,
                    data_dir=data_dir,
                    project_id=namespace.project,
                    source_id=namespace.source,
                    limit=namespace.limit,
                    include_retired=namespace.include_retired,
                )
            if namespace.concept_command == "inspect":
                return _call_knowledge(
                    api["concept_inspect"],
                    namespace.concept_id,
                    data_dir=data_dir,
                    application_limit=namespace.application_limit,
                )
            if namespace.purge and not namespace.yes:
                concept = _call_knowledge(
                    api["concept_inspect"],
                    namespace.concept_id,
                    data_dir=data_dir,
                    application_limit=1,
                )
                return {
                    "purged": False,
                    "requires_confirmation": True,
                    "card": concept.get("card"),
                    "impact": "将永久删除概念卡及其全部真实应用记录；原始资料仍保留。",
                    "next_command": "knowledge concept remove %s --purge --yes"
                    % namespace.concept_id,
                    "untrusted_content": True,
                    "usage_notice": concept.get("usage_notice"),
                }
            return _call_knowledge(
                api["concept_remove"],
                namespace.concept_id,
                data_dir=data_dir,
                purge=namespace.purge,
            )
        if namespace.knowledge_command == "application":
            if namespace.application_command == "record":
                if namespace.project:
                    get_project(store, namespace.project)
                return _call_knowledge(
                    api["application_record"],
                    namespace.concept_id,
                    situation=namespace.situation,
                    decision=namespace.decision,
                    outcome=namespace.outcome,
                    data_dir=data_dir,
                    project_id=namespace.project,
                    evidence=namespace.evidence,
                    independence=namespace.independence,
                )
            if namespace.project:
                get_project(store, namespace.project)
            return _call_knowledge(
                api["application_list"],
                data_dir=data_dir,
                concept_id=namespace.concept,
                project_id=namespace.project,
                limit=namespace.limit,
            )
        raise ExperienceLoopError("未实现的 knowledge 子命令。")
    if command == "export":
        return export_archive(
            store,
            namespace.destination,
            include_sources=namespace.include_sources,
            force=namespace.force,
        )
    if command == "import":
        return import_archive(store, namespace.source, replace=namespace.replace)
    raise ExperienceLoopError("未实现的命令：%s" % command)


def _emit(payload: Dict[str, Any], json_mode: bool, stream: Any = sys.stdout) -> None:
    if json_mode:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return
    data = payload.get("data") if payload.get("ok") else None
    if isinstance(data, dict) and data.get("message"):
        stream.write(str(data["message"]) + "\n")
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _result_exit_code(data: Any) -> int:
    if not isinstance(data, dict) or data.get("ok") is not False:
        return EXIT_OK
    successes = 0
    for key in ("added", "restored", "revised", "unchanged", "updated", "removed"):
        value = data.get(key)
        if isinstance(value, list):
            successes += len(value)
        elif isinstance(value, int) and not isinstance(value, bool):
            successes += max(0, value)
    return EXIT_PARTIAL if successes else EXIT_OPERATION_FAILED


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in raw
    try:
        cleaned, home, json_mode = _extract_global_options(raw)
        parser = _parser()
        namespace = parser.parse_args(cleaned)
        namespace.home = home
        namespace.json = json_mode
        store = Store(home)
        data = _dispatch(namespace, store)
        exit_code = _result_exit_code(data)
        _emit({"ok": exit_code == EXIT_OK, "command": namespace.command, "data": data}, json_mode)
        return exit_code
    except ExperienceLoopError as exc:
        payload = {"ok": False, "error": {"message": exc.message, "code": exc.code, "details": exc.details}}
        _emit(payload, json_mode, sys.stderr)
        return exc.code
    except OSError as exc:
        payload = {"ok": False, "error": {"message": str(exc), "code": EXIT_IO, "type": "OSError"}}
        _emit(payload, json_mode, sys.stderr)
        return EXIT_IO
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception as exc:
        payload = {
            "ok": False,
            "error": {"message": "未预期错误：%s" % exc, "code": EXIT_UNEXPECTED, "type": exc.__class__.__name__},
        }
        _emit(payload, json_mode, sys.stderr)
        return EXIT_UNEXPECTED
