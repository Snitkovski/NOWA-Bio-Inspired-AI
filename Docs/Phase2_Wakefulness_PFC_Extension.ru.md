# Расширение фазы 2: бодрствование, циркадный процесс C и модуляция префронтальной коры

English version: [Phase2_Wakefulness_PFC_Extension.en.md](Phase2_Wakefulness_PFC_Extension.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Статус

Реализовано в коде (`src/wakefulness.py`, `src/agent.py`, `src/storage.py`) по состоянию на 23 марта 2026 г.

---

## Цель

Поддерживать физиологическое состояние бодрствования, которое:
- не принимает решений,
- не является эмоцией или нейромедиатором,
- модулирует надёжность когнитивного контроля (PFC),
- влияет на существующую систему нейромедиаторов через отдельные дельты,
- объединяет гомеостатическое давление сна (Process S) и циркадный сигнал (Process C).

---

## WakefulnessState (актуальная модель)

```python
class WakefulnessState:
    wakefulness: float              # Process S, [0.0 .. 1.0]
    last_update_ts: float
    accumulated_waking_time: float
    total_sleep_time: float

    circadian_time_hours: float
    circadian_period_hours: float   # default 24.0
    circadian_amplitude: float      # default 0.3
    circadian_phase: float          # default 0.0
```

Интерпретация:
- `wakefulness = 0.0` — минимальное давление сна (отдохнувшее состояние).
- `wakefulness = 1.0` — высокая депривация сна.

---

## Process S (давление сна)

### Накопление во время бодрствования

```text
wakefulness += dt * ACCUMULATION_RATE
ACCUMULATION_RATE = 1 / (16 * 60 * 60)
```

### Восстановление во время сна

```text
wakefulness -= dt * RECOVERY_RATE
RECOVERY_RATE = 1 / (8 * 60 * 60)
```

Ограничение: значение всегда ограничивается диапазоном `[0, 1]`.

---

## Process C (циркадный ритм)

Формула:

```text
C(t) = A * sin(2π * t / T + phase)
```

Где:
- `A = circadian_amplitude` (по умолчанию `0.3`)
- `T = circadian_period_hours` (по умолчанию `24h`)
- `t = circadian_time_hours`

В текущей реализации `circadian_time_hours` продвигается при:
- `update_waking(...)`
- `update_sleeping(...)`

---

## Производные сигналы бодрствования (Borbély)

```text
sleep_pressure = Process S = wakefulness
circadian_signal = Process C
wake_drive = circadian_signal - sleep_pressure
alertness = base_alertness - sleep_pressure + circadian_signal
```

По умолчанию:
- `base_alertness = 1.0`
- `cognitive_reliability = clamp(alertness, 0..1)`

---

## Влияние на нейромедиаторы

При каждом обновлении:

```text
cortisol       += wakefulness * 0.01
norepinephrine += wakefulness * 0.02
serotonin      -= wakefulness * 0.015
```

Ограничения:
- все значения проходят ограничение диапазона,
- dopamine не изменяется напрямую этим модулем.

---

## Влияние на PFC

### Сила сигнала и шум

```text
get_pfc_signal_strength_modifier() -> 1.0
get_pfc_signal_noise_modifier()    -> 1.0 + wakefulness * 0.7
```

Смысл:
- номинальная сила PFC не меняется,
- усталость увеличивает шум и ненадёжность сигнала.

### Конфликтное понижение веса PFC

```text
effective_PFC_weight *= (1 - conflict * wakefulness)
```

---

## Сохранение и загрузка

Сохраняются и восстанавливаются поля:
- `wakefulness`, `last_update_ts`, `accumulated_waking_time`, `total_sleep_time`
- `circadian_time_hours`, `circadian_period_hours`, `circadian_amplitude`, `circadian_phase`

---

## Тест-кейсы (актуально)

1. Накопление Process S (8 ч ≈ 0.5, 16 ч ≈ 1.0).
2. Восстановление Process S во сне (8 ч от высокой усталости стремится к 0).
3. Монотонный рост cortisol при росте `wakefulness`.
4. Сила PFC постоянна, шум PFC растёт с `wakefulness`.
5. `effective_PFC_weight` снижается при высоком конфликте и высокой усталости.
6. Process C:
   - `t=0` → сигнал около `0`,
   - `t=T/4` → сигнал около `+amplitude`,
   - фазовый сдвиг корректно изменяет значение.
7. Цикл сохранения и загрузки сохраняет циркадные параметры.
