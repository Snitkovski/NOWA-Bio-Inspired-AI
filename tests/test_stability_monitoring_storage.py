from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from selector import ActionSelector
from stability_monitoring import StabilityMonitoringLayer
from storage import AgentStorage


def _update_many(layer, steps):
    for _ in range(steps):
        layer.update(
            emotional_state_snapshot={"valence": 0.0, "arousal": 0.0},
            affective_background_snapshot={
                "background_anxiety": 0.0,
                "background_tension": 0.0,
                "background_satisfaction": 0.0,
                "background_interest": 0.0,
            },
            neuromodulators_snapshot={
                "dopamine": 0.1,
                "norepinephrine": 0.1,
                "serotonin": 0.1,
                "cortisol": 0.05,
            },
            expectations_snapshot={"expectations": [], "dominant_forecast": "", "global_outlook": "stabilizing"},
            regulation_snapshot={"regulation_active": True, "regulation_mode": "stabilizing"},
            semantic_emotions_snapshot=[],
        )


def test_stability_monitoring_save_load(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a"])

    layer = StabilityMonitoringLayer(window_size=500, baseline_background=0.0)
    _update_many(layer, 500)
    src_snapshot = layer.snapshot()

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        emotional_stability=layer,
        filename="stability_monitoring.pkl",
    )

    restored = StabilityMonitoringLayer()
    storage.load_agent(
        hip,
        cortex,
        selector,
        path,
        emotional_stability=restored,
    )

    dst_snapshot = restored.snapshot()
    assert abs(float(dst_snapshot.get("stability_index", 0.0)) - float(src_snapshot.get("stability_index", 0.0))) < 1e-9
    assert dict(dst_snapshot.get("drift_flags", {})) == dict(src_snapshot.get("drift_flags", {}))
    assert dst_snapshot.get("recommendation") == src_snapshot.get("recommendation")
    assert int(dst_snapshot.get("metrics", {}).get("sample_count", 0)) >= 500

