from affective_space import AffectiveSpace
from semantic_emotions import SemanticEmotionsLayer
from emotional_memory_narratives import EmotionalMemoryNarrativesLayer
from emotional_expectations import EmotionalExpectationsLayer


def _update_memory(layer, sem, space, background, t, lifetime=1000.0):
    sem.update_from_space(space)
    layer.update_from_layers(
        semantic_emotions=sem,
        space=space,
        background=background,
        agent_lifetime=float(lifetime),
        timestamp=t,
    )


def test_emotional_expectations_tc1_stable_joy():
    joy_space = AffectiveSpace(
        axes={"pleasure": 0.8, "arousal": 0.6, "pain": 0.0},
        noise_sigma=0.0,
    )
    joy_space.last_axes = dict(joy_space.axes)

    sem = SemanticEmotionsLayer()
    memory = EmotionalMemoryNarrativesLayer()
    for t in (0.0, 10.0, 20.0, 30.0):
        _update_memory(memory, sem, joy_space, {}, float(t))

    expectations = EmotionalExpectationsLayer()
    result = expectations.update(
        memory_layer=memory,
        semantic_emotions=sem,
        background={},
        agent_lifetime=1000.0,
        timestamp=40.0,
    )

    joy = next(e for e in result["expectations"] if e.get("emotion") == "joy")
    assert joy.get("trend") in ("stable", "increasing")
    assert joy.get("probability", 0.0) > 0.6


def test_emotional_expectations_tc2_direction_shift():
    sad_space = AffectiveSpace(
        axes={"pain": 0.8, "attachment": 0.6, "arousal": 0.1},
        noise_sigma=0.0,
    )
    sad_space.last_axes = dict(sad_space.axes)

    joy_space = AffectiveSpace(
        axes={"pleasure": 0.8, "arousal": 0.7, "pain": 0.0},
        noise_sigma=0.0,
    )
    joy_space.last_axes = dict(joy_space.axes)

    sem = SemanticEmotionsLayer()
    memory = EmotionalMemoryNarrativesLayer()

    lifetime = 1000.0
    _update_memory(memory, sem, sad_space, {}, 100.0, lifetime=lifetime)
    _update_memory(memory, sem, sad_space, {}, 200.0, lifetime=lifetime)
    _update_memory(memory, sem, joy_space, {}, 900.0, lifetime=lifetime)

    expectations = EmotionalExpectationsLayer()
    result = expectations.update(
        memory_layer=memory,
        semantic_emotions=sem,
        background={},
        agent_lifetime=lifetime,
        timestamp=900.0,
    )

    joy = next(e for e in result["expectations"] if e.get("emotion") == "joy")
    sadness = next(e for e in result["expectations"] if e.get("emotion") == "sadness")
    assert joy.get("trend") in {"stable", "increasing"}
    assert sadness.get("trend") in {"stable", "decreasing"}


def test_emotional_expectations_tc3_obsessive_fear():
    fear_space = AffectiveSpace(
        axes={
            "stress": 0.8,
            "arousal": 0.9,
            "stability": -0.8,
            "dominance": 0.9,
            "curiosity": 0.7,
        },
        inertia={"stress": 0.9, "arousal": 0.9, "stability": 0.9, "dominance": 0.9},
        fall_rate={"stress": 0.1, "arousal": 0.1, "stability": 0.1, "dominance": 0.1},
        noise_sigma=0.0,
    )
    fear_space.last_axes = dict(fear_space.axes)

    sem = SemanticEmotionsLayer()
    memory = EmotionalMemoryNarrativesLayer()
    for t in (0.0, 10.0, 20.0):
        _update_memory(memory, sem, fear_space, {}, float(t))

    expectations = EmotionalExpectationsLayer()
    result = expectations.update(
        memory_layer=memory,
        semantic_emotions=sem,
        background={},
        agent_lifetime=1000.0,
        timestamp=30.0,
    )

    fear = next(e for e in result["expectations"] if e.get("emotion") == "fear")
    assert fear.get("risk_of_repetition") is True
    assert fear.get("probability", 0.0) >= 0.8


def test_emotional_expectations_tc4_high_variability():
    joy_space = AffectiveSpace(
        axes={"pleasure": 0.8, "arousal": 0.7, "pain": 0.0},
        noise_sigma=0.0,
    )
    joy_space.last_axes = dict(joy_space.axes)

    sad_space = AffectiveSpace(
        axes={"pain": 0.8, "attachment": 0.6, "arousal": 0.1},
        noise_sigma=0.0,
    )
    sad_space.last_axes = dict(sad_space.axes)

    fear_space = AffectiveSpace(
        axes={"pain": 0.7, "arousal": 0.8, "vulnerability": 0.7},
        noise_sigma=0.0,
    )
    fear_space.last_axes = dict(fear_space.axes)

    sem = SemanticEmotionsLayer()
    memory = EmotionalMemoryNarrativesLayer()
    sequence = [joy_space, sad_space, fear_space, joy_space]
    for idx, space in enumerate(sequence):
        _update_memory(memory, sem, space, {}, float(idx * 10))

    expectations = EmotionalExpectationsLayer()
    result = expectations.update(
        memory_layer=memory,
        semantic_emotions=sem,
        background={},
        agent_lifetime=1000.0,
        timestamp=50.0,
    )

    assert result.get("global_outlook") == "volatile"
    top = result["expectations"][0]
    assert top.get("confidence", 1.0) < 0.6


def test_emotional_expectations_tc5_insufficient_data():
    joy_space = AffectiveSpace(
        axes={"pleasure": 0.8, "arousal": 0.6, "pain": 0.0},
        noise_sigma=0.0,
    )
    joy_space.last_axes = dict(joy_space.axes)

    sem = SemanticEmotionsLayer()
    memory = EmotionalMemoryNarrativesLayer()
    _update_memory(memory, sem, joy_space, {}, 0.0)
    _update_memory(memory, sem, joy_space, {}, 10.0)

    expectations = EmotionalExpectationsLayer()
    result = expectations.update(
        memory_layer=memory,
        semantic_emotions=sem,
        background={},
        agent_lifetime=1000.0,
        timestamp=20.0,
    )

    assert result.get("expectations") == []
    assert result.get("global_outlook") == "stabilizing"
