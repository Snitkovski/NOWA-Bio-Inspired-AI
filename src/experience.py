import sys
import time
from typing import List, Tuple
from enum import Enum


def _pickle_state_dict(state):
    """One dict for both pickle layouts.

    ``main`` saved ordinary instances, so the payload is their ``__dict__``.
    A slotted instance saved on this branch arrives as ``(None, slot_dict)``
    from ``object.__getstate__`` (or ``(dict, slot_dict)`` if both exist).
    """
    if isinstance(state, dict):
        return state
    if (
        isinstance(state, tuple)
        and len(state) == 2
        and (state[0] is None or isinstance(state[0], dict))
        and isinstance(state[1], dict)
    ):
        merged = dict(state[0] or {})
        merged.update(state[1])
        return merged
    raise TypeError(f"unsupported pickle state: {type(state).__name__}")


def _intern_short_token(value):
    if isinstance(value, str) and len(value) <= 80:
        return sys.intern(value)
    return value


def _intern_token_collection(value):
    if isinstance(value, set):
        return {_intern_short_token(item) for item in value}
    if isinstance(value, tuple):
        return tuple(_intern_short_token(item) for item in value)
    if isinstance(value, list):
        return [_intern_short_token(item) for item in value]
    return _intern_short_token(value)


class EventType(Enum):
    """Types of events in experience"""
    CONTEXT = "context"      # Внешний контекст
    ACTION = "action"        # Выбранное действие (now IntentType)
    REALIZATION = "realization"  # Output/expression of the action
    CONSEQUENCE = "consequence"  # Результат действия


class Event:
    """Immutable event with timestamp and magnitude"""

    __slots__ = ("name", "event_type", "magnitude", "timestamp", "_frozen")

    def __init__(self, name: str, event_type: EventType = EventType.CONTEXT, 
                 magnitude: float = 1.0, timestamp: float = None):
        if isinstance(name, str) and len(name) <= 80:
            # Repeated context tokens share one str. Unique long names stay unpinned.
            name = sys.intern(name)
        self.name = name
        self.event_type = event_type
        self.magnitude = magnitude  # Интенсивность события
        self.timestamp = timestamp or time.time()
        self._frozen = False  # Флаг неизменяемости

    def freeze(self):
        """Сделать событие неизменяемым"""
        self._frozen = True

    def __getstate__(self):
        return {slot: getattr(self, slot) for slot in self.__slots__}

    def __setstate__(self, state):
        # object.__setattr__ so a frozen flag cannot reject the load.
        # A save from main is the old __dict__. A save from this branch is the slot dict.
        payload = _pickle_state_dict(state)
        name = payload.get("name", "")
        if not isinstance(name, str):
            name = str(name)
        object.__setattr__(self, "name", _intern_short_token(name))
        event_type = payload.get("event_type", EventType.CONTEXT)
        if not isinstance(event_type, EventType):
            event_type = EventType.CONTEXT
        object.__setattr__(self, "event_type", event_type)
        try:
            magnitude = float(payload.get("magnitude", 1.0))
        except (TypeError, ValueError):
            magnitude = 1.0
        object.__setattr__(self, "magnitude", magnitude)
        try:
            timestamp = float(payload.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            timestamp = 0.0
        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "_frozen", bool(payload.get("_frozen", False)))

    def __setattr__(self, name, value):
        # Позволяем установить _frozen
        if name == '_frozen':
            object.__setattr__(self, name, value)
        elif hasattr(self, '_frozen') and self._frozen:
            raise ValueError(f"Cannot modify frozen Event: {name}")
        else:
            object.__setattr__(self, name, value)

    def __repr__(self):
        return f"{self.name}({self.event_type.value}@{self.magnitude})"

    def __hash__(self):
        return hash((self.name, self.event_type, self.magnitude))

    def __eq__(self, other):
        if isinstance(other, Event):
            return (self.name == other.name and 
                    self.event_type == other.event_type)
        return False


class Path:
    """Immutable sequence of events that forms an experience"""

    __slots__ = ("events", "_frozen")

    def __init__(self, events: List[Event] = None):
        self.events = tuple(events) if events else ()
        self._frozen = False

    def add_event(self, event: Event) -> 'Path':
        """Create new Path with additional event (doesn't modify this)"""
        if self._frozen:
            raise ValueError("Cannot add to frozen Path")
        new_events = list(self.events) + [event]
        return Path(new_events)

    def freeze(self):
        """Сделать Path неизменяемым"""
        for event in self.events:
            event.freeze()
        self._frozen = True

    def signature(self) -> Tuple:
        """Get immutable signature of path"""
        return tuple(e.name for e in self.events)

    def matches(self, context_events: List[str]) -> bool:
        """Check if path contains all context events"""
        names = [e.name for e in self.events]
        return all(c in names for c in context_events)

    def __repr__(self):
        return f"Path({len(self.events)} events)"

    def __hash__(self):
        return hash(self.signature())

    def __eq__(self, other):
        if isinstance(other, Path):
            return self.signature() == other.signature()
        return False

    def __getstate__(self):
        return {slot: getattr(self, slot) for slot in self.__slots__}

    def __setstate__(self, state):
        payload = _pickle_state_dict(state)
        events = payload.get("events", ())
        if events is None:
            events = ()
        elif not isinstance(events, tuple):
            events = tuple(events)
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "_frozen", bool(payload.get("_frozen", False)))


class Experience:
    """
    IMMUTABLE experience after creation.
    
    Contains:
    - path: sequence of events (context + action + consequence)
    - intensity: emotional intensity of experience (not reward)
    - encoding_strength: strength of contextual encoding for replay/consolidation
    - timestamp: when this experience occurred
    - reinforcement_count: how many times this pattern was reinforced
    - activation_energy: current activation in hippocampus
    - stability: consolidation level to cortex
    """

    # Fixed fields replace a per-episode __dict__. Optional names stay unset
    # until a writer assigns them, so hasattr keeps its previous meaning.
    __slots__ = (
        "path",
        "consequence",
        "intensity",
        "encoding_strength",
        "reward",
        "causal_depth",
        "timestamp",
        "first_seen",
        "last_activated",
        "reinforcement_count",
        "activation_energy",
        "stability",
        "_recall_actions",
        "_sleep_consolidation_score",
        "_sleep_variance_gate",
        "acetylcholine_mean_snapshot",
        "acetylcholine_snapshot",
        "action_stability",
        "affect_gain_at_encoding",
        "arousal",
        "causality_score",
        "confirmation_count",
        "consolidated",
        "consolidated_revision",
        "consolidated_reward",
        "consolidation_probability",
        "consolidation_weight",
        "context_events",
        "decided_action",
        "emotional_salience",
        "emotional_trace",
        "encoded_at",
        "episode_id",
        "episode_step",
        "error_likelihood",
        "executed_action",
        "expectation_confidence_score",
        "expectation_stability_score",
        "expected_reward_mean",
        "expected_reward_var",
        "feedback_rating",
        "labile_contribution",
        "neuromodulator_snapshot",
        "next_experience",
        "novelty",
        "novelty_score",
        "outcome_revision",
        "overridden",
        "override_source",
        "prediction_shock_flag",
        "prediction_shock_score",
        "replay_action_id",
        "replay_count_sleep",
        "replay_importance",
        "replay_priority",
        "replay_salience",
        "shock_replay_boost",
        "stability_flag",
        "state_distance",
        "state_estimate_variance",
        "td_abs_snapshot",
        "td_applied_delta",
        "td_committed_reward",
        "td_error_snapshot",
        "td_history_snapshot",
        "td_mean_snapshot",
        "td_outcome_committed",
        "td_prior_value",
        "td_sign_snapshot",
        "td_variance_snapshot",
        "trajectory_id",
        "two_tier_replay_priority",
        "value_next_context_events",
        "value_next_state_snapshot",
        "value_state_key",
        "value_state_snapshot",
        "value_terminal",
        "warriner_word",
        "warriner_valence_norm",
        "warriner_arousal_norm",
        "warriner_dominance_norm",
        "warriner_seed_events",
    )

    def __init__(
        self,
        path: Path,
        consequence: Event = None,
        intensity: float = 1.0,
        reward: float = 0.0,
        encoding_strength: float = None,
    ):
        """
        Create immutable experience
        
        Args:
            path: Sequence of events (context + action)
            consequence: Result event (positive/negative/neutral)
            intensity: Emotional intensity (0-2), not used for optimization
        """
        self.path = path
        self.consequence = consequence  # Event with type CONSEQUENCE
        self.intensity = max(0.0, min(2.0, intensity))  # Clamp to [0, 2]
        if encoding_strength is None:
            self.encoding_strength = float(self.intensity)
        else:
            self.encoding_strength = max(0.0, min(3.0, float(encoding_strength)))
        # Preserve original reward if provided (may be in range -1..1)
        self.reward = reward

        # Spec-011A: causal depth marker for credit assignment.
        self.causal_depth = 0
        
        # Metadata
        self.timestamp = time.time()
        self.first_seen = self.timestamp
        self.last_activated = self.timestamp
        
        # Hippocampal state (can change, but experience stays same)
        self.reinforcement_count = 1
        self.activation_energy = 1.0  # Возбудимость в гиппокампе
        self.stability = 0.0  # Консолидация в кортекс
        
        # Freeze to prevent modification
        self._finalize()
    
    def _finalize(self):
        """Lock the immutable parts"""
        self.path.freeze()
        if self.consequence:
            self.consequence.freeze()
    
    def __repr__(self):
        return (f"Experience(path={self.path}, intensity={self.intensity}, "
                f"reinforcement={self.reinforcement_count}, "
                f"stability={self.stability:.2f})")
    
    def __hash__(self):
        return hash(self.path)

    def __getstate__(self):
        # Unset optional fields stay out of the payload, matching hasattr on main.
        state = {}
        for slot in self.__slots__:
            try:
                state[slot] = getattr(self, slot)
            except AttributeError:
                continue
        return state

    def __setstate__(self, state):
        """Restore a main ``__dict__`` or a slotted payload.

        Fields ``__init__`` always wrote get those defaults when a legacy blob
        omitted them. Optional markers stay unset so ``hasattr`` keeps the
        meaning it had before slots.
        """
        payload = _pickle_state_dict(state)
        for name in self.__slots__:
            if name in payload:
                object.__setattr__(self, name, payload[name])

        if not hasattr(self, "path") or self.path is None:
            object.__setattr__(self, "path", Path())
        if not hasattr(self, "consequence"):
            object.__setattr__(self, "consequence", None)
        if not hasattr(self, "intensity"):
            object.__setattr__(self, "intensity", 1.0)
        if not hasattr(self, "encoding_strength"):
            object.__setattr__(self, "encoding_strength", float(getattr(self, "intensity", 1.0)))
        if not hasattr(self, "reward"):
            object.__setattr__(self, "reward", 0.0)
        if not hasattr(self, "causal_depth"):
            object.__setattr__(self, "causal_depth", 0)
        if not hasattr(self, "timestamp"):
            object.__setattr__(self, "timestamp", 0.0)
        timestamp = float(getattr(self, "timestamp", 0.0) or 0.0)
        if not hasattr(self, "first_seen"):
            object.__setattr__(self, "first_seen", timestamp)
        if not hasattr(self, "last_activated"):
            object.__setattr__(self, "last_activated", timestamp)
        if not hasattr(self, "reinforcement_count"):
            object.__setattr__(self, "reinforcement_count", 1)
        if not hasattr(self, "activation_energy"):
            object.__setattr__(self, "activation_energy", 1.0)
        if not hasattr(self, "stability"):
            object.__setattr__(self, "stability", 0.0)
