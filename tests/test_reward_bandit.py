"""Regression: a contextual bandit must learn from reward.

Refs #32. Two contexts, three actions, fixed ±1 reward. The final policy
has to beat chance for every action mapping and every PYTHONHASHSEED.
On the unfixed core the first salted hash pick is locked by outcome-blind
frequency pressure, so at least one context stays at zero.
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from agent import Agent
from cortex import CortexMemory
from hippocampus import NOWAHippocampus
from intent_memory import IntentMemory
from selector import ActionSelector
from sleep import SleepManager

_CHANCE = 1.0 / 3.0
_MIN_ACCURACY = 0.60
_MIN_CONTEXT_ACCURACY = 0.50
_HASH_SEEDS = ("0", "1", "7")
_CASES = (
    {
        "actions": ("red", "green", "blue"),
        "best": {"north": "red", "south": "green"},
    },
    {
        "actions": ("red", "green", "blue"),
        "best": {"north": "blue", "south": "red"},
    },
    {
        "actions": ("blue", "red", "green"),
        "best": {"north": "green", "south": "blue"},
    },
)


def _parse_case(spec: str) -> dict:
    actions_raw, best_raw = spec.split(";")
    actions = tuple(part for part in actions_raw.split(",") if part)
    best = {}
    for item in best_raw.split(","):
        context, action = item.split(":")
        best[context] = action
    return {"actions": actions, "best": best}


def _case_spec(case: dict) -> str:
    actions = ",".join(case["actions"])
    best = ",".join(f"{context}:{action}" for context, action in case["best"].items())
    return f"{actions};{best}"


def _build_agent(actions, seed: int) -> Agent:
    hippocampus = NOWAHippocampus(max_experiences=40)
    cortex = CortexMemory()
    intent_memory = IntentMemory()
    sleep_manager = SleepManager(hippocampus, cortex, intent_memory)
    selector = ActionSelector(actions=list(actions))
    agent = Agent(
        hippocampus,
        cortex,
        selector,
        sleep_manager,
        intent_memory,
    )
    random.seed(seed)
    rng = getattr(agent, "_rng", None)
    if rng is not None and hasattr(rng, "seed"):
        rng.seed(seed)
    return agent


def run_contextual_bandit(case: dict, seed: int = 0, train_trials: int = 240, eval_trials: int = 80) -> dict:
    """Train on a fixed ±1 contextual bandit and score the following choices."""
    actions = list(case["actions"])
    best = dict(case["best"])
    contexts = list(best.keys())
    agent = _build_agent(actions, seed)

    def _episode(context: str) -> bool:
        action = agent.step([context], terminal=True)
        correct = action == best[context]
        rating = 2 if correct else -2
        agent.apply_feedback_to_last_experience(
            rating,
            context_events=[context],
            action_id=action,
        )
        return bool(correct)

    for trial in range(train_trials):
        context = contexts[trial % len(contexts)]
        _episode(context)

    per_context = {context: {"hits": 0, "total": 0} for context in contexts}
    hits = 0
    for trial in range(eval_trials):
        context = contexts[trial % len(contexts)]
        correct = _episode(context)
        hits += int(correct)
        per_context[context]["hits"] += int(correct)
        per_context[context]["total"] += 1

    accuracy = hits / float(eval_trials)
    context_accuracy = {
        context: (bucket["hits"] / float(bucket["total"])) if bucket["total"] else 0.0
        for context, bucket in per_context.items()
    }
    return {
        "accuracy": accuracy,
        "per_context": context_accuracy,
        "min_context": min(context_accuracy.values()) if context_accuracy else 0.0,
        "chance": _CHANCE,
        "best": best,
        "actions": actions,
    }


def _assert_beats_chance(report: dict) -> None:
    assert report["accuracy"] >= _MIN_ACCURACY, (
        f"bandit accuracy {report['accuracy']:.3f} is not above chance "
        f"({report['chance']:.3f}); per context {report['per_context']}; "
        f"mapping {report['best']}"
    )
    assert report["min_context"] >= _MIN_CONTEXT_ACCURACY, (
        f"a context stayed near the locked first action: {report['per_context']}; "
        f"mapping {report['best']}"
    )


def test_contextual_bandit_beats_chance_for_every_mapping_and_hash_seed():
    """Accuracy stays above chance for every mapping and PYTHONHASHSEED."""
    if os.environ.get("NOWA_BANDIT_WORKER") == "1":
        case = _parse_case(os.environ["NOWA_BANDIT_CASE"])
        seed = int(os.environ.get("NOWA_BANDIT_SEED", "0"))
        _assert_beats_chance(run_contextual_bandit(case, seed=seed))
        return

    repo_root = Path(__file__).resolve().parents[1]
    failures = []
    for hash_seed in _HASH_SEEDS:
        for case in _CASES:
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = hash_seed
            env["NOWA_BANDIT_WORKER"] = "1"
            env["NOWA_BANDIT_CASE"] = _case_spec(case)
            env["NOWA_BANDIT_SEED"] = "0"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/test_reward_bandit.py::test_contextual_bandit_beats_chance_for_every_mapping_and_hash_seed",
                    "-q",
                    "--tb=short",
                ],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                tail = (completed.stdout or "") + "\n" + (completed.stderr or "")
                failures.append(
                    f"PYTHONHASHSEED={hash_seed} mapping={case['best']}\n{tail[-2000:]}"
                )

    assert not failures, "bandit failed to beat chance:\n\n" + "\n---\n".join(failures)


def test_bandit_worker_rejects_incomplete_case_spec():
    with pytest.raises(ValueError):
        _parse_case("only-actions")


def test_bootstrap_prior_is_seeded_and_does_not_single_out_one_action():
    """C02: tie-break comes from sha256 + the agent RNG, not hash()."""
    left = _build_agent(("red", "green", "blue"), seed=11)
    right = _build_agent(("red", "green", "blue"), seed=11)
    actions = ("red", "green", "blue")
    left_priors = [left._stable_bootstrap_prior("north", name) for name in actions]
    right_priors = [right._stable_bootstrap_prior("north", name) for name in actions]
    assert left_priors == right_priors
    assert max(left_priors) - min(left_priors) < 0.02
    other = _build_agent(("red", "green", "blue"), seed=12)
    other_priors = [other._stable_bootstrap_prior("north", name) for name in actions]
    assert other_priors != left_priors
