"""
Action Intent and Realization - Adaptive mouth implementation.

According to the refactoring plan:
- NOWA chooses intention (ActionIntent), not text
- Form of expression is body experience, not behavior logic
- Realization of intent is adaptive, based on learned experiences
- No hardcoded if/else mappings of action to text
"""

import time
from typing import List, Dict, Any
from enum import Enum


class IntentType(Enum):
    """Types of behavioral intentions"""
    RESPOND_ABOUT_SELF = "respond_about_self"
    GREET_USER = "greet_user"
    REFUSE = "refuse"
    HELP_USER = "help_user"
    ASK_QUESTION = "ask_question"
    EXPRESS_CONFUSION = "express_confusion"
    ACKNOWLEDGE = "acknowledge"


class ActionIntent:
    """
    Represents WHAT the agent intends to do, not HOW to express it.
    
    This is what the selector chooses - pure intention without form.
    Form comes from RealizationExperience.
    """
    
    def __init__(self, intent_type: IntentType, parameters: Dict[str, Any] = None):
        """
        Create action intent
        
        Args:
            intent_type: Type of intention (RESPOND_ABOUT_SELF, GREET_USER, etc.)
            parameters: Optional context parameters (style, formality, etc.)
        """
        self.intent_type = intent_type
        self.parameters = parameters or {}
        self.timestamp = time.time()
    
    def __repr__(self):
        params_str = f", params={self.parameters}" if self.parameters else ""
        return f"ActionIntent({self.intent_type.value}{params_str})"
    
    def __hash__(self):
        return hash((self.intent_type, tuple(sorted(self.parameters.items()))))
    
    def __eq__(self, other):
        if isinstance(other, ActionIntent):
            return (self.intent_type == other.intent_type and 
                    self.parameters == other.parameters)
        return False


class RealizationExperience:
    """
    Represents ONE way of expressing an intention.
    
    Each realization is an independent experience:
    - Same intention can be expressed in different ways
    - Each way has its own intensity and activation energy
    - Different forms degrade during sleep at different rates
    
    Key principle: This is NOT generated text.
    This is learned form of expression stored as memory.
    """
    
    def __init__(self, 
                 intent_type: IntentType,
                 output: str,
                 context: List[str] = None,
                 intensity: float = 1.0,
                 parameters: Dict[str, Any] = None):
        """
        Create realization experience
        
        Args:
            intent_type: What intention this realizes
            output: The text/output for this realization
            context: Context in which this realization occurred
            intensity: Emotional intensity of this realization (0-2)
            parameters: Parameters used in realization
        """
        self.intent_type = intent_type
        self.output = output  # The actual output text
        self.context = context or []
        self.intensity = max(0.0, min(2.0, intensity))  # Clamp to [0, 2]
        self.parameters = parameters or {}
        
        # Metadata
        self.timestamp = time.time()
        self.first_seen = self.timestamp
        self.last_activated = self.timestamp
        
        # Memory state (can change)
        self.activation_count = 1
        self.activation_energy = 1.0  # How easily this realization activates
        self.stability = 0.0  # How stable/consolidated this is
        
    def activate(self):
        """Increase activation when this realization is used"""
        self.activation_count += 1
        self.last_activated = time.time()
        self.activation_energy = min(2.0, self.activation_energy + 0.1)
    
    def degrade(self, factor: float = 0.95):
        """
        Decrease activation during sleep consolidation.
        Rarely used forms fade away.
        """
        self.activation_energy *= factor
        self.activation_energy = max(0.1, self.activation_energy)
    
    def __repr__(self):
        return (f"RealizationExperience(intent={self.intent_type.value}, "
                f"output='{self.output[:30]}...', "
                f"activation={self.activation_energy:.2f})")
    
    def __hash__(self):
        return hash((self.intent_type, self.output))
    
    def __eq__(self, other):
        if isinstance(other, RealizationExperience):
            return (self.intent_type == other.intent_type and 
                    self.output == other.output)
        return False


class RealizationMemory:
    """
    Storage for all possible realization experiences.
    
    Tracks:
    - Multiple ways to express each intention
    - Activation levels
    - Stability/consolidation state
    """
    
    def __init__(self):
        """Initialize empty realization memory"""
        # Map: IntentType -> List[RealizationExperience]
        self.realizations: Dict[IntentType, List[RealizationExperience]] = {}
        
        # Keep all ever-seen for reference
        self.all_realizations: List[RealizationExperience] = []
    
    def store(self, realization: RealizationExperience):
        """Store a new realization experience"""
        intent_type = realization.intent_type
        
        if intent_type not in self.realizations:
            self.realizations[intent_type] = []
        
        # Check if we already have this exact realization
        existing = None
        for r in self.realizations[intent_type]:
            if r == realization:
                existing = r
                break
        
        if existing:
            # Reinforce existing realization
            existing.activate()
        else:
            # Add new realization
            self.realizations[intent_type].append(realization)
            self.all_realizations.append(realization)
    
    def get_realizations(self, intent_type: IntentType) -> List[RealizationExperience]:
        """Get all realizations for a given intent type"""
        return self.realizations.get(intent_type, [])
    
    def get_active_realizations(self, intent_type: IntentType) -> List[RealizationExperience]:
        """Get realizations that are currently active (activation_energy > threshold)"""
        threshold = 0.3
        realizations = self.get_realizations(intent_type)
        return [r for r in realizations if r.activation_energy > threshold]
    
    def degrade_all(self, factor: float = 0.95):
        """
        Degrade all realizations (used during sleep consolidation).
        Rarely-used forms fade away naturally.
        """
        for realization in self.all_realizations:
            realization.degrade(factor)
    
    def __repr__(self):
        count = sum(len(r) for r in self.realizations.values())
        return f"RealizationMemory({count} realizations)"
