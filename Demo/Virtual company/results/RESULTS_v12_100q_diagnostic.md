# Stage 1a extended diagnostic — 100 quarters, seed 1 (v1.2 open Q1)

**Date:** 2026-08-05  
**Command:** Stage 1a, seed 1, 100 quarters, `--no-stop-on-graduation`  
**Artifacts:** `results/stage1a_seed1_extended.json`, `checkpoints/stage1a_seed1_extended.ckpt`  
**Runtime:** ~47 minutes

## Verdict (open question 1)

On a 10-quarter moving average, **no criterion clears the LEARNING TREND
threshold** (`slope > 0.002`) from `tools/trend_diagnostic.py`:

| Criterion | raw_std | smoothed_std | MA10 slope | Verdict |
|---|---|---|---|---|
| cost_efficiency | 0.155 | 0.062 | +0.00096 | NO CLEAR TREND |
| stockout_avoidance | 0.381 | 0.110 | +0.00137 | NO CLEAR TREND |
| budget_discipline | 0.000 | 0.000 | 0.00000 | NO CLEAR TREND (ceiling) |
| reaction_to_risk_events | 0.120 | 0.031 | +0.00049 | NO CLEAR TREND |

So **more quarters alone do not reveal a clear learning curve**. Direction B
(sleep consolidation / world difficulty) remains a live candidate for v1.3 —
this is not “Stage 1a just needs 100 quarters to graduate more reliably” as the
primary explanation.

Caveat: first-20 vs last-20 means still move up modestly
(`stockout` 0.391→0.524, `cost` 0.756→0.828), and graduation density rises in
later decades. That is a weak positive signal below the diagnostic threshold,
not strong enough to close open question 1 as “solved by sample size.”

## Graduation

- **22 / 100** quarters with `all_passed`
- First pass at Q8; clusters in Q44–51, Q85–93, Q98
- Decades with most passes: Q41–50 (4), Q81–90 (4), Q91–100 (3)
- Decade Q31–40: **0** passes

Graduation is intermittent noise with a mild late bias, not a monotonic climb.

## Block means (window 10)

| Block | n_ok | cost | stockout | budget | risk |
|---|---|---|---|---|---|
| Q1–10 | 2 | 0.704 | 0.444 | 1.000 | 0.711 |
| Q11–20 | 1 | 0.808 | 0.338 | 1.000 | 0.732 |
| Q21–30 | 2 | 0.780 | 0.405 | 1.000 | 0.738 |
| Q31–40 | 0 | 0.679 | 0.335 | 1.000 | 0.783 |
| Q41–50 | 4 | 0.788 | 0.528 | 1.000 | 0.773 |
| Q51–60 | 3 | 0.832 | 0.437 | 1.000 | 0.784 |
| Q61–70 | 1 | 0.849 | 0.255 | 1.000 | 0.717 |
| Q71–80 | 2 | 0.801 | 0.492 | 1.000 | 0.821 |
| Q81–90 | 4 | 0.798 | 0.562 | 1.000 | 0.795 |
| Q91–100 | 3 | 0.857 | 0.487 | 1.000 | 0.754 |

`stockout_avoidance` remains the noisiest series (IQR over 100Q = **0.835**).

## Median baseline on 100Q (for reference)

| Criterion | median | IQR | v1.2 floor |
|---|---|---|---|
| cost_efficiency | 0.8359 | 0.2051 | 0.6308 |
| stockout_avoidance | 0.3766 | 0.8351 | 0.0000 |
| budget_discipline | 1.0000 | 0.0000 | 0.9000 |
| reaction_to_risk_events | 0.7833 | 0.1795 | 0.6038 |

Compared with the 30Q seed1 baseline: stockout median rises slightly
(0.296→0.377); IQR stays extreme.

## Implication for v1.3

1. **Do not** treat “run more Stage 1a quarters” as the main fix for missing
   learning trend — 100Q did not produce `LEARNING TREND` on stockout.
2. **Do** investigate Direction B next:
   - sleep / consolidation between quarters (open Q2)
   - world parameter variance (`demand_shock`, late delivery) — already high
     in `world_volatility_diagnostic` (open Q3)
3. Weak late improvement (first20→last20, graduation density) can still inform
   calibration, but it is not a clean curriculum curve.

## Reproduce

```bat
cd "Demo\Virtual company"
set PYTHONPATH=%CD%\src
python src\nowa_sandbox\run_sandbox.py --stage 1a --seed 1 --quarters 100 --no-stop-on-graduation --output results\stage1a_seed1_extended.json --checkpoint checkpoints\stage1a_seed1_extended.ckpt
python tools\trend_diagnostic.py results\stage1a_seed1_extended.json --window 10
```
