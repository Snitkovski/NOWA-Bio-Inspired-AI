"""Saves written on main must open after episodes moved to slots.

``tests/fixtures/agent_from_main_c3bbd62.pkl`` is an ``AgentStorage`` blob
produced on ``c3bbd62`` (before ``__slots__``). Its episodes still carry
paths and emotional traces. A second test writes and reads a blob on this
branch.
"""

from __future__ import annotations

import pickle
import random
import sys
from pathlib import Path

import pytest

from affective_space import AXES, EmotionalTrace
from agent import Agent
from experience import Event, EventType, Experience
from experience import Path as EpisodePath
from hippocampus import NOWAHippocampus, SignatureTrace
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import CortexMemory, SleepManager
from storage import AgentStorage

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "agent_from_main_c3bbd62.pkl"
FIXED_TS = 1_700_000_000.0
MAIN_EPISODES = (
    (("nest", "tag:0", "action:stop"), 0.2, 1.0, 1.0, 0.2, "ep-1"),
    (("bowl", "tag:1", "action:stop"), -0.1, 1.0, 1.0, 0.1, "ep-2"),
    (("wheel", "tag:2", "action:stop"), 0.4, 1.0, 1.0, 0.4, "ep-3"),
)


def _freeze_clock(monkeypatch) -> None:
    for module in (
        "hippocampus",
        "affective_space",
        "intent_memory",
        "agent",
        "experience",
        "sleep",
    ):
        monkeypatch.setattr(f"{module}.time.time", lambda: FIXED_TS)


def _build_agent(actions=("go", "stop", "rest"), capacity=32, seed=53) -> Agent:
    hip = NOWAHippocampus(max_experiences=capacity)
    cortex = CortexMemory()
    intent = IntentMemory()
    sleep = SleepManager(hip, cortex, intent)
    selector = ActionSelector(actions=list(actions))
    agent = Agent(hip, cortex, selector, sleep, intent, rng_seed=seed)
    for action in actions:
        agent.register_action_channel(action, go_weight=0.4, nogo_weight=0.4, habit_strength=0.1)
    sleep._rng.seed(seed)
    return agent


def _episode_rows(hip: NOWAHippocampus) -> list[tuple]:
    rows = []
    for exp in hip.experiences:
        trace = getattr(exp, "emotional_trace", None)
        rows.append(
            (
                tuple(exp.path.signature()),
                float(exp.reward),
                float(exp.intensity),
                float(exp.activation_energy),
                None if trace is None else float(trace.intensity),
                str(getattr(exp, "episode_id", "")),
            )
        )
    return rows


class _LegacyShell:
    """Pickle reducer that delivers a raw ``__dict__`` to ``__setstate__``."""

    def __init__(self, cls, state):
        self.cls = cls
        self.state = state

    def __reduce__(self):
        return (self.cls.__new__, (self.cls,), self.state)


def test_main_agent_pickle_loads_and_keeps_working(monkeypatch, tmp_path):
    assert FIXTURE.is_file()
    _freeze_clock(monkeypatch)
    agent = _build_agent()
    storage = AgentStorage(save_dir=str(tmp_path))
    storage.load_agent(
        agent.hippocampus,
        agent.cortex,
        agent.selector,
        str(FIXTURE),
        sleep_manager=agent.sleep_manager,
        affective_space=agent.affective_space,
        agent=agent,
    )

    rows = _episode_rows(agent.hippocampus)
    assert len(rows) == len(MAIN_EPISODES)
    for row, expected in zip(rows, MAIN_EPISODES):
        assert row[0] == expected[0]
        assert row[1] == pytest.approx(expected[1])
        assert row[2] == pytest.approx(expected[2])
        assert row[3] == pytest.approx(expected[3])
        assert row[4] == pytest.approx(expected[4])
        assert row[5] == expected[5]
        assert row[0][0] is sys.intern(row[0][0])

    recalled = agent.hippocampus.activate(["nest", "tag:0"])
    assert any(tuple(exp.path.signature()) == MAIN_EPISODES[0][0] for exp in recalled)

    action = agent.step(
        context_events=["nest", "tag:0"],
        reward=0.0,
        novelty=0.1,
        conflict=0.0,
        intensity=1.0,
        dt=0.25,
    )
    assert isinstance(action, str) and action
    report = agent.sleep(cycles=1)
    assert isinstance(report, dict)
    assert int(report.get("cycles", 0)) == 1


def test_branch_agent_pickle_roundtrip(monkeypatch, tmp_path):
    _freeze_clock(monkeypatch)
    random.seed(53)
    agent = _build_agent()
    for context, reward in (
        (["nest", "tag:0"], 0.2),
        (["bowl", "tag:1"], -0.1),
        (["wheel", "tag:2"], 0.4),
    ):
        agent.step(
            context_events=context,
            reward=reward,
            novelty=0.2,
            conflict=0.0,
            intensity=1.0,
            dt=0.25,
        )
    before = _episode_rows(agent.hippocampus)
    assert len(before) == 3
    assert all(row[4] is not None for row in before)

    storage = AgentStorage(save_dir=str(tmp_path))
    path = storage.save_agent(
        agent.hippocampus,
        agent.cortex,
        agent.selector,
        sleep_manager=agent.sleep_manager,
        affective_space=agent.affective_space,
        agent=agent,
        filename="branch.pkl",
    )
    restored_agent = _build_agent(seed=99)
    storage.load_agent(
        restored_agent.hippocampus,
        restored_agent.cortex,
        restored_agent.selector,
        path,
        sleep_manager=restored_agent.sleep_manager,
        affective_space=restored_agent.affective_space,
        agent=restored_agent,
    )
    assert _episode_rows(restored_agent.hippocampus) == before

    hip_blob = pickle.dumps(agent.hippocampus)
    hip = pickle.loads(hip_blob)
    assert _episode_rows(hip) == before
    assert len(hip.signatures) == len(hip.experiences)
    recalled = hip.activate(["bowl", "tag:1"])
    assert any("bowl" in exp.path.signature() for exp in recalled)
    action = restored_agent.step(
        context_events=["bowl", "tag:1"],
        reward=0.0,
        novelty=0.1,
        conflict=0.0,
        intensity=1.0,
        dt=0.25,
    )
    assert isinstance(action, str) and action
    report = restored_agent.sleep(cycles=1)
    assert isinstance(report, dict)
    assert int(report.get("cycles", 0)) == 1


def test_legacy_dict_state_restores_slotted_memory_objects():
    event = pickle.loads(
        pickle.dumps(
            _LegacyShell(
                Event,
                {
                    "name": "ctx:nest",
                    "event_type": EventType.CONTEXT,
                    "magnitude": 1.0,
                    "timestamp": FIXED_TS,
                    "_frozen": True,
                },
            )
        )
    )
    assert event.name is sys.intern("ctx:nest")
    assert event._frozen is True

    path = pickle.loads(
        pickle.dumps(_LegacyShell(EpisodePath, {"events": (event,), "_frozen": True}))
    )
    assert path.signature() == ("ctx:nest",)

    trace = pickle.loads(
        pickle.dumps(
            _LegacyShell(
                EmotionalTrace,
                {
                    "snapshot_vector": {"valence": 0.4, "stress": -0.2},
                    "intensity": 0.5,
                    "timestamp": FIXED_TS,
                    "decay_rate": 0.05,
                },
            )
        )
    )
    impulse = trace.to_impulse(now=FIXED_TS)
    assert impulse.intensity == pytest.approx(0.125)
    assert trace._raw_axes["valence"] == pytest.approx(0.4)
    assert set(trace._raw_axes) == set(AXES)

    experience = pickle.loads(
        pickle.dumps(
            _LegacyShell(
                Experience,
                {
                    "path": path,
                    "consequence": None,
                    "intensity": 0.7,
                    "encoding_strength": 0.7,
                    "reward": 0.3,
                    "causal_depth": 0,
                    "timestamp": FIXED_TS,
                    "first_seen": FIXED_TS,
                    "last_activated": FIXED_TS,
                    "reinforcement_count": 1,
                    "activation_energy": 0.8,
                    "stability": 0.0,
                    "emotional_trace": trace,
                },
            )
        )
    )
    assert experience.path.signature() == ("ctx:nest",)
    assert experience.reward == pytest.approx(0.3)
    assert not hasattr(experience, "td_error_snapshot")
    assert experience.emotional_trace.intensity == pytest.approx(0.5)

    signature = pickle.loads(
        pickle.dumps(
            _LegacyShell(
                SignatureTrace,
                {
                    "feature_set": {"ctx:nest", "action:go"},
                    "drive_vector": (1.0, 0.0, 1.0),
                    "context_vector": (0.0, 0.0, 0.0),
                    "timestamp": FIXED_TS,
                    "context_tokens": ("ctx:nest",),
                    "activation_weight": 0.8,
                    "repetition_count": 2,
                    "reward_signal": 0.3,
                    "source_experience": experience,
                    "last_decay_ts": FIXED_TS,
                },
            )
        )
    )
    assert signature._mask_ready is False
    assert signature.feature_count == 0
    assert next(item for item in signature.feature_set if item == "ctx:nest") is sys.intern("ctx:nest")

    hippocampus = NOWAHippocampus.__new__(NOWAHippocampus)
    hippocampus.__setstate__(
        {
            "experiences": [signature.source_experience],
            "signatures": [signature],
            "max_experiences": 8,
            "_feature_bits": {},
            "_token_bits": {},
            "_nov_valid": False,
            "activation_similarity_threshold": 0.2,
            "activation_decay_half_life": 3600.0,
            "decay_rate": 0.015,
            "activation_threshold": 0.03,
        }
    )
    assert hippocampus.experiences[0].path.signature() == ("ctx:nest",)
    assert hippocampus.signatures[0].source_experience is hippocampus.experiences[0]
