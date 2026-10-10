"""Tests for BusinessHippocampusSeeder — lesson 2 ACTION event is mandatory."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List, Optional

import pytest

from nowa_body.business_hippocampus_seeder import (
    BusinessHippocampusSeeder,
    SeedEpisode,
)
from nowa_roles.procurement.seed_corpus import PROCUREMENT_SEED_EPISODES

from body_support import FakeAgent, FakeHippocampus


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
        return list(path) if isinstance(path, (list, tuple)) else []
    return list(events)


def test_seed_episode_without_action_raises_or_defaults():
    """SeedEpisode requires .action; dataclass enforces it (lesson 2)."""
    with pytest.raises(TypeError):
        SeedEpisode(context_tokens=["x"], consequence="y", reward=0.1)


def test_seeded_path_contains_action_event():
    seeder = BusinessHippocampusSeeder([
        SeedEpisode(
            ["event:x"], action="do_thing", consequence="ok", reward=0.5
        )
    ])
    agent = FakeAgent()
    seeder.seed_agent(agent)
    stored_path = agent.hippocampus.experiences[0].path
    action_events = [
        e for e in _path_events(stored_path)
        if _event_type_value(e) == "action" or _event_name(e).startswith("action:")
    ]
    assert len(action_events) == 1
    assert _event_name(action_events[0]) == "action:do_thing"


def test_empty_action_is_not_stored_as_context_only_path():
    seeder = BusinessHippocampusSeeder([
        SeedEpisode(["event:x"], action="   ", consequence="ok", reward=0.1)
    ])
    agent = FakeAgent()
    added = seeder.seed_agent(agent)
    assert added == 0
    assert agent.hippocampus.experiences == []


def test_path_is_built_by_reassignment_not_mutation():
    seeder = BusinessHippocampusSeeder([])
    path = seeder._build_path(["a", "b"], "act")
    names = [_event_name(e) for e in _path_events(path)]
    assert names == ["a", "b", "action:act"]
    types = [_event_type_value(e) for e in _path_events(path)]
    assert types.count("action") == 1
    assert types[-1] == "action"


def test_seeder_only_touches_hippocampus():
    agent = FakeAgent()
    axes_before = dict(agent.affective_space.axes)
    seeder = BusinessHippocampusSeeder(PROCUREMENT_SEED_EPISODES)
    added = seeder.seed_agent(agent)
    assert added == len(PROCUREMENT_SEED_EPISODES)
    assert agent.affective_space.axes == axes_before
    assert agent.affective_space.step_calls == []
    assert agent.neuromodulators.update_calls == 0
    assert agent.value_layer.update_count == 0
    assert len(agent.hippocampus.experiences) == added


def test_reinforce_flag_calls_hippocampus_reinforce():
    seeder = BusinessHippocampusSeeder([
        SeedEpisode(["x"], action="a", consequence="ok", reward=0.5, reinforce=True)
    ])
    agent = FakeAgent()
    seeder.seed_agent(agent)
    assert len(agent.hippocampus.reinforced) == 1


def test_missing_hippocampus_returns_zero():
    agent = SimpleNamespace()
    added = BusinessHippocampusSeeder([
        SeedEpisode(["x"], action="a", consequence="ok", reward=0.1)
    ]).seed_agent(agent)
    assert added == 0


def test_failed_episode_does_not_abort_remaining():
    class Flaky(FakeHippocampus):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        def store(self, path, consequence=None, intensity=1.0, reward=0.0, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("boom")
            return super().store(path, consequence, intensity, reward)

    agent = FakeAgent()
    agent.hippocampus = Flaky()
    seeder = BusinessHippocampusSeeder([
        SeedEpisode(["a"], action="one", consequence="x", reward=0.1),
        SeedEpisode(["b"], action="two", consequence="y", reward=0.1),
    ])
    assert seeder.seed_agent(agent) == 1
    assert len(agent.hippocampus.stored) == 1
