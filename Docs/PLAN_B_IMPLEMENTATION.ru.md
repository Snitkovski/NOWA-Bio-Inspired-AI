# Реализация плана B: временные цепи, протостратегия и присвоение кредита

English version: [PLAN_B_IMPLEMENTATION.en.md](PLAN_B_IMPLEMENTATION.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Обзор

**План B** успешно встроен в проект NOWA-Cognitive. Документ описывает реализацию, архитектуру и способ использования новой системы временных цепей.

---

## Что такое план B?

План B вводит **временные цепи** — лёгкие структуры памяти, которые фиксируют поведенческие последовательности и применяют ретроспективное присвоение кредита без градиентов и без явного планирования. Так возникает **протостратегия**: поведение, которое появляется как паттерны сцепленных действий, причём каждая цепь смещена своим ретроспективным (чистым) исходом.

**Ключевые свойства:**
- Нет обучения во время бодрствующего поведения
- Цепи формируются **только во время консолидации сна**
- Цепи чисто совещательны: они смещают выбор действия, но не диктуют его
- Нет градиентов, целей и самоповествования
- Кредит присваивается ретроспективно через чистый аффект, а не обратным распространением ошибки

---

## Архитектура

### 1. TemporalChain (temporal_chains.py)

```python
class TemporalChain:
    signature: Tuple[str, ...]      # Event sequence (e.g., ("user:hello", "action:say_hello"))
    net_affect: float               # Retrospective aggregate outcome (-1 to +1)
    stability: float                # Consolidation strength (0 to 1)
    usage_count: int                # How many times this chain has been seen
    created_at: float               # Timestamp
    last_updated: float             # Last update time
```

**Методы:**
- `update(net_affect)` — пошагово обновляет net_affect и stability цепи
- `matches_suffix(event_sequence)` — проверяет, совпадает ли цепь с хвостом недавних событий

### 2. ChainMemory (temporal_chains.py)

Диспетчер хранения и запросов временных цепей:

```python
class ChainMemory:
    chains: Dict[Tuple, TemporalChain]  # Signature -> TemporalChain
```

**Методы:**
- `add_or_update(signature, net_affect)` — создать или обновить цепь
- `match_bias(recent_sequence)` — вернуть словарь «действие → смещение» для совпавших цепей
- `statistics()` — вернуть сводную статистику (total_chains, avg_stability, avg_net_affect)

### 3. Встраивание в SleepManager (sleep.py)

Во время консолидации сна новый шаг образует цепи из недавнего опыта:

```python
def sleep_cycle(self) -> dict:
    # ... existing consolidation logic ...
    
    # 4.5 Form temporal chains from recent experiences (Plan B)
    formed = self._form_chains_from_recent()
    stats["chains_formed"] = formed
    
    return stats
```

**Алгоритм формирования цепей:**
1. Извлечь все имена событий из недавних опытов гиппокампа
2. Построить все возможные подпоследовательности длины 2–7 (настраивается)
3. Для каждой подпоследовательности вычислить ретроспективный net_affect:
   - если есть событие последствия, извлечь числовое значение
   - иначе взять среднюю интенсивность участвующих опытов
4. Вызвать `chain_memory.add_or_update(signature, net_affect)`

### 4. Встраивание в ActionSelector (selector.py)

Селектор теперь принимает необязательный параметр `temporal_chains_bias`:

```python
action = selector.choose(
    hippocampal_exps,
    cortical_patterns,
    intent_pressure=intent_pressure,
    affect_modifier=affect_modifier,
    temporal_chains_bias=chain_bias    # NEW: optional chain biasing
)
```

**Логика применения смещения:**
1. Если других давлений нет (base_total_pressure == 0) и у цепей есть смещение:
   - непосредственно выбрать действие с наибольшим смещением цепи: **выбор протостратегии**
2. Если цепи присутствуют и вносят вклад в верхнее действие:
   - вернуть верхнее действие детерминированно: **проведение протостратегии**
3. Иначе применить обычный выбор по уверенности

### 5. Встраивание в Agent (agent.py)

Перед выбором действия агент вычисляет смещение цепей по недавней истории:

```python
try:
    if hasattr(self.sleep_manager, 'chain_memory'):
        recent = self.hippocampus.experiences[-50:]
        flat = []
        for exp in recent:
            flat.extend(list(exp.path.signature()))
        chain_bias = self.sleep_manager.chain_memory.match_bias(flat)
except Exception:
    chain_bias = None

action = self.selector.choose(
    hip_exps, ctx_patterns,
    intent_pressure=intent_pressure,
    affect_modifier=affect_modifier,
    temporal_chains_bias=chain_bias
)
```

---

## Ключевые поведения

### Отложенная оценка

**Тест:** `test_chain_formation_and_bias`
- Создать последовательность A → B → good_outcome
- Создать последовательность A → C → bad_outcome
- После сна агент слегка предпочитает B после A (без планирования, только статистическое предпочтение)

### Контекстная стратегия

Цепи различают:
- одно и то же действие в разных контекстах
- разные последовательности действий, ведущие к одному исходу

### Нет обучения без сна

- Шаги бодрствования сохраняют опыт, но никогда не образуют цепей
- Цепи появляются только после вызова `agent.sleep(cycles=3)`
- Это соответствует биологической консолидации памяти

---

## Изменения интерфейса

Интерфейс теперь показывает статистику временных цепей:

1. **Панель отображения памяти** (правая панель, нижняя часть):
   - Показывает число цепей и их среднюю устойчивость

2. **Инспектор, вкладка сна**:
   - Новый раздел с общим числом цепей и средней устойчивостью

3. **Встраивание обратной связи**:
   - Оценки пользователя задают net_affect последствия, используемый при формировании цепей

---

## Пример использования

```python
from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager
from experience import Event, EventType

# Setup
hip = NOWAHippocampus()
cortex = CortexMemory()
sel = ActionSelector(actions=["action_a", "action_b", "action_c"])
sleep_mgr = SleepManager(hip, cortex)
agent = Agent(hip, cortex, sel, sleep_manager=sleep_mgr)

# Waking behavior (no chain formation)
for i in range(10):
    context = ["context:test"] if i % 2 == 0 else ["context:other"]
    reward = 1.0 if i < 5 else -1.0
    action = agent.step(context, reward=reward, intensity=1.0)
    print(f"Step {i}: Action={action}, Reward={reward}")

# Sleep consolidation (chains formed here)
sleep_stats = agent.sleep(cycles=3)
print(f"Chain formation: {sleep_stats}")

# Check chains
chains_stats = sleep_mgr.chain_memory.statistics()
print(f"Total chains: {chains_stats['total_chains']}")
```

---

## Тестирование

Вся функциональность плана B покрыта модульными тестами в `tests/test_temporal_chains.py`:

- `test_chain_formation_and_bias`: проверить, что цепи образуются во сне и дают смещение
- Интеграционные тесты подтверждают, что цепи работают вместе с гиппокампом, корой и селектором

Запуск тестов:
```bash
pytest tests/test_temporal_chains.py -q
```

---

## Проектные ограничения (по спецификации)

- **Без градиентов:** цепи используют только простые скользящие средние
- **Без планирования:** цепи смотрят только назад (ретроспективно)
- **Без целей:** цепи нейтральны к исходу и чисто статистичны
- **Без самоповествования:** цепи существуют, но агент их не описывает
- **Цепи только во сне:** формирование происходит исключительно во время консолидации
- **Короткая фиксированная длина:** не более 7 шагов на цепь
- **Присвоение кредита без обратного распространения:** ретроспективное распределение net_affect

---

## Дальнейшие расширения

- **План C (ландшафты ценности):** дрейф на длинном горизонте и динамика аттракторов
- **Временное затухание:** неиспользуемые цепи теряют устойчивость
- **Кластеризация цепей:** группировка сходных цепей для сокращения памяти
- **Иерархические цепи:** поддержка многоуровневой временной абстракции

---

## Изменённые файлы

- `src/temporal_chains.py` — новый: классы TemporalChain и ChainMemory
- `src/sleep.py` — добавлен метод `_form_chains_from_recent()`
- `src/selector.py` — `choose()` расширен, чтобы принимать и использовать temporal_chains_bias
- `src/agent.py` — вычисление chain_bias перед выбором действия
- `src/gui.py` — показ статистики цепей на панели памяти и в инспекторе
- `tests/test_temporal_chains.py` — новый: развёрнутые тесты плана B

---

**Дата завершения:** 4 февраля 2026  
**Статус:** завершено и проверено (168 тестов проходят)
