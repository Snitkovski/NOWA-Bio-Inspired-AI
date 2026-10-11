"""Warriner dashboard catalogs have matching EN and RU keys."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nowa_validation.ui_i18n import assert_catalog_parity, peek_lang, t


def test_catalog_parity() -> None:
    assert_catalog_parity()


def test_language_resolution(monkeypatch) -> None:
    monkeypatch.delenv("NOWA_LANG", raising=False)
    assert peek_lang([]) == "en"
    assert t("run", "en") == "Run Validation"
    assert t("run", "ru") == "Запустить проверку"
    monkeypatch.setenv("NOWA_LANG", "ru")
    assert peek_lang([]) == "ru"
    assert peek_lang(["--lang", "en"]) == "en"
