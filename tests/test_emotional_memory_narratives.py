from affective_space import AffectiveSpace
from semantic_emotions import SemanticEmotionsLayer
from emotional_memory_narratives import EmotionalMemoryNarrativesLayer


def _update(layer, sem, space, background, t, lifetime=10000.0):
    sem.update_from_space(space)
    layer.update_from_layers(
        semantic_emotions=sem,
        space=space,
        background=background,
        agent_lifetime=float(lifetime),
        timestamp=t,
    )


def test_emotional_memory_tc1_recurrent_sadness():
    sad_space = AffectiveSpace(
        axes={"pain": 0.8, "attachment": 0.6, "arousal": 0.1},
        noise_sigma=0.0,
    )
    sad_space.last_axes = dict(sad_space.axes)

    neutral_space = AffectiveSpace(axes={"pleasure": 0.0}, noise_sigma=0.0)
    neutral_space.last_axes = dict(neutral_space.axes)

    sem = SemanticEmotionsLayer()
    layer = EmotionalMemoryNarrativesLayer()

    _update(layer, sem, sad_space, {}, 0.0)
    _update(layer, sem, neutral_space, {}, 10.0)
    _update(layer, sem, sad_space, {}, 20.0)
    _update(layer, sem, neutral_space, {}, 30.0)
    _update(layer, sem, sad_space, {}, 40.0)

    text = layer.describe_brief(max_fragments=3)
    assert "Часто возникает грусть" in text


def test_emotional_memory_tc2_obsessive_pattern():
    space = AffectiveSpace(
        axes={"rejection": 0.8, "arousal": 0.9, "focus": 1.0},
        inertia={"rejection": 0.9, "arousal": 0.9, "focus": 0.9},
        fall_rate={"rejection": 0.1, "arousal": 0.1, "focus": 0.1},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    sem = SemanticEmotionsLayer()
    layer = EmotionalMemoryNarrativesLayer()
    for t in (0.0, 10.0, 20.0):
        _update(layer, sem, space, {}, float(t))

    patterns = layer.snapshot().get("patterns", [])
    assert any(p.get("emotion") == "hate" and p.get("obsessive") for p in patterns)


def test_emotional_memory_tc3_mixed_joy_tension():
    space = AffectiveSpace(
        axes={"pleasure": 0.8, "arousal": 0.7, "pain": 0.0},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    sem = SemanticEmotionsLayer()
    layer = EmotionalMemoryNarrativesLayer()
    for t in (0.0, 10.0, 20.0):
        _update(layer, sem, space, {"background_tension": 0.8}, float(t))

    text = layer.describe_brief(max_fragments=3).lower()
    assert "радость" in text
    assert "напряжение" in text


def test_emotional_memory_tc4_no_future_leakage():
    space = AffectiveSpace(
        axes={"pleasure": 0.6, "arousal": 0.5, "pain": 0.0},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    sem = SemanticEmotionsLayer()
    layer = EmotionalMemoryNarrativesLayer()
    for t in (0.0, 10.0, 20.0):
        _update(layer, sem, space, {"background_tension": 0.2}, float(t))

    text = layer.describe_brief(max_fragments=3).lower()
    forbidden = ["будет", "будущ", "следующ", "потом", "завтра", "скоро", "ожида", "прогноз"]
    assert all(word not in text for word in forbidden)


def test_emotional_memory_tc5_stability_effect():
    space = AffectiveSpace(
        axes={"pleasure": 0.7, "arousal": 0.6, "pain": 0.0},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    sem = SemanticEmotionsLayer()
    layer = EmotionalMemoryNarrativesLayer()
    for t in (0.0, 10.0, 20.0):
        _update(layer, sem, space, {}, float(t))

    stability_frags = [f for f in layer.narrative_fragments if f.get("tag") == "stability"]
    assert stability_frags
    assert stability_frags[0].get("confidence", 0.0) >= 0.7


def test_emotional_memory_tc6_direction_shift():
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
    layer = EmotionalMemoryNarrativesLayer()
    layer.activation_threshold = 0.4

    lifetime = 1000.0
    _update(layer, sem, sad_space, {}, 100.0, lifetime=lifetime)
    _update(layer, sem, sad_space, {}, 120.0, lifetime=lifetime)
    _update(layer, sem, joy_space, {}, 900.0, lifetime=lifetime)

    text = layer.describe_brief(max_fragments=3)
    assert "грусть" in text
    assert (
        ("раннем этапе" in text)
        or ("последнее время" in text)
        or ("Ранее преобладала" in text)
    )
