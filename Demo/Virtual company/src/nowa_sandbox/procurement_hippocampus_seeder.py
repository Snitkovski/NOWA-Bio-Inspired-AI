"""Seed professional procurement intuition into a NOWA hippocampus.

Corpus stays here (sandbox domain). Path/ACTION construction is
``hippocampus_seeder.HippocampusSeeder``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._common import ensure_core_src_on_path

ensure_core_src_on_path()

from hippocampus_seeder import HippocampusSeeder, SeedEpisode  # noqa: E402


PROFESSIONAL_SEED_EPISODES: List[Dict[str, Any]] = [
    {
        "context_tokens": ["event:stock_critical_low", "domain:procurement",
                           "valence:very_negative", "arousal:high"],
        "action": "urgent_reorder",
        "consequence": "stock_restored",
        "reward": 0.8,
        "intensity": 0.9,
        "reinforcement": True,
    },
    {
        "context_tokens": ["event:stock_critical_low", "domain:procurement",
                           "budget:critical"],
        "action": "place_order_cheap_supplier",
        "consequence": "budget_preserved",
        "reward": 0.6,
        "intensity": 0.7,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:supplier_defaulted", "domain:procurement",
                           "valence:negative"],
        "action": "diversify_supplier",
        "consequence": "risk_reduced",
        "reward": 0.7,
        "intensity": 0.8,
        "reinforcement": True,
    },
    {
        "context_tokens": ["event:order_arrived_on_time", "domain:trust",
                           "valence:positive"],
        "action": "place_order_reliable_supplier",
        "consequence": "reliable_delivery",
        "reward": 0.5,
        "intensity": 0.5,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:quiet_day", "domain:neutral",
                           "valence:neutral"],
        "action": "wait_and_monitor",
        "consequence": "no_action_needed",
        "reward": 0.1,
        "intensity": 0.2,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:demand_shock", "domain:procurement",
                           "arousal:high", "valence:negative"],
        "action": "urgent_reorder",
        "consequence": "demand_met",
        "reward": 0.75,
        "intensity": 0.85,
        "reinforcement": True,
    },
    {
        "context_tokens": ["budget:high_utilization", "domain:finance",
                           "valence:negative"],
        "action": "wait_and_monitor",
        "consequence": "budget_protected",
        "reward": 0.4,
        "intensity": 0.6,
        "reinforcement": False,
    },
    {
        "context_tokens": ["event:order_arrived_late", "domain:risk",
                           "valence:negative"],
        "action": "diversify_supplier",
        "consequence": "supplier_risk_reduced",
        "reward": 0.6,
        "intensity": 0.7,
        "reinforcement": True,
    },
]


def _episode_to_seed(episode: Dict[str, Any]) -> SeedEpisode:
    return SeedEpisode(
        context_tokens=list(episode.get("context_tokens") or []),
        action=str(episode.get("action") or ""),
        consequence=str(episode.get("consequence") or ""),
        reward=float(episode.get("reward", 0.0)),
        intensity=float(episode.get("intensity", 0.5)),
        reinforce=bool(episode.get("reinforcement") or episode.get("reinforce")),
    )


class ProcurementHippocampusSeeder:
    """Domain corpus + platform ``BusinessHippocampusSeeder``.

    Does not touch affective_space, neuromodulators, or value_layer.
    """

    def __init__(self, episodes: Optional[List[dict]] = None) -> None:
        self.episodes = (
            list(episodes) if episodes is not None else list(PROFESSIONAL_SEED_EPISODES)
        )
        self._platform = HippocampusSeeder(
            [_episode_to_seed(item) for item in self.episodes]
        )

    def seed_agent(self, agent: Any) -> int:
        return self._platform.seed_agent(agent)

    def _build_path(self, tokens: List[str], action: Optional[str] = None) -> Any:
        return self._platform._build_path(list(tokens or []), str(action or ""))

    def _build_consequence(self, label: str) -> Any:
        return self._platform._build_consequence(label)


__all__ = [
    "PROFESSIONAL_SEED_EPISODES",
    "ProcurementHippocampusSeeder",
]
