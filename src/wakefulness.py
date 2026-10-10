"""
Wakefulness State - Physiological sleep-wake regulation.

Phase 2 Extension: Wakefulness, Sleep and Prefrontal Cortex Modulation

This module implements:
- Wakefulness state [0.0 .. 1.0] representing sleep deprivation
- Gradual accumulation during wakefulness
- Recovery during sleep
- Modulation of neuromodulators
- Modulation of PFC trust signals

Key principle: Wakefulness modulates, it does NOT make decisions.
It represents a physiological state affecting cognitive reliability.
"""

import time
import math
from typing import Dict, Optional


class WakefulnessState:
    """
    Physiological wakefulness state.
    
    Represents Borbély Process S (sleep pressure) plus Process C (circadian signal).
    
    Specification:
    - 0.0 = fully rested agent
    - 1.0 = severe sleep deprivation
    - Accumulates during wakefulness
    - Recovers during sleep
    - Modulates neuromodulators and PFC trust
    - Combines Process S and Process C into effective alertness
    """
    
    # Accumulation parameters (production defaults)
    # Full deprivation (~1.0) occurs after ~16 hours of continuous wakefulness
    ACCUMULATION_RATE = 1.0 / (16.0 * 60.0 * 60.0)  # per second

    # Recovery parameters
    # Full recovery (~0.0) occurs after ~8 hours of sleep
    RECOVERY_RATE = 1.0 / (8.0 * 60.0 * 60.0)  # per second

    # Circadian Process C parameters
    CIRCADIAN_PERIOD_HOURS = 24.0
    CIRCADIAN_AMPLITUDE = 0.3
    CIRCADIAN_PHASE = 0.0
    DEFAULT_ALERTNESS_BASE = 1.0
    
    # PFC modulation constants
    PFC_SIGNAL_STRENGTH_MULTIPLIER = 0.4  # (1 + wakefulness * 0.4)
    PFC_SIGNAL_NOISE_MULTIPLIER = 0.7    # (1 + wakefulness * 0.7)
    
    # Neuromodulator interaction constants
    CORTISOL_INCREASE = 0.01      # per wakefulness unit
    NOREPINEPHRINE_INCREASE = 0.02  # per wakefulness unit
    SEROTONIN_DECREASE = 0.015    # per wakefulness unit
    
    def __init__(
        self,
        initial_wakefulness: float = 0.0,
        accumulation_rate: float = None,
        recovery_rate: float = None,
        circadian_period_hours: float = None,
        circadian_amplitude: float = None,
        circadian_phase: float = None,
        initial_circadian_time_hours: float = 0.0,
    ):
        """
        Initialize wakefulness state.
        
        Args:
            initial_wakefulness: Initial wakefulness level [0.0 .. 1.0]
                0.0 = fully rested
                1.0 = severe deprivation
        """
        self._wakefulness = max(0.0, min(1.0, float(initial_wakefulness)))
        self.last_update_ts = time.time()
        self.accumulated_waking_time = 0.0  # Track for statistics
        self.total_sleep_time = 0.0  # Track for statistics
        # allow per-instance rates for demo/embedding use; default to class constants
        self.accumulation_rate = float(accumulation_rate) if accumulation_rate is not None else float(self.ACCUMULATION_RATE)
        self.recovery_rate = float(recovery_rate) if recovery_rate is not None else float(self.RECOVERY_RATE)
        self.circadian_period_hours = max(
            1e-6,
            float(circadian_period_hours) if circadian_period_hours is not None else float(self.CIRCADIAN_PERIOD_HOURS),
        )
        self.circadian_amplitude = max(
            0.0,
            float(circadian_amplitude) if circadian_amplitude is not None else float(self.CIRCADIAN_AMPLITUDE),
        )
        self.circadian_phase = float(circadian_phase) if circadian_phase is not None else float(self.CIRCADIAN_PHASE)
        self.circadian_time_hours = float(initial_circadian_time_hours)
        self.alertness_base = float(self.DEFAULT_ALERTNESS_BASE)
    
    @property
    def wakefulness(self) -> float:
        """Get current wakefulness level"""
        return self._wakefulness
    
    @wakefulness.setter
    def wakefulness(self, value: float):
        """Set wakefulness level (auto-clamped to [0.0, 1.0])"""
        self._wakefulness = max(0.0, min(1.0, float(value)))
    
    def _clamp(self, value: float) -> float:
        """Clamp wakefulness to [0.0, 1.0]."""
        return max(0.0, min(1.0, value))

    def _advance_circadian_time(self, elapsed_seconds: float):
        """Advance Process C time coordinate (in hours)."""
        self.circadian_time_hours += max(0.0, float(elapsed_seconds)) / 3600.0
    
    def update_waking(self, elapsed_seconds: float = None) -> float:
        """
        Update wakefulness during waking period.
        
        Accumulates wakefulness at constant rate.
        
        Args:
            elapsed_seconds: Time elapsed since last update.
                            If None, uses time.time() difference.
        
        Returns:
            New wakefulness level [0.0 .. 1.0]
        """
        if elapsed_seconds is None:
            current_time = time.time()
            elapsed_seconds = max(0.0, current_time - self.last_update_ts)
            self.last_update_ts = current_time
        
        if elapsed_seconds <= 0:
            return self._wakefulness
        
        self.accumulated_waking_time += elapsed_seconds
        self._advance_circadian_time(elapsed_seconds)
        
        # Linear accumulation (instance-level override possible)
        self._wakefulness += elapsed_seconds * self.accumulation_rate
        self._wakefulness = self._clamp(self._wakefulness)
        
        return self._wakefulness
    
    def update_sleeping(self, elapsed_seconds: float = None) -> float:
        """
        Update wakefulness during sleep period.
        
        Recovers wakefulness (reduces level) at constant rate.
        
        Args:
            elapsed_seconds: Time elapsed since sleep started.
                            If None, uses time.time() difference.
        
        Returns:
            New wakefulness level [0.0 .. 1.0]
        """
        if elapsed_seconds is None:
            current_time = time.time()
            elapsed_seconds = max(0.0, current_time - self.last_update_ts)
            self.last_update_ts = current_time
        
        if elapsed_seconds <= 0:
            return self._wakefulness
        
        self.total_sleep_time += elapsed_seconds
        self._advance_circadian_time(elapsed_seconds)
        
        # Linear recovery (could be made nonlinear - faster recovery early)
        self._wakefulness -= elapsed_seconds * self.recovery_rate
        self._wakefulness = self._clamp(self._wakefulness)
        
        return self._wakefulness

    def get_sleep_pressure(self) -> float:
        """Return Process S (sleep pressure)."""
        return self._wakefulness

    def get_circadian_signal(self) -> float:
        """
        Return Process C circadian component.

        C(t) = A * sin(2πt / T + phase)
        """
        omega = (2.0 * math.pi) / self.circadian_period_hours
        return self.circadian_amplitude * math.sin((omega * self.circadian_time_hours) + self.circadian_phase)

    def get_wake_drive(self) -> float:
        """Return Borbély wake drive: Process C - Process S."""
        return self.get_circadian_signal() - self.get_sleep_pressure()

    def get_alertness(self, base_alertness: Optional[float] = None, clamp: bool = True) -> float:
        """
        Compute effective alertness from Process S and Process C.

        alertness = base - sleep_pressure + circadian_signal
        """
        base = self.alertness_base if base_alertness is None else float(base_alertness)
        alertness = base - self.get_sleep_pressure() + self.get_circadian_signal()
        if clamp:
            return self._clamp(alertness)
        return alertness
    
    def get_neuromodulator_deltas(self) -> Dict[str, float]:
        """
        Get neuromodulator changes caused by wakefulness state.
        
        Specification:
        - cortisol += wakefulness * 0.01
        - norepinephrine += wakefulness * 0.02
        - serotonin -= wakefulness * 0.015
        
        Returns:
            Dict with keys: 'cortisol', 'norepinephrine', 'serotonin'
            Values are changes (deltas) to apply to neuromodulators
        """
        return {
            'cortisol': self._wakefulness * self.CORTISOL_INCREASE,
            'norepinephrine': self._wakefulness * self.NOREPINEPHRINE_INCREASE,
            'serotonin': -self._wakefulness * self.SEROTONIN_DECREASE,
        }
    
    def get_pfc_signal_strength_modifier(self) -> float:
        """
        FIXED (Spec #8): Get PFC signal reliability modifier.
        
        Tiredness = noise, not weakness. High wakefulness -> reliable signal.
        Low wakefulness -> noisy, unreliable PFC signal.
        
        Returns:
            Reliability multiplier for PFC signal
            Formula: 1.0 - (1.0 - wakefulness) * 0.4
            When awake (1.0): returns 1.0 (full strength)
            When sleepy (0.0): returns 0.6 (reduced reliability)
            Range: [0.6 .. 1.0]
        """
        # Specification: tiredness should introduce noise, not reduce or
        # increase the intrinsic signal strength. The PFC maintains its
        # nominal influence (strength) while its reliability/noise changes.
        # Keep strength constant at 1.0 so callers can model noise vs. weight
        # separately (use `get_pfc_signal_noise_modifier` for unreliability).
        return 1.0
    
    def get_pfc_signal_noise_modifier(self) -> float:
        """
        Get PFC signal noise modulation.
        
        Higher wakefulness → more noisy, less precise thoughts.
        
        Returns:
            Multiplier for PFC signal noise
            Formula: 1 + wakefulness * 0.7
            Range: [1.0 .. 1.7]
        """
        return 1.0 + self._wakefulness * self.PFC_SIGNAL_NOISE_MULTIPLIER
    
    def get_pfc_weight_modifier(self, conflict: float) -> float:
        """
        Get effective PFC weight modifier under conflict.
        
        When fatigued and under conflict, PFC influence degrades.
        
        Specification:
        effective_PFC_weight *= (1 - conflict * wakefulness)
        
        Args:
            conflict: Conflict/ambiguity score [0.0 .. 1.0]
        
        Returns:
            Multiplier for PFC weight
            Range: [0.0 .. 1.0]
        """
        return max(0.0, 1.0 - (conflict * self._wakefulness))
    
    def get_cognitive_reliability(self) -> float:
        """
        Get overall cognitive reliability metric.

        Includes both homeostatic pressure (Process S) and circadian support
        (Process C) via effective alertness.

        Returns:
            Reliability score [0.0 .. 1.0]
            1.0 = fully reliable
            0.0 = completely unreliable
        """
        return self.get_alertness(base_alertness=1.0, clamp=True)
    
    def get_statistics(self) -> Dict[str, float]:
        """
        Get wakefulness statistics.
        
        Returns:
            Dict with:
            - 'current': current wakefulness [0..1]
            - 'cognitive_reliability': effective alertness/reliability
            - 'accumulated_waking_hours': total hours awake
            - 'total_sleep_hours': total hours asleep
        """
        return {
            'current': self._wakefulness,
            'cognitive_reliability': self.get_cognitive_reliability(),
            'accumulated_waking_hours': self.accumulated_waking_time / 3600.0,
            'total_sleep_hours': self.total_sleep_time / 3600.0,
            'circadian_signal': self.get_circadian_signal(),
            'wake_drive': self.get_wake_drive(),
            'alertness': self.get_alertness(),
            'circadian_time_hours': self.circadian_time_hours,
            'circadian_period_hours': self.circadian_period_hours,
            'circadian_amplitude': self.circadian_amplitude,
            'circadian_phase': self.circadian_phase,
        }
    
    def reset(self, to_value: float = 0.0):
        """
        Reset wakefulness state.
        
        Args:
            to_value: Target wakefulness value [0.0 .. 1.0]
        """
        self.wakefulness = to_value
        self.last_update_ts = time.time()
        self.accumulated_waking_time = 0.0
        self.total_sleep_time = 0.0
        self.circadian_time_hours = 0.0
    
    def __repr__(self) -> str:
        reliability = self.get_cognitive_reliability()
        circadian = self.get_circadian_signal()
        return (
            f"WakefulnessState(w={self._wakefulness:.3f}, "
            f"reliability={reliability:.3f}, "
            f"circadian={circadian:.3f}, "
            f"awake_hours={self.accumulated_waking_time/3600:.1f}h)"
        )
