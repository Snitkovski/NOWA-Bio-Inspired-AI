# NOWA Body Layer — Патч v1.1

English version: [NOWA_Body_Layer_Phase1_Patch_v1.1.en.md](NOWA_Body_Layer_Phase1_Patch_v1.1.en.md)

## Аннотация

Патч v1.1 закрывает вопросы фазы 1 о моменте сна и о частоте шага, не строя в `nowa_body` вторую модель усталости. `SleepScheduler` читает уже существующее в ядре состояние бодрствования по двухпроцессной схеме Борбели: процесс S — гомеостатическое давление сна, растущее с активностью, процесс C — циркадная компонента. На каждом тике планировщик возвращает пару «спать ли» и причину `circadian` либо `fatigue`. Окно по умолчанию — часы от 2 включительно до 5 исключительно. Порог усталости равен 0,85. Минимальный промежуток между снами — 3600 тиков, около часа при шаге 1 Гц. До истечения промежутка сон не начинается. Если атрибут давления прочитать не удаётся, планировщик остаётся при одном циркадном триггере и не падает. Точное имя поля процесса S патч требует сверить с `wakefulness.py` до окончательной привязки: давление может расти от активности само либо требовать явного накопления на тик.

Вторая часть разводит когнитивный тик и опрос сенсоров. Хозяин вызывает `tick()` около одного раза в секунду. Функция чтения сенсоров исполняется, когда с прошлого обновления прошло не менее `sensor_refresh_interval_s`, по умолчанию 300 секунд; остальные тики повторяют `run_cycle` на кэшированном снимке. За час это 3600 решений на одном и том же или редко обновляемом наблюдении, так что заказ и письмо оказываются решениями разных тиков. `hippocampus.store` вызывается только при непустом `ProposedAction`. Тик с действием `wait_and_monitor` эпизода не создаёт: это ограничение B8. Частота сенсоров не равна частоте шага: это ограничение B9. `run_cycle` остаётся проходом по уже готовому снимку и пригоден для тестов. Вопрос о формате `intent_summary` патч не меняет и оставляет открытым.

Критерий готовности патча — реализация планировщика после сверки API ядра, зелёные проверки обоих триггеров сна, реализация `tick` с кэшем сенсоров и тесты, в которых за десять тиков при интервале 300 с читатель сенсоров вызывается один раз, а сто тиков ожидания не увеличивают число эпизодов. Сборка фазы 1 включает планировщик и обёртку `tick`, а не только чистый `run_cycle`.

---

**Базовый документ:** NOWA_Body_Layer_Phase1_Spec.md (v1.0)
**Статус:** готово к реализации — отвечает на открытые вопросы
Q-Phase1-1 и Q-Phase1-2 из раздела 17 базовой спецификации
**Q-Phase1-3** (формат intent_summary) — остаётся открытым, без изменений,
по решению владельца проекта.

---

## 1. Q-Phase1-1: гибридный триггер сна через `WakefulnessState`

### Решение

Не строить новую эвристику "усталости" в `nowa_body`. Использовать уже
существующий в ядре NOWA `WakefulnessState` (двухпроцессная модель Борбели:
процесс S — гомеостатическое давление сна, растёт с активностью;
процесс C — циркадный компонент, ночной паттерн). Это архитектурно
правильнее, чем параллельная логика: тот же принцип, что "не обходить
когнитивный контур внешними эвристиками" (принцип 0 родительской
спецификации), применённый теперь к самому решению "пора ли спать".

### Почему это не тривиальная замена

`SandboxTrainer` вызывал `sleep_cycle()` по фиксированному
`sleep_every_n_days` — простой счётчик, без обращения к `WakefulnessState`
вообще. Живой режим требует другого: комбинации двух независимых
сигналов, ни один из которых сам по себе не даёт "гибридности".

### Контракт `SleepScheduler`

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

### Обновление `runtime.py`

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

### Открытый под-вопрос Q-Phase1-1a (обязателен к закрытию до реализации)

Прежде чем писать `_read_sleep_pressure` в финальном виде — нужно
открыть реальный `wakefulness.py` и убедиться, как называется атрибут
Process S и растёт ли он естественным образом от активности агента
(вызовов `step()`), или требует явного `wakefulness_state.accumulate()`
на каждый тик. Это тот же класс проверки, что Q-v2.0-1/2/3 в
песочнице — три раза за этот проект незнание точного API ядра
приводило к тихим провалам (мутация Path, отсутствие ACTION events),
поэтому здесь закладываем проверку заранее, а не постфактум.

```bash
grep -n "process_s\|class WakefulnessState\|def accumulate\|circadian" src/wakefulness.py
```

Если `WakefulnessState` не растёт автоматически от тиков — `runtime.py`
должен явно вызывать метод накопления давления на каждый `run_cycle()`,
до проверки `should_sleep`. Точное место вызова уточняется по факту
чтения исходника.

### Тест-кейсы

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

## 2. Q-Phase1-2: тиковая модель — `agent.step()` раз в секунду

### Решение

`run_cycle()` вызывается по таймеру ~1 раз в секунду, а не по MCP-событию.
Каждый тик — полный проход когнитивного pipeline на **текущем** снапшоте
наблюдений (который может не измениться с прошлого тика, если новых
MCP-событий не было). Это устраняет саму постановку вопроса "несколько
ProposedAction за цикл" — за час работы будет 3600 тиков, и заказ товара,
и письмо поставщику естественным образом окажутся решениями на разных
тиках.

### Разделение частоты тика и частоты обновления сенсоров

Критически важное следствие: **опрашивать MCP READ-тулы каждую секунду
нельзя** — это либо нагрузка на внешнюю систему (1С), либо просто
бессмысленно (остатки на складе не меняются каждую секунду). Нужно
развязать:

```
Тик когнитивного pipeline:     ~1 Hz  (agent.step() вызывается каждую секунду)
Обновление наблюдений (сенсоры): ~1/300 Hz (раз в 5 минут, конфигурируемо)
                                  или event-driven (webhook от MCP-сервера)
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

### Хранение эпизодов не раздувается на каждый тик

Важное ограничение, уже соблюдённое в дизайне (сандбокс это подтвердил):
`hippocampus.store()` вызывается **только** когда тик приводит к
конкретному `ProposedAction`, не на каждом тике. Тики, где
`action_type == "wait_and_monitor"`, не создают эпизод (см.
`_store_order_experience` в песочнице — вызывается только внутри
`if order_params is not None`). При 1 Hz и подавляющем большинстве
`wait_and_monitor`-тиков гиппокамп не переполняется бессмысленными
записями "ничего не произошло" — только реальные решения.

**Явное ограничение B8** (дополняет раздел 10 базовой спецификации):

| # | Ограничение |
|---|---|
| **B8** | `hippocampus.store()` вызывается только при непустом `ProposedAction`; тики с `action_type == "wait_and_monitor"` не создают эпизод |
| **B9** | Частота обновления сенсоров (`sensor_refresh_interval_s`) развязана с частотой когнитивного тика; `agent.step()` может вызываться на неизменном контексте много раз подряд |

### Обновление `run_cycle`: разделение на `tick()` и внутренний `run_cycle()`

`run_cycle(observations)` из базовой спецификации (раздел 9) остаётся
как чистая функция "один проход pipeline на данном снапшоте" — полезна
для тестов и для песочницы, где наблюдения уже готовы. Новый `tick()`
(раздел 2 этого патча) — обёртка, которая добавляет кэширование сенсоров
и вызывает `run_cycle()` внутри. Хост (планировщик, cron или цикл событий)
вызывает `tick()`, не `run_cycle()` напрямую, в живом режиме.

### Тест-кейсы

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

## 3. Критерий готовности патча v1.1

- [ ] `sleep_scheduler.py` реализован, `_read_sleep_pressure` явно
      помечен как "проверить API до финализации" (Q-Phase1-1a закрыт
      чтением исходника `wakefulness.py`)
- [ ] Все тесты `TestSleepScheduler` зелёные
- [ ] `BusinessAgentRuntime.tick()` реализован с разделением частоты
      сенсоров/когнитивного тика
- [ ] `test_sensor_fetcher_not_called_every_tick` зелёный — подтверждает
      B9
- [ ] `test_wait_and_monitor_does_not_store_episode` зелёный —
      подтверждает B8
- [ ] Обновлён раздел 16 (порядок реализации) базовой спецификации:
      день 6 ("Сборка") теперь включает `sleep_scheduler.py` и
      `tick()`-обёртку, не только `run_cycle()`

---

## 4. Q-Phase1-3 — статус: отложен

Формат `intent_summary` для интерфейса подтверждения остаётся текущей реализацией
(`_summarize()` — простая строка). Решение по NLG-слою или
роль-специфичному шаблонизатору откладывается до Фазы 2, когда
появится реальный человеческий интерфейс подтверждения (Slack/email),
которому это будет действительно нужно. Для MockMCP-тестирования
текущего формата достаточно.

---

*Патч v1.1 к спецификации Body Layer Фазы 1. Отвечает на Q-Phase1-1
(гибридный сон через WakefulnessState) и Q-Phase1-2 (тиковая модель
~1 Гц вместо вызовов по событиям). Q-Phase1-3 сознательно отложен.*
