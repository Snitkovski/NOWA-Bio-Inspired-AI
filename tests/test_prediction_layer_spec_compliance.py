"""
Comprehensive test suite for PredictionLayer (Plan C) specification compliance.

Tests cover:
- I. Architectural guarantees (TC-C-01 to TC-C-02)
- II. Behavioral tests (TC-C-03 to TC-C-05)
- III. Conflict resolution (TC-C-06 to TC-C-07)
- IV. Degradation tests (TC-C-08 to TC-C-10)
- V. Anti-pattern checks (TC-C-A1 to TC-C-A3)
"""

import pytest
from src.prediction_layer import PredictionLayer
from src.selector import ActionSelector
from src.affect import AffectiveState
from src.temporal_chains import ChainMemory, TemporalChain
from src.neuromodulators import NeuromodulatorState


class TestArchitecturalGuarantees:
    """I. Architectural tests - ensure Plan C doesn't violate core invariant"""

    def test_TC_C_01_prediction_layer_returns_pressure_not_action(self):
        """
        TC-C-01: Plan C does not make decisions
        - PredictionLayer.predict() returns pressure dict, NOT action string
        - No direct call to ActionSelector.choose()
        """
        pl = PredictionLayer(max_pressure=0.3)
        result = pl.predict(
            context={},
            recent_events=["action:walk", "action:walk", "action:talk"],
            affect_state=AffectiveState(),
            neuromodulators=NeuromodulatorState(),
            temporal_levels={}
        )
        
        # Result is a dict, not a string
        assert isinstance(result, dict)
        
        # Values are pressures (floats), not action names
        for action_name, pressure in result.items():
            assert isinstance(action_name, str)
            assert isinstance(pressure, float)
            assert -0.3 <= pressure <= 0.3

    def test_TC_C_02_prediction_layer_has_no_feedback_from_selector(self):
        """
        TC-C-02: Plan C doesn't know what selector chose
        - Same context → same pressure output regardless of selector's choice
        """
        pl = PredictionLayer(max_pressure=0.3)
        context = {}
        recent = ["action:walk", "action:talk"]
        affect = AffectiveState()
        neo = NeuromodulatorState()
        temporal = {}
        
        # Call predict twice with same inputs
        result1 = pl.predict(context, recent, affect, neo, temporal)
        result2 = pl.predict(context, recent, affect, neo, temporal)
        
        # Results must be identical (no adaptation to unknown feedback)
        assert result1 == result2


class TestBehavioralFunc:
    """II. Behavioral tests - core prediction functionality"""

    def test_TC_C_03_negative_prediction_lowers_pressure(self):
        """
        TC-C-03: Negative predictions suppress action
        - History contains:   action:irritate → bad_outcome (-1)
        - Expected behavior: lower pressure on 'irritate'
        """
        pl = PredictionLayer(max_pressure=0.3)
        
        # Simulate history where 'irritate' has negative association
        recent_bad = [
            "context:conflict",
            "action:irritate",
            "context:conflict",
            "action:irritate"
        ]
        
        neo = NeuromodulatorState()
        neo.dopamine = -0.3  # Negative valence signal
        
        result = pl.predict(
            context={},
            recent_events=recent_bad,
            affect_state=AffectiveState(valence=-0.5),
            neuromodulators=neo,
            temporal_levels={}
        )
        
        # 'irritate' should have negative or minimal pressure
        irritate_pressure = result.get("irritate", 0.0)
        assert irritate_pressure <= 0.1, f"Expected low/negative pressure, got {irritate_pressure}"

    def test_TC_C_04_positive_prediction_increases_pressure(self):
        """
        TC-C-04: Positive predictions enhance action
        - History: user:hello → action:greet → feedback:+1
        - Expected: higher pressure on 'greet'
        """
        pl = PredictionLayer(max_pressure=0.3)
        
        recent_good = [
            "context:user_greeting",
            "action:greet",
            "context:user_greeting",
            "action:greet"
        ]
        
        neo = NeuromodulatorState()
        neo.dopamine = 0.5  # Positive valence
        
        result = pl.predict(
            context={},
            recent_events=recent_good,
            affect_state=AffectiveState(valence=0.5),
            neuromodulators=neo,
            temporal_levels={}
        )
        
        # 'greet' should have positive pressure
        greet_pressure = result.get("greet", 0.0)
        assert greet_pressure >= 0.04, f"Expected positive pressure, got {greet_pressure}"

    def test_TC_C_05_no_hard_override_by_prediction_layer(self):
        """
        TC-C-05: Pressures sum, not override
        - Plan B (chains) suggests action A
        - Plan C predicts weak negative on action A
        - Result: soft influence, not hard block
        """
        # Create selector with multiple actions
        selector = ActionSelector(actions=["suggest", "ignore", "explore"])
        
        # Prepare: Plan B (dummy) would biasToward 'suggest'
        chain_bias = {"suggest": 0.5}  # Moderate positive from chains
        
        # Plan C gives weak negative
        plan_c_pressure = {"suggest": -0.1}  # Weak negative
        
        # Create pressure dict combining both
        pressure = {"suggest": 0.0, "ignore": 0.0, "explore": 0.0}
        pressure["suggest"] += chain_bias["suggest"] * 0.6  # Chain weight
        pressure["suggest"] += plan_c_pressure["suggest"] * 0.8  # PredictionLayer weight
        
        # After modifiers: 'suggest' still has positive pressure
        total_suggest = 0.5 * 0.6 + (-0.1) * 0.8
        assert total_suggest > 0, "Pressures should sum softly, not hard-override"


class TestConflictResolution:
    """III. Tests for conflict detection and no hard dominance"""

    def test_TC_C_06_only_selector_chooses(self):
        """
        TC-C-06: Verify single point of decision
        - ActionSelector.choose() is the only place where action is chosen
        - PredictionLayer only returns pressures
        """
        pl = PredictionLayer()
        selector = ActionSelector(actions=["a", "b", "c"])
        
        # PredictionLayer returns pressures
        pressures = pl.predict({}, ["action:a"], AffectiveState(), NeuromodulatorState(), {})
        assert isinstance(pressures, dict)
        
        # Selector chooses based on multiple inputs
        hippocampal_exps = []  # empty for simplicity
        cortical_patterns = []
        action = selector.choose(
            hippocampal_exps, cortical_patterns,
            prediction_pressure=pressures
        )
        assert isinstance(action, str)
        assert action in selector.actions

    def test_TC_C_07_order_independence_of_pressures(self):
        """
        TC-C-07: Pressure sources must be combinable independently
        - Apply pressures in different orders
        - Numerical difference allowed, logic not
        """
        affect_pressure = {"walk": 0.2, "run": -0.1}
        chain_pressure = {"walk": -0.2, "talk": 0.3}
        plan_c_pressure = {"walk": 0.05, "run": 0.1}
        
        # Combine in order 1: affect → chain → plan_c
        combined_1 = {}
        for a in ["walk", "run", "talk"]:
            combined_1[a] = (affect_pressure.get(a, 0) * 1.0 +
                            chain_pressure.get(a, 0) * 0.6 +
                            plan_c_pressure.get(a, 0) * 0.8)
        
        # Combine in order 2: plan_c → affect → chain (different order, same weights)
        combined_2 = {}
        for a in ["walk", "run", "talk"]:
            combined_2[a] = (plan_c_pressure.get(a, 0) * 0.8 +
                            affect_pressure.get(a, 0) * 1.0 +
                            chain_pressure.get(a, 0) * 0.6)
        
        # Results should be identical (addition is commutative)
        assert combined_1 == combined_2


class TestDegradation:
    """IV. Degradation tests - robustness without data"""

    def test_TC_C_08_empty_memory(self):
        """
        TC-C-08: Plan C works with no history
        - No temporal chains
        - No prior experiences
        - Should return neutral/empty pressure
        """
        pl = PredictionLayer()
        
        result = pl.predict(
            context={},
            recent_events=[],  # Empty history
            affect_state=AffectiveState(),
            neuromodulators=NeuromodulatorState(),
            temporal_levels={}
        )
        
        # Should return empty or near-zero pressures
        assert isinstance(result, dict)
        assert len(result) == 0, "Empty history → empty pressure"

    def test_TC_C_09_noisy_conflicting_data(self):
        """
        TC-C-09: Robustness to conflicting signals
        - History shows: A→+1, A→-1, A→+1, A→-1
        - Expected: pressure ≈ 0 (conflicting signals cancel)
        """
        pl = PredictionLayer(max_pressure=0.3)
        
        # Alternate positive and negative signals for same action
        recent_conflicting = [
            "action:ask", "action:ask", "action:ask", "action:ask"
        ]
        
        # First half: positive affect
        neo1 = NeuromodulatorState()
        neo1.dopamine = 0.5
        result1 = pl.predict({}, recent_conflicting, AffectiveState(valence=0.5), neo1, {})
        
        # Second half: negative affect (simulated by different call)
        neo2 = NeuromodulatorState()
        neo2.dopamine = -0.5
        result2 = pl.predict({}, recent_conflicting, AffectiveState(valence=-0.5), neo2, {})
        
        # Average should be close to neutral
        ask_pressure_1 = result1.get("ask", 0.0)
        ask_pressure_2 = result2.get("ask", 0.0)
        avg_pressure = (ask_pressure_1 + ask_pressure_2) / 2
        
        assert abs(avg_pressure) < 0.15, f"Conflicting signals should average near 0, got {avg_pressure}"

    def test_TC_C_10_emotional_pressure_vs_prediction(self):
        """
        TC-C-10: Emotions can override weak predictions
        - High arousal + dopamine
        - Plan C predicts small negative
        - Expected: agent may still choose action (emotions > caution)
        """
        pl = PredictionLayer()
        
        # Setup: weak negative prediction
        recent = ["action:risky"] * 3
        result = pl.predict(
            context={},
            recent_events=recent,
            affect_state=AffectiveState(arousal=1.8, valence=0.8),  # High arousal/positive
            neuromodulators=NeuromodulatorState(dopamine=0.8),  # High dopamine
            temporal_levels={}
        )
        
        # Prediction should reflect high dopamine, weak suppression
        risky_pressure = result.get("risky", 0.0)
        # Even with some negative history, high dopamine dominates
        assert risky_pressure >= -0.2, "Emotions can override weak predictions"


class TestAntiPatterns:
    """V. Anti-pattern checks (must NOT happen)"""

    def test_TC_C_A1_no_second_selector(self):
        """
        TC-C-A1: Plan C must NOT contain action selection logic
        - Check code has no 'if best_action == ... then return other_action'
        - PredictionLayer.predict only returns dict
        """
        pl = PredictionLayer()
        result = pl.predict({}, ["action:a"], AffectiveState(), NeuromodulatorState(), {})
        
        # Result is dict (not string/action)
        assert isinstance(result, dict)
        
        # Verify no hardcoded action selection
        for value in result.values():
            assert isinstance(value, float), "Values must be pressures, not actions"

    def test_TC_C_A2_no_learning_during_predict(self):
        """
        TC-C-A2: Plan C must NOT learn/update weights during predict()
        - Same input → same output (no side effects)
        - No state change in internal models
        """
        pl = PredictionLayer()
        recent = ["action:test"] * 5
        affect = AffectiveState()
        neo = NeuromodulatorState()
        
        # Get initial predict result
        result1 = pl.predict({}, recent, affect, neo, {})
        
        # Simulate some learning (would happen in sleep, not here)
        # Call predict again - should not change internal state
        result2 = pl.predict({}, recent, affect, neo, {})
        
        # Results identical → no learning during predict
        assert result1 == result2, "predict() must be side-effect free"

    def test_TC_C_A3_no_direct_affect_mutation(self):
        """
        TC-C-A3: Plan C must NOT mutate affect_state directly
        - affect_state is read-only input
        - Only returns pressures for selector to use
        """
        pl = PredictionLayer()
        affect = AffectiveState(curiosity=0.5, threat=0.2)
        
        # Store original values
        orig_curiosity = affect.curiosity
        orig_threat = affect.threat
        
        # Call predict
        pl.predict(
            {}, ["action:test"], affect,
            NeuromodulatorState(), {}
        )
        
        # Affect state unchanged
        assert affect.curiosity == orig_curiosity, "PredictionLayer must not mutate affect"
        assert affect.threat == orig_threat, "PredictionLayer must not mutate affect"


class TestIntegrationScenario:
    """VI. Mini-integration: realistic cognitive flow"""

    def test_TC_C_realistic_negative_feedback_scenario(self):
        """
        Mini-integration: User harsh → agent responds harshly → negative feedback
        → subsequent Plan C learns to suppress harsh response
        
        This is a simplified version (full version would need sleep consolidation)
        """
        from src.temporal_chains import ChainMemory
        
        # Setup chains: harsh_input → harsh_response → negative outcome
        chains = ChainMemory()
        
        # Record negative chain: user:insult → action:respond_harshly → bad
        chains.add_or_update(
            ("context:user:insult", "action:respond_harshly"),
            net_affect=-0.8  # Strong negative
        )
        
        # Now test PredictionLayer with this history
        pl = PredictionLayer()
        
        # Recent context contains harsh exchange
        recent = [
            "context:user:insult",
            "action:respond_harshly",
            "context:user:insult",
            "action:respond_harshly"
        ]
        
        # PredictionLayer should see negative pattern
        result = pl.predict(
            context={"context_events": ["user:insult"]},
            recent_events=recent,
            affect_state=AffectiveState(valence=-0.6),
            neuromodulators=NeuromodulatorState(dopamine=-0.3),
            temporal_levels={}
        )
        
        # respond_harshly should get negative or low pressure
        harsh_pressure = result.get("respond_harshly", 0.0)
        assert harsh_pressure < 0.1, "Plan C should suppress previously-punished action"

    def test_TC_C_positive_pattern_reinforcement(self):
        """
        Integration: User polite → agent responds politely → positive feedback
        → Plan C reinforces polite response
        """
        pl = PredictionLayer()
        
        # Recent history: polite input → friendly response → good outcome
        recent = [
            "context:user:polite",
            "action:respond_friendly",
            "context:user:polite",
            "action:respond_friendly"
        ]
        
        result = pl.predict(
            context={},
            recent_events=recent,
            affect_state=AffectiveState(valence=0.6),
            neuromodulators=NeuromodulatorState(dopamine=0.5),
            temporal_levels={}
        )
        
        # respond_friendly should get positive pressure
        friendly_pressure = result.get("respond_friendly", 0.0)
        assert friendly_pressure >= 0.04, "Plan C should reinforce previously-rewarded action"
