# Phase 6.1 — спецификация слоя ацетилхолина (ACh)

English version: [Phase_6_1_ACh_RU_Spec.en.md](Phase_6_1_ACh_RU_Spec.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## 1. Цель фазы

Введение нейромодулятора ацетилхолина (ACh) как механизма:

- attention gating
- novelty amplification
- modulation learning rate
- contextual encoding strength
- replay priority modulation

ACh НЕ является системой вознаграждения (это роль dopamine). ACh — это регулятор селективности и пластичности.

---

## 2. Архитектурные принципы

1. ACh ∈ [0.0, 1.0]
2. Имеет baseline
3. Усиливается новизной
4. Снижается при повторяемости
5. Стремится к baseline через экспоненциальный decay
6. Не влияет напрямую на TD error
7. Не влияет на sleep alpha

---

## 3. Расширение Neuromodulators

### 3.1 Новые поля

```python
self.acetylcholine: float = 0.1
self.ach_baseline: float = 0.1
self.ach_decay_rate: float = 0.02
self.ach_novelty_gain: float = 0.25
self.ach_repetition_penalty: float = 0.05
self.ach_alpha_gain: float = 0.4
self.ach_replay_gain: float = 0.5
```

Ограничение:

```python
self.acetylcholine = clamp(self.acetylcholine, 0.0, 1.0)
```

---

### 3.2 Метод обновления

```python
def update_acetylcholine(self, novelty: float, stable_repetition: bool):
    if novelty > 0.5:
        self.acetylcholine += self.ach_novelty_gain * novelty

    if stable_repetition:
        self.acetylcholine -= self.ach_repetition_penalty

    # decay toward baseline
    delta = self.ach_baseline - self.acetylcholine
    self.acetylcholine += self.ach_decay_rate * delta

    self.acetylcholine = clamp(self.acetylcholine, 0.0, 1.0)
```

---

## 4. Интеграция с ValueLayer

### 4.1 Online alpha modulation

В `ValueLayer.update()`:

```python
alpha_effective = alpha_online_default * (1 + ach_alpha_gain * ACh)
alpha_effective = min(alpha_effective, 0.15)
```

Sleep alpha НЕ масштабируется ACh.

---

## 5. Интеграция с Memory Encoding (T1)

При создании эпизода:

```python
encoding_strength = base_strength * (1 + 0.5 * ACh)
```

---

## 6. Интеграция с Replay Priority

В `SleepManager._compute_replay_priority()`:

```python
priority *= (1 + ach_replay_gain * ACh_snapshot)
priority = min(priority, priority_cap)
```

---

## 7. Ограничения безопасности

1. ACh не модифицирует TD error.
2. ACh не влияет на dopamine напрямую.
3. ACh не масштабирует sleep alpha.
4. ACh ≤ 1.0.
5. При ACh > 0.9 включается soft alpha cap.

---

## 8. Тест-кейсы

### Test 1 — Novelty Spike

novelty = 1.0

Ожидается:
- ACh возрастает
- alpha_online возрастает
- replay_priority возрастает

---

### Test 2 — Repetition

novelty = 0.1
stable_repetition = True

Ожидается:
- ACh снижается

---

### Test 3 — Saturation Protection

Многократная новизна.

Ожидается:
- ACh ≤ 1.0
- alpha_online ≤ 0.15

---

### Test 4 — Decay to Baseline

Без новизны 100 шагов.

Ожидается:
- ACh стремится к baseline

---

## 9. Метрики

В snapshot:

```python
"acetylcholine": self.acetylcholine
```

В sleep stats:

```python
"mean_ach_during_cycle": ...
```

---

## 10. Критерии завершения

Фаза завершена если:

- ACh корректно обновляется
- alpha_online масштабируется
- replay priority масштабируется
- нет runaway plasticity
- все тесты проходят
