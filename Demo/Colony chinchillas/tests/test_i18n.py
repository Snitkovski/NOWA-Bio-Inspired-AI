"""EN/RU catalogs stay in lockstep, and English is the default UI language."""

from __future__ import annotations

from colony_gui.i18n import (
    assert_catalog_parity,
    get_language,
    label,
    reset_language,
    set_language,
    tr,
)
from colony_gui.nowa_interpreter import get_axis_label, interpret_affect


def test_catalog_parity() -> None:
    assert_catalog_parity()


def test_default_language_is_english(monkeypatch) -> None:
    monkeypatch.delenv("NOWA_LANG", raising=False)
    reset_language()
    assert get_language() == "en"
    assert label("action", "eat") == "eating"
    assert tr("стресс") == "stress"
    assert get_axis_label("stress", 0.95) == "critical"


def test_english_affect_tone() -> None:
    set_language("en")
    try:
        result = interpret_affect(
            {
                "stress": 0.92,
                "arousal": 0.88,
                "valence": -0.55,
                "attachment": -0.07,
                "curiosity": 0.04,
                "trust": -0.29,
                "dominance": -0.25,
                "energy": 0.96,
                "social_drive": 0.00,
            }
        )
        assert result.tone_label == "PANIC"
        assert result.axis_labels["stress"] == "critical"
    finally:
        reset_language()


def test_cli_override_beats_environment(monkeypatch) -> None:
    monkeypatch.setenv("NOWA_LANG", "ru")
    reset_language()
    assert get_language() == "ru"
    set_language("en")
    assert get_language() == "en"
    assert tr("энергия") == "energy"
    reset_language()
