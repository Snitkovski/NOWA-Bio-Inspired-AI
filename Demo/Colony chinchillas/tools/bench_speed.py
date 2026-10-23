#!/usr/bin/env python3
"""Achieved colony speed at 1x and 10x.

Drives the same catch-up as the pygame frame loop: wall time accumulates,
each simulation tick is ``sim_step * speed``, and a slow tick may widen
``sim_step`` up to 0.25s. The reported multiplier is simulated seconds
divided by wall seconds, which is what the HUD calls "actual x".

The colony is filled until every hippocampus is at capacity (or the warmup
budget runs out) so the number is the sustained rate, not the empty-memory
burst.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

DEMO_SRC = Path(__file__).resolve().parents[1] / "src"
if str(DEMO_SRC) not in sys.path:
    sys.path.insert(0, str(DEMO_SRC))

from colony_gui.app import (  # noqa: E402
    SIM_ACCUMULATOR_MAX_STEPS,
    SIM_FRAME_DT_CAP_S,
    SIM_MAX_CATCHUP_STEPS,
    _adaptive_sim_step_s,
    _apply_sim_load_adaptation,
    build_demo_runner,
)
from colony_gui.colony_gui import ColonyGUI  # noqa: E402


def _memory_size(runner) -> int:
    return max(len(agent.hippocampus.experiences) for agent in runner.agents)


def _capacity(runner) -> int:
    return max(int(agent.hippocampus.max_experiences) for agent in runner.agents)


def warm_until_full(runner, wall_budget_s: float) -> None:
    """Advance at the load-adapted 10x step until memory is full."""
    deadline = time.perf_counter() + max(0.0, wall_budget_s)
    while _memory_size(runner) < _capacity(runner) and time.perf_counter() < deadline:
        runner.tick(2.5)


def measure(runner, speed: float, wall_s: float) -> dict[str, float]:
    """Run the GUI catch-up for ``wall_s`` seconds at ``speed``."""
    gui = ColonyGUI(runner)
    gui.speed = float(speed)
    gui._update_snapshot()
    accumulator = 0.0
    cost_ema = 0.0
    sim_start = float(runner.sim_time)
    wall_start = time.perf_counter()
    deadline = wall_start + max(0.05, wall_s)
    previous = wall_start
    frames = 0
    ticks = 0
    while True:
        now = time.perf_counter()
        if now >= deadline:
            break
        raw_frame_dt = max(0.0, now - previous)
        previous = now
        frames += 1
        if raw_frame_dt <= 0.0:
            continue
        sim_frame_dt = min(raw_frame_dt, SIM_FRAME_DT_CAP_S)
        sim_before = float(runner.sim_time)
        accumulator += sim_frame_dt
        step = _apply_sim_load_adaptation(
            _adaptive_sim_step_s(len(runner.agents)),
            cost_ema,
        )
        taken = 0
        while accumulator >= step and taken < SIM_MAX_CATCHUP_STEPS:
            started = time.perf_counter()
            gui._sim_tick(step)
            cost = time.perf_counter() - started
            cost_ema = cost if cost_ema <= 0.0 else (cost_ema * 0.9) + (cost * 0.1)
            accumulator -= step
            taken += 1
            ticks += 1
        if taken >= SIM_MAX_CATCHUP_STEPS:
            accumulator = min(accumulator, step)
        accumulator = min(accumulator, step * SIM_ACCUMULATOR_MAX_STEPS)
        gui.note_sim_pace(
            real_dt=raw_frame_dt,
            sim_advanced=float(runner.sim_time) - sim_before,
        )
        gui._update_snapshot()
    wall = time.perf_counter() - wall_start
    simulated = float(runner.sim_time) - sim_start
    return {
        "speed": float(speed),
        "wall_s": wall,
        "sim_s": simulated,
        "achieved": (simulated / wall) if wall > 0.0 else 0.0,
        "hud": float(gui.achieved_speed_ratio) * float(speed),
        "frames": float(frames),
        "ticks": float(ticks),
        "memory": float(_memory_size(runner)),
    }


def format_row(row: dict[str, float]) -> str:
    return (
        f"{row['speed']:.0f}x: achieved {row['achieved']:.2f}x "
        f"(sim {row['sim_s']:.1f}s / wall {row['wall_s']:.1f}s, "
        f"hud x{row['hud']:.2f}, ticks {int(row['ticks'])}, "
        f"memory {int(row['memory'])})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Colony achieved speed at 1x and 10x")
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--measure-wall", type=float, default=8.0)
    parser.add_argument("--warmup-wall", type=float, default=60.0)
    args = parser.parse_args()

    runner = build_demo_runner(max(1, args.agents))
    started = time.perf_counter()
    warm_until_full(runner, args.warmup_wall)
    print(
        f"warmup {time.perf_counter() - started:.1f}s "
        f"sim={runner.sim_time:.0f}s memory={_memory_size(runner)}/{_capacity(runner)}",
        flush=True,
    )
    for speed in (1.0, 10.0):
        print(format_row(measure(runner, speed, args.measure_wall)), flush=True)


if __name__ == "__main__":
    main()
