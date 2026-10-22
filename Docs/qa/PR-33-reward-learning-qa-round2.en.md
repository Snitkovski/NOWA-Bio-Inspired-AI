# QA round 2: PR #33 — re-check of fixes

> **Superseded by issue #13 two-tier plasticity** — see `Docs/qa/PR-33-reward-learning-qa.en.md` header. / **Superseded by #13** — see `PR-33-reward-learning-qa.en.md` header.

Branch: `team/issue-32-reward-learning` (after `2efdb6b`)
PR: https://github.com/burlakovmb/NOWA-Bio-Inspired-AI/pull/33
Product code was not changed. QA file `tests/test_qa_issue32_reward_learning.py` does not differ between `09c997e` and `HEAD` (`git diff` empty): asserts were not weakened.

## Verdict

PASS

## Coverage

- scenarios: 10 passed / 0 failed / 4 not run
- `pytest tests`: 782 passed, 5 skipped, 53.72 s
- QA file is in that run: previous 7 failures are now green, 18 tests in the file total

Passed:

1. Full `pytest tests`.
2. Revision of the first of eight `+2`: Q `0.2163 → 0.1609` (old backup removed and new one written), not reset to a single step from zero. Revising back to `+2` returns `0.2158` (delta `0.0004`). Foreign Q (`0.4`) did not move.
3. Repeated same feedback does not move go, habit, sleep log, or TD count. `step(reward=1.0)` and following feedback `+2` on the same episode also do not duplicate: go `0.58`, habit `0.2`, TD count `1`, Q `0.03`.
4. `rng_seed=5` gives one trace even if global `random` is advanced. Agent without `rng_seed` still repeats from `random.seed` and diverges on another seed.
5. Load of save without `hippocampus_episode_seq`, `last_episode_id`, `action_visit_counts`, and without `episode_id` on episodes does not crash; next step gets `ep-1`.
6. Load of save where ids are already on episodes but counter key is missing: `get_experience("ep-1")` finds reward `1.0`, counter rises to max id, next step is `ep-4`, old reward stays `1.0`.
7. `reward=nan`: step survives, episode reward `0.0`, TD not committed, Q `0`. `reward=+inf/-inf`: step survives, reward saturates to `+1/-1`, Q `+0.03/-0.03`.

Not run: #9, #10, #12, colony #19–#21.

## Defects

None new.

Status from the previous round:

1. Rating revision clobbered Q — fixed. Correction is from current Q (`stored + new backup − old backup`).
2. Repeated same feedback moved Go/NoGo and habit — fixed. Matching already committed rating exits before those updates.
3. `step(reward=...)` did not teach habit and channel — fixed. Shared path `_record_known_outcome`.
4. NaN/inf aborted `step` — fixed. NaN is unknown outcome, ±inf clamped to ±1 before hippocampus store.
5. After save/load id `ep-1` was reused — fixed. Counter is written in save and restored from max `ep-N` when key missing. Repeated id does not steal an existing episode.
6. `rng_seed` did not control thalamic softmax — fixed. With `rng_seed`, `ThalamicGate.select` uses `self._rng`.
7. Docstrings described old formulas — fixed. Channel NoGo in `process`, waking TD in `Agent`.

## Questions / blockers

No blockers.

Habit and Go/NoGo on rating change are a second EMA step toward the new outcome, not subtraction of the first. After `+2` and revision to `-2` habit stays around `0.16`, not zero. Q still converges. Does not affect verdict: previous round required Q correction; idempotency only for the same rating.

`td_applied_delta` is stored on the episode while old backup subtraction is recomputed with the same formula. On a round trip the mismatch is `0.0004`.

## Recommendations

Safe to merge as closure of #3–#8 and #11. Exact habit rollback on rating change is not required for this release.

## Release readiness

yes
