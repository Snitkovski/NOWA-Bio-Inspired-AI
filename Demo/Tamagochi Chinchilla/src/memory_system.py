"""
Memory and Learning System for Tamagotchi Chinchilla
Implements behavioral learning, successful interaction tracking, and preference consolidation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime
import json
import numpy as np
from pathlib import Path
import logging


@dataclass
class MemoryEntry:
    """Records a single behavioral interaction and its outcome"""
    timestamp: float
    chain_name: str
    interaction_type: Optional[str]  # 'pet_head', 'pet_back', 'feed', 'play', 'scare'
    affect_before: Dict[str, float]
    affect_after: Dict[str, float]
    affect_delta: Dict[str, float]  # Change in affect values
    success: bool  # Whether outcome was positive for current emotional state
    reward: float  # Use -1.0 to +1.0 scale
    
    def to_dict(self):
        """Serialize to dictionary for JSON storage"""
        return {
            'timestamp': self.timestamp,
            'chain_name': self.chain_name,
            'interaction_type': self.interaction_type,
            'affect_before': self.affect_before,
            'affect_after': self.affect_after,
            'affect_delta': self.affect_delta,
            'success': self.success,
            'reward': self.reward,
        }


@dataclass
class BehaviorPreference:
    """Stores learned preference weights for behavioral chains"""
    chain_name: str
    success_count: int = 0
    total_attempts: int = 0
    average_reward: float = 0.0
    last_used: float = 0.0
    recent_success_rate: float = 0.5  # For recent interactions
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate, handle division by zero"""
        return self.success_count / max(1, self.total_attempts)
    
    @property
    def preference_weight(self) -> float:
        """Calculate preference weight: higher = more learned preference"""
        # Combine success rate, recent success, and attempt frequency
        # Weight recent successes more heavily (recency bias)
        base_weight = self.success_rate * 0.6 + self.recent_success_rate * 0.4
        # Dampen preferences for frequently-used chains (novelty bonus)
        attempt_factor = 1.0 / (1.0 + self.total_attempts * 0.1)
        return base_weight * (0.8 + attempt_factor * 0.2)
    
    def to_dict(self):
        """Serialize to dictionary"""
        return {
            'chain_name': self.chain_name,
            'success_count': self.success_count,
            'total_attempts': self.total_attempts,
            'average_reward': self.average_reward,
            'success_rate': self.success_rate,
            'preference_weight': self.preference_weight,
        }


class MemorySystem:
    """
    Tracks behavioral interactions and learns from outcomes
    Consolidates learning during rest periods
    Provides weighted chain selection based on learned preferences
    """
    
    def __init__(self, memory_file: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize memory system
        
        Args:
            memory_file: Path to save/load memory data
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.memory_file = memory_file
        
        # Memory storage
        self.entries: List[MemoryEntry] = []
        self.chain_preferences: Dict[str, BehaviorPreference] = {}
        self.interaction_preferences: Dict[str, BehaviorPreference] = {}
        
        # Tracking for consolidation
        self.last_consolidation_time: float = 0.0
        self.memory_capacity: int = 1000  # Max entries to store
        self.consolidation_interval: float = 300.0  # Consolidate every 5 minutes
        
        # Load existing memory if available
        if memory_file and memory_file.exists():
            self._load_memory()
    
    def record_interaction(
        self,
        chain_name: str,
        affect_before: Dict[str, float],
        affect_after: Dict[str, float],
        interaction_type: Optional[str] = None,
        current_time: float = 0.0,
    ) -> MemoryEntry:
        """
        Record a behavioral interaction and calculate reward
        
        Args:
            chain_name: Name of executed chain (e.g., 'eating', 'grooming')
            affect_before: Affect state before chain execution
            affect_after: Affect state after chain execution
            interaction_type: Type of user interaction if applicable
            current_time: Simulation time stamp
        
        Returns:
            MemoryEntry with success/reward assessment
        """
        # Calculate affect delta
        affect_delta = {}
        for key in affect_before:
            affect_delta[key] = affect_after.get(key, 0.0) - affect_before.get(key, 0.0)
        
        # Assess success: reward improvements in critical affects
        # Positive = moving toward neutral/positive values, away from extremes
        reward = self._calculate_reward(affect_before, affect_after, chain_name)
        success = reward > 0.0
        
        # Create memory entry
        entry = MemoryEntry(
            timestamp=current_time,
            chain_name=chain_name,
            interaction_type=interaction_type,
            affect_before=affect_before.copy(),
            affect_after=affect_after.copy(),
            affect_delta=affect_delta,
            success=success,
            reward=reward,
        )
        
        # Store in memory
        self.entries.append(entry)
        
        # Update preference weights
        self._update_preferences(entry)
        
        # Trim memory if over capacity
        if len(self.entries) > self.memory_capacity:
            self.entries = self.entries[-self.memory_capacity:]
        
        self.logger.debug(
            f"Memory: chain={chain_name}, reward={reward:.2f}, "
            f"success={success}, memory_size={len(self.entries)}"
        )
        
        return entry
    
    def _calculate_reward(
        self,
        affect_before: Dict[str, float],
        affect_after: Dict[str, float],
        chain_name: str,
    ) -> float:
        """
        Calculate reward for interaction based on affect changes
        
        Reward favors:
        - Moving fearful/sad emotions toward neutral
        - Maintaining happy/calm emotions
        - Chain-specific benefits (e.g., eating reduces hunger)
        
        Args:
            affect_before: Initial affect state
            affect_after: Final affect state
            chain_name: Current behavioral chain
        
        Returns:
            Reward value in [-1.0, 1.0] range
        """
        reward = 0.0

        # Вычислить производные значения из правильных ключей
        hunger_before   = affect_before.get('hunger', 0.0)
        hunger_after    = affect_after.get('hunger', 0.0)
        tiredness_before = affect_before.get('tiredness', 0.0)
        tiredness_after  = affect_after.get('tiredness', 0.0)
        boredom_before  = affect_before.get('boredom', 0.0)
        boredom_after   = affect_after.get('boredom', 0.0)

        valence_before  = affect_before.get('valence', 0.0)
        valence_after   = affect_after.get('valence', 0.0)
        stress_before   = affect_before.get('stress', 0.0)
        stress_after    = affect_after.get('stress', 0.0)

        # Chain-specific rewards
        if chain_name in ('eating', 'eating_and_grooming'):
            if hunger_after < hunger_before:
                reward += 0.3

        elif chain_name in ('bedtime_routine', 'sleeping'):
            if tiredness_after < tiredness_before:
                reward += 0.3

        elif chain_name in ('play', 'activity_burst', 'exploration', 'hyperactivity'):
            if boredom_after < boredom_before:
                reward += 0.25
            if valence_after > valence_before:
                reward += 0.15

        elif chain_name in ('full_grooming', 'dust_bathing'):
            if stress_after < stress_before:
                reward += 0.2

        # Общее: снижение стресса всегда хорошо
        if stress_after < stress_before:
            reward += (stress_before - stress_after) * 0.1

        # Общее: рост позитивного настроения
        if valence_after > 0.3:
            reward += valence_after * 0.05

        # Патологические цепочки — штраф
        if chain_name == 'chronic_stress':
            reward -= 0.4

        return max(-1.0, min(1.0, reward))
    
    def _update_preferences(self, entry: MemoryEntry):
        """
        Update chain and interaction preferences based on memory entry
        
        Args:
            entry: MemoryEntry to learn from
        """
        # Update chain preference
        if entry.chain_name not in self.chain_preferences:
            self.chain_preferences[entry.chain_name] = BehaviorPreference(
                chain_name=entry.chain_name
            )
        
        pref = self.chain_preferences[entry.chain_name]
        pref.total_attempts += 1
        if entry.success:
            pref.success_count += 1
        pref.average_reward += (entry.reward - pref.average_reward) / pref.total_attempts
        
        # Update interaction preference if applicable
        if entry.interaction_type:
            if entry.interaction_type not in self.interaction_preferences:
                self.interaction_preferences[entry.interaction_type] = BehaviorPreference(
                    chain_name=entry.interaction_type
                )
            
            int_pref = self.interaction_preferences[entry.interaction_type]
            int_pref.total_attempts += 1
            if entry.success:
                int_pref.success_count += 1
            int_pref.average_reward += (entry.reward - int_pref.average_reward) / int_pref.total_attempts
    
    def get_chain_weight(self, chain_name: str) -> float:
        """
        Get learned preference weight for a chain
        Higher weight = more learned preference for this chain
        
        Args:
            chain_name: Name of behavioral chain
        
        Returns:
            Weight value, default 1.0 for unknown chains
        """
        if chain_name in self.chain_preferences:
            pref = self.chain_preferences[chain_name]
            # Base weight 1.0 + preference adjustment (-0.5 to +0.5)
            return 1.0 + (pref.preference_weight - 0.5)
        return 1.0
    
    def get_chain_weights(self, chains: List[str]) -> Dict[str, float]:
        """
        Get learned preference weights for multiple chains
        
        Args:
            chains: List of chain names
        
        Returns:
            Dictionary mapping chain names to weight values
        """
        weights = {}
        for chain in chains:
            weights[chain] = self.get_chain_weight(chain)
        return weights
    
    def consolidate_memory(self, current_time: float):
        """
        Consolidate learning during rest periods
        Updates recency biases, strengthens successful patterns
        
        Args:
            current_time: Current simulation time
        """
        if current_time - self.last_consolidation_time < self.consolidation_interval:
            return
        
        self.logger.info("Consolidating memory...")
        
        # Analyze recent entries (last 100 interactions)
        recent_entries = self.entries[-100:] if len(self.entries) > 100 else self.entries
        
        # Update recent success rates
        for chain_name, pref in self.chain_preferences.items():
            recent_successes = sum(
                1 for e in recent_entries
                if e.chain_name == chain_name and e.success
            )
            recent_attempts = sum(
                1 for e in recent_entries
                if e.chain_name == chain_name
            )
            
            if recent_attempts > 0:
                pref.recent_success_rate = recent_successes / recent_attempts
        
        # Log consolidation results
        top_chains = sorted(
            self.chain_preferences.items(),
            key=lambda x: x[1].preference_weight,
            reverse=True
        )[:3]
        
        self.logger.info(
            f"Top learned chains: {[c[0] for c in top_chains]}"
        )
        
        self.last_consolidation_time = current_time
    
    def get_memory_summary(self) -> Dict:
        """
        Get summary of learned preferences and memory statistics
        
        Returns:
            Dictionary with memory statistics and preferences
        """
        return {
            'total_entries': len(self.entries),
            'unique_chains': len(self.chain_preferences),
            'unique_interactions': len(self.interaction_preferences),
            'average_reward': np.mean([e.reward for e in self.entries]) if self.entries else 0.0,
            'success_rate': sum(1 for e in self.entries if e.success) / max(1, len(self.entries)),
            'chain_preferences': {
                name: pref.to_dict()
                for name, pref in self.chain_preferences.items()
            },
        }
    
    def save_memory(self, file_path: Optional[Path] = None):
        """
        Save memory to JSON file for persistence
        
        Args:
            file_path: Path to save to, uses self.memory_file if not provided
        """
        path = file_path or self.memory_file
        if not path:
            return
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'entries': [e.to_dict() for e in self.entries[-500:]],  # Keep last 500
            'chain_preferences': {
                name: pref.to_dict()
                for name, pref in self.chain_preferences.items()
            },
            'interaction_preferences': {
                name: pref.to_dict()
                for name, pref in self.interaction_preferences.items()
            },
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Memory saved to {path}")
    
    def _load_memory(self):
        """Load memory from file if it exists"""
        if not self.memory_file or not self.memory_file.exists():
            return
        
        try:
            with open(self.memory_file, 'r') as f:
                data = json.load(f)
            
            # Reconstruct chain preferences
            for name, pref_data in data.get('chain_preferences', {}).items():
                pref = BehaviorPreference(
                    chain_name=name,
                    success_count=pref_data.get('success_count', 0),
                    total_attempts=pref_data.get('total_attempts', 0),
                    average_reward=pref_data.get('average_reward', 0.0),
                    recent_success_rate=pref_data.get('recent_success_rate', 0.5),
                )
                self.chain_preferences[name] = pref
            
            self.logger.info(f"Loaded memory: {len(self.chain_preferences)} chain preferences")
        
        except Exception as e:
            self.logger.warning(f"Failed to load memory: {e}")
