"""Tests for SandboxObserver."""

import json

import pytest

from nowa_sandbox.procurement_world import ProcurementWorldConfig
from nowa_sandbox.sandbox_observer import SandboxObserver
from nowa_sandbox.training_loop import SandboxTrainer


def _result(sandbox_agent, encoder, fitness_evaluator, n_quarters=2):
    trainer = SandboxTrainer(sandbox_agent, encoder, fitness_evaluator)
    config = ProcurementWorldConfig(
        initial_budget=10_000.0, n_products=2, n_suppliers=2,
        days_per_quarter=10, seed=1,
    )
    return trainer.run_quarters(
        n_quarters=n_quarters, world_config=config, stop_on_graduation=False
    )


class TestRecording:

    def test_record_appends_snapshots(self, sandbox_agent, encoder, fitness_evaluator):
        result = _result(sandbox_agent, encoder, fitness_evaluator)
        observer = SandboxObserver()
        for quarter in result.quarters:
            observer.record(quarter)
        assert len(observer.snapshots) == 2

    def test_record_all_is_equivalent(self, sandbox_agent, encoder, fitness_evaluator):
        result = _result(sandbox_agent, encoder, fitness_evaluator)
        observer = SandboxObserver()
        observer.record_all(result.quarters)
        assert len(observer.snapshots) == 2

    def test_observer_does_not_mutate_quarters(
        self, sandbox_agent, encoder, fitness_evaluator
    ):
        result = _result(sandbox_agent, encoder, fitness_evaluator, n_quarters=1)
        before = result.quarters[0].fitness.as_dict()
        observer = SandboxObserver()
        observer.record_all(result.quarters)
        observer.to_records()
        assert result.quarters[0].fitness.as_dict() == before


class TestJsonExport:

    def test_to_json_writes_valid_file(
        self, sandbox_agent, encoder, fitness_evaluator, tmp_path
    ):
        result = _result(sandbox_agent, encoder, fitness_evaluator)
        observer = SandboxObserver()
        observer.record_all(result.quarters)

        output = tmp_path / "run.json"
        observer.to_json(str(output))

        data = json.loads(output.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert set(data[0]) >= {
            "quarter_index", "fitness", "graduation", "world_summary"
        }

    def test_to_json_creates_missing_directories(
        self, sandbox_agent, encoder, fitness_evaluator, tmp_path
    ):
        result = _result(sandbox_agent, encoder, fitness_evaluator, n_quarters=1)
        observer = SandboxObserver()
        observer.record_all(result.quarters)

        output = tmp_path / "nested" / "deeper" / "run.json"
        observer.to_json(str(output))
        assert output.exists()

    def test_empty_observer_writes_empty_list(self, tmp_path):
        output = tmp_path / "empty.json"
        SandboxObserver().to_json(str(output))
        assert json.loads(output.read_text(encoding="utf-8")) == []

    def test_records_include_all_six_criteria(
        self, sandbox_agent, encoder, fitness_evaluator
    ):
        from nowa_sandbox.procurement_fitness import PROCUREMENT_CRITERIA

        result = _result(sandbox_agent, encoder, fitness_evaluator, n_quarters=1)
        observer = SandboxObserver()
        observer.record_all(result.quarters)
        record = observer.to_records()[0]
        assert set(record["fitness"]) == set(PROCUREMENT_CRITERIA)

    def test_dict_snapshots_pass_through(self, tmp_path):
        observer = SandboxObserver()
        observer.record({"quarter_index": 1, "custom": True})
        output = tmp_path / "custom.json"
        observer.to_json(str(output))
        assert json.loads(output.read_text(encoding="utf-8"))[0]["custom"] is True


class TestPlotProgress:

    def test_plot_progress_is_explicitly_unimplemented(self):
        with pytest.raises(NotImplementedError):
            SandboxObserver().plot_progress()
