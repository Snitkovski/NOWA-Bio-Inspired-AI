# Issue #13 [C11] — Core two-tier plasticity: specification / Двухуровневая пластичность ядра: спецификация

Base: `main` @ `cbce2fb`. Line numbers refer to this commit.
Scope: the NOWA **core** (`src/`) as a general-purpose engine, independent of any host application. Demo applications are covered only in the appendix and are not part of core acceptance.
Supersedes earlier drafts (strict sleep-only and mixed core+demo variants) discussed in issue #13.

---

# PART I — ENGLISH

## 1. Goal / Principle

The core has two tiers of plasticity plus a slowest habit system.

- **Stable tier** (long-term parameters): value table V/Q, BG Go/NoGo/habit weights, habit traces, visit counts, strategy weights, slow affective statistics. **Written only during sleep.**
- **Labile tier** (synaptic tags / eligibility traces): small, bounded, time-decaying offsets on Q/V and on BG channel Go/NoGo. **Written while awake**, decays with elapsed host time, lost if not consolidated.
- **Habits** (dorsolateral-striatum analogue): slowest. No change from single waking outcomes; at most an empty trace (strength 0) is created. Updated only in sleep.

**Invariant W (stable tier is read-only while awake).** Between two calls of `Agent.sleep()`, every stable parameter (§4.2 A) is bit-for-bit unchanged, whatever the host calls: `step()` with or without `reward`, `step(decision_only=True)`, `commit_executed_transition()`, `apply_feedback_to_last_experience()`, external feedback (`execute_external_action`, `resolve_external_feedback`). Waking changes are allowed only in the labile tier (§4.2 B), within clamps.

**Invariant S (sleep is the only writer of the stable tier).** Stable writes happen only inside the consolidation API reached from `Agent.sleep()`. Each episode is consolidated exactly once.

**Waking behavior:** selection uses effective values = stable + labile, so recent outcomes influence behavior before the next sleep.

**Host contract.** The core does not decide when to sleep or how fast time runs. The host supplies (a) `dt` (elapsed time per waking call, in host seconds) and (b) calls `sleep()`. The host declares the expected interval between sleeps `expected_wake_interval_s` in `PlasticityConfig`; time-based defaults are derived from it (§6).

## 2. Neuroscience rationale (brain mechanism → core component)
Textbook-level correspondences only; no numbers are taken from the literature.

| Brain mechanism | Core component |
|---|---|
| Phasic dopamine encodes reward prediction error (Schultz and colleagues) | δ = r + γ·V(s') − V(s) on effective values; phasic DA level (state) driven by δ |
| Three-factor rule: pre/post coincidence leaves an eligibility trace, a neuromodulator turns it into a weight change | Labile tier tags written by DA-signed δ; tags decay in time |
| Striatal D1 (direct, Go) and D2 (indirect, NoGo) pathways; DA potentiates D1 and depresses D2 on positive RPE, the reverse on negative | Go/NoGo channel weights: positive outcome → Go↑ NoGo↓, negative → Go↓ NoGo↑ |
| Synaptic tagging and capture (Frey & Morris): early LTP is transient unless captured into late LTP | Labile offsets decay unless captured into the stable tier during sleep with coefficient κ |
| Rapid (one-shot) hippocampal episodic encoding | `hippocampus.store` records each episode with `episode_id`, reward, executed action, `overridden` |
| Sharp-wave-ripple replay during sleep, biased toward rewarding/salient/novel experiences | Prioritized sleep replay by |δ|, |r|, novelty, emotional salience |
| Complementary learning systems (McClelland, McNaughton, O'Reilly): fast hippocampal, slow cortical/striatal learning via replay | Fast labile tier + episodic store by day; slow stable tier via replay in sleep |
| Synaptic homeostasis hypothesis, SHY (Tononi & Cirelli): sleep down-scales synapses potentiated during waking | Down-scaling of BG weights toward prior in sleep (exists: `_apply_bg_decay`, PR #35) |
| Habits depend on dorsolateral striatum and form slowly through repetition | Habit traces: no waking change; bounded EMA only in sleep |
| REM sleep is hypothesized to reduce the affective charge of memories | Optional REM step (Core decision 10); not implemented today (§3.4) |

## 3. Current state of the core (verified at `cbce2fb`)

### 3.1 Waking writes into stable parameters — must move to the labile tier or to sleep
`src/agent.py`:
| Location | Writes today | Target |
|---|---|---|
| module docstring lines 11–13: *"While awake, a known reward updates the value of the transition, the outcome-gated habit, and that action's Go/NoGo channel. Sleep consolidates episodes; it is not the only learning step."* | — | rewrite |
| `step()` docstring ~293–299: *"When `reward` is known, this step also applies one TD backup and the outcome updates for the habit and the basal-ganglia channel."* | — | rewrite |
| `step()` ~1173 `value_layer.update(..., mode="online")` when the outcome is known; episode fields `td_committed_reward`, `td_prior_value`, `td_applied_delta` (~1205–1212) | stable Q/V | labile Q tag |
| `step()` ~1216 `_record_known_outcome(...)` | habits, Go/NoGo, `bg_sleep_memories` | habits → sleep; Go/NoGo → labile channel tag; log → episode |
| `step()` ~1045–1052 `intent_memory.note_selection(...)`, fallback `record_trace(...)` | trace at strength 0; fallback increments strength | keep `note_selection`; remove the strength-incrementing fallback |
| `commit_executed_transition()` line 935, docstring 952: *"Store and learn the action that was actually executed … applies the same TD / habit / channel update as a waking step whose reward is already known"* | same as `step(reward=)` | episode + labile only |
| `apply_feedback_to_last_experience()` line 3112, docstring: *"A new rating commits one TD backup and the shared outcome update … A changed rating revises that one backup inside the current Q"*; ~3162 `_record_known_outcome`; ~3626 `value_layer.update` | stable Q, habits, Go/NoGo | episode outcome + idempotent labile contribution |
| `_record_known_outcome()` 2997 | dispatcher | split into a labile writer (day) and stable writers (sleep) |
| `_apply_outcome_to_channel()` 3015 → `channel.update_weights(go ±0.08·r, nogo ∓0.04·r)` 3030/3036 | stable Go/NoGo | labile by day, stable in sleep |
| `_apply_outcome_to_habits()` 3041 → `intent_memory.apply_outcome` 3054/3061 (EMA rate 0.20·gain, gain ∈ [0.25, 1.5]) | stable habits | sleep only |
| `record_action_outcome()` 2975 → `bg_sleep_memories` | sleep log | replaced by the episode record (Core decision 5) |
| `step()` ~1442 `emotional_expectations.update`, ~1418 `semantic_emotions.update_from_space`, ~1429 `emotional_memory.update_from_layers`, ~1377 `affective_background.update_from_traces`, ~1536 `conflict_arbitration.register_outcome` | slow affective/expectation statistics ("expectation profiles" in #13) | gray zone → Core decision 3 |
| `_apply_external_feedback_learning()` 4164 → `external_interaction_layer.apply_learning_hooks(alpha=0.1, learning_rate=0.05)` (`src/external_interaction_layer.py:516`) | strategy weights, strategy–drive coupling, `selector.action_metadata` | sleep (Core decision 8) |
| `step()` ~346–348 elapsed time from `time.time()` (wall clock) | — | labile decay uses host-supplied `dt` (§4.1) |
| `sleep()` 3343: *"This is THE ONLY mechanism for learning/adaptation."* | — | reword: only mechanism for stable learning |

`src/intent_memory.py`: `record_trace` 149 (increments strength via `IntentTrace.strengthen` 78), `strengthen_trace` 251 (legacy), `note_selection` 271 (strength 0, allowed), `apply_outcome` 296 (→ sleep only), `degrade_unused` 234 (already sleep only).
`src/basal_ganglia.py`: `ActionChannel.update_weights` (stable writer → sleep only); `prior_go/prior_nogo/prior_habit` (PR #35, constants); `BasalGangliaGate.process` (reader, must read effective weights).
`src/value_layer.py`: `update(..., mode="online")` path and `alpha_online_default` (512) — online mode removed.

### 3.2 Sleep side today (`src/sleep.py`)
`SleepManager` 118 (docstring *"Sleep consolidation - THE ONLY learning mechanism."*). `sleep_cycle()` 254: candidates → filtered consolidation, `_select_replay_sample` 1295, `_compute_replay_priority` 1366, `_apply_replay_td_bg` 1404 (δ recomputed at replay, #9 / PR #35), semantic action consolidation 1809 → `_apply_bg_decay` 2500 (toward prior) + `_normalize_bg_weights` 2521 → clustering → cortex, temporal chains, `_forget_unstable` 2691 → `intent_memory.degrade_unused(0.8)` → `_apply_neuromodulators_during_sleep` 615. `_consolidate_bg_outcome_cache` 2548 applies `bg_sleep_memories` once; `Agent.sleep()` clears it (agent.py 3399).

### 3.3 History
Before PR #33 waking already wrote V(s) online and strengthened habits regardless of outcome. PR #33 added waking Q(s,a), outcome-gated habits (`b68ac53`), per-channel Go/NoGo (`3cad48d`), `step(reward=)` (`c72e808`); PR #36 added `commit_executed_transition`. #13 stayed open.

### 3.4 REM in code
`sleep.py` 229–245 and `_classify_sleep_phase` 1143 classify replay batches as SWS / REM / TRANSITIONAL to tune semantic action consolidation (`sac_*_sws`). No step reduces affective charge of episodes.

## 4. Required behavior

### 4.1 Waking
1. **Encoding:** each executed transition stores one episode: `episode_id`, context, state snapshot, `decided_action`, `executed_action`, `overridden`, `override_source`, `reward` (None = unknown), `terminal`, next context, neuromodulator snapshot at encoding, novelty / conflict / intensity, affect gain at encoding, `outcome_revision`, `labile_contribution`, `encoded_at` (host time), `consolidated = False`.
2. **Effective values:** `Q_eff(s,a) = Q_stable(s,a) + L_Q(s,a)` (and `V_eff` if V is used); `go_eff = clamp01(go_stable + L_go)`, `nogo_eff = clamp01(nogo_stable + L_nogo)`. Habit term in selection = stable habit strength.
3. **Three-factor labile update** when an outcome becomes known (`step(reward=r)`, `commit_executed_transition(reward=r)`, feedback):
   - `δ = r + γ·(0 if terminal else max_a' Q_eff(s',a')) − Q_eff(s,a)`;
   - `ΔL_Q = clamp(η_L·g_DA·δ, −a_step, +a_step)`; `L_Q(s,a) = clamp(L_Q + ΔL_Q, −A_Q, +A_Q)`; `g_DA` = bounded phasic-DA gain (state), default 1;
   - channel: r>0 → `ΔL_go = +η_Lc·r`, `ΔL_nogo = −½η_Lc·r`; r<0 → `ΔL_go = −½η_Lc·|r|`, `ΔL_nogo = +η_Lc·|r|`; each L clamped to `[−A_c, +A_c]`;
   - the episode stores its own applied contribution (after clamping) to allow replacement.
4. **Idempotent feedback:** same rating → no-op (no change to tags, episode, logs, revision counter). Changed rating → remove the episode's stored contribution (decayed by the same factor as the tags), apply the new one, store it; never accumulate. Unknown/evicted `episode_id` → `updated=False`, no change. NaN = unknown; ±inf → ±1. Return keys unchanged (`updated`, `reward_signal`, `td_error`, `salience`, `importance`); `td_error` is computed on effective values.
5. **Time decay:** `L ← L·exp(−Δt/τ_L)`, closed form, applied lazily per entry from its last-update time on the agent's host clock. Host clock advances by `dt` passed to `step(..., dt=...)` / `commit_executed_transition(..., dt=...)` (new optional argument) or by an explicit `agent.advance_time(dt)`. If `dt` is never passed, the clock falls back to the current elapsed-time source (wall clock) and a one-time warning is logged. One call with dt=T and N calls with dt=T/N give identical results. Entries with |L| < 1e-6 are dropped.
6. **Habits:** no change from waking outcomes; `note_selection` may create a strength-0 trace.
7. **Visit counts:** stable counts frozen; optional labile visit counter for the waking exploration bonus (Core decision 6).
8. **State** (neuromodulator levels, affect, wakefulness, energy) continues as now.

### 4.2 Categories
**A. Stable parameters (sleep-only writes; bit-exact frozen awake):** (1) `value_layer` V/Q, expected-reward mean/var, confirmation counts, per-state variance; (2) stable visit counts; (3) `intent_memory` trace strengths (traces with strength > 0); (4) BG `go_weight`, `nogo_weight`, `habit_strength`, `bg_learning` parameters; (5) cortex patterns, temporal chains; (6) external `strategy_weights`, strategy–drive coupling, learned `selector.action_metadata`; (7) slow affective/expectation statistics (default, Core decision 3); (8) neuromodulator set-points/baselines.
Constants: channel priors `prior_go/prior_nogo/prior_habit`; `PlasticityConfig` values.

**B. Labile tier (waking writes, clamped, decaying):** `L_Q(s,a)`, `L_V(s)` if used, `L_go[a]`, `L_nogo[a]`, optional labile visit counter, per-entry last-update time, per-episode contributions.

**C. State:** neuromodulator levels incl. phasic DA, affect position, valence/arousal, regulation output, wakefulness, energy, working context, RNG state, counters, `episode_id` sequence, host clock, hippocampal episodes and feedback records, stability-monitor readings.

### 4.3 Sleep (order per `Agent.sleep()`)
1. Apply pending labile decay up to sleep onset (host clock).
2. Select unconsolidated episodes with known outcome (+ revised-after-consolidation ones per Core decision 1).
3. **Prioritized replay:** `priority = w_δ·|δ_now| + w_r·|r| + w_n·novelty + w_e·emotional_salience`, δ_now on current stable values; deterministic tie-break by `episode_id`. Extends `_compute_replay_priority`.
4. **TD replay** of stable Q (as #9): δ recomputed at replay time on current stable values; eligibility along trajectory order; per-state variance gate (as now).
5. **Capture:** for each episode consolidated in this sleep, move κ × its remaining (decayed) channel contribution into stable Go/NoGo; remove the contribution from L. For Q, default: labile Q is not captured (Q is learned by replay, step 4) and is cleared for consolidated episodes, to avoid double counting (Core decision 13).
6. **Habit consolidation** (bounded EMA from #8): per episode `strength += rate·(target − strength)`, target 1 if r>0, 0 if r<0, none if r=0; `rate = 0.20·clamp(affect_gain_at_encoding, 0.25, 1.5)`.
7. **Stable Go/NoGo learning** (D1/D2-like) per episode, rate `η_c_sleep` (§6), scaled by the encoding neuromodulator snapshot (bounded). With capture on, `η_c_sleep_eff = η_c_sleep − κ·η_Lc` so the total per outcome stays `η_c_sleep`.
8. External strategies / slow statistics from recorded feedback (Core decisions 3, 8).
9. Stable visit counts += consolidated episodes.
10. **SHY down-scaling:** existing `_apply_bg_decay` + `_normalize_bg_weights`, formulas unchanged.
11. Existing steps: clustering → cortex, temporal chains, `_forget_unstable`, `degrade_unused`, sleep neuromodulator dynamics.
12. Optional REM step (Core decision 10; off by default).
13. Mark episodes `consolidated = True`, `consolidated_reward`, `consolidated_revision`; clear their labile contributions. Labile entries of unconsolidated episodes keep decaying (Core decision 14).
With several cycles per sleep, steps 5–7 run once per episode per sleep; replay (step 4) may revisit transitions.
No sleep → stable tier unchanged; labile fades with τ_L; unconsolidated outcomes stay in the hippocampus until eviction (stat `lost_unconsolidated`).

### 4.4 Exactly once
Each episode contributes to capture, habits and Go/NoGo once. Revision before sleep: final value only. Revision after consolidation: Core decision 1.

## 5. Structural enforcement
1. `src/labile_layer.py` — `LabileLayer` (`effective_q`, `effective_channel`, `apply_outcome`, `replace_contribution`, `decay_to`, `pop_contribution`, `to_dict/from_dict`). Stable objects never store labile values.
2. `src/learning_guard.py` — `learning_allowed()` (entered by `Agent.sleep()`), `initializing()` (construction, load, `register_action_channel`, explicit host seeding), `assert_learning_allowed()` in every stable writer: `ValueLayer.update`, strength-changing `IntentMemory` methods, `ActionChannel.update_weights`, `apply_learning_hooks`, slow-statistics updaters (per Core decision 3). Strict mode (`NOWA_STRICT_LEARNING=1`, enabled in core `conftest.py`) raises `WakingLearningError`; production per Core decision 2.
3. `stable_fingerprint(agent)` (sha256 of canonical serialization of category A) and `labile_snapshot(agent)`.
4. Remove `mode="online"` from `ValueLayer`; split `_record_known_outcome`.
5. `PlasticityConfig` (one block, §6); persisted in save/load. No product flag.

Core docs to fix:
- Docstrings: `src/agent.py` 11–13, `step()` ~293–299, `commit_executed_transition()` 952–958, `apply_feedback_to_last_experience()` 3119–3124, `sleep()` 3347; `src/sleep.py` 120.
- `docs/qa/PR-33-reward-learning-qa*.md`, `docs/qa/PR-35-sleep-learning-qa.md`: note "superseded by #13 two-tier" where relevant.
- One clarifying sentence (stable vs labile) in: `Docs/ARCHITECTURE.en/ru.md` (11, 204/206, 268/270, 312/314), `Docs/ARCHITECTURE_UPDATED.en.md` 671, 861 / `.ru.md` 925, `Docs/00_INDEX(.NEW).en.md` 104/100, `Docs/DELIVERY_SUMMARY.*`, `Docs/GUI_COMPLETE.*`, `Docs/GUI_QUICK_REFERENCE.en.md` 12, `Docs/arxiv_NOWA_en.md` 24 and `Docs/arxiv_NOWA_ru.md`. `Docs/API.*`: document `dt`, `advance_time`, `PlasticityConfig`, host contract.
- README / quick start: no waking-learning claims; add the host contract to API docs only.

## 6. Core parameters (`PlasticityConfig`)
| Parameter | Default | Rationale (core / neuroscience) | Depends on host |
|---|---|---|---|
| `expected_wake_interval_s` (T_w) | **must be set by host**; fallback 3600 s with warning | The core cannot know how often the host sleeps | yes, defines the time scale |
| `tau_labile_s` (τ_L) | **= T_w** (i.e. `tau_labile_ratio = 1.0`) | Early-LTP-like tags should survive to the next sleep partially: an outcome at the start of the waking period keeps e⁻¹ ≈ 37 % at sleep onset, one near the end keeps almost all — recent experience dominates, older unconsolidated change fades, as in tagging-and-capture. Ratio < 0.3 loses most of the day; ratio > 3 makes the labile tier nearly permanent between sleeps | yes, via T_w and `dt` units |
| `eta_labile_q` (η_L) | 0.1 × stable replay α (`alpha_default`) | Labile tier is fast but must not dominate stable values; tenfold-smaller step keeps waking adaptation gentle | no |
| `labile_step_clamp_q` (a_step) | 0.05 (reward scale ±1) | Bounds one outcome's effect | reward scale |
| `labile_amp_clamp_q` (A_Q) | 0.2 | Max total labile shift; less than typical separation of learned values on ±1 scale | reward scale |
| `eta_labile_channel` (η_Lc) | 0.02 | ¼ of stable channel rate | no |
| `labile_amp_clamp_channel` (A_c) | 0.1 | Weights live in [0,1]; ≤10 % shift by day | no |
| `capture_kappa` (κ) | 0.5 | Partial capture: tags are not all converted; rest is lost | no |
| `eta_channel_sleep` | 0.08 | Equals today's per-outcome Go step (PR #33), keeps existing thresholds | no |
| `replay_priority_weights` (w_δ, w_r, w_n, w_e) | 1.0, 0.5, 0.25, 0.25 | Prioritized replay mainly by surprise (|RPE|), then reward magnitude, novelty, emotion | no |
| `labile_epsilon` | 1e-6 | storage cleanup | no |
Host obligations: pass `dt` in consistent units; set `expected_wake_interval_s`; call `sleep()`. If the host never sleeps, the stable tier never changes — by design.

## 7. Core tests
Rule: existing assertions are not weakened; rewritten to an equivalent labile-by-day or after-sleep form, same thresholds/seeds. All core tests construct `Agent` directly; no import from `Demo/`.

Rewrite (core): `tests/test_reward_bandit.py`, `tests/test_td_transition.py`, `tests/test_qa_issue32_reward_learning.py`, `tests/test_episode_feedback_addressing.py`, `tests/test_k02_decide_act_learn.py` (core decide/act/learn via `commit_executed_transition`), `tests/test_k03_habit_signature.py`, `tests/test_intent_memory_integration.py`, `tests/test_intent_memory.py`, `tests/test_basal_ganglia.py`, `tests/test_basal_ganglia_integration_spec.py`, `tests/test_selector.py`, `tests/test_affect_integration.py`, `tests/test_affective_persistence.py`, `tests/test_agent.py`.
Audit (rewrite only if asserting waking stable change): `test_value_layer_integration.py`, `test_value_layer.py`, `test_dopaminergic_td_layer.py`, `test_deliberative_planning_spec_011.py`, `test_neuromodulator_integration.py`, `test_external_interaction_layer.py`, `test_hie_002.py`, `test_hie_003.py`, `test_imagination_engine_spec_001.py`, `test_affective_space_integration.py`, `test_acc_conflict_modulation.py`, `test_conflict_arbitration_integration.py`, `test_phase_5_edpc.py`, `test_agent_factory.py`, `test_neuromodulators*.py`, `test_semantic_action_consolidation.py`, `test_phase_6_*`, `test_sleep_replay_td_bg.py`, `test_issue9/10/12_*.py`, `test_qa_pr35_sleep_learning.py`.
Tests in `tests/` that import Demo code (`test_k01_*`, `test_qa_pr36_colony_core.py`) move to the demo follow-up (Appendix).

New `tests/test_issue13_two_tier.py` (contextual bandit on `Agent`, 2 contexts × 3 actions, ±1, fixed seed, `expected_wake_interval_s = 1000`, dt = 1):
1. Stable guard: 200 waking calls (step with rewards, decision_only + commit with `overridden`, feedback incl. revisions, external feedback) → `stable_fingerprint` identical; strict guard raises for any stable writer outside sleep.
2. Labile changes behavior: P(rewarded action) after 100 rewarded steps without sleep > initial; |L| ≤ clamps throughout.
3. Habits untouched by day (only strength-0 traces may appear).
4. Labile decay without sleep: after 5·τ_L of host time, |L| < 1 % of initial; policy equals stable-only policy.
5. dt independence: dt=T once vs N×T/N → identical labile values (1e-12) and fingerprints.
6. Consolidation direction: after sleep Q_stable↑, habit↑, go_stable↑, nogo_stable↓ for rewarded (c,a); opposite for punished; consolidated contributions = 0.
7. Exactly once: second sleep without new episodes = control agent sleeping without episodes (only SHY decay).
8. Idempotency: r×3 ≡ r×1 (labile, and stable after sleep); r1→r2 ≡ r2.
9. Lost if not consolidated: evicted episode → no stable effect.
10. Determinism across PYTHONHASHSEED 0/1/7.
11. Save/load: labile layer, host clock, unconsolidated episodes, `PlasticityConfig` restored; decay continues.
12. Replay priority order deterministic and by the configured weights.
13. τ_L follows config: doubling `expected_wake_interval_s` doubles τ_L (ratio default).

## 8. Out of scope
How/when the host sleeps; host time scale; sleep performance and sample sizes; PR #33/#35 formulas of NoGo signal, SHY decay/normalization, neuromodulator fixed points; REM affect processing unless Core decision 10 = yes; any Demo code or tests (Appendix, PR D).

## 9. Core acceptance criteria
1. Stable fingerprint bit-exact across any waking call sequence; strict guard on in all core tests; core suite passes.
2. All waking learning goes into `LabileLayer`, within clamps; no waking habit strength change.
3. Selection uses stable + labile for Q/V and Go/NoGo.
4. Labile decay exponential in host time, dt-independent; τ_L derived from `PlasticityConfig`.
5. Feedback idempotent; changed rating replaces the episode contribution.
6. Sleep runs §4.3 in order; each episode consolidated once.
7. `mode="online"` removed; stable writers only under `learning_allowed()` / `initializing()`.
8. New tests 1–13 green; rewritten tests keep thresholds; no core test imports `Demo/`.
9. Core docstrings and `Docs/` updated; API docs describe the host contract.
10. Save/load covers labile tier, host clock, consolidation marks, config.

## 10. Core decisions (open questions, with defaults)
1. Rating changed after consolidation → default: correction in next sleep (fresh observation; replay uses new reward). Alt: ignore.
2. Guard in production → default: raise in tests/debug, log-and-skip in production.
3. Slow affective/expectation statistics → default: stable, sleep-only.
4. Host seeding of habits/channels → default: allowed under `initializing()`.
5. `bg_sleep_memories` → default: drop, use episodes.
6. Visit counts → default: stable frozen + labile counter for waking exploration.
7. Stable Go/NoGo rate in sleep → default: 0.08 (not `bg_learning` 0.05).
8. External `apply_learning_hooks` → default: move to sleep.
9. Labile rate/clamps → default: η_L = 0.1·α, a_step 0.05, A_Q 0.2, η_Lc 0.02, A_c 0.1.
10. REM affect-reduction step → default: off.
11. τ_L → default: `tau_labile_ratio = 1.0 × expected_wake_interval_s`; host must set the interval (fallback 3600 s + warning).
12. κ → default: 0.5.
13. Capture vs replay for Q → default: Q by replay only, labile Q cleared; capture for Go/NoGo with compensated sleep rate.
14. Labile entries of unconsolidated episodes after sleep → default: keep decaying.
15. Replay priority weights → default: 1.0 / 0.5 / 0.25 / 0.25.
16. `dt` missing → default: wall-clock fallback with one-time warning (alt: raise).

## 11. Size and PR split
Core total ≈ L (~2 weeks, ~2–3k lines incl. tests).
- **PR A — labile tier + guard:** `LabileLayer`, `PlasticityConfig`, host clock and `dt`, effective values, guard + fingerprints, waking writers → labile, habits off by day, core test rewrites, new tests 1–5, 8, 10, 11, 13.
- **PR B — sleep consolidation:** prioritized replay, capture, habit EMA, Go/NoGo from episodes, marks, exactly-once, revisions after consolidation, slow statistics/external hooks to sleep; tests 6, 7, 9, 12.
- **PR C — core docstrings/Docs:** §5 list, API host contract, QA notes.
- **PR D — demo adaptation** (after A+B): see Appendix.
Order: A → B → C (C may go in parallel with B); D after B.

## Appendix: impact on the Colony demo (not part of core acceptance)
No core requirement comes from this appendix.
- `Demo/Colony chinchillas/src/colony_agent.py`: `sim_step(dt)` (419) calls `step(reward=None, decision_only=True)` (~452) and `commit_executed_transition(reward=...)` (~470) — both remain valid APIs; demo should pass `dt=dt` and set `expected_wake_interval_s` in its agent construction. `_apply_sleep_recovery` (867) calls `self.sleep(cycles, sleep_duration_seconds=0.0)` — unchanged. `_seed_habit_bootstrap` (901) writes traces directly — must run under `initializing()`.
- Demo constants and `PHYSIOLOGY_AS_POLICY` are not changed by the core work.
- Tests to adapt in PR D: `tests/test_k01_colony_ablation.py` (#19 ablation), `tests/test_k01_need_consumption.py`, `tests/test_qa_pr36_colony_core.py`, `Demo/Colony chinchillas/tests/test_nowa_agent.py`, `test_knowledge.py`, `test_death_registry_inspector_lineage.py`. If the ablation's core advantage relied on waking stable learning, add explicit `sleep()` calls between blocks in the test; keep asserts.
- Demo docs mentioning sleep-only learning (`Demo/Tamagochi Chinchilla/Docs/*`, `Demo/Virtual company/Docs/*`, `Demo/Warriner Validation/Docs/*`): optional note.

**Demo follow-up questions (defaults):**
1. Demo `expected_wake_interval_s` → default: the demo's measured mean waking duration between sleeps.
2. Ablation #19 if it fails → default: explicit `sleep()` in the test, demo constants untouched.
3. `_seed_habit_bootstrap` → default: wrap in `initializing()`, no behavior change.
4. Demo docs → default: one-line note, separate from core docs PR.

---

# ЧАСТЬ II — РУССКИЙ

База: `main` @ `cbce2fb`. Номера строк — по этому коммиту.
Scope: **ядро** NOWA (`src/`) как универсальный движок, независимо от хост-приложения. Демо рассматриваются только в приложении и в критерии приёмки ядра не входят.
Заменяет ранние черновики (строгий вариант «только сон» и смешанный вариант ядро+демо), обсуждавшиеся в issue #13.

## 1. Цель / Принцип

В ядре два уровня пластичности плюс самая медленная система привычек.

- **Стабильный слой** (долговременные параметры): таблица V/Q, веса Go/NoGo/habit BG, следы привычек, счётчики визитов, веса стратегий, медленная аффективная статистика. **Пишется только во сне.**
- **Лабильный слой** (синаптические метки / eligibility traces): малые, ограниченные, затухающие во времени добавки к Q/V и к Go/NoGo каналов BG. **Пишется днём**, затухает по прошедшему времени хоста, теряется, если не консолидирован.
- **Привычки** (аналог дорсолатерального стриатума): самый медленный слой. Одиночные дневные исходы их не меняют; максимум создаётся пустой след (сила 0). Обновляются только во сне.

**Инвариант W (стабильный слой днём только читается).** Между двумя вызовами `Agent.sleep()` каждый стабильный параметр (§4.2 A) не меняется бит-в-бит, что бы ни вызывал хост: `step()` с `reward` и без, `step(decision_only=True)`, `commit_executed_transition()`, `apply_feedback_to_last_experience()`, внешний feedback (`execute_external_action`, `resolve_external_feedback`). Дневные изменения разрешены только в лабильном слое (§4.2 B), в пределах clamp.

**Инвариант S (сон — единственный писатель стабильного слоя).** Запись в стабильный слой — только внутри API консолидации, вызываемого из `Agent.sleep()`. Каждый эпизод консолидируется ровно один раз.

**Поведение днём:** выбор использует эффективные значения = стабильное + лабильное, поэтому недавние исходы влияют на поведение ещё до следующего сна.

**Контракт с хостом.** Ядро не решает, когда спать и с какой скоростью идёт время. Хост передаёт (а) `dt` (прошедшее время на дневной вызов, в секундах хоста) и (б) вызывает `sleep()`. Хост объявляет ожидаемый интервал между снами `expected_wake_interval_s` в `PlasticityConfig`; временные дефолты выводятся из него (§6).

## 2. Нейронаучное обоснование (механизм мозга → компонент ядра)
Только общеизвестные соответствия уровня учебника; числа из литературы не берутся.

| Механизм мозга | Компонент ядра |
|---|---|
| Фазический дофамин кодирует ошибку предсказания награды (Шульц и коллеги) | δ = r + γ·V(s') − V(s) по эффективным значениям; уровень фазического DA (состояние) задаётся δ |
| Трёхфакторное правило: совпадение пре/пост оставляет eligibility trace, нейромодулятор превращает его в изменение веса | Метки лабильного слоя пишутся DA-знаковой δ; метки затухают во времени |
| Пути стриатума D1 (прямой, Go) и D2 (непрямой, NoGo); при положительной RPE DA усиливает D1 и ослабляет D2, при отрицательной — наоборот | Веса Go/NoGo канала: положительный исход → Go↑ NoGo↓, отрицательный → Go↓ NoGo↑ |
| Synaptic tagging and capture (Фрей и Моррис): ранняя LTP временна, если не захвачена в позднюю | Лабильные добавки затухают, если во сне не захвачены в стабильный слой с коэффициентом κ |
| Быстрое (с одного предъявления) эпизодическое кодирование в гиппокампе | `hippocampus.store` записывает каждый эпизод с `episode_id`, наградой, исполненным действием, `overridden` |
| Replay в sharp-wave ripples во сне, смещённый к наградным/значимым/новым эпизодам | Приоритетный replay во сне по |δ|, |r|, новизне, эмоциональной значимости |
| Комплементарные системы обучения (McClelland, McNaughton, O'Reilly): быстрое обучение гиппокампа, медленное корковое/стриатное через replay | Быстрый лабильный слой + эпизодическая память днём; медленный стабильный слой через replay во сне |
| Гипотеза синаптического гомеостаза, SHY (Тонони и Чирелли): сон понижает синапсы, усиленные за день | Понижение весов BG к prior во сне (уже есть: `_apply_bg_decay`, PR #35) |
| Привычки зависят от дорсолатерального стриатума и формируются медленно через повторение | Следы привычек: днём не меняются; ограниченная EMA только во сне |
| Есть гипотеза, что REM-сон снижает аффективную окраску воспоминаний | Опциональный REM-шаг (решение ядра 10); сейчас не реализован (§3.4) |

## 3. Текущее состояние ядра (проверено на `cbce2fb`)

### 3.1 Дневные записи в стабильные параметры — должны уйти в лабильный слой или в сон
`src/agent.py`:
| Место | Что пишет сейчас | Куда |
|---|---|---|
| docstring модуля, строки 11–13: *«While awake, a known reward updates the value of the transition, the outcome-gated habit, and that action's Go/NoGo channel. Sleep consolidates episodes; it is not the only learning step.»* | — | переписать |
| docstring `step()` ~293–299: *«When `reward` is known, this step also applies one TD backup and the outcome updates for the habit and the basal-ganglia channel.»* | — | переписать |
| `step()` ~1173 `value_layer.update(..., mode="online")` при известном исходе; поля эпизода `td_committed_reward`, `td_prior_value`, `td_applied_delta` (~1205–1212) | стабильная Q/V | лабильная метка Q |
| `step()` ~1216 `_record_known_outcome(...)` | привычки, Go/NoGo, `bg_sleep_memories` | привычки → сон; Go/NoGo → лабильная метка канала; журнал → эпизод |
| `step()` ~1045–1052 `intent_memory.note_selection(...)`, fallback `record_trace(...)` | след силы 0; fallback увеличивает силу | `note_selection` оставить; fallback с увеличением силы убрать |
| `commit_executed_transition()`, строка 935, docstring 952: *«Store and learn the action that was actually executed … applies the same TD / habit / channel update as a waking step whose reward is already known»* | то же, что `step(reward=)` | только эпизод + лабильный слой |
| `apply_feedback_to_last_experience()`, строка 3112, docstring: *«A new rating commits one TD backup and the shared outcome update … A changed rating revises that one backup inside the current Q»*; ~3162 `_record_known_outcome`; ~3626 `value_layer.update` | стабильные Q, привычки, Go/NoGo | исход эпизода + идемпотентный лабильный вклад |
| `_record_known_outcome()` 2997 | диспетчер | разделить на лабильного писателя (день) и стабильных (сон) |
| `_apply_outcome_to_channel()` 3015 → `channel.update_weights(go ±0.08·r, nogo ∓0.04·r)` 3030/3036 | стабильные Go/NoGo | днём лабильно, во сне стабильно |
| `_apply_outcome_to_habits()` 3041 → `intent_memory.apply_outcome` 3054/3061 (EMA, rate 0.20·gain, gain ∈ [0.25, 1.5]) | стабильные привычки | только сон |
| `record_action_outcome()` 2975 → `bg_sleep_memories` | журнал для сна | заменяется записью в эпизоде (решение ядра 5) |
| `step()` ~1442 `emotional_expectations.update`, ~1418 `semantic_emotions.update_from_space`, ~1429 `emotional_memory.update_from_layers`, ~1377 `affective_background.update_from_traces`, ~1536 `conflict_arbitration.register_outcome` | медленная аффективная статистика и статистика ожиданий («expectation profiles» в #13) | серая зона → решение ядра 3 |
| `_apply_external_feedback_learning()` 4164 → `external_interaction_layer.apply_learning_hooks(alpha=0.1, learning_rate=0.05)` (`src/external_interaction_layer.py:516`) | веса стратегий, связь стратегия–драйв, `selector.action_metadata` | сон (решение ядра 8) |
| `step()` ~346–348: прошедшее время из `time.time()` (настенные часы) | — | лабильное затухание по `dt` от хоста (§4.1) |
| `sleep()` 3343: *«This is THE ONLY mechanism for learning/adaptation.»* | — | переформулировать: единственный механизм стабильного обучения |

`src/intent_memory.py`: `record_trace` 149 (увеличивает силу через `IntentTrace.strengthen` 78), `strengthen_trace` 251 (legacy), `note_selection` 271 (сила 0, разрешено), `apply_outcome` 296 (→ только сон), `degrade_unused` 234 (уже только во сне).
`src/basal_ganglia.py`: `ActionChannel.update_weights` (стабильный писатель → только сон); `prior_go/prior_nogo/prior_habit` (PR #35, константы); `BasalGangliaGate.process` (читатель, должен читать эффективные веса).
`src/value_layer.py`: путь `update(..., mode="online")` и `alpha_online_default` (512) — режим online удаляется.

### 3.2 Сонная сторона сейчас (`src/sleep.py`)
`SleepManager` 118 (docstring *«Sleep consolidation - THE ONLY learning mechanism.»*). `sleep_cycle()` 254: кандидаты → фильтрованная консолидация, `_select_replay_sample` 1295, `_compute_replay_priority` 1366, `_apply_replay_td_bg` 1404 (δ пересчитывается при replay, #9 / PR #35), семантическая консолидация действий 1809 → `_apply_bg_decay` 2500 (к prior) + `_normalize_bg_weights` 2521 → кластеризация → кора, временные цепочки, `_forget_unstable` 2691 → `intent_memory.degrade_unused(0.8)` → `_apply_neuromodulators_during_sleep` 615. `_consolidate_bg_outcome_cache` 2548 применяет `bg_sleep_memories` один раз; `Agent.sleep()` его очищает (agent.py 3399).

### 3.3 История
До PR #33 бодрствование уже писало V(s) в режиме online и усиливало привычки без учёта исхода. PR #33 добавил дневной Q(s,a), привычки по исходу (`b68ac53`), Go/NoGo канала (`3cad48d`), `step(reward=)` (`c72e808`); PR #36 добавил `commit_executed_transition`. #13 оставался открытым.

### 3.4 REM в коде
`sleep.py` 229–245 и `_classify_sleep_phase` 1143 классифицируют пачки replay как SWS / REM / TRANSITIONAL для настройки семантической консолидации действий (`sac_*_sws`). Шага, снижающего аффективную окраску эпизодов, нет.

## 4. Требуемое поведение

### 4.1 Бодрствование
1. **Кодирование:** каждый исполненный переход сохраняет один эпизод: `episode_id`, контекст, снимок состояния, `decided_action`, `executed_action`, `overridden`, `override_source`, `reward` (None = неизвестен), `terminal`, следующий контекст, снимок нейромодуляторов при кодировании, novelty / conflict / intensity, аффективный gain при кодировании, `outcome_revision`, `labile_contribution`, `encoded_at` (время хоста), `consolidated = False`.
2. **Эффективные значения:** `Q_eff(s,a) = Q_stable(s,a) + L_Q(s,a)` (и `V_eff`, если V используется); `go_eff = clamp01(go_stable + L_go)`, `nogo_eff = clamp01(nogo_stable + L_nogo)`. Вклад привычки в выбор = стабильная сила привычки.
3. **Трёхфакторное лабильное обновление**, когда исход становится известен (`step(reward=r)`, `commit_executed_transition(reward=r)`, feedback):
   - `δ = r + γ·(0 если terminal иначе max_a' Q_eff(s',a')) − Q_eff(s,a)`;
   - `ΔL_Q = clamp(η_L·g_DA·δ, −a_step, +a_step)`; `L_Q(s,a) = clamp(L_Q + ΔL_Q, −A_Q, +A_Q)`; `g_DA` — ограниченный gain фазического DA (состояние), по умолчанию 1;
   - канал: r>0 → `ΔL_go = +η_Lc·r`, `ΔL_nogo = −½η_Lc·r`; r<0 → `ΔL_go = −½η_Lc·|r|`, `ΔL_nogo = +η_Lc·|r|`; каждая L зажимается в `[−A_c, +A_c]`;
   - эпизод хранит свой фактически применённый вклад (после clamp), чтобы его можно было заменить.
4. **Идемпотентный feedback:** та же оценка → no-op (метки, эпизод, журналы, счётчик ревизий не меняются). Изменённая оценка → убрать сохранённый вклад эпизода (с тем же коэффициентом затухания, что у меток), применить новый, сохранить его; никакого накопления. Неизвестный/вытесненный `episode_id` → `updated=False`, без изменений. NaN = неизвестно; ±inf → ±1. Ключи результата не меняются (`updated`, `reward_signal`, `td_error`, `salience`, `importance`); `td_error` считается по эффективным значениям.
5. **Затухание по времени:** `L ← L·exp(−Δt/τ_L)`, в замкнутой форме, лениво для каждой записи от её времени последнего обновления по часам хоста в агенте. Часы хоста продвигаются на `dt`, переданный в `step(..., dt=...)` / `commit_executed_transition(..., dt=...)` (новый необязательный аргумент), или явным `agent.advance_time(dt)`. Если `dt` никогда не передаётся, часы берутся из текущего источника прошедшего времени (настенные часы) и один раз пишется предупреждение. Один вызов с dt=T и N вызовов с dt=T/N дают одинаковый результат. Записи с |L| < 1e-6 удаляются.
6. **Привычки:** дневные исходы их не меняют; `note_selection` может создать след силы 0.
7. **Счётчики визитов:** стабильные заморожены; опционально лабильный счётчик для дневного бонуса исследования (решение ядра 6).
8. **Состояние** (уровни нейромодуляторов, аффект, бодрость, энергия) меняется как сейчас.

### 4.2 Категории
**A. Стабильные параметры (пишутся только во сне; днём заморожены бит-в-бит):** (1) V/Q `value_layer`, среднее/дисперсия ожидаемой награды, счётчики подтверждений, дисперсия по состоянию; (2) стабильные счётчики визитов; (3) силы следов `intent_memory` (следы с силой > 0); (4) `go_weight`, `nogo_weight`, `habit_strength` BG, параметры `bg_learning`; (5) паттерны коры, временные цепочки; (6) внешние `strategy_weights`, связь стратегия–драйв, обучаемые поля `selector.action_metadata`; (7) медленная аффективная статистика и статистика ожиданий (по умолчанию, решение ядра 3); (8) уставки/базовые линии нейромодуляторов.
Константы: priors каналов `prior_go/prior_nogo/prior_habit`; значения `PlasticityConfig`.

**B. Лабильный слой (днём писать можно, с clamp, затухает):** `L_Q(s,a)`, `L_V(s)` (если используется), `L_go[a]`, `L_nogo[a]`, опциональный лабильный счётчик визитов, время последнего обновления записи, вклады эпизодов.

**C. Состояние:** уровни нейромодуляторов, включая фазический DA, положение в аффективном пространстве, valence/arousal, выход регуляции, бодрость, энергия, рабочий контекст, состояние RNG, счётчики, последовательность `episode_id`, часы хоста, эпизоды гиппокампа и записи feedback, показания монитора стабильности.

### 4.3 Сон (порядок за один `Agent.sleep()`)
1. Применить отложенное лабильное затухание до момента засыпания (по часам хоста).
2. Выбрать неконсолидированные эпизоды с известным исходом (+ ревизованные после консолидации — по решению ядра 1).
3. **Приоритетный replay:** `priority = w_δ·|δ_now| + w_r·|r| + w_n·novelty + w_e·emotional_salience`, δ_now — по текущим стабильным значениям; детерминированное разрешение ничьих по `episode_id`. Расширяет `_compute_replay_priority`.
4. **TD replay** стабильного Q (как #9): δ пересчитывается в момент replay по текущим стабильным значениям; eligibility по порядку траектории; гейт по дисперсии состояния (как сейчас).
5. **Capture:** для каждого эпизода, консолидируемого в этом сне, κ × его оставшийся (после затухания) вклад канала переносится в стабильные Go/NoGo; вклад удаляется из L. Для Q по умолчанию лабильный Q не захватывается (Q учится через replay, шаг 4) и очищается для консолидированных эпизодов, чтобы не считать дважды (решение ядра 13).
6. **Консолидация привычек** (ограниченная EMA из #8): на эпизод `strength += rate·(target − strength)`, target 1 при r>0, 0 при r<0, без изменений при r=0; `rate = 0.20·clamp(affect_gain_при_кодировании, 0.25, 1.5)`.
7. **Стабильное обучение Go/NoGo** (D1/D2-подобно) по эпизоду, скорость `η_c_sleep` (§6), масштабируется снимком нейромодуляторов при кодировании (с ограничением). При включённом capture `η_c_sleep_eff = η_c_sleep − κ·η_Lc`, чтобы суммарный шаг на исход оставался `η_c_sleep`.
8. Внешние стратегии / медленная статистика по записанному feedback (решения ядра 3, 8).
9. Стабильные счётчики визитов += консолидированные эпизоды.
10. **Понижение по SHY:** существующие `_apply_bg_decay` + `_normalize_bg_weights`, формулы не меняются.
11. Существующие шаги: кластеризация → кора, временные цепочки, `_forget_unstable`, `degrade_unused`, сонная динамика нейромодуляторов.
12. Опциональный REM-шаг (решение ядра 10; по умолчанию выключен).
13. Пометить эпизоды `consolidated = True`, `consolidated_reward`, `consolidated_revision`; очистить их лабильные вклады. Лабильные записи неконсолидированных эпизодов продолжают затухать (решение ядра 14).
При нескольких циклах за сон шаги 5–7 выполняются один раз на эпизод за сон; replay (шаг 4) может возвращаться к переходам.
Нет сна → стабильный слой не меняется; лабильный затухает с τ_L; неконсолидированные исходы остаются в гиппокампе до вытеснения (статистика `lost_unconsolidated`).

### 4.4 Ровно один раз
Каждый эпизод вносит вклад в capture, привычки и Go/NoGo один раз. Ревизия до сна: только финальное значение. Ревизия после консолидации: решение ядра 1.

## 5. Структурное принуждение
1. `src/labile_layer.py` — `LabileLayer` (`effective_q`, `effective_channel`, `apply_outcome`, `replace_contribution`, `decay_to`, `pop_contribution`, `to_dict/from_dict`). Стабильные объекты лабильных значений не хранят.
2. `src/learning_guard.py` — `learning_allowed()` (в него входит `Agent.sleep()`), `initializing()` (создание, загрузка, `register_action_channel`, явный посев хостом), `assert_learning_allowed()` в каждом стабильном писателе: `ValueLayer.update`, методы `IntentMemory`, меняющие силу, `ActionChannel.update_weights`, `apply_learning_hooks`, обновления медленной статистики (по решению ядра 3). Строгий режим (`NOWA_STRICT_LEARNING=1`, включён в `conftest.py` ядра) бросает `WakingLearningError`; продакшен — по решению ядра 2.
3. `stable_fingerprint(agent)` (sha256 канонической сериализации категории A) и `labile_snapshot(agent)`.
4. Удалить `mode="online"` из `ValueLayer`; разделить `_record_known_outcome`.
5. `PlasticityConfig` (один блок, §6); сохраняется в save/load. Продуктового флага нет.

Документы ядра к исправлению:
- Docstrings: `src/agent.py` 11–13, `step()` ~293–299, `commit_executed_transition()` 952–958, `apply_feedback_to_last_experience()` 3119–3124, `sleep()` 3347; `src/sleep.py` 120.
- `docs/qa/PR-33-reward-learning-qa*.md`, `docs/qa/PR-35-sleep-learning-qa.md`: пометка «заменено двухуровневой моделью #13», где относится.
- Одна уточняющая фраза (стабильный vs лабильный) в: `Docs/ARCHITECTURE.en/ru.md` (11, 204/206, 268/270, 312/314), `Docs/ARCHITECTURE_UPDATED.en.md` 671, 861 / `.ru.md` 925, `Docs/00_INDEX(.NEW).en.md` 104/100, `Docs/DELIVERY_SUMMARY.*`, `Docs/GUI_COMPLETE.*`, `Docs/GUI_QUICK_REFERENCE.en.md` 12, `Docs/arxiv_NOWA_en.md` 24 и `Docs/arxiv_NOWA_ru.md`. `Docs/API.*`: описать `dt`, `advance_time`, `PlasticityConfig`, контракт с хостом.
- README / quick start: утверждений о дневном обучении нет; контракт с хостом — только в документации API.

## 6. Параметры ядра (`PlasticityConfig`)
| Параметр | По умолчанию | Обоснование (свойства ядра / нейронаука) | Зависит от хоста |
|---|---|---|---|
| `expected_wake_interval_s` (T_w) | **задаёт хост**; fallback 3600 с с предупреждением | Ядро не может знать, как часто хост вызывает сон | да, задаёт масштаб времени |
| `tau_labile_s` (τ_L) | **= T_w** (`tau_labile_ratio = 1.0`) | Метки, подобные ранней LTP, должны частично дожить до следующего сна: исход в начале периода бодрствования сохраняет e⁻¹ ≈ 37 % к засыпанию, исход в конце — почти всё; недавний опыт преобладает, старое неконсолидированное затухает, как в tagging-and-capture. Ratio < 0.3 теряет большую часть дня; ratio > 3 делает лабильный слой почти постоянным между снами | да, через T_w и единицы `dt` |
| `eta_labile_q` (η_L) | 0.1 × стабильный α replay (`alpha_default`) | Лабильный слой быстрый, но не должен доминировать над стабильными значениями; шаг в 10 раз меньше делает дневную адаптацию мягкой | нет |
| `labile_step_clamp_q` (a_step) | 0.05 (шкала награды ±1) | Ограничивает эффект одного исхода | масштаб награды |
| `labile_amp_clamp_q` (A_Q) | 0.2 | Максимальный суммарный лабильный сдвиг; меньше типичного разделения выученных значений на шкале ±1 | масштаб награды |
| `eta_labile_channel` (η_Lc) | 0.02 | ¼ стабильной скорости канала | нет |
| `labile_amp_clamp_channel` (A_c) | 0.1 | Веса лежат в [0,1]; днём сдвиг ≤10 % | нет |
| `capture_kappa` (κ) | 0.5 | Частичный захват: не все метки превращаются в стабильные, остальное теряется | нет |
| `eta_channel_sleep` | 0.08 | Равна нынешнему шагу Go на исход (PR #33), сохраняет существующие пороги | нет |
| `replay_priority_weights` (w_δ, w_r, w_n, w_e) | 1.0, 0.5, 0.25, 0.25 | Приоритетный replay в основном по неожиданности (|RPE|), затем величина награды, новизна, эмоция | нет |
| `labile_epsilon` | 1e-6 | очистка хранилища | нет |
Обязанности хоста: передавать `dt` в согласованных единицах; задать `expected_wake_interval_s`; вызывать `sleep()`. Если хост никогда не вызывает сон, стабильный слой никогда не меняется — так задумано.

## 7. Тесты ядра
Правило: существующие ассерты не ослабляются; переписываются в эквивалентную форму «лабильно днём» или «после сна» с теми же порогами/seeds. Все тесты ядра создают `Agent` напрямую; импорта из `Demo/` нет.

Переписать (ядро): `tests/test_reward_bandit.py`, `tests/test_td_transition.py`, `tests/test_qa_issue32_reward_learning.py`, `tests/test_episode_feedback_addressing.py`, `tests/test_k02_decide_act_learn.py` (decide/act/learn ядра через `commit_executed_transition`), `tests/test_k03_habit_signature.py`, `tests/test_intent_memory_integration.py`, `tests/test_intent_memory.py`, `tests/test_basal_ganglia.py`, `tests/test_basal_ganglia_integration_spec.py`, `tests/test_selector.py`, `tests/test_affect_integration.py`, `tests/test_affective_persistence.py`, `tests/test_agent.py`.
Аудит (переписывать, только если проверяют дневное изменение стабильного слоя): `test_value_layer_integration.py`, `test_value_layer.py`, `test_dopaminergic_td_layer.py`, `test_deliberative_planning_spec_011.py`, `test_neuromodulator_integration.py`, `test_external_interaction_layer.py`, `test_hie_002.py`, `test_hie_003.py`, `test_imagination_engine_spec_001.py`, `test_affective_space_integration.py`, `test_acc_conflict_modulation.py`, `test_conflict_arbitration_integration.py`, `test_phase_5_edpc.py`, `test_agent_factory.py`, `test_neuromodulators*.py`, `test_semantic_action_consolidation.py`, `test_phase_6_*`, `test_sleep_replay_td_bg.py`, `test_issue9/10/12_*.py`, `test_qa_pr35_sleep_learning.py`.
Тесты в `tests/`, импортирующие код демо (`test_k01_*`, `test_qa_pr36_colony_core.py`), переходят в доработку демо (Приложение).

Новый `tests/test_issue13_two_tier.py` (контекстный бандит на `Agent`, 2 контекста × 3 действия, ±1, фиксированный seed, `expected_wake_interval_s = 1000`, dt = 1):
1. Guard стабильного слоя: 200 дневных вызовов (step с наградами, decision_only + commit с `overridden`, feedback с ревизиями, внешний feedback) → `stable_fingerprint` идентичен; строгий guard бросает исключение на любом стабильном писателе вне сна.
2. Лабильный слой меняет поведение: P(вознаграждённого действия) после 100 вознаграждённых шагов без сна > исходной; |L| всё время ≤ clamp.
3. Привычки днём не меняются (могут появиться только следы силы 0).
4. Затухание без сна: через 5·τ_L времени хоста |L| < 1 % от начального; policy совпадает с policy только по стабильному слою.
5. Независимость от dt: dt=T один раз против N×T/N → одинаковые лабильные значения (1e-12) и отпечатки.
6. Направление консолидации: после сна Q_stable↑, habit↑, go_stable↑, nogo_stable↓ для вознаграждённой (c,a); наоборот для наказанной; консолидированные вклады = 0.
7. Ровно один раз: второй сон без новых эпизодов = контрольный агент, спящий без эпизодов (только понижение SHY).
8. Идемпотентность: r×3 ≡ r×1 (лабильно и стабильно после сна); r1→r2 ≡ r2.
9. Не консолидировано — потеряно: вытесненный эпизод → стабильного эффекта нет.
10. Детерминизм при PYTHONHASHSEED 0/1/7.
11. Save/load: лабильный слой, часы хоста, неконсолидированные эпизоды, `PlasticityConfig` восстанавливаются; затухание продолжается.
12. Порядок приоритетного replay детерминирован и следует заданным весам.
13. τ_L следует конфигурации: удвоение `expected_wake_interval_s` удваивает τ_L (при дефолтном ratio).

## 8. Вне scope
Как/когда хост вызывает сон; масштаб времени хоста; производительность сна и размеры выборки; формулы PR #33/#35 для сигнала NoGo, затухания/нормализации SHY, неподвижных точек нейромодуляторов; аффективная обработка в REM, если решение ядра 10 ≠ да; любой код и тесты демо (Приложение, PR D).

## 9. Критерии приёмки ядра
1. Стабильный отпечаток бит-в-бит неизменен при любой последовательности дневных вызовов; строгий guard включён во всех тестах ядра; набор тестов ядра проходит.
2. Всё дневное обучение идёт в `LabileLayer`, в пределах clamp; дневных изменений силы привычек нет.
3. Выбор использует стабильное + лабильное для Q/V и Go/NoGo.
4. Лабильное затухание экспоненциально по времени хоста, не зависит от dt; τ_L выводится из `PlasticityConfig`.
5. Feedback идемпотентен; изменённая оценка заменяет вклад эпизода.
6. Сон выполняет §4.3 по порядку; каждый эпизод консолидируется один раз.
7. `mode="online"` удалён; стабильные писатели — только внутри `learning_allowed()` / `initializing()`.
8. Новые тесты 1–13 зелёные; переписанные тесты сохраняют пороги; ни один тест ядра не импортирует `Demo/`.
9. Docstrings ядра и `Docs/` обновлены; документация API описывает контракт с хостом.
10. Save/load покрывает лабильный слой, часы хоста, метки консолидации, конфигурацию.

## 10. Решения по ядру (открытые вопросы, с дефолтами)
1. Оценка изменена после консолидации → по умолчанию: коррекция в следующем сне (свежее наблюдение; replay берёт новую награду). Альтернатива: игнорировать.
2. Guard в продакшене → по умолчанию: исключение в тестах/отладке, лог и пропуск в продакшене.
3. Медленная аффективная статистика / статистика ожиданий → по умолчанию: стабильная, только сон.
4. Посев привычек/каналов хостом → по умолчанию: разрешён внутри `initializing()`.
5. `bg_sleep_memories` → по умолчанию: убрать, брать из эпизодов.
6. Счётчики визитов → по умолчанию: стабильные заморожены + лабильный счётчик для дневного исследования.
7. Стабильная скорость Go/NoGo во сне → по умолчанию: 0.08 (не 0.05 из `bg_learning`).
8. Внешние `apply_learning_hooks` → по умолчанию: перенести в сон.
9. Скорость/clamp лабильного слоя → по умолчанию: η_L = 0.1·α, a_step 0.05, A_Q 0.2, η_Lc 0.02, A_c 0.1.
10. REM-шаг снижения аффекта → по умолчанию: выключен.
11. τ_L → по умолчанию: `tau_labile_ratio = 1.0 × expected_wake_interval_s`; интервал обязан задать хост (fallback 3600 с + предупреждение).
12. κ → по умолчанию: 0.5.
13. Capture против replay для Q → по умолчанию: Q только через replay, лабильный Q очищается; capture для Go/NoGo с компенсированной скоростью во сне.
14. Лабильные записи неконсолидированных эпизодов после сна → по умолчанию: продолжают затухать.
15. Веса приоритета replay → по умолчанию: 1.0 / 0.5 / 0.25 / 0.25.
16. `dt` не передан → по умолчанию: настенные часы с однократным предупреждением (альтернатива: исключение).

## 11. Объём и разбиение на PR
Ядро ≈ L (~2 недели, ~2–3 тыс. строк с тестами).
- **PR A — лабильный слой + guard:** `LabileLayer`, `PlasticityConfig`, часы хоста и `dt`, эффективные значения, guard + отпечатки, дневные писатели → лабильный слой, привычки днём выключены, переписанные тесты ядра, новые тесты 1–5, 8, 10, 11, 13.
- **PR B — консолидация во сне:** приоритетный replay, capture, EMA привычек, Go/NoGo по эпизодам, метки, ровно-один-раз, ревизии после консолидации, медленная статистика/внешние хуки в сон; тесты 6, 7, 9, 12.
- **PR C — docstrings/Docs ядра:** список из §5, контракт с хостом в API, пометки QA.
- **PR D — адаптация демо** (после A+B): см. Приложение.
Порядок: A → B → C (C можно параллельно с B); D после B.

## Приложение: влияние на демо колонии (вне критериев приёмки ядра)
Из этого приложения никаких требований к ядру не следует.
- `Demo/Colony chinchillas/src/colony_agent.py`: `sim_step(dt)` (419) вызывает `step(reward=None, decision_only=True)` (~452) и `commit_executed_transition(reward=...)` (~470) — оба API остаются; демо должно передавать `dt=dt` и задавать `expected_wake_interval_s` при создании агента. `_apply_sleep_recovery` (867) вызывает `self.sleep(cycles, sleep_duration_seconds=0.0)` — без изменений. `_seed_habit_bootstrap` (901) пишет следы напрямую — должен выполняться внутри `initializing()`.
- Константы демо и `PHYSIOLOGY_AS_POLICY` работой над ядром не меняются.
- Тесты для адаптации в PR D: `tests/test_k01_colony_ablation.py` (абляция #19), `tests/test_k01_need_consumption.py`, `tests/test_qa_pr36_colony_core.py`, `Demo/Colony chinchillas/tests/test_nowa_agent.py`, `test_knowledge.py`, `test_death_registry_inspector_lineage.py`. Если преимущество ядра в абляции держалось на дневном стабильном обучении — добавить в тест явные `sleep()` между блоками; ассерты сохранить.
- Документы демо, где говорится об обучении только во сне (`Demo/Tamagochi Chinchilla/Docs/*`, `Demo/Virtual company/Docs/*`, `Demo/Warriner Validation/Docs/*`): по желанию, пометка.

**Вопросы по доработке демо (дефолты):**
1. `expected_wake_interval_s` демо → по умолчанию: измеренная средняя длительность бодрствования между снами в демо.
2. Абляция #19, если упадёт → по умолчанию: явные `sleep()` в тесте, константы демо не трогать.
3. `_seed_habit_bootstrap` → по умолчанию: обернуть в `initializing()`, без изменения поведения.
4. Документы демо → по умолчанию: однострочная пометка, отдельно от PR документации ядра.


---
**Owner decision (2026-10-19):** all default answers to the open questions (Core decisions 1–16, Demo follow-up 1–4) are accepted. Implementation order: PR A → B → C (core), then D (demo).

**Решение владельца (2026-10-19):** все варианты по умолчанию в открытых вопросах (решения по ядру 1–16, демо 1–4) приняты. Порядок: PR A → B → C (ядро), затем D (демо).

---
**Owner decisions after PR A (2026-10-19), scope of PR B:**
1. Slow affective statistics are stable parameters: they change only during sleep (decision 3), included in the stable fingerprint.
2. Phasic dopamine gain `g_DA` stays 1 (no dependence on dopamine level for now; possible separate feature later).
3. Labile visit counters do not decay during waking; during sleep they are transferred into stable visit counts and reset (decision 6).
4. Guard bypasses are closed: direct `go_weight` assignment, `register_action_channel`, `ValueLayer._set_value` outside sleep, `consolidate_habits` without guard; `apply_sleep_learning` must not open the guard when called during waking.
5. Demo adaptation (former PR D) is split into a separate stage and PR per demo: Colony chinchillas, Tamagochi Chinchilla, Virtual company, Warriner Validation — each adapted and fully checked independently, without tuning the core.

**Решения владельца после PR A (2026-10-19), объём PR B:**
1. Медленная аффективная статистика — стабильный параметр: меняется только во сне (решение 3), входит в отпечаток стабильного слоя.
2. Фазический коэффициент дофамина `g_DA` остаётся 1 (без зависимости от уровня дофамина; возможна отдельная фича позже).
3. Лабильные счётчики визитов днём не затухают; во сне переносятся в стабильные визиты и обнуляются (решение 6).
4. Обходы guard закрываются: прямая запись `go_weight`, `register_action_channel`, `ValueLayer._set_value` вне сна, `consolidate_habits` без guard; `apply_sleep_learning` не должен открывать guard при вызове днём.
5. Адаптация демо (бывший PR D) разбита на отдельные этапы и PR по каждому демо: Colony chinchillas, Tamagochi Chinchilla, Virtual company, Warriner Validation — каждое адаптируется и полностью проверяется отдельно, без подстройки ядра.
