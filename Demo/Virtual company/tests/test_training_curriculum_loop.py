"""Curriculum cycling in SandboxTrainer."""

from typing import Any, List

from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_world import ProcurementWorldConfig
from nowa_sandbox.sandbox_encoder import SandboxEncoder
from nowa_sandbox.training_loop import SandboxTrainer
from nowa_sandbox.world_curriculum import WorldCurriculum, default_template_quarter


class _StubAgent:
    def __init__(self) -> None:
        self.calls = 0

    def step(self, *args: Any, **kwargs: Any) -> str:
        self.calls += 1
        return "wait_and_monitor"


def _cheap_curriculum() -> WorldCurriculum:
    """Two distinct quarters marked by different unit prices."""
    cur = WorldCurriculum()
    q1 = default_template_quarter(budget=100_000.0)
    q1["offers"][0]["unit_price"] = 1.0
    q2 = default_template_quarter(budget=100_000.0)
    q2["offers"][0]["unit_price"] = 3.0
    # Short days so tests stay fast — overridden via world_config.
    cur.set_quarter(1, q1)
    cur.set_quarter(2, q2)
    return cur


def test_curriculum_cycles_alternate_quarters():
    cur = _cheap_curriculum()
    trainer = SandboxTrainer(
        _StubAgent(),
        SandboxEncoder(),
        ProcurementFitnessEvaluator(stage="1a"),
        sleep_every_n_days=99,
    )
    cfg = ProcurementWorldConfig(days_per_quarter=2, seed=1, n_products=1, n_suppliers=1)
    result = trainer.run_curriculum_cycles(
        cur,
        world_config=cfg,
        stop_on_graduation=False,
        max_cycles=2,
    )
    assert len(result.quarters) == 4
    cur_qs = [q.world_summary.get("curriculum_quarter") for q in result.quarters]
    cycles = [q.world_summary.get("cycle") for q in result.quarters]
    assert cur_qs == [1, 2, 1, 2]
    assert cycles == [1, 1, 2, 2]
    prices = []
    for q in result.quarters:
        offers = (q.world_summary.get("entities") or {}).get("offers") or []
        prices.append(offers[0]["unit_price"])
    assert prices == [1.0, 3.0, 1.0, 3.0]


def test_soft_stop_callback_halts():
    cur = _cheap_curriculum()
    trainer = SandboxTrainer(
        _StubAgent(),
        SandboxEncoder(),
        ProcurementFitnessEvaluator(stage="1a"),
        sleep_every_n_days=99,
    )
    cfg = ProcurementWorldConfig(days_per_quarter=2, seed=1)
    stop_after: List[int] = []

    def should_stop() -> bool:
        # Stop before starting the 3rd step.
        return len(stop_after) >= 2

    def on_progress(q_idx: int, total: int) -> None:
        stop_after.append(q_idx)

    result = trainer.run_curriculum_cycles(
        cur,
        world_config=cfg,
        stop_on_graduation=False,
        max_cycles=5,
        should_stop=should_stop,
        progress_callback=on_progress,
    )
    # First two steps run; third sees should_stop before body — at most 2.
    assert len(result.quarters) <= 2
