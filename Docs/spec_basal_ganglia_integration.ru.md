# Обязательная спецификация интеграции базальных ганглиев (реализовано)

English version: [spec_basal_ganglia_integration.en.md](spec_basal_ganglia_integration.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


Последняя проверка: 25 февраля 2026 г.

Этот документ — источник истины для потока выбора действия в текущей кодовой базе.

---

## 1. Цель

Сделать базальные ганглии обязательной стадией принятия решения.
Ни одно окончательное действие не может обойти базальные ганглии и таламическое пропускание.

---

## 2. Обязательный поток решения

Текущий поток времени выполнения:

```text
ActionSelector.compute_pressures(...) -> pressure_vector
                     |
                     v
BasalGangliaGate.process(...)
                     |
                     v
ThalamicGate.select(...)
                     |
                     v
final_action (or NO_ACTION)
```

Этот поток используется в:
1. живых решениях `Agent.step(...)`
2. пути предложения внутреннего моделирования в `InternalSimulationLoop`

---

## 3. Разделение ответственности (без двойной модуляции)

### Ответственность селектора
`ActionSelector.compute_pressures(...)` возвращает только корковую и когнитивную конкуренцию:
1. следы гиппокампа
2. корковые паттерны
3. давление намерения
4. консультативное давление временной цепи
5. консультативное давление слоя предсказания

`compute_pressures(...)` не применяет биологическую модуляцию.

### Ответственность базальных ганглиев
`BasalGangliaGate.process(...)` применяет биологическую модуляцию:
1. дофамин (усиление Go)
2. кортизол и аверсивный сигнал (усиление NoGo)
3. вклад привычки
4. модуляторы канала (`go_weight`, `nogo_weight`)
5. модуляция CER:
   - `exploration_bias`
   - `decision_threshold_shift`
   - `habit_gain_scale`

Инвариант:
1. аффект и угроза не должны применяться и в селекторе, и в базальных ганглиях за один проход конвейера.

---

## 4. Контракт процесса базальных ганглиев

Вход:
1. `pressure_vector`
2. `dopamine_level`
3. `cortisol_level`
4. `norepinephrine_level` (для подсказки температуры и связи с финальным пропусканием)
5. `habit_strengths`
6. `aversive_signal`
7. `channel_modulators`
8. `exploration_bias`
9. `decision_threshold_shift`
10. `habit_gain_scale`

Текущая формула на действие:

```text
uncertainty_bonus_raw = exploration_bias * max(0, 0.25 - |pressure|) * cer_bonus_gain
uncertainty_bonus = min(cer_bonus_cap_abs, uncertainty_bonus_raw)

habit_term = beta * habit_gain_scale * habit
Go_raw = (pressure * (1 + alpha * dopamine) + habit_term + uncertainty_bonus) * go_weight

go_cap = (
    cer_go_pressure_cap_ratio * |pressure * (1 + alpha * dopamine)|
    + habit_term
    + cer_bonus_cap_abs
) * go_weight
Go = min(Go_raw, go_cap)

NoGo = (|pressure| * (gamma * cortisol + delta * aversive_signal)) * nogo_weight
Net = Go - NoGo
effective_threshold = threshold + decision_threshold_shift
gated_score = max(Net - effective_threshold, 0)
```

Инварианты безопасности CER:
1. `uncertainty_bonus <= cer_bonus_cap_abs`
2. `Go <= go_cap`
3. `habit_gain_scale` ограничивается в базальных ганглиях

---

## 5. Семантика бодрствования и усталости

Когнитивная надёжность на основе бодрствования должна интерпретироваться так:

```text
wake_mod = get_cognitive_reliability() if available else (1 - wakefulness)  # legacy fallback
```

Текущая семантика `WakefulnessState.get_cognitive_reliability()`:

```text
sleep_pressure = Process S
circadian_signal = Process C
reliability = clamp(base_alertness - sleep_pressure + circadian_signal, 0..1)
```

Итак:
1. отдохнувшее состояние даёт более высокую когнитивную надёжность
2. утомлённое состояние даёт меньший вклад префронтальной коры

---

## 6. Угроза и аверсивный сигнал

В канальном `choose(...)` аверсивный путь таков:

```text
aversive_signal = threat
```

Угроза читается из:
1. `affective_space.axes["stress"]` (предпочтительно)
2. запасного прежнего `affect_state.threat`

Никакой дополнительной произвольной добавки давления угрозы вне этого контракта не допускается.

---

## 7. Контракт таламического пропускания

`ThalamicGate.select(gated_scores, norepinephrine_level, exploration_bias=0.0)`:
1. возвращает `NO_ACTION`, когда все пропущенные оценки нулевые или отсутствуют
2. иначе выбирает по softmax среди неотрицательных пропущенных оценок
3. использует температуру, модулированную норадреналином и CER:
   `temperature = base_temperature * (1 + ne_gain * norepinephrine) * (1 + 0.8 * exploration_bias)`

Инвариант:
1. если пропускание возвращает `NO_ACTION`, среда выполнения не должна заменять его случайным действием.

---

## 8. Ограничитель поведения нейтрального состояния

Принудительное базовое давление селектора в полностью нейтральном состоянии запрещено.

Текущий компромисс времени выполнения в `Agent.step(...)`:
1. если вектор давления селектора полностью нулевой
2. и контекст непуст
3. вводится крошечное стартовое давление (`0.12`) для одного действия, выведенного из контекста

Это сохраняет отзывчивость на контекст, не принуждая к действию в подлинно нейтральных состояниях без входа.

---

## 9. Паритет внутреннего моделирования

Предложение внутреннего моделирования должно оставаться согласованным с живой средой выполнения:

```text
compute_pressures -> BG.process -> ThalamicGate.select
```

Это предотвращает расхождение между смоделированным и реальным выбором.

---

## 10. Тестовый контракт

Обязательное регрессионное покрытие:
1. `tests/test_basal_ganglia.py`
2. `tests/test_basal_ganglia_integration_spec.py`

Обязательные сценарии:
1. высокий дофамин усиливает выход Go
2. высокий кортизол подавляет выход действия
3. привычки могут доминировать над слабым давлением
4. нулевое давление и аверсивные условия могут дать `NO_ACTION`
5. предложение внутреннего моделирования совпадает с живым конвейером базальных ганглиев и таламуса
6. бонус исследования CER ограничен потолком
7. масштабирование выигрыша привычки CER усиливает привычный канал в условиях, подобных стрессу
