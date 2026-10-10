import time
from typing import List, Tuple
from enum import Enum


class EventType(Enum):
    """Types of events in experience"""
    CONTEXT = "context"      # Внешний контекст
    ACTION = "action"        # Выбранное действие (now IntentType)
    REALIZATION = "realization"  # Output/expression of the action
    CONSEQUENCE = "consequence"  # Результат действия


class Event:
    """Immutable event with timestamp and magnitude"""
    
    def __init__(self, name: str, event_type: EventType = EventType.CONTEXT, 
                 magnitude: float = 1.0, timestamp: float = None):
        self.name = name
        self.event_type = event_type
        self.magnitude = magnitude  # Интенсивность события
        self.timestamp = timestamp or time.time()
        self._frozen = False  # Флаг неизменяемости

    def freeze(self):
        """Сделать событие неизменяемым"""
        self._frozen = True

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
