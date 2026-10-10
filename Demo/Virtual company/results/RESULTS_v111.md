# Fresh results after v1.1.1 (2026-08-03)

| File | What it is | Outcome |
|---|---|---|
| `stage1a_seed11.json` | Stage 1a, 30 quarters, seed 11 | Not graduated — `stockout_avoidance=0` all quarters |
| `stage1a_seed14.json` | Stage 1a, 30 quarters, seed 14 | Not graduated — same stockout collapse |
| `stage1a_seed4_rerun.json` | Stage 1a, 30 quarters, seed 4 (historically graduated) | Not graduated this time — stockouts noisy, no full pass (agent cognition is not bit-reproducible) |
| `stage1b_v111_seed1.json` | Stage 1b, 20 quarters from `stage1a_seed1` checkpoint + `stage_1a_baseline.json` | **NOT YET GRADUATED** under v1.1.1 |

## Stage 1b verification (the important one)

Resumed from the graduated Stage 1a seed-1 checkpoint. Under the old v1.1 rule
this run would have set `graduated=True` as soon as a single `all_passed` hit
(e.g. quarter 31). Under v1.1.1:

- 11 of 20 Stage 1b quarters had `all_passed=true`
- **0** of those were clean under the non-regression guard
- `qualifying_streak` never left 0
- summary ends with `NOT YET GRADUATED - continue training`

That is the patch working as designed.

## How to reproduce / continue

From `Demo/Virtual company/`:

```bat
run_sandbox.bat
run_stage1a.bat
set SANDBOX_SEED=1 && run_stage1a.bat
set SANDBOX_SEED=1 && set SANDBOX_QUARTERS=20 && run_stage1b.bat --resume-from checkpoints\stage1a_seed1.ckpt
```

Or:

```bat
python src\nowa_sandbox\run_sandbox.py --stage 1b --baseline-from results\stage_1a_baseline.json --seed 1 --quarters 20 --no-stop-on-graduation --resume-from checkpoints\stage1a_seed1.ckpt --output results\stage1b_v111_seed1.json --checkpoint checkpoints\stage1b_v111_seed1.ckpt
```
