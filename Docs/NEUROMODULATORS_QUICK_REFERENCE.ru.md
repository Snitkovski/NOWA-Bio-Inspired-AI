# Нейромодуляторы — Краткая справка

English version: [NEUROMODULATORS_QUICK_REFERENCE.en.md](NEUROMODULATORS_QUICK_REFERENCE.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

**Размещение:** Правая боковая панель GUI  
**Файл реализации:** `src/neuromodulators.py`  
**Тесты:** `tests/test_neuromodulators.py`, `tests/test_neuromodulators_phase2.py`, `tests/test_neuromodulator_integration.py`, `tests/test_neuromodulator_interaction_layer.py`

---

## Связанный слой взаимодействия (DA/5HT/NE/ACh)

В `NeuromodulatorState` встроен `NeuromodulatorField` с матрицей межмодуляторных связей.

Используемая динамика:

```text
dM/dt = base_signal + W * (M - baseline) - decay * (M - baseline)
```

Где:
- `M = [DA, 5HT, NE, ACh]`
- `base_signal` собирается из reward/novelty/conflict + новизны и повторения ACh
- вариант с центром на базовом уровне удерживает устойчивое состояние покоя

---

## Четыре нейромодулятора

### DA — дофамин
**Подкрепление и ценность**

| Параметр | Значение |
|----------|----------|
| Увеличивается при | Положительная награда (reward > 0) |
| Влияет на | Усиление кортикальных паттернов во время сна |
| Диапазон | 0.0 – 1.0 |
| Коэффициент роста | +0.25 при reward > 0; -0.10×\|reward\| при reward < 0 |
| Спад | Экспоненциальный к 0.1 |

**Эффект во время сна:**
```
pattern.strength *= (1.0 + dopamine * 0.05)
```

---

### NE — норадреналин
**Мобилизация и неожиданность**

| Параметр | Значение |
|----------|----------|
| Увеличивается при | Novelty > 0 или Conflict > 0 |
| Влияет на | Формирование дополнительных цепочек, исследование |
| Диапазон | 0.0 – 1.0 |
| Коэффициент роста | +0.3 на единицу novelty |
| Спад | Экспоненциальный к 0.1 |

**Эффект во время сна (при NE > 0.4):**
```
_form_chains_from_recent(max_len=9)  # вместо обычных 7
```

---

### 5-HT — серотонин
**Стабильность и насыщение**

| Параметр | Значение |
|----------|----------|
| Увеличивается при | Положительная награда без конфликта и устойчивое повторение |
| Влияет на | Стабилизация паттернов и опытов |
| Диапазон | 0.0 – 1.0 |
| Коэффициент роста | +0.05×reward (при conflict=0) +0.01 за устойчивое повторение |
| Спад | Экспоненциальный к 0.1 |

**Эффект во время сна (при 5-HT > 0.1):**
```
for exp in hippocampus.experiences[-50:]:
    exp.stability += serotonin * 0.01
```

---

### CORT — кортизол
**Стресс и перегрузка**

| Параметр | Значение |
|----------|----------|
| Увеличивается при | Отрицательная награда (reward < 0) или Conflict > 0 |
| Влияет на | Агрессивное забывание нестабильных трасс |
| Диапазон | 0.0 – 1.0 |
| Коэффициент роста | +0.20×\|reward\| +0.25×conflict |
| Спад | Экспоненциальный к 0.05 |

**Эффект во время сна (при CORT > 0.4):**
```
threshold = forget_threshold + (cortisol * 0.2)
kept = [exp for exp in hippocampus if exp.stability >= threshold ...]
```

---

## Использование в коде

### Инициализация

```python
from neuromodulators import NeuromodulatorState

agent = Agent(...)
# agent.neuromodulators уже инициализирован
print(agent.neuromodulators.dopamine)  # 0.1 (базовый уровень)
```

### Обновление во время шага

```python
action = agent.step(
    context=["user:hello"],
    reward=+0.5,     # → DA растёт
    novelty=0.2,     # → NE растёт
    conflict=0.0     # → CORT не растёт
)

# Нейромодуляторы обновились автоматически
print(agent.neuromodulators.dopamine)  # ~0.23
print(agent.neuromodulators.norepinephrine)  # ~0.16
```

### Применение во время сна

```python
stats = agent.sleep(cycles=1)

# Во время сна:
# - DA усилит паттерны
# - NE создаст больше цепочек
# - CORT забудет нестабильные трассы
# - 5-HT стабилизирует опыты
```

### Сохранение и загрузка

```python
from storage import AgentStorage

storage = AgentStorage()

# Сохранить вместе с нейромодуляторами
filepath = storage.save_agent(
    hippocampus, cortex, selector,
    neuromodulators=agent.neuromodulators  # ← добавить
)

# Загрузить
storage.load_agent(
    hippocampus, cortex, selector,
    filepath,
    neuromodulators_data=saved_nm_data
)
```

---

## Примеры сценариев

### Сценарий 1: Успешное обучение

```
Шаг 1: reward=+1.0 → DA=0.3, 5-HT=0.15
Шаг 2: reward=+0.8 → DA=0.4, 5-HT=0.20
Шаг 3: reward=+0.9 → DA=0.5, 5-HT=0.25

Во время сна:
Сильное усиление паттернов (эффект DA)
Стабилизация опытов (эффект 5-HT)
Минимальное забывание (низкий CORT)
```

### Сценарий 2: Неожиданное событие

```
Шаг 1: novelty=0.9 → NE=0.37
Шаг 2: novelty=0.7 → NE=0.44

Во время сна:
Больше цепочек формируется (NE > 0.4)
Более длинные последовательности запоминаются
Система подготовлена к повторению неожиданного
```

### Сценарий 3: Стресс и восстановление

```
Шаг 1: reward=-1.0, conflict=0.8 → CORT=0.35, DA=0.05
Шаг 2: reward=-0.9, conflict=0.7 → CORT=0.50, DA=0.04

Во время сна:
Агрессивное забывание неудачных трасс (CORT > 0.4)
Упрощение стратегий
Сохранение только наиболее стабильных

Восстановление:
Шаг 3: reward=+0.5 → DA растёт, CORT спадает
→ Система возвращается к нормальному состоянию
```

---

## Тест-кейсы

### TC-1: Повторяющийся успех

```python
for i in range(5):
    agent.step([f"context{i}"], reward=+0.8)

# Ожидание:
assert agent.neuromodulators.dopamine > 0.5
assert agent.neuromodulators.serotonin > 0.3
# ✓ Цепочки стабилизируются
# ✓ Паттерны усиливаются
```

### TC-2: Резкая неожиданность

```python
agent.step(["context"], novelty=0.9, conflict=0.3)

# Ожидание:
assert agent.neuromodulators.norepinephrine > 0.4
assert agent.neuromodulators.cortisol > 0.15
# ✓ NE скачок → больше исследования
# ✓ CORT растёт → немного стресса
```

### TC-3: Долгий негатив

```python
for i in range(6):
    agent.step(["context"], reward=-0.7, conflict=0.5)

before_count = len(agent.hippocampus.experiences)
agent.sleep(cycles=1)
after_count = len(agent.hippocampus.experiences)

# Ожидание:
assert agent.neuromodulators.cortisol > 0.4
assert after_count < before_count  # забывание активировано
# ✓ CORT высокий
# ✓ Нестабильные трассы удалены
```

### TC-4: Стабильность

```python
for i in range(8):
    agent.step(["context"], reward=0.0, novelty=0.0, conflict=0.0)

# Ожидание:
assert agent.neuromodulators.serotonin > 0.05
assert agent.neuromodulators.dopamine == 0.1  # на базовом уровне
# ✓ 5-HT растёт (стабильность)
# ✓ DA не меняется (нет подкрепления)
```

---

## Визуализация в GUI

### Диагностический блок

```
Нейромодуляторы:
  DA: 0.42        ← дофамин (усиление)
  NE: 0.31        ← норадреналин (мобилизация)
  5-HT: 0.58      ← серотонин (стабильность)
  CORT: 0.12      ← кортизол (стресс)
```

**Интерпретация:**
- **DA высокий** — успешное обучение, укрепление
- **NE высокий** — исследование, адаптация
- **5-HT высокий** — стабильность, меньше изменений
- **CORT высокий** — стресс, забывание активировано

---

## Справочник API

### NeuromodulatorState

```python
class NeuromodulatorState:
    def __init__(
        self,
        dopamine: float = None,
        norepinephrine: float = None,
        serotonin: float = None,
        cortisol: float = None,
        acetylcholine: float = None,
    ):
        ...

    # Coupled dynamics entrypoint
    def update_from_signals(
        self,
        reward: float = 0.0,
        novelty: float = 0.0,
        conflict: float = 0.0,
        stable_repetition: bool = False,
        use_reward_for_dopamine: bool = True,
    ):
        ...

    # ACh helper update
    def update_acetylcholine(self, novelty: float = 0.0, stable_repetition: bool = False):
        ...

    # Temporal decay
    def decay_over_time(self, elapsed: float):
        ...

    # Serialization / persistence
    def to_dict(self) -> dict:
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "NeuromodulatorState":
        ...

    # Immutable snapshot
    def snapshot(self) -> dict:
        ...
```

---

## Часто задаваемые вопросы

**Вопрос: можно ли отключить нейромодуляторы?**  
Ответ: да, просто не передавайте их в `SleepManager`:
```python
sleep_manager = SleepManager(hip, cortex)  # без neuromodulators
```

**Вопрос: какие коэффициенты можно менять?**  
Ответ: основные коэффициенты задаются на уровне класса `NeuromodulatorState` и параметров слоя взаимодействия:
```python
NeuromodulatorState.DA_REWARD_POSITIVE
NeuromodulatorState.NE_NOVELTY
NeuromodulatorState.ACH_NOVELTY_GAIN
NeuromodulatorState.INTERACTION_DECAY
NeuromodulatorState.INTERACTION_DT
```

**Вопрос: почему базовый уровень 0.1?**  
Ответ: это обеспечивает баланс между отсутствием стимуляции и полной нейтральностью.

**Вопрос: когда применяются эффекты?**  
Ответ: часть эффектов применяется уже в `step()` (через `update_from_signals` и слой взаимодействия), а часть — в `sleep()` через нижестоящие механизмы консолидации.

---

**Версия:** 1.1  
**Дата обновления:** март 2026
