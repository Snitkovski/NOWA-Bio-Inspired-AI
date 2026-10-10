"""Global affective preset catalog (YAML, not Python literals)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from nowa_body.affect_presets import (
    BUILTIN_PRESET_IDS,
    AffectPreset,
    AffectPresetCatalog,
    AffectPresetError,
    load_factory_vectors,
    load_preset_file,
    package_defaults_path,
)


def test_shipped_defaults_have_four_factory_ids():
    path = package_defaults_path()
    presets = load_preset_file(path, builtin_all=True)
    ids = [item.id for item in presets]
    assert tuple(ids) == BUILTIN_PRESET_IDS
    vectors = load_factory_vectors()
    assert vectors["crisis"]["valence"] == pytest.approx(-0.80)
    assert vectors["trust_break"]["trust"] == pytest.approx(-0.80)
    assert vectors["routine"]["intensity"] == pytest.approx(0.20)


def test_merge_without_user_file_is_factory(tmp_path):
    catalog = AffectPresetCatalog(tmp_path)
    visible = catalog.visible_presets()
    assert [item.id for item in visible] == list(BUILTIN_PRESET_IDS)
    assert all(item.builtin and not item.overlay for item in visible)


def test_user_overlay_and_restore(tmp_path):
    catalog = AffectPresetCatalog(tmp_path)
    catalog.upsert_user_preset(
        AffectPreset(id="crisis", axes={"valence": -0.9, "arousal": 0.9}, intensity=0.3, label_en="Crisis", label_ru="Кризис")
    )
    crisis = catalog.get("crisis")
    assert crisis.builtin is True
    assert crisis.overlay is True
    assert crisis.axes["valence"] == pytest.approx(-0.9)
    catalog.restore_factory("crisis")
    restored = catalog.get("crisis")
    assert restored.overlay is False
    assert restored.axes["valence"] == pytest.approx(-0.80)


def test_custom_preset_add_and_delete(tmp_path):
    catalog = AffectPresetCatalog(tmp_path)
    catalog.upsert_user_preset(
        AffectPreset(
            id="month_close",
            axes={"valence": -0.4, "arousal": 0.5},
            intensity=0.3,
            label_en="Month close",
            label_ru="Закрытие месяца",
        )
    )
    ids = [item.id for item in catalog.visible_presets()]
    assert "month_close" in ids
    assert "crisis" in ids
    catalog.delete_user_preset("month_close")
    ids = [item.id for item in catalog.visible_presets()]
    assert "month_close" not in ids
    assert "crisis" in ids


def test_hide_builtin_does_not_delete_factory(tmp_path):
    catalog = AffectPresetCatalog(tmp_path)
    catalog.hide("routine", True)
    visible = [item.id for item in catalog.visible_presets()]
    assert "routine" not in visible
    assert catalog.get("routine").builtin is True
    catalog.hide("routine", False)
    assert "routine" in [item.id for item in catalog.visible_presets()]


def test_unknown_axis_in_user_catalog_raises(tmp_path):
    path = tmp_path / "nowa_affect_presets.yaml"
    path.write_text(
        yaml.safe_dump({
            "schema_version": 1,
            "presets": [{"id": "x", "label_en": "X", "pain": 1.0}],
        }),
        encoding="utf-8",
    )
    catalog = AffectPresetCatalog(tmp_path)
    with pytest.raises(AffectPresetError, match="unknown key 'pain'"):
        catalog.all_presets()


def test_cannot_delete_unmodified_builtin(tmp_path):
    catalog = AffectPresetCatalog(tmp_path)
    with pytest.raises(AffectPresetError, match="cannot delete a shipped preset"):
        catalog.delete_user_preset("crisis")
