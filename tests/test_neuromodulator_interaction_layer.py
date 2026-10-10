from neuromodulators import NeuromodulatorField, NeuromodulatorState


def test_field_stays_stable_on_baseline_without_signals():
    field = NeuromodulatorField(
        dopamine=0.1,
        serotonin=0.1,
        norepinephrine=0.1,
        acetylcholine=0.1,
        baselines={
            "dopamine": 0.1,
            "serotonin": 0.1,
            "norepinephrine": 0.1,
            "acetylcholine": 0.1,
        },
    )
    before = field.snapshot()
    for _ in range(5):
        field.update(signals={"dopamine": 0.0, "serotonin": 0.0, "norepinephrine": 0.0, "acetylcholine": 0.0})
    after = field.snapshot()
    assert after == before


def test_field_high_serotonin_damps_dopamine():
    field = NeuromodulatorField(
        dopamine=0.1,
        serotonin=0.3,
        norepinephrine=0.1,
        acetylcholine=0.1,
        baselines={
            "dopamine": 0.1,
            "serotonin": 0.1,
            "norepinephrine": 0.1,
            "acetylcholine": 0.1,
        },
    )
    before_da = field.snapshot()["dopamine"]
    field.update(signals={})
    after_da = field.snapshot()["dopamine"]
    assert after_da < before_da


def test_field_high_dopamine_suppresses_ach():
    field = NeuromodulatorField(
        dopamine=0.35,
        serotonin=0.1,
        norepinephrine=0.1,
        acetylcholine=0.1,
        baselines={
            "dopamine": 0.1,
            "serotonin": 0.1,
            "norepinephrine": 0.1,
            "acetylcholine": 0.1,
        },
    )
    before_ach = field.snapshot()["acetylcholine"]
    field.update(signals={})
    after_ach = field.snapshot()["acetylcholine"]
    assert after_ach < before_ach


def test_state_interaction_layer_affects_followup_step():
    nm = NeuromodulatorState()
    nm.update_from_signals(reward=1.0, novelty=0.0, conflict=0.0)
    after_reward = nm.snapshot()

    nm.update_from_signals(
        reward=0.0,
        novelty=0.0,
        conflict=0.0,
        use_reward_for_dopamine=False,
    )
    after_coupling = nm.snapshot()

    # First step follows base signal, second step applies coupled dynamics.
    assert after_reward["dopamine"] > 0.1
    assert after_coupling["dopamine"] < after_reward["dopamine"]
    assert after_coupling["acetylcholine"] <= after_reward["acetylcholine"]


def test_state_serialization_preserves_interaction_field():
    nm = NeuromodulatorState(dopamine=0.25, serotonin=0.2, norepinephrine=0.3, acetylcholine=0.15)
    data = nm.to_dict()
    assert "interaction_field" in data
    assert isinstance(data["interaction_field"], dict)

    restored = NeuromodulatorState.from_dict(data)
    assert restored.snapshot()["dopamine"] == nm.snapshot()["dopamine"]
    assert restored.snapshot()["serotonin"] == nm.snapshot()["serotonin"]
