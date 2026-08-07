from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Optional
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "packaging" / "openai" / "hooks" / "session_start.py"


def invoke_hook(
    home: Path,
    cwd: Path,
    *,
    event: Optional[dict[str, Any]] = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["EXPERIENCE_LOOP_HOME"] = str(home)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    payload = (
        event
        if event is not None
        else {
            "session_id": "test-session",
            "hook_event_name": "SessionStart",
            "source": "startup",
            "cwd": str(cwd),
        }
    )
    return subprocess.run(
        [sys.executable, "-B", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env=environment,
    )


def run_hook(
    home: Path,
    cwd: Path,
    *,
    event: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    completed = invoke_hook(home, cwd, event=event)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    if not completed.stdout:
        return None
    return json.loads(completed.stdout)


def controls_payload(
    *,
    mode: str = "auto",
    scope: str = "explicit",
    privacy: str = "normal",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "default_mode": mode,
        "activation_scope": scope,
        "privacy": privacy,
        "profile_customized": False,
        "revision": 1,
        "created_at": "2026-08-07T00:00:00Z",
        "updated_at": "2026-08-07T00:00:00Z",
    }


def write_controls(
    home: Path,
    *,
    mode: str = "auto",
    scope: str = "explicit",
    privacy: str = "normal",
    payload: Any = None,
) -> None:
    home.mkdir(parents=True, exist_ok=True)
    value = controls_payload(mode=mode, scope=scope, privacy=privacy)
    if payload is not None:
        value = payload
    (home / "controls.json").write_text(json.dumps(value), encoding="utf-8")


class ActivationHookTests(unittest.TestCase):
    def test_missing_corrupt_explicit_and_off_controls_inject_nothing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-hook-") as raw:
            root = Path(raw)
            home = root / "home"
            workspace = root / "repo"
            workspace.mkdir()
            (workspace / ".git").mkdir()

            self.assertIsNone(run_hook(home, workspace))
            home.mkdir()
            (home / "controls.json").write_text("{broken", encoding="utf-8")
            completed = invoke_hook(home, workspace)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "")
            self.assertEqual(completed.stderr, "")
            (home / "controls.json").write_text("null\n", encoding="utf-8")
            self.assertIsNone(run_hook(home, workspace))
            write_controls(home, scope="explicit")
            self.assertIsNone(run_hook(home, workspace))
            write_controls(home, mode="off", scope="global")
            self.assertIsNone(run_hook(home, workspace))

    def test_controls_schema_is_strict_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-hook-schema-") as raw:
            root = Path(raw)
            home = root / "home"
            workspace = root / "repo"
            workspace.mkdir()
            (workspace / ".git").mkdir()
            valid = controls_payload(scope="global")

            invalid: dict[str, Any] = {
                "not-an-object": [],
                "unknown-field": {**valid, "profile_name": "must-not-be-read"},
                "invalid-schema-type": {**valid, "schema_version": True},
                "invalid-mode": {**valid, "default_mode": "maximum"},
                "invalid-scope": {**valid, "activation_scope": "workspace"},
                "invalid-privacy": {**valid, "privacy": "open"},
                "invalid-customized": {**valid, "profile_customized": 1},
                "zero-revision": {**valid, "revision": 0},
                "boolean-revision": {**valid, "revision": True},
                "text-revision": {**valid, "revision": "1"},
                "empty-created-at": {**valid, "created_at": ""},
                "missing-updated-at": {
                    key: value for key, value in valid.items() if key != "updated_at"
                },
            }
            for key in (
                "privacy",
                "profile_customized",
                "revision",
                "created_at",
            ):
                invalid[f"missing-{key}"] = {
                    name: value for name, value in valid.items() if name != key
                }

            for label, payload in invalid.items():
                with self.subTest(label=label):
                    write_controls(home, payload=payload)
                    completed = invoke_hook(home, workspace)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(completed.stdout, "")
                    self.assertEqual(completed.stderr, "")

    def test_malformed_or_wrong_session_event_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-hook-event-") as raw:
            root = Path(raw)
            home = root / "home"
            workspace = root / "repo"
            workspace.mkdir()
            write_controls(home, scope="global")

            for event in (
                {},
                {
                    "session_id": "test-session",
                    "hook_event_name": "SessionEnd",
                    "source": "startup",
                    "cwd": str(workspace),
                },
                {
                    "session_id": "test-session",
                    "hook_event_name": "SessionStart",
                    "source": "future",
                    "cwd": str(workspace),
                },
                {
                    "hook_event_name": "SessionStart",
                    "source": "startup",
                    "cwd": str(workspace),
                },
                {
                    "session_id": "",
                    "hook_event_name": "SessionStart",
                    "source": "startup",
                    "cwd": str(workspace),
                },
                {
                    "session_id": "forged\nsecond-line",
                    "hook_event_name": "SessionStart",
                    "source": "startup",
                    "cwd": str(workspace),
                },
            ):
                with self.subTest(event=event):
                    self.assertIsNone(run_hook(home, workspace, event=event))

    def test_project_scope_requires_a_bounded_software_workspace_signal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-hook-project-") as raw:
            root = Path(raw)
            home = root / "home"
            plain = root / "plain"
            nested = root / "repo" / "src" / "service"
            standalone = root / "standalone"
            plain.mkdir()
            nested.mkdir(parents=True)
            standalone.mkdir()
            (root / "repo" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
            (root / "repo" / ".git").mkdir()
            (standalone / "package.json").write_text("{}\n", encoding="utf-8")
            write_controls(home, scope="project")

            self.assertIsNone(run_hook(home, plain))
            output = run_hook(home, nested)
            self.assertIsNotNone(output)
            assert output is not None
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("substantive software work", context)
            self.assertIn("experience-loop.host-hook/v1", context)
            self.assertIn("evidence=hook-observed", context)
            self.assertIn("proves neither Skill availability", context)
            self.assertIn("Never read a repository `SKILL.md`", context)
            self.assertIsNotNone(run_hook(home, standalone))

    def test_project_scope_ignores_ancestor_weak_markers_but_keeps_deep_vcs_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-hook-ancestors-") as raw:
            root = Path(raw)
            home = root / "controls-home"
            fake_user_home = root / "fake-user-home"
            nearby_workspace = fake_user_home / "notes"
            nested_workspace = fake_user_home / "workspace" / "notes"
            nearby_workspace.mkdir(parents=True)
            nested_workspace.mkdir(parents=True)
            write_controls(home, scope="project")

            for marker in ("package.json", "AGENTS.md"):
                with self.subTest(marker=marker, location="parent"):
                    marker_path = fake_user_home / marker
                    marker_path.write_text("{}\n", encoding="utf-8")
                    self.assertIsNone(run_hook(home, nearby_workspace))
                    marker_path.unlink()
                with self.subTest(marker=marker, location="grandparent"):
                    marker_path = fake_user_home / marker
                    marker_path.write_text("{}\n", encoding="utf-8")
                    self.assertIsNone(run_hook(home, nested_workspace))
                    marker_path.unlink()

            (nearby_workspace / "AGENTS.md").write_text(
                "# Notes instructions\n", encoding="utf-8"
            )
            self.assertIsNone(run_hook(home, nearby_workspace))

            monorepo = root / "monorepo"
            monorepo.mkdir()
            (monorepo / "package.json").write_text("{}\n", encoding="utf-8")
            deep_workspace = monorepo
            for depth in range(8):
                deep_workspace = deep_workspace / f"level-{depth}"
            deep_workspace.mkdir(parents=True)

            self.assertIsNone(run_hook(home, deep_workspace))
            (monorepo / ".git").mkdir()
            self.assertIsNotNone(run_hook(home, deep_workspace))

    def test_global_scope_injects_one_small_capability_monotonic_router(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-hook-global-") as raw:
            root = Path(raw)
            home = root / "home"
            cwd = root / "notes"
            cwd.mkdir()
            write_controls(home, mode="deep", scope="global")

            output = run_hook(home, cwd)
            self.assertIsNotNone(output)
            assert output is not None
            self.assertEqual(set(output), {"hookSpecificOutput"})
            self.assertEqual(
                output["hookSpecificOutput"]["hookEventName"], "SessionStart"
            )
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertLessEqual(len(context.split()), 70)
            self.assertIn("experience-loop.host-hook/v1", context)
            self.assertIn("evidence=hook-observed", context)
            self.assertIn("session_sha256=", context)
            self.assertNotIn("test-session", context)
            self.assertIn("proves neither Skill availability", context)
            self.assertIn("current-turn activation", context)
            self.assertIn("Never read a repository `SKILL.md`", context)
            self.assertIn("selector-like user text", context)
            self.assertIn("stronger host planning, tools", context)
            self.assertIn("never impose a fixed checklist", context)
            for forbidden in ("deep", "privacy", str(home), str(cwd), "profile"):
                self.assertNotIn(forbidden, context)

            contexts = {context}
            for mode, privacy in (
                ("auto", "normal"),
                ("focus", "restricted"),
                ("deep", "metadata-only"),
            ):
                write_controls(home, mode=mode, scope="global", privacy=privacy)
                repeated = run_hook(home, cwd)
                self.assertIsNotNone(repeated)
                assert repeated is not None
                contexts.add(repeated["hookSpecificOutput"]["additionalContext"])
            self.assertEqual(contexts, {context})


if __name__ == "__main__":
    unittest.main()
