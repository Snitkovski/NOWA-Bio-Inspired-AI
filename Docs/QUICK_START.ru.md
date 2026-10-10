# Краткое руководство

English version: [QUICK_START.en.md](QUICK_START.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


**Время до первого запуска:** 5 минут
**Сложность:** для начинающих
**Версия:** 2.1

---

## 1. Установка (2 минуты)

### Требования
- Python 3.13+
- pip (диспетчер пакетов Python)

### Шаги

```bash
# Navigate to project folder
cd e:\git\NOWA-Cognitive

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from src.agent import Agent; print('✅ Ready!')"
```

---

## 2. Запуск тестов (1 минута)

Проверьте, что всё работает:

```bash
# Run all tests
pytest tests/ -q

# Expected output:
# 279 passed in ~1.5s ✅
```

---

## 3. Первая программа (2 минуты)

Создайте файл `my_first_agent.py`:

```python
from src.agent import Agent

# Create an agent
agent = Agent(agent_name="MyBot")

# Register some possible actions
agent.register_action_channel(
    action_id="attack",
    go_weight=0.8,      # Strong approach
    nogo_weight=0.2     # Weak avoid
)

agent.register_action_channel(
    action_id="defend",
    go_weight=0.5,      # Medium balance
    nogo_weight=0.5
)

agent.register_action_channel(
    action_id="rest",
    go_weight=0.3,      # Weak approach
    nogo_weight=0.7     # Strong avoid
)

# Let the BG choose an action
action = agent.choose_action_via_basal_ganglia(pfc_pressure=1.0)
print(f"Agent chose: {action}")

# Record what happened
agent.record_action_outcome(
    action=action,
    success=True,
    dopamine=1.5
)

# Agent sleeps and learns
agent.sleep()
print("Agent slept and consolidated learning!")

# Check the state
state = agent.get_basal_ganglia_state()
print(f"Action channels: {state['action_channels'].keys()}")
```

Запустите:

```bash
python my_first_agent.py
```

Ожидаемый вывод:

```
Agent chose: attack
Agent slept and consolidated learning!
Action channels: dict_keys(['attack', 'defend', 'rest'])
```

---

## 4. Интерактивный пример

Создайте `interactive_agent.py`:

```python
from src.agent import Agent

agent = Agent(agent_name="InteractiveBot")

# Register actions
agent.register_action_channel("action_a", go_weight=0.8, nogo_weight=0.2)
agent.register_action_channel("action_b", go_weight=0.5, nogo_weight=0.5)
agent.register_action_channel("action_c", go_weight=0.2, nogo_weight=0.8)

# Simulate 10 decisions
for day in range(1, 11):
    print(f"\n=== Day {day} ===")
    
    # Let BG choose
    action = agent.choose_action_via_basal_ganglia(pfc_pressure=0.5)
    print(f"Chose: {action}")
    
    # See what the scores were (for learning)
    bg_state = agent.get_basal_ganglia_state()
    channel = bg_state['action_channels'][action]
    print(f"  go_weight: {channel['go_weight']:.2f}")
    print(f"  nogo_weight: {channel['nogo_weight']:.2f}")
    print(f"  habit_strength: {channel['habit_strength']:.2f}")
    
    # Simulate outcome (action_a is most successful)
    success = (action == "action_a")
    dopamine = 2.0 if success else 0.0
    
    agent.record_action_outcome(action, success=success, dopamine=dopamine)
    
    # Every 3 days, agent sleeps and learns
    if day % 3 == 0:
        agent.sleep()
        print("💤 Slept and learned!")

print("\n=== Learning Summary ===")
print("action_a should have higher habit_strength now!")
```

Запустите:

```bash
python interactive_agent.py
```

---

## 5. Модуляция нейромодуляторов

Посмотрите, как химические сигналы влияют на решения:

```python
from src.agent import Agent

agent = Agent()

agent.register_action_channel("approach", go_weight=0.7, nogo_weight=0.3)
agent.register_action_channel("avoid", go_weight=0.3, nogo_weight=0.7)

print("Testing neuromodulator effects:\n")

# Test 1: High dopamine (motivated)
print("1️⃣ HIGH DOPAMINE (motivated)")
agent.neuromodulators.dopamine = 2.0
choices = []
for _ in range(10):
    action = agent.choose_action_via_basal_ganglia(pfc_pressure=0.0)
    choices.append(action)
print(f"   'approach' chosen {choices.count('approach')}/10 times")

# Test 2: High cortisol (stressed)
print("\n2️⃣ HIGH CORTISOL (stressed)")
agent.neuromodulators.dopamine = 1.0  # Reset
agent.neuromodulators.cortisol = 2.0
choices = []
for _ in range(10):
    action = agent.choose_action_via_basal_ganglia(pfc_pressure=0.0)
    choices.append(action)
print(f"   'avoid' chosen {choices.count('avoid')}/10 times")

# Test 3: High norepinephrine (exploring)
print("\n3️⃣ HIGH NOREPINEPHRINE (exploring)")
agent.neuromodulators.cortisol = 1.0  # Reset
agent.neuromodulators.norepinephrine = 2.0
choices = []
for _ in range(20):
    action = agent.choose_action_via_basal_ganglia(pfc_pressure=0.0)
    choices.append(action)
variety = len(set(choices))
print(f"   Chose both actions: {variety == 2}")
print(f"   More variety in 20 decisions")
```

---

## 6. Визуализация в графическом интерфейсе

В проекте есть графический интерфейс:

```bash
python src/gui.py
```

Интерфейс показывает:
- состояние агента в реальном времени
- аффективные ответы
- уровни нейромодуляторов
- историю выбора действий
- ход обучения

---

## 7. Дальнейшие шаги

### Начинающий
1. Настоящее руководство прочитано
2. Прочитать START_HERE.md
3. Осмотреть каталог демонстраций
4. Написать простые сценарии

### Средний уровень
1. Прочитать ARCHITECTURE.md
2. Изучить API.md
3. Запустить pytest с флагом `-v`
4. Разобрать тестовые случаи

### Продвинутый уровень
1. Прочитать исходный код
2. Расширить систему
3. Добавить новые нейромодуляторы
4. См. DEVELOPMENT.md

---

## Типичные затруднения

### Установка не удаётся
```bash
# Make sure you have Python 3.13+
python --version

# Try upgrading pip first
pip install --upgrade pip
pip install -r requirements.txt
```

### Тесты не проходят
```bash
# Run with verbose output to see what's wrong
pytest tests/ -v

# Check that all dependencies installed
pip install -r requirements.txt
```

### Ошибки импорта
```bash
# Make sure you're in the right directory
cd e:\git\NOWA-Cognitive

# Make sure Python can find the src folder
python -c "import sys; print(sys.path)"
```

---

## Замечания

1. **Демонстрации:** `python basal_ganglia_demo.py` показывает все возможности
2. **Тесты:** в них видны реальные примеры использования
3. **Строки документации:** у классов подробные описания
4. **Аннотации типов:** среда разработки дополнит имена по типам

---

## Полезные команды

```bash
# Run all tests
pytest tests/ -q

# Run BG tests only
pytest tests/test_basal_ganglia.py -v

# Run a specific test
pytest tests/test_basal_ganglia.py::TestActionChannel -v

# Run with coverage
pytest --cov=src tests/

# Run GUI
python src/gui.py

# Run demo
python basal_ganglia_demo.py
```

---

## Если нужна помощь

1. **Установка:** см. INSTALLATION.ru.md
2. **Устройство системы:** прочитать ARCHITECTURE.md
3. **Сведения об интерфейсе:** см. API.md
4. **Примеры:** каталог Demo/
5. **Тесты:** каталог tests/

---

## Итог

Теперь понятно:
- как установить проект
- как создать агента
- как зарегистрировать действия
- как запустить выбор
- как записать исход
- как агенты обучаются

**Далее:** выберите тему в указателе документации и углубитесь в неё.

---

**Последнее обновление:** 2026-02-07
**Версия:** 2.1
**Статус:** проверено, работает
