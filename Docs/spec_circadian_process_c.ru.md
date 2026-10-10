# Циркадный процесс C

English version: [spec_circadian_process_c.en.md](spec_circadian_process_c.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Статус

Реализовано в `WakefulnessState` (23 марта 2026 г.).

---

## Модель

Используется формализация Borbély:

```text
sleep_pressure = Process S
circadian_signal = Process C
wake_drive = Process C - Process S
```

Где:

```text
Process C: C(t) = A * sin(2π * t / T + phase)
```

---

## Влияние на бодрствование

```text
alertness = base_alertness - sleep_pressure + circadian_signal
```

В проекте:
- `sleep_pressure = wakefulness`
- `base_alertness = 1.0` (по умолчанию)
- `cognitive_reliability = clamp(alertness, 0..1)`

---

## Параметры

```python
circadian_period_hours = 24.0
circadian_amplitude = 0.3
circadian_phase = 0.0
```

---

## Привязка к интерфейсу

В `src/wakefulness.py`:
- `get_circadian_signal()`
- `get_wake_drive()`  # `Process C - Process S`
- `get_alertness(base_alertness=None, clamp=True)`

В `src/agent.py` (`get_wakefulness_state()`):
- `circadian_signal`
- `wake_drive`
- `alertness`

Сохранение (`src/agent.py`, `src/storage.py`):
- `circadian_time_hours`
- `circadian_period_hours`
- `circadian_amplitude`
- `circadian_phase`

---

## Проверка

Покрыто тестами:
- `tests/test_wakefulness.py::TestCircadianProcessC`
- `tests/test_agent_lifetime_save_load.py::test_wakefulness_and_autonomous_runtime_persistence`
