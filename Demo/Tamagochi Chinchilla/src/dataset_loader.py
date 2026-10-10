"""
Dataset loading for Chinchilla Agent.
Loads action realizations, sprites, and SFX from JSON configuration files.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

# ============================================================================
# ACTION REALIZATION STRUCTURES
# ============================================================================

@dataclass
class ActionRealization:
    """A single realization of an action with animation, sound, position, etc."""
    action_id: str
    anim: str  # Animation sprite to load
    sfx: Optional[str] = None  # Sound effect to play
    position: Optional[str] = None  # Target position in enclosure
    duration: tuple = field(default_factory=lambda: (10, 30))  # (min, max)
    subtitle_ru: str = ""
    loop: bool = True
    layer: str = "action"  # action | postural | micro
    
    def to_pygame_command(self) -> Dict[str, Any]:
        """Convert to pygame rendering command."""
        return {
            "anim": self.anim,
            "sfx": self.sfx,
            "position": self.position,
            "duration": list(self.duration),
            "subtitle": self.subtitle_ru,
            "loop": self.loop,
            "layer": self.layer,
        }


@dataclass
class ActionRealizationPool:
    """Pool of possible realizations for a single action."""
    action_id: str
    realizations: List[ActionRealization] = field(default_factory=list)
    
    def add_realization(self, realization: ActionRealization) -> None:
        """Add a realization to the pool."""
        self.realizations.append(realization)
    
    def get_random(self) -> Optional[ActionRealization]:
        """Get random realization. In full impl, would consider context weights."""
        if not self.realizations:
            return None
        import random
        return random.choice(self.realizations)
    
    def count(self) -> int:
        """Number of realizations for this action."""
        return len(self.realizations)


# ============================================================================
# DATASET LOADER
# ============================================================================

class DatasetLoader:
    """Loads action realizations from JSON dataset files."""
    
    def __init__(self, dataset_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Initialize dataset loader.
        
        Args:
            dataset_dir: Path to directory containing JSON dataset files
            logger: Optional logger for debug output
        """
        self.dataset_dir = Path(dataset_dir)
        self.logger = logger or logging.getLogger(__name__)
        self.realizations: Dict[str, ActionRealizationPool] = {}
        self.sprite_manifest: Dict[str, Dict[str, Any]] = {}
        self.sfx_manifest: Dict[str, Dict[str, Any]] = {}
    
    def load_all(self) -> None:
        """Load all datasets and manifests."""
        self.load_realizations()
        self.load_sprite_manifest()
        self.load_sfx_manifest()
        self.logger.info(
            f"Loaded {len(self.realizations)} action pools, "
            f"{len(self.sprite_manifest)} sprites, "
            f"{len(self.sfx_manifest)} SFX entries"
        )
    
    def load_realizations(self) -> None:
        """Load action realizations from JSON files."""
        # Try to load basic, extended, and advanced datasets
        datasets = [
            "chinchilla_realizations_basic.json",
            "chinchilla_realizations_extended.json",
            "chinchilla_realizations_advanced.json",
        ]
        
        total_loaded = 0
        for dataset_name in datasets:
            dataset_path = self.dataset_dir / dataset_name
            if not dataset_path.exists():
                self.logger.warning(f"Dataset not found: {dataset_path}")
                continue
            
            try:
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Parse realizations - data is a list of realization objects
                if isinstance(data, list):
                    for real_data in data:
                        action_id = real_data.get("intent_type")
                        if not action_id:
                            continue
                        
                        if action_id not in self.realizations:
                            self.realizations[action_id] = ActionRealizationPool(action_id)
                        
                        realization = self._parse_realization(action_id, real_data)
                        if realization:
                            self.realizations[action_id].add_realization(realization)
                            total_loaded += 1
                
                # Fallback: if data is dict, parse by action_id keys
                elif isinstance(data, dict):
                    for action_id, realizations in data.items():
                        if action_id not in self.realizations:
                            self.realizations[action_id] = ActionRealizationPool(action_id)
                        
                        if not isinstance(realizations, list):
                            realizations = [realizations]
                        
                        for real_data in realizations:
                            realization = self._parse_realization(action_id, real_data)
                            if realization:
                                self.realizations[action_id].add_realization(realization)
                                total_loaded += 1
                
                self.logger.info(
                    f"Loaded {dataset_name}: {total_loaded} total realizations"
                )
            except Exception as e:
                self.logger.error(f"Error loading {dataset_path}: {e}")
                import traceback
                traceback.print_exc()
    
    def _parse_realization(self, action_id: str, data: Dict[str, Any]) -> Optional[ActionRealization]:
        """Parse a single realization from JSON data."""
        try:
            # Handle new format where output is nested
            output_data = data.get("output", data)
            
            duration = output_data.get("duration", [10, 30])
            if isinstance(duration, (list, tuple)) and len(duration) == 2:
                duration = tuple(duration)
            else:
                duration = (10, 30)
            
            return ActionRealization(
                action_id=action_id,
                anim=output_data.get("anim", f"{action_id}_anim"),
                sfx=output_data.get("sfx"),
                position=output_data.get("position"),
                duration=duration,
                subtitle_ru=output_data.get("subtitle", ""),
                loop=output_data.get("loop", True),
                layer=output_data.get("layer", "action"),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse realization for {action_id}: {e}")
            return None
    
    def load_sprite_manifest(self) -> None:
        """Load sprite manifest from JSON."""
        manifest_path = self.dataset_dir.parent / "sprites" / "manifest.json"
        if not manifest_path.exists():
            self.logger.warning(f"Sprite manifest not found: {manifest_path}")
            return
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                self.sprite_manifest = json.load(f)
            self.logger.info(f"Loaded sprite manifest with {len(self.sprite_manifest)} entries")
        except Exception as e:
            self.logger.error(f"Error loading sprite manifest: {e}")
    
    def load_sfx_manifest(self) -> None:
        """Load SFX manifest from JSON."""
        manifest_path = self.dataset_dir.parent / "sfx" / "sfx_manifest.json"
        if not manifest_path.exists():
            self.logger.warning(f"SFX manifest not found: {manifest_path}")
            return
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                self.sfx_manifest = json.load(f)
            self.logger.info(f"Loaded SFX manifest with {len(self.sfx_manifest)} entries")
        except Exception as e:
            self.logger.error(f"Error loading SFX manifest: {e}")
    
    def get_realization_pool(self, action_id: str) -> Optional[ActionRealizationPool]:
        """Get realization pool for an action."""
        return self.realizations.get(action_id)
    
    def has_realization(self, action_id: str) -> bool:
        """Check if action has any realizations."""
        return action_id in self.realizations and self.realizations[action_id].count() > 0
    
    def get_random_realization(self, action_id: str) -> Optional[ActionRealization]:
        """Get a random realization for an action."""
        pool = self.get_realization_pool(action_id)
        if pool:
            return pool.get_random()
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dataset loading statistics."""
        total_realizations = sum(
            pool.count() for pool in self.realizations.values()
        )
        return {
            "num_action_types": len(self.realizations),
            "total_realizations": total_realizations,
            "num_sprites": len(self.sprite_manifest),
            "num_sfx": len(self.sfx_manifest),
            "avg_realizations_per_action": (
                total_realizations / len(self.realizations)
                if self.realizations else 0
            ),
        }


# ============================================================================
# DEFAULT FALLBACK REALIZATIONS
# ============================================================================

def get_fallback_realization(action_id: str) -> ActionRealization:
    """
    Get a fallback realization when dataset loading fails.
    Ensures basic functionality even with incomplete data.
    """
    from config import ACTION_LIBRARY
    meta = ACTION_LIBRARY.get(action_id)
    position = (
        getattr(getattr(meta, "default_position", None), "value", None)
        if meta else "current"
    ) or "current"
    return ActionRealization(
        action_id=action_id,
        anim=f"{action_id}_loop",
        sfx=None,
        position=position,
        duration=(10, 30),
        subtitle_ru=action_id,
        loop=True,
        layer="action",
    )
