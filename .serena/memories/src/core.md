Entry point is `Agent` in `src/agent.py`. Waking call is `Agent.step()`. Consolidation is `Agent.sleep()`.

Stable tier (Q/V, basal-ganglia Go/NoGo, habits, slow affect) is writable only inside `learning_allowed()` (sleep) or `initializing()` (construction, load, host seeding). Guard: `src/learning_guard.py` (`WakingLearningError`, `NOWA_STRICT_LEARNING`).

Labile tier: `src/labile_layer.py` (`LabileLayer`, `PlasticityConfig`). Bounded offsets on Q and Go/NoGo that decay with host time. The host passes `dt` and calls sleep. `expected_wake_interval_s` is the host's interval between sleeps.

Other core organs, still host-agnostic: hippocampus, cortex, basal ganglia, affect, genome, epigenome, neuromodulators, and `src/mcp_body/` (admission circuit for an external tool). Details of a body do not belong here. See `mem:critical_info`.
