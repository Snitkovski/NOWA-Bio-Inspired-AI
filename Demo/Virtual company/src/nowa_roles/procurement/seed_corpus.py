"""Procurement professional-intuition corpus as SeedEpisode objects."""

from __future__ import annotations

from typing import Any, Dict, List

from nowa_body.business_hippocampus_seeder import SeedEpisode

PROCUREMENT_SEED_EPISODES: List[SeedEpisode] = [
    SeedEpisode(
        context_tokens=["event:stock_critical_low", "domain:procurement",
                        "valence:very_negative", "arousal:high"],
        action="mcp__drivemcp__create_purchase_order",
        consequence="stock_restored",
        reward=0.8,
        intensity=0.9,
        reinforce=True,
    ),
    SeedEpisode(
        context_tokens=["event:stock_critical_low", "domain:procurement",
                        "budget:critical"],
        action="mcp__drivemcp__create_purchase_order",
        consequence="budget_preserved",
        reward=0.6,
        intensity=0.7,
        reinforce=False,
    ),
    SeedEpisode(
        context_tokens=["event:supplier_defaulted", "domain:procurement",
                        "valence:negative"],
        action="mcp__drivemcp__create_purchase_order",
        consequence="risk_reduced",
        reward=0.7,
        intensity=0.8,
        reinforce=True,
    ),
    SeedEpisode(
        context_tokens=["event:order_arrived_on_time", "domain:trust",
                        "valence:positive"],
        action="mcp__drivemcp__create_purchase_order",
        consequence="reliable_delivery",
        reward=0.5,
        intensity=0.5,
        reinforce=False,
    ),
    SeedEpisode(
        context_tokens=["event:quiet_day", "domain:neutral", "valence:neutral"],
        action="wait_and_monitor",
        consequence="no_action_needed",
        reward=0.1,
        intensity=0.2,
        reinforce=False,
    ),
    SeedEpisode(
        context_tokens=["event:demand_shock", "domain:procurement",
                        "arousal:high", "valence:negative"],
        action="mcp__drivemcp__create_purchase_order",
        consequence="demand_met",
        reward=0.75,
        intensity=0.85,
        reinforce=True,
    ),
    SeedEpisode(
        context_tokens=["budget:high_utilization", "domain:finance",
                        "valence:negative"],
        action="wait_and_monitor",
        consequence="budget_protected",
        reward=0.4,
        intensity=0.6,
        reinforce=False,
    ),
    SeedEpisode(
        context_tokens=["event:order_arrived_late", "domain:risk",
                        "valence:negative"],
        action="mcp__drivemcp__create_purchase_order",
        consequence="supplier_risk_reduced",
        reward=0.6,
        intensity=0.7,
        reinforce=True,
    ),
]


def procurement_seed_episodes() -> List[SeedEpisode]:
    return list(PROCUREMENT_SEED_EPISODES)


def seed_episodes_from_dicts(rows: List[Dict[str, Any]]) -> List[SeedEpisode]:
    """Wrap dict-shaped sandbox episodes into SeedEpisode (no sandbox import)."""
    episodes: List[SeedEpisode] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        action = str(row.get("action") or "").strip()
        if not action:
            continue
        reinforce = bool(row.get("reinforce", row.get("reinforcement", False)))
        episodes.append(
            SeedEpisode(
                context_tokens=list(row.get("context_tokens") or []),
                action=action,
                consequence=str(row.get("consequence") or "unspecified_outcome"),
                reward=float(row.get("reward", 0.0)),
                intensity=float(row.get("intensity", 0.5)),
                reinforce=reinforce,
            )
        )
    return episodes
