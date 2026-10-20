"""Waking labile tier: bounded, time-decaying offsets on Q and BG channels.

Stable Q and Go/NoGo stay on their own objects. This layer stores only the
offsets, the host time of each entry, and the applied contribution of each
episode so a revised rating can replace that episode instead of stacking.

``capture_kappa`` and ``replay_priority_weights`` are part of the config
block. Sleep reads them. This layer stores the tags and can report the
decayed remainder of one episode; it does not write the stable tier.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

_QKey = Tuple[str, str]
_VisitKey = Tuple[str, str]


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    if not math.isfinite(parsed):
        return float(default)
    return parsed


@dataclass
class PlasticityConfig:
    """Host-facing plasticity block. Time defaults derive from the wake interval."""

    expected_wake_interval_s: Optional[float] = None
    tau_labile_ratio: float = 1.0
    # Explicit tau overrides ratio * wake interval when set.
    tau_labile_s: Optional[float] = None
    # None → 0.1 * alpha_reference (stable replay alpha_default).
    eta_labile_q: Optional[float] = None
    alpha_reference: float = 0.03
    labile_step_clamp_q: float = 0.05
    labile_amp_clamp_q: float = 0.2
    eta_labile_channel: float = 0.02
    labile_amp_clamp_channel: float = 0.1
    # Sleep consolidation. κ of the decayed channel tag is captured;
    # the sleep Go/NoGo step uses eta_channel_sleep - κ * eta_labile_channel.
    capture_kappa: float = 0.5
    eta_channel_sleep: float = 0.08
    replay_priority_weights: Tuple[float, float, float, float] = (1.0, 0.5, 0.25, 0.25)
    labile_epsilon: float = 1e-6
    _wake_interval_warning_sent: bool = field(default=False, repr=False, compare=False)

    def warn_unset_wake_interval(self, logger) -> None:
        if self.expected_wake_interval_s is not None:
            return
        if self._wake_interval_warning_sent:
            return
        self._wake_interval_warning_sent = True
        logger.warning(
            "PlasticityConfig.expected_wake_interval_s is unset; "
            "falling back to 3600 s. The host should set the expected "
            "interval between sleeps."
        )

    def resolved_wake_interval_s(self) -> float:
        raw = self.expected_wake_interval_s
        if raw is None:
            return 3600.0
        value = _finite(raw, 3600.0)
        if value <= 0.0:
            return 3600.0
        return value

    def resolved_tau_s(self) -> float:
        if self.tau_labile_s is not None:
            explicit = _finite(self.tau_labile_s, 0.0)
            if explicit > 0.0:
                return explicit
        ratio = _finite(self.tau_labile_ratio, 1.0)
        if ratio <= 0.0:
            ratio = 1.0
        return ratio * self.resolved_wake_interval_s()

    def resolved_eta_q(self) -> float:
        if self.eta_labile_q is not None:
            return max(0.0, _finite(self.eta_labile_q, 0.0))
        return 0.1 * max(0.0, _finite(self.alpha_reference, 0.03))

    def to_dict(self) -> dict:
        weights = tuple(float(item) for item in self.replay_priority_weights)
        return {
            "expected_wake_interval_s": self.expected_wake_interval_s,
            "tau_labile_ratio": float(self.tau_labile_ratio),
            "tau_labile_s": self.tau_labile_s,
            "eta_labile_q": self.eta_labile_q,
            "alpha_reference": float(self.alpha_reference),
            "labile_step_clamp_q": float(self.labile_step_clamp_q),
            "labile_amp_clamp_q": float(self.labile_amp_clamp_q),
            "eta_labile_channel": float(self.eta_labile_channel),
            "labile_amp_clamp_channel": float(self.labile_amp_clamp_channel),
            "capture_kappa": float(self.capture_kappa),
            "eta_channel_sleep": float(self.eta_channel_sleep),
            "replay_priority_weights": list(weights),
            "labile_epsilon": float(self.labile_epsilon),
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "PlasticityConfig":
        raw = dict(data or {})
        weights_raw = raw.get("replay_priority_weights", (1.0, 0.5, 0.25, 0.25))
        try:
            weights = tuple(float(item) for item in list(weights_raw))
        except (TypeError, ValueError):
            weights = (1.0, 0.5, 0.25, 0.25)
        if len(weights) != 4:
            weights = (1.0, 0.5, 0.25, 0.25)
        eta = raw.get("eta_labile_q", None)
        tau = raw.get("tau_labile_s", None)
        interval = raw.get("expected_wake_interval_s", None)
        return cls(
            expected_wake_interval_s=None if interval is None else float(interval),
            tau_labile_ratio=float(raw.get("tau_labile_ratio", 1.0)),
            tau_labile_s=None if tau is None else float(tau),
            eta_labile_q=None if eta is None else float(eta),
            alpha_reference=float(raw.get("alpha_reference", 0.03)),
            labile_step_clamp_q=float(raw.get("labile_step_clamp_q", 0.05)),
            labile_amp_clamp_q=float(raw.get("labile_amp_clamp_q", 0.2)),
            eta_labile_channel=float(raw.get("eta_labile_channel", 0.02)),
            labile_amp_clamp_channel=float(raw.get("labile_amp_clamp_channel", 0.1)),
            capture_kappa=float(raw.get("capture_kappa", 0.5)),
            eta_channel_sleep=float(raw.get("eta_channel_sleep", 0.08)),
            replay_priority_weights=weights,  # type: ignore[arg-type]
            labile_epsilon=float(raw.get("labile_epsilon", 1e-6)),
        )


class LabileLayer:
    """Clamped waking offsets. Decay is closed-form in host time."""

    def __init__(self, config: Optional[PlasticityConfig] = None):
        self.config = config if config is not None else PlasticityConfig()
        self._q: Dict[_QKey, float] = {}
        self._q_time: Dict[_QKey, float] = {}
        self._go: Dict[str, float] = {}
        self._nogo: Dict[str, float] = {}
        self._channel_time: Dict[str, float] = {}
        self._contributions: Dict[str, dict] = {}
        self._visits: Dict[_VisitKey, float] = {}

    def _tau(self) -> float:
        return max(1e-9, float(self.config.resolved_tau_s()))

    def _epsilon(self) -> float:
        return max(0.0, float(self.config.labile_epsilon))

    def _factor(self, t0: float, t1: float) -> float:
        dt = float(t1) - float(t0)
        if dt <= 0.0:
            return 1.0
        exponent = -dt / self._tau()
        if exponent < -80.0:
            return 0.0
        return math.exp(exponent)

    def _q_key(self, state_key: str, action: str) -> _QKey:
        return (str(state_key or ""), str(action or ""))

    def _materialize_q(self, key: _QKey, now: float) -> float:
        if key not in self._q:
            return 0.0
        value = float(self._q[key]) * self._factor(self._q_time.get(key, now), now)
        if abs(value) < self._epsilon():
            self._q.pop(key, None)
            self._q_time.pop(key, None)
            return 0.0
        self._q[key] = value
        self._q_time[key] = float(now)
        return value

    def _materialize_channel(self, action: str, now: float) -> Tuple[float, float]:
        name = str(action or "")
        if name not in self._go and name not in self._nogo:
            return 0.0, 0.0
        factor = self._factor(self._channel_time.get(name, now), now)
        go = float(self._go.get(name, 0.0)) * factor
        nogo = float(self._nogo.get(name, 0.0)) * factor
        eps = self._epsilon()
        if abs(go) < eps and abs(nogo) < eps:
            self._go.pop(name, None)
            self._nogo.pop(name, None)
            self._channel_time.pop(name, None)
            return 0.0, 0.0
        self._go[name] = go
        self._nogo[name] = nogo
        self._channel_time[name] = float(now)
        return go, nogo

    def q_offset(self, state_key: str, action: str, now: float) -> float:
        return self._materialize_q(self._q_key(state_key, action), now)

    def channel_offset(self, action: str, now: float) -> Tuple[float, float]:
        return self._materialize_channel(str(action or ""), now)

    def effective_q(self, state_key: str, action: str, stable: float, now: float) -> float:
        return float(stable) + self.q_offset(state_key, action, now)

    def effective_channel(
        self,
        action: str,
        go_stable: float,
        nogo_stable: float,
        now: float,
    ) -> Tuple[float, float]:
        go_l, nogo_l = self.channel_offset(action, now)
        return (
            _clamp(float(go_stable) + go_l, 0.0, 1.0),
            _clamp(float(nogo_stable) + nogo_l, 0.0, 1.0),
        )

    def _remaining(self, delta: float, t0: float, now: float) -> float:
        return float(delta) * self._factor(t0, now)

    def _subtract_q(self, contrib: dict, now: float) -> None:
        key = self._q_key(str(contrib.get("state_key", "")), str(contrib.get("action", "")))
        current = self._materialize_q(key, now)
        removed = self._remaining(
            _finite(contrib.get("q_delta", 0.0)),
            _finite(contrib.get("q_time", now), now),
            now,
        )
        updated = current - removed
        if abs(updated) < self._epsilon():
            self._q.pop(key, None)
            self._q_time.pop(key, None)
            return
        self._q[key] = updated
        self._q_time[key] = float(now)

    def _subtract_channel(self, contrib: dict, now: float) -> None:
        action = str(contrib.get("action", "") or "")
        if not action:
            return
        go, nogo = self._materialize_channel(action, now)
        t0 = _finite(contrib.get("channel_time", now), now)
        go -= self._remaining(_finite(contrib.get("go_delta", 0.0)), t0, now)
        nogo -= self._remaining(_finite(contrib.get("nogo_delta", 0.0)), t0, now)
        eps = self._epsilon()
        if abs(go) < eps and abs(nogo) < eps:
            self._go.pop(action, None)
            self._nogo.pop(action, None)
            self._channel_time.pop(action, None)
            return
        self._go[action] = go
        self._nogo[action] = nogo
        self._channel_time[action] = float(now)

    def remaining_channel(self, episode_id: str, now: float) -> Tuple[float, float]:
        """Decayed Go/NoGo tag still attributed to this episode. Does not remove it."""
        contrib = self._contributions.get(str(episode_id or ""))
        if not isinstance(contrib, dict):
            return 0.0, 0.0
        t0 = _finite(contrib.get("channel_time", now), now)
        go = self._remaining(_finite(contrib.get("go_delta", 0.0)), t0, now)
        nogo = self._remaining(_finite(contrib.get("nogo_delta", 0.0)), t0, now)
        return float(go), float(nogo)

    def take_visits(self) -> Dict[_VisitKey, float]:
        """Hand the waking visit counters to sleep and reset them.

        The counters do not decay. Sleep adds them into the stable counts.
        """
        rows = dict(self._visits)
        self._visits.clear()
        return rows

    def pop_contribution(self, episode_id: str, now: float) -> dict:
        """Remove one episode's decayed contribution. Unknown ids are a no-op."""
        key = str(episode_id or "")
        contrib = self._contributions.pop(key, None)
        if not isinstance(contrib, dict):
            return {}
        self._subtract_q(contrib, now)
        self._subtract_channel(contrib, now)
        return dict(contrib)

    def _channel_raw(self, reward: float) -> Tuple[float, float]:
        eta = max(0.0, _finite(self.config.eta_labile_channel, 0.0))
        if reward > 0.0:
            return eta * reward, -0.5 * eta * reward
        if reward < 0.0:
            magnitude = abs(reward)
            return -0.5 * eta * magnitude, eta * magnitude
        return 0.0, 0.0

    def _q_step(self, td_error: float, g_da: float) -> float:
        gain = _clamp(_finite(g_da, 1.0), 0.0, 2.0)
        raw = self.config.resolved_eta_q() * gain * float(td_error)
        step = abs(_finite(self.config.labile_step_clamp_q, 0.05))
        return _clamp(raw, -step, step)

    def apply_outcome(
        self,
        *,
        episode_id: str,
        state_key: str,
        action: str,
        reward: float,
        td_error: float,
        now: float,
        g_da: float = 1.0,
    ) -> dict:
        """Add one episode's clamped contribution.

        Call ``pop_contribution`` first when replacing a rating. The stored
        deltas are the post-clamp change, so a later pop undoes this write
        after the same decay.
        """
        episode = str(episode_id or "")
        if episode and episode in self._contributions:
            self.pop_contribution(episode, now)
        action_name = str(action or "")
        key = self._q_key(state_key, action_name)
        amp_q = abs(_finite(self.config.labile_amp_clamp_q, 0.2))
        q_before = self._materialize_q(key, now)
        q_after = _clamp(q_before + self._q_step(td_error, g_da), -amp_q, amp_q)
        q_delta = q_after - q_before
        if abs(q_after) < self._epsilon():
            self._q.pop(key, None)
            self._q_time.pop(key, None)
        else:
            self._q[key] = q_after
            self._q_time[key] = float(now)

        amp_c = abs(_finite(self.config.labile_amp_clamp_channel, 0.1))
        go_before, nogo_before = self._materialize_channel(action_name, now) if action_name else (0.0, 0.0)
        raw_go, raw_nogo = self._channel_raw(float(reward)) if action_name else (0.0, 0.0)
        go_after = _clamp(go_before + raw_go, -amp_c, amp_c)
        nogo_after = _clamp(nogo_before + raw_nogo, -amp_c, amp_c)
        go_delta = go_after - go_before
        nogo_delta = nogo_after - nogo_before
        if action_name:
            if abs(go_after) < self._epsilon() and abs(nogo_after) < self._epsilon():
                self._go.pop(action_name, None)
                self._nogo.pop(action_name, None)
                self._channel_time.pop(action_name, None)
            else:
                self._go[action_name] = go_after
                self._nogo[action_name] = nogo_after
                self._channel_time[action_name] = float(now)

        contrib = {
            "state_key": str(state_key or ""),
            "action": action_name,
            "q_delta": float(q_delta),
            "q_time": float(now),
            "go_delta": float(go_delta),
            "nogo_delta": float(nogo_delta),
            "channel_time": float(now),
            "reward": float(reward),
            "td_error": float(td_error),
        }
        if episode:
            self._contributions[episode] = dict(contrib)
        return dict(contrib)

    def replace_contribution(
        self,
        episode_id: str,
        *,
        state_key: str,
        action: str,
        reward: float,
        td_error: float,
        now: float,
        g_da: float = 1.0,
    ) -> dict:
        """Drop the episode's decayed contribution, then apply ``td_error``.

        ``td_error`` must already be computed on effective values after the
        removal. Prefer pop, recompute δ, then ``apply_outcome``.
        """
        self.pop_contribution(episode_id, now)
        return self.apply_outcome(
            episode_id=episode_id,
            state_key=state_key,
            action=action,
            reward=reward,
            td_error=td_error,
            now=now,
            g_da=g_da,
        )

    def decay_to(self, now: float) -> None:
        """Materialize every entry at ``now`` and drop numerical dust."""
        for key in list(self._q):
            self._materialize_q(key, now)
        for action in list(set(self._go) | set(self._nogo)):
            self._materialize_channel(action, now)

    def note_visit(self, context_key: str, action: str, amount: float = 1.0) -> None:
        """Waking exploration counter. It does not decay and is not stable."""
        token = (str(context_key or ""), str(action or ""))
        if not token[1]:
            return
        self._visits[token] = float(self._visits.get(token, 0.0)) + float(amount)

    def visit_count(self, context_key: str, action: str) -> float:
        return float(self._visits.get((str(context_key or ""), str(action or "")), 0.0))

    def max_abs_q(self, now: float) -> float:
        self.decay_to(now)
        if not self._q:
            return 0.0
        return max(abs(float(value)) for value in self._q.values())

    def max_abs_channel(self, now: float) -> float:
        self.decay_to(now)
        values = list(self._go.values()) + list(self._nogo.values())
        if not values:
            return 0.0
        return max(abs(float(value)) for value in values)

    def snapshot(self, now: float) -> dict:
        """Effective offsets at ``now``, independent of how time was sliced."""
        self.decay_to(now)
        q_rows = [
            {
                "state_key": key[0],
                "action": key[1],
                "value": float(self._q[key]),
                "updated_at": float(self._q_time.get(key, now)),
            }
            for key in sorted(self._q)
        ]
        actions = sorted(set(self._go) | set(self._nogo))
        channels = [
            {
                "action": action,
                "go": float(self._go.get(action, 0.0)),
                "nogo": float(self._nogo.get(action, 0.0)),
                "updated_at": float(self._channel_time.get(action, now)),
            }
            for action in actions
        ]
        visits = [
            {"context": key[0], "action": key[1], "count": float(count)}
            for key, count in sorted(self._visits.items())
        ]
        contributions = {
            str(episode_id): dict(payload)
            for episode_id, payload in sorted(self._contributions.items())
        }
        return {
            "q": q_rows,
            "channels": channels,
            "visits": visits,
            "contributions": contributions,
            "tau_s": float(self.config.resolved_tau_s()),
            "eta_q": float(self.config.resolved_eta_q()),
        }

    def to_dict(self) -> dict:
        return {
            "config": self.config.to_dict(),
            "q": [
                {
                    "state_key": key[0],
                    "action": key[1],
                    "value": float(value),
                    "updated_at": float(self._q_time.get(key, 0.0)),
                }
                for key, value in self._q.items()
            ],
            "channels": [
                {
                    "action": action,
                    "go": float(self._go.get(action, 0.0)),
                    "nogo": float(self._nogo.get(action, 0.0)),
                    "updated_at": float(self._channel_time.get(action, 0.0)),
                }
                for action in set(self._go) | set(self._nogo)
            ],
            "contributions": {
                str(episode_id): dict(payload)
                for episode_id, payload in self._contributions.items()
            },
            "visits": [
                {"context": key[0], "action": key[1], "count": float(count)}
                for key, count in self._visits.items()
            ],
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "LabileLayer":
        raw = dict(data or {})
        config_raw = raw.get("config")
        layer = cls(
            PlasticityConfig.from_dict(config_raw) if isinstance(config_raw, dict) else PlasticityConfig()
        )
        for row in list(raw.get("q") or []):
            if not isinstance(row, dict):
                continue
            key = layer._q_key(str(row.get("state_key", "")), str(row.get("action", "")))
            layer._q[key] = _finite(row.get("value", 0.0))
            layer._q_time[key] = _finite(row.get("updated_at", 0.0))
        for row in list(raw.get("channels") or []):
            if not isinstance(row, dict):
                continue
            action = str(row.get("action", "") or "")
            if not action:
                continue
            layer._go[action] = _finite(row.get("go", 0.0))
            layer._nogo[action] = _finite(row.get("nogo", 0.0))
            layer._channel_time[action] = _finite(row.get("updated_at", 0.0))
        contributions = raw.get("contributions") or {}
        if isinstance(contributions, dict):
            for episode_id, payload in contributions.items():
                if isinstance(payload, dict):
                    layer._contributions[str(episode_id)] = dict(payload)
        for row in list(raw.get("visits") or []):
            if not isinstance(row, dict):
                continue
            token = (str(row.get("context", "")), str(row.get("action", "")))
            layer._visits[token] = _finite(row.get("count", 0.0))
        return layer
