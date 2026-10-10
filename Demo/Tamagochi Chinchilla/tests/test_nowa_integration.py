import sys
import uuid
import shutil
from pathlib import Path


# Add demo src directory to path
SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def test_agent_wires_nowa_layers():
    from main import ChinchillaAgent

    demo_dir = Path(__file__).parent.parent
    agent = ChinchillaAgent(demo_dir=str(demo_dir), use_pygame=False, use_gui=False)

    assert agent.affect_space is not None
    assert agent.neuromod is not None
    assert agent.wakefulness is not None
    assert agent.drives is not None
    assert agent.bg_gate is not None
    assert agent.bg_channels
    assert agent.sleep_manager is not None

    agent.running = True
    for _ in range(5):
        agent.sim_step(0.1)
    # Backward-compatible API (regression): step() should exist.
    agent.step(0.1)

    # Debug lines should never crash (regression for KeyError 'valence')
    lines = agent._build_debug_lines()
    assert isinstance(lines, list)
    assert any("Valence" in line for line in lines)

    drives = agent.drives.snapshot()
    assert "energy_need" in drives
    assert "curiosity" in drives

    # Candidate chains produced by BG pipeline
    candidates = agent._build_candidate_chains(drives)
    assert isinstance(candidates, list)
    assert len(candidates) <= 3

    # Persistence roundtrip using repo root saves to avoid OS temp ACL issues
    repo_saves = demo_dir.parent.parent / "saves"
    repo_saves.mkdir(parents=True, exist_ok=True)
    tmp_path = repo_saves / f"nowa_test_{uuid.uuid4().hex[:8]}"
    tmp_save_dir = tmp_path / "saves"
    tmp_save_dir.mkdir(parents=True, exist_ok=True)

    try:
        agent.saves_dir = tmp_save_dir
        agent.save_nowa_state()
        state_path = tmp_save_dir / "nowa_state.json"
        assert state_path.exists()

        # mutate and restore
        agent.wakefulness.wakefulness = 0.62
        agent.drives.set_drive("curiosity", 0.71)
        agent.save_nowa_state()

        agent.neuromod.dopamine = 0.99
        agent.wakefulness.wakefulness = 0.01
        agent.drives.set_drive("curiosity", 0.02)
        loaded = agent.load_nowa_state()
        assert loaded is True
        assert agent.neuromod.dopamine != 0.99
        assert abs(agent.wakefulness.wakefulness - 0.62) < 1e-6
        assert abs(agent.drives.snapshot().get("curiosity", 0.0) - 0.71) < 1e-6
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_self_model_timer_and_value_path_regression():
    """
    Regression: SelfModel periodic introspection must not reference
    chain-local variables (value_state_before/after, prev_chain).
    """
    from main import ChinchillaAgent

    demo_dir = Path(__file__).parent.parent
    agent = ChinchillaAgent(demo_dir=str(demo_dir), use_pygame=False, use_gui=False)
    agent.running = True

    # Cross the 30s introspection window where this regression was triggered.
    for _ in range(320):
        agent.sim_step(0.1)

    assert isinstance(agent._self_model_report, dict)


def test_snapshot_candidate_path_does_not_mutate_arbitrator_ema():
    """
    Regression: get_state_snapshot() calls _build_candidate_chains(update_runtime=False)
    and must not mutate DecisionArbitrator runtime EMA fields.
    """
    from main import ChinchillaAgent

    demo_dir = Path(__file__).parent.parent
    agent = ChinchillaAgent(demo_dir=str(demo_dir), use_pygame=False, use_gui=False)
    agent.running = True

    # Prime runtime arbitration state once via normal runtime update path.
    drives = agent.drives.snapshot()
    _ = agent._build_candidate_chains(drives, update_runtime=True)

    ema_before = float(getattr(agent.decision_arbitrator, "_uncertainty_ema", 0.0))
    decision_before = dict(agent._last_decision_arbitration_output or {})

    _ = agent.get_state_snapshot()

    ema_after = float(getattr(agent.decision_arbitrator, "_uncertainty_ema", 0.0))
    decision_after = dict(agent._last_decision_arbitration_output or {})

    assert ema_after == ema_before
    assert decision_after == decision_before

