"""
Hippocampal imagination engine.

Generates imagined trajectories by recombining similar transitions from
episodic memory.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from value_layer import ValueLayer, state_similarity


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _clamp(value: float, min_value: float, max_value: float) -> float:
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def quantile(values: Sequence[float], q: float) -> float:
    cleaned = sorted(float(v) for v in list(values or []))
    if not cleaned:
        return 0.0
    if len(cleaned) == 1:
        return float(cleaned[0])
    q_v = _clamp(_safe_float(q, 0.5), 0.0, 1.0)
    index_f = q_v * float(len(cleaned) - 1)
    lo = int(index_f)
    hi = min(len(cleaned) - 1, lo + 1)
    if lo == hi:
        return float(cleaned[lo])
    alpha = index_f - float(lo)
    return float(((1.0 - alpha) * cleaned[lo]) + (alpha * cleaned[hi]))


@dataclass
class ImaginedTrajectory:
    states: list
    actions: list
    rewards: list
    root_action: str
    terminal_state_value: float
    cumulative_reward: float
    value_estimate: float
    novelty_score: float
    confidence: float
    depth: int


@dataclass
class HippocampalImagineEngine:
    """
    Replay + recombination imagination over episodic transitions.
    """

    samples: int = 8
    depth: int = 4
    branching: int = 3
    similarity_threshold: float = 0.6
    reward_decay: float = 0.9
    novelty_bonus: float = 0.05
    goal_bias: float = 0.35
    confidence_decay: float = 0.9
    state_novelty_weight: float = 0.4
    max_nodes: int = 96
    max_graph_nodes: int = 96
    max_graph_edges: int = 192
    max_tree_nodes: int = 128
    action_temperature: float = 0.7
    value_backup: float = 0.8
    min_discount: float = 0.02
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self.samples = max(1, min(8, int(_safe_float(self.samples, 8.0))))
        self.depth = max(1, min(5, int(_safe_float(self.depth, 4.0))))
        self.branching = max(1, min(4, int(_safe_float(self.branching, 3.0))))
        self.similarity_threshold = _clamp(
            _safe_float(self.similarity_threshold, 0.6),
            0.0,
            1.0,
        )
        self.reward_decay = _clamp(_safe_float(self.reward_decay, 0.9), 0.1, 1.0)
        self.novelty_bonus = _clamp(_safe_float(self.novelty_bonus, 0.05), 0.0, 1.0)
        self.goal_bias = _clamp(_safe_float(self.goal_bias, 0.35), 0.0, 1.0)
        self.confidence_decay = _clamp(_safe_float(self.confidence_decay, 0.9), 0.0, 1.0)
        self.state_novelty_weight = _clamp(
            _safe_float(self.state_novelty_weight, 0.4),
            0.0,
            1.0,
        )
        # HIE-002 limits.
        self.max_graph_nodes = max(
            1,
            min(
                96,
                int(
                    _safe_float(
                        self.max_graph_nodes,
                        _safe_float(self.max_nodes, 96.0),
                    )
                ),
            ),
        )
        self.max_nodes = int(self.max_graph_nodes)
        self.max_graph_edges = max(1, min(192, int(_safe_float(self.max_graph_edges, 192.0))))
        self.max_tree_nodes = max(1, min(128, int(_safe_float(self.max_tree_nodes, 128.0))))
        self.action_temperature = _clamp(_safe_float(self.action_temperature, 0.7), 0.05, 5.0)
        self.value_backup = _clamp(_safe_float(self.value_backup, 0.8), 0.0, 1.0)
        self.min_discount = _clamp(_safe_float(self.min_discount, 0.02), 0.001, 0.2)

    def generate_rollouts(
        self,
        *,
        start_state: Mapping[str, Any],
        action_id: str,
        experiences: Sequence[Any],
        depth: int,
        gamma: float,
        value_layer: Optional[ValueLayer] = None,
    ) -> Dict[str, Any]:
        # Backward-compatible wrapper for HIE-001 call sites.
        result = self.generate_structured_imagination(
            start_state=start_state,
            action_id=action_id,
            experiences=experiences,
            depth=depth,
            gamma=gamma,
            value_layer=value_layer,
        )
        trajectories = list(result.get("trajectories", []) or [])
        max_depth_reached = 0
        for trajectory in trajectories:
            try:
                max_depth_reached = max(max_depth_reached, int(getattr(trajectory, "depth", 0)))
            except Exception:
                continue
        return {
            "values": [float(v) for v in list(result.get("values", []) or [])],
            "nodes_visited": int(result.get("nodes_visited", 0)),
            "max_depth_reached": int(max_depth_reached),
            "novelty_hits": int(result.get("novelty_hits", 0)),
        }

    def generate_structured_imagination(
        self,
        *,
        start_state: Mapping[str, Any],
        action_id: str,
        experiences: Sequence[Any],
        depth: int,
        gamma: float,
        value_layer: Optional[ValueLayer],
    ) -> Dict[str, Any]:
        pool = list(experiences or [])
        if not pool:
            return self._empty_structured_result()

        depth_limit = max(1, min(5, int(_safe_float(depth, self.depth))))
        sample_limit = max(1, min(8, int(_safe_float(self.samples, 8.0))))
        branch_limit = max(1, min(4, int(_safe_float(self.branching, 3.0))))
        gamma_v = _clamp(_safe_float(gamma, 0.95), 0.0, 0.999)
        action_token = str(action_id or "")
        node_limit = max(1, min(96, int(_safe_float(self.max_graph_nodes, 96.0))))
        edge_limit = max(1, min(192, int(_safe_float(self.max_graph_edges, 192.0))))

        observed_state_signatures = self._observed_state_signatures_for_action(
            experiences=pool,
            action_id=action_token,
            value_layer=value_layer,
        )
        start_signature = self._state_signature(start_state, value_layer=value_layer)
        if start_signature:
            observed_state_signatures.add(start_signature)

        trajectories: List[ImaginedTrajectory] = []
        values: List[float] = []
        nodes_visited = 0
        edges_visited = 0
        novelty_hits = 0

        for _ in range(sample_limit):
            if nodes_visited >= node_limit or edges_visited >= edge_limit:
                break
            seed_candidates = self._select_candidates(
                current_state=start_state,
                experiences=pool,
                value_layer=value_layer,
                action_id=action_token,
            )
            if not seed_candidates:
                break
            seed_candidates = list(seed_candidates[:branch_limit])
            seed_exp = self.rng.choice(seed_candidates)

            current_state = dict(start_state or {})
            states = [dict(current_state)]
            actions: List[str] = []
            rewards: List[float] = []
            similarity_values: List[float] = []
            local_novel_states = set()
            reward_total = 0.0
            discount = 1.0
            depth_reached = 0
            novelty_count = 0
            seen_edges = set()

            while (
                depth_reached < depth_limit
                and discount >= self.min_discount
                and nodes_visited < node_limit
                and edges_visited < edge_limit
            ):
                next_candidates = self._select_candidates(
                    current_state=current_state,
                    experiences=pool,
                    value_layer=value_layer,
                    action_id=action_token if depth_reached == 0 else "",
                )
                if not next_candidates:
                    break
                next_candidates = list(next_candidates[:branch_limit])
                if depth_reached == 0 and seed_exp in next_candidates:
                    next_exp = seed_exp
                else:
                    next_exp = self.rng.choice(next_candidates)
                edge_id = id(next_exp)
                if edge_id in seen_edges:
                    break
                seen_edges.add(edge_id)

                exp_state = self._extract_state(next_exp)
                similarity = self._similarity(
                    state_a=current_state,
                    state_b=exp_state,
                    value_layer=value_layer,
                )
                if similarity < self.similarity_threshold:
                    break
                similarity_values.append(float(similarity))

                reward_v = _safe_float(getattr(next_exp, "reward", 0.0), 0.0)
                rewards.append(float(reward_v))
                reward_total += discount * reward_v
                discount *= gamma_v * self.reward_decay

                actions.append(self._extract_action_id(next_exp))
                next_state = self._extract_next_state(next_exp)
                if not isinstance(next_state, Mapping):
                    if isinstance(exp_state, Mapping):
                        next_state = dict(exp_state)
                    else:
                        next_state = dict(current_state)
                else:
                    next_state = dict(next_state)
                states.append(next_state)

                depth_reached += 1
                nodes_visited += 1
                edges_visited += 1

                next_signature = self._state_signature(next_state, value_layer=value_layer)
                if (
                    next_signature
                    and next_signature not in observed_state_signatures
                    and next_signature not in local_novel_states
                ):
                    local_novel_states.add(next_signature)
                    novelty_count += 1
                    novelty_hits += 1

                current_state = next_state

            if depth_reached <= 0:
                continue

            novelty_score = float(novelty_count) / float(max(1, depth_limit))
            similarity_mean = (
                float(sum(similarity_values) / float(len(similarity_values)))
                if similarity_values
                else 0.0
            )
            confidence = _clamp(
                similarity_mean * (self.confidence_decay ** float(depth_reached)),
                0.0,
                1.0,
            )
            last_state = dict(states[-1] or {})
            last_state_value = 0.0
            if value_layer is not None:
                try:
                    last_state_value = float(value_layer.get_value(last_state))
                except Exception:
                    last_state_value = 0.0
            value_estimate = float(
                reward_total
                + (self.goal_bias * last_state_value)
                + (self.state_novelty_weight * novelty_score)
            )
            backup_factor = float(self.value_backup ** float(max(0, depth_reached - 1)))
            trajectory_value = float(value_estimate * confidence * backup_factor)
            root_action = str(action_token or (actions[0] if actions else ""))

            trajectory = ImaginedTrajectory(
                states=list(states),
                actions=list(actions),
                rewards=list(rewards),
                root_action=root_action,
                terminal_state_value=float(last_state_value),
                cumulative_reward=float(reward_total),
                value_estimate=float(value_estimate),
                novelty_score=float(novelty_score),
                confidence=float(confidence),
                depth=int(depth_reached),
            )
            trajectories.append(trajectory)
            values.append(float(trajectory_value))

        action_values = {}
        if action_token and values:
            action_values[action_token] = float(quantile(values, 0.7))
        return {
            "trajectories": list(trajectories),
            "values": list(values),
            "nodes_visited": int(min(nodes_visited, node_limit)),
            "edges_visited": int(min(edges_visited, edge_limit)),
            "novelty_hits": int(novelty_hits),
            "action_values": dict(action_values),
        }

    def generate_action_tree_imagination(
        self,
        *,
        start_state: Mapping[str, Any],
        candidate_actions: Sequence[str],
        experiences: Sequence[Any],
        depth: int,
        gamma: float,
        value_layer: Optional[ValueLayer],
    ) -> Dict[str, Any]:
        pool = list(experiences or [])
        if not pool:
            return self._empty_action_tree_result()

        unique_actions = []
        seen_actions = set()
        for action in list(candidate_actions or []):
            token = str(action or "").strip()
            if not token or token in seen_actions:
                continue
            seen_actions.add(token)
            unique_actions.append(token)
        if not unique_actions:
            return self._empty_action_tree_result()

        depth_limit = max(1, min(5, int(_safe_float(depth, self.depth))))
        gamma_v = _clamp(_safe_float(gamma, 0.95), 0.0, 0.999)
        branching_limit = max(1, min(4, int(_safe_float(self.branching, 3.0))))
        root_limit = max(1, min(branching_limit, len(unique_actions)))
        node_limit = max(1, min(128, int(_safe_float(self.max_tree_nodes, 128.0))))
        temperature = _clamp(_safe_float(self.action_temperature, 0.7), 0.05, 5.0)

        root_actions = self._top_k_actions(
            start_state=start_state,
            candidate_actions=unique_actions,
            experiences=pool,
            k=root_limit,
            temperature=temperature,
            value_layer=value_layer,
        )
        if not root_actions:
            return self._empty_action_tree_result()

        original_max_nodes = int(self.max_nodes)
        original_max_graph_nodes = int(self.max_graph_nodes)
        original_max_graph_edges = int(self.max_graph_edges)

        trajectories: List[ImaginedTrajectory] = []
        values: List[float] = []
        action_values: Dict[str, float] = {}
        nodes_visited = 0
        edges_visited = 0
        novelty_hits = 0
        remaining_nodes = int(node_limit)
        try:
            for root_action in list(root_actions):
                if remaining_nodes <= 0:
                    break
                per_action_nodes = max(
                    1,
                    min(
                        96,
                        int(remaining_nodes),
                        int(_safe_float(original_max_graph_nodes, 96.0)),
                    ),
                )
                per_action_edges = max(
                    1,
                    min(
                        192,
                        int(per_action_nodes * max(2, branching_limit)),
                        int(_safe_float(original_max_graph_edges, 192.0)),
                    ),
                )
                self.max_graph_nodes = int(per_action_nodes)
                self.max_nodes = int(per_action_nodes)
                self.max_graph_edges = int(per_action_edges)
                self.__post_init__()

                result = self.generate_structured_imagination(
                    start_state=dict(start_state or {}),
                    action_id=str(root_action),
                    experiences=pool,
                    depth=depth_limit,
                    gamma=gamma_v,
                    value_layer=value_layer,
                )
                root_trajectories = list(result.get("trajectories", []) or [])
                root_values = [float(v) for v in list(result.get("values", []) or [])]

                if root_values:
                    action_values[str(root_action)] = float(quantile(root_values, 0.7))
                trajectories.extend(root_trajectories)
                values.extend(root_values)
                action_nodes = int(result.get("nodes_visited", 0))
                action_edges = int(result.get("edges_visited", action_nodes))
                nodes_visited += action_nodes
                edges_visited += action_edges
                novelty_hits += int(result.get("novelty_hits", 0))
                remaining_nodes = max(0, node_limit - nodes_visited)
        finally:
            self.max_nodes = int(original_max_nodes)
            self.max_graph_nodes = int(original_max_graph_nodes)
            self.max_graph_edges = int(original_max_graph_edges)
            self.__post_init__()

        return {
            "trajectories": list(trajectories),
            "values": list(values),
            "action_values": dict(action_values),
            "nodes_visited": int(min(nodes_visited, node_limit)),
            "edges_visited": int(max(0, edges_visited)),
            "novelty_hits": int(max(0, novelty_hits)),
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "values": [],
            "nodes_visited": 0,
            "max_depth_reached": 0,
            "novelty_hits": 0,
        }

    def _empty_structured_result(self) -> Dict[str, Any]:
        return {
            "trajectories": [],
            "values": [],
            "nodes_visited": 0,
            "edges_visited": 0,
            "novelty_hits": 0,
            "action_values": {},
        }

    def _empty_action_tree_result(self) -> Dict[str, Any]:
        return {
            "trajectories": [],
            "values": [],
            "action_values": {},
            "nodes_visited": 0,
            "edges_visited": 0,
            "novelty_hits": 0,
        }

    def _similarity(
        self,
        *,
        state_a: Mapping[str, Any],
        state_b: Optional[Mapping[str, Any]],
        value_layer: Optional[ValueLayer],
    ) -> float:
        if not isinstance(state_b, Mapping):
            return 0.0
        try:
            return float(
                state_similarity(
                    state_a,
                    state_b,
                    encoder=getattr(value_layer, "encoder", None),
                )
            )
        except Exception:
            return 0.0

    def _select_candidates(
        self,
        *,
        current_state: Mapping[str, Any],
        experiences: Sequence[Any],
        value_layer: Optional[ValueLayer],
        action_id: str,
    ) -> List[Any]:
        ranked = []
        action_token = str(action_id or "")

        for exp in list(experiences or []):
            if action_token:
                exp_action = self._extract_action_id(exp)
                if exp_action and exp_action != action_token:
                    continue
            exp_state = self._extract_state(exp)
            if not isinstance(exp_state, Mapping):
                continue
            sim = self._similarity(
                state_a=current_state,
                state_b=exp_state,
                value_layer=value_layer,
            )
            if sim < self.similarity_threshold:
                continue
            ranked.append((sim, exp))

        ranked.sort(key=lambda item: float(item[0]), reverse=True)
        branch_limit = max(1, min(4, int(_safe_float(self.branching, 3.0))))
        return [exp for _, exp in ranked[:branch_limit]]

    def _top_k_actions(
        self,
        *,
        start_state: Mapping[str, Any],
        candidate_actions: Sequence[str],
        experiences: Sequence[Any],
        k: int,
        temperature: float,
        value_layer: Optional[ValueLayer],
    ) -> List[str]:
        action_tokens = []
        seen_actions = set()
        for action in list(candidate_actions or []):
            token = str(action or "").strip()
            if not token or token in seen_actions:
                continue
            seen_actions.add(token)
            action_tokens.append(token)
        if not action_tokens:
            return []

        limit = max(1, min(4, int(_safe_float(k, 1.0)), len(action_tokens)))
        branch_limit = max(1, min(4, int(_safe_float(self.branching, 3.0))))
        noise_scale = max(0.0, _safe_float(temperature, 0.7))
        scored = []

        for action_id in action_tokens:
            candidates = self._select_candidates(
                current_state=start_state,
                experiences=experiences,
                value_layer=value_layer,
                action_id=action_id,
            )
            if not candidates:
                score = -1e6
            else:
                window = list(candidates[:branch_limit])
                similarities = []
                rewards = []
                for exp in window:
                    exp_state = self._extract_state(exp)
                    similarities.append(
                        self._similarity(
                            state_a=start_state,
                            state_b=exp_state,
                            value_layer=value_layer,
                        )
                    )
                    rewards.append(_safe_float(getattr(exp, "reward", 0.0), 0.0))
                similarity_mean = (
                    float(sum(similarities) / float(len(similarities)))
                    if similarities
                    else 0.0
                )
                reward_mean = (
                    float(sum(rewards) / float(len(rewards)))
                    if rewards
                    else 0.0
                )
                score = float(similarity_mean + (0.25 * reward_mean))
            noise = (self.rng.random() - 0.5) * noise_scale
            scored.append((float(score + noise), str(action_id)))

        scored.sort(key=lambda item: (float(item[0]), str(item[1])), reverse=True)
        return [str(action_id) for _, action_id in scored[:limit]]

    def _extract_state(self, exp: Any) -> Optional[Mapping[str, Any]]:
        state = getattr(exp, "value_state_snapshot", None)
        if isinstance(state, Mapping):
            return dict(state)
        return None

    def _extract_next_state(self, exp: Any) -> Optional[Mapping[str, Any]]:
        next_state = getattr(exp, "value_next_state_snapshot", None)
        if isinstance(next_state, Mapping):
            return dict(next_state)
        return None

    def _extract_action_id(self, exp: Any) -> str:
        replay_action = str(getattr(exp, "replay_action_id", "")).strip()
        if replay_action:
            return replay_action
        try:
            signature = getattr(getattr(exp, "path", None), "signature", lambda: ())()
            for event_name in signature:
                token = str(event_name)
                if token.startswith("action:"):
                    return token.split(":", 1)[1]
        except Exception:
            return ""
        return ""

    def _state_signature(self, state: Optional[Mapping[str, Any]], value_layer: Optional[ValueLayer]) -> str:
        if not isinstance(state, Mapping):
            return ""
        layer = value_layer
        if layer is not None:
            try:
                return str(layer.encoder.encode(state))
            except Exception:
                pass
        context_signature = str(state.get("context_signature", "")).strip()
        action = str(state.get("action", "")).strip()
        consequence = str(state.get("consequence", "")).strip()
        return f"{context_signature}|{action}|{consequence}"

    def _observed_state_signatures_for_action(
        self,
        *,
        experiences: Sequence[Any],
        action_id: str,
        value_layer: Optional[ValueLayer],
    ) -> set:
        action_token = str(action_id or "")
        observed = set()
        for exp in list(experiences or []):
            exp_action = self._extract_action_id(exp)
            if action_token and exp_action != action_token:
                continue
            exp_state = self._extract_state(exp)
            signature = self._state_signature(exp_state, value_layer=value_layer)
            if signature:
                observed.add(signature)
        return observed


__all__ = ["HippocampalImagineEngine", "ImaginedTrajectory", "quantile"]
