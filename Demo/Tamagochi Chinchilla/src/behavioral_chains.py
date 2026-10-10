"""
Behavioral Chain Executor - executes sequences of behavior patterns.

Extended with DYNAMIC_CHAINS support: chains promoted from TemporalChain
memory (formed during sleep) are registered at runtime alongside the
hardcoded BEHAVIORAL_CHAINS catalog.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import random

from config import BEHAVIORAL_CHAINS

# ============================================================================
# DYNAMIC CHAIN REGISTRY
# ============================================================================

DYNAMIC_CHAINS: Dict[str, List[Tuple[str, float]]] = {}

DYNAMIC_CHAIN_STABILITY_THRESHOLD = 0.55
DYNAMIC_CHAIN_USAGE_THRESHOLD     = 3
DYNAMIC_CHAIN_AFFECT_THRESHOLD    = 0.04
DYNAMIC_CHAIN_MAX_REGISTERED      = 200


def _all_chains() -> Dict[str, List]:
    combined = dict(BEHAVIORAL_CHAINS)
    combined.update(DYNAMIC_CHAINS)
    return combined


def register_dynamic_chain(name: str, steps: List[Tuple[str, float]]) -> bool:
    if name in BEHAVIORAL_CHAINS:
        return False
    if name not in DYNAMIC_CHAINS and len(DYNAMIC_CHAINS) >= DYNAMIC_CHAIN_MAX_REGISTERED:
        oldest = next(iter(DYNAMIC_CHAINS))
        del DYNAMIC_CHAINS[oldest]
    DYNAMIC_CHAINS[name] = steps
    return True


def is_dynamic_chain(name: str) -> bool:
    return name in DYNAMIC_CHAINS


class BehavioralChainExecutor:
    """
    Manages behavioral chain execution.
    Supports static BEHAVIORAL_CHAINS and dynamically promoted DYNAMIC_CHAINS.
    """

    def __init__(self, action_realizer, logger: Optional[logging.Logger] = None):
        self.action_realizer = action_realizer
        self.logger = logger or logging.getLogger(__name__)
        self.current_chain: Optional[str] = None
        self.chain_progress = 0
        self.chain_history: List[str] = []
        self.logger.info("BehavioralChainExecutor initialized (dynamic chains enabled)")

    def _chain_steps(self, chain_name: str) -> List:
        return _all_chains().get(chain_name, [])

    def select_chain(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        context = context or {}
        possible_chains = self._get_applicable_chains(context)
        if not possible_chains:
            return None
        weights = [1.0 / (1.0 + self.chain_history[-5:].count(c)) for c in possible_chains]
        total = sum(weights) or 1.0
        return random.choices(possible_chains, weights=[w/total for w in weights], k=1)[0]

    def _get_applicable_chains(self, context: Dict[str, Any]) -> List[str]:
        applicable = []
        affect      = context.get("affect", {})
        is_daytime  = context.get("is_daytime", True)
        is_nighttime = context.get("is_nighttime", False)
        stress    = affect.get("stress",    0.0)
        arousal   = affect.get("arousal",   0.5)
        curiosity = affect.get("curiosity", 0.5)

        if is_nighttime or arousal < 0.3:
            applicable.extend(["bedtime_routine", "full_grooming", "nesting"])
        if is_daytime and arousal > 0.6:
            applicable.extend(["morning_awakening", "activity_burst",
                                "hyperactivity", "territorial_patrol"])
        if stress > 0.5:
            applicable.extend(["extreme_fear", "mild_fear", "chronic_stress"])
        if curiosity > 0.6:
            applicable.extend(["exploration", "activity_burst"])
        if affect.get("trust", 0.5) > 0.3:
            applicable.append("social_contact")
        applicable.extend(["eating_and_grooming", "dust_bathing", "full_grooming"])
        for dname in DYNAMIC_CHAINS:
            applicable.append(dname)
        applicable = list(set(applicable))
        return applicable or list(_all_chains().keys())

    def start_chain(self, chain_name: str) -> Optional[Dict[str, Any]]:
        if chain_name not in _all_chains():
            self.logger.warning(f"Unknown chain: {chain_name}")
            return None
        self.current_chain = chain_name
        self.chain_progress = 0
        tag = "dynamic" if is_dynamic_chain(chain_name) else "static"
        self.logger.info(f"Starting {tag} chain: {chain_name} ({len(self._chain_steps(chain_name))} steps)")
        return self.get_next_action_in_chain()

    def get_next_action_in_chain(self) -> Optional[Dict[str, Any]]:
        if not self.current_chain:
            return None
        chain_actions = self._chain_steps(self.current_chain)
        while self.chain_progress < len(chain_actions):
            step = chain_actions[self.chain_progress]
            self.chain_progress += 1
            action_id, probability = step if isinstance(step, tuple) else (step, 1.0)
            if random.random() > probability:
                self.logger.debug(f"Skipped step {action_id} (p={probability:.1f})")
                continue
            command = self.action_realizer.realize_action(
                action_id, pressure=0.9,
                context={"chain_context": self.current_chain}
            )
            if command:
                command["layer"] = "action"
                self.logger.debug(f"Chain step {self.chain_progress}/{len(chain_actions)}: {action_id}")
                return command
        self.chain_history.append(self.current_chain)
        if len(self.chain_history) > 50:
            self.chain_history.pop(0)
        self.logger.info(f"Chain '{self.current_chain}' completed")
        self.current_chain = None
        self.chain_progress = 0
        return None

    def can_continue_chain(self) -> bool:
        if not self.current_chain:
            return False
        return self.chain_progress < len(self._chain_steps(self.current_chain))

    def interrupt_chain(self) -> None:
        if self.current_chain:
            self.logger.info(f"Interrupting chain: {self.current_chain}")
            self.current_chain = None
            self.chain_progress = 0

    def get_chain_stats(self) -> Dict[str, Any]:
        return {
            "current_chain":          self.current_chain,
            "current_progress":       self.chain_progress,
            "total_chains_completed": len(self.chain_history),
            "completions_by_chain":   {c: self.chain_history.count(c) for c in _all_chains()},
            "most_recent_chains":     self.chain_history[-10:],
            "dynamic_chains_count":   len(DYNAMIC_CHAINS),
            "dynamic_chains":         list(DYNAMIC_CHAINS.keys()),
        }