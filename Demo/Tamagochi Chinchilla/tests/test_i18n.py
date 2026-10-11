"""Tamagotchi EN/RU catalogs and the default English subtitle."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tama_i18n import assert_catalog_parity, get_language, reset_language, set_language, tr


def test_catalog_parity() -> None:
    assert_catalog_parity()


def test_default_english_subtitle(monkeypatch) -> None:
    monkeypatch.delenv("NOWA_LANG", raising=False)
    reset_language()
    assert get_language() == "en"
    assert tr("ест сено") == "eating hay"
    assert tr("Самочувствие") == "Wellbeing"
    set_language("ru")
    try:
        assert tr("ест сено") == "ест сено"
        assert tr("Показать состояние питомца") == "Показать состояние питомца"
    finally:
        reset_language()
