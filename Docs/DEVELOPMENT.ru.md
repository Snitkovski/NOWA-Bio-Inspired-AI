# Руководство по разработке NOWA Cognitive

English version: [DEVELOPMENT.en.md](DEVELOPMENT.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.

## Правила участия

### Прежде чем начать

1. **Прочитать:** [ARCHITECTURE.md](ARCHITECTURE.ru.md) — понять систему
2. **Сверить:** [API.md](API.ru.md) — знать интерфейсы
3. **Проверить:** выполнить `pytest tests/ -v` — убедиться, что исходная линия проходит

---

## Порядок разработки

### 1. Подготовка среды разработки

```bash
# Clone your fork (or use main repo if contributor)
git clone https://github.com/yourusername/NOWA-Cognitive.git
cd NOWA-Cognitive

# Create feature branch
git checkout -b feature/your-feature-name

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dev dependencies (if available)
pip install -r requirements-dev.txt
```

### 2. Внесение изменений

**Пример: добавление новой возможности в нейромедиаторы**

```bash
# Edit file
code src/neuromodulators.py

# Or in your editor:
# 1. Add new method
# 2. Add docstring
# 3. Add type hints
```

### 3. Написание тестов

```bash
# Create test file
code tests/test_my_feature.py

# Write test template:
# def test_my_feature():
#     """Description of what you're testing"""
#     # Arrange
#     # Act
#     # Assert
```

### 4. Запуск тестов

```bash
# Run your new tests
python -m pytest tests/test_my_feature.py -v

# Run all tests to ensure nothing broke
python -m pytest tests/ -v

# Expected: 219+ passed (including your new tests)
```

### 5. Фиксация и отправка

```bash
# Stage changes
git add src/ tests/ Docs/

# Commit with clear message
git commit -m "feat: add new feature to neuromodulators

- Description of what changed
- Why it was necessary
- Any breaking changes (if none, omit)"

# Push to your fork
git push origin feature/your-feature-name
```

### 6. Открытие запроса на слияние

- Перейти на GitHub
- Нажать «Compare & pull request»
- Написать ясное описание
- Дождаться рецензии

---

## Руководство по стилю кода

### Стиль Python (PEP 8)

```python
# GOOD: 4 spaces, clear names, docstrings
class NeuromodulatorState:
    """State of all neurotransmitter levels."""
    
    def __init__(self):
        self.dopamine = 0.1
        self.serotonin = 0.1
    
    def update_from_signals(self, reward: float, novelty: float, conflict: float):
        """Update all modulators based on environmental signals.
        
        Args:
            reward: [-1.0, 1.0] reward prediction error
            novelty: [0.0, 1.0] environment novelty
            conflict: [0.0, 1.0] action conflict
        """
        if reward > 0:
            self.dopamine += 0.25 * reward

# BAD: Unclear names, no docstrings, poor formatting
class NM:
    def __init__(self):
        self.d=0.1
    def upd(self,r,n,c):
        if r>0:self.d+=0.25*r
```

### Соглашения об именах

```python
# Classes: PascalCase
class NeuromodulatorState:
    pass

class AffectiveState:
    pass

# Functions/Methods: snake_case
def update_from_signals(self, reward: float):
    pass

def get_learning_rate_modifier(self) -> float:
    pass

# Constants: UPPER_SNAKE_CASE
DA_BASELINE = 0.1
DECAY_HALF_LIFE = 90

# Private methods: _leading_underscore
def _clamp_all(self):
    pass
```

### Аннотации типов

```python
# ALWAYS use type hints for clarity
from typing import Dict, List, Optional

def consolidate_pattern(
    experience_cluster: List[dict],
    strength: float
) -> Dict[str, float]:
    """Consolidate experiences into pattern."""
    return {}

# Optional for simple cases
def decay_over_time(self, seconds: float) -> None:
    """Decay all modulators over time."""
    pass
```

### Строки документации

```python
class NeuromodulatorState:
    """State of all neurotransmitter levels.
    
    Phase 2 Implementation with 4 modulators:
    - Dopamine (DA): Reward prediction & motivation
    - Serotonin (HT): Stability & temporal depth
    - Norepinephrine (NE): Arousal & attention
    - Cortisol (CORT): Stress response
    
    Range: [0.0, 1.0] for all, clamped automatically.
    Baseline: DA=0.1, HT=0.1, NE=0.1, CORT=0.05
    
    Attributes:
        dopamine (float): Current dopamine level
        serotonin (float): Current serotonin level
        norepinephrine (float): Current norepinephrine level
        cortisol (float): Current cortisol level
    """
    
    def update_from_signals(
        self,
        reward: float,
        novelty: float,
        conflict: float
    ) -> None:
        """Update all modulators based on environmental signals.
        
        Implements Phase 2 specification exactly.
        
        Args:
            reward: [-1.0, 1.0] reward prediction error
            novelty: [0.0, 1.0] environmental novelty
            conflict: [0.0, 1.0] action conflict/uncertainty
            
        Returns:
            None (updates internal state)
            
        Raises:
            ValueError: If parameters are out of valid ranges
            
        Note:
            All values are clamped to [0.0, 1.0] after update.
            
        Example:
            >>> state = NeuromodulatorState()
            >>> state.update_from_signals(0.8, 0.3, 0.0)
            >>> state.dopamine
            0.3
        """
```

---

## Принципы архитектуры

### 1. Нейромедиаторы не принимают решение

**Неверно:**
```python
def choose_action(self):
    if self.dopamine > 0.5:
        return "attack"  # VIOLATION!
```

**Верно:**
```python
def choose_action(self):
    # Selector chooses, neuromodulators only modify
    base_confidence = compute_confidence()
    modified_rate = base_confidence * self.get_learning_rate_modifier()
    return selector.choose(modified_rate)
```

### 2. Нет обучения в бодрствовании

**Неверно:**
```python
def step(self):
    # Store experience
    self.hippocampus.add(experience)
    # WRONG: Learning during waking!
    self.cortex.consolidate(experience)
```

**Верно:**
```python
def step(self):
    # Only store experience, don't learn
    self.hippocampus.add(experience)
    
def sleep(self):
    # Learning only happens here
    self.sleep_manager.consolidate()
```

### 3. Эпизодическая память неизменяема

**Неверно:**
```python
# Trying to modify hippocampal memories
experience.reward = 0.9  # This changes the past!
```

**Верно:**
```python
# Hippocampus stores immutable records
experience = Experience(reward=0.8)
hippocampus.add(experience)  # Stored forever, unchanged
```

### 4. Селектор — единственный выбирающий действие

**Неверно:**
```python
# Directly returning action from affect
def choose_action(affect):
    if affect.valence > 0:
        return "happy_action"  # Only Selector can choose!
```

**Верно:**
```python
# Get pressures from all sources
pressures = {
    "action1": 0.8,
    "action2": 0.3,
}
# Only selector decides
return selector.choose(pressures)
```

---

## Требования к тестам

### Для любого изменения кода

1. **Модульные тесты обязательны**
   - Проверять отдельные методы
   - Подменять внешние зависимости
   - Покрывать успешный путь и граничные случаи

2. **Интеграционные тесты**
   - Проверять взаимодействие модулей
   - Убеждаться, что сигналы распространяются верно
   - Проверять согласованность состояния

3. **Покрытие тестами**
   - Не менее 80 % покрытия кода
   - Все открытые методы проверены
   - Все ветви проверены

### Пример файла теста

```python
import pytest
from src.neuromodulators import NeuromodulatorState

class TestNewFeature:
    """Test suite for new neuromodulator feature."""
    
    def test_basic_functionality(self):
        """Test basic operation of new feature."""
        state = NeuromodulatorState()
        # ... test code ...
        assert state.dopamine > 0.0
    
    def test_edge_case_zero_input(self):
        """Test with zero input values."""
        state = NeuromodulatorState()
        state.update_from_signals(0.0, 0.0, 0.0)
        assert state.dopamine == 0.1  # No change from baseline
    
    def test_edge_case_max_input(self):
        """Test with maximum input values."""
        state = NeuromodulatorState()
        state.update_from_signals(1.0, 1.0, 1.0)
        # All should be clamped to <= 1.0
        assert state.dopamine <= 1.0
        assert state.serotonin <= 1.0
    
    def test_consistency_with_spec(self):
        """Verify Phase 2 specification compliance."""
        state = NeuromodulatorState()
        state.dopamine = 0.1
        state.update_from_signals(reward=1.0, novelty=0.0, conflict=0.0)
        # From spec: DA increases by 0.25 * reward
        assert state.dopamine == 0.1 + 0.25 * 1.0
```

---

## Обычные задачи разработки

### Добавление нового метода-модификатора

```python
# In src/neuromodulators.py

def get_my_new_modifier(self) -> float:
    """Description of what this modifier does.
    
    Returns:
        float: Modifier value in valid range
        
    Example:
        >>> state = NeuromodulatorState()
        >>> state.dopamine = 0.8
        >>> modifier = state.get_my_new_modifier()
        >>> 0.0 <= modifier <= 1.0
        True
    """
    # Compute modifier based on neuromodulator state
    modifier = 1.0 + 0.3 * self.dopamine
    
    # ALWAYS clamp to valid range
    return max(MIN_VALUE, min(MAX_VALUE, modifier))
```

**Затем проверить его:**
```python
def test_my_new_modifier():
    state = NeuromodulatorState()
    
    # Test low state
    state.dopamine = 0.0
    mod_low = state.get_my_new_modifier()
    assert mod_low >= 0.0
    
    # Test high state
    state.dopamine = 1.0
    mod_high = state.get_my_new_modifier()
    assert mod_high <= 1.5
    
    # Test it increases with input
    assert mod_high > mod_low
```

### Изменение update_from_signals

**Крайняя осторожность.** Это проверяется тестами спецификации фазы 2.

```python
# Phase 2 specification (DO NOT CHANGE without good reason):
# Dopamine: reward > 0 → DA += 0.25 * reward
# Serotonin: reward > 0 ∧ conflict == 0 → HT += 0.05 * reward
# Norepinephrine: NE += 0.30 * novelty + 0.15 * conflict
# Cortisol: CORT += 0.20 * |reward| + 0.25 * conflict

# If you must change:
# 1. Get approval from project maintainers
# 2. Update specification document
# 3. Update ALL tests
# 4. Run: pytest tests/test_neuromodulators_phase2.py -v
# 5. Verify all 14 tests still pass
```

---

## Советы по отладке

### Печать

```python
def update_from_signals(self, reward, novelty, conflict):
    print(f"[DEBUG] Input: reward={reward}, novelty={novelty}, conflict={conflict}")
    
    if reward > 0:
        self.dopamine += 0.25 * reward
        print(f"[DEBUG] Updated dopamine to {self.dopamine}")
```

### pytest -v и --tb

```bash
# Verbose output
python -m pytest tests/test_something.py -v

# Full traceback
python -m pytest tests/test_something.py -v --tb=long

# Print debugging output
python -m pytest tests/test_something.py -v -s
```

### pdb (отладчик Python)

```python
def problematic_function(self):
    import pdb; pdb.set_trace()  # Execution stops here
    # You can now:
    # p variable_name    - print variable
    # n                   - next line
    # c                   - continue
    # l                   - list code
```

### Проверка утверждений

```python
def test_something():
    state = NeuromodulatorState()
    state.dopamine = 0.5
    
    # If this fails, pytest shows what was expected vs actual
    assert state.dopamine == 0.5  # Clear failure message
```

---

## Оптимизация производительности

### Прежде чем оптимизировать

1. **Измерить:** действительно ли это замедляет работу?
   ```bash
   python -m pytest tests/ --durations=10
   ```

2. **Профилировать:** какая часть медленна?
   ```python
   import cProfile
   cProfile.run("agent.step(event)")
   ```

3. **Оптимизировать:** только после измерения

### Обычные узкие места

- Доступ к памяти (для численных операций использовать numpy)
- Операции со списками (выбирать подходящие структуры данных)
- Повторные вычисления (кэшировать результаты)

---

## Требования к документации

### Документация кода

У каждого открытого метода должны быть:
- Строка документации (что метод делает)
- Аннотации типов (типы параметров и возвращаемого значения)
- Пример (как этим пользоваться)

### Документация файла

Каждый файл начинается так:
```python
"""Module description and purpose.

This module implements [what it does] for [which part of system].

Key classes:
- ClassName1: Brief description
- ClassName2: Brief description

Example:
    >>> from src.module import Class
    >>> obj = Class()
    >>> result = obj.method()
"""
```

### Документация в Markdown

При добавлении возможностей обновлять соответствующие документы:
- [ARCHITECTURE.md](ARCHITECTURE.ru.md) — изменения системы
- [API.md](API.ru.md) — новые методы и классы
- [TESTING.ru.md](TESTING.ru.md) — новые категории тестов

---

## Сообщения фиксации Git

### Формат

```
type(scope): brief message

Longer explanation of what changed and why.
Can be multiple paragraphs.

- List specific changes
- Can include bullet points

Fixes #123  (if related to issue)
```

### Типы

- `feat:` новая возможность
- `fix:` исправление ошибки
- `docs:` документация
- `test:` изменения тестов
- `refactor:` перестройка кода
- `perf:` улучшение производительности

### Примеры

```bash
git commit -m "feat(neuromodulators): add dopamine spike mechanism

- Dopamine now increases 25% more on unexpected positive rewards
- Updated get_learning_rate_modifier() to consider spike state
- Added tests for spike behavior (3 new unit tests)

Implements feature requested in issue #42"

git commit -m "fix(selector): ensure stochastic selection works for low confidence"

git commit -m "docs: update API reference with new modifier methods"
```

---

## Перечень проверки перед рецензией

Перед отправкой запроса на слияние убедиться:

- Все тесты проходят: `pytest tests/ -v`
- Стиль кода следует руководству выше
- Аннотации типов стоят на всех открытых методах
- Строки документации содержат примеры
- Тесты покрывают новый код (покрытие 80 % и выше)
- Нет жёстко заданных значений без обоснования
- Нейромедиаторы только изменяют, но никогда не решают
- Нет обучения в фазе бодрствования
- Селектор по-прежнему единственный, кто выбирает действие
- Документы обновлены, если изменился API
- Сообщение фиксации содержательно
- Не осталось отладочной печати и закомментированного кода

---

## Источники

### Внутренняя документация
- [ARCHITECTURE.md](ARCHITECTURE.ru.md) — устройство системы
- [API.md](API.ru.md) — интерфейсы компонентов
- [TESTING.ru.md](TESTING.ru.md) — руководство по тестам
- [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.ru.md) — спецификация фазы 2

### Внешние источники
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [pytest Documentation](https://docs.pytest.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Git Commit Best Practices](https://chris.beams.io/posts/git-commit/)

---

## Как получить помощь

1. **Задавать вопросы в комментариях к запросу на слияние**
   - Сопровождающие помогут.

2. **Смотреть примеры тестов**
   - В похожих тестах видны образцы.

3. **Читать ARCHITECTURE.md**
   - Там объяснены проектные решения.

4. **Смотреть историю git**
   - `git log -p src/file.py` показывает, как развивался код

---

## Порядок выпуска (для сопровождающих)

```bash
# Update version
# 1. Update src/__version__.py
# 2. Update version in setup.py or pyproject.toml

# Run full test suite
python -m pytest tests/ -v

# Create tag
git tag v1.2.0

# Push to main
git push origin main
git push origin v1.2.0

# Create release on GitHub
# - Summary of changes
# - Breaking changes warning
# - Link to full changelog
```

---

**Удачной работы.**

Помните: сначала тесты, затем код, оптимизация в последнюю очередь.
