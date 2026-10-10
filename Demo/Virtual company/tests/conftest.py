"""Shared fixtures for sandbox tests."""

import random
import sys
from pathlib import Path

import pytest


DEMO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEMO_ROOT.parents[1]

for _path in (DEMO_ROOT / "src", REPO_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_world import ProcurementWorld, ProcurementWorldConfig
from nowa_sandbox.sandbox_agent_factory import create_procurement_agent
from nowa_sandbox.sandbox_encoder import SandboxEncoder


def pytest_configure(config):
    """Register markers here too, so the suite is clean from any rootdir."""
    config.addinivalue_line(
        "markers", "slow: long-running end-to-end sandbox runs"
    )
    config.addinivalue_line(
        "markers", "perf: performance budget checks from spec section 24"
    )
    config.addinivalue_line(
        "markers", "tk: requires a usable Tk/Tcl runtime"
    )


def _tkinter_is_usable() -> bool:
    cached = getattr(_tkinter_is_usable, "_cached", None)
    if cached is not None:
        return cached
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except Exception:
        _tkinter_is_usable._cached = False
        return False
    _tkinter_is_usable._cached = True
    return True


def pytest_collection_modifyitems(config, items):
    if _tkinter_is_usable():
        return
    skip_tk = pytest.mark.skip(
        reason="Tk/Tcl runtime is not usable in this environment"
    )
    for item in items:
        if item.get_closest_marker("tk"):
            item.add_marker(skip_tk)


@pytest.fixture
def small_world_config():
    return ProcurementWorldConfig(
        initial_budget=10_000.0,
        n_products=3,
        n_suppliers=2,
        days_per_quarter=30,
        seed=42,
    )


@pytest.fixture
def small_world(small_world_config):
    return ProcurementWorld(small_world_config)


@pytest.fixture
def encoder():
    return SandboxEncoder()


@pytest.fixture
def fitness_evaluator():
    return ProcurementFitnessEvaluator()


@pytest.fixture
def sandbox_agent():
    return create_procurement_agent(agent_id="test_agent", rng=random.Random(42))


@pytest.fixture
def seeded_agent():
    return create_procurement_agent(
        agent_id="seeded_agent", rng=random.Random(42), seed_intuition=True
    )


@pytest.fixture
def bankrupt_world():
    """A world driven into bankruptcy purely by holding costs."""
    config = ProcurementWorldConfig(
        initial_budget=1.0, n_products=2, n_suppliers=1,
        days_per_quarter=10, seed=1,
    )
    world = ProcurementWorld(config)
    for _ in range(300):
        world.tick()
        if world.bankrupt:
            break
    return world
