# Спецификация: ACC-модуляция конфликта с защитой от динамической нестабильности

English version: [spec_acc_conflict_modulation.en.md](spec_acc_conflict_modulation.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

---

## 1. Цель

Устранить архитектурный дефект:

> возбуждение и стресс ACC вне формул `conflict_score`

и внедрить двустороннюю динамику между конфликтом и нейромодуляторами.

Одновременно обеспечить:

- устойчивость системы
- отсутствие разгонной динамики
- обратную совместимость поведения агента

---

## 2. Биологическая модель

ACC кодирует когнитивный конфликт и усиливается системой LC-NE (возбуждение) и стрессом (кортизол):

```
perceived_conflict =
    raw_conflict
    × arousal_gain
    × stress_gain
```

---

## 3. Архитектурное положение

Модуляция выполняется внутри `NeuromodulatorState`.

**Поток сигналов:**

```
Среда
    ↓
raw_conflict
    ↓
модуляция ACC
    ↓
effective_conflict
    ↓
обновление нейромодуляторов
```

---

## 4. Формула

```
effective_conflict =
    raw_conflict
    × (1 + k_NE   × (NE − baseline_NE))
    × (1 + k_CORT × cortisol)
```

| Параметр  | Значение |
|-----------|----------|
| `k_NE`    | 0.5      |
| `k_CORT`  | 0.7      |

---

## 5. Ограничения

### 5.1 Диапазоны входных сигналов

```
0 ≤ raw_conflict    ≤ 1
0 ≤ norepinephrine  ≤ 1
0 ≤ cortisol        ≤ 1
```

Все значения проходят: `clamp(x, 0, 1)`.

### 5.2 Ограничение выхода

После вычисления:

```
effective_conflict = clamp(effective_conflict, 0, 1)
```

### 5.3 Ограничение коэффициента усиления

```
0.5 ≤ arousal_gain ≤ 2.0
0.5 ≤ stress_gain  ≤ 2.0
```

> Предотвращает разгонную динамику.

---

## 6. Алгоритм

**Шаг 1 — нормализация конфликта:**

```
conflict_v = clamp(conflict, 0, 1)
```

**Шаг 2 — вычисление `arousal_gain`:**

```
arousal_gain = 1 + k_NE × (NE − baseline_NE)
arousal_gain = clamp(arousal_gain, 0.5, 2.0)
```

**Шаг 3 — вычисление `stress_gain`:**

```
stress_gain = 1 + k_CORT × cortisol
stress_gain = clamp(stress_gain, 0.5, 2.0)
```

**Шаг 4 — вычисление `effective_conflict`:**

```
effective_conflict = conflict_v × arousal_gain × stress_gain
```

**Шаг 5 — ограничение диапазона:**

```
effective_conflict = clamp(effective_conflict, 0, 1)
```

---

## 7. Использование effective_conflict

**Было:**

```python
NE   += NE_CONFLICT   × conflict
CORT += CORT_CONFLICT × conflict
```

**Стало:**

```python
NE   += NE_CONFLICT   × effective_conflict
CORT += CORT_CONFLICT × effective_conflict
```

---

## 8. Защита от системных рисков

### 8.1 Положительная петля стресс → конфликт → стресс

**Риск:** `conflict → cortisol → усиление конфликта → cortisol`.

**Решение:** `stress_gain ≤ 2` и малый коэффициент `CORT_CONFLICT`.

### 8.2 Разгонная динамика NE

**Риск:** `conflict → NE → conflict`.

**Решение:** ограничить `arousal_gain`, использовать центрирование на базовом уровне `NE − baseline_NE`.

### 8.3 Разрушение обучения TD

Конфликт не должен напрямую влиять на дофамин:

```
conflict → NE, CORT    допустимо
conflict → dopamine    запрещено
```

### 8.4 Неустойчивость аффективной системы

**Риск:** `NE → возбуждение → conflict → NE`.

**Решение:** `arousal_gain ≤ 2` и ограничение аффективных осей.

---

## 9. Требования к реализации

**Метод:** `NeuromodulatorState._compute_effective_conflict()`

**Сигнатура:**

```python
_compute_effective_conflict(conflict: float) -> float
```

**Требования:**

- чистая функция
- не изменяет состояние
- использует текущие значения NE и cortisol

---

## 10. Инварианты системы

После обновления должны выполняться:

```
0 ≤ dopamine        ≤ 1
0 ≤ norepinephrine  ≤ 1
0 ≤ serotonin       ≤ 1
0 ≤ cortisol        ≤ 1
0 ≤ acetylcholine   ≤ 1
```

---

## 11. Тест-кейсы

### Тест 1 — базовый уровень

**Вход:** `conflict = 0.5`, `NE = 0.1`, `cortisol = 0`.

**Ожидается:** `effective_conflict = 0.5`.

### Тест 2 — высокое возбуждение

**Вход:** `conflict = 0.5`, `NE = 0.6`, `cortisol = 0`.

**Ожидается:** `effective_conflict ≈ 0.625`.

### Тест 3 — высокий стресс

**Вход:** `conflict = 0.5`, `cortisol = 0.5`.

**Ожидается:** `effective_conflict ≈ 0.675`.

### Тест 4 — комбинированный эффект

**Вход:** `conflict = 0.5`, `NE = 0.6`, `cortisol = 0.5`.

**Ожидается:** `effective_conflict ≈ 0.84`.

### Тест 5 — насыщение

**Вход:** `conflict = 1`, `NE = 1`, `cortisol = 1`.

До ограничения: `2.46`. После ограничения: `1.0`.

### Тест 6 — нулевой конфликт

**Вход:** `conflict = 0`.

**Результат:** `effective_conflict = 0`.

---

## 12. Интеграционные тесты

### Тест устойчивости

1000 итераций с `conflict = 0.6`.

**Проверяется:** NE не уходит в насыщение, cortisol не уходит в насыщение.

### Тест стресс-динамики

10 шагов с `conflict = 0.8`.

**Ожидается:** плавный рост cortisol, затем стабилизация.

---

## 13. Критерии принятия

Реализация считается корректной, если:

- все тесты проходят
- динамика системы устойчива
- базовое поведение агента не меняется
- нейромодуляторы остаются в диапазоне `[0, 1]`

---

## 14. Результат

**После внедрения:**

```
конфликт
    ↓
модуляция ACC
    ↓
effective_conflict
    ↓
NE / cortisol
```

**Вместо прежней:**

```
конфликт → нейромодуляторы
```

---

## 15. Реализация в коде (актуально на 2026-03-24)

Файл: `src/neuromodulators.py`, класс `NeuromodulatorState`.

Текущая реализация расширяет базовую формулу этой спецификации дополнительной стабилизацией:

1. Нелинейное ограничение чувствительности коэффициента усиления:
```python
bounded_delta(x) = x / (1 + abs(x))
arousal_gain = 1 + k_NE * bounded_delta(NE - baseline_NE)
stress_gain  = 1 + k_CORT * max(0, bounded_delta(CORT - baseline_CORT))
```

2. Серотониновое ингибирование и мягкая нормализация:
```python
inhibition_gain = clamp(1 - k_HT * max(0, HT - baseline_HT), ACC_INHIBITION_MIN, 1.0)
modulated = conflict * arousal_gain * stress_gain * inhibition_gain
effective_conflict = modulated / (1 + ACC_SOFT_NORM * modulated)
```

3. Временная динамика ACC (фильтр нижних частот):
```python
alpha = 1 - exp(-dt / ACC_CONFLICT_TAU)
trace_next = trace + alpha * (target - trace)
```

4. Разделение каналов конфликта:
- `cognitive_conflict` влияет на ветку `NE`,
- `affective_conflict` влияет на ветку `CORT`,
- `combined_conflict` ведётся отдельным следом как интегральная метрика ACC и используется в гейте 5-HT.

5. Симметричная семантика `None` для разделённых конфликтов:
- если оба канала `None`, оба берутся из `conflict`,
- если один канал `None`, он копируется из второго.

6. Гомеостатическая стабилизация:
```python
NE   += ACC_NE_HOMEOSTATIC_DECAY   * (BASELINE_NE   - NE)
CORT += ACC_CORT_HOMEOSTATIC_DECAY * (BASELINE_CORT - CORT)
```

7. Временной шаг согласован в одном обновлении:
- `dt` используется и в сглаживании ACC, и в `interaction_field.update(..., dt=dt)`.

8. `cortisol` намеренно остаётся вне быстрого поля взаимодействия (`DA/5HT/NE/ACh`) как медленная ось стресса.

### Тестовое покрытие реализации

- `tests/test_acc_conflict_modulation.py`:
  - формула ACC и инварианты,
  - чистота `_compute_effective_conflict`,
  - динамика следов нижних частот,
  - разделённые конфликты и семантика `None`,
  - ограниченная долговременная динамика.
- `tests/test_neuromodulators_phase2.py`:
  - прежние сценарии фазы 2, синхронизированные с ACC-модуляцией.
