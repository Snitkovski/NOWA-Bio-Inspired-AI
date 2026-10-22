# QA PR #36 — colony depends on the core

Branch: `team/colony-core-dependence`, commit `43a3903`
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/36
Issues: #19, #20, #21
Base: `9921d04`. Product code was not changed in this pass.

The first pass (before the owner decided to enable the flag by default) is replaced by this report. Sleep and wakefulness were not checked: over 600 s the need threshold is not reached; the owner deferred that question and it is not counted as a defect of this PR.

## Verdict

PASS

## Coverage

0 failed. `pytest tests`: **849 passed, 5 skipped** (179 s). The five skips are unchanged (autonomous runtime / Drive MCP).

Headless: `python -m colony_gui --headless --duration 2` from `Demo/Colony chinchillas/src`, `--lang en` and `--lang ru`, both print `ok: sim_time=00:00:02 agents=4`, exit code 0.

## What was checked

1. Diff of tests from the previous QA commit `d85cb61` to `43a3903` — additions and retargeting to the new contract only. Old thresholds were not lowered. `position_confidence < 0.5` in `Demo/Colony chinchillas/tests/test_knowledge.py` remains, window still 120 s, position still `wheel`. The only edit — both agents are created with `physiology_as_policy=False`. That is honest: execution in the test is already frozen (`_interpret_action` is a no-op), and with the new default unsatisfied hunger drains energy and ends the window with death. Measurement: with the flag off, no deaths in 120 s, confidence = 0.45. With the flag on and the same freeze the agent dies of exhaustion at 90 s, confidence = 0.55, and the `< 0.5` assert no longer tests memory decay. Pinning the old gate preserves the subject of the test.
2. Four founders, age 0, 600 s. All alive, 0 deaths. Hunger and thirst do not hit 1.

| seed | dt | min water | min food | max thirst | max hunger |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 s | 0.425 | 0.466 | 0.625 | 0.626 |
| 2 | 1 s | 0.419 | 0.466 | 0.653 | 0.654 |
| 7 | 1 s | 0.425 | 0.466 | 0.631 | 0.660 |
| 1 | 1/12 s | 0.400 | 0.464 | 0.585 | 0.608 |
| 2 | 1/12 s | 0.406 | 0.464 | 0.586 | 0.603 |
| 7 | 1/12 s | 0.400 | 0.464 | 0.590 | 0.606 |

Shared bowl drain does not depend on step size: food matches within 0.002, water differs by at most 0.025. This is not an artifact of emptying the bowl with frequent ticks.
3. Reward. Spamming `drink` and `eat` without need yields 0.2, like `rest`, and does not touch water or food. Successful `drink` at thirst 0.9: reward 1.0, thirst 0.28, water −0.006. `drink` from an empty bowl: reward −0.3605, thirst stays 0.9. Rest at the same thirst gives −0.1425, so an empty sip is worse than doing nothing.
4. Ablation, seeds 1, 2, 7. Core alive all 30 s (energy 0.80, 0.55, 0.96). Constant `rest` dies of exhaustion at step 21, energy 0.055. Same seed repeats match. Core reproduces (names `G1A1SM`, `G1A2SF`, `G1A3SM`, `G1A4SM`, `G1A5SM`), `rest` does not get pregnant in the same 40 s. Gestation after pregnancy is shortened to 1 s as in test K01. Offspring inherit the parent flag (`True`).
5. Save. Agent with `True` and agent with `False` load back with their flags. JSON without the field loads as `True`. Mother's offspring with `False` gets `False`. Offspring name `G1A6SF`.
6. Regressions #33/#35 and key #21 are in the same 849: repeated rating on `episode_id` does not move Go/NoGo, habit, or sleep cache (`tests/test_qa_pr36_colony_core.py`, `tests/test_k02_decide_act_learn.py`); canonical md5 key and `PYTHONHASHSEED` — `tests/test_k03_habit_signature.py` and the QA signature test.

## Defects

None new.

## Release readiness

Yes.
