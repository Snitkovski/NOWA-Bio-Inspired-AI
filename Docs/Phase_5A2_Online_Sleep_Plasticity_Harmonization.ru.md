# Задачи — фаза 5.A.2

English version: [Phase_5A2_Online_Sleep_Plasticity_Harmonization.en.md](Phase_5A2_Online_Sleep_Plasticity_Harmonization.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Согласование пластичности бодрствования и сна

---

## 1. Разделить online и sleep обновления в ValueLayer

### Проблема
Сейчас `update_count` общий.

### Требуется
В `ValueLayer`:

**Добавить:**
```python
self.online_update_count = 0
self.sleep_update_count = 0
```

**Изменить:**
- Обновление в режиме online увеличивает `online_update_count`
- Воспроизведение во сне увеличивает `sleep_update_count`

**Добавить в снимок:**
```python
"online_update_count": ...,
"sleep_update_count": ...
```

---

## 2. Добавить флаг режима обновления

**Изменить сигнатуру:**
```python
update(..., mode: str = "online")
```

**Внутри:**
```python
if mode == "online":
    self.online_update_count += 1
elif mode == "sleep":
    self.sleep_update_count += 1
```

`SleepManager` должен вызывать:
```python
value_layer.update(..., mode="sleep")
```

---

## 3. Разделить alpha для online и sleep

В `ValueLayer` добавить параметры:
```python
self.alpha_online_default = 0.03
self.alpha_sleep_default = 0.08
```

**Режим online:**
```python
alpha = self.alpha_online_default
```

**Режим сна:**
```python
alpha = self.alpha_sleep_default
```

**Цель:**  
Сон должен быть усиливающей фазой, но не неуправляемым ростом.

---

## 4. Модуляция sleep alpha устойчивостью

В `SleepManager` перед вызовом `update`:
```python
alpha_sleep_effective = alpha_sleep_default * clamp(stability_index, 0.3, 1.0)
```

Если `stability_index` низкий, воспроизведение ослабляется.

**Это связывает:**
- устойчивость фазы 4.5
- пластичность воспроизведения фазы 5

---

## 5. Ограничить амплитуду online TD

Добавить ограничение для online TD:
```python
td_error = clamp(td_error, -td_clip_online, td_clip_online)
```

**Например:**
```python
td_clip_online = 1.0
```

**Чтобы:**  
сильное подкрепление не ломало пространство ценности.

---

## 6. Добавить затухание температуры воспроизведения

В `SleepManager`:

**В начале сна:**
```python
replay_temperature = 1.0
```

**После каждого воспроизведения:**
```python
replay_temperature *= 0.95
```

**Приоритет воспроизведения:**
```python
effective_priority = priority * replay_temperature
```

**Это делает воспроизведение:**
- сначала сильным
- потом затухающим
- биологически правдоподобным.

---

## 7. Ввести масштабирование дофамина во сне

Сейчас дофамин модулируется только в режиме online.

**Добавить в `SleepManager`:**

После TD воспроизведения:
```python
dopamine_delta_sleep = k_sleep * td_error
```

**Но:**
```python
dopamine_delta_sleep *= 0.3
```

(сон слабее, чем бодрствование)

**Применить через:**
```python
neuromodulators.apply_dopamine_delta(...)
```

---

## 8. Добавить сводку обучения во сне

После сна в статистику сна добавить:
```python
{
    "total_value_delta_sleep": ...,
    "total_bg_delta_sleep": ...,
    "sleep_update_count": ...,
    "replay_blocked": ...
}
```

Это нужно для анализа устойчивости.

---

## 9. Добавить защиту от неуправляемого роста

Если во время сна:
```python
abs(total_value_delta) > value_total_cap
```

**остановить воспроизведение немедленно.**

Даже если бюджет не исчерпан.

---

## 10. Добавить диагностический крючок

В `Agent.snapshot()`:

**Добавить:**
```python
"value_drift_ratio": sleep_update_count / (online_update_count + 1)
```

Если значение `> 3.0`, выдаётся предупреждение.

---

## Поведенческая логика (что должно получиться)

После изменений:

### Бодрствование (online):
- небольшие обновления TD
- дофамин отражает ошибку предсказания

### Сон:
- воспроизведение усиливает важные эпизоды
- пластичность зависит от устойчивости
- есть затухание и потолки
- нет неуправляемого роста

---

## Что проверить после реализации

- Всплеск подкрепления не ломает ценность.
- Нестабильность ослабляет воспроизведение.
- Много повторяющихся подкреплений не уводит веса в насыщение.
- Без подкрепления ценность постепенно забывается (затухание).
