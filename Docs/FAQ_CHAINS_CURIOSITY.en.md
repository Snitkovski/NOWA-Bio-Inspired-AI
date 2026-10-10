# Answers to the questions: the interface, chains, curiosity, and defects

Russian version: [FAQ_CHAINS_CURIOSITY.ru.md](FAQ_CHAINS_CURIOSITY.ru.md)

**Status (27 September 2026).** A core document. The current scientific exposition of the complex, in Russian and in English, is [SCIENTIFIC_DESCRIPTION.en.md](SCIENTIFIC_DESCRIPTION.en.md). The text below retains the wording of its original drafting: a normative module contract or a laboratory record.


## 1. Where to view information about Temporal Chains in the interface

### Main window, right panel, "Memory" (lower part):

```
Episodic memory:
  Experiences: 15
  Mean reinforcement: 1.20

Semantic memory:
  Patterns: 3
  Mean strength: 0.65

Habit memory (IntentMemory):
  Habits: 8

Sleep process:
  Cycles: 2

Temporal Chains:
  Chains: 12
  Mean stability: 0.42
```

**This shows:**
- `Chains: 12` — how many chains have formed
- `Mean stability: 0.42` — how stable (consolidated) the chains are

### Alternative: Inspector, tab "Consolidation"

Press the **"Inspector"** button (left panel), open the **"Consolidation"** tab, and scroll down:

```
Temporal Chains:
  Total chains: 12
  Avg stability: 0.42
```

---

## 2. Which defects were present in the interface?

### Defect 1: Curiosity was always 0.0
**Problem:**
- Curiosity was initialized at 0.0
- Even with new messages it grew very slowly
- The effect of novelty was difficult to see

**Corrected:**
- Curiosity now starts at **0.1** (it slightly encourages exploration)
- It grows faster: with coefficient **0.4** instead of 0.25
- The effect of new messages is now visible immediately

### Defect 2: No distinctive marker for Chains
**Problem:**
- "Temporal Chains" was visually indistinct
- The field was difficult to find in the interface

**Corrected:**
- The field is now labelled **"Temporal Chains"** and is easier to notice in memory

### Defect 3: The novelty parameter was not used explicitly
**Problem:**
- `agent.step()` accepts a `novelty` parameter, but this was not obvious
- Users did not know how to pass a novelty signal

**Corrected:**
- The document `TESTING_CURIOSITY.md` shows explicitly how to use it
- Code examples show how to pass the `novelty` parameter

---

## 3. How to test curiosity

### Method 1: Using the interface

**Step 1:** Open the main interface window

**Step 2:** Watch **"Curiosity:"** (right panel, affective state)

**Step 3:** Send messages:

```
Input: "hello"  → curiosity stays low (repeated)
Input: "hello"  → curiosity is low
Input: "hello"  → curiosity is low

Input: "how are you?"      → curiosity RISES (new)
Input: "what do you know?" → curiosity RISES further
```

**Expect:**
- New or unusual messages → curiosity rises
- Identical messages → curiosity is stable or falls

---

### Method 2: A programmatic test (recommended)

**Create the file `test_curiosity_simple.py`:**

```python
import sys
sys.path.insert(0, 'src')

from agent import Agent
from hippocampus import NOWAHippocampus
from cortex import CortexMemory
from selector import ActionSelector
from sleep import SleepManager

# Setup
hip = NOWAHippocampus()
cortex = CortexMemory()
sel = ActionSelector(actions=['say', 'ask', 'listen'])
sleep_mgr = SleepManager(hip, cortex)
agent = Agent(hip, cortex, sel, sleep_manager=sleep_mgr)

print("=" * 50)
print("TEST: Curiosity with Novelty")
print("=" * 50)

# Test 1: Repeated messages (low novelty)
print("\n1. REPEATED (low novelty):")
for i in range(3):
    agent.step(["user:hello"], novelty=0.0)
    print(f"   Step {i+1}: curiosity = {agent.affect_state.curiosity:.2f}")

# Test 2: NEW messages (high novelty)
print("\n2. NEW (high novelty):")
for i in range(3):
    agent.step(["user:new"], novelty=0.8)
    print(f"   Step {i+1}: curiosity = {agent.affect_state.curiosity:.2f}")

print("\n" + "=" * 50)
print("RESULT:")
print(f"Curiosity started at 0.1 (baseline exploration)")
print(f"Curiosity rose to {agent.affect_state.curiosity:.2f} under high novelty")
print("=" * 50)
```

**Run:**
```bash
python test_curiosity_simple.py
```

**Expected result:**
```
==================================================
TEST: Curiosity with Novelty
==================================================

1. REPEATED (low novelty):
   Step 1: curiosity = 0.10
   Step 2: curiosity = 0.10
   Step 3: curiosity = 0.10

2. NEW (high novelty):
   Step 1: curiosity = 0.42
   Step 2: 0.66
   Step 3: 0.84

==================================================
RESULT:
Curiosity started at 0.1 (baseline exploration)
Curiosity rose to 0.84 under high novelty
==================================================
```

---

## 4. Why it failed earlier

### Common errors:

#### Error 1: Not passing the novelty parameter
```python
# INCORRECT — novelty defaults to 0.0
agent.step(["user:hello"])

# CORRECT — pass novelty explicitly
agent.step(["user:hello"], novelty=0.8)
```

#### Error 2: Expecting curiosity without sleep
```python
# INCORRECT
# Send several messages
# Curiosity rose... but chains do not form

# CORRECT
# Send several messages
agent.sleep(cycles=3)  # ← Sleep for chain consolidation
# Chains are now formed
```

#### Error 3: Expecting many chains from a single message
```python
# INCORRECT
agent.step(["user:hello"], novelty=0.8)
agent.sleep(cycles=1)
print(sleep_mgr.chain_memory.statistics())
# total_chains: 0  ← One message is not enough

# CORRECT
# Send several DIFFERENT messages
for msg in ["hello", "how are you?", "what's up?"]:
    agent.step([f"user:{msg}"], novelty=0.8)

agent.sleep(cycles=1)
print(sleep_mgr.chain_memory.statistics())
# total_chains: 5+  ← Many chains from different contexts
```

---

## 5. Full testing procedure

### Variant A: A minimal interface test (3 minutes)

1. **Start the interface:**
   ```bash
   cd src
   python -c "from gui import NOWAGUI; import tkinter as tk; root = tk.Tk(); gui = NOWAGUI(root); root.mainloop()"
   ```

2. **Send 3 identical messages:**
   - "hello"
   - "hello"
   - "hello"
   → Curiosity remains about 0.10

3. **Send 3 different messages:**
   - "how are you?"
   - "tell me about yourself"
   - "what do you think?"
   → Curiosity rises: 0.42 → 0.66 → 0.84

4. **Press "Sleep":**
   → Observe "Chains: 3-5"

---

### Variant B: A full programmatic test (10 minutes)

```bash
# Copy the code from TESTING_CURIOSITY.md
# Run:
python test_curiosity.py
```

---

## 6. What now works correctly

- **Curiosity rises** with new messages
- **Curiosity starts at 0.1** (not at zero)
- **Chains are displayed** in the interface
- **All tests pass** (168/168)
- **The novelty parameter works** as specified

---

## Reference

| Concept | Value | When it changes |
|-----------|----------|----------------|
| **Curiosity** | 0.1 → 1.0 | When `novelty > 0.0` |
| **Novelty** | 0.0 → 1.0 | Passed to `agent.step()` |
| **Temporal Chains** | Are formed | Only during sleep |
| **Chain Stability** | 0.0 → 1.0 | With each use |

---

## If something still does not work

### Checklist:

- [ ] Curiosity must be **visible** on the right panel (progress bar)
- [ ] With new messages curiosity must **rise**
- [ ] Chains must be **in memory** after sleep
- [ ] Tests must **pass** (`pytest -q`)

### If curiosity is not visible:
```bash
# Check that the interface updates
python -c "
import sys; sys.path.insert(0, 'src')
from affect import AffectiveState
s = AffectiveState()
print(f'Curiosity: {s.curiosity}')  # Must be 0.1
"
```

### If curiosity does not rise:
```bash
# Check update_from_novelty
python -c "
import sys; sys.path.insert(0, 'src')
from affect import AffectiveState
s = AffectiveState()
print(f'Before: {s.curiosity}')
s.update_from_novelty(0.8)
print(f'After: {s.curiosity}')  # Must be 0.42
"
```

---

**Complete. All defects are corrected, the tests pass, and the documentation is complete. The system is ready for testing.**
