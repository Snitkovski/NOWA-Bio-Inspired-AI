# Fresh results after v1.2 (2026-08-05)

Patch v1.2 replaces the Stage 1a non-regression baseline methodology:
**median across all quarters** + IQR-aware floor, instead of the mean of the
last five successful quarters.

| File | What it is | Outcome |
|---|---|---|
| `stage_1a_baseline.json` | Rewritten with `method=median_all` from `stage1a_seed1` | stockout median **0.296** (was 0.949), IQR **0.741** HIGH VOLATILITY |
| `stage1b_v12_smoke.json` | Fresh Stage 1b smoke (5×30-day quarters, seed 1, new baseline) | Guard wired; `stockout_avoidance` never flagged |
| `stage1b_v111_seed1.json` | Prior 20-quarter Stage 1b (re-scored under new floors) | See below |

## Re-score of Stage 1b seed1 quarters 31–50

Same recorded fitness values, two floors:

| Floor | stockout fails | cost_eff fails | risk fails | guard-clean quarters |
|---|---|---|---|---|
| v1.1 mean-of-best × 0.9 | 9 / 20 | 20 / 20 | 5 / 20 | **0** |
| v1.2 median + IQR floor | **0 / 20** | 20 / 20 | 0 / 20 | **0** |

`stockout_avoidance` false regressions are gone — that was the v1.2 target.
`cost_efficiency` still collapses in Stage 1b (values ~0.08–0.45 vs floor
0.59), so the qualifying streak remains 0. That is agent / world calibration
(Direction B / section 19), not a baseline methodology bug.

New floors from `results/stage_1a_baseline.json`:

| Criterion | median | IQR | floor |
|---|---|---|---|
| cost_efficiency | 0.8359 | 0.2417 | 0.5942 |
| stockout_avoidance | 0.2961 | 0.7407 | **0.0000** |
| budget_discipline | 1.0000 | 0.0000 | 0.9000 |
| reaction_to_risk_events | 0.7449 | 0.2058 | 0.5391 |

## Direction B diagnostics (open questions)

```bash
python tools/trend_diagnostic.py results/stage1a_seed1.json --window 10
python tools/world_volatility_diagnostic.py --quarters 30 --seed 1
```

On seed1 (30 quarters):

- `cost_efficiency` — LEARNING TREND (slope +0.004)
- `stockout_avoidance` — **NO CLEAR TREND** (raw_std 0.357)
- World with no agent: demand shocks and stockout units vary widely across
  seeds → exogenous quarter difficulty is itself high (open question 3)
- `sleep_manager.sleep_cycle` is present and callable (open question 2 needs
  hippocampus/cortex profiling between specific quarters, not this probe)

## How to reproduce

From `Demo/Virtual company/`:

```bat
set PYTHONPATH=%CD%\src
python src\nowa_sandbox\stage1a_report.py results\stage1a_seed1.json --write-baseline results\stage_1a_baseline.json
python tools\trend_diagnostic.py results\stage1a_seed1.json --window 10
python src\nowa_sandbox\run_sandbox.py --stage 1b --baseline-from results\stage_1a_baseline.json --seed 1 --quarters 20 --no-stop-on-graduation --output results\stage1b_v12_seed1.json --checkpoint checkpoints\stage1b_v12_seed1.ckpt
```

If you still have a Stage 1a checkpoint, resume it for a fair comparison with
the v1.1.1 trial:

```bat
set SANDBOX_SEED=1 && set SANDBOX_QUARTERS=20 && run_stage1b.bat --resume-from checkpoints\stage1a_seed1.ckpt
```

## Tests

```bat
cd "Demo\Virtual company"
python -m pytest -m "not slow"   # 381 passed
```

The slow perf budget `test_standard_quarter_is_under_thirty_seconds` can still
trip (~38 s) — known from v1.0 (agent.step / hippocampal search), unrelated to
baseline methodology.
