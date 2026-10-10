from copy import deepcopy

from stability_monitoring import StabilityMonitoringLayer


def _affect_snapshot(valence=0.0, arousal=0.0):
    return {
        "valence": valence,
        "arousal": arousal,
        "threat": 0.0,
        "curiosity": 0.0,
    }


def _background_snapshot(anxiety=0.0):
    return {
        "background_anxiety": anxiety,
        "background_tension": 0.0,
        "background_satisfaction": 0.0,
        "background_interest": 0.0,
    }


def _neuromod_snapshot(dopamine=0.1, norepinephrine=0.1, serotonin=0.1, cortisol=0.05):
    return {
        "dopamine": dopamine,
        "norepinephrine": norepinephrine,
        "serotonin": serotonin,
        "cortisol": cortisol,
    }


def _expectations_snapshot(outlook="stabilizing"):
    return {
        "expectations": [],
        "dominant_forecast": "",
        "global_outlook": outlook,
    }


def _regulation_snapshot(active=False):
    return {
        "regulation_active": active,
        "regulation_mode": "none",
        "applied_adjustments": {"background_shift": {}, "neuromodulator_shift": {}},
    }


def _update_many(
    layer,
    steps,
    affect=None,
    background=None,
    neuromodulators=None,
    expectations=None,
    regulation=None,
    semantic=None,
):
    snapshot = {}
    for _ in range(steps):
        snapshot = layer.update(
            emotional_state_snapshot=affect or _affect_snapshot(),
            affective_background_snapshot=background or _background_snapshot(),
            neuromodulators_snapshot=neuromodulators or _neuromod_snapshot(),
            expectations_snapshot=expectations or _expectations_snapshot(),
            regulation_snapshot=regulation or _regulation_snapshot(),
            semantic_emotions_snapshot=semantic or [],
        )
    return snapshot


def test_stability_monitoring_regulation_overuse():
    layer = StabilityMonitoringLayer(window_size=500, baseline_background=0.0)
    snapshot = _update_many(layer, 500, regulation=_regulation_snapshot(active=True))

    flags = snapshot["drift_flags"]
    assert flags["regulation_overuse"] is True
    assert snapshot["recommendation"] == "inspect_regulation"
    assert abs(snapshot["stability_index"] - 0.75) < 1e-9


def test_stability_monitoring_background_drift_hysteresis():
    layer = StabilityMonitoringLayer(window_size=500, baseline_background=0.0, hysteresis_windows=2)
    first = _update_many(layer, 500, background=_background_snapshot(anxiety=0.35))
    second = _update_many(layer, 1, background=_background_snapshot(anxiety=0.35))

    assert first["drift_flags"]["background_drift"] is False
    assert second["drift_flags"]["background_drift"] is True
    assert second["recommendation"] == "inspect_background"


def test_stability_monitoring_neuromodulator_drift_hysteresis():
    layer = StabilityMonitoringLayer(window_size=500, baseline_background=0.0, hysteresis_windows=2)
    first = _update_many(layer, 500, neuromodulators=_neuromod_snapshot(dopamine=0.5))
    second = _update_many(layer, 1, neuromodulators=_neuromod_snapshot(dopamine=0.5))

    assert first["drift_flags"]["neuromodulator_drift"] is False
    assert second["drift_flags"]["neuromodulator_drift"] is True
    assert second["recommendation"] == "inspect_neuromodulators"


def test_stability_monitoring_outlook_bias_recommendation():
    layer = StabilityMonitoringLayer(window_size=500, baseline_background=0.0, hysteresis_windows=2)
    first = _update_many(layer, 500, expectations=_expectations_snapshot(outlook="escalating"))
    second = _update_many(layer, 1, expectations=_expectations_snapshot(outlook="escalating"))

    assert first["drift_flags"]["outlook_bias"] is False
    assert second["drift_flags"]["outlook_bias"] is True
    assert second["recommendation"] == "inspect_expectations"
    assert abs(second["stability_index"] - 0.90) < 1e-9


def test_stability_monitoring_dominant_emotion_lock_recommendation():
    layer = StabilityMonitoringLayer(window_size=500, baseline_background=0.0, hysteresis_windows=2)
    semantic = [{"emotion": "fear", "activation": 0.60, "stability": 0.8, "obsessive": False}]
    _update_many(layer, 500, semantic=semantic, expectations=_expectations_snapshot(outlook="stabilizing"))
    second = _update_many(layer, 1, semantic=semantic, expectations=_expectations_snapshot(outlook="stabilizing"))

    assert second["drift_flags"]["dominant_emotion_lock"] is True
    assert second["recommendation"] == "inspect_memory"


def test_stability_monitoring_read_only_inputs():
    layer = StabilityMonitoringLayer(window_size=500, baseline_background=0.0)
    affect = _affect_snapshot()
    background = _background_snapshot(anxiety=0.2)
    neuromod = _neuromod_snapshot()
    expectations = _expectations_snapshot(outlook="volatile")
    regulation = _regulation_snapshot(active=True)
    semantic = [{"emotion": "joy", "activation": 0.7, "stability": 0.8, "obsessive": False}]

    affect_src = deepcopy(affect)
    background_src = deepcopy(background)
    neuromod_src = deepcopy(neuromod)
    expectations_src = deepcopy(expectations)
    regulation_src = deepcopy(regulation)
    semantic_src = deepcopy(semantic)

    layer.update(
        emotional_state_snapshot=affect,
        affective_background_snapshot=background,
        neuromodulators_snapshot=neuromod,
        expectations_snapshot=expectations,
        regulation_snapshot=regulation,
        semantic_emotions_snapshot=semantic,
    )

    assert affect == affect_src
    assert background == background_src
    assert neuromod == neuromod_src
    assert expectations == expectations_src
    assert regulation == regulation_src
    assert semantic == semantic_src


def test_stability_monitoring_background_baseline_uses_warmup_median():
    layer = StabilityMonitoringLayer(window_size=500)

    layer.update(
        emotional_state_snapshot=_affect_snapshot(),
        affective_background_snapshot=_background_snapshot(anxiety=0.95),
        neuromodulators_snapshot=_neuromod_snapshot(),
        expectations_snapshot=_expectations_snapshot(),
        regulation_snapshot=_regulation_snapshot(),
    )
    _update_many(layer, 499, background=_background_snapshot(anxiety=0.20))

    assert abs(float(layer.baseline_background or 0.0) - 0.20) < 1e-9
