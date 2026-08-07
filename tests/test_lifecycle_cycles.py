from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"
SKILL_NAME = "experience-loop"
INVOCATION = "$experience-loop"


def isolated_environment(root: Path, data_home: Path) -> dict[str, str]:
    """Keep every mutable host and runtime path inside one temporary root."""

    fake_home = root / "isolated-user-home"
    temp_root = root / "temp"
    fake_home.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(fake_home),
            "USERPROFILE": str(fake_home),
            "HOMEDRIVE": fake_home.drive,
            "HOMEPATH": str(fake_home)[len(fake_home.drive) :],
            "XDG_CONFIG_HOME": str(fake_home / ".config"),
            "APPDATA": str(fake_home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(fake_home / "AppData" / "Local"),
            "EXPERIENCE_LOOP_HOME": str(data_home),
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "TMPDIR": str(temp_root),
            "PYTHONUTF8": "1",
        }
    )
    return environment


def run_python(
    script: Path,
    *args: str,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(script), *args],
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def json_object(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    raw = result.stdout.strip() or result.stderr.strip()
    if not raw:
        raise AssertionError(
            f"process produced no JSON (exit={result.returncode}, stderr={result.stderr!r})"
        )
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            "process output is not JSON "
            f"(exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r})"
        ) from exc
    if not isinstance(value, dict):
        raise AssertionError(f"expected a JSON object, received {value!r}")
    return value


def runtime_data(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    envelope = json_object(result)
    if result.returncode != 0 or envelope.get("ok") is not True:
        raise AssertionError(
            f"runtime command failed (exit={result.returncode}): {envelope!r}"
        )
    value = envelope.get("data")
    if not isinstance(value, dict):
        raise AssertionError(f"runtime data must be an object: {envelope!r}")
    return value


def declared_skill_name(path: Path) -> str | None:
    manifest = path / "SKILL.md"
    if not manifest.is_file():
        return None
    for line in manifest.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if separator and key.strip() == "name":
            return value.strip().strip("\"'")
    return None


def discoverable_copies(discovery_root: Path) -> list[Path]:
    if not discovery_root.is_dir():
        return []
    return sorted(
        (
            path.resolve()
            for path in discovery_root.iterdir()
            if path.is_dir() and declared_skill_name(path) == SKILL_NAME
        ),
        key=str,
    )


def data_snapshot(root: Path) -> dict[str, tuple[int, str]]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): (
            len(content := path.read_bytes()),
            hashlib.sha256(content).hexdigest(),
        )
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
    }


class LifecycleCycleTests(unittest.TestCase):
    def test_five_clean_install_identity_setup_use_uninstall_cycles(self) -> None:
        scenarios = (
            {
                "mode": "auto",
                "scope": "explicit",
                "privacy": "normal",
                "name": "循环用户一",
                "role": "backend-engineer",
                "goal": "验证安装闭环",
            },
            {
                "mode": "focus",
                "scope": "project",
                "privacy": "restricted",
                "name": "循环用户二",
                "role": "frontend-engineer",
                "goal": "练习边界判断",
            },
            {
                "mode": "deep",
                "scope": "global",
                "privacy": "metadata-only",
                "name": "循环用户三",
                "role": "platform-engineer",
                "goal": "复盘架构取舍",
            },
            {
                "mode": "off",
                "scope": "explicit",
                "privacy": "normal",
                "name": "循环用户四",
                "role": "mobile-engineer",
                "goal": "验证关闭时不记录",
            },
            {
                "mode": "auto",
                "scope": "project",
                "privacy": "normal",
                "name": "循环用户五",
                "role": "full-stack-engineer",
                "goal": "验证重装连续性",
            },
        )

        with tempfile.TemporaryDirectory(prefix="experience-loop-five-cycles-") as raw:
            root = Path(raw)
            discovery_root = root / "isolated-host" / "skills"
            target = discovery_root / SKILL_NAME
            transaction_root = root / "transactions"
            data_home = root / "personal-data"
            environment = isolated_environment(root, data_home)
            expected_event_count = 0
            observed_fingerprints: list[str] = []

            for cycle_number, scenario in enumerate(scenarios, start=1):
                with self.subTest(cycle=cycle_number, scenario=scenario):
                    # Every round starts from a host discovery root with no active copy.
                    self.assertFalse(target.exists())
                    self.assertEqual(discoverable_copies(discovery_root), [])
                    before_install_data = data_snapshot(data_home)

                    installed = run_python(
                        INSTALLER,
                        "--host",
                        "isolated-lifecycle-host",
                        "--scope",
                        "user",
                        "--target",
                        str(target),
                        "--transaction-root",
                        str(transaction_root),
                        "--discovery-root",
                        str(discovery_root),
                        "--invocation",
                        INVOCATION,
                        "--reload-hint",
                        "Start a fresh isolated lifecycle-test session.",
                        "--host-evidence",
                        "Resolved from the isolated lifecycle harness contract.",
                        "--json",
                        cwd=ROOT,
                        env=environment,
                    )
                    install_receipt = json_object(installed)
                    self.assertEqual(installed.returncode, 0, installed.stderr)
                    self.assertEqual(install_receipt["status"], "installed")
                    self.assertIsNone(install_receipt["backup"])
                    self.assertEqual(
                        discoverable_copies(discovery_root), [target.resolve()]
                    )
                    self.assertEqual(data_snapshot(data_home), before_install_data)

                    self.assertEqual(
                        install_receipt["receipt_schema"],
                        "experience-loop.install/v2",
                    )
                    self.assertEqual(
                        install_receipt["facts_schema"],
                        "experience-loop.host-facts/v1",
                    )
                    facts = install_receipt["facts"]
                    self.assertEqual(
                        set(facts),
                        {
                            "identity",
                            "plugin_registration",
                            "skill_availability",
                            "current_turn_activation",
                            "hook_observed",
                        },
                    )
                    self.assertEqual(facts["identity"]["status"], "verified")
                    self.assertEqual(
                        facts["plugin_registration"]["status"], "not-observed"
                    )
                    self.assertEqual(
                        facts["skill_availability"]["status"], "not-observed"
                    )
                    self.assertEqual(
                        facts["current_turn_activation"],
                        {
                            "status": "not-observed",
                            "evidence": (
                                "requires-current-turn-host-attachment-provenance"
                            ),
                            "identity_substitution": "forbidden",
                        },
                    )
                    self.assertEqual(facts["hook_observed"]["status"], "not-observed")
                    self.assertEqual(
                        install_receipt["activation_handoff"]["state"],
                        "awaiting-explicit-invocation",
                    )
                    self.assertEqual(
                        install_receipt["activation_handoff"]["invocation"],
                        INVOCATION,
                    )
                    self.assertEqual(
                        install_receipt["activation_handoff"]["required_receipt"],
                        "experience-loop.activation/v1",
                    )
                    self.assertEqual(
                        install_receipt["activation_handoff"][
                            "required_receipt_status"
                        ],
                        "deprecated-advisory",
                    )
                    self.assertEqual(
                        install_receipt["activation_handoff"]["required_provenance"],
                        "host-attachment",
                    )
                    self.assertFalse(install_receipt["onboarding_gate"]["allowed"])
                    self.assertEqual(
                        install_receipt["onboarding_gate"]["status"],
                        "blocked-pending-explicit-activation",
                    )

                    expected_identity = install_receipt["activation_handoff"][
                        "expected_identity"
                    ]
                    fingerprint = expected_identity["fingerprint"]
                    observed_fingerprints.append(fingerprint)
                    self.assertEqual(Path(expected_identity["root"]), target.resolve())
                    self.assertEqual(
                        install_receipt["onboarding_gate"][
                            "required_identity_fingerprint"
                        ],
                        fingerprint,
                    )

                    runtime = target / "scripts" / "experience_loop.py"
                    before_identity_data = data_snapshot(data_home)
                    mismatch_result = run_python(
                        runtime,
                        "--home",
                        str(data_home),
                        "--json",
                        "identity",
                        "--expected-fingerprint",
                        "sha256:" + "0" * 64,
                        cwd=root,
                        env=environment,
                    )
                    mismatch_envelope = json_object(mismatch_result)
                    self.assertNotEqual(mismatch_result.returncode, 0)
                    self.assertFalse(mismatch_envelope["ok"])
                    mismatch = mismatch_envelope["data"]
                    self.assertEqual(mismatch["status"], "mismatch")
                    self.assertEqual(
                        mismatch["host_activation"]["status"], "not_evaluated"
                    )
                    self.assertNotIn("onboarding_identity_gate", mismatch)
                    self.assertEqual(data_snapshot(data_home), before_identity_data)

                    # Direct CLI execution exercises the installed runtime only. It
                    # proves identity independently and cannot simulate host attachment.
                    identity = runtime_data(
                        run_python(
                            runtime,
                            "--home",
                            str(data_home),
                            "--json",
                            "identity",
                            "--expected-fingerprint",
                            fingerprint,
                            cwd=root,
                            env=environment,
                        )
                    )
                    self.assertEqual(identity["receipt_schema"], "experience-loop.identity/v1")
                    self.assertEqual(identity["status"], "matched")
                    self.assertTrue(identity["match"])
                    self.assertEqual(
                        identity["host_activation"]["status"], "not_evaluated"
                    )
                    self.assertNotIn("onboarding_identity_gate", identity)
                    self.assertEqual(identity["identity"]["fingerprint"], fingerprint)
                    self.assertEqual(
                        identity["runtime"]["initialized"], cycle_number > 1
                    )
                    self.assertIn(
                        "current-turn explicit activation",
                        identity["proof_scope"]["does_not_prove"],
                    )
                    self.assertEqual(data_snapshot(data_home), before_identity_data)

                    setup = runtime_data(
                        run_python(
                            runtime,
                            "--home",
                            str(data_home),
                            "--json",
                            "setup",
                            "--name",
                            scenario["name"],
                            "--role",
                            scenario["role"],
                            "--goal",
                            scenario["goal"],
                            "--learning-focus",
                            f"生命周期第 {cycle_number} 轮",
                            "--mode",
                            scenario["mode"],
                            "--activation-scope",
                            scenario["scope"],
                            "--privacy",
                            scenario["privacy"],
                            cwd=root,
                            env=environment,
                        )
                    )
                    self.assertEqual(setup["profile"]["name"], scenario["name"])
                    self.assertEqual(setup["profile"]["role"], scenario["role"])
                    self.assertEqual(
                        setup["controls"]["default_mode"], scenario["mode"]
                    )
                    self.assertEqual(
                        setup["controls"]["activation_scope"], scenario["scope"]
                    )
                    self.assertEqual(setup["controls"]["privacy"], scenario["privacy"])
                    if cycle_number == 1:
                        self.assertFalse(setup["already_initialized"])
                        self.assertEqual(
                            setup["next_actions"], ["offer_short_tutorial"]
                        )
                        self.assertIn("本地状态已初始化", setup["message"])
                        self.assertIn("不证明宿主已激活", setup["message"])
                        (data_home / "lifecycle-sentinel.txt").write_text(
                            "preserve-across-uninstalls", encoding="utf-8"
                        )
                    else:
                        self.assertTrue(setup["already_initialized"])
                        self.assertEqual(setup["next_actions"], [])
                        self.assertIn("不重复新手教学", setup["message"])

                    recorded = runtime_data(
                        run_python(
                            runtime,
                            "--home",
                            str(data_home),
                            "--json",
                            "ledger",
                            "record",
                            "--kind",
                            "verification",
                            "--summary",
                            f"完成隔离生命周期第 {cycle_number} 轮",
                            "--capability",
                            "verification",
                            "--independence",
                            "independent",
                            "--evidence",
                            f"isolated:lifecycle-cycle-{cycle_number}",
                            "--outcome",
                            "安装、身份、初始化与卸载边界均按契约执行",
                            cwd=root,
                            env=environment,
                        )
                    )
                    if scenario["mode"] == "off":
                        self.assertFalse(recorded["recorded"])
                        self.assertEqual(recorded["reason"], "mode_off")
                    else:
                        expected_event_count += 1
                        self.assertTrue(recorded["recorded"])
                        self.assertEqual(recorded["event"]["mode"], scenario["mode"])

                    status = runtime_data(
                        run_python(
                            runtime,
                            "--home",
                            str(data_home),
                            "--json",
                            "status",
                            cwd=root,
                            env=environment,
                        )
                    )
                    self.assertTrue(status["initialized"])
                    self.assertEqual(status["default_mode"], scenario["mode"])
                    self.assertEqual(status["activation_scope"], scenario["scope"])
                    self.assertEqual(status["privacy"], scenario["privacy"])
                    self.assertEqual(status["ledger_events"], expected_event_count)

                    before_uninstall_data = data_snapshot(data_home)
                    uninstalled = run_python(
                        target / "scripts" / "uninstall.py",
                        "--yes",
                        "--json",
                        cwd=root,
                        env=environment,
                    )
                    uninstall_receipt = json_object(uninstalled)
                    self.assertEqual(uninstalled.returncode, 0, uninstalled.stderr)
                    self.assertEqual(uninstall_receipt["status"], "uninstalled")
                    self.assertTrue(uninstall_receipt["personal_data_preserved"])
                    self.assertEqual(
                        Path(uninstall_receipt["personal_data_location_hint"]),
                        data_home.resolve(),
                    )
                    self.assertEqual(
                        uninstall_receipt["personal_data_location_basis"],
                        "EXPERIENCE_LOOP_HOME",
                    )
                    self.assertEqual(data_snapshot(data_home), before_uninstall_data)
                    self.assertFalse(target.exists())
                    self.assertEqual(discoverable_copies(discovery_root), [])
                    self.assertEqual(
                        list(discovery_root.rglob(".experience-loop-install.json")), []
                    )
                    self.assertEqual(
                        list(discovery_root.rglob(".experience-loop-SKILL.md")), []
                    )

            self.assertEqual(len(observed_fingerprints), 5)
            self.assertEqual(len(set(observed_fingerprints)), 1)
            self.assertEqual(
                (data_home / "lifecycle-sentinel.txt").read_text(encoding="utf-8"),
                "preserve-across-uninstalls",
            )
            self.assertEqual(expected_event_count, 4)


if __name__ == "__main__":
    unittest.main()
