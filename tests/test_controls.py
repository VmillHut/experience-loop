from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from helpers import payload, run_cli
from experience_loop_lib.common import DataCorruptionError, ExperienceLoopError, atomic_write_json
from experience_loop_lib.controls import load_controls, set_controls
from experience_loop_lib.profile import (
    configure_profile,
    load_profile,
    load_profile_controls,
    set_mode,
)
from experience_loop_lib.storage import Store


class ControlsTests(unittest.TestCase):
    def test_uninitialized_query_returns_defaults_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-default-") as raw:
            home = Path(raw) / "data"
            controls = load_controls(Store(str(home)), allow_uninitialized=True)

            self.assertEqual(controls["default_mode"], "auto")
            self.assertEqual(controls["activation_scope"], "explicit")
            self.assertEqual(controls["privacy"], "normal")
            self.assertEqual(controls["revision"], 0)
            self.assertFalse(controls["persisted"])
            self.assertEqual(controls["source"], "defaults")
            self.assertFalse(home.exists())

    def test_first_control_write_materializes_defaults_without_a_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-first-write-") as raw:
            store = Store(str(Path(raw) / "data"))
            controls = set_controls(store, default_mode="deep")

            self.assertEqual(controls["default_mode"], "deep")
            self.assertEqual(controls["activation_scope"], "explicit")
            self.assertEqual(controls["revision"], 1)
            self.assertEqual(controls["legacy_profile_mirror"], "missing")
            self.assertTrue(store.controls_path.is_file())
            self.assertFalse(store.profile_path.exists())

    def test_setup_materializes_controls_and_compatibility_mirrors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-setup-") as raw:
            store = Store(str(Path(raw) / "data"))
            profile = configure_profile(
                store,
                role="backend-engineer",
                mode="deep",
                privacy="restricted",
            )

            controls = load_controls(store)
            stored_profile = json.loads(store.profile_path.read_text(encoding="utf-8"))
            self.assertEqual(controls["default_mode"], "deep")
            self.assertEqual(controls["activation_scope"], "explicit")
            self.assertEqual(controls["privacy"], "restricted")
            self.assertTrue(controls["profile_customized"])
            self.assertEqual(controls["revision"], 1)
            self.assertEqual(stored_profile["mode"], "deep")
            self.assertEqual(stored_profile["privacy"], "restricted")
            self.assertTrue(stored_profile["customized"])
            self.assertEqual(profile["mode"], "deep")

    def test_legacy_profile_is_read_without_implicit_migration_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-legacy-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store)
            store.controls_path.unlink()
            legacy = json.loads(store.profile_path.read_text(encoding="utf-8"))
            legacy["mode"] = "coach"
            legacy["privacy"] = "metadata-only"
            store.profile_path.write_text(
                json.dumps(legacy, ensure_ascii=False), encoding="utf-8"
            )

            controls = load_controls(store)
            profile_controls = load_profile_controls(store)
            self.assertEqual(controls["default_mode"], "focus")
            self.assertEqual(controls["privacy"], "metadata-only")
            self.assertEqual(controls["source"], "legacy-profile")
            self.assertEqual(controls["revision"], 0)
            self.assertFalse(controls["persisted"])
            self.assertEqual(profile_controls["mode"], "focus")
            self.assertFalse(store.controls_path.exists())

    def test_controls_are_authoritative_over_stale_profile_mirrors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-authority-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, role="backend-engineer")
            updated = set_controls(
                store,
                default_mode="deep",
                activation_scope="global",
                privacy="restricted",
            )
            stale = json.loads(store.profile_path.read_text(encoding="utf-8"))
            stale["mode"] = "off"
            stale["privacy"] = "metadata-only"
            store.profile_path.write_text(
                json.dumps(stale, ensure_ascii=False), encoding="utf-8"
            )

            controls = load_profile_controls(store)
            profile = load_profile(store)
            self.assertEqual(updated["revision"], 2)
            self.assertEqual(controls["mode"], "deep")
            self.assertEqual(controls["activation_scope"], "global")
            self.assertEqual(controls["privacy"], "restricted")
            self.assertEqual(profile["mode"], "deep")
            self.assertEqual(profile["privacy"], "restricted")

    def test_doctor_detects_and_repairs_stale_profile_control_mirrors_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-doctor-") as raw:
            home = Path(raw) / "data"
            setup = run_cli(
                home,
                "setup",
                "--name",
                "Ada",
                "--role",
                "backend-engineer",
                "--goal",
                "reliable releases",
                "--mode",
                "deep",
                "--privacy",
                "restricted",
            )
            self.assertEqual(setup.returncode, 0, setup.stderr)
            profile_path = home / "profile.json"
            controls_path = home / "controls.json"
            stale = json.loads(profile_path.read_text(encoding="utf-8"))
            stale["mode"] = "off"
            stale["privacy"] = "metadata-only"
            stale["customized"] = False
            profile_path.write_text(
                json.dumps(stale, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            stale_bytes = profile_path.read_bytes()
            controls_bytes = controls_path.read_bytes()

            diagnosed = run_cli(home, "doctor")
            self.assertEqual(diagnosed.returncode, 4, diagnosed.stderr or diagnosed.stdout)
            diagnosis = payload(diagnosed)["data"]
            mirror_check = next(
                check
                for check in diagnosis["checks"]
                if check["name"] == "profile-control-mirrors"
            )
            self.assertEqual(mirror_check["status"], "fail")
            self.assertEqual(
                set(mirror_check["details"]["mismatches"]),
                {"mode", "privacy", "customized"},
            )
            self.assertEqual(profile_path.read_bytes(), stale_bytes)
            self.assertEqual(controls_path.read_bytes(), controls_bytes)

            repaired = run_cli(home, "doctor", "--repair")
            self.assertEqual(repaired.returncode, 0, repaired.stderr or repaired.stdout)
            repair_data = payload(repaired)["data"]
            self.assertIn("profile_control_mirrors", repair_data["repaired_items"])
            repaired_check = next(
                check
                for check in repair_data["checks"]
                if check["name"] == "profile-control-mirrors"
            )
            self.assertEqual(repaired_check["status"], "pass")
            self.assertEqual(
                repaired_check["details"]["repaired_fields"],
                ["customized", "mode", "privacy"],
            )

            repaired_profile = json.loads(profile_path.read_text(encoding="utf-8"))
            for key, value in stale.items():
                if key not in {"mode", "privacy", "customized"}:
                    self.assertEqual(repaired_profile[key], value, key)
            self.assertEqual(repaired_profile["mode"], "deep")
            self.assertEqual(repaired_profile["privacy"], "restricted")
            self.assertTrue(repaired_profile["customized"])
            self.assertEqual(controls_path.read_bytes(), controls_bytes)

    def test_repeated_value_does_not_increment_revision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-revision-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store)
            initial = load_controls(store)
            unchanged = set_controls(store, default_mode="auto")
            changed = set_controls(store, activation_scope="project")
            mirrored = json.loads(store.profile_path.read_text(encoding="utf-8"))

            self.assertFalse(unchanged["changed"])
            self.assertEqual(unchanged["revision"], initial["revision"])
            self.assertTrue(changed["changed"])
            self.assertEqual(changed["revision"], initial["revision"] + 1)
            self.assertEqual(changed["legacy_profile_mirror"], "unchanged")
            self.assertEqual(mirrored["mode"], "auto")
            self.assertEqual(mirrored["privacy"], "normal")

    def test_corrupt_controls_fail_closed_without_profile_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-corrupt-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, mode="focus")
            damaged = json.loads(store.controls_path.read_text(encoding="utf-8"))
            damaged["default_mode"] = "definitely-invalid"
            store.controls_path.write_text(
                json.dumps(damaged, ensure_ascii=False), encoding="utf-8"
            )
            before = store.controls_path.read_bytes()

            with self.assertRaises(DataCorruptionError):
                load_controls(store)
            with self.assertRaises(DataCorruptionError):
                set_mode(store, "off")
            self.assertEqual(store.controls_path.read_bytes(), before)

    def test_json_null_controls_fail_closed_without_profile_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-null-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, mode="focus")
            store.controls_path.write_text("null\n", encoding="utf-8")

            with self.assertRaises(DataCorruptionError):
                load_controls(store)
            with self.assertRaises(DataCorruptionError):
                set_controls(store, default_mode="deep")
            self.assertEqual(store.controls_path.read_text(encoding="utf-8"), "null\n")

    def test_configure_profile_rolls_back_when_controls_write_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-profile-rollback-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, role="backend-engineer")
            profile_before = store.profile_path.read_bytes()
            controls_before = store.controls_path.read_bytes()

            def fail_after_controls_write(path: Path, value: object) -> None:
                atomic_write_json(path, value)
                raise ExperienceLoopError("simulated controls write failure")

            with mock.patch(
                "experience_loop_lib.controls.atomic_write_json",
                side_effect=fail_after_controls_write,
            ):
                with self.assertRaisesRegex(
                    ExperienceLoopError, "simulated controls write failure"
                ):
                    configure_profile(store, name="Ada", mode="deep")

            self.assertEqual(store.profile_path.read_bytes(), profile_before)
            self.assertEqual(store.controls_path.read_bytes(), controls_before)

    def test_set_controls_rolls_back_when_profile_mirror_write_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-rollback-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, role="backend-engineer")
            profile_before = store.profile_path.read_bytes()
            controls_before = store.controls_path.read_bytes()

            def fail_after_profile_write(path: Path, value: object) -> None:
                atomic_write_json(path, value)
                if Path(path) == store.profile_path:
                    raise ExperienceLoopError("simulated profile write failure")

            with mock.patch(
                "experience_loop_lib.controls.atomic_write_json",
                side_effect=fail_after_profile_write,
            ):
                with self.assertRaisesRegex(
                    ExperienceLoopError, "simulated profile write failure"
                ):
                    set_controls(store, default_mode="deep", privacy="restricted")

            self.assertEqual(store.profile_path.read_bytes(), profile_before)
            self.assertEqual(store.controls_path.read_bytes(), controls_before)

    def test_set_mode_rolls_back_when_controls_write_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-mode-rollback-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, role="backend-engineer")
            profile_before = store.profile_path.read_bytes()
            controls_before = store.controls_path.read_bytes()

            def fail_after_controls_write(path: Path, value: object) -> None:
                atomic_write_json(path, value)
                raise ExperienceLoopError("simulated mode controls failure")

            with mock.patch(
                "experience_loop_lib.controls.atomic_write_json",
                side_effect=fail_after_controls_write,
            ):
                with self.assertRaisesRegex(
                    ExperienceLoopError, "simulated mode controls failure"
                ):
                    set_mode(store, "deep")

            self.assertEqual(store.profile_path.read_bytes(), profile_before)
            self.assertEqual(store.controls_path.read_bytes(), controls_before)

    def test_initialized_home_missing_both_control_sources_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-missing-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store)
            store.controls_path.unlink()
            store.profile_path.unlink()

            with self.assertRaises(DataCorruptionError):
                set_controls(store, activation_scope="global")
            self.assertFalse(store.controls_path.exists())

    def test_lightweight_controls_ignore_unrelated_profile_content_corruption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-profile-damage-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, role="backend-engineer")
            damaged = json.loads(store.profile_path.read_text(encoding="utf-8"))
            damaged["responsibilities"] = [{"unexpected": "object"}]
            store.profile_path.write_text(
                json.dumps(damaged, ensure_ascii=False), encoding="utf-8"
            )

            controls = load_profile_controls(store)
            self.assertEqual(controls["mode"], "auto")
            switched = set_mode(store, "off")
            self.assertEqual(switched["mode"], "off")
            self.assertEqual(load_controls(store)["default_mode"], "off")

    def test_controls_remain_available_when_profile_json_is_unreadable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-profile-json-") as raw:
            store = Store(str(Path(raw) / "data"))
            configure_profile(store, role="backend-engineer")
            store.profile_path.write_text("{broken", encoding="utf-8")

            controls = load_controls(store)
            self.assertEqual(controls["default_mode"], "auto")
            switched = set_controls(store, default_mode="off")
            self.assertEqual(switched["default_mode"], "off")
            self.assertEqual(switched["legacy_profile_mirror"], "invalid")
            self.assertEqual(store.profile_path.read_text(encoding="utf-8"), "{broken")

    def test_concurrent_partial_updates_preserve_both_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="experience-loop-controls-race-") as raw:
            root = Path(raw)
            store = Store(str(root / "data"))
            configure_profile(store)
            gate = root / "go"
            worker = (
                "import sys,time; from pathlib import Path; "
                "sys.path.insert(0, sys.argv[5]); "
                "from experience_loop_lib.controls import set_controls; "
                "from experience_loop_lib.storage import Store; "
                "gate=Path(sys.argv[2]); "
                "\nwhile not gate.exists(): time.sleep(0.01)\n"
                "set_controls(Store(sys.argv[1]), **{sys.argv[3]: sys.argv[4]})"
            )
            common = [str(store.home), str(gate)]
            first = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    worker,
                    *common,
                    "default_mode",
                    "deep",
                    str(SCRIPTS),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=os.environ.copy(),
            )
            second = subprocess.Popen(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    worker,
                    *common,
                    "activation_scope",
                    "global",
                    str(SCRIPTS),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=os.environ.copy(),
            )
            gate.write_text("go\n", encoding="utf-8")
            first_output = first.communicate(timeout=10)
            second_output = second.communicate(timeout=10)

            self.assertEqual(first.returncode, 0, first_output[1])
            self.assertEqual(second.returncode, 0, second_output[1])
            controls = load_controls(store)
            self.assertEqual(controls["default_mode"], "deep")
            self.assertEqual(controls["activation_scope"], "global")
            self.assertEqual(controls["revision"], 3)


if __name__ == "__main__":
    unittest.main()
