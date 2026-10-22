# Руководство по установке и настройке

English version: [INSTALLATION.en.md](INSTALLATION.en.md)

**Статус (27 сентября 2026 г.).** Документ ядра. Актуальное научное изложение комплекса на русском и английском языках приведено в [SCIENTIFIC_DESCRIPTION.ru.md](SCIENTIFIC_DESCRIPTION.ru.md). Текст ниже сохраняет формулировки исходной редакции: это нормативный контракт модуля либо лабораторная запись.


## Быстрый старт (5 минут)

### Предварительные требования

- **Python:** 3.10+ (проверено на 3.13.1)
- **Git:** для клонирования репозитория
- **ОС:** Windows, macOS, Linux

### Шаги установки

```bash
# 1. Clone repository
git clone https://github.com/yourusername/NOWA-Cognitive.git
cd NOWA-Cognitive

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
# No third-party dependencies required (stdlib + Tkinter)

# 5. Run tests to verify installation
python -m pytest -q

# Expected: 289 passed ✅
```

**Время: около 2–3 минут (зависит от скорости загрузки)**

---

## Подробная установка

### Шаг 1. Системные требования

#### Windows
```bash
# Check Python version
python --version
# Should be 3.10 or higher

# If not installed, download from:
# https://www.python.org/downloads/

# Verify pip
pip --version
```

#### macOS
```bash
# Using Homebrew
brew install python@3.13

# Verify
python3 --version
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.13 python3-pip python3-venv

# Verify
python3 --version
```

---

### Шаг 2. Клонирование репозитория

**Вариант A: HTTPS (рекомендуется)**
```bash
git clone https://github.com/yourusername/NOWA-Cognitive.git
cd NOWA-Cognitive
```

**Вариант B: SSH**
```bash
git clone git@github.com:yourusername/NOWA-Cognitive.git
cd NOWA-Cognitive
```

**Вариант C: загрузка ZIP**
- Адрес: https://github.com/yourusername/NOWA-Cognitive
- Нажать «Code», затем «Download ZIP»
- Распаковать каталог
- Открыть терминал в этом каталоге

---

### Шаг 3. Виртуальное окружение

**Зачем?** Оно изолирует зависимости проекта от системного Python.

```bash
# Create virtual environment named 'venv'
python -m venv venv
```

**Активация:**

Windows (PowerShell):
```powershell
venv\Scripts\Activate.ps1
```

Windows (CMD):
```cmd
venv\Scripts\activate.bat
```

macOS/Linux:
```bash
source venv/bin/activate
```

**Проверка активации:**
```bash
# Prompt should show (venv) prefix
(venv) $ _
```

---

### Шаг 4. Установка зависимостей

```bash
# Upgrade pip first
pip install --upgrade pip

# Install from requirements.txt
pip install -r requirements.txt
```

**Что устанавливается:**

```
pytest==9.0.2              # Testing framework
pytest-cov==5.0.0          # Test coverage
numpy==2.0.0               # Numerical computing
scipy==1.14.0              # Scientific computing
matplotlib==3.9.0          # Plotting
(no external ML frameworks)
```

**Время установки:** 1–2 минуты

---

### Шаг 5. Проверка установки

```bash
# Run test suite
python -m pytest tests/ -v

# This should show:
# ======================== 289 passed in ~1.2s =========================
```

Если видно **289 passed**, установка готова.

---

## Необязательно: настройка графического интерфейса

### Tkinter (входит в состав Python)

Графический интерфейс использует Tkinter, который поставляется вместе с Python.

**Проверить доступность Tkinter:**

```bash
python -c "import tkinter; print('Tkinter OK')"
```

### В Linux (если потребуется):

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

---

## Настройка среды разработки

### Visual Studio Code (рекомендуется)

1. **Установить VS Code:** https://code.visualstudio.com/

2. **Установить расширения:**
   - Python (Microsoft)
   - Pylance (языковой сервер)
   - Pytest (обозреватель тестов)

3. **Настроить интерпретатор Python:**
   - Нажать `Ctrl+Shift+P`
   - Ввести «Python: Select Interpreter»
   - Выбрать `./venv/bin/python` (виртуальное окружение)

4. **Запуск тестов в VS Code:**
   - Открыть файл теста
   - Нажать значок «Test» на левой панели
   - Нажать «Run All Tests»

---

### PyCharm

1. **Установить PyCharm:** https://www.jetbrains.com/pycharm/

2. **Открыть проект:**
   - File, затем Open, затем каталог NOWA-Cognitive

3. **Настроить интерпретатор:**
   - Settings, затем Project, затем Python Interpreter
   - Add, затем Existing Environment
   - Выбрать `venv/bin/python`

4. **Запуск тестов:**
   - Щёлкнуть правой кнопкой файл теста
   - Выбрать «Run Tests in...»

---

### Vim/Neovim

```bash
# Install language server support
pip install python-lsp-server pylsp-mypy

# In your init.vim, add LSP client config
# (e.g., using vim-lsp plugin)
```

---

## Настройка Docker (необязательно)

### Dockerfile

Создать `Dockerfile` в корне проекта:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["pytest", "tests/", "-v"]
```

### Сборка и запуск

```bash
# Build image
docker build -t nowa-cognitive .

# Run tests
docker run nowa-cognitive

# Run interactive shell
docker run -it nowa-cognitive bash
```

---

## Устранение неполадок

### Проблема: «Command 'python' not found»

**Решение:**
```bash
# Use python3 instead
python3 -m venv venv
python3 -m pip install -r requirements.txt
```

### Проблема: «ModuleNotFoundError: No module named 'pytest'»

**Решение:**
```bash
# Make sure venv is activated
which python  # Should show venv/bin/python

# Reinstall requirements
pip install --upgrade -r requirements.txt
```

### Проблема: «Permission denied: ...venv...»

**Решение (macOS/Linux):**
```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

### Проблема: «No module named tkinter»

**Решение:**

Windows:
- Переустановить Python, отметив параметр Tcl/Tk

macOS:
```bash
brew install python-tk
```

Linux:
```bash
sudo apt-get install python3-tk
```

### Проблема: тесты завершаются с «ImportError»

**Решение:**
```bash
# Make sure you're in the project root directory
cd NOWA-Cognitive

# Verify structure
ls -la src/
ls -la tests/

# Run tests from project root
python -m pytest tests/ -v
```

### Проблема: «pytest: command not found»

**Решение:**
```bash
# Use python -m pytest instead
python -m pytest tests/ -v
```

---

## Настройка для разработки

### Для участия в разработке

```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Install dev dependencies
pip install -r requirements-dev.txt  # If it exists

# 3. Make changes
# ... edit code ...

# 4. Run tests
python -m pytest tests/ -v

# 5. Run linter (optional)
# pylint src/
# flake8 src/

# 6. Commit & push
git add .
git commit -m "Add feature: description"
git push origin feature/your-feature-name

# 7. Open Pull Request on GitHub
```

---

## Структура проекта после установки

```
NOWA-Cognitive/
├── venv/                           # Virtual environment (created)
│   ├── bin/                        # Python interpreter
│   ├── lib/                        # Installed packages
│   └── ...
│
├── src/                            # Source code
│   ├── agent.py                    # Core agent
│   ├── neuromodulators.py          # Phase 2 neuromodulators
│   ├── affect.py                   # Affective system
│   ├── sleep.py                    # Sleep consolidation
│   ├── selector.py                 # Action selection
│   ├── prediction_layer.py         # Plan C
│   ├── intent_memory.py            # Habits
│   ├── hippocampus.py              # Episodic memory
│   ├── cortex.py                   # Semantic memory
│   ├── gui.py                      # GUI (Tkinter)
│   └── ...
│
├── tests/                          # Test suite (219 tests)
│   ├── test_neuromodulators_phase2.py      # Phase 2 tests
│   ├── test_neuromodulator_integration.py  # Integration tests
│   ├── test_agent.py
│   ├── test_affect.py
│   ├── test_sleep.py
│   └── ...
│
├── datasets/                       # Sample data
│   ├── habits.json
│   ├── realizations_*.json
│   └── test.json
│
├── Docs/                           # Documentation (this folder)
│   ├── ARCHITECTURE.md             # System overview
│   ├── API.md                      # API reference
│   ├── TESTING.ru.md                  # Test guide
│   ├── INSTALLATION.ru.md             # This file
│   ├── DEVELOPMENT.md              # Development guide
│   ├── NEUROMODULATORS_PHASE2_SUMMARY.md
│   ├── FINAL_REPORT_NEUROMODULATORS_PHASE2.md
│   └── ...
│
├── Demo/                           # Demo scripts
│   ├── demo_intent_memory.py
│   ├── demo_realizations.py
│   └── examples_training.py
│
├── requirements.txt                # Python dependencies
├── README.md                       # Project README
└── LICENSE                         # PolyForm Strict License 1.0.0
```

---

## Проверка работоспособности

### Проверка 1. Импорт модулей

```bash
python -c "from src.agent import Agent; print('✅ Agent imported')"
python -c "from src.neuromodulators import NeuromodulatorState; print('✅ Neuromodulators imported')"
python -c "from src.affect import AffectiveState; print('✅ Affect imported')"
```

### Проверка 2. Создание агента

```bash
python -c "
from src.agent import Agent
agent = Agent('TestAgent')
print(f'✅ Agent created: {agent.name}')
print(f'✅ Dopamine: {agent.neuromodulators.dopamine}')
"
```

### Проверка 3. Полный набор тестов

```bash
python -m pytest tests/ -v --tb=short

# Should show:
# ======================== 289 passed in ~1.2s =========================
```

---

## Запуск демонстрационных сценариев

```bash
# Demo 1: Intent Memory (Habits)
python Demo/demo_intent_memory.py

# Demo 2: Realizations & Learning
python Demo/demo_realizations.py

# Demo 3: Training Examples
python Demo/examples_training.py
```

---

## Дальнейшие шаги

1. **Читать:** [ARCHITECTURE.md](ARCHITECTURE.ru.md) — обзор системы
2. **Изучить:** [API.md](API.ru.md) — интерфейсы компонентов
3. **Разобрать:** [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.ru.md) — подробности фазы 2
4. **Проверить:** [TESTING.ru.md](TESTING.ru.md) — руководство по проверке
5. **Разрабатывать:** [DEVELOPMENT.md](DEVELOPMENT.ru.md) — участие в разработке

---

## Обычные команды

```bash
# Activate environment (do this first!)
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows

# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_neuromodulators_phase2.py::TestNeuromodulatorPhase2::test_tc1_positive_reinforcement -v

# View test coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run demo
python Demo/demo_intent_memory.py

# Deactivate environment
deactivate
```

---

## Сводка системных требований

| Требование | Версия | Статус |
|------------|---------|--------|
| Python | 3.10+ | Требуется |
| pip | Последняя | Поставляется с Python |
| pytest | 9.0.2+ | В `requirements.txt` |
| Tkinter | Встроенный | Поставляется с Python |
| Git | Последняя | Для клонирования |

---

## Часто задаваемые вопросы

### Вопрос: можно ли использовать Python 3.9?
**Ответ:** Нет. Фаза 2 требует Python 3.10+. Дистрибутив берётся с python.org.

### Вопрос: нужно ли устанавливать что-либо ещё?
**Ответ:** Нет. pip сам загружает все зависимости из `requirements.txt`.

### Вопрос: можно ли обойтись без виртуального окружения?
**Ответ:** Не рекомендуется. Виртуальное окружение изолирует зависимости и предотвращает конфликты.

### Вопрос: как обновить зависимости?
**Ответ:** Выполнить `pip install --upgrade -r requirements.txt`.

### Вопрос: как удалить установку?
**Ответ:** Достаточно удалить каталог NOWA-Cognitive и `venv`. В систему ничего не ставилось.

---

## Поддержка

- **Сообщения об ошибках:** открыть issue на GitHub
- **Документация:** каталог `Docs/`
- **Тесты:** выполнить `pytest tests/ -v`
- **Пример:** каталог `Demo/`

---

**Состояние установки:** завершено

Когда проходят все 219 тестов, NOWA Cognitive готов к использованию.

**Следующий шаг:** прочитать [ARCHITECTURE.md](ARCHITECTURE.ru.md)
