import tempfile

from affect import AffectiveState
from affective_persistence import AffectivePersistenceLayer
from neuromodulators import NeuromodulatorState
from temporal import TemporalLevels
from selector import ActionSelector
from experience import Event, Path, EventType, Experience
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from storage import AgentStorage


def test_persistence_trace_survives_after_signal():
    layer = AffectivePersistenceLayer()
    affect = AffectiveState(threat=1.0)
    nm = NeuromodulatorState()
    temporal = TemporalLevels()

    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())
    trace = layer.get_trace("anxiety")
    assert trace is not None
    assert trace.intensity > 0.0

    # Signal disappears, trace should persist > 0
    affect.threat = 0.0
    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())
    trace = layer.get_trace("anxiety")
    assert trace is not None
    assert trace.intensity > 0.0


def test_trace_decay_monotonic():
    layer = AffectivePersistenceLayer()
    affect = AffectiveState(threat=1.0)
    nm = NeuromodulatorState()
    temporal = TemporalLevels()

    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())

    affect.threat = 0.0
    temporal.log(affect.snapshot())
    prev = layer.get_trace("anxiety").intensity
    for _ in range(5):
        layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())
        curr = layer.get_trace("anxiety").intensity
        assert curr <= prev + 1e-9
        prev = curr


def test_accumulation_non_linear_growth():
    layer = AffectivePersistenceLayer()
    affect = AffectiveState(threat=0.8)
    nm = NeuromodulatorState()
    temporal = TemporalLevels()

    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())
    first = layer.get_trace("anxiety").intensity

    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())
    second = layer.get_trace("anxiety").intensity

    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())
    third = layer.get_trace("anxiety").intensity

    # Non-linear: increments should change over time (not perfectly linear)
    inc1 = second - first
    inc2 = third - second
    assert third > second > first
    assert abs(inc2 - inc1) > 1e-6


def test_no_action_influence_from_traces():
    selector = ActionSelector(actions=["action_a", "action_b"], confidence_threshold=0.5)
    affect = AffectiveState(valence=0.0, arousal=0.0, threat=0.0, curiosity=0.1)

    # Build a single experience that biases toward action_a
    path = Path().add_event(Event("ctx", event_type=EventType.CONTEXT))
    path = path.add_event(Event("action:action_a", event_type=EventType.ACTION))
    exp = Experience(path, intensity=1.0)

    hip_exps = [exp]
    cortex_patterns = []

    action_before = selector.choose(
        hip_exps, cortex_patterns, intent_pressure=None, affect_modifier=affect.get_action_pressure_modifier()
    )

    layer = AffectivePersistenceLayer()
    nm = NeuromodulatorState()
    temporal = TemporalLevels()
    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())

    action_after = selector.choose(
        hip_exps, cortex_patterns, intent_pressure=None, affect_modifier=affect.get_action_pressure_modifier()
    )

    assert action_before == action_after == "action_a"


def test_save_load_affective_persistence_roundtrip():
    hip = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions=["a", "b"])
    layer = AffectivePersistenceLayer()
    affect = AffectiveState(threat=1.0)
    temporal = TemporalLevels()
    nm = NeuromodulatorState()

    temporal.log(affect.snapshot())
    layer.update(affect, neuromodulators=nm, temporal_levels=temporal.get_levels())

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AgentStorage(save_dir=tmpdir)
        filepath = storage.save_agent(
            hip,
            cortex,
            selector,
            affective_persistence=layer,
            filename="affective_persistence.pkl",
        )

        new_layer = AffectivePersistenceLayer()
        storage.load_agent(
            hip,
            cortex,
            selector,
            filepath,
            affective_persistence=new_layer,
        )

        restored = new_layer.get_trace("anxiety")
        assert restored is not None
        assert restored.intensity > 0.0
