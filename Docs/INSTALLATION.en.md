# 📦 Installation & Setup Guide

Russian version: [INSTALLATION.ru.md](INSTALLATION.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## Quick Start (5 minutes)

### Prerequisites

- **Python:** 3.10+ (tested on 3.13.1)
- **Git:** For cloning repository
- **OS:** Windows, macOS, Linux

### Installation Steps

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

**Time: ~2-3 minutes (depends on download speed)**

---

## Detailed Installation

### Step 1: System Requirements

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

### Step 2: Clone Repository

**Option A: HTTPS (recommended)**
```bash
git clone https://github.com/yourusername/NOWA-Cognitive.git
cd NOWA-Cognitive
```

**Option B: SSH**
```bash
git clone git@github.com:yourusername/NOWA-Cognitive.git
cd NOWA-Cognitive
```

**Option C: Download ZIP**
- Visit: https://github.com/yourusername/NOWA-Cognitive
- Click "Code" → "Download ZIP"
- Unzip folder
- Open terminal in folder

---

### Step 3: Virtual Environment

**Why?** Isolates project dependencies from system Python.

```bash
# Create virtual environment named 'venv'
python -m venv venv
```

**Activate it:**

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

**Verify activation:**
```bash
# Prompt should show (venv) prefix
(venv) $ _
```

---

### Step 4: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install from requirements.txt
pip install -r requirements.txt
```

**What gets installed:**

```
pytest==9.0.2              # Testing framework
pytest-cov==5.0.0          # Test coverage
numpy==2.0.0               # Numerical computing
scipy==1.14.0              # Scientific computing
matplotlib==3.9.0          # Plotting
(no external ML frameworks)
```

**Installation time:** 1-2 minutes

---

### Step 5: Verify Installation

```bash
# Run test suite
python -m pytest tests/ -v

# This should show:
# ======================== 289 passed in ~1.2s =========================
```

If you see **289 passed**, you're ready! ✅

---

## Optional: GUI Setup

### Tkinter (included with Python)

The GUI uses Tkinter which is bundled with Python.

**Verify Tkinter is available:**

```bash
python -c "import tkinter; print('Tkinter OK')"
```

### On Linux (if needed):

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

---

## IDE Setup

### Visual Studio Code (Recommended)

1. **Install VS Code:** https://code.visualstudio.com/

2. **Install Extensions:**
   - Python (by Microsoft)
   - Pylance (language server)
   - Pytest (test explorer)

3. **Configure Python Interpreter:**
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose `./venv/bin/python` (your virtual environment)

4. **Run Tests in VS Code:**
   - Open test file
   - Click "Test" icon in left sidebar
   - Click "Run All Tests"

---

### PyCharm

1. **Install PyCharm:** https://www.jetbrains.com/pycharm/

2. **Open Project:**
   - File → Open → NOWA-Cognitive folder

3. **Configure Interpreter:**
   - Settings → Project → Python Interpreter
   - Add → Existing Environment
   - Select `venv/bin/python`

4. **Run Tests:**
   - Right-click test file
   - Select "Run Tests in..."

---

### Vim/Neovim

```bash
# Install language server support
pip install python-lsp-server pylsp-mypy

# In your init.vim, add LSP client config
# (e.g., using vim-lsp plugin)
```

---

## Docker Setup (Optional)

### Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["pytest", "tests/", "-v"]
```

### Build & Run

```bash
# Build image
docker build -t nowa-cognitive .

# Run tests
docker run nowa-cognitive

# Run interactive shell
docker run -it nowa-cognitive bash
```

---

## Troubleshooting

### Issue: "Command 'python' not found"

**Solution:**
```bash
# Use python3 instead
python3 -m venv venv
python3 -m pip install -r requirements.txt
```

### Issue: "ModuleNotFoundError: No module named 'pytest'"

**Solution:**
```bash
# Make sure venv is activated
which python  # Should show venv/bin/python

# Reinstall requirements
pip install --upgrade -r requirements.txt
```

### Issue: "Permission denied: ...venv..."

**Solution (macOS/Linux):**
```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

### Issue: "No module named tkinter"

**Solution:**

Windows:
- Reinstall Python with Tcl/Tk option checked

macOS:
```bash
brew install python-tk
```

Linux:
```bash
sudo apt-get install python3-tk
```

### Issue: Tests fail with "ImportError"

**Solution:**
```bash
# Make sure you're in the project root directory
cd NOWA-Cognitive

# Verify structure
ls -la src/
ls -la tests/

# Run tests from project root
python -m pytest tests/ -v
```

### Issue: "pytest: command not found"

**Solution:**
```bash
# Use python -m pytest instead
python -m pytest tests/ -v
```

---

## Development Setup

### For Contributing

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

## Project Structure After Installation

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
│   ├── TESTING.en.md                  # Test guide
│   ├── INSTALLATION.en.md             # This file
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

## Verify Everything Works

### Test 1: Import Modules

```bash
python -c "from src.agent import Agent; print('✅ Agent imported')"
python -c "from src.neuromodulators import NeuromodulatorState; print('✅ Neuromodulators imported')"
python -c "from src.affect import AffectiveState; print('✅ Affect imported')"
```

### Test 2: Create Agent

```bash
python -c "
from src.agent import Agent
agent = Agent('TestAgent')
print(f'✅ Agent created: {agent.name}')
print(f'✅ Dopamine: {agent.neuromodulators.dopamine}')
"
```

### Test 3: Run Full Test Suite

```bash
python -m pytest tests/ -v --tb=short

# Should show:
# ======================== 289 passed in ~1.2s =========================
```

---

## Running Demo Scripts

```bash
# Demo 1: Intent Memory (Habits)
python Demo/demo_intent_memory.py

# Demo 2: Realizations & Learning
python Demo/demo_realizations.py

# Demo 3: Training Examples
python Demo/examples_training.py
```

---

## Next Steps

1. **Read:** [ARCHITECTURE.md](ARCHITECTURE.en.md) for system overview
2. **Explore:** [API.md](API.en.md) for component interfaces
3. **Learn:** [NEUROMODULATORS_PHASE2_SUMMARY.md](NEUROMODULATORS_PHASE2_SUMMARY.en.md) for Phase 2 details
4. **Test:** [TESTING.en.md](TESTING.en.md) for comprehensive testing guide
5. **Develop:** [DEVELOPMENT.md](DEVELOPMENT.en.md) for contributing

---

## Common Commands

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

## System Requirements Summary

| Requirement | Version | Status |
|------------|---------|--------|
| Python | 3.10+ | ✅ Required |
| pip | Latest | ✅ Auto with Python |
| pytest | 9.0.2+ | ✅ In requirements.txt |
| Tkinter | Built-in | ✅ Auto with Python |
| Git | Latest | ✅ For cloning |

---

## Frequently Asked Questions

### Q: Can I use Python 3.9?
**A:** No, Phase 2 requires Python 3.10+. Download from python.org

### Q: Do I need to install anything else?
**A:** No, pip automatically downloads all dependencies from requirements.txt

### Q: Can I run without creating a virtual environment?
**A:** Not recommended. Virtual environments isolate dependencies and prevent conflicts.

### Q: How do I update dependencies?
**A:** Run `pip install --upgrade -r requirements.txt`

### Q: How do I uninstall?
**A:** Just delete the NOWA-Cognitive folder and venv. Nothing installed globally.

---

## Support

- **Issues:** Open issue on GitHub
- **Documentation:** See `Docs/` folder
- **Tests:** Run `pytest tests/ -v`
- **Example:** Check `Demo/` folder

---

**Installation Status:** ✅ Complete

When you see all 219 tests passing, you're ready to use NOWA Cognitive!

🚀 **Next Step:** Read [ARCHITECTURE.md](ARCHITECTURE.en.md)
