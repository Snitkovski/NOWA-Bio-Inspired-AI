# Руководство разработчика

English version: [DEVELOPER_GUIDE.en.md](DEVELOPER_GUIDE.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


**Для**: разработчики, которые добавляют функции, исправляют ошибки и расширяют систему  
**Время**: 2–4 часа на полное освоение  
**Предварительные требования**: Python 3.13+, базовое знание асинхронности

---

## Содержание

1. [Установка](#установка)
2. [Обзор архитектуры](#обзор-архитектуры)
3. [Ключевые компоненты](#ключевые-компоненты)
4. [Фаза 3: базальные ганглии](#фаза-3-базальные-ганглии)
5. [Добавление функций](#добавление-функций)
6. [Тестирование](#тестирование)
7. [Типовые задачи](#типовые-задачи)
8. [Рекомендации](#рекомендации)

---

## Установка

### 1. Установка проекта

```bash
cd e:\git\NOWA-Cognitive
pip install -r requirements.txt
python -m pytest tests/ -q
# Should show: 279 passed ✅
```

### 2. Проверка установки

```python
# test_setup.py
from src.agent import Agent
from src.basal_ganglia import ActionChannel, BasalGangliaGate

agent = Agent()
print(f"✅ Agent created: {agent.agent_name}")
print(f"✅ Imports working!")
```

### 3. Настройка среды

**Рекомендуется**: VS Code с расширениями Python:
- Pylance (проверка типов)
- Python (подсветка синтаксиса)
- Pytest Explorer (запуск тестов)

---

## Обзор архитектуры

### Структура верхнего уровня

```
┌─────────────────────────────────────┐
│         AGENT (main class)          │
└─────────────────────────────────────┘
         ↓⬅️⬆️↓⬅️⬆️↓
┌──────────────────────────────────────────────────────────────┐
│ Basal Ganglia    │ PFC Advisory │ Neuromodulators │ Sleep    │
├──────────────────┼──────────────┼─────────────────┼──────────┤
│ Go/NoGo          │ Pressure     │ Dopamine        │ Learning │
│ Selection        │ Signal       │ Cortisol        │ Pipeline │
│ Habit Learning   │ Modulation   │ Norepinephrine  │          │
└──────────────────────────────────────────────────────────────┘
         ↓⬅️⬆️↓⬅️⬆️↓
┌─────────────────────────────────────┐
│  Affective Regulators (4 states)    │
│  - Valence, Arousal, Threat, Curiosity
└─────────────────────────────────────┘
```

### Связи компонентов

1. **Agent**: главный оркестратор, содержит все подсистемы
2. **BasalGanglia**: реализует выбор действия через Go/NoGo
3. **ActionChannel**: отдельное действие с весами и привычкой
4. **Neuromodulators**: химические модуляторы, влияющие на поведение
5. **AffectiveState**: параметры эмоционального состояния
6. **Sleep**: консолидация обучения во сне

---

## Ключевые компоненты

### 1. ActionChannel (src/basal_ganglia.py)

Представляет одно исполнимое действие:

```python
class ActionChannel:
    """Individual action in Basal Ganglia decision."""
    
    action_id: str              # Unique identifier
    go_weight: float            # "Approach" weight (0-1)
    nogo_weight: float          # "Avoid" weight (0-1)
    habit_strength: float       # Learned habit strength (0-1)
    last_outcome: float         # Last success indicator
```

**Основные операции**:
- `get_go_signal()` — вычислить сигнал Go
- `get_nogo_signal()` — вычислить сигнал NoGo
- `learn_from_outcome()` — обновить habit_strength по успеху

### 2. BasalGangliaGate (src/basal_ganglia.py)

Реализует механизм выбора действия:

```python
class BasalGangliaGate:
    """Go/NoGo competition for action selection."""
    
    def choose(
        self,
        channels: list[ActionChannel],
        pfc_pressure: float = 0.5,    # PFC advisory signal
        affective_state: AffectiveState = None,
        neuromodulators: NeuromodulatorState = None
    ) -> str:
        """Select action via Go/NoGo competition.
        
        Formula: Net = Go - 0.5×NoGo + PFC + habit×0.3
        - Go: approach tendency
        - NoGo: avoid tendency  
        - PFC: prefrontal cortex pressure
        - habit: learned behavior strength
        """
```

**Ключевая формула**:
```
For each channel:
  Go = go_weight × dopamine × (1 + norepinephrine)
  NoGo = nogo_weight × cortisol
  Net = Go - 0.5×NoGo + pfc_pressure + habit_strength×0.3
  
Select action with highest Net (softmax with temperature)
```

### 3. Neuromodulators (src/neuromodulators.py)

Химические сигналы, влияющие на поведение:

```python
class NeuromodulatorState:
    dopamine: float             # Motivation (default: 1.0)
    cortisol: float             # Stress (default: 0.5)
    norepinephrine: float       # Attention (default: 0.8)
    serotonin: float            # Mood (default: 0.7)
```

**Эффекты**:
- **Dopamine**: умножает сигнал Go
- **Cortisol**: умножает сигнал NoGo
- **Norepinephrine**: температура softmax (исследование)
- **Serotonin**: влияет на скорость обучения

---

## Фаза 3: базальные ганглии

### Что такое фаза 3?

Полная реализация выбора действия через биологический контур Go/NoGo базальных ганглиев.

### Основные возможности

1. **Регистрация действия**
   ```python
   agent.register_action_channel(
       action_id="attack",
       go_weight=0.8,      # Strong approach tendency
       nogo_weight=0.2     # Weak avoid tendency
   )
   ```

2. **Выбор действия**
   ```python
   action = agent.choose_action_via_basal_ganglia(
       pfc_pressure=1.0    # Strong directive from PFC
   )
   ```

3. **Обучение по исходу**
   ```python
   agent.record_action_outcome(
       action=action,
       success=True,       # Did it work?
       dopamine=1.5        # How much reward?
   )
   ```

4. **Консолидация во сне**
   ```python
   agent.sleep()  # Habit strengths based on success history
   ```

### Покрытие тестами

Фаза 3 покрыта 29 тестами:

```
ActionChannel (8 tests):
  ✅ Signal computation
  ✅ Habit learning
  ✅ Outcome recording

BasalGangliaGate (12 tests):
  ✅ Basic action selection
  ✅ Go/NoGo competition
  ✅ Neuromodulator effects
  ✅ PFC pressure effects
  ✅ Test cases TC1-TC6

Learning (4 tests):
  ✅ Habit consolidation
  ✅ Success tracking
  ✅ Dopamine effects

Integration (2 tests):
  ✅ Full agent use
  ✅ Multi-episode learning

Edge Cases (3 tests):
  ✅ No actions registered
  ✅ Empty parameters
  ✅ Extreme values
```

Запуск:
```bash
pytest tests/test_basal_ganglia.py -v
# Output: 29 passed ✅
```

---

## Добавление функций

### Добавить новый нейромодулятор

1. **Обновить NeuromodulatorState** (src/neuromodulators.py):

```python
class NeuromodulatorState:
    # ... existing fields ...
    my_new_modulator: float = 1.0  # Default value
```

2. **Добавить эффект в choose()** (src/basal_ganglia.py):

```python
net = channel.go_weight * neuromodulators.dopamine
# Add your modulator effect:
net *= (1 + neuromodulators.my_new_modulator * 0.5)
```

3. **Добавить тест** (tests/test_basal_ganglia.py):

```python
def test_my_new_modulator():
    """Test that my_new_modulator affects choice."""
    # ...test code...
    assert action == expected_action
```

4. **Запустить тесты**:
```bash
pytest tests/test_basal_ganglia.py::test_my_new_modulator -v
```

### Добавить новый механизм обучения

1. **Создать новый класс** в src/basal_ganglia.py:

```python
class MyLearningMechanism:
    """Description of your learning mechanism."""
    
    def learn(self, outcome: float) -> None:
        """Update based on outcome."""
        pass
```

2. **Встроить в BasalGangliaLearning**:

```python
class BasalGangliaLearning:
    def consolidate_during_sleep(self, ...):
        # ... existing code ...
        my_mechanism = MyLearningMechanism()
        # ... use it ...
```

3. **Тщательно протестировать**:

```python
def test_my_learning_mechanism():
    """Test learning behavior."""
    pass
```

---

## Тестирование

### Структура тестов

```
tests/
├── test_basal_ganglia.py      # Phase 3 tests (29)
├── test_agent.py              # Agent integration
├── test_affective_regulators.py
└── ... (250 other tests)
```

### Написать тест

```python
def test_my_feature():
    """Test description.
    
    Tests: action_selection with specific neuromodulator
    Expected: specific behavior
    """
    # Setup
    gate = BasalGangliaGate()
    channels = [
        ActionChannel("a", go_weight=0.8, nogo_weight=0.2),
        ActionChannel("b", go_weight=0.2, nogo_weight=0.8),
    ]
    
    # Execute
    action = gate.choose(channels, pfc_pressure=1.0)
    
    # Verify
    assert action == "a", f"Expected 'a', got {action}"
```

### Запуск тестов

```bash
# All tests
pytest tests/ -q

# Specific test class
pytest tests/test_basal_ganglia.py::TestActionChannel -v

# Specific test
pytest tests/test_basal_ganglia.py::test_basic_action_selection -v

# With coverage
pytest --cov=src tests/

# Watch mode (requires pytest-watch)
ptw tests/
```

### Рекомендации по тестам

1. **Одно утверждение на тест** (или связанные утверждения)
2. **Ясные имена тестов** — описывают, что проверяется
3. **Использовать docstring** — пояснять, что и зачем
4. **Схема Arrange–Act–Assert**:
   ```python
   # Arrange - setup
   gate = BasalGangliaGate()
   
   # Act - execute
   action = gate.choose(channels)
   
   # Assert - verify
   assert action == expected
   ```

---

## Типовые задачи

### Задача 1. Добавить агенту новое действие

```python
# Create agent
agent = Agent(agent_name="MyBot")

# Register action
agent.register_action_channel(
    action_id="my_action",
    go_weight=0.7,      # 0-1
    nogo_weight=0.3     # 0-1
)

# Use it
action = agent.choose_action_via_basal_ganglia()
assert "my_action" in [a for a in agent.get_basal_ganglia_state()...]
```

### Задача 2. Проверить эффекты нейромодуляторов

```python
agent = Agent()
agent.register_action_channel("brave", go_weight=0.8, nogo_weight=0.2)
agent.register_action_channel("cautious", go_weight=0.2, nogo_weight=0.8)

# Test 1: High dopamine makes agent brave
agent.neuromodulators.dopamine = 2.0
brave_count = sum(
    agent.choose_action_via_basal_ganglia() == "brave"
    for _ in range(100)
)
assert brave_count > 70, f"Expected >70, got {brave_count}"

# Test 2: High cortisol makes agent cautious
agent.neuromodulators.dopamine = 1.0
agent.neuromodulators.cortisol = 2.0
cautious_count = sum(
    agent.choose_action_via_basal_ganglia() == "cautious"
    for _ in range(100)
)
assert cautious_count > 70, f"Expected >70, got {cautious_count}"
```

### Задача 3. Обучить агента

```python
agent = Agent()
agent.register_action_channel("good_action", go_weight=0.5, nogo_weight=0.5)
agent.register_action_channel("bad_action", go_weight=0.5, nogo_weight=0.5)

# Train for 100 episodes
for episode in range(100):
    action = agent.choose_action_via_basal_ganglia()
    
    # "good_action" always succeeds
    success = (action == "good_action")
    dopamine = 1.5 if success else 0.0
    
    agent.record_action_outcome(action, success=success, dopamine=dopamine)
    
    # Sleep every 10 episodes to consolidate
    if episode % 10 == 0:
        agent.sleep()

# Check learning
state = agent.get_basal_ganglia_state()
good_habit = state['action_channels']['good_action']['habit_strength']
bad_habit = state['action_channels']['bad_action']['habit_strength']

print(f"Good action habit: {good_habit:.3f}")
print(f"Bad action habit: {bad_habit:.3f}")
assert good_habit > bad_habit, "Agent should have learned good_action"
```

---

## Рекомендации

### 1. Аннотации типов

Всегда указывайте аннотации типов:

```python
# ✅ Good
def choose(self, channels: list[ActionChannel]) -> str:
    pass

# ❌ Avoid
def choose(self, channels):
    pass
```

### 2. Docstring

Документируйте все публичные методы:

```python
def choose(self, channels: list[ActionChannel]) -> str:
    """Select action via Go/NoGo competition.
    
    Args:
        channels: List of possible actions
        
    Returns:
        Action ID string of selected action
        
    Formula:
        Net = Go - 0.5×NoGo + PFC + habit×0.3
    """
```

### 3. Константы

Выносите «магические» числа в константы:

```python
# ✅ Good
HABIT_GAIN = 0.3
NOGO_MULTIPLIER = 0.5

net = (channel.go_weight - NOGO_MULTIPLIER * channel.nogo_weight
       + pfc_pressure + channel.habit_strength * HABIT_GAIN)

# ❌ Avoid
net = channel.go_weight - 0.5 * channel.nogo_weight + pfc_pressure + channel.habit_strength * 0.3
```

### 4. Обработка ошибок

Обрабатывайте краевые случаи аккуратно:

```python
# ✅ Good
if not channels:
    raise ValueError("At least one action channel required")

# ❌ Avoid
channels[0]  # Crash if empty
```

### 5. Тестирование

Тщательно тестируйте публичные интерфейсы:

```python
# ✅ Good
def test_choose_raises_on_empty_channels():
    gate = BasalGangliaGate()
    with pytest.raises(ValueError):
        gate.choose([])

# ❌ Avoid
def test_choose():
    gate = BasalGangliaGate()
    gate.choose([ActionChannel(...)])
```

---

## Навигация по коду

### Ключевые файлы

```
src/
├── agent.py                    # Main Agent class (400+ lines)
├── basal_ganglia.py           # Phase 3 implementation (600+ lines)
├── neuromodulators.py         # Neuromodulator effects (200+ lines)
├── affective_regulators.py    # Affective state (300+ lines)
├── sleep.py                   # Learning consolidation (200+ lines)
└── gui.py                     # Visualization interface (800+ lines)

tests/
├── test_basal_ganglia.py      # 29 Phase 3 tests
├── test_agent.py              # Integration tests
└── ... (20+ other test files)

Docs/
├── QUICK_START.md             # First 5 minutes
├── PHASE_3_GUIDE.md           # Detailed Phase 3
├── ARCHITECTURE.md            # Full system design
└── API.md                     # API reference
```

### Поиск

```bash
# Find a class
grep -r "class ActionChannel" src/

# Find a method
grep -r "def choose" src/

# Find imports of something
grep -r "from src.basal_ganglia import" tests/

# Find all test files
find tests/ -name "test_*.py"
```

---

## Диагностика

### Проблема: тесты падают с «ModuleNotFoundError»

**Решение**:
```bash
# Make sure you're in project root
cd e:\git\NOWA-Cognitive

# Verify all tests pass
pytest tests/ -q

# If still failing, reinstall
pip install -r requirements.txt
```

### Проблема: «AttributeError: module has no attribute X»

**Решение**:
1. Проверить, существует ли класс или функция
2. Проверить правильность пути импорта
3. Проверить циклические импорты

```python
# Debug imports
python -c "from src.basal_ganglia import BasalGangliaGate; print('✅')"
```

### Проблема: тест иногда падает (неустойчивый тест)

**Решение**: тестам со случайностью нужна большая выборка:

```python
# ❌ Flaky (small sample)
choices = [gate.choose(channels) for _ in range(10)]
assert choices.count("a") > 8

# ✅ More robust (larger sample)
choices = [gate.choose(channels) for _ in range(1000)]
assert choices.count("a") > 800
```

---

## Дальнейшие шаги

1. **Прочитать PHASE_3_GUIDE.md** — подробная документация фазы 3
2. **Прочитать ARCHITECTURE.md** — полный проект системы
3. **Просмотреть тестовые файлы** — учиться на примерах из тестов
4. **Приступить к коду** — выбрать функцию для добавления или улучшения

---

## Вопросы?

1. Свериться с [API.md](API.ru.md) как со справочником интерфейса
2. Читать тестовые файлы как примеры использования
3. Смотреть docstring в исходном коде
4. Искать в issues и обсуждениях, если работа остановилась

---

**Удачной разработки.**

**Последнее обновление**: февраль 2026 г.  
**Статус**: завершено и актуально
