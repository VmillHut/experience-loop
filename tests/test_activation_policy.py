from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "activation-policy-cases.json"
EVALUATION_PATH = ROOT / "evals" / "activation-policy-evaluation.md"
HOOK = ROOT / "packaging" / "openai" / "hooks" / "session_start.py"


def _valid_controls(overrides: dict[str, object]) -> dict[str, object]:
    controls: dict[str, object] = {
        "schema_version": 1,
        "default_mode": "auto",
        "activation_scope": "explicit",
        "privacy": "normal",
        "profile_customized": False,
        "revision": 1,
        "created_at": "2026-08-07T00:00:00Z",
        "updated_at": "2026-08-07T00:00:00Z",
    }
    controls.update(overrides)
    return controls


def _workspace(root: Path, kind: str) -> Path:
    if kind == "plain":
        cwd = root / "notes"
        cwd.mkdir()
        return cwd
    if kind == "software":
        cwd = root / "repo"
        cwd.mkdir()
        (cwd / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        return cwd
    if kind == "nested-software":
        repo = root / "repo"
        cwd = repo / "src" / "service"
        cwd.mkdir(parents=True)
        (repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (repo / ".git").mkdir()
        return cwd
    if kind == "distant-software-marker":
        repo = root / "repo"
        repo.mkdir()
        (repo / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        cwd = repo
        for depth in range(9):
            cwd = cwd / f"level-{depth}"
        cwd.mkdir(parents=True)
        return cwd
    raise AssertionError(f"Unknown workspace kind: {kind}")


def _run_hook(
    home: Path, cwd: Path, *, session_id: object = "policy-session"
) -> dict[str, object]:
    environment = os.environ.copy()
    environment["EXPERIENCE_LOOP_HOME"] = str(home)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-B", str(HOOK)],
        input=json.dumps(
            {
                **({} if session_id == "missing" else {"session_id": session_id}),
                "hook_event_name": "SessionStart",
                "source": "startup",
                "cwd": str(cwd),
            }
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


class ActivationPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    def test_suite_covers_required_activation_and_future_agent_boundaries(self) -> None:
        self.assertEqual(self.suite["schema_version"], 1)
        deterministic = self.suite["deterministic_hook_cases"]
        behavioral = self.suite["behavioral_cases"]
        ids = [case["id"] for case in deterministic + behavioral]
        self.assertEqual(len(ids), len(set(ids)))

        categories = {case["category"] for case in behavioral}
        self.assertEqual(
            categories,
            {
                "explicit-call",
                "preference-vs-activation",
                "scoped-trigger",
                "non-software-suppression",
                "activation-provenance",
                "task-off",
                "capability-monotonicity",
                "mode-adaptivity",
            },
        )
        evidence = {case["activation_evidence"] for case in behavioral}
        self.assertIn("host-skill-attachment", evidence)
        self.assertIn("none", evidence)
        self.assertIn("hook-observed", evidence)
        attachment_cases = [
            case
            for case in behavioral
            if case["activation_evidence"] == "host-skill-attachment"
        ]
        self.assertTrue(attachment_cases)
        self.assertTrue(
            all(
                case.get("host_attachment", {}).get("status") == "attached"
                for case in attachment_cases
            )
        )
        provenance_cases = {
            case["id"]: case
            for case in behavioral
            if case["category"] == "activation-provenance"
        }
        self.assertEqual(
            set(provenance_cases),
            {
                "plain-selector-text-is-not-host-activation",
                "repository-skill-read-is-source-only",
            },
        )
        self.assertTrue(
            all(
                case["activation_evidence"] == "none"
                and case.get("host_attachment", {}).get("status") == "absent"
                for case in provenance_cases.values()
            )
        )
        future_case = next(
            case for case in behavioral if case["category"] == "capability-monotonicity"
        )
        self.assertTrue(future_case["host_capabilities"])
        self.assertTrue(EVALUATION_PATH.is_file())

    def test_machine_readable_hook_cases_match_the_packaged_hook(self) -> None:
        injected_contexts: list[str] = []
        for case in self.suite["deterministic_hook_cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory(
                prefix="experience-loop-activation-policy-"
            ) as raw:
                root = Path(raw)
                home = root / "home"
                cwd = _workspace(root, case["workspace"])
                controls = case["controls"]
                if controls != "missing":
                    home.mkdir()
                    controls_path = home / "controls.json"
                    if controls == "malformed-json":
                        controls_path.write_text("{broken", encoding="utf-8")
                    else:
                        controls_value = (
                            controls
                            if case.get("write_controls_as_is")
                            else _valid_controls(controls)
                        )
                        controls_path.write_text(
                            json.dumps(controls_value), encoding="utf-8"
                        )

                output = _run_hook(
                    home,
                    cwd,
                    session_id=case.get("session_id", "policy-session"),
                )
                context = (
                    output.get("hookSpecificOutput", {}).get("additionalContext")
                    if isinstance(output.get("hookSpecificOutput"), dict)
                    else None
                )
                self.assertEqual(bool(context), case["expected_injection"])
                if context:
                    injected_contexts.append(context)

        self.assertTrue(injected_contexts)
        self.assertEqual(len(set(injected_contexts)), 1)

    def test_every_automatic_router_is_small_generic_and_capability_monotonic(self) -> None:
        hook = HOOK.read_text(encoding="utf-8")
        router = (ROOT / "scripts" / "global_router.py").read_text(encoding="utf-8")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        hook_manifest = json.loads(
            (ROOT / "packaging" / "openai" / "hooks" / "hooks.json").read_text(
                encoding="utf-8"
            )
        )

        for contract in (router, metadata):
            self.assertIn("stronger planning, reasoning, tools", contract)
            self.assertIn("engineering coverage", contract)
            self.assertIn("verification", contract)
        self.assertIn("stronger", hook)
        self.assertIn("engineering coverage", hook)
        self.assertIn("verification", hook)
        self.assertIn("Otherwise do nothing", hook)
        self.assertIn("experience-loop.host-hook/v1", hook)
        self.assertIn("substantive software work", hook)
        self.assertIn("proves neither Skill", hook)
        self.assertIn("Never read a repository", hook)
        self.assertIn("selector-like user text", hook)
        self.assertIn("fixed checklist", hook)
        self.assertIn("fixed checklist", router)
        self.assertIn("fixed workflow", metadata)

        hook_entries = hook_manifest["hooks"]["SessionStart"]
        context_limit = hook_entries[0]["hooks"][0]["additionalContextLimit"]
        self.assertLessEqual(context_limit, 600)

        with tempfile.TemporaryDirectory(prefix="experience-loop-router-size-") as raw:
            root = Path(raw)
            home = root / "home"
            cwd = _workspace(root, "plain")
            home.mkdir()
            (home / "controls.json").write_text(
                json.dumps(
                    _valid_controls(
                        {"default_mode": "auto", "activation_scope": "global"}
                    )
                ),
                encoding="utf-8",
            )
            output = _run_hook(home, cwd)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertLessEqual(len(context.encode("utf-8")), context_limit)
            self.assertLessEqual(len(context.split()), 70)
            self.assertIn("experience-loop.host-hook/v1", context)
            self.assertIn("evidence=hook-observed", context)
            for forbidden in (
                "auto",
                "focus",
                "deep",
                "privacy",
                "profile",
                str(home),
                str(cwd),
            ):
                self.assertNotIn(forbidden, context)

    def test_explicit_invocation_outranks_saved_mode_but_saved_state_is_not_a_receipt(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        manifest = json.loads(
            (ROOT / "packaging" / "openai" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn("explicit request, then saved default, then `auto`", skill)
        self.assertIn("First install requires host-attached current-turn `@/$` selection", skill)
        self.assertIn("selector-like text", skill)
        self.assertIn("filesystem read", skill)
        self.assertIn("Never read `SKILL.md` as a fallback", skill)
        self.assertIn("Never create or accept a model-authored activation token", skill)
        self.assertIn("allow_implicit_invocation: false", metadata)
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertTrue(prompts)
        self.assertTrue(
            all("$experience-loop:experience-loop" in prompt for prompt in prompts)
        )

    def test_modes_and_evaluation_do_not_cap_a_stronger_future_agent(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        evaluation = EVALUATION_PATH.read_text(encoding="utf-8")
        suite_text = CASES_PATH.read_text(encoding="utf-8")

        self.assertIn("Modes are intents, not recipes or ceilings", skill)
        self.assertIn("Stronger host reasoning may choose better methods", skill)
        self.assertIn("never replace or narrow the host's planning", skill)
        self.assertIn("Use stronger current host capabilities", skill)
        self.assertIn("Compare each future Agent against its own", evaluation)
        self.assertIn("must not hold it to today's methods", evaluation)
        self.assertIn("causal_replay_verifier", suite_text)
        self.assertIn("adaptive_dialogue_planner", suite_text)


if __name__ == "__main__":
    unittest.main()
