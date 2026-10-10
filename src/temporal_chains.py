"""
Temporal Chains (Plan B) - lightweight sequence memory and biasing

Stores short fixed-length chains of events (including actions) discovered during
sleep consolidation and provides a small bias to the ActionSelector at decision
time based on retrospective net affect.
"""
import time
from collections import defaultdict
from typing import List, Tuple, Dict


class TemporalChain:
    def __init__(self, signature: Tuple[str, ...], net_affect: float = 0.0):
        self.signature = tuple(signature)
        self.net_affect = float(net_affect)
        self.stability = 0.0
        self.usage_count = 1
        self.created_at = time.time()
        self.last_updated = time.time()

    def update(self, net_affect: float):
        # Simple running average with count
        self.usage_count += 1
        # small smoothing: new net_affect blended with existing
        self.net_affect = (self.net_affect * (self.usage_count - 1) + net_affect) / self.usage_count
        # stability increases slightly when updated
        self.stability = min(1.0, self.stability + 0.05)
        self.last_updated = time.time()

    def matches_suffix(self, event_sequence: List[str]) -> bool:
        """Return True if this chain's signature matches the tail of event_sequence."""
        if not event_sequence:
            return False
        seq = list(event_sequence)
        sig = list(self.signature)
        if len(sig) > len(seq):
            return False
        return seq[-len(sig):] == sig


class ChainMemory:
    """Manager for TemporalChain objects."""

    def __init__(self):
        self.chains = {}  # signature -> TemporalChain

    def add_or_update(self, signature: Tuple[str, ...], net_affect: float):
        if not signature:
            return None
        key = tuple(signature)
        if key in self.chains:
            self.chains[key].update(net_affect)
            return self.chains[key]
        chain = TemporalChain(key, net_affect)
        # initialize stability proportional to abs(net_affect)
        chain.stability = min(1.0, abs(net_affect) * 0.2)
        self.chains[key] = chain
        return chain

    def match_bias(self, recent_sequence: List[str]) -> Dict[str, float]:
        """Return a mapping action -> bias based on matching chains.

        For every chain that matches the tail of recent_sequence, bias the
        final action (last action event in chain) by chain.net_affect scaled by
        usage/stability. The caller will incorporate these biases into pressures.
        """
        bias = defaultdict(float)
        for chain in self.chains.values():
            if chain.matches_suffix(recent_sequence):
                # find last action token in signature (starts with 'action:')
                last_action = None
                for name in reversed(chain.signature):
                    if name.startswith("action:"):
                        last_action = name.split(":", 1)[1]
                        break
                if last_action is None:
                    continue
                weight = chain.net_affect * (0.5 + 0.5 * chain.stability) * (chain.usage_count ** 0.5)
                bias[last_action] += weight
        return dict(bias)

    def statistics(self) -> dict:
        if not self.chains:
            return {
                "total_chains": 0,
                "avg_stability": 0,
                "avg_net_affect": 0,
                "avg_length": 0,
                "last_chain_events": []
            }
        total = len(self.chains)
        chains_list = list(self.chains.values())
        avg_length = sum(len(c.signature) for c in chains_list) / total if total > 0 else 0
        last_chain = chains_list[-1].signature if chains_list else []
        
        return {
            "total_chains": total,
            "avg_stability": sum(c.stability for c in chains_list) / total,
            "avg_net_affect": sum(c.net_affect for c in chains_list) / total,
            "avg_length": avg_length,
            "last_chain_events": list(last_chain) if last_chain else []
        }

    def to_dict(self) -> dict:
        """Serialize chains to dict for saving"""
        chains_data = {}
        for signature, chain in self.chains.items():
            chains_data[signature] = {
                "signature": list(signature),
                "net_affect": chain.net_affect,
                "stability": chain.stability,
                "usage_count": chain.usage_count,
                "created_at": chain.created_at,
                "last_updated": chain.last_updated
            }
        return {"chains": chains_data}

    def from_dict(self, data: dict):
        """Restore chains from dict (loaded from save)"""
        if "chains" not in data:
            return
        
        import time
        for signature_tuple, chain_data in data["chains"].items():
            # signature_tuple is already the key from dict
            signature = tuple(signature_tuple) if isinstance(signature_tuple, (list, tuple)) else tuple([signature_tuple])
            
            chain = TemporalChain(signature, chain_data.get("net_affect", 0.0))
            chain.stability = chain_data.get("stability", 0.0)
            chain.usage_count = chain_data.get("usage_count", 1)
            chain.created_at = chain_data.get("created_at", time.time())
            chain.last_updated = chain_data.get("last_updated", time.time())
            
            self.chains[signature] = chain
