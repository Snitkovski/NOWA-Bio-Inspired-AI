"""Tests for sandbox training persistence (spec section 22)."""

import random

import pytest

from nowa_sandbox.procurement_fitness import ProcurementFitnessEvaluator
from nowa_sandbox.procurement_world import ProcurementWorldConfig
from nowa_sandbox.sandbox_agent_factory import (
    create_procurement_agent,
    seed_procurement_intuition,
)
from nowa_sandbox.sandbox_checkpoint import (
    CheckpointError,
    load_checkpoint,
    restore_agent,
    save_checkpoint,
)
from nowa_sandbox.sandbox_encoder import SandboxEncoder
from nowa_sandbox.training_loop import SandboxTrainer, SandboxTrainingResult


SMALL_WORLD = ProcurementWorldConfig(
    initial_budget=10_000.0, n_products=2, n_suppliers=2,
    days_per_quarter=10, seed=1,
)


def _trainer(agent):
    return SandboxTrainer(
        agent, SandboxEncoder(), ProcurementFitnessEvaluator(), sleep_every_n_days=5
    )


class TestPersistence:

    def test_checkpoint_roundtrip_preserves_hippocampus_size(
        self, sandbox_agent, tmp_path
    ):
        seed_procurement_intuition(sandbox_agent, repeats=2)
        expected = len(sandbox_agent.hippocampus.experiences)
        assert expected > 0

        path = save_checkpoint(
            tmp_path / "ckpt.pkl", sandbox_agent, SandboxTrainingResult()
        )
        checkpoint = load_checkpoint(path)

        fresh = create_procurement_agent("restored", rng=random.Random(7))
        assert restore_agent(checkpoint, fresh) is True
        assert len(fresh.hippocampus.experiences) == expected

    def test_resume_continues_from_correct_quarter(self, sandbox_agent, tmp_path):
        trainer = _trainer(sandbox_agent)
        first = trainer.run_quarters(
            n_quarters=2, world_config=SMALL_WORLD, stop_on_graduation=False
        )
        path = save_checkpoint(tmp_path / "ckpt.pkl", sandbox_agent, first)

        checkpoint = load_checkpoint(path)
        assert checkpoint.last_quarter == 2
        assert checkpoint.next_quarter == 3

        resumed_agent = create_procurement_agent("resumed", rng=random.Random(7))
        restore_agent(checkpoint, resumed_agent)
        second = _trainer(resumed_agent).run_quarters(
            n_quarters=2, world_config=SMALL_WORLD, stop_on_graduation=False,
            initial_result=checkpoint.result,
        )
        assert len(second.quarters) == 4
        assert [q.quarter_index for q in second.quarters] == [1, 2, 3, 4]

    def test_resume_of_already_graduated_agent_is_flagged(
        self, sandbox_agent, tmp_path
    ):
        result = SandboxTrainingResult(graduated=True, graduated_at_quarter=3)
        path = save_checkpoint(tmp_path / "grad.pkl", sandbox_agent, result)
        checkpoint = load_checkpoint(path)
        assert checkpoint.graduated is True
        assert checkpoint.graduated_at_quarter == 3
        assert "graduated at quarter 3" in checkpoint.summary()

    def test_checkpoint_stores_genome(self, sandbox_agent, tmp_path):
        path = save_checkpoint(
            tmp_path / "genome.pkl", sandbox_agent, SandboxTrainingResult()
        )
        assert load_checkpoint(path).genome is not None

    def test_checkpoint_stores_rng_state(self, sandbox_agent, tmp_path):
        rng = random.Random(11)
        rng.random()
        path = save_checkpoint(
            tmp_path / "rng.pkl", sandbox_agent, SandboxTrainingResult(), rng=rng
        )
        checkpoint = load_checkpoint(path)

        restored = random.Random()
        restored.setstate(checkpoint.rng_state)
        assert restored.random() == rng.random()

    def test_checkpoint_preserves_quarter_history(self, sandbox_agent, tmp_path):
        trainer = _trainer(sandbox_agent)
        result = trainer.run_quarters(
            n_quarters=2, world_config=SMALL_WORLD, stop_on_graduation=False
        )
        path = save_checkpoint(tmp_path / "hist.pkl", sandbox_agent, result)
        loaded = load_checkpoint(path).result
        assert len(loaded.quarters) == 2
        assert loaded.quarters[0].fitness.as_dict() == result.quarters[0].fitness.as_dict()

    def test_checkpoint_does_not_persist_world_state(self, sandbox_agent, tmp_path):
        """Constraint V1: a quarter's world is never carried forward."""
        trainer = _trainer(sandbox_agent)
        result = trainer.run_quarters(n_quarters=1, world_config=SMALL_WORLD)
        path = save_checkpoint(tmp_path / "world.pkl", sandbox_agent, result)
        checkpoint = load_checkpoint(path)
        assert not hasattr(checkpoint, "world")
        assert "world" not in checkpoint.metadata

    def test_saving_creates_missing_directories(self, sandbox_agent, tmp_path):
        path = save_checkpoint(
            tmp_path / "deep" / "nested" / "ckpt.pkl",
            sandbox_agent,
            SandboxTrainingResult(),
        )
        assert path.exists()

    def test_metadata_is_preserved(self, sandbox_agent, tmp_path):
        path = save_checkpoint(
            tmp_path / "meta.pkl", sandbox_agent, SandboxTrainingResult(),
            metadata={"run_label": "sweep_a"},
        )
        assert load_checkpoint(path).metadata["run_label"] == "sweep_a"


class TestCheckpointFailureModes:

    def test_loading_missing_file_raises(self, tmp_path):
        with pytest.raises(CheckpointError):
            load_checkpoint(tmp_path / "nope.pkl")

    def test_loading_foreign_pickle_raises(self, tmp_path):
        import pickle

        path = tmp_path / "foreign.pkl"
        path.write_bytes(pickle.dumps({"not": "a checkpoint"}))
        with pytest.raises(CheckpointError):
            load_checkpoint(path)

    def test_restore_without_agent_file_returns_false(self, sandbox_agent, tmp_path):
        path = save_checkpoint(
            tmp_path / "ckpt.pkl", sandbox_agent, SandboxTrainingResult()
        )
        checkpoint = load_checkpoint(path)
        checkpoint.agent_state_path = str(tmp_path / "missing.agent.pkl")
        assert restore_agent(checkpoint, sandbox_agent) is False

    def test_restore_with_no_recorded_path_returns_false(self, sandbox_agent):
        from nowa_sandbox.sandbox_checkpoint import SandboxCheckpoint

        checkpoint = SandboxCheckpoint(
            last_quarter=0, graduated=False, graduated_at_quarter=None,
            result=SandboxTrainingResult(), agent_state_path=None,
        )
        assert restore_agent(checkpoint, sandbox_agent) is False
