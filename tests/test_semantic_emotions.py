from affective_space import AffectiveSpace
from semantic_emotions import SemanticEmotionsLayer


def _by_name(items, name):
    for item in items:
        if item.get("emotion") == name:
            return item
    return None


def test_semantic_emotions_tc1_love_sadness():
    space = AffectiveSpace(
        axes={
            "attachment": 0.9,
            "pleasure": 0.7,
            "pain": 0.6,
            "vulnerability": 0.8,
            "arousal": 0.0,
        },
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    layer = SemanticEmotionsLayer()
    active = layer.update_from_space(space)

    love = _by_name(active, "love")
    sadness = _by_name(active, "sadness")

    assert love is not None
    assert sadness is not None
    assert love["activation"] > 0.6
    assert sadness["activation"] > 0.3
    assert love["stability"] >= 0.99


def test_semantic_emotions_tc2_obsessive_hate():
    space = AffectiveSpace(
        axes={
            "rejection": 0.8,
            "arousal": 0.9,
            "focus": 1.0,
        },
        inertia={"rejection": 0.9, "arousal": 0.9, "focus": 0.9},
        fall_rate={"rejection": 0.1, "arousal": 0.1, "focus": 0.1},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    layer = SemanticEmotionsLayer()
    active = layer.update_from_space(space)

    hate = _by_name(active, "hate")
    assert hate is not None
    assert hate["activation"] > 0.0
    assert hate["obsessive"] is True


def test_semantic_emotions_tc3_pleasure_rest():
    space = AffectiveSpace(
        axes={
            "pleasure": 0.6,
            "relaxation": 0.7,
            "arousal": 0.1,
            "pain": 0.0,
        },
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)

    layer = SemanticEmotionsLayer()
    active = layer.update_from_space(space)

    pleasure_rest = _by_name(active, "pleasure_rest")
    assert pleasure_rest is not None
    assert pleasure_rest["activation"] > 0.6
