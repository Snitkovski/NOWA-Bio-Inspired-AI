# Quick Start Guide

Russian version: [QUICK_START.ru.md](QUICK_START.ru.md)



**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


**Time to first run:** 5 minutes  
**Difficulty:** Beginner-friendly  
**Version:** 2.1

---

## ⚡ 1. Install (2 minutes)

### Requirements
- Python 3.13+
- pip (Python package manager)

### Steps

```bash
# Navigate to project folder
cd e:\git\NOWA-Cognitive

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from src.agent import Agent; print('✅ Ready!')"
```

---

## 🚀 2. Run Tests (1 minute)

Verify everything works:

```bash
# Run all tests
pytest tests/ -q

# Expected output:
# 279 passed in ~1.5s ✅
```

---

## 💻 3. Write Your First Program (2 minutes)

Create a file `my_first_agent.py`:

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

Run it:

```bash
python my_first_agent.py
```

Expected output:

```
Agent chose: attack
Agent slept and consolidated learning!
Action channels: dict_keys(['attack', 'defend', 'rest'])
```

---

## 🎲 4. Interactive Example

Create `interactive_agent.py`:

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

Run it:

```bash
python interactive_agent.py
```

---

## 🧬 5. Try Modulating Neuromodulators

See how chemicals affect decisions:

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

## 📊 6. Visualize with GUI

The project includes a graphical interface:

```bash
python src/gui.py
```

The GUI shows:
- Real-time agent state
- Affective responses  
- Neuromodulator levels
- Action selection history
- Learning progress

---

## 📚 7. Next Steps

### Beginner
1. ✅ You've read this guide
2. 📖 Read START_HERE.md
3. 🔍 Explore the demo folder
4. 💻 Write simple scripts

### Intermediate  
1. 📖 Read ARCHITECTURE.md
2. 📚 Study API.md
3. 🧪 Run pytest with -v flag
4. 🔬 Examine test cases

### Advanced
1. 📖 Read source code  
2. 🛠️ Extend the system
3. 🧬 Add new neuromodulators
4. 🎓 See DEVELOPMENT.md

---

## 🐛 Common Issues

### Installation fails
```bash
# Make sure you have Python 3.13+
python --version

# Try upgrading pip first
pip install --upgrade pip
pip install -r requirements.txt
```

### Tests fail
```bash
# Run with verbose output to see what's wrong
pytest tests/ -v

# Check that all dependencies installed
pip install -r requirements.txt
```

### Import errors
```bash
# Make sure you're in the right directory
cd e:\git\NOWA-Cognitive

# Make sure Python can find the src folder
python -c "import sys; print(sys.path)"
```

---

## 💡 Tips

1. **Use the demos**: `python basal_ganglia_demo.py` shows all features
2. **Check tests**: Tests show real usage examples
3. **Read docstrings**: Classes have detailed documentation
4. **Use type hints**: IDE will autocomplete with type info

---

## 🔗 Useful Commands

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

## 📞 Need Help?

1. **Installation**: Check INSTALLATION.en.md
2. **Understanding the system**: Read ARCHITECTURE.md
3. **API details**: Check API.md
4. **Examples**: Look in Demo/ folder
5. **Tests**: Review tests/ folder

---

## ✨ Success! 🎉

You now understand:
- ✅ How to install the project
- ✅ How to create an agent
- ✅ How to register actions
- ✅ How to run selection
- ✅ How to record outcomes
- ✅ How agents learn

**Next:** Pick a topic from the documentation index and dive deeper!

---

**Last Updated**: 2026-02-07  
**Version**: 2.1  
**Status**: ✅ Verified Working
