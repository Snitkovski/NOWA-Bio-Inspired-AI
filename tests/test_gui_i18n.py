"""Display-language coverage for the core Tk interface."""

from gui_i18n import (
    action_label,
    assert_catalog_parity,
    axis_label,
    drive_label,
    format_auto_thought,
    reset_language,
    set_language,
    tr,
)


def setup_function():
    reset_language()


def teardown_function():
    reset_language()


def test_core_gui_catalog_parity():
    assert_catalog_parity()


def test_affect_labels_hide_raw_ids():
    set_language("en")
    assert axis_label("bg_anxiety") == "Anxiety"
    assert axis_label("background_tension") == "Tension"
    assert "bg_" not in axis_label("bg_satisfaction")
    set_language("ru")
    assert axis_label("bg_anxiety") == "Тревога"
    assert axis_label("valence") == "Валентность"
    assert axis_label("bg_anxiety") != "bg_anxiety"


def test_action_and_drive_labels_keep_ids_out_of_the_sentence():
    set_language("en")
    assert action_label("сказать_привет") == "say hello"
    assert drive_label("social_drive") == "social drive"
    line = format_auto_thought("curiosity", "сказать_привет", 0.4)
    assert line == "[AUTO] think: drive=curiosity | action=say hello | confidence=0.40"
    assert "сказать_привет" not in line
    set_language("ru")
    line = format_auto_thought("curiosity", "отказаться", 0.4)
    assert "любопытство" in line
    assert "отказаться" in line
    assert "мысль" in line
    assert "уверенность" in line


def test_window_chrome_switches_language():
    set_language("en")
    assert tr("Диалог:") == "Dialog:"
    assert tr("Отправить") == "Send"
    assert tr("❤️ Аффективное состояние") == "❤️ Affective state"
    assert tr("NOWA - Cognitive Agent Interface") == "NOWA - Cognitive Agent Interface"
    assert tr("🤖 NOWA - Neural Memory Agent") == "🤖 NOWA - Neural Memory Agent"
    assert tr("Тревога:") == "Anxiety:"
    set_language("ru")
    assert tr("Диалог:") == "Диалог:"
    assert tr("Отправить") == "Отправить"
    assert tr("Semantic Emotions:") == "Смысловые эмоции:"
    assert tr("NOWA - Cognitive Agent Interface") == "NOWA — интерфейс когнитивного агента"
    assert tr("🤖 NOWA - Neural Memory Agent") == "🤖 NOWA — агент нейронной памяти"
    assert tr("Тревога:") == "Тревога:"
