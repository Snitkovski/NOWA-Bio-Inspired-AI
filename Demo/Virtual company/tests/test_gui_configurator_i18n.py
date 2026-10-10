"""Bilingual strings for the Role Configurator GUI."""

from nowa_body.gui_configurator_i18n import HELP_TOPICS, I18n, STRINGS, assert_string_parity


def test_en_ru_key_parity():
    assert_string_parity()
    assert set(STRINGS) == {"en", "ru"}


def test_help_topics_have_instruction_copy():
    assert_string_parity()
    expected = {
        "help.button",
        "help.close",
        *(f"help.{topic}.title" for topic in HELP_TOPICS),
        *(f"help.{topic}.body" for topic in HELP_TOPICS),
    }
    assert expected <= set(STRINGS["en"])
    for topic in HELP_TOPICS:
        for lang in ("en", "ru"):
            title = STRINGS[lang][f"help.{topic}.title"]
            body = STRINGS[lang][f"help.{topic}.body"]
            assert title.strip()
            assert "\n" in body
            assert len(body) > 250
            assert "{" not in body
            assert "}" not in body
    tools_en = STRINGS["en"]["help.tools.body"].lower()
    tools_ru = STRINGS["ru"]["help.tools.body"].lower()
    assert "tag" in tools_en
    assert "procurement" in tools_en
    assert "тег" in tools_ru
    assert "закупки" in tools_ru


def test_format_placeholders_survive_translation():
    i18n = I18n(lang="ru")
    text = i18n.t("list.meta", domain="procurement", tools=4, lessons=8, when="вчера")
    assert "procurement" in text
    assert "4" in text
    assert "8" in text


def test_language_switch_changes_title_adjacent_strings():
    i18n = I18n(lang="en")
    en = i18n.t("list.new")
    i18n.set_language("ru")
    ru = i18n.t("list.new")
    assert en != ru
    assert i18n.t("app.title")


def test_employee_ui_says_employee_not_agent():
    for lang, forbidden in (("en", "agent"), ("ru", "агент")):
        for key, value in STRINGS[lang].items():
            if not str(key).startswith("emp."):
                continue
            lowered = str(value).lower()
            assert forbidden not in lowered, f"{lang} {key} contains {forbidden!r}"
