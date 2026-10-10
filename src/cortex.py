"""
Cortex - Consolidated slow memory.

This module maintains compatibility but the main CortexMemory and CorticalPattern
are now defined in sleep.py as they're part of the sleep consolidation system.

Import from sleep.py for the active implementations.
"""

# Re-export for backward compatibility
from sleep import CortexMemory, CorticalPattern, SleepManager

__all__ = ['CortexMemory', 'CorticalPattern', 'SleepManager']
