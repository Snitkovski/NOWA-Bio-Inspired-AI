"""Issue #53: seeded colony trajectories stay put, and the pygame loop still advances.

The dense episode layout and the render cap are implementation details.
Two colonies with the same seed must take the same actions, and one 2.5 s
tick must match ten 0.25 s ticks. The short GUI run checks that painting
at a capped rate does not stall the simulation clock.
"""

from __future__ import annotations

import os
import random

import pytest

from colony_agent import ChinchillaAgent
from colony_gui.app import run_pygame_demo
from genome import GenomeVector
from simulation_runner import SimulationRunner


def _colony(seed: int, count: int, journal: str) -> SimulationRunner:
    rng = random.Random(seed)
    runner = SimulationRunner(death_journal_path=journal)
    for index in range(count):
        runner.add_agent(
            ChinchillaAgent(
                sex="F" if index % 2 == 0 else "M",
                name=f"c{index}",
                agent_id=f"issue53-{seed}-{index}",
                rng_seed=seed * 100 + index,
                genome=GenomeVector.random(rng),
            )
        )
    return runner


def _fingerprint(runner: SimulationRunner) -> list[tuple]:
    rows = []
    for agent in runner.agents:
        hip = agent.hippocampus
        signatures = tuple(
            (
                tuple(sorted(sig.feature_set)),
                round(float(sig.activation_weight), 5),
                round(float(exp.activation_energy), 5),
                round(float(exp.reward), 5),
            )
            for exp, sig in zip(hip.experiences, hip.signatures)
        )
        rows.append(
            (
                agent.position,
                agent.current_action,
                round(float(agent.energy), 5),
                round(float(agent.hunger), 5),
                round(float(agent.thirst), 5),
                round(float(getattr(agent, "stress", 0.0)), 5),
                len(hip.experiences),
                signatures,
            )
        )
    return rows


def _run(seed: int, dt: float, duration_s: float, journal: str, count: int = 3) -> list[tuple]:
    state = random.getstate()
    random.seed(seed)
    try:
        runner = _colony(seed, count, journal)
        runner.run_for(duration_s, dt=dt)
        return _fingerprint(runner)
    finally:
        random.setstate(state)


def _assert_same_trajectory(left: list[tuple], right: list[tuple]) -> None:
    """Actions and episodes match. Floats tolerate the wall-clock decay gap."""
    assert len(left) == len(right)
    for one, other in zip(left, right):
        assert one[0] == other[0]
        assert one[1] == other[1]
        assert one[6] == other[6]
        for value, expected in zip(one[2:6], other[2:6]):
            assert value == pytest.approx(expected, abs=1e-4)
        assert len(one[7]) == len(other[7])
        for episode, reference in zip(one[7], other[7]):
            assert episode[0] == reference[0]
            assert episode[1] == pytest.approx(reference[1], abs=1e-4)
            assert episode[2] == pytest.approx(reference[2], abs=1e-4)
            assert episode[3] == pytest.approx(reference[3], abs=1e-4)


def test_same_seed_colony_trajectory_matches(tmp_path) -> None:
    left = _run(7, 0.25, 2.5, str(tmp_path / "a.jsonl"))
    right = _run(7, 0.25, 2.5, str(tmp_path / "b.jsonl"))
    assert left
    _assert_same_trajectory(left, right)


def test_quarter_second_steps_match_one_accelerated_tick(tmp_path) -> None:
    fine = _run(7, 0.25, 2.5, str(tmp_path / "fine.jsonl"))
    fast = _run(7, 2.5, 2.5, str(tmp_path / "fast.jsonl"))
    _assert_same_trajectory(fine, fast)


def test_capped_pygame_loop_advances_simulation(tmp_path, monkeypatch) -> None:
    pygame = pytest.importorskip("pygame")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if pygame.get_init():
        pygame.quit()
    runner = _colony(3, 2, str(tmp_path / "gui.jsonl"))
    before = float(runner.sim_time)
    profile: dict[str, float] = {}
    run_pygame_demo(runner=runner, speed=10.0, wall_s=0.6, frame_profile=profile)
    assert float(runner.sim_time) > before
    assert profile["paints"] >= 1.0
    assert profile["sim_advanced_s"] > 0.0
    assert profile["loop_wall_s"] > 0.0
