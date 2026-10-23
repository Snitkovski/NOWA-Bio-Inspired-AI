"""Tests for autonomous organism runtime (spec v1)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from affective_space import AffectiveSpace
from autonomous_organism import (
    AutonomousOrganismAgent,
    DriveSystem,
    EnergySystem,
    InternalSimulationLoop,
    OrganismHardLimits,
    SpeechGovernor,
    DRIVE_NAMES,
)
from simulation_utility import compute_drive_utility_components


class ClockStub:
    def __init__(self, start: float = 0.0):
        self._now = float(start)

    def time(self) -> float:
        return self._now

    def advance(self, dt: float) -> None:
        self._now += float(dt)


class StubMemory:
    def __init__(self, recalls=None):
        self.recalls = list(recalls or [])
        self.decay_calls = 0

    def recall_by_drive(self, active_drive, limit=6):
        return self.recalls[:limit]

    def update_memory_decay(self, dt):
        self.decay_calls += 1


class StubCognitive:
    def __init__(self):
        self.baseline_calls = 0

    def generate_hypotheses(self, active_drive=None, recalls=None):
        recalls = list(recalls or [])
        count = max(1, len(recalls))
        return [{"h": f"{active_drive}:{i}", "confidence": 0.7} for i in range(count)]

    def update_baseline(self, dt):
        self.baseline_calls += 1


class StubDecision:
    def __init__(self, relevance=0.7, confidence=0.8):
        self.relevance = float(relevance)
        self.confidence = float(confidence)

    def evaluate_internal(self, active_drive=None, hypotheses=None, recalls=None):
        return {
            "relevance_score": self.relevance,
            "confidence": self.confidence,
        }

    def generate_speech(self, active_drive=None, internal_result=None):
        return f"say:{active_drive}"

    def speech_relevance(self, active_drive=None, internal_result=None):
        return self.relevance


class DecisionProbe:
    def __init__(self):
        self.seen_states = []

    def evaluate(self, hypothetical_state):
        # Internal loop must pass isolated hypothetical snapshots.
        assert "variant_index" in hypothetical_state
        assert "mutated" not in hypothetical_state
        hypothetical_state["mutated"] = True
        self.seen_states.append(dict(hypothetical_state))
        return {"utility": 0.7, "confidence": 0.8, "relevance_score": 0.65}

    def __call__(self, hypothetical_state):
        return self.evaluate(hypothetical_state)


class MetadataCognitive:
    def generate_hypotheses(self, active_drive=None, recalls=None):
        return [{"action": "opaque_token_action", "confidence": 0.6}]

    def get_action_effect(self, action_name):
        if action_name != "opaque_token_action":
            return {"axes": {}, "drives": {}, "active_drive_delta": -0.05}
        return {
            "axes": {"trust": 0.22, "stress": -0.15},
            "drives": {"social_drive": -0.20},
            "active_drive_delta": -0.05,
        }


class FailingAffectiveCore(AffectiveSpace):
    def step(self, external_impulses=None, recall_impulses=None, internal_impulses=None, time_elapsed=1.0):
        if recall_impulses is not None or internal_impulses is not None:
            raise RuntimeError("affect-step-failure")
        return super().step(
            external_impulses=external_impulses,
            recall_impulses=recall_impulses,
            internal_impulses=internal_impulses,
            time_elapsed=time_elapsed,
        )


class TestAutonomousOrganismSpec(unittest.TestCase):
    def _build_agent(
        self,
        *,
        clock,
        drive_system=None,
        energy_system=None,
        hard_limits=None,
        decision=None,
        memory=None,
        internal_trigger_threshold=0.35,
        drive_weights=None,
        speech_governor=None,
        affective_core=None,
    ):
        affect = affective_core or AffectiveSpace()
        memory = memory or StubMemory()
        cognitive = StubCognitive()
        decision = decision or StubDecision()

        agent = AutonomousOrganismAgent(
            affective_core=affect,
            cognitive_core=cognitive,
            decision_engine=decision,
            memory_system=memory,
            drive_system=drive_system,
            energy_system=energy_system,
            hard_limits=hard_limits,
            internal_trigger_threshold=internal_trigger_threshold,
            drive_weights=drive_weights,
            speech_governor=speech_governor,
            time_fn=clock.time,
        )
        return agent, affect, memory

    def test_1_idle_curiosity_growth(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 0.05})
        hard_limits = OrganismHardLimits(drive_thresholds={"curiosity": 1.0})

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            hard_limits=hard_limits,
            internal_trigger_threshold=1.0,
            decision=StubDecision(relevance=0.0, confidence=0.5),
        )

        values = []
        for _ in range(40):
            clock.advance(1.0)
            tick = agent.organism_step(1.0)
            values.append(tick["drives"]["curiosity"])

        for i in range(1, len(values)):
            self.assertGreaterEqual(values[i], values[i - 1] - 1e-9)
        self.assertLessEqual(values[-1], 1.0)

    def test_2_energy_suppression(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 1.0})
        energy_system = EnergySystem(
            energy=1.0,
            cognitive_cost=0.12,
            recovery_rate=0.01,
            low_threshold=0.35,
            floor_threshold=0.2,
        )

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            energy_system=energy_system,
            internal_trigger_threshold=0.05,
        )

        ticks = []
        for _ in range(25):
            clock.advance(1.0)
            ticks.append(agent.organism_step(1.0))

        energies = [t["energy_level"] for t in ticks]
        self.assertLess(energies[-1], energies[0])
        self.assertTrue(any(t["energy_snapshot"]["suppress_internal_cycles"] for t in ticks))
        suppressed_idx = next(
            (i for i, t in enumerate(ticks) if t["energy_snapshot"]["suppress_internal_cycles"]),
            None,
        )
        if suppressed_idx is not None:
            for t in ticks[suppressed_idx + 1 :]:
                if t["energy_snapshot"]["suppress_internal_cycles"]:
                    self.assertFalse(t["internal_cycle_triggered"])

    def test_3_speech_cooldown(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"social_drive": 0.95})
        speech_governor = SpeechGovernor(
            communication_threshold=0.2,
            relevance_minimum=0.1,
            cooldown_seconds=3.0,
            max_speech_events_per_interval=30,
            speech_interval_seconds=30.0,
        )

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            speech_governor=speech_governor,
            internal_trigger_threshold=1.0,
            decision=StubDecision(relevance=1.0, confidence=0.7),
        )

        speech_times = []
        for _ in range(10):
            clock.advance(1.0)
            tick = agent.organism_step(1.0)
            if tick["speech_event"]:
                speech_times.append(tick["timestamp"])

        self.assertGreater(len(speech_times), 0)
        self.assertLessEqual(len(speech_times), 4)
        for i in range(1, len(speech_times)):
            self.assertGreaterEqual(speech_times[i] - speech_times[i - 1], 3.0)

    def test_4_drive_competition(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 0.70, "exploration": 0.70})
        hard_limits = OrganismHardLimits(
            drive_thresholds={"curiosity": 0.3, "exploration": 0.3}
        )
        drive_weights = {"curiosity": 1.0, "exploration": 1.4}

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            hard_limits=hard_limits,
            drive_weights=drive_weights,
            internal_trigger_threshold=0.3,
        )

        clock.advance(1.0)
        tick = agent.organism_step(1.0)
        self.assertTrue(tick["internal_cycle_triggered"])
        self.assertEqual(tick["active_drive"], "exploration")

    def test_5_affect_overload_triggers_regulation_without_new_drive(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 0.05})

        agent, affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            internal_trigger_threshold=1.0,
            decision=StubDecision(relevance=0.0, confidence=0.5),
        )

        # Near-cap affect norm to force overload modulation.
        affect.axes = {axis: 0.9 for axis in affect.axes}
        before_stress = float(affect.axes.get("stress", 0.0))

        clock.advance(1.0)
        tick = agent.organism_step(1.0)
        after_stress = float(getattr(agent.affective_core, "axes", {}).get("stress", 0.0))
        self.assertTrue(bool(tick.get("regulation", {}).get("regulation_active", False)))
        self.assertLess(after_stress, before_stress)
        self.assertNotIn("emotional_discharge", tick["drives"])
        self.assertNotIn("self_reflection", tick["drives"])

    def test_6_memory_recall_limit(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 1.0})
        axes = (
            "valence",
            "arousal",
            "dominance",
            "stress",
            "trust",
            "curiosity",
            "stability",
            "attachment",
        )
        recalls = [{"affect_vector": {axis: 1.0 for axis in axes}} for _ in range(10)]
        memory = StubMemory(recalls=recalls)

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            memory=memory,
            internal_trigger_threshold=0.05,
        )

        clock.advance(1.0)
        tick = agent.organism_step(1.0)
        self.assertTrue(tick["internal_cycle_triggered"])
        self.assertLessEqual(tick["recall_impulse_share"], 0.400001)

        detail = agent.internal_loop.last_result
        self.assertGreater(detail.get("total_impulse_energy", 0.0), 0.0)

    def test_7_long_term_stability(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 0.02, "social_drive": 0.01})
        energy_system = EnergySystem(
            energy=0.15,
            cognitive_cost=0.02,
            recovery_rate=0.05,
            low_threshold=0.05,
            floor_threshold=0.03,
        )

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            energy_system=energy_system,
            internal_trigger_threshold=1.0,
            decision=StubDecision(relevance=0.0, confidence=0.5),
        )

        start_energy = agent.energy_system.energy
        for _ in range(300):
            clock.advance(0.5)
            tick = agent.organism_step(0.5)
            for name, value in tick["drives"].items():
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

        self.assertGreaterEqual(agent.energy_system.energy, start_energy)
        failures = [f["failure_mode"] for f in agent.failure_log]
        self.assertNotIn("infinite_internal_cycle_loop", failures)

        # Per-tick logging contract.
        required = {
            "timestamp",
            "dt",
            "active_drive",
            "energy_level",
            "speech_event",
            "internal_cycle_triggered",
        }
        self.assertTrue(required.issubset(set(agent.tick_history[-1].keys())))

    def test_8_idle_mode_reduces_fatigue_and_load(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 0.02, "social_drive": 0.01})
        hard_limits = OrganismHardLimits(
            drive_thresholds={
                "curiosity": 1.0,
                "social_drive": 1.0,
                "goal_tension": 1.0,
                "exploration": 1.0,
                "energy_need": 1.0,
            }
        )
        energy_system = EnergySystem(energy=0.75, fatigue=0.65, cognitive_cost=0.03, recovery_rate=0.05)

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            hard_limits=hard_limits,
            energy_system=energy_system,
            internal_trigger_threshold=1.0,
            decision=StubDecision(relevance=0.0, confidence=0.5),
        )

        clock.advance(1.0)
        tick = agent.organism_step(1.0)
        self.assertEqual(tick["physiology_mode"], "idle")
        self.assertFalse(tick["internal_cycle_triggered"])
        self.assertFalse(tick["speech_event"])
        self.assertLess(tick["cognitive_load"], 0.3)
        self.assertLess(float(tick["energy_update"]["fatigue_delta"]), 0.0)
        self.assertEqual(float(tick["load_components"]["speech"]), 0.0)

    def test_9_dt_is_clamped_and_logged(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 0.01, "social_drive": 0.01})
        hard_limits = OrganismHardLimits(drive_thresholds={"curiosity": 1.0, "social_drive": 1.0})
        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            hard_limits=hard_limits,
            internal_trigger_threshold=1.0,
            decision=StubDecision(relevance=0.0, confidence=0.5),
        )

        clock.advance(5.0)
        tick = agent.organism_step(5.0)

        self.assertAlmostEqual(float(tick["dt"]), 1.0, places=9)
        self.assertAlmostEqual(float(tick["dt_input"]), 5.0, places=9)
        self.assertTrue(bool(tick["dt_clamped"]))
        self.assertTrue(any(f["failure_mode"] == "dt_anomaly" for f in agent.failure_log))

    def test_10_speech_discharges_social_drive(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"social_drive": 0.95, "curiosity": 0.01})
        speech_governor = SpeechGovernor(
            communication_threshold=0.2,
            relevance_minimum=0.1,
            cooldown_seconds=0.0,
            max_speech_events_per_interval=10,
            speech_interval_seconds=30.0,
        )

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            speech_governor=speech_governor,
            internal_trigger_threshold=1.0,
            decision=StubDecision(relevance=1.0, confidence=0.8),
        )

        before = float(agent.drive_system.drives.get("social_drive", 0.0))
        clock.advance(1.0)
        tick = agent.organism_step(1.0)
        after = float(tick["drives"]["social_drive"])

        self.assertTrue(tick["speech_event"])
        self.assertLess(after, before)
        self.assertGreater(float(tick["load_components"]["speech"]), 0.0)

    def test_11_internal_impulse_failure_is_logged(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 1.0})
        affect = FailingAffectiveCore()

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            internal_trigger_threshold=0.05,
            affective_core=affect,
        )

        clock.advance(1.0)
        tick = agent.organism_step(1.0)

        self.assertTrue(tick["internal_cycle_triggered"])
        self.assertTrue(any(f["failure_mode"] == "internal_affect_apply_failed" for f in agent.failure_log))

    def test_12_drive_taxonomy_removed_meta_drives(self):
        self.assertNotIn("emotional_discharge", DRIVE_NAMES)
        self.assertNotIn("self_reflection", DRIVE_NAMES)
        drives = DriveSystem().snapshot()
        self.assertNotIn("emotional_discharge", drives)
        self.assertNotIn("self_reflection", drives)

    def test_13_internal_loop_output_contract_present(self):
        clock = ClockStub()
        drive_system = DriveSystem(initial_drives={"curiosity": 1.0})

        agent, _affect, _memory = self._build_agent(
            clock=clock,
            drive_system=drive_system,
            internal_trigger_threshold=0.05,
        )

        clock.advance(1.0)
        tick = agent.organism_step(1.0)
        self.assertTrue(tick["internal_cycle_triggered"])
        detail = dict(agent.internal_loop.last_result)
        self.assertIn("best_action", detail)
        self.assertIn("confidence", detail)
        self.assertIn("evaluated_variants", detail)
        self.assertGreaterEqual(int(detail["evaluated_variants"]), 1)
        self.assertIsInstance(detail["best_action"], str)

    def test_14_decision_engine_gets_isolated_hypothetical_states(self):
        probe = DecisionProbe()
        affect = AffectiveSpace()
        recalls = [{"affect_vector": {axis: 0.1 for axis in ("valence", "arousal", "dominance", "stress", "trust", "curiosity", "stability", "attachment")}} for _ in range(3)]
        memory = StubMemory(recalls=recalls)
        cognitive = StubCognitive()
        loop = InternalSimulationLoop(
            affective_core=affect,
            cognitive_core=cognitive,
            decision_engine=probe,
            memory_system=memory,
            max_active_memory_recalls=3,
        )

        result = loop.run_cycle(active_drive="curiosity", now=1.0, dt=1.0)
        self.assertTrue(result["triggered"])
        self.assertGreaterEqual(result["evaluated_variants"], 1)
        self.assertGreaterEqual(len(probe.seen_states), 1)

    def test_15_simulation_uses_action_metadata_effects(self):
        probe = DecisionProbe()
        affect = AffectiveSpace()
        memory = StubMemory(recalls=[{"affect_vector": {"trust": 0.1}}])
        cognitive = MetadataCognitive()
        loop = InternalSimulationLoop(
            affective_core=affect,
            cognitive_core=cognitive,
            decision_engine=probe,
            memory_system=memory,
            max_active_memory_recalls=2,
        )

        result = loop.run_cycle(active_drive="social_drive", now=1.0, dt=1.0)
        self.assertTrue(result["triggered"])
        self.assertGreaterEqual(len(probe.seen_states), 1)
        seen = probe.seen_states[0]
        predicted = dict(seen.get("predicted_effect", {}) or {})
        self.assertAlmostEqual(float((predicted.get("axes", {}) or {}).get("trust", 0.0)), 0.22, places=6)
        self.assertAlmostEqual(float((predicted.get("axes", {}) or {}).get("stress", 0.0)), -0.15, places=6)
        self.assertAlmostEqual(float((predicted.get("drives", {}) or {}).get("social_drive", 0.0)), -0.20, places=6)

    def test_16_heuristic_utility_depends_on_active_drive(self):
        base_state = {
            "drives_before": {"curiosity": 0.9, "social_drive": 0.9},
            "drives": {"curiosity": 0.7, "social_drive": 0.7},
            "axes": {"trust": 0.9, "attachment": 0.8, "curiosity": -0.6, "stress": 0.2, "stability": 0.1},
        }
        utility_social = compute_drive_utility_components(dict(base_state, active_drive="social_drive"))["utility"]
        utility_curiosity = compute_drive_utility_components(dict(base_state, active_drive="curiosity"))["utility"]
        self.assertNotAlmostEqual(float(utility_social), float(utility_curiosity), places=5)

    def test_17_live_drive_snapshot_used_for_simulation_seed(self):
        probe = DecisionProbe()
        loop = InternalSimulationLoop(
            affective_core=AffectiveSpace(),
            cognitive_core=MetadataCognitive(),
            decision_engine=probe,
            memory_system=StubMemory(recalls=[{"affect_vector": {"trust": 0.1}}]),
        )

        result = loop.run_cycle(
            active_drive="social_drive",
            now=1.0,
            dt=1.0,
            live_drives={"social_drive": 0.23, "curiosity": 0.11},
        )
        self.assertTrue(result["triggered"])
        seen = probe.seen_states[0]
        self.assertAlmostEqual(float(seen.get("drives_before", {}).get("social_drive", 0.0)), 0.23, places=6)
        self.assertEqual(str(seen.get("drives_source", "")), "live_snapshot")

    def test_18_tick_history_keeps_latest_and_full_count(self):
        clock = ClockStub()
        agent, _affect, _memory = self._build_agent(clock=clock)
        returned = []
        for index in range(5):
            clock.advance(0.2)
            returned.append(agent.organism_step(0.2))
        self.assertEqual(len(returned), 5)
        self.assertEqual(len(agent.tick_history), 1)
        self.assertEqual(agent.tick_history[-1], returned[-1])
        self.assertEqual(int(agent.snapshot()["tick_count"]), 5)
        self.assertEqual(float(agent.tick_history[-1]["dt_input"]), 0.2)


if __name__ == "__main__":
    unittest.main()
