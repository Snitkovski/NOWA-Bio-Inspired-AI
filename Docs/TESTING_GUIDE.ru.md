# Руководство по тестированию

English version: [TESTING_GUIDE.en.md](TESTING_GUIDE.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

**Для:** инженеры контроля качества, разработчики, пишущие тесты, архитекторы, проверяющие системы  
**Время:** 1–2 часа для полного понимания  
**Версия:** 2.0

---

## Оглавление

1. [Обзор](#обзор)
2. [Структура тестов](#структура-тестов)
3. [Тесты фазы 3](#тесты-фазы-3)
4. [Написание тестов](#написание-тестов)
5. [Образцы тестов](#образцы-тестов)
6. [Запуск тестов](#запуск-тестов)
7. [Рекомендуемая практика](#рекомендуемая-практика)

---

## Обзор

### Стратегия тестирования

Проект использует **исчерпывающее тестирование на pytest**, охватывающее:

- **Модульные тесты:** поведение отдельного компонента
- **Интеграционные тесты:** взаимодействие компонентов
- **Системные тесты:** сквозное поведение агента
- **Тесты спецификации:** проверка соответствия требованиям

### Покрытие тестами

```
Total Tests: 297
├── Phase 3 Basal Ganglia: 29 tests 
├── Phase 4 (pre) Affective Space: 8 tests 
├── Neuromodulators: 20+ tests 
├── Affective System: 30+ tests 
├── Agent: 50+ tests 
├── Sleep/Learning: 20+ tests 
└── Legacy/Integration: 150+ tests 

Success Rate: 100% (297/297 PASSING)
Execution Time: ~1.5 seconds
```

---

## Структура тестов

### Организация каталогов

```
tests/
├── test_basal_ganglia.py         # 29 Phase 3 tests
├── test_basal_ganglia_advanced.py # Advanced BG tests
├── test_agent.py                  # Agent integration (50+ tests)
├── test_affective_regulators.py   # Affective system
├── test_neuromodulators.py        # Neuromodulator effects
├── test_sleep.py                  # Sleep learning
├── test_integration.py            # Full system tests
└── ... (20+ other test files)
```

### Соглашение об именовании

```python
# Good
def test_basal_ganglia_chooses_higher_net_pressure():
    """BG selects action with highest net pressure."""
    
def test_dopamine_increases_go_signal():
    """High dopamine multiplies Go signals."""

def test_cortisol_increases_nogo_signal():
    """High cortisol multiplies NoGo signals."""

# Avoid
def test_1():
    pass
    
def test_bg():
    pass
```

---

## Тесты фазы 3

### Категории тестов (всего 29)

#### 1. Тесты ActionChannel (8 тестов)

Проверяют поведение отдельного канала действия:

```python
# test_basal_ganglia.py::TestActionChannel

def test_action_channel_creation():
    """ActionChannel stores weights correctly."""
    
def test_action_channel_get_go_signal():
    """Go signal computed correctly."""
    
def test_action_channel_get_nogo_signal():
    """NoGo signal computed correctly."""
    
def test_action_channel_habit_learning():
    """Habit strength increases with reinforcement."""
    
# ... 4 more tests for edge cases
```

#### 2. Тесты BasalGangliaGate (12 тестов)

Проверяют механизм выбора действия:

```python
# test_basal_ganglia.py::TestBasalGangliaGate

def test_basic_action_selection():
    """BG selects the action with highest net pressure."""
    
def test_go_nogo_competition():
    """Strong Go bias action is preferred."""
    
def test_dopamine_effect():
    """High dopamine makes all actions more likely."""
    
def test_cortisol_effect():
    """High cortisol inhibits NoGo-based actions."""
    
def test_pfc_pressure_effect():
    """PFC pressure modifies selection."""
    
def test_habit_strength_effect():
    """Higher habit strength increases selection probability."""
    
# ... 6 more tests including specification tests TC1-TC6
```

#### 3. Тесты BasalGangliaLearning (4 теста)

Проверяют формирование привычки во время сна:

```python
# test_basal_ganglia.py::TestBasalGangliaLearning

def test_habit_consolidation_during_sleep():
    """Habit strengthened after successful action."""
    
def test_habit_differential_learning():
    """Successful actions get stronger habits."""
    
def test_habitmax_cap():
    """Habit strength capped at maximum."""
    
def test_habit_unused_decay():
    """Unused actions decay slowly."""
```

#### 4. Интеграционные тесты (2 теста)

Проверяют фазу 3 вместе с полным агентом:

```python
def test_agent_basal_ganglia_integration():
    """Agent uses BG correctly for action selection."""
    
def test_agent_learning_from_outcomes():
    """Agent updates habit strength from outcomes."""
```

#### 5. Тесты граничных случаев (3 теста)

Проверяют граничные условия:

```python
def test_empty_channels_raises():
    """Choosing from empty channels raises error."""
    
def test_extreme_neuromodulators():
    """Very high/low neuromodulators handled correctly."""
    
def test_no_habit_learning():
    """Zero habit_strength means minimal preference."""
```

### Тест-кейсы спецификации

Тесты TC1–TC6 проверяют соответствие требованиям спецификации:

```python
# TC1: Basic Go/NoGo Competition
agent.register_action_channel("go_strong", 0.8, 0.2)   # Go-biased
agent.register_action_channel("nogo_strong", 0.2, 0.8) # NoGo-biased
# With balanced neuromodulators → "go_strong" selected more often

# TC2: Dopamine Effect
# High DA → increases Go signals for all channels
choices_high_da = [...]
choices_low_da = [...]
assert choices_high_da has more exploitation

# TC3: Cortisol Effect
# High cortisol → increases NoGo inhibition
choices_high_cortisol = [...]
# NoGo-biased actions selected more

# TC4: PFC Pressure Effect
# High PFC pressure → nudges toward certain actions
choices_pfc_high = [...]
# If PFC pressure for specific action → higher selection

# TC5: Habit Integration
# Higher habit_strength → higher selection probability
agent.record_successful_outcomes(...)
agent.sleep()
# Successful action's habit increased

# TC6: Temperature from Neuromodulation
# High NE → more exploration (temperature increase)
choices_high_ne = [...]
# More variety in choices with high NE
variety_high_ne > variety_low_ne
```

---

## Написание тестов

### Шаблон теста

```python
def test_feature_description():
    """
    Test description: What is being tested
    
    Setup: Initial conditions
    Action: What we're testing
    Expected: What should happen
    """
    # ARRANGE - Setup
    gate = BasalGangliaGate()
    channels = [
        ActionChannel("a", go_weight=0.8, nogo_weight=0.2),
        ActionChannel("b", go_weight=0.2, nogo_weight=0.8),
    ]
    neuromodulators = NeuromodulatorState(dopamine=1.0, cortisol=0.5)
    
    # ACT - Execute
    action = gate.choose(channels, neuromodulators=neuromodulators)
    
    # ASSERT - Verify
    assert action == "a", f"Expected 'a', got '{action}'"
```

### Типичные образцы

#### Образец 1. Проверка влияния нейромедиаторов

```python
def test_dopamine_increases_action_selection():
    """High dopamine makes actions more likely."""
    gate = BasalGangliaGate()
    channel = ActionChannel("attack", 0.8, 0.2)
    
    # Count selections with low dopamine
    low_da_count = 0
    for _ in range(100):
        neuromod = NeuromodulatorState(dopamine=0.5)
        if gate.choose([channel], neuromodulators=neuromod) == "attack":
            low_da_count += 1
    
    # Count selections with high dopamine
    high_da_count = 0
    for _ in range(100):
        neuromod = NeuromodulatorState(dopamine=2.0)
        if gate.choose([channel], neuromodulators=neuromod) == "attack":
            high_da_count += 1
    
    assert high_da_count > low_da_count, \
        f"High DA should increase selection: {high_da_count} vs {low_da_count}"
```

#### Образец 2. Проверка обучения привычке

```python
def test_habit_learns_from_success():
    """Habit strength increases after successful outcomes."""
    agent = Agent()
    
    # Register action
    agent.register_action_channel("good", go_weight=0.5, nogo_weight=0.5)
    
    # Record many successful outcomes
    for _ in range(10):
        agent.record_action_outcome("good", success=True, dopamine=2.0)
    
    # Sleep to consolidate
    agent.sleep()
    
    # Check habit increased
    state = agent.get_basal_ganglia_state()
    habit = state['action_channels']['good']['habit_strength']
    assert habit > 0.1, f"Expected habit > 0.1, got {habit}"
```

#### Образец 3. Проверка вероятностей выбора (стохастика)

```python
def test_net_pressure_determines_probability():
    """Higher net pressure → higher selection probability."""
    gate = BasalGangliaGate()
    
    channels = [
        ActionChannel("strong", go_weight=0.8, nogo_weight=0.0),
        ActionChannel("weak", go_weight=0.2, nogo_weight=0.0),
    ]
    
    # Run many selections
    strong_count = 0
    for _ in range(200):
        action = gate.choose(channels)
        if action == "strong":
            strong_count += 1
    
    # Strong should be selected >150 times out of 200 (>75%)
    assert strong_count > 150, \
        f"Expected >75% 'strong' selections, got {strong_count}/200"
```

#### Образец 4. Проверка граничных случаев

```python
def test_empty_channels_raises_error():
    """Choosing from empty list should raise ValueError."""
    gate = BasalGangliaGate()
    
    with pytest.raises(ValueError):
        gate.choose([])
```

---

## Образцы тестов

### Образец: единственная обязанность

Каждый тест проверяет ОДНУ вещь:

```python
# Good - tests one aspect
def test_dopamine_increases_go_signal():
    gate = BasalGangliaGate()
    channel = ActionChannel("a", 0.8, 0.2)
    
    low_da = gate.choose([channel], neuromodulators=NeuromodulatorState(dopamine=0.5))
    high_da = gate.choose([channel], neuromodulators=NeuromodulatorState(dopamine=2.0))
    # Both should select "a", high_da more often
    
# Bad - tests multiple things
def test_everything():
    # Test dopamine
    # Test cortisol
    # Test habit
    # Test PFC
    # ...
    pass
```

### Образец: ясность имени

```python
# Good
def test_cortisol_inhibits_nogo_biased_actions():
    """When cortisol high, NoGo-biased actions are inhibited."""

# Bad
def test_cortisol():
    """Tests cortisol."""
```

### Образец: строка документации

Строка документации обязательна всегда:

```python
def test_my_feature():
    """
    Brief description.
    
    Testing: What aspect is being tested
    Scenario: Under what conditions
    Expected: What should happen
    """
```

---

## Запуск тестов

### Запуск всех тестов

```bash
# Quick run
pytest tests/ -q
# Output: 279 passed in 1.51s 

# Verbose output
pytest tests/ -v

# With coverage
pytest --cov=src tests/
```

### Запуск отдельных тестов

```bash
# Run Phase 3 tests only
pytest tests/test_basal_ganglia.py -v

# Run specific test class
pytest tests/test_basal_ganglia.py::TestActionChannel -v

# Run specific test
pytest tests/test_basal_ganglia.py::test_basic_action_selection -v

# Run tests matching pattern
pytest -k "dopamine" -v
```

### Режим наблюдения

```bash
# Requires pytest-watch: pip install pytest-watch
ptw tests/
# Re-runs tests when files change
```

### Только проверка синтаксиса (без исполнения)

```bash
# Check for syntax errors without running
python -m pytest tests/ --collect-only
```

---

## Рекомендуемая практика

### 1. Изоляция тестов

Каждый тест независим:

```python
# Good - each test creates its own objects
def test_action_a():
    gate = BasalGangliaGate()
    # ...

def test_action_b():
    gate = BasalGangliaGate()  # New instance
    # ...

# Bad - tests depend on order
shared_gate = None

def test_first():
    global shared_gate
    shared_gate = BasalGangliaGate()

def test_second():
    global shared_gate
    # Depends on test_first running first!
```

### 2. Фикстуры для общей подготовки

```python
# Good
import pytest

@pytest.fixture
def basic_channels():
    return [
        ActionChannel("a", 0.8, 0.2),
        ActionChannel("b", 0.2, 0.8),
    ]

def test_choice_1(basic_channels):
    gate = BasalGangliaGate()
    action = gate.choose(basic_channels)
    assert action in ["a", "b"]

def test_choice_2(basic_channels):
    gate = BasalGangliaGate()
    action = gate.choose(basic_channels)
    assert action in ["a", "b"]
```

### 3. Ясные утверждения

```python
# Good
assert high_da_count > low_da_count, \
    f"High DA should increase count: {high_da_count} vs {low_da_count}"

# Bad
assert high_da_count > low_da_count
```

### 4. Достаточный объём выборки для стохастических тестов

```python
# Good - large sample for stochastic behavior
choices = [gate.choose(channels) for _ in range(1000)]
assert choices.count("action") > 750

# Bad - small sample, flaky
choices = [gate.choose(channels) for _ in range(10)]
assert choices.count("action") > 8
```

### 5. Проверять и успешный, и неуспешный путь

```python
def test_success_case():
    """Test when everything works."""
    agent.record_action_outcome("action", success=True, dopamine=1.5)
    agent.sleep()
    habit = agent.get_habit("action")
    assert habit > 0.1

def test_failure_case():
    """Test when action fails."""
    agent.record_action_outcome("action", success=False, dopamine=0.0)
    agent.sleep()
    habit = agent.get_habit("action")
    assert habit < 0.5  # Habit decay
```

---

## Отладка неудачных тестов

### Шаг 1. Прочитать ошибку

```
AssertionError: assert 45 > 60
  where 45 = high_da_count
```

Что не удалось? Значение переменной неверно. Почему? Это нужно выяснить.

### Шаг 2. Запуск с подробным выводом

```bash
pytest tests/test_basal_ganglia.py::failing_test -v --tb=long
```

### Шаг 3. Добавить отладочную печать

```python
def test_something():
    result = gate.choose(channels)
    print(f"DEBUG: result = {result}")
    print(f"DEBUG: channels = {channels}")
    assert result == expected  # Now you see debug output
```

Запуск: `pytest -s` (не перехватывать вывод).

### Шаг 4. Средства отладки

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # Now you can step through code
```

---

## Типичные проблемы

### Проблема: неустойчивый тест (то проходит, то нет)

**Причина:** стохастическое поведение при недостаточной выборке.

**Решение:** увеличить объём выборки.

```python
# Flaky (50 samples)
for _ in range(50):
    action = gate.choose(channels)
# Assertion on frequency might pass or fail randomly

# Robust (1000 samples)
for _ in range(1000):
    action = gate.choose(channels)
# Much more stable statistics
```

### Проблема: тест падает время от времени

**Причина:** сравнение чисел с плавающей точкой или случайность.

**Решение:** использовать допуски.

```python
# Can fail due to floating point
assert habit == 0.5

# Better with tolerance
import math
assert math.isclose(habit, 0.5, rel_tol=1e-5)
```

### Проблема: тест проходит, хотя не должен

**Причина:** неверное утверждение, либо тест на самом деле ничего не проверяет.

**Решение:** намеренно сделать утверждение ложным, чтобы убедиться, что тест работает.

```python
def test_my_feature():
    # Intentionally swap expected to make it fail
    assert action == "wrong_action"  # Should fail
    # If it doesn't fail, something is wrong with the test!
```

---

## Шаблон документации теста

При написании сложного теста объясните его:

```python
def test_complex_scenario():
    """
    Test: Action selection with competing factors
    
    Scenario:
      - Two actions: "aggressive" (go=0.8, nogo=0.1) vs "cautious" (go=0.2, nogo=0.8)
      - High cortisol (stress) makes NoGo dominate
      - Even with go_weight advantage, NoGo-biased action should win
    
    Expected Behavior:
      - With high cortisol, "cautious" selected more often
      - Cortisol effect: multiplies nogo_weight
      
    Verification:
      - 100 selections, count distribution
      - Assert "cautious" > "aggressive" with high cortisol
      - Assert opposite with low cortisol
    """
    # Test code here...
```

---

## Дальнейшие шаги

1. **Запустить существующие тесты** — понять, как они устроены
2. **Прочитать файлы тестов** — изучить образцы тестирования
3. **Написать простой тест** — начать с основного случая
4. **Написать сложный тест** — добавить граничные случаи и стохастическое поведение
5. **Включить в набор тестов** — прогнать полный набор

---

## Источники

- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.ru.md) — справочник разработчика
- [QUICK_START.md](QUICK_START.ru.md) — краткие примеры
- [pytest documentation](https://docs.pytest.org/) — официальное руководство pytest
- Исходный код в `src/` — образцы находятся там

---

**Последнее обновление:** февраль 2026 г.  
**Статус:** завершено и актуально
