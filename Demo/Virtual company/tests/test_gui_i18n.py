"""Tests for lab GUI bilingual strings."""

from __future__ import annotations

from pathlib import Path

from nowa_sandbox.gui_i18n import (
    I18n,
    STRINGS,
    assert_string_parity,
    format_readiness_localized,
)


# Transliterations / leftover English that must not appear in RU UI chrome.
_RU_FORBIDDEN = (
    "Свип",
    "свип",
    "Baseline",
    "Fitness",
    "graduation",
    "graduated",
    "ckpt",
    "Config YAML",
    "Output JSON",
    "Checkpoint",
    "Resume",
    "all_passed",
)
# Keys that intentionally keep short Latin tokens (NR, least_used strategy id).
_RU_ALLOW_KEYS = {
    "col.nr",
    "diag.flags",
    "diag.nr_fail",
    "diag.table_header",
}


class TestI18nCatalog:

    def test_en_ru_key_parity(self):
        assert_string_parity()
        assert set(STRINGS) == {"en", "ru"}

    def test_russian_has_no_translit_or_english_chrome(self):
        for key, value in STRINGS["ru"].items():
            if key in _RU_ALLOW_KEYS:
                continue
            if key.startswith("filetypes.") or key in ("filetypes.json",):
                continue
            # Path templates may mention results/ filenames — skip those.
            if "results/" in value or "stage1a_lab" in value:
                continue
            for bad in _RU_FORBIDDEN:
                assert bad not in value, f"ru[{key!r}] contains {bad!r}: {value!r}"

    def test_switch_and_persist(self, tmp_path: Path):
        pref = tmp_path / "lang.json"
        i18n = I18n(lang="en", pref_path=pref)
        assert i18n.t("status.ready") == "Ready."
        i18n.set_language("ru")
        assert i18n.t("status.ready") == "Готово."
        assert pref.exists()

        again = I18n(lang="en", pref_path=pref)
        assert again.lang == "ru"
        assert again.t("tab.run") == "Запуск"

    def test_format_kwargs(self):
        i18n = I18n(lang="en")
        assert "42" in i18n.t("status.added_files", n=42)

    def test_readiness_localized_ru(self):
        report = {
            "rows": [
                {
                    "name": "seed42",
                    "graduated": True,
                    "first_graduation_quarter": 10,
                    "n_graduated_quarters": 5,
                }
            ],
            "readiness": {
                "n_graduated": 4,
                "n_runs": 5,
                "graduation_quarters": [8, 10, 12, 14],
                "spread_ratio": 0.4,
                "spread_half_width": 5.0,
                "spread_within_tolerance": True,
                "ready_for_stage_1b": True,
            },
            "baseline_path": None,
            "refused": None,
        }
        i18n = I18n(lang="ru")
        text = format_readiness_localized(report, i18n)
        assert "ГОТОВО к этапу 1b" in text
        assert "да" in text
        assert "Свип" not in i18n.t("tab.sweep")
        assert i18n.t("tab.sweep") == "Перебор"
        assert "Baseline" not in i18n.t("tab.report")
        assert i18n.t("col.cost_efficiency") == "стоимость"
