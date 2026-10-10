"""
Action Realizer - translates action selection into pygame output.
Takes action pressure from BG and produces rendering commands.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import random

from config import (
    ACTION_LIBRARY, ActionMetadata, ActionLayer, Position,
    BEHAVIORAL_CHAINS
)
from dataset_loader import ActionRealization, DatasetLoader, get_fallback_realization


@dataclass
class ActionSelection:
    """Result of action selection."""
    action_id: str
    pressure: float  # Selection pressure from BG
    layer: ActionLayer
    related_chain: Optional[str] = None  # If part of behavioral chain


class ActionRealizer:
    """
    Realizes action selections into pygame rendering commands.
    
    Responsibilities:
    1. Select among competing action realizations
    2. Handle behavioral chains
    3. Produce pygame output format
    4. Track action context (previous action, position, etc.)
    """
    
    # Duration values in config are already in seconds — no scaling needed.
    # The original TIME_SCALE=40 was a leftover from a tick-based system and
    # caused actions to run 40× longer than intended (eat_pellets → 400–1200s).
    TIME_SCALE = 1.0
    
    def __init__(self, dataset_loader: DatasetLoader, logger: Optional[logging.Logger] = None):
        """
        Initialize ActionRealizer.
        
        Args:
            dataset_loader: Loaded dataset with realizations
            logger: Optional logger
        """
        self.dataset = dataset_loader
        self.logger = logger or logging.getLogger(__name__)
        self.previous_action: Optional[str] = None
        self.previous_position: str = "floor"
        self.chain_progress: Dict[str, int] = {}  # chain_name -> current_step
        self.chain_execution: Optional[str] = None  # currently executing chain
        self.action_history: List[str] = []  # last N actions
        self.max_history = 20
        self.logger.info("ActionRealizer initialized")
    
    def realize_action(self, action_id: str, pressure: float = 1.0,
                      context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Realize an action into pygame command.
        
        Args:
            action_id: Action to realize (from ACTION_LIBRARY)
            pressure: Selection pressure (0-1, higher = more likely context match)
            context: Optional context (affect state, current position, etc.)
        
        Returns:
            Pygame command dict or None if action cannot be realized
        """
        context = context or {}
        
        # Get action metadata
        action_meta = ACTION_LIBRARY.get(action_id)
        if not action_meta:
            self.logger.warning(f"Unknown action: {action_id}")
            return None
        
        # Select realization from dataset
        realization = self._select_realization(action_id, pressure, context)
        if not realization:
            self.logger.warning(f"No realization found for {action_id}")
            realization = get_fallback_realization(action_id)
        
        # Convert to pygame command
        command = self._build_pygame_command(action_id, realization, action_meta, context)
        
        # Update history
        self._update_history(action_id, command)
        
        return command
    
    def _select_realization(self, action_id: str, pressure: float,
                           context: Dict[str, Any]) -> Optional[ActionRealization]:
        """
        Select best realization from pool based on:
        1. Context matching (current position, previous action, etc.)
        2. Pressure (higher pressure = more contextual matching)
        3. Randomness (add variance)
        
        Args:
            action_id: Action to select realization for
            pressure: Selection pressure (contextual sensitivity)
            context: Current context dict
        
        Returns:
            Selected realization or None
        """
        pool = self.dataset.get_realization_pool(action_id)
        if not pool or pool.count() == 0:
            return None
        
        if pool.count() == 1:
            return pool.realizations[0]
        
        # Score realizations based on context
        realizations_with_scores = []
        for realization in pool.realizations:
            score = self._score_realization(realization, pressure, context)
            realizations_with_scores.append((realization, score))
        
        # Sort by score and select probabilistically
        realizations_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Use softmax-like selection: higher pressure = more likely to select top-scored
        if pressure > 0.8:
            # High pressure: pick top realization
            selected = realizations_with_scores[0][0]
        else:
            # Lower pressure: add randomness
            total_score = sum(score for _, score in realizations_with_scores)
            if total_score > 0:
                probabilities = [score / total_score for _, score in realizations_with_scores]
                selected = random.choices(
                    [r for r, _ in realizations_with_scores],
                    weights=probabilities,
                    k=1
                )[0]
            else:
                selected = random.choice(pool.realizations)
        
        return selected
    
    def _score_realization(self, realization: ActionRealization, pressure: float,
                          context: Dict[str, Any]) -> float:
        """
        Score a realization based on context matching.
        
        Factors:
        - Position continuity (favor same/nearby position)
        - Action flow (some actions naturally follow others)
        - Behavioral chain (within chain, favor sequential)
        - Temporal factors (time-of-day, wakefulness state)
        
        Returns:
            Score (0-1)
        """
        score = 0.5  # Base score
        
        # Position continuity
        current_pos = context.get("current_position", "floor")
        if realization.position:
            if realization.position == current_pos:
                score += 0.3  # Strong bonus for same position
            elif self._are_nearby(realization.position, str(current_pos)):
                score += 0.15  # Weak bonus for nearby position
        
        # Action flow - favor natural sequences
        prev_action = context.get("previous_action")
        if prev_action:
            flow_score = self._action_flow_score(prev_action, realization.action_id)
            score += flow_score * 0.2
        
        # Behavioral chain bonus
        chain = context.get("chain_context")
        if chain and chain in BEHAVIORAL_CHAINS:
            chain_actions = BEHAVIORAL_CHAINS[chain]
            if realization.action_id in chain_actions:
                chain_idx = chain_actions.index(realization.action_id)
                # Favor actions later in chain if we're executing it
                score += (chain_idx / len(chain_actions)) * 0.2
        
        # Clamp score to [0, 1]
        return min(1.0, max(0.0, score))
    
    def _action_flow_score(self, prev_action: str, next_action: str) -> float:
        """Get natural flow score between two actions."""
        # Define natural transitions
        natural_flows = {
            "sleep_house": ["stretch_body", "yawn", "groom_face"],
            "eat_pellets": ["drink_water", "groom_face"],
            "run_wheel": ["rest_loaf", "drink_water"],
            "explore_corner": ["observe_room", "sniff_corners"],
            "hide_house": ["doze_shelf", "stretch_body", "observe_room"],
        }
        
        if prev_action in natural_flows:
            if next_action in natural_flows[prev_action]:
                return 0.8
            elif next_action.startswith(next_action.split("_")[0]):
                return 0.4  # Same category bonus
        
        return 0.0
    
    def _are_nearby(self, pos1: str, pos2: str) -> bool:
        """Check if two positions are nearby."""
        adjacent = {
            "floor": ["house", "bowl_pellets", "wheel", "toy"],
            "wheel": ["floor", "shelf_lower"],
            "shelf_lower": ["floor", "shelf_mid", "wheel"],
            "shelf_mid": ["shelf_lower", "shelf_upper"],
            "house": ["floor", "dustbath", "litter"],
            "corner": ["floor", "litter"],
        }
        
        return pos2 in adjacent.get(pos1, [])
    
    def _build_pygame_command(self, action_id: str, realization: ActionRealization,
                             action_meta: ActionMetadata,
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """Build pygame command from realization and metadata."""
        # Determine actual duration
        duration_min = int(action_meta.duration_min * self.TIME_SCALE)
        duration_max = int(action_meta.duration_max * self.TIME_SCALE)
        duration = (duration_min, duration_max)
        
        # Determine position
        position = realization.position or str(action_meta.default_position.value)
        
        # Get subtitle
        subtitle = action_meta.subtitle_ru or action_id
        
        command = {
            "action_id": action_id,
            "anim": realization.anim,
            "sfx": realization.sfx,
            "position": position,
            "duration": list(duration),
            "subtitle": subtitle,
            "loop": action_meta.is_loop,
            "layer": action_meta.layer.value,
            "pressure": context.get("pressure", 1.0),
        }
        
        return command
    
    def _update_history(self, action_id: str, command: Dict[str, Any]) -> None:
        """Update action history."""
        self.action_history.append(action_id)
        if len(self.action_history) > self.max_history:
            self.action_history.pop(0)
        self.previous_action = action_id
        self.previous_position = command.get("position", "floor")
    
    def try_behavioral_chain(self, chain_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Try to realize a behavioral chain.
        
        Returns:
            List of pygame commands for each action in chain, or None if can't execute
        """
        if chain_name not in BEHAVIORAL_CHAINS:
            self.logger.warning(f"Unknown chain: {chain_name}")
            return None
        
        chain_actions = BEHAVIORAL_CHAINS[chain_name]
        commands = []
        
        for action_id in chain_actions:
            command = self.realize_action(
                action_id,
                pressure=0.9,  # High pressure for chain execution
                context={"chain_context": chain_name}
            )
            if command:
                commands.append(command)
        
        if commands:
            self.chain_execution = chain_name
            self.chain_progress[chain_name] = len(chain_actions)
            return commands
        
        return None
    
    def get_action_stats(self) -> Dict[str, Any]:
        """Get statistics about action realization."""
        return {
            "previous_action": self.previous_action,
            "previous_position": self.previous_position,
            "action_history_length": len(self.action_history),
            "active_chain": self.chain_execution,
            "num_loaded_actions": len(self.dataset.realizations),
            "avg_realizations_per_action": (
                sum(pool.count() for pool in self.dataset.realizations.values())
                / len(self.dataset.realizations)
                if self.dataset.realizations else 0
            ),
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_action_realizer(demo_dir: str, logger: Optional[logging.Logger] = None) -> Optional[ActionRealizer]:
    """
    Factory function to create ActionRealizer with loaded datasets.
    
    Args:
        demo_dir: Path to Demo/Tamagochi Chinchilla directory (or dataset directory)
        logger: Optional logger for internal components
    
    Returns:
        ActionRealizer instance or None if dataset loading fails
    """
    from pathlib import Path
    # If demo_dir already points to a Datasets folder, use it directly;
    # otherwise append "Datasets" so callers can pass either path.
    base = Path(demo_dir)
    if (base / "Datasets").exists():
        dataset_dir = base / "Datasets"
    else:
        dataset_dir = base

    if not dataset_dir.exists():
        if logger:
            logger.error(f"Dataset directory not found: {dataset_dir}")
        else:
            logging.error(f"Dataset directory not found: {dataset_dir}")
        return None

    loader = DatasetLoader(dataset_dir, logger)
    loader.load_all()

    stats = loader.get_stats()
    if logger:
        logger.info(f"Datasets loaded: {stats}")
    else:
        logging.info(f"Datasets loaded: {stats}")

    return ActionRealizer(loader, logger)

# Note: earlier duplicate definition removed by replacing both definitions above.
