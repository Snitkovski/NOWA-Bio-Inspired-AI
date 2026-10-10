"""
Tests for Wakefulness State - Phase 2 Extension.

Test cases from specification:
- TC-1: Accumulation of fatigue
- TC-2: Sleep recovery
- TC-3: Cortisol increase
- TC-4: PFC signal amplification
- TC-5: Reality check (PFC weight modifier under conflict)
- TC-6: Recovery after sleep
"""

import pytest
import math
from wakefulness import WakefulnessState


class TestWakefulnessAccumulation:
    """TC-1: Fatigue accumulation during wakefulness"""
    
    def test_initial_state_fully_rested(self):
        """Initial state should be fully rested (0.0)"""
        w = WakefulnessState()
        assert w.wakefulness == 0.0
        assert w.get_cognitive_reliability() == 1.0
    
    def test_accumulation_linear(self):
        """Wakefulness should accumulate linearly at ACCUMULATION_RATE"""
        w = WakefulnessState()
        
        # Simulate 1 hour of wakefulness
        elapsed = 3600.0
        w.update_waking(elapsed)
        
        # After 1 hour, wakefulness should be:
        # elapsed * ACCUMULATION_RATE = 3600 * (1 / (16 * 3600)) = 0.0625
        expected = elapsed * WakefulnessState.ACCUMULATION_RATE
        assert abs(w.wakefulness - expected) < 0.001
    
    def test_accumulation_eight_hours(self):
        """After 8 hours of wakefulness, should be ~0.5"""
        w = WakefulnessState()
        elapsed = 8 * 3600.0
        w.update_waking(elapsed)
        
        # 8 hours / 16 hours = 0.5
        assert abs(w.wakefulness - 0.5) < 0.01
    
    def test_accumulation_sixteen_hours(self):
        """After 16 hours of wakefulness, should be ~1.0"""
        w = WakefulnessState()
        elapsed = 16 * 3600.0
        w.update_waking(elapsed)
        
        # Should reach 1.0 (clamped)
        assert abs(w.wakefulness - 1.0) < 0.01
    
    def test_accumulation_clamped_at_one(self):
        """Wakefulness should be clamped at 1.0"""
        w = WakefulnessState()
        elapsed = 20 * 3600.0  # More than 16 hours
        w.update_waking(elapsed)
        
        assert w.wakefulness == 1.0


class TestWakefulnessSleep:
    """TC-2: Sleep recovery"""
    
    def test_sleep_recovery_linear(self):
        """Sleep should reduce wakefulness at RECOVERY_RATE"""
        w = WakefulnessState()
        
        # Start with high wakefulness
        w.wakefulness = 0.8
        
        # Sleep for 1 hour
        elapsed = 3600.0
        w.update_sleeping(elapsed)
        
        # After 1 hour sleep from 0.8:
        # reduction = elapsed * RECOVERY_RATE = 3600 * (1 / (8 * 3600)) = 0.125
        expected = 0.8 - elapsed * WakefulnessState.RECOVERY_RATE
        assert abs(w.wakefulness - expected) < 0.001
    
    def test_sleep_recovery_six_hours(self):
        """After 6 hours of sleep, wakefulness should decrease significantly"""
        w = WakefulnessState()
        w.wakefulness = 0.8
        
        elapsed = 6 * 3600.0
        w.update_sleeping(elapsed)
        
        # 6 hours / 8 hours = 0.75 recovery
        expected = 0.8 - 0.75
        assert abs(w.wakefulness - expected) < 0.01
    
    def test_sleep_recovery_eight_hours(self):
        """After 8 hours of sleep, should return to 0.0"""
        w = WakefulnessState()
        w.wakefulness = 1.0
        
        elapsed = 8 * 3600.0
        w.update_sleeping(elapsed)
        
        # Should reach 0.0 (fully recovered)
        assert abs(w.wakefulness - 0.0) < 0.01
    
    def test_sleep_recovery_clamped_at_zero(self):
        """Wakefulness should be clamped at 0.0"""
        w = WakefulnessState()
        w.wakefulness = 0.1
        
        elapsed = 10 * 3600.0  # More than full recovery
        w.update_sleeping(elapsed)
        
        assert w.wakefulness == 0.0


class TestCircadianProcessC:
    """Process C: Circadian rhythm integration"""

    def test_circadian_signal_defaults_to_zero_at_t0(self):
        w = WakefulnessState(accumulation_rate=0.0)
        assert abs(w.get_circadian_signal()) < 1e-9

    def test_circadian_peak_after_quarter_cycle(self):
        w = WakefulnessState(accumulation_rate=0.0)

        # 6h = T/4 for default T=24h, therefore sin(...) should be close to +1.
        w.update_waking(6 * 3600.0)
        assert abs(w.get_circadian_signal() - WakefulnessState.CIRCADIAN_AMPLITUDE) < 1e-6

    def test_circadian_phase_shift(self):
        w = WakefulnessState(
            accumulation_rate=0.0,
            circadian_phase=math.pi / 2.0,
        )
        assert abs(w.get_circadian_signal() - WakefulnessState.CIRCADIAN_AMPLITUDE) < 1e-6

    def test_wake_drive_uses_process_c_minus_process_s(self):
        w = WakefulnessState(accumulation_rate=0.0)
        w.wakefulness = 0.4
        w.update_waking(6 * 3600.0)  # Circadian signal -> +0.3

        expected = WakefulnessState.CIRCADIAN_AMPLITUDE - 0.4
        assert abs(w.get_wake_drive() - expected) < 1e-6

    def test_alertness_formula_with_and_without_clamp(self):
        w = WakefulnessState(accumulation_rate=0.0)
        w.update_waking(6 * 3600.0)  # Circadian signal -> +0.3

        unclamped = w.get_alertness(clamp=False)
        clamped = w.get_alertness()

        assert abs(unclamped - 1.3) < 1e-6
        assert clamped == 1.0

    def test_statistics_include_circadian_fields(self):
        w = WakefulnessState(accumulation_rate=0.0)
        w.update_waking(6 * 3600.0)

        stats = w.get_statistics()
        assert "circadian_signal" in stats
        assert "wake_drive" in stats
        assert "alertness" in stats
        assert "circadian_time_hours" in stats
        assert "circadian_period_hours" in stats
        assert "circadian_amplitude" in stats
        assert "circadian_phase" in stats


class TestNeuromodulatorInteraction:
    """TC-3: Neuromodulator changes due to wakefulness"""
    
    def test_cortisol_increase_from_wakefulness(self):
        """Cortisol should increase with wakefulness"""
        w = WakefulnessState()
        w.wakefulness = 0.5
        
        deltas = w.get_neuromodulator_deltas()
        
        expected_cortisol = 0.5 * WakefulnessState.CORTISOL_INCREASE
        assert abs(deltas['cortisol'] - expected_cortisol) < 0.001
        assert deltas['cortisol'] > 0
    
    def test_norepinephrine_increase_from_wakefulness(self):
        """Norepinephrine should increase with wakefulness"""
        w = WakefulnessState()
        w.wakefulness = 0.5
        
        deltas = w.get_neuromodulator_deltas()
        
        expected_ne = 0.5 * WakefulnessState.NOREPINEPHRINE_INCREASE
        assert abs(deltas['norepinephrine'] - expected_ne) < 0.001
        assert deltas['norepinephrine'] > 0
    
    def test_serotonin_decrease_from_wakefulness(self):
        """Serotonin should decrease with wakefulness"""
        w = WakefulnessState()
        w.wakefulness = 0.5
        
        deltas = w.get_neuromodulator_deltas()
        
        expected_serotonin = -0.5 * WakefulnessState.SEROTONIN_DECREASE
        assert abs(deltas['serotonin'] - expected_serotonin) < 0.001
        assert deltas['serotonin'] < 0
    
    def test_dopamine_unchanged(self):
        """Dopamine should NOT be affected by wakefulness"""
        w = WakefulnessState()
        w.wakefulness = 0.9
        
        deltas = w.get_neuromodulator_deltas()
        
        # dopamine should not be in deltas (spec says "Dopamine НЕ изменяется напрямую")
        assert 'dopamine' not in deltas or deltas.get('dopamine') == 0.0
    
    def test_neuromodulator_monotonic_increase(self):
        """Cortisol should increase monotonically with wakefulness"""
        w = WakefulnessState()
        
        previous_cort = 0.0
        for level in [0.1, 0.3, 0.5, 0.7, 0.9]:
            w.wakefulness = level
            deltas = w.get_neuromodulator_deltas()
            current_cort = deltas['cortisol']
            
            assert current_cort >= previous_cort
            previous_cort = current_cort


class TestPFCModulation:
    """TC-4 & TC-5: PFC signal modulation and conflict interaction"""
    
    def test_pfc_signal_strength_increases_with_wakefulness(self):
        """PFC signal strength should remain constant; tiredness => noise"""
        w = WakefulnessState()

        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            w.wakefulness = level
            mod = w.get_pfc_signal_strength_modifier()
            # Strength is constant per specification (tiredness introduces noise, not weakness)
            assert mod == 1.0
    
    def test_pfc_signal_noise_increases_with_wakefulness(self):
        """Higher wakefulness → more noisy PFC signal"""
        w = WakefulnessState()
        
        modifiers = []
        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            w.wakefulness = level
            mod = w.get_pfc_signal_noise_modifier()
            modifiers.append(mod)
        
        # Should be monotonically increasing
        for i in range(len(modifiers) - 1):
            assert modifiers[i] <= modifiers[i + 1]
        
        # Range check: [1.0, 1.7]
        assert modifiers[0] == 1.0
        assert abs(modifiers[-1] - 1.7) < 0.01
    
    def test_pfc_weight_modifier_no_conflict(self):
        """Without conflict, PFC weight should be 1.0"""
        w = WakefulnessState()
        w.wakefulness = 0.9
        conflict = 0.0
        
        modifier = w.get_pfc_weight_modifier(conflict)
        assert modifier == 1.0
    
    def test_pfc_weight_modifier_with_conflict(self):
        """With conflict, PFC weight degrades based on wakefulness"""
        w = WakefulnessState()
        conflict = 0.8
        
        # No wakefulness: weight should be preserved
        w.wakefulness = 0.0
        mod_no_wake = w.get_pfc_weight_modifier(conflict)
        assert mod_no_wake == 1.0
        
        # High wakefulness: weight should degrade
        w.wakefulness = 0.9
        mod_wake = w.get_pfc_weight_modifier(conflict)
        
        # Expected: 1 - (0.8 * 0.9) = 1 - 0.72 = 0.28
        expected = 1.0 - (conflict * w.wakefulness)
        assert abs(mod_wake - expected) < 0.001
        assert mod_wake < mod_no_wake
    
    def test_pfc_weight_modifier_range(self):
        """PFC weight modifier should be in [0.0, 1.0]"""
        w = WakefulnessState()
        
        for w_level in [0.0, 0.5, 1.0]:
            for c_level in [0.0, 0.5, 1.0]:
                w.wakefulness = w_level
                mod = w.get_pfc_weight_modifier(c_level)
                
                assert 0.0 <= mod <= 1.0


class TestCognitiveReliability:
    """General cognitive reliability metric"""
    
    def test_reliability_inverse_of_wakefulness(self):
        """Cognitive reliability should be 1 - wakefulness"""
        w = WakefulnessState()
        
        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            w.wakefulness = level
            reliability = w.get_cognitive_reliability()
            
            expected = 1.0 - level
            assert abs(reliability - expected) < 0.001
    
    def test_reliability_range(self):
        """Reliability should be in [0.0, 1.0]"""
        w = WakefulnessState()
        
        for level in [0.0, 0.25, 0.5, 0.75, 1.0]:
            w.wakefulness = level
            reliability = w.get_cognitive_reliability()
            
            assert 0.0 <= reliability <= 1.0


class TestWakefulnessStatistics:
    """Statistics tracking"""
    
    def test_statistics_initial(self):
        """Initial statistics should be zero"""
        w = WakefulnessState()
        
        stats = w.get_statistics()
        assert stats['current'] == 0.0
        assert stats['cognitive_reliability'] == 1.0
        assert stats['accumulated_waking_hours'] == 0.0
        assert stats['total_sleep_hours'] == 0.0
    
    def test_accumulated_waking_time_tracking(self):
        """Should track accumulated waking time"""
        w = WakefulnessState()
        
        elapsed = 3600.0  # 1 hour
        w.update_waking(elapsed)
        
        stats = w.get_statistics()
        assert abs(stats['accumulated_waking_hours'] - 1.0) < 0.001
    
    def test_total_sleep_time_tracking(self):
        """Should track total sleep time"""
        w = WakefulnessState()
        w.wakefulness = 0.5
        
        elapsed = 3600.0  # 1 hour
        w.update_sleeping(elapsed)
        
        stats = w.get_statistics()
        assert abs(stats['total_sleep_hours'] - 1.0) < 0.001


class TestWakefulnessReset:
    """Reset and set operations"""
    
    def test_reset_to_default(self):
        """Reset should return to 0.0"""
        w = WakefulnessState()
        w.wakefulness = 0.8
        w.accumulated_waking_time = 1000.0
        
        w.reset()
        
        assert w.wakefulness == 0.0
        assert w.accumulated_waking_time == 0.0
        assert w.total_sleep_time == 0.0
    
    def test_reset_to_value(self):
        """Reset should accept a target value"""
        w = WakefulnessState()
        
        w.reset(0.5)
        
        assert w.wakefulness == 0.5
    
    def test_set_wakefulness_clamping(self):
        """Setting wakefulness should clamp to [0.0, 1.0]"""
        w = WakefulnessState()
        
        w.wakefulness = 1.5
        assert w.wakefulness == 1.0
        
        w.wakefulness = -0.5
        assert w.wakefulness == 0.0


class TestIntegrationWithNeuromodulators:
    """Integration test with neuromodulator state"""
    
    def test_wakefulness_affects_neuromodulators(self):
        """Wakefulness changes should affect neuromodulator values"""
        from neuromodulators import NeuromodulatorState
        
        nm = NeuromodulatorState()
        initial_cortisol = nm.cortisol
        
        w = WakefulnessState()
        w.wakefulness = 0.5
        
        deltas = w.get_neuromodulator_deltas()
        nm.cortisol = nm._clamp(nm.cortisol + deltas['cortisol'])
        nm.norepinephrine = nm._clamp(nm.norepinephrine + deltas['norepinephrine'])
        nm.serotonin = nm._clamp(nm.serotonin + deltas['serotonin'])
        
        # Cortisol should have increased
        assert nm.cortisol > initial_cortisol


class TestPhysiologicalReasoning:
    """Test physiological reasonableness"""
    
    def test_16_hour_deprivation_realistic(self):
        """16 hours of wakefulness should cause full deprivation"""
        w = WakefulnessState()
        
        # Accumulate over 16 hours
        for hour in range(16):
            w.update_waking(3600.0)
        
        # Should be very close to 1.0 (severe deprivation)
        assert w.wakefulness >= 0.95
    
    def test_8_hour_sleep_full_recovery(self):
        """8 hours of sleep should fully recover from deprivation"""
        w = WakefulnessState()
        w.wakefulness = 0.9  # Severely deprived
        
        # Sleep for 8 hours
        w.update_sleeping(8 * 3600.0)
        
        # Should be close to 0.0
        assert w.wakefulness <= 0.05
    
    def test_realistic_daily_cycle(self):
        """Simulate a realistic daily cycle"""
        w = WakefulnessState()
        
        # Wake for 16 hours
        w.update_waking(16 * 3600.0)
        assert w.wakefulness >= 0.95
        
        # Sleep for 8 hours
        w.update_sleeping(8 * 3600.0)
        assert w.wakefulness <= 0.05


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
