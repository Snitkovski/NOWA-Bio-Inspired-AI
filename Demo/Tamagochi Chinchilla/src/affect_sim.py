"""
Simple Affect/Mood System - simulates emotional state for demo.
Used for contextual chain selection without full NOWA integration.
"""

import logging
import time
from typing import Dict, Any
import math

# ============================================================================
# AFFECT SIMULATION
# ============================================================================

class SimpleAffect:
    """
    Simplified 8-dimensional affect space for demo.
    Based on spec Section 5, but with deterministic transitions instead of learningFull dimensions: valence, arousal, dominance, stress, trust, curiosity, stability, att attachment
    """
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize affect state."""
        self.logger = logger or logging.getLogger(__name__)
        
        # 8-dimensional affect state (all start at neutral ~0.0)
        self.state = {
            "valence": 0.3,      # Positive mood
            "arousal": 0.5,      # Medium activity
            "dominance": 0.4,    # Balanced confidence
            "stress": 0.0,       # No stress
            "trust": 0.5,        # Neutral trust
            "curiosity": 0.6,    # Interested
            "stability": 0.5,    # Balanced
            "attachment": 0.3,   # Less attached initially
        }
        
        # Circadian rhythm
        self.circadian_phase = 0.0  # 0-1, wraps daily
        self.cycle_period = 1440.0  # 24 hours in ticks (for demo: seconds)
        self._start_time = time.time()
    
    def update(self, dt: float = 1.0, action_reward: float = 0.0) -> None:
        """
        Update affect state based on time and action rewards.
        
        Args:
            dt: Delta time in seconds
            action_reward: Reward from action execution (-1 to +1)
        """
        # Update circadian phase
        elapsed = time.time() - self._start_time
        self.circadian_phase = (elapsed % self.cycle_period) / self.cycle_period
        
        # Time-based modulation
        self._apply_circadian_modulation()
        
        # Reward-based changes
        if action_reward != 0:
            self._apply_reward(action_reward)
        
        # Natural decay toward neutral
        self._apply_decay()
        
        # Clamp values to [-1, 1]
        for key in self.state:
            self.state[key] = max(-1.0, min(1.0, self.state[key]))
    
    def _apply_circadian_modulation(self) -> None:
        """Apply time-of-day modulation using sin curve."""
        # Arousal peaks during day, low at night
        circadian_arousal = math.sin(self.circadian_phase * 2 * math.pi)
        self.state["arousal"] = self.state["arousal"] * 0.8 + circadian_arousal * 0.2
        
        # Sleep pressure increases at night
        sleep_pressure = math.sin(self.circadian_phase * 2 * math.pi - math.pi / 2)
        
        # Slightly different mood in evening
        if 0.6 < self.circadian_phase < 1.0:  # Evening
            self.state["valence"] -= 0.05
        elif 0.3 < self.circadian_phase < 0.6:  # Day
            self.state["valence"] += 0.05
    
    def _apply_reward(self, reward: float) -> None:
        """Apply reward/punishment to affect dimensions."""
        # Positive reward increases valence and reduces stress
        if reward > 0:
            self.state["valence"] += reward * 0.2
            self.state["stress"] -= reward * 0.15
            self.state["curiosity"] += reward * 0.1
        
        # Negative reward (punishment) increases stress
        else:
            self.state["stress"] -= reward * 0.2  # negative of negative = increase
            self.state["valence"] += reward * 0.15
    
    def _apply_decay(self) -> None:
        """Natural decay toward neutral values."""
        for key in self.state:
            # Slower decay for stable dimensions
            decay = 0.98 if key in ["stability", "attachment"] else 0.99
            self.state[key] *= decay
    
    def get_chain_context(self) -> Dict[str, Any]:
        """
        Get context dict for behavioral chain selection.
        
        Returns:
            Dict with affect-influenced context
        """
        return {
            "circadian_phase": self.circadian_phase,
            "is_daytime": 0.3 < self.circadian_phase < 0.8,
            "is_nighttime": self.circadian_phase > 0.7 or self.circadian_phase < 0.3,
            "affect": self.state.copy(),
            "mood": self._compute_mood_label(),
            "activity_level": self.state["arousal"],
            "stress_level": self.state["stress"],
        }
    
    def _compute_mood_label(self) -> str:
        """Compute a text label for current mood."""
        val = self.state["valence"]
        stress = self.state["stress"]
        
        if stress > 0.6:
            return "anxious"
        elif val > 0.6:
            return "happy"
        elif val < -0.3:
            return "sad"
        elif self.state["curiosity"] > 0.7:
            return "curious"
        else:
            return "neutral"
    
    def get_state(self) -> Dict[str, Any]:
        """Get current affect state."""
        return self.state.copy()
    
    def _phase_to_time_label(self) -> str:
        """Convert circadian phase to human-readable time."""
        hour = int(self.circadian_phase * 24)
        return f"{hour:02d}:00"
