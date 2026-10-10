"""Global affective-preset catalog: shipped YAML + user overlay.

Independent of the open role. One user file next to ``nowa_roles/`` is shared
by every role in this configurator workspace.

Axis names, clamp, and ``EmotionalImpulse`` come from ``src/affective_space.py``.
This module only stores/merges YAML templates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from ._compat import clamp, ensure_core_src_on_path, safe_float

ensure_core_src_on_path()

from affective_space import AXES, EmotionalImpulse  # noqa: E402

PRESET_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
BUILTIN_PRESET_IDS = ("crisis", "success", "trust_break", "routine")
DEFAULTS_RELATIVE = Path("data") / "affect_presets.defaults.yaml"
USER_FILENAME = "nowa_affect_presets.yaml"
# YAML overlay default (spec). Core ``EmotionalImpulse.intensity`` defaults to 1.0.
DEFAULT_INTENSITY = 0.35
_PRESET_META = frozenset({"id", "label_en", "label_ru", "intensity"})


class AffectPresetError(Exception):
    """Raised on a malformed preset catalog YAML."""


@dataclass
class AffectPreset:
    id: str
    axes: Dict[str, float]
    intensity: float = DEFAULT_INTENSITY
    label_en: str = ""
    label_ru: str = ""
    builtin: bool = False
    overlay: bool = False
    hidden: bool = False

    def label(self, lang: str = "en") -> str:
        if str(lang).lower().startswith("ru"):
            return self.label_ru or self.label_en or self.id
        return self.label_en or self.label_ru or self.id

    def as_vector(self) -> Dict[str, float]:
        payload = dict(self.axes)
        payload["intensity"] = float(self.intensity)
        return payload

    def to_impulse(self) -> EmotionalImpulse:
        return EmotionalImpulse(
            vector=dict(self.axes),
            intensity=float(self.intensity),
            source="external",
        )


@dataclass
class _UserDoc:
    hidden: List[str] = field(default_factory=list)
    order: List[str] = field(default_factory=list)
    presets: List[AffectPreset] = field(default_factory=list)


def package_defaults_path() -> Path:
    return Path(__file__).resolve().parent / DEFAULTS_RELATIVE


def default_user_presets_path(roles_root: Any) -> Path:
    """Sibling of ``nowa_roles/``, same rule as ``default_employees_root``."""
    root = Path(roles_root)
    if root.name == "nowa_roles":
        return root.parent / USER_FILENAME
    return root / USER_FILENAME


def load_factory_vectors(path: Optional[Path] = None) -> Dict[str, Dict[str, float]]:
    """``id → axes+intensity`` loaded from the shipped YAML (not a Python dict)."""
    presets = load_preset_file(path or package_defaults_path(), builtin_all=True)
    return {item.id: item.as_vector() for item in presets}


def load_preset_file(path: Path, *, builtin_all: bool = False) -> List[AffectPreset]:
    loc = str(path)
    if not path.is_file():
        raise AffectPresetError(f"preset catalog not found: {loc}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AffectPresetError(f"invalid YAML in {loc}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise AffectPresetError(f"{loc} must be a YAML mapping at the top level")
    return _parse_preset_list(raw.get("presets"), loc, builtin_all=builtin_all)


def _parse_preset_list(items: Any, loc: str, *, builtin_all: bool) -> List[AffectPreset]:
    if items is None:
        return []
    if not isinstance(items, list):
        raise AffectPresetError(f"{loc}: presets must be a list")
    seen: set = set()
    result: List[AffectPreset] = []
    for idx, entry in enumerate(items):
        preset = _parse_preset_entry(entry, f"{loc}: presets[{idx}]", builtin=builtin_all)
        if preset.id in seen:
            raise AffectPresetError(f"{loc}: duplicate preset id '{preset.id}'")
        seen.add(preset.id)
        result.append(preset)
    return result


def _parse_user_doc(path: Path) -> _UserDoc:
    if not path.is_file():
        return _UserDoc()
    loc = str(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AffectPresetError(f"invalid YAML in {loc}: {exc}") from exc
    if raw is None:
        return _UserDoc()
    if not isinstance(raw, dict):
        raise AffectPresetError(f"{loc} must be a YAML mapping at the top level")
    hidden_raw = raw.get("hidden") or []
    order_raw = raw.get("order") or []
    if hidden_raw and not isinstance(hidden_raw, list):
        raise AffectPresetError(f"{loc}: hidden must be a list")
    if order_raw and not isinstance(order_raw, list):
        raise AffectPresetError(f"{loc}: order must be a list")
    return _UserDoc(
        hidden=[str(item).strip() for item in hidden_raw if str(item).strip()],
        order=[str(item).strip() for item in order_raw if str(item).strip()],
        presets=_parse_preset_list(raw.get("presets"), loc, builtin_all=False),
    )


def _parse_preset_entry(entry: Any, loc: str, *, builtin: bool) -> AffectPreset:
    if not isinstance(entry, dict):
        raise AffectPresetError(f"{loc} must be a mapping")
    unknown = [str(key) for key in entry if str(key) not in AXES and str(key) not in _PRESET_META]
    if unknown:
        raise AffectPresetError(f"{loc} unknown key '{unknown[0]}'")
    preset_id = str(entry.get("id") or "").strip()
    if not PRESET_ID_RE.match(preset_id):
        raise AffectPresetError(
            f"{loc}: id must match [a-z][a-z0-9_]{{1,47}}, got {preset_id!r}"
        )
    label_en = str(entry.get("label_en") or "").strip()
    label_ru = str(entry.get("label_ru") or "").strip()
    if not label_en and not label_ru:
        raise AffectPresetError(f"{loc}: need label_en or label_ru")
    axes: Dict[str, float] = {}
    for axis in AXES:
        if axis not in entry or entry.get(axis) is None:
            continue
        axes[axis] = clamp(safe_float(entry[axis], 0.0), -1.0, 1.0)
    intensity = DEFAULT_INTENSITY
    if entry.get("intensity") is not None:
        intensity = clamp(safe_float(entry.get("intensity"), DEFAULT_INTENSITY), 0.0, 1.0)
    return AffectPreset(
        id=preset_id,
        axes=axes,
        intensity=intensity,
        label_en=label_en,
        label_ru=label_ru,
        builtin=builtin,
    )


def merge_catalog(
    defaults: Sequence[AffectPreset],
    user: _UserDoc,
) -> List[AffectPreset]:
    """Factory first, then user-only ids. Overlay replaces vector/labels of a builtin."""
    by_id: Dict[str, AffectPreset] = {}
    for item in defaults:
        by_id[item.id] = AffectPreset(
            id=item.id,
            axes=dict(item.axes),
            intensity=item.intensity,
            label_en=item.label_en,
            label_ru=item.label_ru,
            builtin=True,
        )
    hidden = set(user.hidden)
    for item in user.presets:
        if item.id in by_id:
            base = by_id[item.id]
            by_id[item.id] = AffectPreset(
                id=item.id,
                axes=dict(item.axes) if item.axes else dict(base.axes),
                intensity=item.intensity,
                label_en=item.label_en or base.label_en,
                label_ru=item.label_ru or base.label_ru,
                builtin=True,
                overlay=True,
            )
        else:
            by_id[item.id] = AffectPreset(
                id=item.id,
                axes=dict(item.axes),
                intensity=item.intensity,
                label_en=item.label_en,
                label_ru=item.label_ru,
                builtin=False,
            )
    if user.order:
        ordered: List[str] = [pid for pid in user.order if pid in by_id]
        for pid in list(by_id):
            if pid not in ordered:
                ordered.append(pid)
    else:
        ordered = [item.id for item in defaults]
        for item in user.presets:
            if item.id not in ordered:
                ordered.append(item.id)
        for pid in list(by_id):
            if pid not in ordered:
                ordered.append(pid)
    result: List[AffectPreset] = []
    for pid in ordered:
        preset = by_id[pid]
        preset.hidden = pid in hidden
        result.append(preset)
    return result


def dump_user_doc(doc: _UserDoc) -> str:
    payload: Dict[str, Any] = {"schema_version": 1}
    if doc.hidden:
        payload["hidden"] = list(doc.hidden)
    if doc.order:
        payload["order"] = list(doc.order)
    presets_payload = []
    for item in doc.presets:
        row: Dict[str, Any] = {"id": item.id}
        if item.label_en:
            row["label_en"] = item.label_en
        if item.label_ru:
            row["label_ru"] = item.label_ru
        for axis in AXES:
            if axis in item.axes:
                row[axis] = float(item.axes[axis])
        row["intensity"] = float(item.intensity)
        presets_payload.append(row)
    payload["presets"] = presets_payload
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, default_flow_style=False)


class AffectPresetCatalog:
    """Merged view of shipped defaults + one user YAML. Not scoped to a role."""

    def __init__(
        self,
        roles_root: Any,
        defaults_path: Optional[Path] = None,
        user_path: Optional[Path] = None,
    ) -> None:
        self.roles_root = Path(roles_root)
        self.defaults_path = Path(defaults_path or package_defaults_path())
        self.user_path = Path(user_path or default_user_presets_path(self.roles_root))
        self.defaults_error: Optional[AffectPresetError] = None
        self._defaults: List[AffectPreset] = []
        try:
            self._defaults = load_preset_file(self.defaults_path, builtin_all=True)
        except AffectPresetError as exc:
            self.defaults_error = exc
            self._defaults = []

    def all_presets(self) -> List[AffectPreset]:
        return merge_catalog(self._defaults, _parse_user_doc(self.user_path))

    def visible_presets(self) -> List[AffectPreset]:
        return [item for item in self.all_presets() if not item.hidden]

    def get(self, preset_id: str) -> AffectPreset:
        key = str(preset_id or "").strip()
        for item in self.all_presets():
            if item.id == key:
                return item
        raise AffectPresetError(f"unknown preset: {key}")

    def _load_user(self) -> _UserDoc:
        return _parse_user_doc(self.user_path)

    def _save_user(self, doc: _UserDoc) -> None:
        self.user_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_path.write_text(dump_user_doc(doc), encoding="utf-8")

    def upsert_user_preset(self, preset: AffectPreset) -> AffectPreset:
        if not PRESET_ID_RE.match(preset.id):
            raise AffectPresetError(
                f"id must match [a-z][a-z0-9_]{{1,47}}, got {preset.id!r}"
            )
        if not (preset.label_en or preset.label_ru):
            raise AffectPresetError("need label_en or label_ru")
        doc = self._load_user()
        remaining = [item for item in doc.presets if item.id != preset.id]
        remaining.append(
            AffectPreset(
                id=preset.id,
                axes=dict(preset.axes),
                intensity=preset.intensity,
                label_en=preset.label_en,
                label_ru=preset.label_ru,
            )
        )
        doc.presets = remaining
        self._save_user(doc)
        return self.get(preset.id)

    def hide(self, preset_id: str, hidden: bool = True) -> None:
        key = str(preset_id or "").strip()
        self.get(key)
        doc = self._load_user()
        current = [item for item in doc.hidden if item != key]
        if hidden:
            current.append(key)
        doc.hidden = current
        self._save_user(doc)

    def restore_factory(self, preset_id: str) -> None:
        key = str(preset_id or "").strip()
        factory_ids = {item.id for item in self._defaults}
        if key not in factory_ids:
            raise AffectPresetError(f"not a shipped preset: {key}")
        doc = self._load_user()
        doc.presets = [item for item in doc.presets if item.id != key]
        doc.hidden = [item for item in doc.hidden if item != key]
        self._save_user(doc)

    def delete_user_preset(self, preset_id: str) -> None:
        key = str(preset_id or "").strip()
        preset = self.get(key)
        if preset.builtin and not preset.overlay:
            raise AffectPresetError("cannot delete a shipped preset; hide or overlay it")
        if preset.builtin and preset.overlay:
            self.restore_factory(key)
            return
        doc = self._load_user()
        doc.presets = [item for item in doc.presets if item.id != key]
        doc.hidden = [item for item in doc.hidden if item != key]
        self._save_user(doc)

    def clear_user_file(self) -> None:
        if self.user_path.is_file():
            self.user_path.unlink()


__all__ = [
    "BUILTIN_PRESET_IDS",
    "DEFAULT_INTENSITY",
    "AffectPreset",
    "AffectPresetCatalog",
    "AffectPresetError",
    "PRESET_ID_RE",
    "default_user_presets_path",
    "load_factory_vectors",
    "load_preset_file",
    "merge_catalog",
    "package_defaults_path",
]
