"""
Dynamic configuration builder - generates action library and metadata from datasets.
Replaces hardcoded ACTION_LIBRARY by inferring properties from loaded realizations.
"""

import logging
from pathlib import Path
from typing import Dict, Set, Any
from dataclasses import dataclass
import json

# ============================================================================
# DYNAMIC ACTION LIBRARY GENERATOR
# ============================================================================

class ActionLibraryBuilder:
    """Builds action library dynamically from datasets."""
    
    def __init__(self, dataset_dir: Path, logger: logging.Logger = None):
        self.dataset_dir = Path(dataset_dir)
        self.logger = logger or logging.getLogger(__name__)
        self.action_library = {}
        self.action_contexts = {}  # action_id -> set of contexts
        self.action_layers = {}    # action_id -> layer value
    
    def build_from_datasets(self) -> Dict[str, Any]:
        """
        Build action library from all dataset JSON files.
        
        Returns:
            Dictionary: action_id -> metadata dict
        """
        datasets = [
            "chinchilla_realizations_basic.json",
            "chinchilla_realizations_extended.json",
            "chinchilla_realizations_advanced.json",
        ]
        
        for dataset_name in datasets:
            dataset_path = self.dataset_dir / dataset_name
            if not dataset_path.exists():
                continue
            
            try:
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    for item in data:
                        self._process_realization_item(item)
            
            except Exception as e:
                self.logger.error(f"Error processing {dataset_name}: {e}")
        
        # Build final action library
        self._finalize_library()
        
        self.logger.info(
            f"Built action library with {len(self.action_library)} actions "
            f"from datasets"
        )
        
        return self.action_library
    
    def _process_realization_item(self, item: Dict[str, Any]) -> None:
        """Process a single realization item from dataset."""
        action_id = item.get("intent_type")
        if not action_id:
            return
        
        output = item.get("output", {})
        
        # Initialize action entry if new
        if action_id not in self.action_library:
            self.action_library[action_id] = {
                "action_id": action_id,
                "display_name": action_id.replace("_", " ").title(),
                "realizations": [],
                "contexts": set(),
                "layer": output.get("layer", "action"),
                "is_pathological": "pathological" in str(item).lower(),
            }
        
        # Track contexts
        contexts = item.get("context", [])
        if action_id not in self.action_contexts:
            self.action_contexts[action_id] = set()
        self.action_contexts[action_id].update(contexts)
        
        # Track layer
        if "layer" in output:
            self.action_library[action_id]["layer"] = output["layer"]
        
        # Store realization for reference
        self.action_library[action_id]["realizations"].append(output)
    
    def _finalize_library(self) -> None:
        """Convert sets to lists for JSON compatibility."""
        for action_id, metadata in self.action_library.items():
            metadata["contexts"] = list(metadata.get("contexts", set()))
            
            # Infer if pathological from contexts
            contexts_str = str(metadata["contexts"]).lower()
            if any(pat in contexts_str for pat in ["stress", "bar_chew", "stereo"]):
                metadata["is_pathological"] = True
            
            # Remove realizations from final output (too verbose)
            metadata.pop("realizations", None)


def load_action_library_from_datasets(dataset_dir: str) -> Dict[str, Any]:
    """
    Load action library from datasets.
    
    Args:
        dataset_dir: Path to Datasets directory
    
    Returns:
        Dictionary with action metadata
    """
    builder = ActionLibraryBuilder(Path(dataset_dir))
    return builder.build_from_datasets()


# ============================================================================
# DEFAULT FALLBACK - when datasets not available
# ============================================================================

def get_default_action_metadata(action_id: str) -> Dict[str, Any]:
    """
    Get default metadata for an action when dataset not available.
    """
    # Categorize action for default properties
    pathological = action_id in [
        "bar_chewing", "stereotypy_pacing", "overgroom_fur", "overgroom_other", "fur_slip"
    ]
    
    layer = "action"
    if action_id in ["ear_forward", "ear_flat", "tail_raise", "press_flat", "eye_half_close"]:
        layer = "postural"
    elif action_id in ["yawn", "whisker_twitch", "nose_twitch", "thump_hind", "body_shake"]:
        layer = "micro"
    
    return {
        "action_id": action_id,
        "display_name": action_id.replace("_", " ").title(),
        "layer": layer,
        "is_pathological": pathological,
        "contexts": [],
    }
