#!/usr/bin/env python3
"""Run a NOWA agent for a few episodes. Standard library only.

From a clean clone, at the repository root:

    python tools/sixty_seconds.py
"""

from __future__ import annotations

import argparse
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
from gui_i18n import action_label, axis_label, resolve_lang, set_language, tr  # noqa: E402


EPISODES = (
    (["context:forage", "event:found_hay"], 0.85, 0.15, 0.0),
    (["context:forage", "event:ate"], 0.70, 0.05, 0.0),
    (["context:shadow", "event:alarm_call"], -0.80, 0.40, 0.75),
    (["context:safe", "event:groom"], 0.45, 0.10, 0.05),
    (["context:novel", "event:object"], 0.15, 0.90, 0.10),
)


def _fmt_axes(agent: Agent) -> str:
    axes = getattr(agent.affective_space, "axes", {}) or {}
    parts = [f"{axis_label(name)}={float(axes.get(name, 0.0)):+.2f}" for name in AXES]
    return "  ".join(parts)


def _fmt_modulators(agent: Agent) -> str:
    nm = agent.neuromodulators
    return (
        f"dopamine={nm.dopamine:.2f}  serotonin={nm.serotonin:.2f}  "
        f"norepinephrine={nm.norepinephrine:.2f}  acetylcholine={nm.acetylcholine:.2f}  "
        f"cortisol={nm.cortisol:.2f}"
    )


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    preview = None
    if "--lang" in raw:
        index = raw.index("--lang")
        if index + 1 < len(raw):
            preview = raw[index + 1]
    set_language(resolve_lang(preview))
    parser = argparse.ArgumentParser(description=tr("Run a short NOWA agent episode"))
    parser.add_argument(
        "--lang",
        choices=("en", "ru"),
        default=None,
        help=tr("UI language. Overrides NOWA_LANG."),
    )
    args = parser.parse_args(argv)
    set_language(resolve_lang(args.lang))
    actions = ["approach", "eat", "rest", "explore", "hide"]
    hippocampus = NOWAHippocampus()
    cortex = CortexMemory()
    selector = ActionSelector(actions)
    sleep_manager = SleepManager(hippocampus, cortex)
    agent = Agent(hippocampus, cortex, selector, sleep_manager=sleep_manager)

    print(tr("NOWA — one agent, awake. No backprop, no language model."))
    print(tr("affect (8): {axes}", axes=_fmt_axes(agent)))
    print(tr("modulators: {mods}", mods=_fmt_modulators(agent)))
    print()

    for index, (context, reward, novelty, conflict) in enumerate(EPISODES, start=1):
        action = agent.step(
            context,
            reward=reward,
            novelty=novelty,
            conflict=conflict,
        )
        print(
            tr(
                "wake {index}: context={context}  reward={reward:+.2f}  action={action}",
                index=index,
                context=context[0],
                reward=reward,
                action=action_label(action),
            )
        )

    print()
    print(tr("Sleep. Slow memory consolidates here; waking did not train weights."))
    stats = agent.sleep(cycles=1)
    cycles = stats.get("cycles", stats.get("sleep_cycles", 1)) if isinstance(stats, dict) else 1
    print(tr("sleep cycles reported: {cycles}", cycles=cycles))
    print(tr("affect (8): {axes}", axes=_fmt_axes(agent)))
    print(tr("modulators: {mods}", mods=_fmt_modulators(agent)))
    print(tr("episodes stored: {n}", n=len(hippocampus.experiences)))

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
        tr(
            "genome: {n} genes. offspring generation={generation} (sister={sister}), one gene neuromodulator DA/NE weight ({gene}) daughter={daughter:+.3f} son={son:+.3f}",
            n=len(GENE_KEYS),
            generation=daughter.generation,
            sister=son.generation,
            gene="nm_da_ne_weight",
            daughter=daughter.genes["nm_da_ne_weight"],
            son=son.genes["nm_da_ne_weight"],
        )
    )
    print(
        tr(
            "epigenome: {n} consolidated pattern(s) eligible to pass to offspring.",
            n=len(snapshot.patterns),
        )
    )
    print()
    print(tr("Next: PYTHONPATH=\"Demo/Colony chinchillas/src\" python3 -m colony_gui --headless --agents 4 --duration 2"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
