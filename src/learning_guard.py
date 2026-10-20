"""Stable-tier write guard.

Waking code may read the stable tier. Writers run only inside
``learning_allowed()`` (sleep consolidation) or ``initializing()``
(construction, load, host seeding).

``NOWA_STRICT_LEARNING=1`` (set by the core test suite) raises
``WakingLearningError``. Production logs once per writer and skips the write.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

_LOG = logging.getLogger("nowa.learning")

_LEARNING_DEPTH: ContextVar[int] = ContextVar("nowa_learning_depth", default=0)
_INIT_DEPTH: ContextVar[int] = ContextVar("nowa_init_depth", default=0)
_SKIP_LOGGED: set[str] = set()


class WakingLearningError(RuntimeError):
    """A stable-tier writer ran while the agent was awake."""


def strict_learning_enabled() -> bool:
    raw = str(os.environ.get("NOWA_STRICT_LEARNING", "")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def learning_is_open() -> bool:
    return _LEARNING_DEPTH.get() > 0 or _INIT_DEPTH.get() > 0


@contextmanager
def learning_allowed() -> Iterator[None]:
    """Mark the dynamic scope as the sleep consolidation writer."""
    token = _LEARNING_DEPTH.set(_LEARNING_DEPTH.get() + 1)
    try:
        yield
    finally:
        _LEARNING_DEPTH.reset(token)


@contextmanager
def initializing() -> Iterator[None]:
    """Mark construction, load, or explicit host seeding."""
    token = _INIT_DEPTH.set(_INIT_DEPTH.get() + 1)
    try:
        yield
    finally:
        _INIT_DEPTH.reset(token)


def assert_learning_allowed(writer: str) -> bool:
    """Return True when the write may proceed.

    Strict mode raises. Production logs once and returns False so the
    caller leaves the stable value unchanged.
    """
    if learning_is_open():
        return True
    if strict_learning_enabled():
        raise WakingLearningError(
            f"{writer} writes the stable tier while awake. "
            "Stable parameters change only inside sleep."
        )
    if writer not in _SKIP_LOGGED:
        _SKIP_LOGGED.add(writer)
        _LOG.warning(
            "%s skipped: stable-tier writes are allowed only during sleep "
            "(set NOWA_STRICT_LEARNING=1 to raise instead).",
            writer,
        )
    return False


def _json_ready(value: Any) -> Any:
    if isinstance(value, float):
        if value != value:
            return "NaN"
        if value == float("inf"):
            return "Infinity"
        if value == float("-inf"):
            return "-Infinity"
        return value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(val) for key, val in value.items()}
    return str(value)


def _canonical(payload: Any) -> str:
    return json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _trace_strengths(agent: Any) -> list:
    memory = getattr(agent, "intent_memory", None)
    traces = getattr(memory, "traces", None)
    if not isinstance(traces, dict):
        return []
    rows = []
    for key, trace in traces.items():
        try:
            strength = float(getattr(trace, "strength", 0.0))
        except (TypeError, ValueError):
            continue
        # Strength 0 is an empty waking trace, not a stable habit.
        if strength <= 0.0:
            continue
        rows.append({"key": str(key), "strength": strength})
    rows.sort(key=lambda row: row["key"])
    return rows


def _channel_rows(agent: Any) -> list:
    channels = getattr(agent, "bg_action_channels", None)
    if not isinstance(channels, dict):
        return []
    rows = []
    for action_id in sorted(channels, key=str):
        channel = channels[action_id]
        rows.append(
            {
                "action": str(action_id),
                "go_weight": float(getattr(channel, "go_weight", 0.0)),
                "nogo_weight": float(getattr(channel, "nogo_weight", 0.0)),
                "habit_strength": float(getattr(channel, "habit_strength", 0.0)),
                "prior_go": float(getattr(channel, "prior_go", 0.0) or 0.0),
                "prior_nogo": float(getattr(channel, "prior_nogo", 0.0) or 0.0),
                "prior_habit": float(getattr(channel, "prior_habit", 0.0) or 0.0),
            }
        )
    return rows


def _visit_rows(agent: Any) -> list:
    counts = getattr(agent, "_action_visit_counts", None)
    if not isinstance(counts, dict):
        return []
    rows = []
    for key, count in counts.items():
        if not isinstance(key, tuple) or len(key) != 2:
            continue
        try:
            rows.append([str(key[0]), str(key[1]), int(count)])
        except (TypeError, ValueError):
            continue
    rows.sort()
    return rows


def _value_rows(agent: Any) -> dict:
    layer = getattr(agent, "value_layer", None)
    values = getattr(layer, "values", None)
    expectation = getattr(layer, "expectation_memory", None)
    value_rows = []
    if isinstance(values, dict):
        for key in sorted(values, key=str):
            try:
                value_rows.append([str(key), float(values[key])])
            except (TypeError, ValueError):
                continue
    expectation_rows = []
    if isinstance(expectation, dict):
        for key in sorted(expectation, key=str):
            expectation_rows.append([str(key), expectation[key]])
    return {"values": value_rows, "expectation_memory": expectation_rows}


def _temporal_chain_rows(agent: Any) -> list:
    """Learned sleep chains. Wall-clock stamps are not part of the structure."""
    sleep = getattr(agent, "sleep_manager", None)
    memory = getattr(sleep, "chain_memory", None)
    chains = getattr(memory, "chains", None)
    if not isinstance(chains, dict):
        return []
    rows = []
    for signature, chain in chains.items():
        try:
            sig = [str(item) for item in tuple(signature)]
        except TypeError:
            sig = [str(signature)]
        try:
            net_affect = float(getattr(chain, "net_affect", 0.0))
            stability = float(getattr(chain, "stability", 0.0))
            usage = int(getattr(chain, "usage_count", 0))
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "signature": sig,
                "net_affect": net_affect,
                "stability": stability,
                "usage_count": usage,
            }
        )
    rows.sort(key=lambda row: row["signature"])
    return rows


def _cortex_rows(agent: Any) -> list:
    cortex = getattr(agent, "cortex", None)
    patterns = getattr(cortex, "patterns", None)
    if not isinstance(patterns, list):
        return []
    rows = []
    for pattern in patterns:
        signature = tuple(getattr(pattern, "signature", ()) or ())
        try:
            strength = float(getattr(pattern, "strength", 0.0))
        except (TypeError, ValueError):
            strength = 0.0
        rows.append(
            {
                "signature": [str(item) for item in signature],
                "strength": strength,
                "source_experiences": int(getattr(pattern, "source_experiences", 0) or 0),
            }
        )
    rows.sort(key=lambda row: (row["signature"], row["strength"]))
    return rows


def _strategy_rows(agent: Any) -> dict:
    layer = getattr(agent, "external_interaction_layer", None)
    weights = getattr(layer, "strategy_weights", None)
    strategy = {}
    if isinstance(weights, dict):
        for key in sorted(weights, key=str):
            try:
                strategy[str(key)] = float(weights[key])
            except (TypeError, ValueError):
                continue
    metadata_weights = {}
    selector = getattr(agent, "selector", None)
    metadata = getattr(selector, "action_metadata", None)
    if isinstance(metadata, dict):
        for key in sorted(metadata, key=str):
            meta = metadata[key]
            if not isinstance(meta, dict) or "strategy_weight" not in meta:
                continue
            try:
                metadata_weights[str(key)] = float(meta["strategy_weight"])
            except (TypeError, ValueError):
                continue
    learning = getattr(agent, "bg_learning", None)
    try:
        bg_rate = float(getattr(learning, "learning_rate", 0.0))
    except (TypeError, ValueError):
        bg_rate = 0.0
    neuromod = getattr(agent, "neuromodulators", None)
    baselines = {}
    raw_baselines = getattr(neuromod, "baselines", None)
    if isinstance(raw_baselines, dict):
        for key in sorted(raw_baselines, key=str):
            try:
                baselines[str(key)] = float(raw_baselines[key])
            except (TypeError, ValueError):
                continue
    try:
        ach_baseline = float(getattr(neuromod, "ach_baseline", 0.0))
    except (TypeError, ValueError):
        ach_baseline = 0.0
    config = getattr(agent, "plasticity", None)
    config_payload = config.to_dict() if hasattr(config, "to_dict") else {}
    return {
        "strategy_weights": strategy,
        "action_metadata_strategy_weight": metadata_weights,
        "bg_learning_rate": bg_rate,
        "neuromodulator_baselines": baselines,
        "ach_baseline": ach_baseline,
        "plasticity": config_payload,
    }


def guard_owned_writer(layer: Any, writer: str) -> bool:
    """Sleep-only check for a layer the agent has bound as stable.

    A free-standing layer (unit tests, construction before bind) is not the
    agent's stable tier and may run its update. Once ``_stable_owner`` is
    set, the same method is a stable writer.
    """
    if getattr(layer, "_stable_owner", None) is None:
        return True
    return assert_learning_allowed(writer)


def _slow_affect_rows(agent: Any) -> dict:
    """Category A item 7. Fast affect position and regulation output stay out.

    Wall-clock stamps are not parameters. Outcome statistics of conflict
    arbitration are included; the per-step control mode is state.
    """
    background = getattr(agent, "affective_background", None)
    semantic = getattr(agent, "semantic_emotions", None)
    memory = getattr(agent, "emotional_memory", None)
    expectations = getattr(agent, "emotional_expectations", None)
    arbitration = getattr(agent, "conflict_arbitration", None)
    background_rows = {}
    if background is not None and hasattr(background, "snapshot"):
        try:
            background_rows = dict(background.snapshot() or {})
        except Exception:
            background_rows = {}
    semantic_rows = []
    if semantic is not None and hasattr(semantic, "snapshot"):
        try:
            for item in list(semantic.snapshot() or []):
                if not isinstance(item, dict):
                    continue
                semantic_rows.append(
                    {
                        "emotion": str(item.get("emotion", "")),
                        "activation": float(item.get("activation", 0.0)),
                        "stability": float(item.get("stability", 0.0)),
                        "obsessive": bool(item.get("obsessive", False)),
                    }
                )
        except Exception:
            semantic_rows = []
    memory_rows = {}
    if memory is not None and hasattr(memory, "snapshot"):
        try:
            raw = dict(memory.snapshot() or {})
            raw.pop("last_update_ts", None)
            memory_rows = raw
        except Exception:
            memory_rows = {}
    expectation_rows = {}
    if expectations is not None and hasattr(expectations, "snapshot"):
        try:
            raw = dict(expectations.snapshot() or {})
            raw.pop("last_update_ts", None)
            expectation_rows = raw
        except Exception:
            expectation_rows = {}
    failure_rows = {}
    if arbitration is not None:
        try:
            failure_rows = {
                "recent_failure_rate": float(getattr(arbitration, "recent_failure_rate", 0.0)),
                "recent_failures": [float(item) for item in list(getattr(arbitration, "recent_failures", []) or [])],
                "error_history_window": [
                    float(item) for item in list(getattr(arbitration, "error_history_window", []) or [])
                ],
            }
        except Exception:
            failure_rows = {}
    return {
        "affective_background": background_rows,
        "semantic_emotions": semantic_rows,
        "emotional_memory": memory_rows,
        "emotional_expectations": expectation_rows,
        "conflict_outcome_stats": failure_rows,
    }


def stable_payload(agent: Any) -> dict:
    """Canonical category-A payload.

    Slow affective statistics are included. They change only inside sleep.
    Fast affect position, valence/arousal, and regulation output stay out:
    those are state and still move while awake.
    """
    return {
        "value_layer": _value_rows(agent),
        "visit_counts": _visit_rows(agent),
        "intent_strengths": _trace_strengths(agent),
        "channels": _channel_rows(agent),
        "cortex": _cortex_rows(agent),
        "temporal_chains": _temporal_chain_rows(agent),
        "strategies": _strategy_rows(agent),
        "slow_affect": _slow_affect_rows(agent),
    }


def stable_fingerprint(agent: Any) -> str:
    """sha256 of the canonical stable-tier serialization."""
    encoded = _canonical(stable_payload(agent)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def labile_snapshot(agent: Any) -> dict:
    """Materialized labile tier at the agent's host clock."""
    layer = getattr(agent, "labile", None)
    if layer is None or not hasattr(layer, "snapshot"):
        return {}
    now = float(getattr(agent, "_host_clock_s", 0.0) or 0.0)
    return layer.snapshot(now)
