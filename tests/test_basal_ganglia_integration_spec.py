import random
import math

from src.autonomous_organism import InternalSimulationLoop
from src.basal_ganglia import BasalGangliaGate, NO_ACTION, ThalamicGate
from src.selector import ActionSelector


def test_spec_tc1_high_dopamine_amplifies_go_path():
    bg = BasalGangliaGate()
    pressure = {"approach": 0.35}

    low_da = bg.process(
        pressure_vector=pressure,
        dopamine_level=0.0,
        cortisol_level=0.1,
        norepinephrine_level=0.1,
        habit_strengths={},
        aversive_signal=0.0,
    )
    high_da = bg.process(
        pressure_vector=pressure,
        dopamine_level=1.0,
        cortisol_level=0.1,
        norepinephrine_level=0.1,
        habit_strengths={},
        aversive_signal=0.0,
    )

    assert high_da["approach"] > low_da["approach"]


def test_spec_tc2_high_cortisol_suppresses_action():
    bg = BasalGangliaGate()
    pressure = {"approach": 0.35}

    low_cort = bg.process(
        pressure_vector=pressure,
        dopamine_level=0.3,
        cortisol_level=0.0,
        norepinephrine_level=0.1,
        habit_strengths={},
        aversive_signal=0.0,
    )
    high_cort = bg.process(
        pressure_vector=pressure,
        dopamine_level=0.3,
        cortisol_level=1.0,
        norepinephrine_level=0.1,
        habit_strengths={},
        aversive_signal=0.0,
    )

    assert high_cort["approach"] < low_cort["approach"]


def test_spec_tc3_habit_dominates_under_weak_pressure():
    bg = BasalGangliaGate()
    gated = bg.process(
        pressure_vector={"habitual": 0.01, "other": 0.02},
        dopamine_level=0.1,
        cortisol_level=0.1,
        norepinephrine_level=0.1,
        habit_strengths={"habitual": 1.0, "other": 0.0},
        aversive_signal=0.0,
    )

    assert gated["habitual"] > gated["other"]


def test_spec_tc4_zero_pressure_plus_high_cortisol_is_no_action():
    bg = BasalGangliaGate()
    thalamus = ThalamicGate(base_temperature=1.0, min_temperature=0.05, ne_gain=1.0)

    gated = bg.process(
        pressure_vector={"a": 0.0, "b": 0.0},
        dopamine_level=0.2,
        cortisol_level=1.0,
        norepinephrine_level=0.1,
        habit_strengths={"a": 0.0, "b": 0.0},
        aversive_signal=0.8,
    )
    action = thalamus.select(gated, norepinephrine_level=0.1)

    assert action == NO_ACTION


def test_spec_tc5_simulation_and_real_pipeline_choose_same_action():
    selector = ActionSelector(actions=["approach", "avoid"])
    bg = BasalGangliaGate(temperature=1.0)
    thalamus = ThalamicGate(base_temperature=0.02, min_temperature=0.01, ne_gain=0.0)
    neuromodulators = {"dopamine": 0.4, "cortisol": 0.05, "norepinephrine": 0.1}

    real_pressures = selector.compute_pressures(
        [],
        [],
        intent_pressure={"approach": 2.0},
        affect_modifier=1.0,
    )
    random.seed(19)
    real_gated = bg.process(
        pressure_vector=real_pressures,
        dopamine_level=neuromodulators["dopamine"],
        cortisol_level=neuromodulators["cortisol"],
        norepinephrine_level=neuromodulators["norepinephrine"],
        habit_strengths={},
        aversive_signal=0.0,
    )
    real_action = thalamus.select(real_gated, norepinephrine_level=neuromodulators["norepinephrine"])

    loop = InternalSimulationLoop(
        affective_core=None,
        cognitive_core=selector,
        decision_engine=selector,
        memory_system=None,
        basal_ganglia=bg,
        thalamic_gate=thalamus,
        neuromodulator_state=neuromodulators,
        habit_strength_provider=lambda action_ids: {str(a): 0.0 for a in list(action_ids or [])},
    )
    simulated_state = {
        "active_drive": "curiosity",
        "recalls": [],
        "cortical_patterns": [],
        "intent_pressure": {"approach": 2.0},
        "affect_modifier": 1.0,
        "axes": {"stress": 0.0},
        "neuromodulators": dict(neuromodulators),
    }
    random.seed(19)
    simulated_action = loop._propose_action(simulated_state)

    assert simulated_action == real_action


def test_thalamic_gate_ignores_non_finite_weights():
    thalamus = ThalamicGate(base_temperature=1.0, min_temperature=0.05, ne_gain=1.0)
    action = thalamus.select(
        gated_scores={"bad_nan": float("nan"), "bad_inf": float("inf"), "ok": 0.25},
        norepinephrine_level=0.1,
        exploration_bias=0.0,
    )
    assert action == "ok"


def test_basal_ganglia_process_returns_finite_non_negative_scores():
    bg = BasalGangliaGate()
    gated = bg.process(
        pressure_vector={"a": float("nan"), "b": float("inf"), "c": -0.2},
        dopamine_level=float("nan"),
        cortisol_level=float("inf"),
        norepinephrine_level=float("nan"),
        habit_strengths={"a": float("nan"), "b": float("inf"), "c": 0.2},
        aversive_signal=float("inf"),
        channel_modulators={
            "a": {"go_weight": float("nan"), "nogo_weight": float("inf")},
            "b": {"go_weight": float("inf"), "nogo_weight": float("nan")},
        },
    )
    assert set(gated.keys()) == {"a", "b", "c"}
    for value in gated.values():
        assert math.isfinite(value)
        assert value >= 0.0
