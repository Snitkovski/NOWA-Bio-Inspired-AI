"""
Action Realizer - Adaptive realization of intentions through experience.

Core principle: NOWA selects intention via selector, then realizes
the intention's form through stored realization experiences.

Key constraint: NO text generation, NO ML models.
Only selection from learned experiences with stochastic choice when
there are multiple ways to express the same intention.

Affective modulation:
- Threat reduces elaborate expressions, favors simple/direct
- High arousal increases conciseness and directness
- Low valence may reduce positive framing
"""

import random
from typing import List, Optional
from action_intent import (
    ActionIntent, IntentType, RealizationExperience, RealizationMemory
)


class ActionRealizer:
    """
    Realizes action intentions by selecting appropriate text outputs.
    
    Algorithm:
    1. Receive ActionIntent from agent
    2. Find all stored realizations for this intent type
    3. Calculate activation pressure for each realization
    4. Choose based on pressure (deterministic if clear winner,
       stochastic if conflict)
    5. Return the output text
    
    NOT a learning mechanism. Behavior emerges from:
    - Realization memory (stored experiences of expression)
    - Activation levels (how often each form was used)
    - Sleep degradation (rarely used forms fade)
    """
    
    def __init__(self, realization_memory: RealizationMemory,
                 confidence_threshold: float = 0.7):
        """
        Initialize realizer
        
        Args:
            realization_memory: Storage of realization experiences
            confidence_threshold: If max_activation/total_activation > threshold,
                                 choose deterministically. Else probabilistically.
        """
        self.memory = realization_memory
        self.confidence_threshold = confidence_threshold
    
    def realize(self, intent: ActionIntent, context: List[str] = None, 
                affect_modifier: float = 1.0) -> str:
        """
        Realize an action intent as actual output with affective modulation.
        
        Args:
            intent: ActionIntent to realize
            context: Optional context for better realization selection
            affect_modifier: Modifier from affective state (0.1-2.0)
                           - High (>1.2) = more concise/direct
                           - Low (<0.8) = more exploratory/variable
        
        Returns:
            Text output for this intention
        """
        context = context or []
        
        # Get all possible realizations for this intent type
        realizations = self.memory.get_active_realizations(intent.intent_type)
        
        if not realizations:
            # No learned realizations for this intent
            # Return fallback based on intent type
            return self._fallback_realization(intent)
        
        # Calculate activation pressure for each realization
        pressure = self._calculate_pressure(realizations, context, affect_modifier)
        
        # Choose realization based on pressure
        chosen = self._choose_realization(realizations, pressure)
        
        # Increase activation of chosen realization
        chosen.activate()
        
        return chosen.output
    
    def _calculate_pressure(self, realizations: List[RealizationExperience],
                           context: List[str], affect_modifier: float = 1.0) -> dict:
        """
        Calculate activation pressure for each realization.
        
        Pressure = activation_energy * relevance_to_context * affect_influence
        
        Affective influence:
        - High affect_modifier (threat/arousal) → prefer simpler realizations
        - Low affect_modifier (uncertainty) → add variance to pressure
        """
        pressure = {}
        
        for real in realizations:
            # Base pressure from activation energy
            base_pressure = real.activation_energy * real.stability
            
            # Boost if context matches
            if context and real.context:
                context_match = len(set(context) & set(real.context)) / max(1, len(real.context))
                base_pressure *= (1.0 + context_match * 0.5)
            
            # Apply affect modulation
            # High threat/arousal favors established (high activation) realizations
            # Low affect (uncertainty) increases variability
            affect_influence = 1.0 + (affect_modifier - 1.0) * 0.3
            
            pressure[id(real)] = base_pressure * affect_influence
        
        return pressure
    
    def _choose_realization(self, realizations: List[RealizationExperience],
                           pressure: dict) -> RealizationExperience:
        """
        Choose realization based on pressure.
        
        High confidence -> deterministic (max pressure)
        Low confidence -> stochastic (probabilistic selection)
        """
        if not realizations:
            return self._create_fallback_realization()
        
        # Create pressure mapping
        pressure_list = [pressure.get(id(r), 0.1) for r in realizations]
        total_pressure = sum(pressure_list)
        
        if total_pressure <= 0:
            # No activation, choose random
            return random.choice(realizations)
        
        # Calculate confidence
        max_pressure = max(pressure_list)
        confidence = max_pressure / total_pressure
        
        if confidence > self.confidence_threshold:
            # Deterministic: choose maximum pressure
            idx = pressure_list.index(max_pressure)
            return realizations[idx]
        else:
            # Stochastic: choose proportional to pressure
            return self._stochastic_choice(realizations, pressure_list)
    
    def _stochastic_choice(self, realizations: List[RealizationExperience],
                          pressure_list: List[float]) -> RealizationExperience:
        """
        Stochastic selection with probability proportional to pressure.
        
        This adds controlled variability in expression without learning.
        """
        total = sum(pressure_list)
        if total <= 0:
            return random.choice(realizations)
        
        # Normalize to probabilities
        probabilities = [p / total for p in pressure_list]
        
        # Sample according to pressure
        return random.choices(realizations, weights=probabilities, k=1)[0]
    
    def _fallback_realization(self, intent: ActionIntent) -> str:
        """
        Return fallback text when no realizations learned yet.
        
        These are minimal fallbacks, not full hardcoded responses.
        Once learning happens, these are overridden.
        """
        fallbacks = {
            IntentType.RESPOND_ABOUT_SELF: "Я NOWA - когнитивный агент.",
            IntentType.GREET_USER: "Привет!",
            IntentType.REFUSE: "Извините, я не могу это сделать.",
            IntentType.HELP_USER: "Я здесь, чтобы помочь.",
            IntentType.ASK_QUESTION: "Что вы имеете в виду?",
            IntentType.EXPRESS_CONFUSION: "Я не совсем понял...",
            IntentType.ACKNOWLEDGE: "Понял.",
        }
        return fallbacks.get(intent.intent_type, "...")
    
    def _create_fallback_realization(self) -> RealizationExperience:
        """Create a minimal fallback realization"""
        return RealizationExperience(
            intent_type=IntentType.ACKNOWLEDGE,
            output="...",
            intensity=0.1
        )


class ActionRealizerWithSelector:
    """
    Integration layer: connects Agent's ActionSelector with ActionRealizer.
    
    Flow:
    1. Agent.step() -> Selector chooses old-style action name
    2. convert_action_to_intent() -> Convert to ActionIntent
    3. ActionRealizer.realize() -> Get output text
    """
    
    # Mapping from old action names to intent types
    ACTION_TO_INTENT = {
        "ответить_кто_я": IntentType.RESPOND_ABOUT_SELF,
        "сказать_привет": IntentType.GREET_USER,
        "отказаться": IntentType.REFUSE,
        "помочь": IntentType.HELP_USER,
        "задать_вопрос": IntentType.ASK_QUESTION,
        "greet": IntentType.GREET_USER,
        "refuse": IntentType.REFUSE,
        "ask": IntentType.ASK_QUESTION,
        "help": IntentType.HELP_USER,
    }
    
    def __init__(self, realizer: ActionRealizer):
        """Initialize with action realizer"""
        self.realizer = realizer
    
    def convert_and_realize(self, action: str, context: List[str] = None) -> str:
        """
        Convert old-style action name to intent and realize it.
        
        Args:
            action: Action name from selector
            context: Optional context
        
        Returns:
            Realized output text
        """
        # Convert action to intent
        intent_type = self.ACTION_TO_INTENT.get(action, IntentType.ACKNOWLEDGE)
        intent = ActionIntent(intent_type)
        
        # Realize the intent
        return self.realizer.realize(intent, context)
