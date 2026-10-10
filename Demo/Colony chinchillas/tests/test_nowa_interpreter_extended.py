from __future__ import annotations

from colony_agent import ChinchillaAgent
from colony_gui import InspectorData, build_inspector_data_from_agent, build_inspector_data_from_memorial
from colony_gui.nowa_interpreter import (
    AXIS_COLORS,
    AffectInterpretation,
    HabitPattern,
    NeuroProfile,
    ValueLayerSnapshot,
    build_nowa_interpretation,
    build_personality_readout,
    extract_significant_episodes,
    extract_top_habits,
    get_axis_label,
    interpret_affect,
    interpret_neuro,
    reward_label,
)
from death_registry import DeathRegistry


def test_tc01_affect_tone_panic() -> None:
    axes = {
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

    result = interpret_affect(axes)

    assert result.tone_label == "ПАНИКА"
    assert result.tone_color[0] > 170
    assert "стресс" in result.summary.lower()
    assert result.axis_labels["stress"] == "критический"
    assert result.axis_labels["curiosity"] in ("подавлено", "отсутствует")


def test_tc02_neuro_profile_stress_activation() -> None:
    nm = {
        "dopamine": 0.00,
        "serotonin": 0.00,
        "norepinephrine": 0.87,
        "cortisol": 0.78,
        "acetylcholine": 0.91,
    }

    result = interpret_neuro(nm)

    assert result.profile_label == "СТРЕССОВАЯ АКТИВАЦИЯ"
    assert "норадреналин" in result.summary.lower()
    assert len(result.interactions) >= 1
    assert any("кортизол" in item.lower() for item in result.interactions)


def test_tc03_neuro_profile_dopamine_peak() -> None:
    nm = {
        "dopamine": 0.72,
        "serotonin": 0.48,
        "norepinephrine": 0.35,
        "cortisol": 0.18,
        "acetylcholine": 0.42,
    }

    result = interpret_neuro(nm)

    assert result.profile_label == "ДОФАМИНОВЫЙ ПИК"
    assert result.modulator_labels["dopamine"] == "активная мотивация"
    assert result.modulator_labels["cortisol"] in ("минимальный", "лёгкий тонус")


def test_tc04_axis_labels_for_stress() -> None:
    assert get_axis_label("stress", 0.95) == "критический"
    assert get_axis_label("stress", 0.72) == "высокий"
    assert get_axis_label("stress", 0.45) == "умеренный"
    assert get_axis_label("stress", 0.20) == "низкий"
    assert get_axis_label("stress", 0.05) == "минимальный"


def test_tc05_axis_labels_for_valence() -> None:
    assert get_axis_label("valence", -0.75) == "тяжёлый"
    assert get_axis_label("valence", -0.40) == "негативный"
    assert get_axis_label("valence", 0.10) == "нейтральный"
    assert get_axis_label("valence", 0.40) == "позитивный"
    assert get_axis_label("valence", 0.75) == "радостный"


def test_tc06_extract_top_habits() -> None:
    patterns = [
        {
            "context_tokens": ["food_low"],
            "action": "eat",
            "consequence": "success",
            "strength": 0.89,
            "activation_count": 47,
        },
        {
            "context_tokens": ["wakefulness_high"],
            "action": "sleep",
            "consequence": "success",
            "strength": 0.71,
            "activation_count": 31,
        },
        {
            "context_tokens": ["stress"],
            "action": "hide",
            "consequence": "success",
            "strength": 0.64,
            "activation_count": 28,
        },
    ]

    habits = extract_top_habits(patterns)

    assert len(habits) == 3
    assert habits[0].action == "eat"
    assert habits[0].strength == 0.89
    assert habits[0].activation_count == 47
    assert habits[1].action == "sleep"


def test_tc07_personality_anxious_loner() -> None:
    habits = [
        HabitPattern(["стресс"], "hide", 0.85, 47, "success"),
        HabitPattern(["усталость"], "rest", 0.71, 31, "success"),
        HabitPattern(["скука"], "groom_self", 0.58, 22, "success"),
    ]
    affect = AffectInterpretation("ПАНИКА", (210, 60, 50), "...", {})
    neuro = NeuroProfile("СТРЕССОВАЯ АКТИВАЦИЯ", "...", {}, [])

    result = build_personality_readout(habits, affect, neuro)

    assert result.character_label == "ТРЕВОЖНЫЙ ОДИНОЧКА"
    assert "избегани" in result.summary.lower() or "стресс" in result.summary.lower()


def test_tc08_extract_significant_episodes() -> None:
    episodes = [
        {
            "timestamp": 100.0,
            "action": "eat",
            "reward": 0.41,
            "encoding_strength": 0.8,
            "context_tokens": ["food_low"],
            "consequence": "success",
        },
        {
            "timestamp": 90.0,
            "action": "explore",
            "reward": 0.01,
            "encoding_strength": 0.2,
            "context_tokens": ["bored"],
            "consequence": "neutral",
        },
        {
            "timestamp": 80.0,
            "action": "socialize",
            "reward": -0.23,
            "encoding_strength": 0.6,
            "context_tokens": ["stranger_nearby"],
            "consequence": "rejected",
        },
        {
            "timestamp": 70.0,
            "action": "drink",
            "reward": 0.19,
            "encoding_strength": 0.5,
            "context_tokens": ["water_critical"],
            "consequence": "success",
        },
        {
            "timestamp": 60.0,
            "action": "hide",
            "reward": 0.12,
            "encoding_strength": 0.4,
            "context_tokens": ["stress"],
            "consequence": "success",
        },
        {
            "timestamp": 50.0,
            "action": "rest",
            "reward": 0.00,
            "encoding_strength": 0.1,
            "context_tokens": [],
            "consequence": "neutral",
        },
    ]

    result = extract_significant_episodes(episodes, n=5)

    assert result[0].action == "eat"
    assert len(result) == 5
    significant_actions = [episode.action for episode in result]
    if "explore" in significant_actions:
        assert significant_actions.index("explore") > 2


def test_tc09_build_nowa_interpretation_empty_data() -> None:
    empty_data = InspectorData(
        agent_id="test",
        display_name="G0A1",
        is_deceased=False,
        sex="F",
        generation=0,
        parents=(None, None),
        age=100.0,
        lived_steps=100,
        cause_of_death="",
    )

    result = build_nowa_interpretation(empty_data)

    assert result is not None
    assert result.affect is not None
    assert result.neuro is not None
    assert isinstance(result.habits, list)
    assert isinstance(result.recent_episodes, list)
    assert result.personality is not None


def test_tc10_axis_colors_cover_required_axes() -> None:
    required_axes = [
        "stress",
        "arousal",
        "valence",
        "attachment",
        "curiosity",
        "trust",
        "dominance",
        "energy",
        "social_drive",
        "dopamine",
        "serotonin",
        "norepinephrine",
        "cortisol",
        "acetylcholine",
        "wakefulness",
        "sleep_pressure",
        "circadian",
        "alertness",
    ]
    for axis in required_axes:
        assert axis in AXIS_COLORS, f"Missing color for {axis}"
        color = AXIS_COLORS[axis]
        assert len(color) == 3
        assert all(0 <= channel <= 255 for channel in color)


def test_tc11_neuro_interactions_for_g0a1sf_state() -> None:
    nm_g0a1sf = {
        "dopamine": 0.00,
        "serotonin": 0.00,
        "norepinephrine": 0.87,
        "cortisol": 0.78,
        "acetylcholine": 0.91,
    }

    result = interpret_neuro(nm_g0a1sf)

    assert len(result.interactions) >= 2
    interaction_text = " ".join(result.interactions).lower()
    assert "кортизол" in interaction_text
    assert "дофамин" in interaction_text


def test_tc12_value_layer_snapshot_top_actions() -> None:
    snap = ValueLayerSnapshot(
        level=0,
        top_actions=[("eat", 0.72), ("drink", 0.43), ("sleep", 0.28)],
        raw_values={"eat": 0.72, "drink": 0.43, "sleep": 0.28, "explore": 0.15},
    )

    assert snap.top_actions[0] == ("eat", 0.72)
    assert len(snap.top_actions) <= 3


def test_tc13_deceased_agent_has_no_value_layers() -> None:
    registry = DeathRegistry()
    agent = ChinchillaAgent(sex="F", generation=0)
    registry.register_birth(agent, 0.0)
    memorial = registry.register_death(agent, 100.0, {})

    data = build_inspector_data_from_memorial(memorial, "G0A1SF")
    interp = build_nowa_interpretation(data)

    assert interp.value_layers == []


def test_tc14_personality_explorer() -> None:
    habits = [
        HabitPattern(["bored"], "explore", 0.82, 55, "neutral"),
        HabitPattern(["energy_high"], "run_wheel", 0.74, 42, "success"),
        HabitPattern(["food_ok"], "explore", 0.61, 38, "neutral"),
    ]
    affect = AffectInterpretation("ЛЮБОПЫТСТВО", (85, 163, 143), "...", {})
    neuro = NeuroProfile("ДОФАМИНОВЫЙ ПИК", "...", {}, [])

    result = build_personality_readout(habits, affect, neuro)

    assert result.character_label == "ИССЛЕДОВАТЕЛЬ"


def test_tc15_reward_labels() -> None:
    text, color = reward_label(0.45)
    assert "+" in text
    assert color[1] > color[0]

    text2, color2 = reward_label(-0.30)
    assert "✗" in text2 or "-" in text2
    assert color2[0] > color2[1]

    _text3, color3 = reward_label(0.02)
    assert color3[0] > 100 and abs(color3[0] - color3[1]) < 40


def test_build_inspector_data_populates_nowa_interpretation() -> None:
    agent = ChinchillaAgent(sex="F", generation=0)
    data = build_inspector_data_from_agent(agent, "G0A1SF")

    assert data.nowa_interpretation is not None
    assert data.nowa_interpretation.affect is not None
