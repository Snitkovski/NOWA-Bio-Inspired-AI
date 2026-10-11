#!/usr/bin/env python3
"""Run a NOWA agent for a few episodes. Standard library only.

From a clean clone, at the repository root:

    python tools/sixty_seconds.py
"""

from __future__ import annotations

import logging
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

logging.disable(logging.WARNING)

from agent import Agent  # noqa: E402
from affective_space import AXES  # noqa: E402
from cortex import CortexMemory  # noqa: E402
from epigenome import EpigenomeSnapshot  # noqa: E402
from genome import GENE_KEYS, GenomeVector  # noqa: E402
from hippocampus import NOWAHippocampus  # noqa: E402
from selector import ActionSelector  # noqa: E402
from sleep import SleepManager  # noqa: E402


EPISODES = (
    (["context:forage", "event:found_hay"], 0.85, 0.15, 0.0),
    (["context:forage", "event:ate"], 0.70, 0.05, 0.0),
    (["context:shadow", "event:predator"], -0.80, 0.40, 0.75),
    (["context:safe", "event:groom"], 0.45, 0.10, 0.05),
    (["context:novel", "event:object"], 0.15, 0.90, 0.10),
)


def _fmt_axes(agent: Agent) -> str:
    axes = getattr(agent.affective_space, "axes", {}) or {}
    parts = [f"{name}={float(axes.get(name, 0.0)):+.2f}" for name in AXES]
    return "  ".join(parts)


def _fmt_modulators(agent: Agent) -> str:
    nm = agent.neuromodulators
    return (
        f"dopamine={nm.dopamine:.2f}  serotonin={nm.serotonin:.2f}  "
        f"norepinephrine={nm.norepinephrine:.2f}  acetylcholine={nm.acetylcholine:.2f}  "
        f"cortisol={nm.cortisol:.2f}"
    )


def main() -> int:
    actions = ["approach", "eat", "rest", "explore", "hide"]
    hippocampus = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions)
    sleep_manager = SleepManager(hippocampus, cortex)
    agent = Agent(hippocampus, cortex, selector, sleep_manager=sleep_manager)

    print("NOWA — one agent, awake. No backprop, no language model.")
    print(f"affect (8): {_fmt_axes(agent)}")
    print(f"modulators: {_fmt_modulators(agent)}")
    print()

    for index, (context, reward, novelty, conflict) in enumerate(EPISODES, start=1):
        action = agent.step(
            context,
            reward=reward,
            novelty=novelty,
            conflict=conflict,
        )
        print(
            f"wake {index}: context={context[0]}  reward={reward:+.2f}  "
            f"action={action}"
        )

    print()
    print("Sleep. Slow memory consolidates here; waking did not train weights.")
    stats = agent.sleep(cycles=1)
    cycles = stats.get("cycles", stats.get("sleep_cycles", 1)) if isinstance(stats, dict) else 1
    print(f"sleep cycles reported: {cycles}")
    print(f"affect (8): {_fmt_axes(agent)}")
    print(f"modulators: {_fmt_modulators(agent)}")
    print(f"episodes stored: {len(hippocampus.experiences)}")

    rng = random.Random(7)
    mother = GenomeVector.random(rng)
    father = GenomeVector.random(rng)
    daughter, son = mother.crossover(father, mode="uniform", rng=rng)
    daughter = daughter.mutate(rate=0.08, rng=rng)
    snapshot = EpigenomeSnapshot.extract(
        cortex_patterns=[
            {
                "context_signature": "context:forage",
                "action": "eat",
                "strength": 0.8,
                "reinforcement_count": 3,
            }
        ],
        action_metadata={},
        value_profiles={},
        source_generation=0,
        source_lineage_id="demo",
        min_reinforcement=2,
        min_stability=0.0,
        min_confirmation=0.0,
    )
    print()
    print(
        f"genome: {len(GENE_KEYS)} genes. "
        f"offspring generation={daughter.generation} "
        f"(sister={son.generation}), "
        f"one gene nm_da_ne_weight daughter={daughter.genes['nm_da_ne_weight']:+.3f} "
        f"son={son.genes['nm_da_ne_weight']:+.3f}"
    )
    print(
        f"epigenome: {len(snapshot.patterns)} consolidated pattern(s) "
        "eligible to pass to offspring."
    )
    print()
    print("Next: PYTHONPATH=\"Demo/Colony chinchillas/src\" python3 -m colony_gui --headless --agents 4 --duration 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
