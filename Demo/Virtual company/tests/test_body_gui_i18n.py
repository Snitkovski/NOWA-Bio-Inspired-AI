"""Bilingual strings for the Body Layer lab GUI."""

from nowa_body.gui_i18n import I18n, STRINGS, assert_string_parity


def test_en_ru_key_parity():
    assert_string_parity()
    assert set(STRINGS) == {"en", "ru"}


def test_format_placeholders_survive_translation():
    i18n = I18n(lang="ru")
    text = i18n.t("status.ticked", tick=3, action="wait_and_monitor", approval="pending")
    assert "3" in text
    assert "wait_and_monitor" in text


def test_language_switch_changes_title_key():
    i18n = I18n(lang="en")
    en = i18n.t("app.title")
    i18n.set_language("ru")
    ru = i18n.t("app.title")
    assert en != ru
    assert "NOWA" in en
    assert "NOWA" in ru
