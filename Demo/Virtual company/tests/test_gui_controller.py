"""Tests for the lab GUI headless controller (no tkinter window)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from nowa_sandbox.gui_charts import FitnessChart
from nowa_sandbox.gui_controller import (
    RunController,
    RunSpec,
    SweepSpec,
    format_readiness_text,
    load_results_json,
    quarter_to_record,
)
from nowa_sandbox.training_loop import QuarterResult
from nowa_sandbox.procurement_fitness import ProcurementFitnessVector


def _tiny_spec(tmp_path: Path, *, quarters: int = 3, seed: int = 3) -> RunSpec:
    return RunSpec(
        stage="1a",
        seed=seed,
        quarters=quarters,
        days_per_quarter=8,
        budget=10_000.0,
        products=2,
        suppliers=2,
        sleep_every=4,
        config_path="configs/default_world.yaml",
        output=str(tmp_path / f"lab_seed{seed}.json"),
        checkpoint=str(tmp_path / f"lab_seed{seed}.ckpt"),
        stop_on_graduation=False,
        seed_intuition=True,
    )


def _wait_idle(ctrl: RunController, timeout: float = 180.0) -> None:
    deadline = time.time() + timeout
    while ctrl.is_busy and time.time() < deadline:
        time.sleep(0.05)
    assert not ctrl.is_busy, "controller still busy after timeout"


class TestLoadAndFormat:

    def test_load_results_list(self, tmp_path):
        path = tmp_path / "r.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "quarter_index": 1,
                        "fitness": {"cost_efficiency": 0.5},
                        "graduation": {"all_passed": False},
                    }
                ]
            ),
            encoding="utf-8",
        )
        rows = load_results_json(str(path))
        assert len(rows) == 1
        assert rows[0]["quarter_index"] == 1

    def test_format_readiness_text_ready(self):
        report = {
            "rows": [
                {
                    "name": "seed42",
                    "graduated": True,
                    "first_graduation_quarter": 10,
                    "n_graduated_quarters": 5,
                }
            ],
            "readiness": {
                "n_graduated": 4,
                "n_runs": 5,
                "graduation_quarters": [8, 10, 12, 14],
                "spread_ratio": 0.4,
                "spread_half_width": 5.0,
                "spread_within_tolerance": True,
                "ready_for_stage_1b": True,
            },
            "baseline_path": None,
            "refused": None,
        }
        text = format_readiness_text(report)
        assert "READY for Stage 1b" in text
        assert "seed42" in text

    def test_write_baseline_refuses_mean_best(self, tmp_path):
        ctrl = RunController()
        # Minimal fake summarize path: write empty list -> summarize may fail;
        # exercise the method gate before summarize by mocking rows via
        # refusing mean_best without needing real files when write is set.
        # mean_best refuse happens after summarize_run — use a tiny results file.
        path = tmp_path / "s.json"
        path.write_text("[]", encoding="utf-8")
        report = ctrl.write_baseline_report(
            [str(path)],
            write_baseline_to=str(tmp_path / "b.json"),
            method="mean_best",
        )
        assert report["refused"] is not None
        assert "mean_best" in report["refused"]
        assert report["baseline_path"] is None


class TestRunController:

    def test_single_run_writes_output(self, tmp_path):
        ctrl = RunController()
        logs: list[str] = []
        quarters: list[dict] = []
        done = threading.Event()
        holder: dict = {}

        def on_done(result, error):
            holder["result"] = result
            holder["error"] = error
            done.set()

        ctrl.start_run(
            _tiny_spec(tmp_path, quarters=2),
            on_log=logs.append,
            on_quarter=quarters.append,
            on_done=on_done,
        )
        assert done.wait(180)
        _wait_idle(ctrl)
        assert holder["error"] is None
        assert holder["result"] is not None
        assert len(holder["result"].quarters) == 2
        assert len(quarters) == 2
        assert Path(ctrl.last_output).exists()
        assert Path(ctrl.last_checkpoint).exists()
        assert any("Quarter" in line for line in logs)

    def test_soft_stop_halts_between_quarters(self, tmp_path):
        ctrl = RunController()
        seen = []
        done = threading.Event()

        def on_quarter(record):
            seen.append(record["quarter_index"])
            if len(seen) == 1:
                ctrl.request_stop()

        def on_done(result, error):
            done.set()

        ctrl.start_run(
            _tiny_spec(tmp_path, quarters=5, seed=11),
            on_quarter=on_quarter,
            on_done=on_done,
        )
        assert done.wait(180)
        _wait_idle(ctrl)
        assert ctrl.last_error is None
        assert 1 <= len(seen) <= 2
        assert len(ctrl.last_result.quarters) == len(seen)

    def test_resume_continues_from_checkpoint(self, tmp_path):
        ctrl = RunController()
        done = threading.Event()

        def on_done(result, error):
            done.set()

        spec = _tiny_spec(tmp_path, quarters=1, seed=5)
        ctrl.start_run(spec, on_done=on_done)
        assert done.wait(180)
        _wait_idle(ctrl)
        assert len(ctrl.last_result.quarters) == 1
        ckpt = ctrl.last_checkpoint

        done.clear()
        resume = RunSpec(
            stage="1a",
            seed=5,
            quarters=1,
            days_per_quarter=8,
            budget=10_000.0,
            products=2,
            suppliers=2,
            sleep_every=4,
            config_path="configs/default_world.yaml",
            output=str(tmp_path / "lab_seed5_resumed.json"),
            checkpoint=str(tmp_path / "lab_seed5_resumed.ckpt"),
            resume_from=ckpt,
            stop_on_graduation=False,
        )
        ctrl.start_run(resume, on_done=on_done)
        assert done.wait(180)
        _wait_idle(ctrl)
        assert ctrl.last_error is None
        assert len(ctrl.last_result.quarters) == 2

    def test_busy_rejects_second_start(self, tmp_path):
        ctrl = RunController()
        done = threading.Event()
        ctrl.start_run(_tiny_spec(tmp_path, quarters=2), on_done=lambda *_: done.set())
        with pytest.raises(RuntimeError, match="already in progress"):
            ctrl.start_run(_tiny_spec(tmp_path, quarters=1, seed=99))
        assert done.wait(180)
        _wait_idle(ctrl)

    def test_sweep_two_seeds(self, tmp_path):
        ctrl = RunController()
        done = threading.Event()
        logs: list[str] = []

        sweep = SweepSpec(
            seeds=[3, 7],
            quarters=1,
            config_path="configs/default_world.yaml",
            stop_on_graduation=False,
            output_template=str(tmp_path / "sweep_seed{seed}.json"),
            checkpoint_template=str(tmp_path / "sweep_seed{seed}.ckpt"),
        )
        # Override world size via first seed's execute path: SweepSpec has no
        # days/products — patch by writing a tiny YAML.
        tiny_cfg = tmp_path / "tiny.yaml"
        tiny_cfg.write_text(
            "world:\n  n_products: 2\n  n_suppliers: 2\n  days_per_quarter: 8\n"
            "  initial_budget: 10000\n"
            "training:\n  sleep_every_n_days: 4\n  seed_intuition: true\n",
            encoding="utf-8",
        )
        sweep.config_path = str(tiny_cfg)

        ctrl.start_sweep(sweep, on_log=logs.append, on_done=lambda *_: done.set())
        assert done.wait(240)
        _wait_idle(ctrl)
        assert ctrl.last_error is None
        assert (tmp_path / "sweep_seed3.json").exists()
        assert (tmp_path / "sweep_seed7.json").exists()
        assert any("SWEEP SEED" in line for line in logs)


class TestQuarterRecord:

    def test_quarter_to_record_from_result_object(self):
        fitness = ProcurementFitnessVector(
            cost_efficiency=0.7,
            stockout_avoidance=0.8,
            budget_discipline=0.6,
            reaction_to_risk_events=0.5,
            supplier_diversification=0.4,
            decision_consistency=0.3,
            n_days=10,
            n_orders=3,
        )
        q = QuarterResult(
            quarter_index=2,
            fitness=fitness,
            graduation={"all_passed": False, "passed": []},
            world_summary={},
            processing_time_s=0.1,
        )
        record = quarter_to_record(q)
        assert record["quarter_index"] == 2
        assert abs(record["fitness"]["cost_efficiency"] - 0.7) < 1e-9


class TestFitnessChartSmoke:

    @pytest.mark.tk
    def test_set_data_and_clear(self):
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            chart = FitnessChart(root, width=320, height=220)
            chart.update_idletasks()
            chart.set_data(
                ["1", "2", "3"],
                {"cost_efficiency": [0.2, 0.4, 0.6]},
                labels={"cost_efficiency": "cost efficiency"},
            )
            assert chart._hit_points
            # Hover nearest to first point should create a tooltip tag.
            pt = chart._hit_points[0]

            class _E:
                x = int(pt["x"])
                y = int(pt["y"])

            chart._on_motion(_E())
            assert chart.find_withtag("tooltip")
            chart.clear()
            assert not chart._hit_points
        finally:
            root.destroy()


class TestGuiAppImport:

    def test_import_main_module(self):
        from nowa_sandbox import gui_app

        assert callable(gui_app.main)

    def test_gui_has_no_anti_monopoly_controls(self):
        import inspect

        from nowa_sandbox import gui_app

        source = inspect.getsource(gui_app)
        assert "chk_anti_monopoly" not in source
        assert "anti_monopoly_scaffold" not in RunSpec.__dataclass_fields__

    def test_gui_resume_path_matches_cli_seeding_lifecycle(self):
        from pathlib import Path

        from nowa_sandbox import gui_controller, run_sandbox

        cli = Path(run_sandbox.__file__).read_text(encoding="utf-8")
        gui = Path(gui_controller.__file__).read_text(encoding="utf-8")
        for source, label in ((cli, "run_sandbox"), (gui, "gui_controller")):
            assert "seed_intuition=config.training.seed_intuition and not" in source, (
                f"{label} must skip factory seeding on resume"
            )
            assert "seed_professional_intuition" in source
            assert "if config.training.seed_intuition:" in source
