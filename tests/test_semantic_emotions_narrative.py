from affective_space import AffectiveSpace
from semantic_emotions import SemanticEmotionsLayer


def test_semantic_emotions_summary_interest_tension():
    space = AffectiveSpace(axes={"pleasure": 0.2}, noise_sigma=0.0)
    space.last_axes = dict(space.axes)
    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    summary = layer.describe_brief(
        space=space,
        background={"background_interest": 0.7, "background_tension": 0.7},
        max_sentences=2,
    )

    assert "смесь интереса и напряжения" in summary


def test_semantic_emotions_summary_background_anxiety():
    space = AffectiveSpace(axes={"pleasure": 0.1}, noise_sigma=0.0)
    space.last_axes = dict(space.axes)
    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    summary = layer.describe_brief(
        space=space,
        background={"background_anxiety": 0.5},
        max_sentences=2,
    )

    assert "фоновая тревога" in summary


def test_semantic_emotions_summary_attachment_conflict():
    space = AffectiveSpace(
        axes={
            "attachment": 0.8,
            "rejection": 0.6,
            "pleasure": 0.8,
            "pain": 0.7,
            "arousal": 0.6,
            "relaxation": 0.6,
        },
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)
    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    summary = layer.describe_brief(
        space=space,
        background={"background_anxiety": 0.1},
        max_sentences=2,
    )

    assert "привязанность" in summary
    assert "внутренний конфликт" in summary


def test_semantic_emotions_summary_arousal_vs_pleasure():
    space = AffectiveSpace(
        axes={"arousal": 0.8, "pleasure": 0.1, "pain": 0.0},
        noise_sigma=0.0,
    )
    space.last_axes = dict(space.axes)
    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    summary = layer.describe_brief(
        space=space,
        background={},
        max_sentences=2,
    )

    assert "больше возбуждения" in summary


def test_semantic_emotions_summary_interest_only():
    space = AffectiveSpace(axes={"pleasure": 0.2}, noise_sigma=0.0)
    space.last_axes = dict(space.axes)
    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    summary = layer.describe_brief(
        space=space,
        background={"background_interest": 0.7, "background_tension": 0.1},
        max_sentences=2,
    )

    assert "интерес" in summary


def test_semantic_emotions_summary_tension_only():
    space = AffectiveSpace(axes={"pleasure": 0.2}, noise_sigma=0.0)
    space.last_axes = dict(space.axes)
    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    summary = layer.describe_brief(
        space=space,
        background={"background_interest": 0.1, "background_tension": 0.8},
        max_sentences=2,
    )

    assert "напряжение" in summary


def test_semantic_emotions_summary_vulnerability():
    space = AffectiveSpace(axes={"vulnerability": 0.8, "pleasure": 0.2}, noise_sigma=0.0)
    space.last_axes = dict(space.axes)
    layer = SemanticEmotionsLayer()
    layer.update_from_space(space)

    summary = layer.describe_brief(
        space=space,
        background={},
        max_sentences=2,
    )

    assert "уязвим" in summary
