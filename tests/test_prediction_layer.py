from src.prediction_layer import PredictionLayer


def test_prediction_layer_predict_basic_bounds():
    p = PredictionLayer(max_pressure=0.3)
    recent = ['context:room', 'action:walk', 'action:look', 'action:walk']
    neu = {'DA': 0.2, '5-HT': 0.1}
    pressures = p.predict(context={}, recent_events=recent, affect_state=None, neuromodulators=neu, temporal_levels={'T1_discount': 1.0})

    assert isinstance(pressures, dict)
    # expected actions discovered
    assert 'walk' in pressures
    assert 'look' in pressures
    for v in pressures.values():
        assert isinstance(v, float)
        assert -0.3 <= v <= 0.3


def test_prediction_layer_predict_does_not_mutate_inputs():
    p = PredictionLayer()
    recent = ['action:one', 'action:two']
    recent_copy = list(recent)
    ctx = {'a': 1}
    ctx_copy = dict(ctx)
    p.predict(context=ctx, recent_events=recent, affect_state=None, neuromodulators={}, temporal_levels={})
    assert recent == recent_copy
    assert ctx == ctx_copy
