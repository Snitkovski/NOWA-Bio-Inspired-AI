# NOWA Body Layer — Patch v1.1

Russian version: [NOWA_Body_Layer_Phase1_Patch_v1.1.ru.md](NOWA_Body_Layer_Phase1_Patch_v1.1.ru.md)

## Abstract

Patch v1.1 closes the Phase 1 questions of when to sleep and how often to step, without building a second fatigue model inside `nowa_body`. `SleepScheduler` reads the wakefulness state that already exists in the core, under Borbély's two-process scheme: process S is homeostatic sleep pressure, growing with activity, and process C is the circadian component. On every tick the scheduler returns a pair of whether to sleep and a reason, `circadian` or `fatigue`. The default window is the hours from 2 inclusive to 5 exclusive. The fatigue threshold is 0.85. The minimum gap between sleeps is 3,600 ticks, about one hour at a 1 Hz step. Until that gap has elapsed, sleep does not start. If the pressure attribute cannot be read, the scheduler remains on the circadian trigger alone and does not crash. The patch requires the exact name of the process-S field to be checked against `wakefulness.py` before the final binding: pressure may grow from activity by itself, or it may require an explicit accumulation on each tick.

The second part separates the cognitive tick from sensor polling. The host calls `tick()` about once a second. The sensor-reading function runs when at least `sensor_refresh_interval_s` has passed since the last refresh, 300 seconds by default; the other ticks repeat `run_cycle` on the cached snapshot. Over an hour that is 3,600 decisions on the same or rarely updated observation, so an order and a letter become decisions of different ticks. `hippocampus.store` is called only for a non-empty `ProposedAction`. A tick whose action is `wait_and_monitor` creates no episode: that is constraint B8. Sensor rate is not the step rate: that is constraint B9. `run_cycle` remains a pass over an already prepared snapshot and is suitable for tests. The question of the `intent_summary` format is not changed by the patch and is left open.

The patch is complete when the scheduler is implemented after the core API has been checked, both sleep triggers pass their tests, `tick` is implemented with a sensor cache, and tests show that over ten ticks at an interval of 300 s the sensor reader is called once, while one hundred waiting ticks do not increase the number of episodes. The Phase 1 assembly includes the scheduler and the `tick` wrapper, not only a pure `run_cycle`.

---

**Base document:** NOWA_Body_Layer_Phase1_Spec.md (v1.0)
**Status:** Ready for implementation — answers the open questions
Q-Phase1-1 and Q-Phase1-2 from section 17 of the base specification
**Q-Phase1-3** (the `intent_summary` format) remains open, unchanged,
by decision of the project owner.

---

## 1. Q-Phase1-1: a hybrid sleep trigger through `WakefulnessState`

### Decision

Do not build a new "fatigue" heuristic in `nowa_body`. Use the `WakefulnessState` that already exists in the NOWA core (Borbély two-process model: Process S is homeostatic sleep pressure and grows with activity; Process C is the circadian component, a nocturnal pattern). This is architecturally sounder than a parallel logic: the same principle as "do not bypass the cognitive contour with external heuristics" (principle 0 of the parent specification), now applied to the decision "is it time to sleep".

### Why this is not a trivial substitution

`SandboxTrainer` called `sleep_cycle()` on a fixed `sleep_every_n_days` — a simple counter, with no reference to `WakefulnessState` at all. The live mode requires something else: a combination of two independent signals, neither of which by itself yields "hybridity".

### Contract of `SleepScheduler`

```python
"""nowa_body/sleep_scheduler.py"""

class SleepScheduler:
    """
    Decides, once per run_cycle() tick, whether the agent should sleep now.

    Combines two independent signals, exactly mirroring the human pattern
    the owner described: a scheduled nightly window, AND an early trigger
    when accumulated waking load crosses a threshold (the "very tired,
    goes to bed early" case).

    Does NOT implement sleep pressure itself — reads it from
    agent.wakefulness_state, which already models Process S/C. This
    scheduler is a thin decision wrapper, not a second source of truth.
    """

    def __init__(
        self,
        circadian_window: Tuple[int, int] = (2, 5),   # hour-of-day, e.g. 2am-5am
        fatigue_threshold: float = 0.85,               # Process S ceiling
        min_ticks_between_sleep: int = 3600,            # ~1 hour at 1Hz, avoid thrashing
    ):
        self.circadian_window = circadian_window
        self.fatigue_threshold = fatigue_threshold
        self.min_ticks_between_sleep = min_ticks_between_sleep
        self._ticks_since_last_sleep = 0

    def should_sleep(self, agent: Any, now: datetime) -> Tuple[bool, str]:
        """
        Returns (should_sleep, reason). reason is "circadian" or "fatigue"
        or "" — logged by the runtime, useful for diagnosing which trigger
        fired most often once the agent has run for a while.
        """
        self._ticks_since_last_sleep += 1
        if self._ticks_since_last_sleep < self.min_ticks_between_sleep:
            return False, ""

        if self._in_circadian_window(now):
            return True, "circadian"

        pressure = self._read_sleep_pressure(agent)
        if pressure is not None and pressure >= self.fatigue_threshold:
            return True, "fatigue"

        return False, ""

    def mark_slept(self) -> None:
        self._ticks_since_last_sleep = 0

    def _in_circadian_window(self, now: datetime) -> bool:
        start, end = self.circadian_window
        return start <= now.hour < end

    def _read_sleep_pressure(self, agent: Any) -> Optional[float]:
        """
        Reads Process S from agent.wakefulness_state defensively — the
        exact attribute/method name must be verified against the real
        wakefulness.py source before this is wired up (see Open Question
        Q-Phase1-1a below). Tries several plausible accessors so a naming
        mismatch degrades to "circadian-only" rather than crashing.
        """
        ws = getattr(agent, "wakefulness_state", None)
        if ws is None:
            return None
        for attr in ("process_s", "sleep_pressure", "homeostatic_pressure"):
            value = getattr(ws, attr, None)
            if isinstance(value, (int, float)):
                return float(value)
            if callable(value):
                try:
                    result = value()
                    if isinstance(result, (int, float)):
                        return float(result)
                except Exception:
                    continue
        return None
```

### Update of `runtime.py`

```python
class BusinessAgentRuntime:
    def __init__(self, agent, tool_registry, motor_adapter, approval_gate,
                encoder, sleep_scheduler: Optional[SleepScheduler] = None):
        ...
        self.sleep_scheduler = sleep_scheduler or SleepScheduler()

    def run_cycle(self, observations: Dict[str, Any]) -> dict:
        result = self._run_decision_cycle(observations)  # раздел 2 этого патча

        should_sleep, reason = self.sleep_scheduler.should_sleep(
            self.agent, now=datetime.now()
        )
        if should_sleep:
            sleep_manager = getattr(self.agent, "sleep_manager", None)
            if sleep_manager is not None and hasattr(sleep_manager, "sleep_cycle"):
                sleep_manager.sleep_cycle()
                self.sleep_scheduler.mark_slept()
            result["slept"] = True
            result["sleep_reason"] = reason
        return result
```

### Open sub-question Q-Phase1-1a (must be closed before implementation)

Before writing `_read_sleep_pressure` in its final form, the real `wakefulness.py` must be opened and the name of the Process S attribute confirmed, together with whether it grows naturally from the agent's activity (calls to `step()`) or requires an explicit `wakefulness_state.accumulate()` on every tick. This is the same class of check as Q-v2.0-1/2/3 in the sandbox: three times in this project, ignorance of the exact core API led to silent failures (mutation of Path, absence of ACTION events). The check is therefore laid in advance, not after the fact.

```bash
grep -n "process_s\|class WakefulnessState\|def accumulate\|circadian" src/wakefulness.py
```

If `WakefulnessState` does not grow automatically from ticks, `runtime.py` must explicitly call the pressure-accumulation method on every `run_cycle()`, before the `should_sleep` check. The exact call site is settled once the source has been read.

### Test cases

```python
class TestSleepScheduler:

    def test_circadian_window_triggers(self):
        scheduler = SleepScheduler(circadian_window=(2, 5), min_ticks_between_sleep=0)
        agent = make_test_agent()  # no wakefulness_state, pressure=None
        now = datetime(2026, 1, 1, 3, 0)  # 3am, inside window
        should, reason = scheduler.should_sleep(agent, now)
        assert should is True
        assert reason == "circadian"

    def test_fatigue_triggers_outside_window(self):
        scheduler = SleepScheduler(fatigue_threshold=0.8, min_ticks_between_sleep=0)
        agent = make_test_agent_with_pressure(0.9)
        now = datetime(2026, 1, 1, 14, 0)  # 2pm, outside circadian window
        should, reason = scheduler.should_sleep(agent, now)
        assert should is True
        assert reason == "fatigue"

    def test_neither_signal_no_sleep(self):
        scheduler = SleepScheduler(fatigue_threshold=0.8, min_ticks_between_sleep=0)
        agent = make_test_agent_with_pressure(0.3)
        now = datetime(2026, 1, 1, 14, 0)
        should, reason = scheduler.should_sleep(agent, now)
        assert should is False

    def test_min_ticks_prevents_thrashing(self):
        """Even a fully fatigued agent must not sleep every tick."""
        scheduler = SleepScheduler(fatigue_threshold=0.1, min_ticks_between_sleep=100)
        agent = make_test_agent_with_pressure(0.99)
        now = datetime(2026, 1, 1, 14, 0)
        results = [scheduler.should_sleep(agent, now)[0] for _ in range(50)]
        assert not any(results)  # min_ticks not yet reached

    def test_mark_slept_resets_counter(self):
        scheduler = SleepScheduler(min_ticks_between_sleep=5)
        agent = make_test_agent()
        for _ in range(5):
            scheduler.should_sleep(agent, datetime(2026, 1, 1, 14, 0))
        scheduler.mark_slept()
        should, _ = scheduler.should_sleep(agent, datetime(2026, 1, 1, 2, 0))
        assert should is False  # counter reset, min_ticks not reached again yet
```

---

## 2. Q-Phase1-2: the tick model — `agent.step()` once a second

### Decision

`run_cycle()` is called by a timer about once a second, not by an MCP event. Each tick is a full pass of the cognitive pipeline on the **current** observation snapshot (which may be unchanged from the previous tick if there were no new MCP events). This removes the question "several ProposedAction per cycle" as it was posed: an hour of work yields 3,600 ticks, and an order for goods and a letter to a supplier naturally become decisions on different ticks.

### Separating tick rate from sensor-update rate

A critically important consequence: **MCP READ tools must not be polled every second**. That is either a load on the external system (1C) or simply pointless (warehouse stock does not change every second). The two rates must be decoupled:

```
Cognitive-pipeline tick:        ~1 Hz  (agent.step() is called every second)
Observation update (sensors):   ~1/300 Hz (once every 5 minutes, configurable)
                                 or event-driven (a webhook from the MCP server)
```

```python
class BusinessAgentRuntime:
    def __init__(self, ..., sensor_refresh_interval_s: float = 300.0):
        self.sensor_refresh_interval_s = sensor_refresh_interval_s
        self._cached_observations: Dict[str, Any] = {}
        self._last_sensor_refresh: Optional[datetime] = None

    def tick(self, sensor_fetcher: Callable[[], Dict[str, Any]]) -> dict:
        """
        Called ~once per second by the host scheduler. sensor_fetcher is
        only actually invoked when the refresh interval has elapsed —
        most ticks reuse the cached observation snapshot, exactly as a
        person doesn't re-check their inbox every second even while
        continuously "paying attention".
        """
        now = datetime.now()
        if self._should_refresh_sensors(now):
            self._cached_observations = sensor_fetcher()
            self._last_sensor_refresh = now

        return self.run_cycle(self._cached_observations)

    def _should_refresh_sensors(self, now: datetime) -> bool:
        if self._last_sensor_refresh is None:
            return True
        elapsed = (now - self._last_sensor_refresh).total_seconds()
        return elapsed >= self.sensor_refresh_interval_s
```

### Episode storage does not grow on every tick

An important constraint, already observed in the design (the sandbox confirmed it): `hippocampus.store()` is called **only** when a tick leads to a concrete `ProposedAction`, not on every tick. Ticks where `action_type == "wait_and_monitor"` create no episode (see `_store_order_experience` in the sandbox — it is called only inside `if order_params is not None`). At 1 Hz, with the overwhelming majority of ticks being `wait_and_monitor`, the hippocampus is not flooded with meaningless records of "nothing happened" — only real decisions are stored.

**Explicit constraint B8** (supplements section 10 of the base specification):

| # | Constraint |
|---|---|
| **B8** | `hippocampus.store()` is called only for a non-empty `ProposedAction`; ticks with `action_type == "wait_and_monitor"` create no episode |
| **B9** | The sensor-update rate (`sensor_refresh_interval_s`) is decoupled from the cognitive tick rate; `agent.step()` may be called many times in a row on an unchanged context |

### Update of `run_cycle`: split into `tick()` and an internal `run_cycle()`

`run_cycle(observations)` from the base specification (section 9) remains a pure function, "one pipeline pass on a given snapshot". It is useful for tests and for the sandbox, where observations are already prepared. The new `tick()` (section 2 of this patch) is a wrapper that adds sensor caching and calls `run_cycle()` inside. The host (scheduler, cron, or event loop) calls `tick()`, not `run_cycle()` directly, in live mode.

### Test cases

```python
class TestTickSensorCaching:

    def test_sensor_fetcher_not_called_every_tick(self):
        runtime = make_test_runtime(sensor_refresh_interval_s=300.0)
        fetcher = MagicMock(return_value={"tool_results": {}})
        for _ in range(10):
            runtime.tick(fetcher)
        assert fetcher.call_count == 1  # only the first tick refreshes

    def test_sensor_fetcher_called_after_interval_elapses(self):
        runtime = make_test_runtime(sensor_refresh_interval_s=0.0)
        fetcher = MagicMock(return_value={"tool_results": {}})
        runtime.tick(fetcher)
        runtime.tick(fetcher)
        assert fetcher.call_count == 2  # zero interval => refresh every tick

    def test_wait_and_monitor_does_not_store_episode(self):
        """B8: quiet ticks must not flood the hippocampus."""
        agent = make_test_agent()
        runtime = make_test_runtime(agent=agent)
        n_before = len(agent.hippocampus.experiences)
        for _ in range(100):
            runtime.run_cycle({"tool_results": {}})  # yields wait_and_monitor
        n_after = len(agent.hippocampus.experiences)
        assert n_after == n_before

    def test_action_tick_does_store_episode(self):
        agent = make_test_agent_that_always_acts()
        runtime = make_test_runtime(agent=agent)
        n_before = len(agent.hippocampus.experiences)
        runtime.run_cycle({"tool_results": {"mcp__x__y": {"status": "urgent"}}})
        n_after = len(agent.hippocampus.experiences)
        assert n_after > n_before
```

---

## 3. Definition of Done for patch v1.1

- [ ] `sleep_scheduler.py` is implemented, and `_read_sleep_pressure` is explicitly marked as "check the API before finalization" (Q-Phase1-1a closed by reading the source of `wakefulness.py`)
- [ ] All `TestSleepScheduler` tests are green
- [ ] `BusinessAgentRuntime.tick()` is implemented with the sensor rate separated from the cognitive tick
- [ ] `test_sensor_fetcher_not_called_every_tick` is green — confirms B9
- [ ] `test_wait_and_monitor_does_not_store_episode` is green — confirms B8
- [ ] Section 16 (implementation order) of the base specification is updated: day 6 ("Assembly") now includes `sleep_scheduler.py` and the `tick()` wrapper, not only `run_cycle()`

---

## 4. Q-Phase1-3 — status: deferred

The `intent_summary` format for the approval UI remains the current implementation (`_summarize()` — a simple string). The decision on an NLG layer or a role-specific templating engine is deferred until Phase 2, when a real human approval interface (Slack/email) will exist and will actually need it. For MockMCP testing, the current format is sufficient.

---

*Patch v1.1 to the Phase 1 Body Layer specification. It answers Q-Phase1-1 (hybrid sleep through WakefulnessState) and Q-Phase1-2 (a tick model at ~1 Hz instead of event-driven calls). Q-Phase1-3 is deliberately deferred.*
