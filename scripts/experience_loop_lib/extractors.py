"""Safe, dependency-light document extraction for Experience Loop.

The module deliberately treats every byte from a source document as untrusted
data.  It never evaluates document content, follows links, loads remote
resources, or interprets embedded instructions as commands.
"""

from __future__ import annotations

import hashlib
import html
import importlib
import json
import os
import posixpath
import re
import sys
import zipfile
import zlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


SUPPORTED_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".html",
    ".htm",
    ".epub",
    ".docx",
    ".pdf",
}

DEFAULT_MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10_000
MAX_ARCHIVE_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 256 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250
MAX_PDF_PAGES = 20_000
MAX_EXTRACTED_CHARS = 100 * 1024 * 1024
PDF_LOW_TEXT_COVERAGE = 0.80
_PYPDF_INFO: Optional[Dict[str, Any]] = None


class ExtractionError(RuntimeError):
    """A source could not be safely converted to text."""


class UnsupportedFormatError(ExtractionError):
    """The source extension is not supported."""


class UnsafeArchiveError(ExtractionError):
    """A compressed document violated an archive safety limit."""


@dataclass(frozen=True)
class ExtractedBlock:
    """A contiguous text block and its exact source locator."""

    text: str
    locator: Dict[str, Any]
    heading: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "locator": dict(self.locator),
            "heading": self.heading,
        }


@dataclass
class ExtractedDocument:
    """Normalized extraction result used by the local knowledge index."""

    title: str
    media_type: str
    blocks: List[ExtractedBlock]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "media_type": self.media_type,
            "blocks": [block.to_dict() for block in self.blocks],
            "metadata": dict(self.metadata),
        }


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a regular file without loading it at once."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def extract_document(
    path: Path,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    format_hint: Optional[str] = None,
) -> ExtractedDocument:
    """Extract a supported local document using a format-specific safe reader."""

    source = Path(path).expanduser()
    try:
        resolved = source.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ExtractionError("资料不存在或无法访问：{0}".format(source)) from exc
    if not resolved.is_file():
        raise ExtractionError("资料路径不是普通文件：{0}".format(resolved))
    size = resolved.stat().st_size
    if size > max_file_bytes:
        raise ExtractionError(
            "资料大小 {0} 字节，超过安全上限 {1} 字节：{2}".format(
                size, max_file_bytes, resolved
            )
        )

    extension = (format_hint or resolved.suffix).lower()
    if extension and not extension.startswith("."):
        extension = "." + extension
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            "不支持 {0}；当前支持：{1}".format(
                extension or "无扩展名文件", ", ".join(sorted(SUPPORTED_EXTENSIONS))
            )
        )

    if extension in {".md", ".markdown", ".txt", ".rst"}:
        return _extract_text_document(resolved, extension)
    if extension in {".html", ".htm"}:
        return _extract_html_document(resolved)
    if extension == ".epub":
        return _extract_epub_document(resolved)
    if extension == ".docx":
        return _extract_docx_document(resolved)
    if extension == ".pdf":
        return _extract_pdf_document(resolved)
    raise UnsupportedFormatError("没有可用的解析器：{0}".format(extension))


def chunk_document(
    document: ExtractedDocument,
    *,
    max_chars: int = 1_800,
    overlap_chars: int = 160,
) -> List[Dict[str, Any]]:
    """Create retrieval chunks while retaining exact start/end locators."""

    if max_chars < 300:
        raise ValueError("max_chars 不能小于 300")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars 必须大于等于 0 且小于 max_chars")

    pieces: List[Tuple[str, Dict[str, Any], Optional[str]]] = []
    for block in document.blocks:
        text = _clean_text(block.text)
        if not text:
            continue
        if len(text) <= max_chars:
            pieces.append((text, dict(block.locator), block.heading))
            continue
        for piece_text, char_start, char_end in _split_long_text(
            text, max_chars=max_chars, overlap_chars=overlap_chars
        ):
            locator = dict(block.locator)
            locator["char_start"] = char_start
            locator["char_end"] = char_end
            pieces.append((piece_text, locator, block.heading))

    chunks: List[Dict[str, Any]] = []
    pending: List[Tuple[str, Dict[str, Any], Optional[str]]] = []
    pending_length = 0

    def flush() -> None:
        nonlocal pending, pending_length
        if not pending:
            return
        texts = [item[0] for item in pending]
        first_locator = pending[0][1]
        last_locator = pending[-1][1]
        locator: Dict[str, Any]
        if len(pending) == 1:
            locator = dict(first_locator)
        else:
            locator = {
                "type": "span",
                "start": dict(first_locator),
                "end": dict(last_locator),
            }
        heading = next(
            (item[2] for item in reversed(pending) if item[2]), None
        )
        joined = "\n\n".join(texts)
        chunks.append(
            {
                "ordinal": len(chunks),
                "text": joined,
                "locator": locator,
                "heading": heading,
                "char_count": len(joined),
            }
        )
        pending = []
        pending_length = 0

    for piece in pieces:
        separator_length = 2 if pending else 0
        heading_changed = bool(pending and piece[2] != pending[-1][2])
        locator_boundary = bool(
            pending and _locator_boundary_requires_flush(pending[-1][1], piece[1])
        )
        if pending and (
            heading_changed
            or locator_boundary
            or pending_length + separator_length + len(piece[0]) > max_chars
        ):
            flush()
        pending.append(piece)
        pending_length += (2 if len(pending) > 1 else 0) + len(piece[0])
        if len(piece[0]) >= int(max_chars * 0.8):
            flush()
    flush()
    return chunks


def _locator_boundary_requires_flush(
    previous: Dict[str, Any],
    current: Dict[str, Any],
) -> bool:
    """Keep page/chapter citations exact instead of spanning unrelated units."""

    previous_type = previous.get("type")
    current_type = current.get("type")
    if previous_type != current_type:
        return True
    if current_type == "pdf":
        return previous.get("page") != current.get("page")
    if current_type == "epub":
        return (
            previous.get("chapter") != current.get("chapter")
            or previous.get("path") != current.get("path")
        )
    return False


def locator_label(locator: Dict[str, Any]) -> str:
    """Render a deterministic human-readable locator without inventing pages."""

    if locator.get("type") == "span":
        start = locator_label(locator.get("start") or {})
        end = locator_label(locator.get("end") or {})
        return start if start == end else "{0}–{1}".format(start, end)
    kind = locator.get("type")
    if kind == "pdf":
        return "第 {0} 页".format(locator.get("page"))
    if kind == "epub":
        chapter = locator.get("chapter")
        path = locator.get("path")
        line_start = locator.get("line_start")
        line_end = locator.get("line_end")
        line = _line_label(line_start, line_end)
        return "章节 {0}（{1}{2}）".format(chapter, path, line)
    if kind == "docx":
        return "第 {0} 段".format(locator.get("paragraph"))
    if kind == "html":
        return "HTML {0}".format(
            _line_label(locator.get("line_start"), locator.get("line_end")).strip()
        )
    if kind == "lines":
        return _line_label(locator.get("line_start"), locator.get("line_end")).strip()
    return "原文定位 {0}".format(
        html.escape(str(locator), quote=False)
    )


def _line_label(start: Any, end: Any) -> str:
    if start is None:
        return ""
    if end is None or end == start:
        return "第 {0} 行".format(start)
    return "第 {0}–{1} 行".format(start, end)


def _clean_text(value: str) -> str:
    value = value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _decode_text(data: bytes) -> str:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16", "utf-8-sig", "gb18030")
    else:
        encodings = ("utf-8-sig", "utf-8", "gb18030", "utf-16")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _split_long_text(
    text: str,
    *,
    max_chars: int,
    overlap_chars: int,
) -> Iterable[Tuple[str, int, int]]:
    start = 0
    text_length = len(text)
    while start < text_length:
        hard_end = min(start + max_chars, text_length)
        end = hard_end
        if hard_end < text_length:
            search_start = start + max(int(max_chars * 0.55), 1)
            candidates = [
                text.rfind("\n", search_start, hard_end),
                text.rfind("。", search_start, hard_end),
                text.rfind("！", search_start, hard_end),
                text.rfind("？", search_start, hard_end),
                text.rfind(". ", search_start, hard_end),
                text.rfind(" ", search_start, hard_end),
            ]
            best = max(candidates)
            if best >= search_start:
                end = best + 1
        piece = text[start:end].strip()
        if piece:
            yield piece, start, end
        if end >= text_length:
            break
        next_start = max(end - overlap_chars, start + 1)
        while next_start < end and text[next_start].isspace():
            next_start += 1
        start = next_start


def _extract_text_document(path: Path, extension: str) -> ExtractedDocument:
    text = _decode_text(path.read_bytes())
    blocks = _blocks_from_lines(text, markup=extension in {".md", ".markdown", ".rst"})
    return ExtractedDocument(
        title=path.stem,
        media_type={
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".rst": "text/x-rst",
            ".txt": "text/plain",
        }[extension],
        blocks=blocks,
        metadata={"source_content_trust": "untrusted"},
    )


def _blocks_from_lines(text: str, *, markup: bool) -> List[ExtractedBlock]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: List[ExtractedBlock] = []
    current: List[str] = []
    start_line = 1
    heading: Optional[str] = None
    rst_underline_lines = set()

    def flush(end_line: int) -> None:
        nonlocal current, start_line
        value = _clean_text("\n".join(current))
        if value:
            blocks.append(
                ExtractedBlock(
                    text=value,
                    locator={
                        "type": "lines",
                        "line_start": start_line,
                        "line_end": max(start_line, end_line),
                    },
                    heading=heading,
                )
            )
        current = []

    for index, line in enumerate(lines, start=1):
        if index in rst_underline_lines:
            start_line = index + 1
            continue
        stripped = line.strip()
        markdown_heading = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        rst_heading = (
            markup
            and index < len(lines)
            and stripped
            and re.match(r"^[=\-~`^\"'*+#_:]{3,}\s*$", lines[index].strip())
        )
        if markup and (markdown_heading or rst_heading):
            flush(index - 1)
            heading_text = (
                markdown_heading.group(1).strip() if markdown_heading else stripped
            )
            heading = heading_text
            blocks.append(
                ExtractedBlock(
                    text=heading_text,
                    locator={
                        "type": "lines",
                        "line_start": index,
                        "line_end": index + (1 if rst_heading else 0),
                    },
                    heading=heading,
                )
            )
            if rst_heading:
                rst_underline_lines.add(index + 1)
            continue
        if not stripped:
            flush(index - 1)
            start_line = index + 1
            continue
        if not current:
            start_line = index
        current.append(line)
    flush(len(lines))
    return blocks


class _SafeHTMLTextParser(HTMLParser):
    _BLOCK_TAGS = {
        "p",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "pre",
        "blockquote",
        "td",
        "th",
        "dt",
        "dd",
    }
    _IGNORED_TAGS = {"script", "style", "noscript", "svg", "math", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: List[ExtractedBlock] = []
        self.title: Optional[str] = None
        self._title_parts: List[str] = []
        self._in_title = False
        self._ignored_depth = 0
        self._active: List[Dict[str, Any]] = []
        self._loose: List[str] = []
        self._current_heading: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        del attrs
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag in self._BLOCK_TAGS:
            line, _ = self.getpos()
            self._active.append({"tag": tag, "start": line, "parts": []})
        elif tag == "br" and self._active:
            self._active[-1]["parts"].append("\n")

    def handle_startendtag(
        self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() != "br":
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = False
            title = _clean_text(" ".join(self._title_parts))
            if title:
                self.title = title
        if tag not in self._BLOCK_TAGS:
            return
        for reverse_index in range(len(self._active) - 1, -1, -1):
            if self._active[reverse_index]["tag"] == tag:
                item = self._active.pop(reverse_index)
                value = _clean_text("".join(item["parts"]))
                if not value:
                    return
                line, _ = self.getpos()
                if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
                    self._current_heading = value
                self.blocks.append(
                    ExtractedBlock(
                        text=value,
                        locator={
                            "type": "html",
                            "line_start": item["start"],
                            "line_end": line,
                            "element": tag,
                        },
                        heading=self._current_heading,
                    )
                )
                return

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
        if self._active:
            self._active[-1]["parts"].append(data)
        elif data.strip():
            self._loose.append(data)

    def finish(self) -> None:
        while self._active:
            item = self._active.pop()
            value = _clean_text("".join(item["parts"]))
            if value:
                self.blocks.append(
                    ExtractedBlock(
                        text=value,
                        locator={
                            "type": "html",
                            "line_start": item["start"],
                            "line_end": item["start"],
                            "element": item["tag"],
                        },
                        heading=self._current_heading,
                    )
                )
        loose = _clean_text(" ".join(self._loose))
        if loose and not self.blocks:
            self.blocks.append(
                ExtractedBlock(
                    text=loose,
                    locator={"type": "html", "line_start": 1, "line_end": 1},
                )
            )


def _parse_html(text: str) -> Tuple[Optional[str], List[ExtractedBlock]]:
    parser = _SafeHTMLTextParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        raise ExtractionError("HTML 结构无法解析：{0}".format(exc)) from exc
    parser.finish()
    return parser.title, parser.blocks


def _extract_html_document(path: Path) -> ExtractedDocument:
    title, blocks = _parse_html(_decode_text(path.read_bytes()))
    return ExtractedDocument(
        title=title or path.stem,
        media_type="text/html",
        blocks=blocks,
        metadata={"source_content_trust": "untrusted"},
    )


def _validate_archive(archive: zipfile.ZipFile, source: Path) -> Dict[str, zipfile.ZipInfo]:
    entries = archive.infolist()
    if len(entries) > MAX_ARCHIVE_ENTRIES:
        raise UnsafeArchiveError(
            "压缩资料包含 {0} 个条目，超过上限 {1}：{2}".format(
                len(entries), MAX_ARCHIVE_ENTRIES, source
            )
        )
    total_size = 0
    safe: Dict[str, zipfile.ZipInfo] = {}
    for info in entries:
        name = info.filename.replace("\\", "/")
        pure = PurePosixPath(name)
        if (
            not name
            or name.startswith("/")
            or "\\" in info.filename
            or any(part == ".." for part in pure.parts)
            or (pure.parts and ":" in pure.parts[0])
        ):
            raise UnsafeArchiveError("压缩资料含路径越界条目：{0}".format(info.filename))
        unix_mode = (info.external_attr >> 16) & 0xFFFF
        if (unix_mode & 0o170000) == 0o120000:
            raise UnsafeArchiveError("压缩资料含符号链接条目：{0}".format(info.filename))
        if info.flag_bits & 0x1:
            raise UnsafeArchiveError("不读取加密压缩条目：{0}".format(info.filename))
        if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
            raise UnsafeArchiveError("压缩条目解压后过大：{0}".format(info.filename))
        total_size += info.file_size
        if total_size > MAX_ARCHIVE_TOTAL_BYTES:
            raise UnsafeArchiveError("压缩资料解压总量超过安全上限：{0}".format(source))
        if info.compress_size == 0:
            ratio = info.file_size if info.file_size else 1
        else:
            ratio = info.file_size / info.compress_size
        if info.file_size > 1024 * 1024 and ratio > MAX_COMPRESSION_RATIO:
            raise UnsafeArchiveError(
                "压缩条目压缩比异常（疑似 zip bomb）：{0}".format(info.filename)
            )
        normalized_name = posixpath.normpath(name)
        if normalized_name in safe:
            raise UnsafeArchiveError(
                "压缩资料含规范化后重名条目：{0}".format(info.filename)
            )
        safe[normalized_name] = info
    return safe


def _read_archive_member(
    archive: zipfile.ZipFile,
    entries: Dict[str, zipfile.ZipInfo],
    member_name: str,
) -> bytes:
    normalized = posixpath.normpath(member_name.replace("\\", "/"))
    if normalized.startswith("../") or normalized == ".." or normalized.startswith("/"):
        raise UnsafeArchiveError("归档成员路径越界：{0}".format(member_name))
    info = entries.get(normalized)
    if info is None:
        raise ExtractionError("压缩资料缺少必要条目：{0}".format(normalized))
    try:
        with archive.open(info, "r") as stream:
            data = stream.read(MAX_ARCHIVE_MEMBER_BYTES + 1)
    except (OSError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        raise ExtractionError("归档成员损坏或无法解压：{0}".format(normalized)) from exc
    if len(data) > MAX_ARCHIVE_MEMBER_BYTES:
        raise UnsafeArchiveError("归档成员读取超过安全上限：{0}".format(normalized))
    return data


def _safe_xml(data: bytes, label: str) -> ElementTree.Element:
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", data, flags=re.IGNORECASE):
        raise UnsafeArchiveError("XML 含 DTD/ENTITY，已拒绝解析：{0}".format(label))
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ExtractionError("XML 无法解析（{0}）：{1}".format(label, exc)) from exc


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _extract_epub_document(path: Path) -> ExtractedDocument:
    try:
        archive = zipfile.ZipFile(str(path), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ExtractionError("EPUB 不是有效 ZIP 文档：{0}".format(path)) from exc
    with archive:
        entries = _validate_archive(archive, path)
        opf_path: Optional[str] = None
        if "META-INF/container.xml" in entries:
            container = _safe_xml(
                _read_archive_member(archive, entries, "META-INF/container.xml"),
                "META-INF/container.xml",
            )
            for element in container.iter():
                if _local_name(element.tag) == "rootfile":
                    candidate = element.attrib.get("full-path")
                    if candidate:
                        opf_path = posixpath.normpath(candidate)
                        break
        if not opf_path:
            opf_candidates = sorted(name for name in entries if name.lower().endswith(".opf"))
            if opf_candidates:
                opf_path = opf_candidates[0]
        if not opf_path:
            raise ExtractionError("EPUB 中找不到 package.opf")

        opf = _safe_xml(_read_archive_member(archive, entries, opf_path), opf_path)
        title: Optional[str] = None
        manifest: Dict[str, Tuple[str, str]] = {}
        spine_ids: List[str] = []
        for element in opf.iter():
            name = _local_name(element.tag)
            if name == "title" and not title and element.text:
                title = _clean_text(element.text)
            elif name == "item":
                item_id = element.attrib.get("id")
                href = element.attrib.get("href")
                if item_id and href:
                    manifest[item_id] = (href, element.attrib.get("media-type", ""))
            elif name == "itemref":
                item_ref = element.attrib.get("idref")
                if item_ref:
                    spine_ids.append(item_ref)

        opf_dir = posixpath.dirname(opf_path)
        chapter_paths: List[str] = []
        for item_id in spine_ids:
            item = manifest.get(item_id)
            if not item:
                continue
            href, media_type = item
            if media_type and media_type not in {"application/xhtml+xml", "text/html"}:
                continue
            parsed_href = urlsplit(href)
            if parsed_href.scheme or parsed_href.netloc:
                raise ExtractionError("EPUB 章节引用了外部资源，已拒绝加载：{0}".format(href))
            local_href = unquote(parsed_href.path)
            chapter_path = posixpath.normpath(posixpath.join(opf_dir, local_href))
            if chapter_path in entries and chapter_path not in chapter_paths:
                chapter_paths.append(chapter_path)
        if not chapter_paths:
            chapter_paths = sorted(
                name
                for name in entries
                if name.lower().endswith((".xhtml", ".html", ".htm"))
            )

        blocks: List[ExtractedBlock] = []
        extracted_chars = 0
        for chapter_index, chapter_path in enumerate(chapter_paths, start=1):
            chapter_text = _decode_text(_read_archive_member(archive, entries, chapter_path))
            chapter_title, chapter_blocks = _parse_html(chapter_text)
            for block in chapter_blocks:
                locator = {
                    "type": "epub",
                    "chapter": chapter_index,
                    "path": chapter_path,
                    "line_start": block.locator.get("line_start"),
                    "line_end": block.locator.get("line_end"),
                    "element": block.locator.get("element"),
                }
                block_heading = block.heading or chapter_title
                blocks.append(
                    ExtractedBlock(
                        text=block.text,
                        locator=locator,
                        heading=block_heading,
                    )
                )
                extracted_chars += len(block.text)
                if extracted_chars > MAX_EXTRACTED_CHARS:
                    raise ExtractionError("EPUB 提取文本超过安全上限：{0}".format(path))

    return ExtractedDocument(
        title=title or path.stem,
        media_type="application/epub+zip",
        blocks=blocks,
        metadata={
            "chapter_count": len(chapter_paths),
            "source_content_trust": "untrusted",
        },
    )


def _extract_docx_document(path: Path) -> ExtractedDocument:
    try:
        archive = zipfile.ZipFile(str(path), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ExtractionError("DOCX 不是有效 ZIP 文档：{0}".format(path)) from exc
    with archive:
        entries = _validate_archive(archive, path)
        document = _safe_xml(
            _read_archive_member(archive, entries, "word/document.xml"),
            "word/document.xml",
        )
        title: Optional[str] = None
        if "docProps/core.xml" in entries:
            core = _safe_xml(
                _read_archive_member(archive, entries, "docProps/core.xml"),
                "docProps/core.xml",
            )
            for element in core.iter():
                if _local_name(element.tag) == "title" and element.text:
                    title = _clean_text(element.text)
                    break

        blocks: List[ExtractedBlock] = []
        current_heading: Optional[str] = None
        paragraph_index = 0
        for paragraph in document.iter():
            if _local_name(paragraph.tag) != "p":
                continue
            paragraph_index += 1
            parts: List[str] = []
            style: Optional[str] = None
            for element in paragraph.iter():
                local = _local_name(element.tag)
                if local == "t" and element.text:
                    parts.append(element.text)
                elif local == "tab":
                    parts.append("\t")
                elif local in {"br", "cr"}:
                    parts.append("\n")
                elif local == "pStyle":
                    style = next(
                        (
                            value
                            for key, value in element.attrib.items()
                            if _local_name(key) == "val"
                        ),
                        None,
                    )
            value = _clean_text("".join(parts))
            if not value:
                continue
            normalized_style = (style or "").lower()
            if normalized_style.startswith(("heading", "title", "subtitle", "titre")):
                current_heading = value
            blocks.append(
                ExtractedBlock(
                    text=value,
                    locator={
                        "type": "docx",
                        "part": "word/document.xml",
                        "paragraph": paragraph_index,
                    },
                    heading=current_heading,
                )
            )

    return ExtractedDocument(
        title=title or path.stem,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        blocks=blocks,
        metadata={
            "paragraph_count": paragraph_index,
            "source_content_trust": "untrusted",
        },
    )


def _load_pypdf() -> Any:
    global _PYPDF_INFO
    cached = sys.modules.get("pypdf")
    if cached is not None and _PYPDF_INFO and _PYPDF_INFO.get("available"):
        if str(getattr(cached, "__version__", "unknown")) == str(
            _PYPDF_INFO.get("version")
        ):
            return cached
    module_path = Path(__file__).resolve()
    repository_root = module_path.parents[2]
    vendor_root = (repository_root / "vendor").resolve()
    manifest_path = vendor_root / "manifest.json"
    bundled_missing = False
    if not manifest_path.is_file():
        bundled_missing = True
    else:
        try:
            if manifest_path.stat().st_size > 1024 * 1024:
                raise ExtractionError("vendor/manifest.json 超过安全大小上限")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ExtractionError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExtractionError("vendor/manifest.json 无法校验") from exc
        packages = manifest.get("packages") if isinstance(manifest, dict) else None
        if not isinstance(packages, list):
            raise ExtractionError("vendor/manifest.json 的 packages 必须是数组")
        package = next(
            (
                item
                for item in (packages or [])
                if isinstance(item, dict) and str(item.get("name") or "").lower() == "pypdf"
            ),
            None,
        )
        if package is None:
            bundled_missing = True
        else:
            relative_file = str(package.get("file") or "").strip()
            expected_hash = str(package.get("sha256") or "").strip().lower()
            expected_version = str(package.get("version") or "").strip()
            if not relative_file:
                raise ExtractionError("pypdf vendor manifest 缺少 wheel 路径")
            try:
                wheel_candidate = (vendor_root / relative_file).resolve(strict=False)
                wheel_candidate.relative_to(vendor_root)
            except (OSError, RuntimeError, ValueError) as exc:
                raise ExtractionError("pypdf vendor wheel 路径越界") from exc
            if not wheel_candidate.is_file():
                bundled_missing = True
            else:
                wheel = wheel_candidate
            if not bundled_missing:
                if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                    raise ExtractionError("pypdf vendor manifest 的 SHA256 无效")
                actual_hash = sha256_file(wheel)
                if actual_hash != expected_hash:
                    raise ExtractionError(
                        "pypdf vendor wheel 完整性校验失败；拒绝回退到未固定的系统版本"
                    )
                dependency_wheels: List[Path] = []
                dependencies: List[Dict[str, Any]] = []
                if sys.version_info[:2] < (3, 11):
                    typing_package = _verified_vendor_package(
                        vendor_root,
                        packages or [],
                        "typing_extensions",
                    )
                    if typing_package is None:
                        raise ExtractionError(
                            "Python 3.9/3.10 需要发行包内经 manifest 校验的 "
                            "typing_extensions wheel；拒绝依赖未固定的系统环境"
                        )
                    dependency_wheels.append(typing_package["path"])
                    dependencies.append(
                        {
                            "name": "typing_extensions",
                            "version": typing_package["version"],
                            "path": str(typing_package["path"]),
                            "sha256": typing_package["sha256"],
                            "verified": True,
                        }
                    )
                module = _import_pypdf_wheel(wheel, dependency_wheels)
                actual_version = str(getattr(module, "__version__", "unknown"))
                if expected_version and actual_version != expected_version:
                    raise ExtractionError(
                        "pypdf vendor wheel 版本与 manifest 不一致：{0}!={1}".format(
                            actual_version, expected_version
                        )
                    )
                _PYPDF_INFO = {
                    "available": True,
                    "source": "bundled-verified-wheel",
                    "version": actual_version,
                    "path": str(wheel),
                    "sha256": actual_hash,
                    "verified": True,
                    "dependencies": dependencies,
                }
                return module

    if bundled_missing:
        try:
            module = importlib.import_module("pypdf")
        except ImportError:
            module = None
        if module is not None:
            _PYPDF_INFO = {
                "available": True,
                "source": "system-fallback",
                "version": str(getattr(module, "__version__", "unknown")),
                "path": str(getattr(module, "__file__", "")),
                "sha256": None,
                "verified": False,
            }
            return module

    _PYPDF_INFO = {
        "available": False,
        "source": "unavailable",
        "version": None,
        "path": None,
        "sha256": None,
        "verified": False,
    }
    raise ExtractionError(
        "PDF 解析器不可用：发行包未包含经 manifest 校验的 pypdf wheel，"
        "且当前 Python 环境没有 pypdf；其他格式不受影响。"
    )


def _verified_vendor_package(
    vendor_root: Path,
    packages: Sequence[Any],
    package_name: str,
) -> Optional[Dict[str, Any]]:
    normalized_name = package_name.lower().replace("-", "_")
    package = next(
        (
            item
            for item in packages
            if isinstance(item, dict)
            and str(item.get("name") or "").lower().replace("-", "_")
            == normalized_name
        ),
        None,
    )
    if package is None:
        return None
    relative_file = str(package.get("file") or "").strip()
    expected_hash = str(package.get("sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ExtractionError(
            "{0} vendor manifest 的 SHA256 无效".format(package_name)
        )
    try:
        wheel = (vendor_root / relative_file).resolve(strict=True)
        wheel.relative_to(vendor_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ExtractionError(
            "{0} vendor wheel 缺失、越界或无法访问".format(package_name)
        ) from exc
    actual_hash = sha256_file(wheel)
    if actual_hash != expected_hash:
        raise ExtractionError(
            "{0} vendor wheel 完整性校验失败".format(package_name)
        )
    return {
        "path": wheel,
        "version": str(package.get("version") or "unknown"),
        "sha256": actual_hash,
    }


def _import_pypdf_wheel(
    wheel: Path,
    dependency_wheels: Sequence[Path] = (),
) -> Any:
    wheel_text = str(wheel)
    dependency_texts = [str(path) for path in dependency_wheels]
    managed_prefixes = ("pypdf",) + (
        ("typing_extensions",) if dependency_texts else ()
    )
    previous_modules = {
        name: module
        for name, module in list(sys.modules.items())
        if any(name == prefix or name.startswith(prefix + ".") for prefix in managed_prefixes)
    }
    for name in previous_modules:
        sys.modules.pop(name, None)
    inserted_paths: List[str] = []
    for path_text in reversed([wheel_text] + dependency_texts):
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
            inserted_paths.append(path_text)
    importlib.invalidate_caches()
    try:
        module = importlib.import_module("pypdf")
        module_file = str(getattr(module, "__file__", ""))
        if not module_file.startswith(wheel_text):
            raise ImportError("pypdf 未从已校验 wheel 加载")
        if dependency_texts:
            dependency_module = sys.modules.get("typing_extensions")
            dependency_file = str(getattr(dependency_module, "__file__", ""))
            if not any(dependency_file.startswith(path_text) for path_text in dependency_texts):
                raise ImportError("typing_extensions 未从已校验 wheel 加载")
        return module
    except Exception as exc:
        for name in list(sys.modules):
            if any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in managed_prefixes
            ):
                sys.modules.pop(name, None)
        sys.modules.update(previous_modules)
        raise ExtractionError("已校验的 pypdf wheel 无法加载") from exc
    finally:
        for path_text in inserted_paths:
            try:
                sys.path.remove(path_text)
            except ValueError:
                pass


def pdf_parser_info() -> Dict[str, Any]:
    """Return deterministic parser provenance for doctor and diagnostics."""

    try:
        _load_pypdf()
    except ExtractionError as exc:
        result = dict(_PYPDF_INFO or {})
        result.setdefault("available", False)
        result.setdefault("source", "unavailable")
        result.setdefault("version", None)
        result.setdefault("path", None)
        result.setdefault("sha256", None)
        result.setdefault("verified", False)
        result["error"] = str(exc)
        return result
    return dict(_PYPDF_INFO or {})


def _extract_pdf_document(path: Path) -> ExtractedDocument:
    pypdf = _load_pypdf()
    try:
        reader = pypdf.PdfReader(str(path), strict=False)
    except Exception as exc:
        raise ExtractionError("PDF 无法打开：{0}".format(path)) from exc
    if getattr(reader, "is_encrypted", False):
        try:
            unlocked = reader.decrypt("")
        except Exception as exc:
            raise ExtractionError("PDF 已加密，且无法用空密码读取：{0}".format(path)) from exc
        if not unlocked:
            raise ExtractionError("PDF 已加密，请先解密后再添加：{0}".format(path))
    page_count = len(reader.pages)
    if page_count > MAX_PDF_PAGES:
        raise ExtractionError(
            "PDF 页数 {0} 超过安全上限 {1}：{2}".format(
                page_count, MAX_PDF_PAGES, path
            )
        )

    title: Optional[str] = None
    metadata = getattr(reader, "metadata", None)
    if metadata:
        try:
            title = _clean_text(str(metadata.get("/Title") or "")) or None
        except Exception:
            title = None
    blocks: List[ExtractedBlock] = []
    extracted_chars = 0
    blank_pages: List[int] = []
    failed_pages: List[int] = []
    for page_index in range(1, page_count + 1):
        try:
            page = reader.pages[page_index - 1]
            value = _clean_text(page.extract_text() or "")
        except Exception:
            # A damaged page must not discard text that was safely extracted from
            # the rest of a book.  The caller receives exact coverage metadata
            # and can decide whether OCR or a repaired copy is needed.
            failed_pages.append(page_index)
            continue
        if not value:
            blank_pages.append(page_index)
            continue
        blocks.append(
            ExtractedBlock(
                text=value,
                locator={"type": "pdf", "page": page_index},
                heading=None,
            )
        )
        extracted_chars += len(value)
        if extracted_chars > MAX_EXTRACTED_CHARS:
            raise ExtractionError("PDF 提取文本超过安全上限：{0}".format(path))

    text_page_count = len(blocks)
    coverage = (float(text_page_count) / float(page_count)) if page_count else 0.0
    warnings: List[str] = []
    if failed_pages:
        warnings.append(
            "{0} 页解析失败，已索引其余可用文本。".format(len(failed_pages))
        )
    if text_page_count and coverage < PDF_LOW_TEXT_COVERAGE:
        warnings.append(
            "PDF 文本覆盖率仅 {0:.1%}，可能包含扫描页；建议 OCR 后重新添加。".format(
                coverage
            )
        )
    extraction_status = "complete"
    if not text_page_count:
        extraction_status = "empty"
    elif failed_pages or coverage < PDF_LOW_TEXT_COVERAGE:
        extraction_status = "partial"

    return ExtractedDocument(
        title=title or path.stem,
        media_type="application/pdf",
        blocks=blocks,
        metadata={
            "page_count": page_count,
            "text_page_count": text_page_count,
            "blank_pages": blank_pages,
            "failed_pages": failed_pages,
            "coverage": round(coverage, 6),
            "extraction_status": extraction_status,
            "warnings": warnings,
            "source_content_trust": "untrusted",
        },
    )
