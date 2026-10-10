from conflict_arbitration import ConflictArbitrationLayer
from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from selector import ActionSelector
from storage import AgentStorage


def test_conflict_arbitration_save_load(tmp_path):
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a"])

    layer = ConflictArbitrationLayer(
        control_cost_limit=0.18,
        control_cost_gain=0.10,
        control_cost_decay=0.0,
    )
    for _ in range(20):
        layer.register_outcome(reward_signal=-1.0, prediction_error=1.0)
    for _ in range(4):
        layer.arbitrate(
            go_signals=[0.34, 0.33, 0.33],
            top2_gap=0.01,
            policy_entropy=0.98,
            novelty_score=0.85,
            pattern_completion_confidence=0.10,
            prediction_error=1.0,
            working_memory_load=0.85,
            task_complexity=0.85,
        )

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        hip,
        cortex,
        selector,
        conflict_arbitration=layer,
        filename="conflict_arbitration.pkl",
    )

    restored = ConflictArbitrationLayer()
    storage.load_agent(
        hip,
        cortex,
        selector,
        path,
        conflict_arbitration=restored,
    )

    src = layer.snapshot()
    dst = restored.snapshot()
    assert dst.get("control_mode") == src.get("control_mode")
    assert abs(float(dst.get("recent_failure_rate", 0.0)) - float(src.get("recent_failure_rate", 0.0))) < 1e-9
    assert int(dst.get("forced_downshift_count", 0)) == int(src.get("forced_downshift_count", 0))
    assert isinstance(dst.get("last_output"), dict)

