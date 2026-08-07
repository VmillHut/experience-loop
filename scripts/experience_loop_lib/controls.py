"""Minimal persisted controls kept separate from content-bearing profiles."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .common import (
    SCHEMA_VERSION,
    DataCorruptionError,
    ExperienceLoopError,
    atomic_write_json,
    capture_file_snapshot,
    load_json,
    normalize_activation_scope,
    normalize_mode,
    restore_file_snapshots,
    utc_now,
)
from .storage import Store


CONTROLS_SCHEMA_VERSION = 1
PRIVACY_LEVELS = ("normal", "restricted", "metadata-only")
DEFAULT_ROLE_SENTINEL = "software-developer"
_CONTROL_KEYS = {
    "schema_version",
    "default_mode",
    "activation_scope",
    "privacy",
    "profile_customized",
    "revision",
    "created_at",
    "updated_at",
}
_MISSING = object()


def profile_is_customized(profile: Dict[str, Any]) -> bool:
    """Return whether profile content can materially personalize an interaction."""
    role = profile.get("role")
    role_provided = (
        isinstance(role, str)
        and bool(role.strip())
        and role != DEFAULT_ROLE_SENTINEL
    )
    return bool(
        profile.get("name")
        or profile.get("responsibilities")
        or profile.get("domains")
        or profile.get("goals")
        or profile.get("learning_focus")
        or role_provided
        or profile.get("experience_level")
        or profile.get("experience_context")
        or profile.get("explanation_style")
        or profile.get("guidance_preference")
        or profile.get("delivery_context")
    )


def _validate_privacy(value: Any, *, corruption: bool) -> str:
    privacy = str(value)
    if privacy not in PRIVACY_LEVELS:
        if corruption:
            raise DataCorruptionError("controls.json 包含未知隐私级别。")
        raise ExperienceLoopError("未知隐私级别：%s" % value)
    return privacy


def default_controls() -> Dict[str, Any]:
    """Return a new persisted-controls value."""
    now = utc_now()
    return {
        "schema_version": CONTROLS_SCHEMA_VERSION,
        "default_mode": "auto",
        "activation_scope": "explicit",
        "privacy": "normal",
        "profile_customized": False,
        "revision": 1,
        "created_at": now,
        "updated_at": now,
    }


def validate_controls(value: Any) -> Dict[str, Any]:
    """Validate strict, non-content-bearing persisted controls."""
    if not isinstance(value, dict):
        raise DataCorruptionError("controls.json 必须是 JSON 对象。")
    unknown = sorted(set(value) - _CONTROL_KEYS)
    if unknown:
        raise DataCorruptionError(
            "controls.json 包含未知字段。", {"unknown_fields": unknown}
        )
    if value.get("schema_version") != CONTROLS_SCHEMA_VERSION:
        raise DataCorruptionError("controls.json 版本无效。")
    try:
        default_mode = normalize_mode(value.get("default_mode"))
    except ExperienceLoopError as exc:
        raise DataCorruptionError("controls.json 包含未知默认模式。") from exc
    try:
        activation_scope = normalize_activation_scope(value.get("activation_scope"))
    except ExperienceLoopError as exc:
        raise DataCorruptionError("controls.json 包含未知激活范围。") from exc
    privacy = _validate_privacy(value.get("privacy"), corruption=True)
    customized = value.get("profile_customized")
    if not isinstance(customized, bool):
        raise DataCorruptionError("controls.json 的 profile_customized 必须是布尔值。")
    revision = value.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise DataCorruptionError("controls.json 的 revision 必须是正整数。")
    created_at = value.get("created_at")
    updated_at = value.get("updated_at")
    if not isinstance(created_at, str) or not created_at.strip():
        raise DataCorruptionError("controls.json 的 created_at 必须是非空文本。")
    if not isinstance(updated_at, str) or not updated_at.strip():
        raise DataCorruptionError("controls.json 的 updated_at 必须是非空文本。")
    return {
        "schema_version": CONTROLS_SCHEMA_VERSION,
        "default_mode": default_mode,
        "activation_scope": activation_scope,
        "privacy": privacy,
        "profile_customized": customized,
        "revision": revision,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _snapshot(
    controls: Dict[str, Any], *, persisted: bool, source: str, changed: bool = False
) -> Dict[str, Any]:
    result = dict(controls)
    result["persisted"] = persisted
    result["source"] = source
    result["changed"] = changed
    return result


def _default_snapshot() -> Dict[str, Any]:
    controls = default_controls()
    controls["revision"] = 0
    return _snapshot(controls, persisted=False, source="defaults")


def _legacy_controls(profile: Any) -> Dict[str, Any]:
    if not isinstance(profile, dict):
        raise DataCorruptionError("profile.json 必须是 JSON 对象。")
    if profile.get("schema_version") != SCHEMA_VERSION:
        raise DataCorruptionError("profile.json 版本无效。")
    try:
        default_mode = normalize_mode(profile.get("mode"))
    except ExperienceLoopError as exc:
        raise DataCorruptionError("profile.json 包含未知工作模式。") from exc
    privacy = profile.get("privacy", "normal")
    if privacy not in PRIVACY_LEVELS:
        raise DataCorruptionError("profile.json 包含未知隐私级别。")
    now = utc_now()
    created_at = profile.get("created_at")
    updated_at = profile.get("updated_at")
    return _snapshot(
        {
            "schema_version": CONTROLS_SCHEMA_VERSION,
            "default_mode": default_mode,
            "activation_scope": "explicit",
            "privacy": privacy,
            "profile_customized": profile_is_customized(profile),
            "revision": 0,
            "created_at": created_at if isinstance(created_at, str) and created_at else now,
            "updated_at": updated_at if isinstance(updated_at, str) and updated_at else now,
        },
        persisted=False,
        source="legacy-profile",
    )


def load_controls(
    store: Store,
    *,
    allow_uninitialized: bool = False,
    legacy_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve controls without writing or validating unrelated profile content."""
    if not store.is_initialized():
        if allow_uninitialized:
            return _default_snapshot()
        store.require_initialized()
    else:
        store.require_initialized()
    value = load_json(store.controls_path, missing=_MISSING)
    if value is not _MISSING:
        return _snapshot(validate_controls(value), persisted=True, source="controls")
    profile = legacy_profile
    if profile is None:
        profile = load_json(store.profile_path, missing=None)
    if profile is None:
        raise DataCorruptionError(
            "控制状态和个人画像均缺失。请运行 doctor --repair。"
        )
    return _legacy_controls(profile)


def update_controls_locked(
    store: Store,
    *,
    default_mode: Optional[str] = None,
    activation_scope: Optional[str] = None,
    privacy: Optional[str] = None,
    profile_customized: Optional[bool] = None,
    legacy_profile: Optional[Dict[str, Any]] = None,
    allow_defaults: bool = False,
) -> Dict[str, Any]:
    """Merge and atomically persist controls while the caller holds Store.lock()."""
    try:
        current = load_controls(store, legacy_profile=legacy_profile)
    except DataCorruptionError:
        if store.controls_path.exists() or legacy_profile is not None:
            raise
        profile = load_json(store.profile_path, missing=None)
        if profile is not None:
            raise
        if not allow_defaults:
            raise
        current = _default_snapshot()

    next_value = {
        key: current[key]
        for key in _CONTROL_KEYS
    }
    if default_mode is not None:
        next_value["default_mode"] = normalize_mode(default_mode)
    if activation_scope is not None:
        next_value["activation_scope"] = normalize_activation_scope(activation_scope)
    if privacy is not None:
        next_value["privacy"] = _validate_privacy(privacy, corruption=False)
    if profile_customized is not None:
        if not isinstance(profile_customized, bool):
            raise ExperienceLoopError("profile_customized 必须是布尔值。")
        next_value["profile_customized"] = profile_customized

    semantic_keys = (
        "default_mode",
        "activation_scope",
        "privacy",
        "profile_customized",
    )
    changed = not current["persisted"] or any(
        next_value[key] != current[key] for key in semantic_keys
    )
    if not changed:
        return _snapshot(validate_controls(next_value), persisted=True, source="controls")

    now = utc_now()
    next_value["revision"] = current["revision"] + 1
    next_value["updated_at"] = now
    if current["revision"] == 0:
        next_value["created_at"] = now
    atomic_write_json(store.controls_path, validate_controls(next_value))
    return _snapshot(
        validate_controls(next_value), persisted=True, source="controls", changed=True
    )


def set_controls(
    store: Store,
    *,
    default_mode: Optional[str] = None,
    activation_scope: Optional[str] = None,
    privacy: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist one or more controls with cross-process read-modify-write locking."""
    if default_mode is None and activation_scope is None and privacy is None:
        raise ExperienceLoopError("至少需要提供一个控制状态变更。")
    already_initialized = store.is_initialized()
    store.initialize()
    with store.lock():
        controls_snapshot = capture_file_snapshot(store.controls_path)
        profile_snapshot = capture_file_snapshot(store.profile_path)
        legacy_profile = None
        mirror_status = "missing"
        try:
            candidate = load_json(store.profile_path, missing=None)
        except DataCorruptionError:
            candidate = None
            mirror_status = "invalid"
        if candidate is not None:
            if (
                isinstance(candidate, dict)
                and candidate.get("schema_version") == SCHEMA_VERSION
            ):
                legacy_profile = candidate
                mirror_status = "unchanged"
            else:
                mirror_status = "invalid"
        try:
            result = update_controls_locked(
                store,
                default_mode=default_mode,
                activation_scope=activation_scope,
                privacy=privacy,
                profile_customized=(
                    profile_is_customized(legacy_profile)
                    if legacy_profile is not None
                    else None
                ),
                legacy_profile=legacy_profile,
                allow_defaults=not already_initialized,
            )
            mirror_changed = False
            if legacy_profile is not None:
                mirror_changed = any(
                    (
                        legacy_profile.get("mode") != result["default_mode"],
                        legacy_profile.get("privacy") != result["privacy"],
                        legacy_profile.get("customized")
                        != result["profile_customized"],
                    )
                )
                if mirror_changed:
                    legacy_profile["mode"] = result["default_mode"]
                    legacy_profile["privacy"] = result["privacy"]
                    legacy_profile["customized"] = result["profile_customized"]
                    legacy_profile["updated_at"] = utc_now()
                    atomic_write_json(store.profile_path, legacy_profile)
                    mirror_status = "synced"
        except Exception as exc:
            restore_file_snapshots(
                (
                    (store.profile_path, profile_snapshot),
                    (store.controls_path, controls_snapshot),
                ),
                operation="更新控制状态",
                original_error=exc,
            )
            raise
        result["legacy_profile_mirror"] = mirror_status
        if result["changed"] or mirror_changed:
            store.touch_state_locked()
    if result["changed"] or mirror_changed:
        store.harden_known_permissions()
    return result
