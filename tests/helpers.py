from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Optional


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "experience_loop.py"


def run_cli(
    home: Path,
    *args: str,
    cwd: Optional[Path] = None,
) -> subprocess.CompletedProcess[str]:
    """Run the public CLI with an isolated user environment and JSON output."""

    fake_user_home = home.parent / "isolated-user-home"
    fake_user_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(fake_user_home),
            "USERPROFILE": str(fake_user_home),
            "HOMEDRIVE": fake_user_home.drive,
            "HOMEPATH": str(fake_user_home)[len(fake_user_home.drive) :],
            "XDG_CONFIG_HOME": str(fake_user_home / ".config"),
            "APPDATA": str(fake_user_home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(fake_user_home / "AppData" / "Local"),
            "EXPERIENCE_LOOP_HOME": str(home),
            "PYTHONUTF8": "1",
        }
    )
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(CLI),
            *args,
            "--home",
            str(home),
            "--json",
        ],
        cwd=cwd or ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def payload(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """Decode the CLI JSON envelope while preserving useful failure context."""

    raw = result.stdout.strip() or result.stderr.strip()
    if not raw:
        raise AssertionError(
            "CLI produced no JSON output (exit={0}, stderr={1!r})".format(
                result.returncode, result.stderr
            )
        )
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            "CLI output is not JSON (exit={0}): stdout={1!r}, stderr={2!r}".format(
                result.returncode, result.stdout, result.stderr
            )
        ) from exc
    if not isinstance(value, dict):
        raise AssertionError("CLI JSON envelope must be an object: {0!r}".format(value))
    return value


def assert_ok(testcase: Any, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    value = payload(result)
    testcase.assertEqual(result.returncode, 0, result.stderr or result.stdout)
    testcase.assertTrue(value.get("ok"), value)
    testcase.assertIsInstance(value.get("data"), dict, value)
    return value["data"]


def tree_fingerprint(root: Path) -> dict[str, tuple[Any, ...]]:
    """Capture project content and metadata so a read-only scan is provable."""

    result: dict[str, tuple[Any, ...]] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            result[relative] = ("dir",)
        elif path.is_file():
            data = path.read_bytes()
            stat = path.stat()
            result[relative] = (
                "file",
                len(data),
                hashlib.sha256(data).hexdigest(),
                stat.st_mtime_ns,
            )
    return result


def write_minimal_pdf(path: Path, pages: Iterable[str]) -> None:
    """Write a tiny text PDF without relying on a test-only PDF dependency."""

    page_texts = list(pages)
    if not page_texts:
        raise ValueError("at least one page is required")
    font_id = 3 + len(page_texts) * 2
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            "<< /Type /Pages /Kids [{0}] /Count {1} >>".format(
                " ".join("{0} 0 R".format(3 + index * 2) for index in range(len(page_texts))),
                len(page_texts),
            )
        ).encode("ascii"),
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, text in enumerate(page_texts):
        page_id = 3 + index * 2
        content_id = page_id + 1
        escaped = (
            text.encode("ascii")
            .replace(b"\\", b"\\\\")
            .replace(b"(", b"\\(")
            .replace(b")", b"\\)")
        )
        stream = b"BT /F1 10 Tf 36 756 Td (" + escaped + b") Tj ET"
        objects[page_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 {0} 0 R >> >> /Contents {1} 0 R >>".format(
                font_id, content_id
            )
        ).encode("ascii")
        objects[content_id] = (
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (font_id + 1)
    for object_id in range(1, font_id + 1):
        offsets[object_id] = len(output)
        output.extend("{0} 0 obj\n".format(object_id).encode("ascii"))
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend("xref\n0 {0}\n".format(font_id + 1).encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for object_id in range(1, font_id + 1):
        output.extend("{0:010d} 00000 n \n".format(offsets[object_id]).encode("ascii"))
    output.extend(
        (
            "trailer\n<< /Size {0} /Root 1 0 R >>\nstartxref\n{1}\n%%EOF\n".format(
                font_id + 1, xref_offset
            )
        ).encode("ascii")
    )
    path.write_bytes(bytes(output))
