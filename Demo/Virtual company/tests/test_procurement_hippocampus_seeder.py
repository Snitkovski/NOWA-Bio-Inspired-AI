"""Tests for ProcurementHippocampusSeeder (spec v2.0 §2.2, R5, §14)."""

from __future__ import annotations

import copy
import random
from types import SimpleNamespace
from typing import Any, List, Optional

from nowa_sandbox._common import ensure_core_src_on_path
from nowa_sandbox.procurement_hippocampus_seeder import (
    PROFESSIONAL_SEED_EPISODES,
    ProcurementHippocampusSeeder,
)
from nowa_sandbox.sandbox_agent_factory import create_procurement_agent

ensure_core_src_on_path()


REINFORCED_COUNT = sum(
    1 for episode in PROFESSIONAL_SEED_EPISODES if episode.get("reinforcement")
)


def _event_name(event: Any) -> str:
    if isinstance(event, str):
        return event
    return str(getattr(event, "name", event))


def _event_type_value(event: Any) -> Optional[str]:
    event_type = getattr(event, "event_type", None)
    if event_type is None:
        return None
    return getattr(event_type, "value", event_type)


def _path_events(path: Any) -> List[Any]:
    events = getattr(path, "events", None)
    if events is None:
        if isinstance(path, (list, tuple)):
            return list(path)
        return []
    return list(events)


def _path_names(path: Any) -> List[str]:
    signature = getattr(path, "signature", None)
    if callable(signature):
        return [str(name) for name in signature()]
    return [_event_name(event) for event in _path_events(path)]


def _action_events(path: Any) -> List[Any]:
    found = []
    for event in _path_events(path):
        name = _event_name(event)
        type_value = _event_type_value(event)
        if type_value == "action" or name.startswith("action:"):
            found.append(event)
    return found


class FakeHippocampus:
    def __init__(self) -> None:
        self.experiences: List[Any] = []
        self.stored: List[Any] = []
        self.reinforced: List[Any] = []

    def store(self, path, consequence=None, intensity=1.0, reward=0.0, **kwargs):
        exp = SimpleNamespace(
            path=path,
            consequence=consequence,
            intensity=intensity,
            reward=reward,
            reinforcement_count=1,
            activation_energy=1.0,
        )
        self.stored.append(exp)
        self.experiences.append(exp)
        return exp

    def reinforce(self, path, consequence=None, intensity=1.0, **kwargs):
        self.reinforced.append((path, consequence, intensity))
        match = None
        for exp in reversed(self.experiences):
            if exp.path is path or _path_names(exp.path) == _path_names(path):
                match = exp
                break
        if match is None:
            return self.store(path, consequence=consequence, intensity=intensity)
        match.reinforcement_count += 1
        match.activation_energy = max(float(match.activation_energy), 1.0)
        return match

    def activate(self, context_events):
        query = {str(token) for token in (context_events or [])}
        if not query:
            return list(self.experiences)
        activated = []
        for exp in self.experiences:
            names = set(_path_names(exp.path))
            if query.intersection(names):
                activated.append(exp)
        return activated


class FakeAffectiveSpace:
    def __init__(self) -> None:
        self.axes = {
            "valence": 0.11,
            "arousal": 0.22,
            "dominance": 0.0,
            "stress": 0.05,
        }
        self.step_calls = 0

    def step(self, *args, **kwargs):
        self.step_calls += 1
        for key in self.axes:
            self.axes[key] += 1.0


class FakeNeuromodulators:
    def __init__(self) -> None:
        self.dopamine = 0.4
        self.serotonin = 0.5
        self.update_calls = 0

    def to_dict(self):
        return {
            "dopamine": self.dopamine,
            "serotonin": self.serotonin,
        }

    def update_from_signals(self, *args, **kwargs):
        self.update_calls += 1
        self.dopamine += 1.0


class FakeValueLayer:
    def __init__(self) -> None:
        self.update_count = 0
        self.last_td_error = 0.0
        self.values = {"seed": 0.3}

    def update(self, *args, **kwargs):
        self.update_count += 1
        self.last_td_error = 1.0
        self.values["seed"] = 9.9


class FakeAgent:
    def __init__(self) -> None:
        self.hippocampus = FakeHippocampus()
        self.affective_space = FakeAffectiveSpace()
        self.neuromodulators = FakeNeuromodulators()
        self.value_layer = FakeValueLayer()


def _r5_snapshot(agent: Any) -> dict:
    affect = getattr(agent, "affective_space", None)
    axes = dict(getattr(affect, "axes", {}) or {})
    neuromodulators = getattr(agent, "neuromodulators", None)
    nm_payload = None
    if neuromodulators is not None and callable(getattr(neuromodulators, "to_dict", None)):
        nm_payload = dict(neuromodulators.to_dict())
        nm_payload.pop("timestamp", None)
    value_layer = getattr(agent, "value_layer", None)
    value_payload = None
    if value_layer is not None:
        values = getattr(value_layer, "values", None)
        value_payload = {
            "update_count": getattr(value_layer, "update_count", None),
            "last_td_error": getattr(value_layer, "last_td_error", None),
            "values": dict(values) if isinstance(values, dict) else copy.deepcopy(values),
        }
    return {
        "axes": axes,
        "affect_step_calls": getattr(affect, "step_calls", None),
        "nm": nm_payload,
        "nm_update_calls": getattr(neuromodulators, "update_calls", None),
        "value_layer": value_payload,
    }


def _try_core_hippocampus():
    try:
        from hippocampus import NOWAHippocampus
        return NOWAHippocampus()
    except Exception:
        return None


class TestSeedCount:
    def test_default_corpus_size_is_eight(self):
        assert len(PROFESSIONAL_SEED_EPISODES) == 8

    def test_seed_agent_stores_every_professional_episode(self):
        agent = FakeAgent()
        added = ProcurementHippocampusSeeder().seed_agent(agent)
        assert added == len(PROFESSIONAL_SEED_EPISODES)
        assert len(agent.hippocampus.stored) == len(PROFESSIONAL_SEED_EPISODES)
        assert len(agent.hippocampus.experiences) == len(PROFESSIONAL_SEED_EPISODES)

    def test_seed_agent_returns_zero_without_hippocampus(self):
        assert ProcurementHippocampusSeeder().seed_agent(SimpleNamespace()) == 0
        assert ProcurementHippocampusSeeder().seed_agent(None) == 0

    def test_custom_episode_list_is_honoured(self):
        episodes = [PROFESSIONAL_SEED_EPISODES[0]]
        agent = FakeAgent()
        added = ProcurementHippocampusSeeder(episodes=episodes).seed_agent(agent)
        assert added == 1
        assert len(agent.hippocampus.stored) == 1


class TestActionEventPresence:
    def test_build_path_keeps_context_tokens_and_action_event(self):
        seeder = ProcurementHippocampusSeeder()
        episode = PROFESSIONAL_SEED_EPISODES[0]
        path = seeder._build_path(episode["context_tokens"], action=episode["action"])
        names = _path_names(path)
        for token in episode["context_tokens"]:
            assert token in names
        actions = _action_events(path)
        assert len(actions) == 1
        assert _event_type_value(actions[0]) == "action"
        assert _event_name(actions[0]) == f"action:{episode['action']}"

    def test_add_event_does_not_mutate_original_path(self):
        seeder = ProcurementHippocampusSeeder()
        path = seeder._build_path(["event:quiet_day"], action="wait_and_monitor")
        original_len = len(_path_events(path))
        extra = seeder._build_path(["event:quiet_day"], action="wait_and_monitor")
        mutated = path.add_event(_path_events(extra)[0])
        assert len(_path_events(path)) == original_len
        assert mutated is not path

    def test_every_stored_path_has_typed_action_event(self):
        agent = FakeAgent()
        ProcurementHippocampusSeeder().seed_agent(agent)
        stored_actions = []
        for exp, episode in zip(agent.hippocampus.stored, PROFESSIONAL_SEED_EPISODES):
            actions = _action_events(exp.path)
            assert actions, f"missing ACTION event for {episode['action']}"
            assert _event_type_value(actions[0]) == "action"
            assert _event_name(actions[0]) == f"action:{episode['action']}"
            stored_actions.append(_event_name(actions[0]).split(":", 1)[-1])
        expected = [episode["action"] for episode in PROFESSIONAL_SEED_EPISODES]
        assert stored_actions == expected

    def test_compute_pressures_reads_seeded_action_events(self):
        hippocampus = _try_core_hippocampus()
        if hippocampus is None:
            agent = FakeAgent()
        else:
            agent = SimpleNamespace(hippocampus=hippocampus)
        added = ProcurementHippocampusSeeder().seed_agent(agent)
        assert added == len(PROFESSIONAL_SEED_EPISODES)

        try:
            from selector import ActionSelector
        except Exception:
            pressures = {}
            for exp in agent.hippocampus.experiences:
                for event in _action_events(exp.path):
                    action_name = _event_name(event).split(":", 1)[-1]
                    pressures[action_name] = pressures.get(action_name, 0.0) + 1.0
            assert "urgent_reorder" in pressures
            return

        selector = ActionSelector(
            actions=[
                "place_order_reliable_supplier",
                "place_order_cheap_supplier",
                "wait_and_monitor",
                "diversify_supplier",
                "urgent_reorder",
            ]
        )
        active = list(agent.hippocampus.experiences)
        pressures = selector.compute_pressures(active, cortical_patterns=[])
        assert pressures["urgent_reorder"] > 0.0
        assert pressures["diversify_supplier"] > 0.0
        assert pressures["wait_and_monitor"] > 0.0
        assert pressures["place_order_reliable_supplier"] > 0.0
        assert pressures["place_order_cheap_supplier"] > 0.0


class TestActivation:
    def test_matching_context_activates_seeded_memories_on_fake(self):
        agent = FakeAgent()
        ProcurementHippocampusSeeder().seed_agent(agent)
        activated = agent.hippocampus.activate(
            ["event:stock_critical_low", "domain:procurement"]
        )
        assert activated
        names = {_event_name(event) for exp in activated for event in _action_events(exp.path)}
        assert "action:urgent_reorder" in names

    def test_matching_context_activates_seeded_memories_on_core(self):
        hippocampus = _try_core_hippocampus()
        if hippocampus is None:
            return
        agent = SimpleNamespace(hippocampus=hippocampus)
        added = ProcurementHippocampusSeeder().seed_agent(agent)
        assert added == len(PROFESSIONAL_SEED_EPISODES)
        activated = hippocampus.activate(
            ["event:stock_critical_low", "domain:procurement"]
        )
        assert activated, "core hippocampus.activate returned no seeded traces"
        action_names = {
            _event_name(event)
            for exp in activated
            for event in _action_events(getattr(exp, "path", None))
        }
        assert action_names.intersection(
            {"action:urgent_reorder", "action:place_order_cheap_supplier"}
        )


class TestReinforcement:
    def test_marked_episodes_are_reinforced(self):
        agent = FakeAgent()
        ProcurementHippocampusSeeder().seed_agent(agent)
        assert len(agent.hippocampus.reinforced) == REINFORCED_COUNT
        reinforced_exp = [
            exp for exp in agent.hippocampus.experiences if exp.reinforcement_count > 1
        ]
        assert len(reinforced_exp) == REINFORCED_COUNT

    def test_core_hippocampus_increments_reinforcement_count(self):
        hippocampus = _try_core_hippocampus()
        if hippocampus is None:
            return
        agent = SimpleNamespace(hippocampus=hippocampus)
        ProcurementHippocampusSeeder().seed_agent(agent)
        reinforced = [
            exp
            for exp in hippocampus.experiences
            if int(getattr(exp, "reinforcement_count", 1)) > 1
        ]
        assert len(reinforced) >= REINFORCED_COUNT


class TestR5Snapshots:
    def test_seeder_only_touches_hippocampus_on_fake_agent(self):
        agent = FakeAgent()
        before = _r5_snapshot(agent)
        added = ProcurementHippocampusSeeder().seed_agent(agent)
        assert added > 0
        after = _r5_snapshot(agent)
        assert before == after
        assert agent.affective_space.step_calls == 0
        assert agent.neuromodulators.update_calls == 0
        assert agent.value_layer.update_count == 0

    def test_seeder_only_touches_hippocampus_on_real_agent(self):
        agent = create_procurement_agent(
            "r5_seeder", rng=random.Random(1), seed_intuition=False,
        )
        before = _r5_snapshot(agent)
        added = ProcurementHippocampusSeeder().seed_agent(agent)
        assert added > 0, "No episodes were seeded"
        after = _r5_snapshot(agent)
        assert before["axes"] == after["axes"]
        for axis, value in (before["axes"] or {}).items():
            assert abs(float(value) - float((after["axes"] or {}).get(axis, 0.0))) < 1e-6
        assert before["nm"] == after["nm"], "Seeder modified neuromodulators"
        assert before["value_layer"] == after["value_layer"], "Seeder modified value_layer"


class TestFailSoftAndFallback:
    def test_failed_episode_does_not_abort_remaining_store(self):
        class FlakyHippocampus(FakeHippocampus):
            def __init__(self) -> None:
                super().__init__()
                self.attempts = 0

            def store(self, path, consequence=None, intensity=1.0, reward=0.0, **kwargs):
                self.attempts += 1
                if self.attempts == 2:
                    raise RuntimeError("transient store failure")
                return super().store(
                    path,
                    consequence=consequence,
                    intensity=intensity,
                    reward=reward,
                    **kwargs,
                )

        agent = FakeAgent()
        agent.hippocampus = FlakyHippocampus()
        added = ProcurementHippocampusSeeder().seed_agent(agent)
        assert added == len(PROFESSIONAL_SEED_EPISODES) - 1
        assert len(agent.hippocampus.stored) == added

    def test_fallback_path_and_event_are_core_compatible(self, monkeypatch):
        import sys

        from mcp_body._compat import _FallbackEvent, _FallbackPath

        monkeypatch.setitem(sys.modules, "experience", None)
        seeder = ProcurementHippocampusSeeder()
        path = seeder._build_path(
            ["event:demand_shock", "domain:procurement"],
            action="urgent_reorder",
        )
        consequence = seeder._build_consequence("demand_met")

        assert isinstance(path, _FallbackPath)
        assert isinstance(consequence, _FallbackEvent)
        names = _path_names(path)
        assert "event:demand_shock" in names
        actions = _action_events(path)
        assert len(actions) == 1
        assert _event_type_value(actions[0]) == "action"
        assert _event_name(actions[0]) == "action:urgent_reorder"
        assert _event_type_value(consequence) == "consequence"
        assert _event_name(consequence) == "demand_met"
        rebuilt = path.add_event(actions[0])
        assert rebuilt is not path
        assert len(_path_events(path)) == 3
