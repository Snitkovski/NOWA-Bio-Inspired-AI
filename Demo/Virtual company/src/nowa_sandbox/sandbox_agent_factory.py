"""Create a single sovereign NOWA agent for sandbox training."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence

from ._common import clamp, ensure_core_src_on_path
from .procurement_hippocampus_seeder import (
    PROFESSIONAL_SEED_EPISODES,
    ProcurementHippocampusSeeder,
)
from .sandbox_encoder import AFFECTIVE_MAPPING, SandboxEncoder


PROCUREMENT_ACTIONS: List[str] = [
    "place_order_reliable_supplier",
    "place_order_cheap_supplier",
    "wait_and_monitor",
    "diversify_supplier",
    "urgent_reorder",
]

# Events worth pre-seeding as "professional intuition" before day one.
SEED_EVENT_NAMES: List[str] = list(AFFECTIVE_MAPPING.keys())

DEFAULT_SEED_ACTION = "wait_and_monitor"
"""Action for legacy seed events the professional corpus does not cover."""


def create_procurement_agent(
    agent_id: str = "procurement_agent_001",
    rng: Optional[random.Random] = None,
    seed_intuition: bool = True,
    seed_repeats: int = 1,
) -> Any:
    """Create ONE independent NOWA agent for the "Buyer" role.

    Unlike NOWAColony in the Warriner demo there are not 100 agents here but
    one, because this is a concrete virtual employee rather than a statistical
    population used to validate correlations.

    If picking "the best of several candidates" is needed later (the
    evolutionary-selection analogue), several candidates with different genomes
    can be initialized and the one with the best ProcurementFitnessVector kept
    after N quarters.
    """
    ensure_core_src_on_path()
    rng = rng or random.Random()

    agent = _create_core_agent(agent_id, rng)
    if agent is None:
        agent = _create_fallback_agent(agent_id, rng)

    if seed_intuition:
        seed_professional_intuition(agent, repeats=seed_repeats)
    return agent


def seed_professional_intuition(agent: Any, repeats: int = 1) -> int:
    """Load the professional-intuition corpus into ``agent.hippocampus``.

    Single entry point for the v2.0 seeding decision, so the CLI and the GUI
    cannot drift apart on when (and how often) an agent gets seeded. Returns
    the number of stored episodes.
    """
    seeder = ProcurementHippocampusSeeder()
    stored = 0
    for _ in range(max(1, int(repeats))):
        stored += seeder.seed_agent(agent)
    return stored


def _create_core_agent(agent_id: str, rng: random.Random) -> Optional[Any]:
    """Build a full NOWA-core agent via ``AgentFactory``, or None if unavailable."""
    ensure_core_src_on_path()
    try:
        from agent_factory import AgentConfig, AgentFactory
    except Exception:
        return None
    try:
        factory = AgentFactory(AgentConfig(actions=list(PROCUREMENT_ACTIONS)))
        return factory.spawn_random(rng=rng, agent_id=agent_id)
    except Exception:
        return None


def seed_procurement_intuition(
    agent: Any,
    event_names: Optional[Sequence[str]] = None,
    repeats: int = 1,
) -> int:
    """Pre-load the hippocampus with affectively labelled business episodes.

    Compatibility wrapper kept for callers predating v2.0. It no longer stores
    episodes itself: every episode goes through ``ProcurementHippocampusSeeder``
    so each stored path carries an ``EventType.ACTION`` event, without which
    ``ActionSelector.compute_pressures`` cannot read the episode at all and the
    seeding is invisible to the decision pipeline.

    ``event_names`` still selects which affective events to seed and ``repeats``
    how many passes to store; the action for each event is taken from the
    professional corpus, falling back to ``wait_and_monitor`` for events the
    corpus does not cover. Returns the number of stored episodes.
    """
    hippocampus = getattr(agent, "hippocampus", None)
    if hippocampus is None or not hasattr(hippocampus, "store"):
        return 0

    names = list(event_names) if event_names is not None else list(SEED_EVENT_NAMES)
    episodes = [_legacy_episode_for_event(name) for name in names]
    if not episodes:
        return 0

    seeder = ProcurementHippocampusSeeder(episodes=episodes)
    stored = 0
    for _ in range(max(1, int(repeats))):
        stored += seeder.seed_agent(agent)
    return stored


def _professional_action_for_event(event_name: str) -> str:
    """Action the professional corpus pairs with ``event:<event_name>``."""
    for episode in PROFESSIONAL_SEED_EPISODES:
        action = str(episode.get("action") or "").strip()
        if not action:
            continue
        for token in episode.get("context_tokens") or []:
            if str(token) == f"event:{event_name}":
                return action
    return DEFAULT_SEED_ACTION


def _legacy_episode_for_event(event_name: str) -> dict:
    """One seeder episode with the legacy reward/intensity labelling."""
    episode = SandboxEncoder().encode_seed_episode(event_name)
    valence = float(episode["v"])
    if valence > 0.1:
        consequence = "positive_procurement_outcome"
    elif valence < -0.1:
        consequence = "negative_procurement_outcome"
    else:
        consequence = "neutral_procurement_outcome"
    return {
        "context_tokens": list(episode["tokens"]),
        "action": _professional_action_for_event(event_name),
        "consequence": consequence,
        "reward": clamp(valence, -1.0, 1.0),
        "intensity": clamp(0.2 + abs(valence), 0.0, 2.0),
        "reinforcement": False,
    }


def _create_fallback_agent(agent_id: str, rng: random.Random) -> Any:
    """Simplified agent used when AgentFactory cannot spawn."""
    ensure_core_src_on_path()
    try:
        from affective_space import AffectiveSpace
        affective_space: Any = AffectiveSpace()
    except Exception:
        class _FallbackAffectiveSpace:
            def __init__(self) -> None:
                self.axes: Dict[str, float] = {}

            def step(self, *args: Any, **kwargs: Any) -> Dict[str, float]:
                del args, kwargs
                return dict(self.axes)

        affective_space = _FallbackAffectiveSpace()

    class _FallbackHippocampus:
        def __init__(self):
            self.experiences = []

        def store(self, path, consequence=None, intensity=1.0, reward=0.0, **kw):
            exp = type("Exp", (), {})()
            exp.path = list(path) if isinstance(path, (list, tuple, set)) else path
            exp.consequence = consequence
            exp.intensity = intensity
            exp.reward = reward
            exp.reinforcement_count = 1
            exp.activation_energy = 1.0
            self.experiences.append(exp)
            return exp

        def activate(self, context_events):
            query = {str(t) for t in context_events or []}
            if not query:
                return []
            result = []
            for exp in self.experiences:
                tokens = exp.path if isinstance(exp.path, (list, set, tuple)) else []
                if query.intersection({str(t) for t in tokens}):
                    result.append(exp)
            return result

    class _FallbackAgent:
        def __init__(self, agent_id, rng):
            self.agent_id = agent_id
            self.hippocampus = _FallbackHippocampus()
            self.affective_space = affective_space
            self.sleep_manager = None
            self.genome = {
                "risk_aversion": rng.uniform(0.2, 0.8),
                "curiosity_baseline": rng.uniform(0.1, 0.4),
            }

        def step(self, context_events, reward: float = 0.0, **kw):
            active = self.hippocampus.activate(context_events)
            if not active:
                return "wait_and_monitor"
            avg_reward = sum(e.reward for e in active) / len(active)
            if avg_reward < -0.4:
                return "urgent_reorder"
            if avg_reward < -0.1:
                return "diversify_supplier"
            return "wait_and_monitor"

    return _FallbackAgent(agent_id, rng)


__all__ = [
    "create_procurement_agent",
    "ensure_core_src_on_path",
    "seed_professional_intuition",
    "seed_procurement_intuition",
    "PROCUREMENT_ACTIONS",
]
